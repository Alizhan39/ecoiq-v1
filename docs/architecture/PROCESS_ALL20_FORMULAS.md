# Process → all 20 KPI candidate formula coverage (Phase 1)

## Purpose

Every *saved* EcoIQ `ProcessAnalysisRun` can now be inspected against
the **same** versioned 20-candidate formula registry in fixed order.

**Every formula is visited.** This does **not** mean that every formula
applies to every process: missing or irrelevant source measurements are
reported as `NEEDS_MEASUREMENTS`, never silently mapped to zero, and the
engine does **not** assert that a KPI is inapplicable. A future human-reviewed
applicability matrix may classify exclusions with reasons.

## Data and trust boundaries

`GET /api/v2/projects/<project_slug>/process-analyses/<run_id>/formula-review/`
returns the saved process metadata, the 20 formulas and a deduplicated
parameter contract with exact units and `used_by` lists.

`POST` the same path, authenticated with Django session + CSRF and
`gold_intelligence.access.ANALYSE` project permission:

```json
{
  "measurements": {
    "total_energy": {"value": "500", "unit": "kWh", "source_ref": "meter-1"},
    "produced_units": {"value": "10", "unit": "unit", "source_ref": "production-log-2"}
  }
}
```

The process's `run_id`, period, case ID and project are **loaded from the
database**. They cannot be changed by a client value. Existing CSV diagnostic
history explicitly does **not** store the CSV measurements; there is no
pretence of automatic source extraction from that record. Inputs are
caller-reported, string/integers only, finite nonnegative bounded and with
exact expected units; duplicate keys and unknown input names cannot escape
normal JSON parsing. Browser values are strings. Period is always taken from
the saved run.

Unknown entries, conflicting units, booleans, floats, NaN, oversized sources
and client-supplied approval fields are rejected. Max content length is 48 KiB,
with an authenticated per-user throttle. No persistence of customer
measurements, no background actions, no AI model call, no external API call.

All 20 formulas run in registry order:
- `REPORTED_NOT_VERIFIED` with exact Decimal value only when all required
  measurements exist and the deterministic AST formula returns a value.
- `NEEDS_MEASUREMENTS` plus an exact `missing_inputs` list for incomplete
  formulas.
- `INSUFFICIENT_DATA`, `UNDEFINED_DENOMINATOR_OR_RESULT`,
  `REVIEW_UNPLAUSIBLE_RATIO` or validation rejection where appropriate.

A shared `produced_units` input can support energy, water and greenhouse-gas
intensity **only when the unit and same process/period are consistent**.
One formula's calculated result is NEVER silently used as the evidence-backed
measurement for a different formula; there is no automatically verified
source-to-claim mapping. Every output remains unpublished and unapproved.

## React Flow

`frontend/web/src/pages/FormulaFlow.tsx` includes a per-process panel that
loads a saved process, highlights statuses on existing React Flow nodes,
displays all deduplicated parameters and shows results/gaps for all 20
formulas. Users can navigate the process ID from a private history listing
and provide source-labelled values; there is no generic arbitrary workflow
execution. A staff/analyst can calculate previews; a viewer can inspect
contracts but cannot POST.

## Test gates

```bash
python manage.py test api.tests_v2_process_formula_review \
  api.tests_v2_formula_flow ecoiq_os.test_formula_registry --noinput
cd frontend/web
npm ci
npm run typecheck
npm run lint
npm test
npm run build
```

## Remaining stages

1. Map *authorized, versioned, primary* source records from
   `evidence_memory` to each required parameter with provenance checks,
   including explicit process scope, periods and units; do not trust client
   `source_ref` identifiers as verified citations.
2. Review process-specific applicability with accountable domain experts,
   including explicit "not applicable" rationale rather than 20 forced
   numeric outputs for every sector.
3. Add multi-process batch runs, idempotency, database lineage and queue
   controls only after tenant access and real workload tests.
4. Extend from the 20 v1 candidates toward the 33 experimental questions
   and the 114 stewardship framework under the existing human review gate.
   No AI-created formula or religious interpretation receives automatic
   publication or decision authority.

**Deploy blocker:** This PR is stacked on PR #378; it must only reach main
once its base is integrated and CI plus staging/browser tests succeed.

## Verified GitHub CI — 2026-11-02

- [Focused run 41534213676](https://github.com/Alizhan39/ecoiq-v1/actions/runs/41534213676):
  Python 3.11 + Django configuration, Ruff and migration checks **PASS**;
  **27/27 targeted Django tests passed**, including complete 20-formula
  shared-parameter evaluation, missing-data protection and project boundaries.
- TypeScript, ESLint, **570/570 React tests**, production Vite build **PASS**.
- The separately triggered interactive browser check for the same revision
  [41534221946](https://github.com/Alizhan39/ecoiq-v1/actions/runs/41534221946)
  passed its configured checks. This is not a substitute for human review
  of real customer workflows or production deploy verification.
- The feature-only CI workflow was removed after success to avoid future
  duplicate jobs. All calculated outputs remain unverified and unapproved.
- Merge this PR only after its base PR #378 lands in main and regular PR
  checks/reviews are satisfactory. Render production was not deployed.
