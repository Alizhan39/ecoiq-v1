# Evidence & Provenance Integration Contract (design gate)

Status: **proposal only**. No migrations, endpoints, production changes, or verified audit claims. Implement in small follow-up PRs after checking the current branch and domain model with maintainers.

## Purpose

Connect saved `ProcessAnalysisRun` and the candidate 20-KPI formula preview to verifiable measurements **without** building a competing evidence database or claiming that self-reported values have been independently verified.

## Existing components to reuse (verified on main when this note was drafted)

- `companies/evidence.py`: canonical provenance vocabulary and eligibility distinctions.
- `companies/provenance.py`: append-only metric provenance; current pointer and bulk lookup.
- `evidence_memory.EvidenceMemory`: source URL/reference, confidence, verification status, review tier, reviewer, expiry, integrity reference and demo flag.
- `company_intelligence/services/source_registry.py`: discovered-source approval and harvester registration.
- `company_intelligence/services/evidence_provenance.py`: regulatory/independent/self-reported source classification, distinct from human review.
- `api/v2_process_analyses.py`: project-authorised process run history; **the original CSV and raw source observations are deliberately not stored**.
- `api/v2_kpi.py`: public source-governance boundary; unreviewed sacred references must not leak into public API responses.

Do not copy these fields into a new generic `EvidenceRecord` model or create a second provenance status vocabulary. First map project access and company-scoped evidence identities, which do **not** automatically have the same ownership semantics.

## Gaps to close in order

1. **Merge check:** verify the process formula-review feature is on `main` before depending on its endpoint. PR #379 was merged into a feature branch, not directly into main, when last checked.
2. **Scope mapping:** document how `GoldProject` ownership / `ProcessAnalysisRun` identity relates (if at all) to `CompanyProfile` / `EvidenceMemory`. Never infer shared ownership from matching text or names.
3. **Source binding:** require a server-resolved, authorised evidence ID when a measurement claims evidence. Free-text `source_id` is only a user-supplied label and remains `REPORTED_NOT_VERIFIED`.
4. **Immutable inputs:** record quantity as Decimal string, unit, reporting period, measurement definition, source identity/version, validation status, verification actor/time, and a stable digest or integrity reference. Files should be retained only after storage, retention, access and privacy decisions. An integrity digest confirms byte equality, **not factual truth**.
5. **Calculation snapshot:** persist the exact approved registry formula ID/version, deterministic canonical input ordering, unit-validation outcome, blockers, output/result and algorithm version in the same project boundary; never recompute silently under changed formula versions.
6. **Status gate:** distinguish NOT_SUPPLIED, INVALID_INPUT, REPORTED_NOT_VERIFIED, HUMAN_REVIEWED and INDEPENDENTLY_VERIFIED; map to existing statuses rather than invent parallel public semantics. No missing-as-zero or synthetic-as-measured.
7. **Review and publication:** authenticated project read vs analyse vs evidence-review permissions; explicit reviewer identity and workflow; no automatic publication, religious verdict, legal opinion or financial suitability conclusion.
8. **Audit/reproducibility:** replay the snapshot using the original formula version; log superseding corrections instead of silently rewriting accepted historical outcomes.

## API contract proposal (not implemented)

`GET /api/v2/projects/<slug>/process-analyses/<run_id>/formula-review/` remains read-only.

Later, a **separate, permission-gated** evidence-binding workflow could accept a project-owned measurement record with canonical unit, period and reference to a server-authorised `EvidenceMemory` object (or an explicit scoped bridge mapping). It must not trust client claims of reviewer, verification tier, company ownership, source classification, or reporting period.

`POST` formula review remains preview-only until persistence and independent review are intentionally approved.

## Tests required before implementation release

- Cross-tenant/project enumeration and evidence-ID guessing both fail closed (404 or appropriate denial).
- Source from company A cannot be bound to an unrelated project B.
- Missing values, zero denominator, invalid Decimal, NaN/infinity, wrong unit and mismatched period never yield a valid KPI.
- Repeated input snapshot + same formula version reproduces same result; changing a formula version never rewrites an old snapshot.
- Self-reported or unreviewed sources never become independently verified based on a free-text label.
- Demo/seeded evidence does not become measured; source expiry and reviewer revocation handled explicitly.
- Sensitive uploaded documents stay private; no raw content leaks in API, logs or errors.
- Sacred-source references requiring scholarly review remain outside public output.

## Acceptance criteria

The first implementation PR must be **small**: one process-to-evidence scoped bridge, no duplication of the company provenance stack, migrations documented, rollback plan, targeted Django tests, and review of retention/privacy implications. A separate PR then adds immutable snapshot persistence and replay. No deployment without normal CI + domain/security review.

## Product scope

This foundation serves financial, legal, ESG and governance analytics, but **does not** claim to adjudicate whether a law is just, issue legal advice/fatwas, or establish causal impacts from correlations.
