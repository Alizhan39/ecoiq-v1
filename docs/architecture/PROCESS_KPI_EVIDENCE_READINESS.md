# Process KPI evidence readiness — v0.1

**Status:** non-public, read-only project-scoped service; not an audit or
automatic verification of a measured KPI value.

## Why this exists

The 20 existing candidate KPI formulas accept user-reported `Observation`
inputs. A string `source_ref` is not source authentication, and
`ProcessAnalysisRun` stores only CSV diagnostic summary, not source rows or
actual source documents. A separate bridge is needed before a user-provided
measurement can be called reviewed.

## Implemented

`api.process_kpi_evidence_readiness.inspect_candidate_source()`:

- requires the current user's project `ANALYSE` permission and an existing
  `ProcessAnalysisRun` under the same project;
- resolves `formula_key` and `input_key` through
  `ecoiq_os.formula_registry.FORMULAS_BY_KEY` (never a new 20-KPI registry);
- looks up a real `EvidenceMemory` record scoped to the SAME project;
- reuses `evidence_memory.services.retrieval_policy.is_record_accessible`
  and `is_disputed`, and rejects demo, rejected, expired, insufficient-review,
  missing-provenance and hash-mismatched records;
- returns only bounded metadata with the expected canonical unit; no source
  chunk, customer identifier, source URL or numeric observation values;
- **always** sets `observed_measurement_verified=False`,
  `source_value_and_period_bound=False`, and `formula_approved=False`.

A present reviewer + verification tier + digest are preliminary *record*
metadata only. They are **not** proof of documentary authenticity, that the
actual value appears in that source, that a reviewer is independent of a
counterparty, or that a reporting period matches.

## Security choices

No cross-project evidence is accepted, even if a memory would be visible for
general cross-project learning. This prevents a source document from company A
being borrowed to justify numbers from company B. Anonymous/viewer/removed
analysts cannot run this service, and inaccessible IDs are indistinguishable
from missing records in the returned result.

There are no endpoints, migrations, writes, document stores, approvals or
changes to production scoring.

## Next separate implementation step

Introduce an append-only project-owned `MeasurementClaim` that binds
`ProcessAnalysisRun`, canonical formula input, finite Decimal quantity,
unit, reporting period, immutable document version/source quote and reviewer
outcome. Gate access with project membership and independently establish value
matching and reviewer qualifications. Then replay formula versions and persist
an audit snapshot; do not infer authentication from a string ID.

## Test

`python manage.py test api.test_process_kpi_evidence_readiness`

Normal PR CI is required before merge; successful tests do not establish
source truth or audit validity.
