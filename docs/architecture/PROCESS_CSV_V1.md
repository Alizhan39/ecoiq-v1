# EcoIQ OS — Stage 2: read-only construction CSV pilot

**Status:** internal CSV adapter prototype, not a live company connection or verified production product.
The preceding Process Diagnostic v1 PR #358 must be reviewed before this stacked contribution is merged.

## Purpose

With consent, one organisation can export observations for one process, one resource,
and one calendar month as a **local UTF-8 CSV file**. This adapter validates row
identity, data boundaries, sources and quantities, aggregates observations and
passes them to the existing EcoIQ OS process diagnostic and Mizan evidence gates.

It has **no network requests, public API, database writes, background jobs, AI calls,
automated interventions or project-permission bypass**.
No real company records were supplied or processed in this change.

## CSV schema

Use the **empty** template at docs/pilots/process_observations_template.csv.
The columns are:

| Column | Definition | Fictional example |
| --- | --- | --- |
| record_id | unique identifier for each observation | R-0001 |
| case_id | opaque internal case identifier | PILOT-001 |
| domain | existing EcoIQ domain key | construction |
| process_name | same process on all rows | Site-materials |
| resource_type | existing EcoIQ resource type | material |
| period | reporting month in YYYY-MM format | 2026-10 |
| unit | one exact unit for all rows, no conversion | kg |
| flow_type | input or loss | input |
| quantity | non-negative decimal or blank (unknown) | 100 |
| evidence_ref | opaque source ID for every known observation | DOC-1 |

Do **not** upload invoices, payroll details, individual customer names or real
business data to GitHub. Do not use client/customer names as case IDs or source IDs.
Keep business files on a trusted computer and get the organisation's consent first.

All rows must describe one case, domain, process, resource, period and unit.
The loss must be a subset of the same defined input (e.g. measured discarded
material from measured site receipts). A purchase total is not automatically
equal to physical material received. Never mix distinct accounting boundaries.

The adapter rejects duplicate record IDs, malformed quoting, extra/missing
columns, negative/nonfinite numbers, mixed units/periods and inconsistent totals.
Maximum size: 512 KiB; maximum rows: 1,000. Decimal quantities have no more
than 12 integer digits and 4 decimal places, and totals are bounded.
A missing observation makes that flow total unknown, not zero. A recorded
zero is retained. A zero input produces an unknown rate, not division by zero.

Source references are **reported labels**: they are not authenticated,
independently reviewed or considered proof of causal impact.

## Local run

From the repository root, with existing Python dependencies installed,
copy the empty template to an authorised **local** destination and populate it
with consented measurements. Then run:

    python -m ecoiq_os.process_csv --input /private/path/process_observations.csv

The CLI prints an intentionally limited JSON summary: KPI value/status,
next-stage status, number of rows and unverified-source warning.
It does **not** print source identifiers, process/customer names or raw rows.
The CSV is not saved in the database.

Internal integrations may call the Python function diagnose_csv(csv_text).
Its full returned dictionary includes business amounts and source identifiers,
so it **must not** be exposed as a public endpoint or written to public logs.

## Claims and approval boundaries

The resulting KPI describes **reported** input and loss only. It does not prove
that loss is avoidable, establish a causal mechanism, assess religious compliance
or authorise changing a process. The default EcoIQ OS outcome is to collect
missing Mizan and causality evidence.

Before real commercial use: verify original documents and measurement methods;
reconcile completeness and dates; evaluate worker safety, environment and
affected groups; test and falsify causal hypotheses; simulate any proposed
Islah change and obtain human review; independently measure before/after impact.

## Stage 3: private project upload and history

See [Project Process History v1](PROCESS_PROJECT_HISTORY_V1.md) for a
permissioned Django session endpoint with role checks, CSRF protection,
minimal private history and no raw CSV persistence. It is a separate,
review-only increment and must not be treated as an approved deployment.

## Developer checks

    python -m unittest ecoiq_os.test_process_csv ecoiq_os.test_process_diagnostic ecoiq_os.test_kernel
    ruff check ecoiq_os/process_csv.py ecoiq_os/test_process_csv.py

**Next:** verified source integration, project-specific permissions and secure
persistence of audit/evidence states. No verified client pilot is claimed until
an authorised company actually supplies records and they have been reviewed.
