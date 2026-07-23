# Good Agent Safety

## Red Team Review (Phase 9)

`good_agents.services.red_team.build_review` runs for every opportunity
before it can be marked `qualified` — deterministically, from data already
on the opportunity and its `AgentActivationRecord`s (no extra LLM call, so
it costs nothing extra to run on every opportunity). It answers: who
benefits, who bears the cost, who may be harmed, hidden externalities,
dependency risk, misleading-impact risk, greenwashing risk, conflict of
interest, contradicting evidence. `RedTeamReview.cleared` is `False`
whenever any lens raised a `concerns`/`conflicts` position or
`insufficient_evidence` is set — a "good" intention alone is not sufficient.

## Preserving disagreement (Phase 10)

`AgentActivationRecord.position` is one of `support` / `concerns` /
`conflicts` per lens, never averaged into one score. See
`good_agents.services.orchestrator.summarise_disagreement` and the Almaty
demo's own fixture, where the equitable-access lens raises a real
affordability concern that survives into the stored records and the
opportunity detail page, rather than being smoothed over.

## Specialist cross-cutting agents (Phase 18) — architecture only

Per the task spec, these are documented as named slots, **not implemented**:

| Specialist | One-line role | Status |
|---|---|---|
| WasteHunter | Finds operational waste signals across sectors | NOT_IMPLEMENTED |
| InvisibleHarmAgent | Surfaces harms not visible in headline metrics | NOT_IMPLEMENTED |
| OpportunityCostAgent | Compares current intervention to real alternatives | **IMPLEMENTED** — `good_agents.services.opportunity_cost` |
| FundingMatcher | Matches an opportunity to funding sources | NOT_IMPLEMENTED |
| ResourceMatcher | Matches unused resources to unmet needs | NOT_IMPLEMENTED |
| GrantFinder | Finds applicable grant programmes | NOT_IMPLEMENTED |
| PolicyOpportunityAgent | Surfaces policy-level intervention options | NOT_IMPLEMENTED |
| IdleAssetAgent | Finds idle/underused physical assets | NOT_IMPLEMENTED |
| CircularEconomyMatcher | Matches waste output to input demand elsewhere | NOT_IMPLEMENTED |
| EmergencyNeedsAgent | Flags time-critical unmet needs | NOT_IMPLEMENTED |
| AntiGreenwashingAgent | Checks claims against evidence for greenwashing | PARTIAL — folded into `RedTeamReview.greenwashing_risk` field, not a standalone agent |
| FairProcurementAgent | Checks procurement fairness | NOT_IMPLEMENTED |

Only `OpportunityCostAgent` (Phase 8, explicitly required for the first
demo) is actually implemented as working code. The rest have a named field/
row reserved (this table) so a future PR has a clear slot, per the task's
own instruction not to build all of these deeply now.

## Religious / ethical safety (Phase 23)

No fatwa, Sharia certification, or religious authority is claimed anywhere
in this app. `GoodAgentDefinition.arabic_name_review_status` defaults to
`needs_scholar_review` the moment an Arabic name is set, and no view or API
in `good_agents` surfaces `arabic_name` as verified. Any future
zakat/waqf/Islamic-finance-specific feature must be marked `REQUIRES
QUALIFIED SHARIA REVIEW` (matching the existing
`waste_to_value_capital_allocation_engine.services.human_approval_gate`'s
`islamic_finance_claim_publication` action type, reused rather than
duplicated).

## Security / autonomy (Phase 24)

- **Prompt injection in external evidence**: the orchestrator's Layer 1/2
  filters are pure deterministic keyword/domain matching over caller-
  supplied `Signal.text` — they do not execute instructions found inside
  evidence content, and the Layer 4 reasoning call only ever replays a
  hand-authored `fixture_output` in `simulated_demo` mode (never invents
  or executes based on scraped text).
- **Runaway API cost**: `agent_runtime_model_router.services.cost_policy.check_cost_policy`
  is checked before every Layer 4 call; `GoodDiscoveryRun.over_budget()`
  stops a run from processing further signals once its cost budget is
  exhausted (tested in `good_agents.tests.GoodDiscoveryRunTests.test_run_budget_exhaustion_stops_processing_further_signals`).
  No code path in this app issues more than one reasoning call per signal.
- **Duplicate opportunities / agent loops**: `GoodDiscoveryRun.idempotency_key`
  is unique; `AgentActivationRecord` has a `unique_together` on
  `(opportunity, agent)`; the demo command reuses an existing opportunity/
  loss/decision rather than duplicating on re-run (tested).
- **Consequential external action requires human approval**: enforced
  structurally by `GoodDeedAction.clean()` (YELLOW/RED cannot reach
  `completed` without `human_approved=True`; RED is unconditionally
  rejected) and by the unmodified existing
  `CapitalAllocationDecision.approval_status='pending'` default.

## Network security for real ingestion (PR4 Phase 21)

PR4 introduces the first outbound network calls this app makes. Threats
and mitigations, all in `good_agents/services/safe_http.py`:

- **SSRF**: every fetch validates scheme (`https` only), validates the
  hostname against the calling adapter's own fixed `allowed_hosts` set
  (never derived from user input — there is no code path from a user
  request to a fetched URL anywhere in this app), AND resolves the
  hostname and rejects private/loopback/link-local/multicast/reserved IP
  ranges before connecting. Tested:
  `good_agents.tests.SafeHttpSSRFTests`.
- **Redirect abuse**: redirects are followed manually, one hop at a time
  (`follow_redirects=False` on the underlying `httpx.Client`), with the
  SAME scheme/host/IP validation re-run on every hop's target, capped at
  `MAX_REDIRECTS=3`. A redirect to an unlisted host is blocked, not followed.
- **Oversized documents / decompression bombs**: `Content-Length` is
  checked before the body is read; the actual body size is checked again
  after; both against `MAX_RESPONSE_BYTES` (5 MB, matching
  `harvester.services.fetchers.MAX_RESPONSE_BYTES`'s existing precedent).
- **Provider timeout**: a bounded `httpx.Timeout` (5s connect / 15s read);
  a timeout is a normal, isolated provider failure
  (`ProviderFetchResult(success=False, ...)`), never an unhandled
  exception. **Verified live, not just in tests**: the UK Environment
  Agency provider genuinely timed out once during this PR's own
  development session, was correctly recorded as `status='failed'` with
  the real error message, and did not affect the other 2 providers or
  the overall run (see `docs/REAL_SIGNAL_INGESTION.md`).
- **Poisoned source content / HTML-script injection**: every provider
  parses a structured JSON API response, never HTML — there is no HTML
  parsing or script-execution path in `provider_adapters.py` at all. Raw
  text (`source_excerpt`, `summary`) is stored as plain Django model
  `TextField` values and rendered through Django's auto-escaping template
  layer wherever displayed — never marked `safe`, never rendered raw.
- **Duplicate replay**: unchanged from PR3 — `WorldSignal.dedup_key` +
  `source_url` prevents the same fetched item from creating a second row
  (see `services/signals.normalise_signal`).
- **No API keys in telemetry**: none of the 3 real providers require an
  API key (a deliberate selection criterion — see
  `docs/REAL_SIGNAL_INGESTION.md`); `AgentActivationRecord`/
  `PipelineStageExecution` metadata never includes request headers or
  credentials, only counts and durations.
- **No private source ingestion**: all 3 providers are public,
  no-authentication APIs; nothing in this PR reads from an
  authenticated/private source.
- **Prompt/response leakage**: unchanged from PR3 — the Layer 4 reasoning
  call's `simulated_demo` mode only ever replays a hand-authored
  `fixture_output`; no real provider text is ever piped into an LLM
  prompt in this PR (real `execution_mode='live'` reasoning is available
  per PR2/PR3's existing `agent_runtime_model_router` plumbing but not
  exercised by any command in this PR).

## Permissions (PR4)

`good_agents.views.good_map_api` and `.observatory_health_api` are
unauthenticated, matching the existing PR2/PR3 `opportunity_list`/
`opportunity_detail`/`morning_brief` views (none of this app's views are
staff-gated). This is a deliberate, unchanged choice: every field these
views expose is already non-sensitive and aggregate (region-level
geography, confidence/urgency scores, provider status) — no precise
location, no individual-level data, no credential, ever appears in any
`good_agents` response. If a future PR adds a field that IS sensitive,
that view must be gated with `@staff_member_required` at that time — this
is a live constraint on future work, not a closed decision.
