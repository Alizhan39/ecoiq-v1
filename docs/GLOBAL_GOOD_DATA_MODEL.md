# Global Good Data Model

All models added in PR3 (`good_agents/models.py`), additive-only — no PR2
model was renamed, altered destructively, or duplicated.

| Model | Purpose | Key honesty guarantee |
|---|---|---|
| `GoodMission` | Standing discovery config (Phase 12) | `schedule` is descriptive text, not an enforced cadence — see `docs/GOOD_WHILE_YOU_SLEEP.md` |
| `SignalProvider` | Provider/adaptor registry (Phase 1) | `fetch_method` is a description, not code — no network call originates here |
| `WorldSignal` | Canonical normalised signal (Phase 2) | `content_classification` defaults to `claim`/`inference`; `fact` requires an explicit high-trust provider |
| `SignalCluster` | Groups related signals (Phase 3) | `confidence_boost` only grows with real corroboration count, never asserted |
| `Need` | Demand side (Phase 6) | `affected_group` is short free text, never named individuals |
| `AvailableResource` | Supply side (Phase 7) | `availability='available'` blocked without `evidence_refs` (enforced in code) |
| `ResourceStatusChange` | Temporal memory (Phase 28) | Append-only; only path to changing a resource's status |
| `ResourceMatch` | NeedResourceMatcher/CircularEconomyMatcher output (Phase 8-9) | `missing_evidence` always populated when relevant |
| `FundingMatch` | FundingMatcher output (Phase 11) | `waqf`/`islamic_finance` structurally forced to `requires_sharia_review` |
| `ZeroCapitalStrategyAction` | Ranked zero-capital actions (Phase 10) | Always derived from a real `ResourceMatch`, never invented independently |
| `HumanReviewDecision` | Feedback loop (Phase 29) | Append-only, rationale captured, never silently overwritten |
| `CrossBorderAssessment` | Cross-border architecture (Phase 25) | Populated by a human/analyst — no automated transferability scoring exists |

Extended (not renamed) from PR2:

- `GoodAgentDefinition` +`definition_quality`, `requires_human_review`,
  `activation_status`, `last_activated_at` — supports scaling from 6 to 114
  rows without losing the distinction between hand-tuned and auto-generated.
- `GoodDiscoveryRun` +`mission_config` (FK to `GoodMission`), `current_stage`,
  `stage_checkpoints`, `rejected_opportunities`, `duplicates_removed`,
  `insufficient_evidence_count` — the existing `mission` CharField and all
  PR2 fields/behaviour are untouched; `run_almaty_good_agent_demo` still
  works unchanged.

## Privacy by design (Phase 19, unchanged discipline from PR2)

Every geography field across every PR3 model is region-level
(`countries.CountryProfile` FK + free-text region) — never a precise
address or coordinate. `Need.affected_group` and
`GoodOpportunity.affected_population` are both short descriptive text,
never a list of named individuals. `/good-agents/api/map/`
(`good_agents.views.good_map_api`) exposes exactly these region-level
fields and nothing more.

## Migrations

One migration this PR: `good_agents/migrations/0002_goodmission_signalcluster_signalprovider_and_more.py`
— entirely additive (new tables + new nullable/defaulted columns on
existing tables). No existing column was dropped, renamed, or had its type
changed.
