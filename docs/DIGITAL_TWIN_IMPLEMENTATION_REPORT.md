# Industrial Digital Twin & Modernisation Engine — Implementation Report

Branch: `worktree-digital-twin-foundation` (isolated git worktree at
`.claude/worktrees/digital-twin-foundation`, branched fresh from `main`).
Related docs: [`docs/digital_twin_existing_system_audit.md`](digital_twin_existing_system_audit.md),
[`docs/adr/ADR-digital-twin-foundation.md`](adr/ADR-digital-twin-foundation.md).

## 1. What was built

A new Django app, `digital_twin`, implementing the first production-ready
vertical slice described in the task: a living baseline Digital Twin for an
industrial asset, deterministic loss detection, deterministic scenario
simulation, a draft/versioned Qur'anic Stewardship KPI engine, an Agent
Council review, human governance, promotion into the existing
capital-allocation workflow, and implementation-outcome tracking.

Every deterministic score in this app (baseline completeness/confidence/
freshness, scenario NPV/IRR/payback, stewardship KPI scores, guardrail
verdicts) is plain, explainable Python — there is no LLM call anywhere in
the calculation path. The Agent Council layer reuses the existing
`ai_agent_council`/`agent_runtime_model_router` schema and infrastructure
unmodified and, consistent with the rest of the repository's own honesty
convention (no live LLM execution runtime exists anywhere in this codebase
today), produces `is_simulated=True` council reviews from scripted
deterministic reasoning over real stored data.

## 2. Files created

**New Django app** (`digital_twin/`, 21 Python files, ~4,800 lines):
- `models.py` — 20 models across asset/twin/component/process/resource/
  metric/data-gap, loss detection, modernisation scenario, the 4-level
  stewardship governance hierarchy, human decision, and implementation
  tracking; plus `AssetType` and `Unit`/`UnitCategory` reference registries
  and the repo's first shared abstract base model (`TimeStampedModel`).
- `admin.py`, `urls.py`, `views.py`, `apps.py`, `tests.py`
- `migrations/0001_initial.py`, `0002_seed_reference_data.py` (AssetType +
  Unit/UnitCategory seed), `0003_seed_stewardship_kpis.py` (10 principles +
  KPIs, all draft/unapproved), `0004_alter_lossdetection_loss_type.py`
- `services/units.py`, `baseline.py`, `loss_detection.py`,
  `scenario_simulation.py`, `stewardship.py`, `guardrails.py`, `council.py`,
  `human_approval_gate.py`, `promotion.py`, `outcomes.py`
- `management/commands/seed_digital_twin_demo.py` — the Industrial Heat
  Modernisation Pilot demo fixture
- `templates/digital_twin/*.html` — 14 minimal screens (shared `_base.html`
  layout + 13 content templates)

**New Agent Council training packs** (`ai_agents/`, 7 new personas × 10
files each = 70 files): `digital_twin_agent/`, `engineering_agent/`,
`energy_resources_agent/`, `worker_safety_agent/`, `community_impact_agent/`,
`evidence_agent/`, `stewardship_agent/`.

**New docs**: `docs/digital_twin_existing_system_audit.md`,
`docs/adr/ADR-digital-twin-foundation.md`, this report.

## 3. Files changed (existing apps)

- `ecoiq/settings.py` — registered `'digital_twin'` in `INSTALLED_APPS`.
- `ecoiq/urls.py` — one `include()` line mounting `digital_twin.urls` at
  `/digital-twin/`.
- `ai_agent_council/agents.py` — appended 7 new entries to the existing
  `OPERATIONAL_AGENTS` list (numbers 18–24). No existing entry was changed,
  renamed, or removed.
- `waste_to_value_capital_allocation_engine/models.py` — additively
  extended `LOSS_TYPE_CHOICES` with 4 loss types the new detection rules
  needed (`avoidable_emissions`, `worker_safety_exposure`, `community_harm`,
  `missing_technology_adoption`) + its migration
  (`0003_alter_operationalloss_loss_type.py`). No existing choice value was
  renamed or removed, so no existing `OperationalLoss` row is affected.
- `ai_agent_council/tests.py`, `agent_runtime_model_router/tests.py` — two
  hardcoded repo-invariant tests (exact agent/file/registry counts) updated
  to reflect the registry's new, larger size. This is the one place the
  addition required touching existing test assertions, since those tests
  exist specifically to catch exactly this kind of change.

**No other existing file was modified.** No existing model, migration, URL,
or template was altered or removed.

## 4. Reused existing components (not duplicated)

- `league.Company` — the real company anchor for `IndustrialAsset.company`.
- `evidence_memory.EvidenceMemory` and its soft `source_reference` string
  convention — no new Evidence model.
- `waste_to_value_capital_allocation_engine.OperationalLoss` /
  `InterventionOption` / `InterventionScenario` (its existing base/upside/
  downside sensitivity model, reused verbatim rather than re-invented) /
  `CapitalAllocationDecision`, plus its `services/loss_intake.py`,
  `services/governance.py`, and `services/capital_allocation_scoring.py`.
- `ai_agent_council.CouncilRun` / `AgentTask` / `CouncilDecision` /
  `CouncilDisagreement` and its deterministic `services/confidence.py`
  (`build_confidence_breakdown`) and `services/disagreement.py`
  (`classify_conflict`) — no new schema.
- `agent_runtime_model_router.services.human_approval_gate` — extended
  (unioned), not forked, exactly like `waste_to_value_capital_allocation_engine`
  already does for its own action types.
- `gold_intelligence.services.project_finance` — `compute_npv`,
  `compute_irr`, `compute_payback_years` (pure functions over a
  `cash_flows` list) reused directly for scenario simulation instead of
  re-deriving NPV/IRR math.
- `capital_guardian.services.capital_decision_bridge`'s promotion pattern
  (score via the real scoring function, `verified_impact_score` deliberately
  left at governance.py's own default until real MRV data exists) — copied
  as the precedent for `digital_twin/services/promotion.py`.

## 5. Migrations

Run against this worktree's local SQLite dev database:
- `digital_twin`: `0001_initial`, `0002_seed_reference_data`,
  `0003_seed_stewardship_kpis`, `0004_alter_lossdetection_loss_type` — all
  applied cleanly.
- `waste_to_value_capital_allocation_engine`: `0003_alter_operationalloss_loss_type`
  — applied cleanly.
- `python manage.py makemigrations --check --dry-run` reports **no changes
  detected** against the final model state.
- Zero migrations touch any existing app's table schema (only additive
  `choices=` metadata changes on two `CharField`s, which SQLite/Postgres
  store as plain text columns regardless of the Python-level choices list).

## 6. Tests executed and results

- `python manage.py test digital_twin` — **60/60 passed.** Covers: model
  constraints (unique active+approved twin per asset, unique twin
  asset/version, unique process edge, honest variance recomputation, human
  decision → human_approved derivation), unit conversion (including
  cross-category rejection), the baseline engine (empty/complete/
  critical-gap cases, idempotent data-gap generation, never self-approving
  to `active`), loss detection (rule triggers, no false positives,
  detection idempotency, promotion approval-gating, promotion idempotency
  and self-healing, never-auto-approved), scenario simulation
  (downside/expected/upside ordering, every value exposing
  formula/inputs/assumptions/output/unit/confidence/missing_inputs,
  zero-CAPEX edge case, persisted `InterventionScenario` idempotency),
  stewardship (all seeded KPIs/principles/sources unapproved by default,
  one assessment per active KPI, harm-keyword blocking, missing-data
  warnings not fabricated scores, re-run idempotency), guardrails (clean
  pass, worker-harm block, undocumented-vs-detected severity distinction,
  missing-evidence escalation, hidden-pollution-transfer block), Agent
  Council integration (registry/training-pack completeness, one task per
  agent with a valid confidence/list-typed schema, simulated flag, a
  blocked scenario producing a rejected decision with real disagreement,
  re-run without duplicating the run), the human-approval gate (base
  8-action union still enforced, new 3 digital-twin actions enforced),
  promotion (approval-gating, real `CapitalAllocationDecision` creation,
  duplicate-prevention, audit-trail link preservation), outcome tracking
  (twin `last_observed_at` refresh, honest null variance for a placeholder
  outcome, `verified_impact_score` update from real measured accuracy),
  view permission boundaries (login-gated approve/promote, public read-only
  pages), and the full demo workflow end to end including its own
  idempotency.
- `python manage.py test digital_twin ai_agent_council ai_agent_workbench agent_runtime_model_router waste_to_value_capital_allocation_engine` — **323/323 passed**, confirming the two most directly touched existing apps and their nearest neighbours are unaffected.
- `python manage.py test` (the entire ~100-app platform test suite, 3,587
  tests) — **3,585 passed, 2 failed, 2 skipped.** The 2 failures
  (`good_agents.tests.GoodWhileYouSleepCommandTests.test_seeds_all_114_and_real_providers`,
  `good_agents.tests.IngestionOrchestrationTests.test_one_provider_failure_does_not_stop_others`)
  are in an app this implementation never touches (`git diff --stat
  80a4e25..HEAD -- good_agents/` is empty) and reproduce identically when
  run against `good_agents/tests.py` checked out at the pre-implementation
  base commit `80a4e25` — a pre-existing, stale-count assertion (test
  expects 3 `SignalProvider` rows, the seed command now configures 5),
  unrelated to and not introduced by this work. The 2 skips are
  environment-only (`CountryProfile` fixtures for the demo country pages,
  unrelated to `digital_twin`).
- Manual browser verification (Django dev server against the seeded demo
  data): asset list → asset detail → twin baseline → operational losses →
  scenarios → the strategic scenario's Agent Council page (confirmed a real
  10-agent disagreement and a `REJECTED` final decision) → confirmed the
  approve/promote views correctly redirect anonymous users to `/login/`.
  **This manual pass caught two real bugs** (see below) that the automated
  test suite, as originally written, had not covered — both are now fixed
  and covered by new regression tests.

### Bugs found and fixed during this implementation

1. `loss_detection._make_candidate`'s `get_or_create` lookup incorrectly
   included `status='candidate'`, so re-running detection after a candidate
   had been promoted created a duplicate row instead of finding the
   existing one — cascading into duplicate scenarios, council runs, and
   capital allocation decisions on every re-run of the demo command.
2. `guardrails.evaluate_guardrails` escalated to `requires_specialist_review`
   on *any* warning from the community-vulnerability KPI, including the
   generic "field not documented" case, not just an actual detected
   vulnerability-keyword signal.
3. `loss_detection.promote_loss_detection`'s idempotent short-circuit could
   leave `status='approved'` while `promoted_loss` was already set, if a
   caller re-set status after the first promotion — a self-contradictory
   state. Fixed to be self-healing.
4. The `scenario_council` view (and any future caller needing a scenario's
   council review) depended on a `HumanDecision` existing to find the
   `CouncilRun`, but a Council review happens *before* any human decision —
   a scenario can be reviewed and never chosen. Fixed by looking the run up
   directly via a shared, deterministic slug function.

## 7. Known limitations

- **No live LLM runtime.** Agent Council positions in this phase are
  produced by scripted, deterministic reasoning functions over real data,
  not a live language model call — consistent with the rest of the
  repository (`ai_agent_council`'s own models module states this is true
  platform-wide today). Wiring a live adapter through
  `agent_runtime_model_router.services.execution` for the new personas is a
  clearly scoped follow-on, not a design flaw requiring rework — the schema
  and gating are already in place.
- **Training packs are foundation-depth, not full-maturity.** The 7 new
  agent training packs (`ai_agents/<persona>/`) are complete (all 10
  required files, specific to their role) but thinner than the platform's
  most mature packs (e.g. `waste_leakage_agent`) — 2 test cases each rather
  than a large golden-case library.
- **Stewardship content is entirely unapproved by design.** All 10 seeded
  `SacredSourceReference`/`StewardshipPrinciple`/`StewardshipKPI` rows ship
  in draft/`source_needed`/`requires_scholarly_review` status. This is
  intentional per the task's explicit instruction, not a gap to silently
  "complete" — a real scholarly review process is a prerequisite for any of
  this content becoming authoritative, and is out of scope for engineering
  work.
- **UI is intentionally minimal.** The 14 templates are plain server-rendered
  HTML with no JavaScript interactivity (no live charts, no drag-and-drop
  process-graph editing) — sufficient to demonstrate and manually verify
  every required screen, not a polished production UI.
- **Loss-detection rules are a small starting set** (downtime, yield,
  idle-machinery-with-energy-use, and resource-flow loss quantity) — real
  deployments will need more asset-type-specific rules over time; the
  `AssetType`/`MetricDefinition` registries are designed to support that
  extension without further schema changes.
- **No PostGIS/real geospatial layer** — `latitude`/`longitude` are plain
  `FloatField`s, matching `geo_intelligence.GeoAsset`'s existing convention
  rather than introducing a new one.

## 8. Recommended next phase

1. Wire a live LLM adapter for the 7 new Council personas through the
   existing `agent_runtime_model_router` execution pipeline, using the
   deterministic reasoning functions in `services/council.py` as the
   ground-truth structured inputs an LLM would explain/synthesise around —
   never replace.
2. Expand the loss-detection rule library per asset type (mining, water,
   compressed air, cold-chain) using `industrial_playbook_library`'s
   existing taxonomy as the vocabulary source.
3. Commission a real scholarly review process for the seeded Stewardship
   Principles/KPIs and route the first batch through it, rather than
   engineering-authoring more draft content.
4. Add a real process-graph visual editor (drag-and-drop `ProcessNode`/
   `ProcessEdge` authoring) to the twin_process_map screen.
5. Extend `MeasuredOutcome` tracking into a scheduled reminder/workflow (via
   `notifications` or `backend_intelligence_engine`) so placeholder outcomes
   get a real measurement prompt at their expected review date, rather than
   relying on manual entry.
