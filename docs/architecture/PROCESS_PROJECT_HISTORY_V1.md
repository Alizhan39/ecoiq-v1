# EcoIQ OS — Stage 3: project-scoped process CSV API and private history

**Status:** review-only integration increment. This is stacked on Stage 2 PR #359,
which is stacked on Stage 1 PR #358. Do not merge directly to production
without reviewing the parent changes, applying the migration and running CI.

## Existing authorities reused

- **Django sessions + DRF SessionAuthentication** authenticate humans;
  unsafe requests require a valid CSRF token. No new JWT/API-key login path.
- **`gold_intelligence.access`** is the single project permission authority.
  Its existing `GoldProject` represents a generic investable project and may
  use `commodity=infrastructure` for a construction pilot. No new tenant
  directory or guessed ownership is introduced.
- **`ecoiq_os.process_csv`** parses a bounded local CSV according to Stage 2.
- **`ecoiq_os.process_diagnostic`** calculates observed, unverified KPI and
  invokes existing Mizan/causality decision gates.
- **`api.ProcessAnalysisRun`** stores minimal, private, project-scoped
  diagnostic history. No uploaded CSV bytes, individual observation rows or
  evidence/source references are stored in that record.

## Endpoints

All routes require a Django login session. They are deliberately not in the
public company leaderboard or institutional API-key authentication surface.

| Method | Path | Permission | Result |
|---|---|---|---|
| POST | `/api/v2/projects/<slug>/process-analyses/` | ANALYSE | Parse one UTF-8 multipart CSV field named `file`; persist one minimal result |
| GET | `/api/v2/projects/<slug>/process-analyses/` | READ | 50 private analyses per page (?page=1..200), total count and has_more |
| GET | `/api/v2/projects/<slug>/process-analyses/<run_id>/` | READ | One private result in the named project |

Role behavior follows the existing project role matrix:

- Viewer / Reviewer: read history, cannot upload.
- Analyst / Manager: read history and upload.
- Active staff users: existing cross-project authority.
- Stranger, revoked membership, inactive account: no access.
- Unknown or inaccessible project returns 404; source project slug never
  grants access by itself. A project membership is checked again for every read.
- API inputs cannot supply an actor ID, project ID, Mizan status, causal
  permission, verified flag or approval status.
- Anonymous requests, other project histories and documents remain private.

Only the validated CSV file may appear in the request body; no extra fields.
Uploads have a 512 KiB file cap and 1,000 observation cap; request body is
bounded before multipart parsing, with a secondary limit on bytes read.
Production reverse proxy should enforce a compatible request-size ceiling.

POST is further limited to 20 attempts/hour per authenticated user. The
response is marked `private, no-store`. Cross-project reading, role spoofing
and revoked access have dedicated regression tests.

## History contract

Each history record contains its project FK (deletion protected), submitting
actor FK, opaque case ID, domain, process label, reporting period/unit,
unverified KPI, stage gate, row/unknown counts and creation timestamp.

The recorded KPI is the **reported loss ratio**, not a verified efficiency,
religious compliance or savings score. Unknown remains `null`.

For repeat uploads of exactly the same file into the **same project**, a
keyed HMAC fingerprint detects duplicates and returns the existing record.
The fingerprint is never returned to clients. A different project has a
separate uniqueness boundary. The server secret key must remain confidential;
a change of key changes deduplication fingerprints, so key rotation needs a
migration or a versioned fingerprint strategy before enterprise use.

History is created only after successful parsing, remains append-only from
the API, and is not exposed through generic public routes. A Django database
administrator can still manage model data; this is not a legal immutable ledger.

No source records or uploads are archived here. The client remains responsible
for secure custody of original evidence; `evidence_ref` labels in CSV are not
authenticated. Future production verification should link them to the
existing evidence/provenance store with an explicit documented access policy.

## Security and readiness limitations

No actual client CSV has been uploaded. Sensitive commercial data would pass
through the application server memory during a POST; deployment, HTTPS,
server-side access logs, hosting data location, backups, retention/deletion,
consent, DPA and incident response must be reviewed before accepting real
client information. This PR does not provide malware scanning, direct ERP
integration, signed evidence, or source authentication.

The current endpoint does not provide a browser file-upload page or an AR
surface. Those require UI and browser validation independently.

Migration: `api/migrations/0003_processanalysisrun.py` (additive; no existing
data reassignment). Assign project roles in the existing Django Admin.
Do not deploy to production or claim multi-tenant compliance without
independent security and operational review.

## Test commands

    python manage.py test api.tests_v2_process_analyses --noinput
    python -m unittest ecoiq_os.test_process_csv ecoiq_os.test_process_diagnostic ecoiq_os.test_kernel
    python manage.py makemigrations --check --dry-run
    python manage.py check
    ruff check api/v2_process_analyses.py api/tests_v2_process_analyses.py api/models.py

## Stage 4: private responsive browser workspace

The optional, Django-rendered [Process Workspace v1](PROCESS_WORKSPACE_V1.md)
provides an authenticated project selector, CSV upload, reported KPI and
private history using the existing API. No public SPA build or new
permission engine is introduced. The workspace remains a reviewed pilot,
not a verified or production-ready client integration.

## Next increment

Run first in a private staging environment with consented or synthetic
observations; independently reconcile sources, confirm before/after
measurement boundaries, then add signed evidence review and a private
browser upload interface. AI suggestions and Islah execution remain behind
causal falsification, Mizan simulation and explicit human approval.
