# ADR: Industrial Digital Twin & Modernisation Engine — Foundation Slice

- Status: Accepted
- Date: 2026-07-26
- Related: `docs/digital_twin_existing_system_audit.md`

## Context

EcoIQ needs a "living baseline Digital Twin" for industrial assets (factories,
mines, mineral deposits, processing plants, energy assets, infrastructure
projects, generic industrial assets) that: models present condition and
process/resource flows; detects missing data and operational losses;
generates and simulates modernisation scenarios; scores them against
technical/financial/environmental/human/Qur'anic-stewardship criteria;
convenes an explainable multi-agent council; requires human approval; and
promotes approved scenarios into capital allocation, with outcome tracking
afterward.

The existing-system audit (`docs/digital_twin_existing_system_audit.md`)
found no generic Digital Twin model anywhere in the repo. The closest
precedent, `capital_guardian`'s "Mining Digital Twin," is a single daily
snapshot table plus a hardcoded process-stage list in a view — narrow to
gold mining and not a persisted, generic graph. Meanwhile, a large amount of
adjacent, working infrastructure already exists and must be reused rather
than duplicated: `waste_to_value_capital_allocation_engine` (loss →
intervention → capital allocation, with governance and promotion already
built), `ai_agent_council` + `agent_runtime_model_router` (a real,
schema-validated, human-approval-gated multi-agent council), `evidence_memory`
(the canonical evidence store), `gold_intelligence.services.project_finance`
(NPV/IRR/payback math), and `ethics`/Tazkiyah-114 (governed,
versioned/reviewable content lifecycles).

## Decision

1. **New Django app `digital_twin`.** It owns exactly the models that do not
   exist anywhere else: `AssetType`, `Unit`/`UnitCategory`, `IndustrialAsset`,
   `DigitalTwin`, `TwinComponent`, `ProcessNode`, `ProcessEdge`,
   `ResourceFlow`, `MetricDefinition`, `OperationalMetric`, `TwinDataGap`,
   `LossDetection`, `ModernisationScenario`, `SacredSourceReference`,
   `StewardshipPrinciple`, `StewardshipKPI`, `StewardshipAssessment`,
   `HumanDecision`, `ImplementationAction`, `MeasuredOutcome`. It does **not**
   re-define `OperationalLoss`, `InterventionOption`, `InterventionScenario`,
   `CapitalAllocationDecision`, `CouncilRun`/`AgentTask`/`CouncilDecision`, or
   any Evidence model — it links to the real ones by hard FK (new app →
   existing app, the same direction `financial_intelligence_cloud` already
   uses against `waste_to_value_capital_allocation_engine`) or by the
   repo-wide soft `source_reference` string convention when a hard FK would
   create an unwanted migration dependency (e.g. into `gold_intelligence` or
   `geo_intelligence`, which the new app should not require).

2. **Loss lifecycle stays two-stage.** A `LossDetection` row (new, digital_twin)
   is the AI-computed, unapproved candidate — never auto-approved, per
   requirement. Only on explicit human approval does
   `digital_twin/services/loss_detection.py` call the existing
   `waste_to_value_capital_allocation_engine.services.loss_intake.create_operational_loss()`
   to create the **real** `OperationalLoss` row, which `LossDetection` then
   references by FK. This means a `ModernisationScenario` (which must extend
   `InterventionOption`, whose `operational_loss` FK is required/non-null)
   can only be built once a loss has been promoted — a stricter, not weaker,
   reading of "do not auto-approve inferred losses."

3. **`ModernisationScenario` is a thin OneToOne companion to
   `InterventionOption`**, adding only the twin-specific fields
   `InterventionOption` doesn't have (technology category, phases, energy/
   water/waste/emissions/worker/community impact, dependencies, regulatory
   requirements, twin/component/process FKs). The existing
   `InterventionType` choices (`do_nothing`, `operational_optimisation`,
   `equipment_upgrade`, ...) are reused directly for the spec's three
   required scenario types (no-change / low-cost / strategic) rather than
   inventing a parallel enum. Downside/expected/upside simulation reuses the
   existing `InterventionScenario` model (`scenario_type` +
   `assumptions`/`risk_flags` JSON) instead of a new one.

4. **Agent Council reuses the existing schema and execution pipeline
   unmodified.** New personas (Digital Twin, Engineering, Energy & Resources,
   Worker Safety, Community Impact, Evidence, Stewardship) are added as data
   entries to `ai_agent_council/agents.py::OPERATIONAL_AGENTS` with training
   packs under `ai_agents/`. Finance, Risk, and Capital Guardian roles reuse
   the existing Finance Modelling Agent, Governance Agent, and Capital
   Allocation Agent respectively rather than duplicating near-identical
   personas. A digital-twin council review is a normal `CouncilRun` with
   `task_category='digital_twin_scenario_review'` — no schema change to
   `ai_agent_council` or `agent_runtime_model_router`. Per repo convention
   (every existing Council seed is `is_simulated=True` — there is no live LLM
   runtime wired to real API traffic anywhere in the repo today), this
   phase's council reviews are deterministic/simulated, generated by a
   scripted reasoning function per persona rather than a live LLM call. This
   keeps the guarantee in the spec ("LLM may explain but must not modify
   deterministic calculations") trivially true in this phase, and live-model
   wiring becomes a follow-on task using the exact same adapters
   `agent_runtime_model_router` already has for other agents.

5. **Qur'anic Stewardship KPI Engine is new, governed, and ships in draft
   status.** `SacredSourceReference` and `StewardshipPrinciple` reuse the
   Tazkiyah-114 review-status lifecycle
   (`draft_reflection → ... → approved_for_public`) and `hikma.Evidence`'s
   `scholar_review_required` flag pattern. No verse text, translation, or
   interpretation is authored by this implementation; every seeded principle
   ships with `review_status='scholar_review_pending'`, a note explaining
   what is missing, and `is_approved_for_use=False`, so the KPI *formulas*
   (which are ordinary deterministic Python) can exist and be tested without
   ever presenting an LLM-generated religious claim as authoritative. The
   four governance levels (sacred source → interpretation → operational rule
   → numerical KPI) are four distinct model classes, never collapsed.

6. **No role/permission system is introduced.** Human approval follows the
   existing pure-function gate pattern
   (`agent_runtime_model_router.services.human_approval_gate`): a
   `human_approved` nullable boolean field, checked by a service-layer
   `require_human_approval()` call, extended (unioned) rather than forked.

7. **A new `AssetType` reference model** (code/display_name/description,
   admin-editable, FK'd from `IndustrialAsset`) is introduced as the first
   fully-wired instance of the extensible-choice-registry pattern the repo
   has only half-built elsewhere (`league.SectorRef`/`CountryRef` exist but
   aren't actually used as FK targets). Seeded with the 7 required categories
   plus a generic `other` row so new categories are a data change, not a
   code change.

8. **A new `Unit`/`UnitCategory` registry** is introduced — the repo has none
   today (units are baked into field names like `_kw`, `_pct`). Every
   `ResourceFlow`/`OperationalMetric` quantity carries an explicit `unit` FK,
   and conversion/compatibility checks live in `digital_twin/services/units.py`.

## Consequences

- Positive: zero migrations touch any existing app; every deterministic
  calculation is unit-tested and reuses either an existing formula
  (NPV/IRR/payback) or an explicit, documented new one (baseline
  confidence, stewardship scoring); the Agent Council gets richer without a
  second orchestration engine; capital allocation promotion reuses the
  exact idempotent `get_or_create` dedup the rest of the platform already
  relies on.
- Trade-off: because `ModernisationScenario` requires a promoted (real)
  `OperationalLoss`, a `LossDetection` candidate cannot be "played with" in
  scenario simulation before a human commits to treating it as a real loss.
  This is judged acceptable — and arguably the correct governance posture —
  given the explicit requirement that AI cannot commit capital or treat
  inferred data as ground truth.
- Trade-off: Council reviews in this phase are deterministic/simulated, not
  live-LLM. This matches the rest of the repo's current honesty convention
  (no app claims live LLM traffic it doesn't have) but means "AI must ...
  understand the current state" in this phase is implemented as deterministic
  rule-based reasoning over real data, not a live language model. Wiring a
  live adapter is a follow-on task, not a foundation-slice blocker.

## Rejected alternatives

- **Reuse `capital_guardian.OperationalSnapshot` as the twin's metric store.**
  Rejected: it is a single flat daily-snapshot row per mining project with
  ore/doré-specific fields; it cannot represent a generic component/process
  graph for a factory, heating plant, or infrastructure project without
  either abusing unrelated field names or making `digital_twin` depend on
  `capital_guardian`'s gold-specific schema.
- **Extend `gold_intelligence.GoldProject` into a generic `IndustrialAsset`.**
  Rejected: despite its commodity-agnostic docstring, its schema is
  fundamentally an investment/finance project (CAPEX, mine life, reserves),
  not a physical-asset/process record; conflating the two would make every
  future finance-only consumer of `GoldProject` carry twin-shaped baggage.
- **Add a GenericForeignKey-based evidence/audit model.** Rejected: no such
  pattern exists anywhere in the 100+ app repo; introducing the first one
  would be new, unreviewed infrastructure outside this task's scope. The
  soft `source_reference` string convention is used everywhere else and is
  used here too.
