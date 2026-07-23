# 114 Good Agents — Progress

## Phase 0 audit summary (full detail was reported to the user in-session)

24 areas audited across the repo before any code was written. Headline
findings that shaped every decision below:

| Area | Status | Consequence for this PR |
|---|---|---|
| 114 principles / Surah framework | DUPLICATED (3 non-cross-referenced, non-scholar-reviewed datasets) | Picked `core.esg_principles_data.PRINCIPLES` as canonical (confirmed with user); did not touch the other two. |
| Evidence | DUPLICATED (3 models: `harvester.Evidence`, `hikma.Evidence`, `league.Evidence`) | No 4th Evidence model added. |
| Evidence Memory | WORKING | Reused directly via `evidence_memory.services.memory`. |
| Observatory | MISSING | `GoodDiscoveryRun` is the unit of work; real continuous signal sourcing not built (see `docs/GOOD_WHILE_YOU_SLEEP.md`). |
| Operational Loss / Better Way / InterventionOption | WORKING (single-axis) | Reused unmodified via `capital_guardian.services.better_way` + `waste_to_value_capital_allocation_engine`. |
| Human Approval | WORKING but thin (admin-editable field) | Reused as-is; did not build a second approval UI. |
| Capital Guardian | WORKING (real eligible/conditional/blocked gate) | Reused unmodified. |
| Execution | DEAD END (no real execution layer exists) | `GoodDeedAction`'s RED class is structurally unreachable — see `docs/GOOD_DEEDS_ENGINE.md`. |
| MRV | DUPLICATED (`impact_mrv_layer` dead stub vs. real `VerifiedCapitalOutcome`) | Used the real one; did not touch `impact_mrv_layer`. |
| Global Opportunity Finder | MISSING | `GoodOpportunity` is new — see `docs/GOOD_OPPORTUNITY_MODEL.md`. |
| Agents / AI infrastructure | WORKING, non-duplicated (12-agent registry, router, cost policy, safety assertions, human-approval gate, LangGraph orchestration) | Reused wholesale — new agent registered as #13 "Good Agent Orchestrator", not a parallel stack. |
| Scheduler / background jobs | WORKING pattern (Celery, on-demand), no cron | Followed the same pattern; did not add `django-celery-beat`. |
| Command Centre | DUPLICATED (dead static app vs. real `capital_guardian.services.command_centre`) | Not touched either way — out of scope for this PR. |

Full 24-area detail with file:line citations was produced by 5 parallel
Explore-agent audits at the start of this session and shared with the user
directly in chat.

## What was built (this PR)

| Capability | Status |
|---|---|
| `GoodAgentDefinition` model + canonical-source decision | **DONE** |
| Seed command (6 of 114 principles) | **DONE** |
| `GoodAgentOrchestrator` (5-layer, cost-controlled) | **DONE** — Layers 1-3 fully deterministic; Layer 4 real (SimulatedDemoAdapter in demo/tests, real adapter available for `execution_mode='live'`); Layer 5 delegated to existing gates |
| `GoodOpportunity` model (estimated/target/measured/verified discipline) | **DONE** |
| `AgentActivationRecord` (disagreement preserved) | **DONE** |
| `GoodDeedsEngine` + autonomy classes (GREEN/YELLOW/RED) | **DONE** — RED structurally blocked |
| `OpportunityCostAssessment` | **DONE** — reuses real Better Way ranking |
| `RedTeamReview` | **DONE** |
| Resource matching network | **PARTIAL** — zero-capital fields only; no `Resource` model/matcher (see `docs/RESOURCE_MATCHING_NETWORK.md`) |
| Zero-capital good | **DONE** |
| Better Way integration | **DONE** (reused unmodified) |
| Opportunity Cost integration | **DONE** |
| Capital Guardian integration | **DONE** (reused unmodified) |
| Human approval integration | **DONE** (reused existing admin-gated field) |
| MRV / ImpactReceipt integration | **DONE** — MRV *plan* path used by the demo; fully-wired *verified-outcome* path exists and is tested but not demo-invoked (no real after-data exists yet) |
| `GoodDiscoveryRun` (Good While You Sleep foundation) | **PARTIAL** — bounded/resumable/idempotent/cost-budgeted run exists; real continuous signal sourcing and production Celery-beat scheduling are **TODO/BLOCKED** (see `docs/GOOD_WHILE_YOU_SLEEP.md`) |
| Morning Brief | **DONE** — real view over stored run/opportunity data |
| Cost controls | **DONE** — `cost_policy` reuse, per-run budget, early stop, one call per signal (never per lens) |
| Safety controls | **DONE** — red team, autonomy boundaries, evidence honesty, religious-authority guard |
| Global Good Taxonomy | **DONE** — `GOOD_TAXONOMY_CHOICES` |
| Specialist cross-cutting agents (Phase 18) | **PARTIAL** — only `OpportunityCostAgent` implemented; rest are named stubs (`docs/GOOD_AGENT_SAFETY.md`) |
| Global Good Map data readiness | **PARTIAL** — model fields ready; no `/good/map` UI (explicitly secondary per spec) |
| Agent observability | **DONE** — `AgentActivationRecord` + `GoodDiscoveryRun` fields |
| Evidence trust model | **DONE** — `insufficient_evidence` as a valid, honest conclusion |
| First end-to-end demonstration | **DONE** — `python manage.py run_almaty_good_agent_demo`, idempotent, tested |
| SEO/distribution connection | **NOT STARTED** — explicitly out of scope per spec ("do NOT automate publishing yet") |
| Dogfood EcoIQ-on-EcoIQ | **NOT STARTED** — not attempted this PR |

## Tests / build

- 36 new tests in `good_agents/tests.py`, all passing, covering: principle
  mapping, agent activation (and non-activation), deduplication/
  idempotency, evidence confidence/insufficiency, disagreement
  preservation, zero-capital classification, autonomy boundaries (incl. RED
  rejection), red-team clearance, run budget exhaustion, run/opportunity/
  action idempotency, Better Way/Opportunity Cost/Capital Decision/MRV/
  ImpactReceipt/Evidence Memory integration, and all 3 views.
- Full existing Django test suite run to check for regressions — see the
  final chat report for the result.
- `python manage.py check` clean (0 issues).
- 1 migration (`good_agents/migrations/0001_initial.py`), additive only —
  no existing table altered.

## Explicitly not done in PR2 (superseded/updated by PR3 below where noted)

- ~~All 114 principles do not have `GoodAgentDefinition` rows — only 6.~~ **Fixed in PR3** — all 114 now have rows (6 hand-tuned + 108 auto-generated, `requires_human_review=True`).
- No real-world signal ingestion — signals are caller-supplied. **Still true in PR3** — see below.
- No production Celery-beat schedule. **Still true in PR3.**
- ~~No `Resource`/`ResourceMatcher` model.~~ **Fixed in PR3** — `Need`, `AvailableResource`, `ResourceMatch`, `NeedResourceMatcher`, `CircularEconomyMatcher` all real and tested.
- No public-facing `/good/map`. **Still true in PR3** — a read-only JSON API exists (`good_agents.views.good_map_api`), no map UI.
- ~~No specialist agents beyond `OpportunityCostAgent`.~~ **Partially addressed in PR3** — `FundingMatcher` now real (conservative); `CircularEconomyMatcher` now real; the rest remain named stubs.

---

## PR3 — Global Good Discovery + Good While You Sleep + Need/Resource Matching

### PR3 Phase 0 verification (traced actual code, not docs)

Re-confirmed every PR2 component's status by direct code inspection before
writing PR3 code (not re-trusting PR2's own documentation blindly): all
matched exactly what PR2's docs claimed — no drift. `good_agents` test
suite (36 tests) was green before any PR3 code was written.

### What PR3 built

| Capability | Status |
|---|---|
| `SignalProvider` (Phase 1) | **DONE** as architecture — real model, `is_stale()`/`mark_refreshed()`/`mark_failed()` logic tested; **no live fetch implementation** (by design — see `docs/GLOBAL_GOOD_DISCOVERY.md`) |
| `WorldSignal` normalisation (Phase 2) | **DONE** — dedup_key, freshness decay, fact/claim/inference classification (fact requires explicit high-trust provider), tested |
| Signal deduplication + clustering (Phase 3) | **DONE** — exact dedup_key folding + keyword-overlap clustering, deterministic, tested |
| `GlobalGoodDiscoveryEngine` (Phase 1, 4) | **DONE** — `services/discovery_engine.py`, staged/checkpointed, reuses PR2's orchestrator/pipeline unchanged |
| Evidence Gate (Phase 5) | **DONE** — qualify/reject/monitor/insufficient_evidence, deterministic thresholds, tested |
| `Need` model (Phase 6) | **DONE** |
| `AvailableResource` model (Phase 7) | **DONE** — `availability='available'` blocked without evidence, enforced not just documented |
| `NeedResourceMatcher` (Phase 8) | **DONE** — deterministic type/geography/expiry/evidence scoring; expired resources hard-excluded (bug caught and fixed during this PR's own development) |
| `CircularEconomyMatcher` (Phase 9) | **DONE** as a real specialisation, feasibility/logistics/regulatory/environmental framing always honest about what's unverified |
| `ZeroCapitalStrategy` (Phase 10) | **DONE** — ranks real matched resources, never invents an action independent of a match |
| `FundingMatcher` (Phase 11) | **DONE** as conservative architecture — no real funder database exists, so nothing is ever asserted `eligible`; Sharia-sensitive types structurally forced to `requires_sharia_review` |
| `GoodMission` (Phase 12) | **DONE** |
| Staged/resumable `GoodDiscoveryRun` (Phase 13) | **DONE** — 12 stages checkpointed, resumable, tested |
| Hard cost controls (Phase 14) | **DONE** — same per-signal budget check as PR2; `max_activated` still caps lens activation even with all 114 seeded (tested explicitly) |
| `PrioritisationEngine` (Phase 15) | **DONE** — multidimensional labels (URGENT/HIGH_LEVERAGE/ZERO_CAPITAL/EVIDENCE_GAP/MONITOR/CAPITAL_REQUIRED), never a fake single score |
| `MorningImpactBrief` v2 (Phase 16) | **DONE** — extends PR2's view, all real stored data |
| Top 3 Actions / `AttentionPriority` (Phase 17-18) | **DONE** |
| Safe autonomy (Phase 19) | **UNCHANGED from PR2** — same GREEN/YELLOW/RED enforcement |
| Outreach preparation (Phase 20) | **PARTIAL** — GoodDeedAction's `connect`/`prepare_*` action types already existed in PR2; no new draft-generation logic added in PR3 |
| Global Good Map data layer (Phase 21) | **DONE** (API only) — `good_agents.views.good_map_api`, filters by theme/status/zero-capital/confidence; no map UI (explicitly secondary) |
| 114 agent activity + status (Phase 22) | **DONE** — `activation_status`, `last_activated_at`, `current_opportunities_count`, `verified_impact_links_count`, all real/computed, not decorative |
| Scale to all 114 (Phase 23) | **DONE** — `seed_all_good_agent_definitions`, 108 auto-generated rows marked `requires_human_review=True`, hand-tuned 6 untouched |
| Agent groups (Phase 24) | **DONE** — `services/agent_groups.py`, 8 operational clusters over the canonical `category` field, never replaces the 114 numbering |
| Cross-border discovery (Phase 25) | **PARTIAL** — `CrossBorderAssessment` model exists (real fields); no automated transferability scoring (would need real comparative data this repo doesn't have) |
| Global comparison (Phase 26) | **NOT STARTED** — no new integration written this PR; PR2's audit already found `countries`/`league` scoring is real-formula-but-static-seed-data, unchanged |
| Anti-duplication (Phase 27) | **DONE** — `dedup_key` on `WorldSignal`/`Need`/`AvailableResource`, tested |
| Temporal memory (Phase 28) | **DONE** — `ResourceStatusChange` append-only log; expired resources hard-excluded from new matches |
| Feedback from human decisions (Phase 29) | **DONE** (model only) — `HumanReviewDecision`; not yet wired into `PrioritisationEngine`'s weighting (a future-PR learning loop) |
| False-positive control (Phase 30) | **DONE** — `rejected_opportunities`/`duplicates_removed`/`insufficient_evidence_count` tracked per run |
| Observatory health (Phase 31) | **DONE** (API only) — `good_agents.views.observatory_health_api` |
| Trust UI (Phase 32) | **PARTIAL** — the opportunity detail page (PR2) already shows evidence/activations/red-team/actions; not extended with explicit "why found/what is unknown" copy sections in PR3 |
| First overnight demo (Phase 33) | **DONE** — `run_overnight_good_discovery_demo`: 4 signals in, 1 opportunity + 2 resources out, 1 noise signal correctly rejected, idempotent, tested |
| Dogfood mission (Phase 34) | **DONE** (config only) — `seed_dogfood_mission` creates the mission row, disabled, run against no fabricated signals (see command docstring for why) |
| SEO/public knowledge pipeline (Phase 35) | **NOT STARTED** — explicitly out of scope per spec |
| Notifications (Phase 36) | **NOT STARTED** — PR2's audit found `notifications.AdminNotification` already real/working; PR3 did not wire GoodOpportunity events into it (a small, safe follow-up) |

### Tests / build (PR3)

- 57 new tests appended to `good_agents/tests.py` (93 total in the app now),
  covering every item in the Phase 38 checklist: signal normalisation,
  duplicate detection, clustering, noise rejection, evidence gate
  (all 4 decisions), Need/Resource creation + idempotency, resource
  eligibility enforcement, resource matching (incl. type-incompatibility
  and expiry hard-exclusion), circular matching, zero-capital strategy,
  funding matching (incl. Sharia-sensitive routing), run cost limits, run
  idempotency, checkpoint resume, scale-to-114 activation cap, Morning
  Brief v2, Top 3 Actions, prioritisation labels, and both new API views.
- Full repo suite: **2399 tests, OK (2 pre-existing skips, unrelated)** —
  up from 2342 in PR2, zero regressions.
- 1 new migration (`good_agents/migrations/0002_goodmission_signalcluster_signalprovider_and_more.py`),
  additive only.
- No Python lint/typecheck tooling exists in this repo (confirmed again).

### Known gaps (do not assume otherwise)

- No real signal ingestion — every signal in every demo is a labelled
  fixture; `SignalProvider` has no live fetch implementation.
- No real `AvailableResource`/funder data source — every resource in this
  repo today is test data or demo fixtures.
- No automated cross-border transferability scoring, no real circular-
  economy distance/regulatory data, no global-comparison integration this
  PR.
- `HumanReviewDecision` feedback is captured but not yet fed back into
  `PrioritisationEngine`'s weighting.
- Notifications not wired to Good Opportunity events yet.
- No production Celery-beat scheduling (same blocker as PR2 — the Celery
  worker itself is commented out in `render.yaml`).

### Recommended next PR

Pick one: (a) wire `HumanReviewDecision` outcomes back into
`PrioritisationEngine` as a real (if simple) learning signal, or (b) wire
urgent/zero-capital `GoodOpportunity` events into the existing
`notifications.AdminNotification` model (already real and working — a
small, safe, additive follow-up). Both are scoped and don't touch anything
built in PR2 or PR3.
