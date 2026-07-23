# Real Signal Ingestion (PR4)

## What changed vs. PR3

PR3's `GlobalGoodDiscoveryEngine` proved the full pipeline against
caller-supplied fixture signals. PR4 adds the missing front-front-door:
real HTTP fetches from real public data sources, so the engine can find
opportunities nobody submitted by hand.

**Nothing in PR2 or PR3 was redesigned.** `services/discovery_run.py` (PR2),
`services/pipeline.py` (PR2), `services/discovery_engine.py`'s stage
structure (PR3) are unchanged in shape — PR4 only:
1. adds real provider adapters that produce the SAME raw-signal-dict shape
   PR3's fixtures always used,
2. fixes two real bugs PR3's fixture-only testing never surfaced (see
   "Bugs found via live data" below),
3. adds a second, real front door (`run_good_while_you_sleep`) alongside
   the existing fixture-based one (`run_almaty_good_agent_demo`,
   `run_overnight_good_discovery_demo` — both untouched).

## Methodology

### How providers are selected (Phase 1)

Three, chosen for being real, free, no-authentication-required, stable,
and legally accessible public data:

| Provider | What it is | Signal types |
|---|---|---|
| USGS Significant Earthquakes | US Geological Survey GeoJSON feed | `environmental_risk` |
| GOV.UK Search API | UK Government Digital Service search, queried with 3 fixed grant/funding/policy terms | `funding_available` / `policy_change` |
| UK Environment Agency Flood Monitoring | Real-time flood warnings, Open Government Licence v3 | `environmental_risk` |

No general-purpose web scraping, no arbitrary URL fetching — every URL a
provider adapter can ever call is a hardcoded constant in
`good_agents/services/provider_adapters.py`, never derived from user
input or a search result.

### How signals are normalised (Phase 2, 4)

`services/signals.normalise_signal` turns a raw dict into a `WorldSignal`:
`title`/`summary` are EcoIQ's own restatement; `source_excerpt` is the
verbatim source text (never paraphrased); `content_classification` is
`fact` only if the provider is a declared high-trust type (government/
regulatory/scientific-dataset) AND the raw signal explicitly asserts it —
otherwise `claim`. A signal missing a required field (e.g. no magnitude on
an earthquake record) is skipped rather than guessed.

### How duplicates are detected (Phase 27) and clusters formed (Phase 3)

`dedup_key` = sha256(type, geography/region, sector, normalised title) —
an exact match folds into the same cluster. Near-duplicates cluster via
keyword-overlap on title (≥50% of the smaller title's keywords shared),
never embeddings or an LLM call.

### How evidence quality is judged (Phase 5)

`services/evidence_gate.evaluate_cluster` — deterministic thresholds on
confidence, source diversity, freshness, contradictions, and missing
geography/sector. Can and does conclude `insufficient_evidence` and stop.

### How agents are selected, and why all 114 are not run deeply on every signal (Phase 6-7)

Layer 1-3 (`services/orchestrator.classify_relevant_agents`) is pure
deterministic keyword/domain overlap — free, always runs, caps activation
at `max_activated` (default 6) regardless of how many `GoodAgentDefinition`
rows exist (114, after `seed_all_good_agent_definitions`). Layer 4
(`run_deep_reasoning`) issues exactly ONE combined reasoning call per
signal covering every activated lens together — never one call per lens.
Verified directly:
`good_agents.tests.DiscoveryEngineTests.test_never_activates_more_than_max_activated_even_with_all_114_seeded`.

### How opportunities qualify (Phase 8) — and never fabricate

A cluster becomes a `GoodOpportunity` only if (a) at least one principle
lens activated (zero activations → skipped, a real bug fixed during this
PR — see below) and (b) the Evidence Gate returns `qualify` or `monitor`
(never `reject`/`insufficient_evidence`). No opportunity's confidence,
urgency, or `affected_population` is ever invented — every field traces
to a real signal field.

### How priorities are calculated, and how HumanReview feedback affects them (Phase 12, 15)

`services/prioritisation.prioritise` returns labels
(URGENT/HIGH_LEVERAGE/ZERO_CAPITAL/CAPITAL_REQUIRED/EVIDENCE_GAP/MONITOR)
plus raw dimensions — never a single fabricated score. A deterministic
feedback adjustment (`_pattern_feedback`) looks at prior
`HumanReviewDecision` rows sharing the same (theme, sector): ≥2
`false_positive`/`not_useful`/`rejected` reviews reduce the *ranking-only*
`adjusted_confidence` by 15; ≥2 `useful`/`high_priority`/`approved`
reviews raise it by 5. The opportunity's own stored `confidence` field
(derived from the Evidence Gate) is never mutated — only the transient
`PrioritisationResult` used for ranking. Every adjustment is visible in
`PrioritisationResult.feedback_reasons`. This is explicitly NOT opaque ML
training — it is two `if` statements over real, inspectable prior rows.

### How resource/funding matching works, and its real limits (Phase 9-11)

`services/matcher.score_match`: type-compatibility (a fixed, conservative
map — a mismatched type never scores above 0), geography, timing/expiry
(a resource past its own `expiry_date` is HARD-EXCLUDED from new matches,
never merely penalised), capacity, evidence-backed confidence.

**A real false positive was caught and fixed during this PR's own live-data
testing**: `government_programme`/`grant`/`subsidy`/`capital`-type
resources are compatible with almost every need category by design (a
government programme can fund nearly anything), so type-compatibility
alone is too coarse for them. The fix (`PROMISCUOUS_RESOURCE_TYPES` in
`services/matcher.py`) requires the need's and resource's titles to share
at least one real keyword — excluding a further list of generic words
("new", "funding", "grant", "scheme", ...) that would otherwise create
spurious matches on category alone. This is documented, not hidden: see
"Bugs found via live data" below.

`FundingMatcher` (`services/funding_matcher.py`) never asserts `eligible`
— every match starts `potentially_relevant`/`eligibility_unknown`, and
`waqf`/`islamic_finance` funder types are structurally forced to
`requires_sharia_review` in `FundingMatch.save()` itself (cannot be
bypassed by calling the model directly). **No real funder/grant deadline
data exists in the current adapters** — "funding match approaching
deadline" notifications are not implemented because there is no real
deadline field being populated; implementing this honestly requires a
provider that actually publishes deadlines.

### Zero-capital strategy (Phase 11 spec numbering — repo's Phase 10)

`services/zero_capital_strategy.rank_actions_for_opportunity` only ranks
actions derived from REAL `ResourceMatch` rows — never invents a partner
or resource independent of a match.

### What is automated vs. what still requires human approval

**Automated (GREEN)**: signal fetch, normalisation, dedup, clustering,
evidence gate, lens activation, opportunity/need/resource-match creation,
prioritisation, notification creation. **Requires human approval
(YELLOW)**: `connect`/`match`/`alert` actions — see
`docs/GOOD_DEEDS_ENGINE.md`, unchanged from PR2/PR3. **Never automated
(RED)**: any capital movement, contract, or physical execution — this
repo has no execution layer at all (confirmed in the original Phase 0
audit and re-confirmed unchanged in PR4).

## Explicit non-claims (Phase 22)

- Discovery does not prove that an intervention is feasible or effective.
- An opportunity is not a guarantee of impact.
- A resource match is a candidate connection, not confirmation of
  availability or suitability.
- This system never determines Sharia compliance.
- "SCHEDULER READY" (this command runs correctly on demand, right now)
  is not "SCHEDULER ACTIVE" (a cron is actually ticking in production) —
  see `docs/GOOD_WHILE_YOU_SLEEP.md`.

## Bugs found via live data (kept here for transparency)

Real-world testing against the 3 live providers surfaced 3 real defects
that fixture-only testing in PR3 never could have caught — each is fixed
in this PR, with a regression test:

1. **Zero-activation opportunities**: the engine created a `GoodOpportunity`
   even when zero principle lenses activated for a signal. Fixed:
   `discovery_engine.py` now skips opportunity creation when
   `activations` is empty. This also exposed that
   `run_overnight_good_discovery_demo` (PR3) never seeded
   `GoodAgentDefinition` rows itself — fixed by adding that seed call.
2. **Resource-type misclassification**: real GOV.UK `funding_available`
   signals were silently defaulting to `resource_type='technology'`
   because `_resource_type_from_signal` only recognised the older PR3
   `'funding'` signal type, not PR4's `'funding_available'`. This
   coincidentally bypassed the (then-nonexistent) promiscuous-type check.
3. **Category-only false-positive matching**: a Californian earthquake
   scored as "matched" to an unrelated UK home-energy grant, and
   separately, a Papua New Guinea earthquake matched a UK flood-funding
   scheme purely on the shared generic word "new". Both fixed via the
   `PROMISCUOUS_RESOURCE_TYPES` keyword-relevance requirement above.

After all three fixes, a live run against all 3 real providers correctly
produces zero resource matches for any of the (genuinely unrelated)
earthquake signals — an honest "no verified match found" result, not a
forced one.
