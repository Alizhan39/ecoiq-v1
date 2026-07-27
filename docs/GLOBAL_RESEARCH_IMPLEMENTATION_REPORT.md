# Global Research, Technology & Manufacturer Discovery Engine — Implementation Report

Branch: `feat/global-research-engine` (isolated git worktree at
`.claude/worktrees/global-research-engine`, branched from the completed
Digital Twin Foundation work so this module builds directly on it).

## 1. What was built

A new Django app, `global_research`, implementing the full flow specified:
Digital Twin → verified operational loss/need → technical problem
definition → research mission → search strategy → source discovery →
claim extraction → evidence evaluation → technology candidates →
manufacturer/product candidates → compatibility screening → comparative
evaluation → supplier-neutral modernisation option → scenario simulation →
stewardship & risk assessment → Agent Council → human shortlisting →
capital allocation workflow.

Every deterministic score (evidence quality, compatibility, comparative
ranking, risk flags) is plain, explainable Python. Claim extraction in this
phase is deterministic and schema-validated over provider-structured
fields — never raw document text fed into a live LLM prompt (see ADR
decision 4) — consistent with this platform's existing honesty convention
and with the task's explicit prompt-injection-defence requirements.

## 2. Files created

**New Django app** (`global_research/`, ~3,900 lines across models/services/views/tests):
- `models.py` — 19 models: the 14 named in the spec (`ResearchMission`,
  `TechnicalRequirement`, `ResearchQueryPlan`, `ResearchSource`,
  `ResearchClaim`, `ClaimAssessment`, `TechnologyCategory`,
  `TechnologyCandidate`, `ManufacturerProfile`,
  `SupplierOrIntegratorProfile`, `ProductCandidate`,
  `CompatibilityAssessment`, `ComparativeEvaluation`,
  `ResearchRecommendation`) plus 5 supporting models (`ResearchRun`,
  `ContradictionRecord`, `SupplyChainRiskFlag`, `ResearchDocumentDraft`,
  `ResearchHumanDecision`). `ManufacturerProfile`/`SupplierOrIntegratorProfile`
  are thin companion profiles on `capability_graph.Organisation` — not a
  new organisation directory.
- `constants.py` — source-type vocabulary and the A/B/C/D evidence-tier mapping.
- `admin.py`, `urls.py`, `views.py`, `apps.py`, `tests.py` (66 tests).
- `migrations/0001_initial.py`, `0002_researchsource_content_safety_flagged_and_more.py`.
- `providers/base.py` (the `ResearchProvider` interface + result
  dataclasses), `providers/simulated.py` (4 fixture-backed providers, one
  per evidence layer, plus the seeded adversarial injection-test fixture),
  `providers/registry.py`.
- `services/orchestrator.py`, `claim_extraction.py`, `evidence_scoring.py`,
  `contradiction.py`, `discovery.py`, `compatibility.py`, `comparison.py`,
  `stewardship_screen.py`, `council.py`, `human_approval_gate.py`, `risk.py`,
  `scenario_bridge.py`, `documents.py`, `content_safety.py`, `permissions.py`.
- `management/commands/seed_global_research_demo.py` — the Global
  Technology Search for Industrial Heat Modernisation demo fixture.
- `templates/global_research/*.html` — 9 templates (shared `_base.html` +
  8 content screens).

**New Agent Council training packs** (`ai_agents/`, 13 new personas × 10
files = 130 files): `problem_definition_agent/`, `technical_requirements_agent/`,
`scientific_research_agent/`, `patent_innovation_agent/`,
`manufacturer_discovery_agent/`, `product_specification_agent/`,
`independent_evidence_agent/`, `compatibility_agent/`,
`commercial_intelligence_agent/`, `supply_chain_risk_agent/`,
`regulatory_agent/`, `evidence_auditor_agent/`, `research_synthesis_agent/`.
The 14th council role (Stewardship) reuses the Digital Twin phase's
existing "Stewardship Agent" persona — not duplicated.

**New docs**: `docs/global_research_existing_system_audit.md`,
`docs/adr/ADR-global-research-engine.md`,
`docs/research_evidence_methodology.md`, this report.

## 3. Files modified (existing apps)

- `ecoiq/settings.py` — registered `'global_research'` in `INSTALLED_APPS`.
- `ecoiq/urls.py` — one `include()` line mounting `global_research.urls` at `/global-research/`.
- `ai_agent_council/agents.py` — appended 13 new entries to `OPERATIONAL_AGENTS`
  (numbers 25–37). No existing entry changed or removed.
- `ai_agent_council/tests.py`, `agent_runtime_model_router/tests.py` — two
  hardcoded repo-invariant tests (exact agent/file/registry counts) updated
  to reflect the registry's new size (20→33 operational agents,
  200→330 training files, 24→37 registry entries) — the same pattern
  followed when the Digital Twin phase added its 7 personas.
- `backend_intelligence_engine/models.py` — additively extended
  `BackgroundTaskRun.TASK_TYPE_CHOICES` with 3 new task types
  (`research_mission_run`, `research_provider_search`,
  `research_claim_extraction`) for future Celery-task observability reuse.

**No other existing file was modified.** No existing model, migration,
URL, or template was altered or removed.

## 4. Reused existing components (not duplicated)

- `capability_graph.Organisation` + `OrganisationCapability` — the real,
  deduplicated organisation identity and evidence-backed capability-claim
  graph. `ManufacturerProfile`/`SupplierOrIntegratorProfile` are companion
  profiles; confirming a manufacturer writes a real
  `OrganisationCapability(capability='manufacture')` row via the existing
  `get_or_create_organisation()` — this **is** the Knowledge Graph edge the
  spec asks for, no second graph engine.
- `harvester.services.verification` — `freshness()` and `corroboration()`
  pure functions reused directly inside `evidence_scoring.py`'s formula.
- `evidence_memory` conventions — the soft `source_reference` string
  pattern (`"global_research.ResearchSource:<pk>"`) used throughout,
  matching every other cross-app link in the platform.
- `gold_intelligence` NPV/IRR-style deterministic-formula discipline —
  imitated (not imported) for the comparative-evaluation weights.
- `digital_twin` — `IndustrialAsset`/`DigitalTwin`/`TwinComponent`/
  `ProcessNode`/`LossDetection`/`TwinDataGap` as mission origins; `Unit` for
  quantities; `TimeStampedModel` imported directly as the abstract base;
  `ModernisationScenario` created (never a parallel model) by
  `services/scenario_bridge.py`; `services.promotion.promote_scenario()`
  reused unmodified for the final capital-allocation step.
- `ai_agent_council` — `CouncilRun`/`AgentTask`/`CouncilDecision` schema
  and `services.confidence.build_confidence_breakdown`/
  `services.disagreement.classify_conflict` reused unmodified.
- `agent_runtime_model_router.services.human_approval_gate` — extended
  by union (3 new action types), not forked.
- `agent_runtime_model_router.services.model_adapters` — the adapter-
  registry *shape* (not the code) reused for `providers/base.py`.
- `outreach_readiness` — the exact draft-versioned-immutable-once-approved
  shape reused for `ResearchDocumentDraft`.
- `legacy_safe` — the "evidence is templated, never executed" philosophy
  and the seeded-adversarial-fixture testing pattern reused for
  `content_safety.py` and the demo's injection-test source.
- `backend_intelligence_engine.services.http_client` — named as the
  reuse point for any future live provider's HTTP calls (no live HTTP call
  is made in this phase).

## 5. Model changes / migrations

- `global_research`: `0001_initial` (19 models), `0002_researchsource_content_safety_flagged_and_more`
  (2 additive fields) — both applied cleanly.
- `backend_intelligence_engine`: `0007_alter_backgroundtaskrun_task_type` — additive `choices=` metadata only.
- `python manage.py makemigrations --check --dry-run` reports **no changes detected**.
- Zero migrations touch any existing app's table schema beyond the one
  additive `choices=` change.

## 6. Provider architecture

`providers/base.py::ResearchProvider` — abstract `search(query_plan) ->
list[SourceCandidateResult]`, `fetch(candidate) -> SourceDocumentResult`,
`normalise(document) -> NormalisedSourceResult`, `health_check() ->
ProviderHealth`. Four concrete providers in `providers/simulated.py`, one
per evidence layer (`authoritative_standards_provider`,
`commercial_manufacturer_provider`, `market_procurement_provider`,
`early_innovation_provider`), each backed by a small, clearly-synthetic
fixture catalog and each honestly reporting
`ProviderHealth(status='simulated', credentials_configured=False)` — no
live network call anywhere in this phase, no uncontrolled scraping, per
the explicit instruction. `providers/registry.py` provides `get_provider`/
`all_providers`/`providers_for_layer`/`health_check_all`. A live adapter
(e.g. a real web-search or CrossRef/PatentsView client) is a drop-in
future subclass of the same interface — the orchestrator never branches on
liveness.

## 7. Formulas and weights (all versioned; see `docs/research_evidence_methodology.md` for full detail)

- **Evidence score** (`services/evidence_scoring.py`, `FORMULA_VERSION='1.0.0'`):
  `0.25·source_authority + 0.15·methodological_quality + 0.20·independence
  + 0.15·reproducibility + 0.10·recency + 0.15·applicability −
  15·unresolved_contradictions`, clamped to [0, 100]. `verified` is only
  ever set from a genuinely agreeing independent claim (a real bug — a
  contradicted vendor claim being marked verified — was found and fixed
  during implementation; see §9).
- **Compatibility** (`services/compatibility.py`, `FORMULA_VERSION='1.0.0'`):
  any failed mandatory requirement forces `mandatory_pass=False` and
  `overall_status ∈ {incompatible}`, independent of the optional-fit score.
- **Comparative evaluation** (`services/comparison.py`,
  `FORMULA_VERSION='1.0.0'`): 20 dimensions, `DEFAULT_WEIGHTS` summing to
  1.0 (asserted at import time), each dimension backed by a real signal or
  explicitly logged in `missing_data` — never silently fabricated. A
  `mandatory_pass=False` candidate is excluded from ranking (`is_ranked=False`,
  `rank=None`) regardless of its weighted score.
- **Risk rules** (`services/risk.py`): threshold-based, idempotent upsert,
  modeled on `capital_guardian.services.red_flag_engine`'s style.

## 8. Security controls

- **Content-is-evidence-never-instruction**, enforced structurally: every
  source/claim text field is a plain `TextField`, rendered only through
  Django's auto-escaping templates; no code path in this app passes
  source/claim text to a function capable of taking an action.
  `services/content_safety.py` adds an explicit, logged detection step
  (regex patterns extending `agent_runtime_model_router.services.safety_assertions`'s
  style) — flagging never changes how content is treated. A deliberately
  adversarial fixture (an "ignore all previous instructions..." source) is
  part of the shipped demo and is asserted, in a test, to have zero effect
  on any candidate's status.
- **No autonomous procurement**: no send/email/HTTP-POST-to-vendor function
  exists anywhere in `global_research` (asserted by a test that greps the
  `documents.py` module source for forbidden calls). `ResearchDocumentDraft`
  can only be drafted and approved — never sent.
- **Human approval gates**: `services/human_approval_gate.py` extends the
  base gate with 3 new action types (`research_candidate_shortlist`,
  `research_document_draft_approval`, `research_scenario_creation`), all
  enforced in the service layer, not just the UI.
- **Mission-level permissions**: `services/permissions.py::can_view_mission()`/
  `can_manage_mission()` — a deterministic, three-input function modeled on
  `legacy_safe.services.permissions.can_access()`, since this platform has
  no multi-tenant concept anywhere (confirmed in the audit).
- **No copyrighted full-text storage**: `ResearchSource.permitted_extract`
  is a bounded excerpt field with a separate `licence_or_usage_note`,
  never a full-document mirror.

## 9. Tests executed and results

- `python manage.py test global_research` — **66/66 passed.** Covers:
  model constraints, provider interface conformance and keyword filtering,
  schema-validated claim extraction and its idempotency, evidence scoring
  (tier ordering, and a regression test for a real "verified from a
  contradicted claim" bug found and fixed during implementation),
  contradiction detection (value-mismatch, tolerance, tier-based
  auto-resolution, never overwriting a human resolution), technology/
  manufacturer/product discovery and idempotency, mandatory-vs-optional
  compatibility gating and formula versioning, comparative-evaluation
  weight validity and rank-exclusion for incompatible candidates,
  mission-readiness validation and idempotent orchestrator re-runs (plus a
  regression test for a real "evidence_score stuck at None" bug found
  during manual UI verification), Research Council persona reuse (Stewardship
  Agent shared) and 14-agent task creation, the human-approval gate,
  scenario-bridge preconditions (twin + promoted loss required), RFI/RFQ
  draft versioning and the structural absence of send capability,
  deterministic risk-flag idempotency, the pre-scenario stewardship
  screen, mission-level permission boundaries, and the full demo workflow
  end to end including its own idempotency.
- `python manage.py test digital_twin global_research ai_agent_council ai_agent_workbench agent_runtime_model_router` — **125+198 = confirmed passing together** (run at two checkpoints during implementation; both clean).
- `python manage.py test` (entire platform) — **3,651 passed, 2 failed, 2
  skipped, out of 3,653 total** (3,587 from the Digital Twin baseline + 66
  new from `global_research`). The 2 failures are the exact same
  pre-existing, unrelated `good_agents` tests
  (`test_seeds_all_114_and_real_providers`,
  `test_one_provider_failure_does_not_stop_others`) already documented as
  pre-existing in `docs/DIGITAL_TWIN_IMPLEMENTATION_REPORT.md` — confirmed
  identical failure count and identical test names before and after this
  work, i.e. this implementation introduced zero new failures anywhere in
  the platform. The 2 skips are the same environment-only `CountryProfile`
  fixture skips as before, unrelated to `global_research`.
- `makemigrations --check --dry-run` — clean, no changes detected.
- Manual browser verification against the seeded demo (mission dashboard,
  manufacturer comparison, evidence view, Research Council view, RFI draft
  view) — **found and fixed two real bugs** neither the automated tests nor
  the shell smoke test had caught:
  1. `evidence_scoring.count_independent_corroborations()` counted any
     independent claim on the same (subject, predicate) as corroboration,
     including one that actually *contradicts* the claim being scored — so
     a vendor claim superseded by a disagreeing independent source was
     still marked `verified=True`. Fixed to exclude claims linked by a
     `ContradictionRecord`.
  2. `TechnologyCandidate`/`ProductCandidate.evidence_score` was aggregated
     from claim confidences *before* those claims were scored (evidence
     scoring runs in a later orchestrator pass), so it stayed `None`
     forever even after a complete, successful mission run. Fixed by
     extracting the aggregation into `refresh_technology_candidate_evidence()`/
     `refresh_product_evidence()` and calling them again after scoring.
  Both fixes have dedicated regression tests.

## 10. Known limitations

- **No live provider is wired.** All four evidence-layer providers are
  simulated/fixture-backed, per the explicit "do not build uncontrolled
  scraping in this phase" instruction. Wiring a real web-search, CrossRef/
  PatentsView, or standards-body API is a clean drop-in (same
  `ResearchProvider` interface) but requires real credentials this repo
  does not have today (confirmed in the audit: zero search/scholarly/patent
  API keys anywhere in `.env.example`/settings).
- **Claim extraction is deterministic/rule-based, not live-LLM**, per ADR
  decision 4 — it parses provider-*structured* fields, not arbitrary
  document prose. A future live-LLM extraction adapter must emit the same
  schema and pass through the same `validate_claim_schema()` gate.
- **Comparative-evaluation dimensions rely on neutral defaults** (logged in
  `missing_data`) for signals this phase has no deterministic source for
  yet: OPEX impact, cybersecurity, data ownership. These are honestly
  flagged, never fabricated, but the ranking is correspondingly less
  informative on those axes until real signal sources are wired.
- **Multilingual support is structural, not translational** — `ResearchSource.language`
  and `ResearchQueryPlan.languages` are real fields, and the demo includes
  sources in 7 languages, but no translation library is integrated (none
  exists anywhere in the repo); a source's `permitted_extract` is stored
  and displayed in its original language only.
- **Training packs are foundation-depth**, matching the Digital Twin
  phase's own limitation note — complete (all 10 required files, specific
  content) but with 1-2 test cases each rather than a large golden-case library.
- **`SupplierOrIntegratorProfile`/`ManufacturerProfile` sanctions screening
  is a status field, not a real sanctions-list integration** — no sanctions
  database API is wired; `sanctions_screening_status` defaults honestly to
  `'not_screened'`.

## 11. Unsupported sources / external services still requiring credentials

- General web search (e.g. a real search API).
- Scholarly/citation databases (e.g. CrossRef, Semantic Scholar).
- Patent databases (e.g. PatentsView, Espacenet).
- Standards-body and regulator publication feeds.
- Procurement/tender databases.
- Sanctions/export-control screening APIs.
- Translation services for non-English source content.

None of these are contacted in this phase; the provider abstraction is the
seam where each becomes a real adapter once credentials exist.

## 12. Recommended next phase

1. Wire one real provider (start with a scholarly/standards API, the
   highest-authority evidence layer) behind the existing `ResearchProvider`
   interface, reusing `backend_intelligence_engine.services.http_client.fetch()`
   for retries and `harvester.services.fetchers`'s robots.txt-respecting
   pattern.
2. Add a schema-validated, live-LLM-assisted extraction adapter for
   unstructured manufacturer documentation (PDFs, web pages) — output must
   conform to the exact same claim schema `claim_extraction.validate_claim_schema()`
   already enforces, and raw document text must never be concatenated
   directly into a prompt without the delimiting discipline
   `docs/adr/ADR-global-research-engine.md` decision 5 requires.
3. Integrate a real sanctions/export-control screening API for
   `ManufacturerProfile.sanctions_screening_status`.
4. Extend `services/comparison.py`'s neutral-default dimensions (OPEX
   impact, cybersecurity, data ownership) with real deterministic signal
   sources as they become available.
5. Add a translation-assist layer for non-English sources, always
   preserving the original-language `permitted_extract` alongside a clearly
   labelled machine translation, with a human-review flag for ambiguous
   translations (per the task's explicit multilingual requirements).
6. Provision the commented-out Celery worker + Redis service in
   `render.yaml` if/when mission execution needs to run asynchronously in
   production rather than via management command / synchronous service call.
