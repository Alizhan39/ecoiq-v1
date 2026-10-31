# EcoIQ Business OS — Stage 4: private browser workspace (internal pilot)

## Delivered source

- **Page:** `/business-os/processes/`
- **Django view:** `core.process_workspace.process_workspace`
- **Template:** `templates/core/process_workspace.html`
- **CSS:** `static/css/process-workspace.css`
- **Browser client:** `static/js/process-workspace.js`
- **Integration:** existing session-only `/api/v2/projects/<project_slug>/process-analyses/` endpoint in Stage 3 PR #360.
- **Navigation:** link from the existing signed-in `/dashboard/` (not the public primary nav).

The direct route is intentionally served by Django instead of modifying the
public Vite/React bundle. The SPA's build under `static/spa/` is committed
and CI asserts it matches source. This bounded internal workspace therefore
uses the *existing Django page system* and a small, same-origin browser script:
no second UI framework, no new REST backend, no new credentials, no SPA build
artefact, no deployment mutation. The future React surface can use the same
existing API unchanged.

## Actual user workflow

1. User logs in through the existing Django session.
2. The page renders at most 100 **already-authorised** project names using
   `gold_intelligence.access.projects_for(actor, READ)`. The app determines
   upload affordance from `ANALYSE`, but actual API writes independently
   recheck the grant, including any mid-request revocation.
3. The user selects a project. The browser loads one page (50 records) of
   *private* existing analysis history from the canonical API.
4. Latest reported KPI, `NOT_VERIFIED` evidence status and the kernel's
   next evidence stage are shown. Missing numeric values are shown as
   unknown, never silently as zero or a positive finding.
5. An Analyst/Manager may select a single consented CSV, maximum 512 KiB,
   and explicitly choose **Analyse CSV**. Only a multipart `file` field is
   sent. Browser includes the Django form CSRF token; the API enforces the
   real project roles, CSRF, upload cap and rate limit.
6. After upload, the project history is refreshed, and repeat uploads show
   the idempotent result rather than inventing another analysis.
7. Project changes abort stale history reads and clear previously displayed
   KPI data, to avoid showing one project's results beside another project.
   No sensitive CSV content, source references or business values are put in
   localStorage/sessionStorage or the URL.

The browser renders server-provided names as text nodes, not HTML strings.
History rows are inserted with `textContent`, which prevents received names
or case IDs from becoming executable markup. Accessible labels, keyboard
controls, status/error announcements and mobile column stacking are included.

## Access and privacy boundaries

The Django page itself is login-required, not cached, and uses both a
`noindex, nofollow` meta directive and an X-Robots-Tag header. It removes
public analytics includes from this private page through the existing shared
base template's optional `suppress_analytics` flag.

The project selector is not an authorisation system. It never receives
arbitrary project slugs from a user-controlled API. Only the existing server
session and project grants can reveal the project name. All actual API reads
and uploads re-authorise on each request. An Analyst losing the ANALYSE role
can still read history while their READ role remains active; an inactive or
revoked account loses access.

No browser cache, graphing library, AI agent, data connector, AR device or
religious compliance verdict was added. History and KPI are from **reported,
not verified** CSV values, and do not prove that loss was avoidable.

### Before using any real client information

- Confirm the consent, client DPA/retention basis, hosting and backups.
- Apply and review Stage 3 migration and the project memberships.
- Test authenticated same-origin CSRF, no-store responses, revoked
  memberships and cross-project data isolation in a *private staging*
  environment.
- Independently validate sources and full accounting boundaries. Do not
  publish a company score or approve a business modification from this UI.

## Run checks

```bash
python manage.py test core.tests_process_workspace api.tests_v2_process_analyses --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
ruff check core/process_workspace.py core/tests_process_workspace.py
```

The full visual browser verification on desktop/mobile and accessibility
audit remain required before merging. The preceding Stage 1/2/3 parent PRs
must be merged/rebased and re-tested in CI before deployment. No claim of
live client integration or production approval is made.

## Stage 5: evidence-planning Decision & Islah

The [Decision & Islah V1](DECISION_ISLAH_V1.md) adds a read-only,
project-scoped investigation panel for competing causal questions and
study-only changes. It does not call an LLM or approve an intervention.

## Next stage (bounded)

Staging with synthetic observations, end-to-end browser checks, private
project role administration, and source-document verification; only then a
human-reviewed Islah recommendation panel with falsification evidence and
Mizan safety review.
