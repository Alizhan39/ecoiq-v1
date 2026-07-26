# Digital Twin Foundation — Existing System Audit

Date: 2026-07-26
Scope: pre-implementation audit for the Industrial Digital Twin & Modernisation
Engine vertical slice. Read-only investigation of the EcoIQ Django monolith
(`/Users/work.tazabekovgmail.com/ecoiq-v1`), performed before any new code was
written, per the operating rules for this task.

## 0. Headline finding

**No generic Digital Twin exists anywhere in this repository.** Every "Digital
Twin" reference outside `capital_guardian` is aspirational copy on a
marketing/vision page (`asset_passport`, `impact_mrv_layer`,
`industrial_playbook_library`, `microsoft_core_stack`, and ~15 similar apps)
describing a *future* Azure Digital Twins integration — none of them has a
`models.py`. The one real implementation, `capital_guardian`'s "Mining Digital
Twin," is a single `OperationalSnapshot` table (daily ore/throughput/recovery
readings) plus a **hardcoded Python list of process stages inside a view
function** (`capital_guardian/views.py`) — narrowly gold/mining-shaped, not a
persisted, generic, cross-asset-type component/process graph. This is
therefore a genuinely new build, not a refactor of something that already
works — but it must sit on top of a large amount of real, working
infrastructure (evidence, loss detection, capital allocation, agent council,
governance gates) that already exists and must not be duplicated.

## A. Reusable existing components

| Concern | Existing component | File(s) | Reuse strategy |
|---|---|---|---|
| Real "company" anchor | `league.Company` (rated entity) + `companies.CompanyProfile` (1:1 intelligence extension) | `league/models.py:69-227`, `companies/models.py:111-253` | `IndustrialAsset.company` FK → `league.Company` (nullable — some assets, e.g. exploration deposits, may not yet be an EcoIQ-rated company) |
| Mining/finance project root | `gold_intelligence.GoldProject` — explicitly designed to be commodity-agnostic (`COMMODITY_CHOICES` includes copper/infrastructure/energy/agriculture/other, docstring lines 43-49) | `gold_intelligence/models.py:29` | Soft `source_reference` string (e.g. `"gold_intelligence.GoldProject:<slug>"`) on `IndustrialAsset`, not a hard FK — keeps `digital_twin` independent of the mining vertical |
| Location | `geo_intelligence.GeoAsset` — plain lat/long FloatFields, `asset_type` choices, `source_reference` soft pointer convention | `geo_intelligence/models.py:25` | Copy the plain-FloatField lat/long pattern directly; optionally link via `source_reference` rather than FK |
| Evidence (canonical) | `evidence_memory.EvidenceMemory` — text chunk, `confidence` (nullable, "never fabricated"), `verification_status`, `review_tier`, `document_category`, `source_reference` soft pointer, SHA-256 `integrity_reference` | `evidence_memory/models.py:50-169` | All digital_twin evidence links use `source_reference = "digital_twin.<Model>:<pk>"`, written into `EvidenceMemory` rows. No new Evidence model. |
| Evidence (SAY/DO/SHOW, scholarly) | `hikma.Evidence` — `scholar_review_required` (default `True`), `confidence_tier` | `hikma/models.py:15-72` | Pattern to imitate for stewardship-KPI evidence: never assert a tier stronger than the source allows |
| Operational loss | `waste_to_value_capital_allocation_engine.OperationalLoss` — 20 loss types, `evidence_quality`, `confidence`, readiness triad, text (not FK) `asset`/`project`/`organisation` fields | `waste_to_value_capital_allocation_engine/models.py:196-241` | Digital Twin never re-implements this. A twin-side `LossDetection` record (candidate, unapproved) is promoted into a **real** `OperationalLoss` row via the existing `services/loss_intake.create_operational_loss()` on human approval. Precedent for a hard FK from a *new* app into this exact model: `financial_intelligence_cloud.PortfolioEntity.source_operational_loss` (models.py:198-202). |
| Intervention / scenario | `InterventionOption` (FK→OperationalLoss, CAPEX/OPEX/payback/readiness/status) + `InterventionScenario` (already has `scenario_type` base/upside/downside, `assumptions`/`risk_flags` JSON!) + `FundingGap` + `CapitalRouteMatch` | `waste_to_value_capital_allocation_engine/models.py:268-372` | `InterventionScenario` **already implements the downside/expected/upside structure** the spec asks for — reuse it verbatim rather than inventing a parallel one. `ModernisationScenario` (new, digital_twin) is a thin OneToOne companion adding only twin-specific fields (technology category, energy/water/waste/emissions impact, worker/community impact, dependencies, phases) that don't exist upstream. `INTERVENTION_TYPE_CHOICES` already contains `do_nothing` / `operational_optimisation` / `equipment_upgrade` — maps directly onto the spec's 3 required scenario types (no-change / low-cost / strategic). |
| Capital allocation decision + promotion | `CapitalAllocationDecision` (FK→InterventionOption, FK→CouncilRun, `approval_status`, `conditions` JSON) + `services/governance.create_governed_investment_case()` (idempotent `get_or_create(intervention=, council_case=)`) + `services/capital_guardian_handoff.promote_to_capital_guardian()` (approval-status gate, ambiguous-match refusal, `IntegrityError`→`already_promoted`) | `waste_to_value_capital_allocation_engine/models.py:375-404`, `services/governance.py`, `services/capital_guardian_handoff.py` | Digital Twin promotion reuses `create_governed_investment_case()` directly — no new CapitalAllocationDecision-equivalent model, no new dedup logic |
| Dry-run / preview pattern | `promote_confirm` (GET, read-only) / `promote_execute` (POST, re-validates from DB) view split | `waste_to_value_capital_allocation_engine/views.py:166-256` | Copy this exact split for the twin's scenario→promotion flow |
| Deterministic risk flags | `capital_guardian.RedFlag` + `RedFlagRuleConfig` (threshold resolution: project override → platform default → hardcoded fallback) + `services/red_flag_engine.py` (12 idempotent pure-Python rules) | `capital_guardian/models.py:184-278`, `services/red_flag_engine.py` | Pattern to imitate for stewardship **guardrail rules** (pass / warning / block), not literally reused (different domain) |
| NPV / IRR / payback | `gold_intelligence/services/project_finance.py` — pure-Python Newton's-method IRR, discounted-cashflow NPV, interpolated payback, ±20% tornado sensitivity, all return `{'available': False, 'reason': ...}` rather than fabricating | `gold_intelligence/services/project_finance.py` | `digital_twin/services/scenario_simulation.py` imports and reuses these functions directly instead of re-deriving NPV/IRR math |
| Agent Council schema + persistence | `ai_agent_council.CouncilRun` / `AgentTask` / `CouncilDecision` / `CouncilDisagreement` + deterministic `services/disagreement.py`, `services/confidence.py`, `services/routing.py` | `ai_agent_council/models.py`, `ai_agent_council/services/*` | Digital Twin council review = a `CouncilRun` with `task_category='digital_twin_scenario_review'`; **no new schema**. New agent personas are added to `ai_agent_council/agents.py::OPERATIONAL_AGENTS`. |
| Agent execution / LLM routing / safety | `agent_runtime_model_router` — provider adapters, `schema_validation.py` (`REQUIRED_FIELDS = ['confidence','human_approval_required','status']`), `confidence_calibration.py` (LLM's own confidence is *never* trusted — recomputed from structural signals), `safety_assertions.py` (regex-based, no LLM judge) | `agent_runtime_model_router/services/*` | Reuse `execute_agent()` / `submit_agent_position_to_council()` as-is |
| Human-approval gate | `agent_runtime_model_router/services/human_approval_gate.py` — `ACTIONS_REQUIRING_APPROVAL` frozenset + `require_human_approval(action_type, obj)`, duck-typed on `.human_approved`. Already extended per-app (see `waste_to_value_capital_allocation_engine/services/human_approval_gate.py`) | same | `digital_twin/services/human_approval_gate.py` imports the base set and unions in `{'digital_twin_scenario_promotion', 'digital_twin_baseline_approval'}` — extend, don't fork |
| KPI definition/instance split | `ethics.FormulaDefinition` (catalog: formula, weight, `is_public`) + `ethics.FormulaScore` (instance: raw/normalized/confidence/analyst override) | `ethics/models.py:78-136, 268-322` | Pattern to imitate (not reuse directly — different domain) for `StewardshipKPI` (definition) / `StewardshipAssessment` (instance) |
| Draft→approved governance lifecycle for religious/interpretive content | Tazkiyah 114 `ReviewStatus` enum: `draft_reflection → source_needed → translation_pending → tafsir_pending → scholar_review_pending → wellbeing_review_required → approved_for_preview → approved_for_public → archived`, version bump on any substantive edit | `docs/tazkiyah-114-content-schema.md:153-188`, `content/tazkiyah114/*.json` | `StewardshipPrinciple`/`SacredSourceReference` reuse this exact lifecycle naming and the rule "any edit to source/translation/wording reopens review" |
| Deterministic confidence/completeness formula template | `ethics/scoring.py::compute_data_confidence()` — additive, capped, point-based, zero LLM involvement | `ethics/scoring.py:469-510` | Direct template for `digital_twin/services/baseline.py` |
| Test conventions | Plain `django.test.TestCase`, no pytest/no factory_boy anywhere in the repo. Two houses style: (1) module-level `_make_x()` helpers (`core/tests.py`), (2) service-layer-only integration tests importing straight from `services/*` (`waste_to_value_capital_allocation_engine/tests.py`) | repo-wide | Follow style (2) — most of the new logic is deterministic services, test those directly |
| DRF conventions | `api/authentication.py::APIKeyAuthentication`, `api/permissions.py`, plain `ListAPIView`/`RetrieveAPIView`/`APIView`, no ViewSets, manual `/api/v1/` URL prefix (no DRF versioning class) | `api/*` | New endpoints follow the same generic-view + manual-prefix style, mounted at `/digital-twin/api/` |

## B. Gaps (things the spec needs that genuinely do not exist)

1. **No generic `IndustrialAsset`/`DigitalTwin`/component/process model** anywhere — confirmed by direct grep (`class.*Twin` returns zero matches) and by the asset/twin-adjacent-apps audit.
2. **No `Organisation` model** — the spec's hierarchy names "Organisation" as the root, but no such model exists in this codebase. `league.Company` is the real anchor. The new hierarchy uses `Company` in its place.
3. **No unit-of-measurement / quantity model** — units are baked into field names (`_kw`, `_pct`, `_usd`, `_m3_per_hour`) everywhere. `digital_twin` is the first app in the repo to need a real `Unit`/`UnitCategory` registry for safe quantity arithmetic.
4. **No extensible-choice-registry pattern actually wired as a FK.** `league.SectorRef`/`CountryRef` exist as standalone lookup models but `Company.sector`/`.country` remain hardcoded `CharField(choices=...)` — the registry is half-built and unused as a real constraint anywhere. `digital_twin.AssetType` will be the first fully-wired version of this pattern (real FK, admin-editable, seeded with the 7 required categories + free-text `other`).
5. **No shared abstract base model** (`TimeStampedModel`, evidence mixin) exists in the repo at all — every model hand-declares `created_at`/`updated_at`. `digital_twin` introduces the first one, called out explicitly as new shared infrastructure other apps could later adopt, not "the existing pattern."
6. **No role/permission system** (no custom `Role` model, no Django Groups in active use, no `core/permissions.py`). "Founder review"/"human approval" is implemented as a pure function (`human_approval_gate.require_human_approval`) reading a duck-typed `.human_approved` boolean field, enforced from the service layer, not a role check. `digital_twin` follows this exact pattern rather than inventing roles.
7. **No Qur'anic/stewardship KPI governance model.** Tazkiyah 114 is reflective/devotional content (surah themes, life pathways) — a different concept from an *operational stewardship KPI* tied to a modernisation scenario. `SacredSourceReference` / `StewardshipPrinciple` / `StewardshipKPI` / `StewardshipAssessment` are genuinely new models, but must reuse Tazkiyah 114's review-status lifecycle and `hikma.Evidence.scholar_review_required` pattern rather than inventing a third governance vocabulary.
8. **No "dry run" concept anywhere** (`grep -rniE "dry.?run"` = zero hits). The `promote_confirm`/`promote_execute` GET/POST split is the closest existing analogue and is reused as the pattern.
9. **No generic audit-trail model.** The `audit` Django app is an unrelated domain (facility efficiency audits: `AuditSession`, `Finding`, `ActionPlan`). `capital_guardian.AuditLogEntry` (FK-scoped to `GoldProject`, not generic) and `legacy_safe.AuditLog` are the two existing patterns to imitate for `HumanDecision`'s audit trail — no GenericForeignKey exists anywhere in the repo, confirmed by grep, so `digital_twin` follows the same soft-`source_reference`-string convention rather than introducing the first GFK.

## C. Conflicts / duplication risks

- **`capital_guardian`'s "Mining Digital Twin" naming collision.** Its URL is literally `/capital-guardian/<slug>/digital-twin/`. The new app is mounted at a different path (`/digital-twin/`) and is explicitly framed in its own docs/UI as the *cross-asset-type, generic* Digital Twin — `capital_guardian`'s page is left untouched and unrenamed (out of scope, and renaming it risks breaking existing links/tests). A cross-link ("see also: Mining Digital Twin for gold projects") is added to the new app's docs only.
- **Two "Evidence" models** (`evidence_memory.EvidenceMemory`, `hikma.Evidence`) already coexist by design (per `evidence_memory`'s own docstring) — `digital_twin` adds no third; it writes into `EvidenceMemory` only, matching every other new app in the repo.
- **`InterventionOption.operational_loss` is a required (non-null) FK.** This means a `ModernisationScenario` cannot be created before its parent loss exists as a *real* `waste_to_value_capital_allocation_engine.OperationalLoss` row — i.e., the twin-side `LossDetection` candidate must be human-approved and promoted into a real `OperationalLoss` **before** scenario generation, not after. This slightly reorders spec step 3→4 in implementation (candidate detection → approval-to-quantify → real loss row → scenario generation) but preserves the spirit ("do not auto-approve inferred losses") more strictly than the spec's literal ordering.
- **Migration direction.** All new hard FKs point from `digital_twin` *into* existing apps (`league.Company`, `waste_to_value_capital_allocation_engine.OperationalLoss/InterventionOption`, `ai_agent_council.CouncilRun`) — never the reverse — so no existing app's migration history changes, and `digital_twin` can be removed cleanly if needed. This mirrors the existing `financial_intelligence_cloud → waste_to_value_capital_allocation_engine` precedent.

## D. Proposed integration points

1. `INSTALLED_APPS` in `ecoiq/settings.py`: add `'digital_twin'`.
2. `ecoiq/urls.py`: add `path('digital-twin/', include('digital_twin.urls', namespace='digital_twin'))`.
3. `digital_twin/services/loss_detection.py` → calls `waste_to_value_capital_allocation_engine.services.loss_intake.create_operational_loss()` on promotion of a `LossDetection` candidate.
4. `digital_twin/services/scenario_simulation.py` → calls `gold_intelligence.services.project_finance.{compute_npv, compute_irr, compute_payback_years}`.
5. `digital_twin/services/promotion.py` → calls `waste_to_value_capital_allocation_engine.services.governance.create_governed_investment_case()`.
6. `digital_twin/services/council.py` → creates a `ai_agent_council.CouncilRun` (`task_category='digital_twin_scenario_review'`) and `AgentTask` rows; new personas registered in `ai_agent_council/agents.py::OPERATIONAL_AGENTS` plus `ai_agents/<folder>/` training packs.
7. `digital_twin/services/human_approval_gate.py` → imports and unions `agent_runtime_model_router.services.human_approval_gate.ACTIONS_REQUIRING_APPROVAL`.
8. Evidence: every digital_twin model that needs evidence writes/reads `evidence_memory.EvidenceMemory` rows filtered by `source_reference` string, exactly like `capital_guardian.OperationalSnapshot.evidence_documents` does.

## E. Migration risks

- New app, new tables only — **zero migrations touch existing apps' schemas.** No risk to existing data.
- `db.sqlite3` in the main worktree is untouched; this worktree runs its own local SQLite for development/testing.
- The only cross-app coupling that could break on `waste_to_value_capital_allocation_engine` refactors is the direct import of `create_operational_loss`, `create_governed_investment_case`, and the `InterventionOption`/`InterventionScenario`/`OperationalLoss`/`CapitalAllocationDecision` models — all stable, well-tested, multi-release-old code, low risk.
- `gold_intelligence.services.project_finance` functions are pure and stateless — safe to import.
- Adding new entries to `ai_agent_council.agents.OPERATIONAL_AGENTS` is additive (a plain list) — confirmed no code elsewhere assumes a fixed length or fixed index.

## F. Implementation plan (sequence)

1. `digital_twin` app skeleton (`apps.py`, `admin.py`, `urls.py`, `services/`, `tests.py`) + `AssetType` registry + `Unit`/`UnitCategory` registry.
2. Core models: `IndustrialAsset`, `DigitalTwin`, `TwinComponent`, `ProcessNode`, `ProcessEdge`, `ResourceFlow`, `MetricDefinition`, `OperationalMetric`, `TwinDataGap`. Migration 0001.
3. `services/baseline.py` — deterministic completeness/confidence/freshness engine + tests.
4. `LossDetection` model + `services/loss_detection.py` (detect → candidate → human-approve → promote into real `OperationalLoss`) + tests.
5. `ModernisationScenario` (OneToOne → `InterventionOption`) + `services/scenario_simulation.py` (formulas, downside/expected/upside via `InterventionScenario`) + tests.
6. Stewardship models (`SacredSourceReference`, `StewardshipPrinciple`, `StewardshipKPI`, `StewardshipAssessment`) + seed data (draft/unapproved) + `services/stewardship.py` (scoring + guardrails) + tests.
7. Agent Council integration: new personas in `ai_agent_council/agents.py`, training packs under `ai_agents/`, `services/council.py` (builds `CouncilRun`/`AgentTask`/`CouncilDecision`, simulated mode only — no live LLM spend in this phase, consistent with the rest of the repo's `is_simulated=True` convention) + tests.
8. `HumanDecision` model + `services/human_approval_gate.py` + `services/promotion.py` (→ `CapitalAllocationDecision`) + tests.
9. `ImplementationAction` / `MeasuredOutcome` models + variance service + tests.
10. DRF API (`digital_twin/api.py` or `serializers.py`+`views.py`) + minimal Django templates for the 13 required screens.
11. Demo fixture: "Industrial Heat Modernisation Pilot" management command.
12. Full test run, `makemigrations --check`, `migrate`, lint.
13. `docs/adr/ADR-digital-twin-foundation.md` + final implementation report.

## Exact files expected to change

**New:**
- `digital_twin/` (new Django app: `__init__.py`, `apps.py`, `models.py`, `admin.py`, `urls.py`, `views.py`, `serializers.py`, `tests.py`, `migrations/`, `services/{baseline,units,loss_detection,scenario_simulation,stewardship,council,human_approval_gate,promotion,outcomes}.py`, `management/commands/seed_digital_twin_demo.py`, `templates/digital_twin/*.html`)
- `ai_agents/<new-persona-folders>/` — training packs for new Council personas
- `docs/digital_twin_existing_system_audit.md` (this file)
- `docs/adr/ADR-digital-twin-foundation.md`

**Modified:**
- `ecoiq/settings.py` — add app to `INSTALLED_APPS`
- `ecoiq/urls.py` — add one `include()` line
- `ai_agent_council/agents.py` — append new entries to `OPERATIONAL_AGENTS`

No other existing file is modified. No existing model, migration, URL, or template is altered or removed.
