# Process KPI measurement claims v1 — scoped persistence, NOT verification

Status: first internal persistence slice. No public endpoint or model-generated legal,
financial or religious assertion. No external AI call. This is a **reported claim**
bound to an indexed source chunk, not a verified or audited KPI measurement.

## Existing components reused

- `api.ProcessAnalysisRun`: real project/period anchor; original CSV lines are not stored.
- `ecoiq_os.formula_registry.FORMULAS_BY_KEY` and `Observation`: existing provisional
  20-formula registry, input units, bounded Decimal and period checks.
- `evidence_memory.EvidenceMemory`: scoped source text, immutable-in-claim text digest,
  current review metadata; its hash is integrity of the indexed text, not proof of source truth.
- `api.process_kpi_evidence_readiness.inspect_candidate_source`: current project
  permission + evidence-access and preliminary metadata gate.

## What v1 implements

- `api.ProcessKPIMeasurementClaim` is an append-only-by-service reported input row:
  project, analysis, actor, source record, canonical input/formula, decimal quantity,
  unit, period, formula specification SHA-256, source text SHA-256 and timestamp.
- `create_process_kpi_measurement_claim` requires current `ANALYSE` permission and
  a source in the *same project* with eligible review metadata. Never infer
  cross-project observation equivalence from organisational similarity.
- `claims_for_process` requires current `READ` permission; no view/serializer
  currently publishes the rows.
- Both source and analysis are protected from deletion by the FK; historical
  digests are retained if the indexed text changes. No existing claim is
  modified by the creation service.
- DB check constraint fixes `review_status='REPORTED_NOT_VERIFIED'`: the
  future independent value-review workflow must use a separate versioned
  human approval record, never silently flip this flag.
- Decimal quantities are not rounded from floats and missing inputs do not
  become zeros.

## Explicit limitations and next work

**The source's review tier is not proof the claimed quantity appears in the
document.** The value can be false, stale, from a different accounting period,
or contrary to the full original document. The content digest is only for the
current EvidenceMemory text chunk; there is no guarantee of custody of the
whole source or verification of reviewer independence.

The next PR must implement: (1) a reviewer-approved, permissioned
value-to-quote matching workflow with authenticated original documents;
(2) a separate review receipt with versioned document ID and revocation;
(3) immutable formula-result snapshots using those approved measurements;
(4) project-scoped read API only after redaction and retention review.

Do not claim this feature produces verified evidence, audit reports or religious
compliance certificates. Do not expose an unreviewed `KnowledgeSource` or
Arabic/Quranic locator on a public KPI endpoint.

## Test and migration commands

```bash
python manage.py makemigrations --check --dry-run
python manage.py test api.test_process_kpi_measurement_claims
python manage.py test api.test_process_kpi_evidence_readiness
```

Run these and the full standard CI before merge. No production migration or
Render deployment is authorised by this PR.
