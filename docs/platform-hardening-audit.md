# Platform Hardening — Audit

**Audited:** `origin/main` @ `6ac4a2c` (PR #288), 2026-08-24
**Method:** read-only inspection of a clean worktree at `origin/main`. No
production access, no deploy, no Render dashboard change.

## Read before auditing

`AGENTS.md` **does not exist** — not on `main`, not on any of the 60+ branches
checked. `CLAUDE.md` is this repository's equivalent instruction file and was
read, along with `README.md`, `DEPLOY.md`, `render.yaml`,
`docs/operations/PRODUCTION_RUNBOOK.md`, `docs/engineering/deployment-runbook.md`
and `docs/product/*`.

## Where "current" is

The checked-out working tree is `feat/stripe-billing-integration` — **327
commits behind `origin/main`**, with 113 modified files, and recorded as
deliberately frozen in `docs/product/CURRENT_STATE.md`. It was not touched.
Auditing it would have described a repository that no longer exists; every
finding below is measured against `origin/main`.

## Render commands — unchanged

`render.yaml` still specifies exactly the historical commands:

| phase | command |
|---|---|
| Build | `pip install -r requirements.txt && ./build.sh` |
| Pre-Deploy | `./predeploy.sh` |
| Start | `./start.sh` |

`healthCheckPath: /healthz/`. Preserved as-is.

---

## The headline finding

**This repository is substantially more hardened than a greenfield hardening
brief assumes.** Of the twenty audited capabilities, **nine are already
COMPLETE** and were built deliberately, with tests and with the reasoning
recorded in module docstrings.

Specifically, three items the brief lists as P0 work to implement are already
done and must **not** be rebuilt:

- **Structured logging** (§4.2) — `structlog` 26.1.0, `core/logging_setup.py`,
  `core/logging_middleware.py`, `core/tests_structured_logging.py`. Request IDs,
  route, duration, status and origin fingerprinting are already emitted.
- **Sentry error reporting** (§4.3) — `core/sentry_setup.py` with
  `EventScrubber`, `before_send` filtering and `ignore_logger`; `sentry-sdk`
  2.66.1 pinned. `SENTRY_DSN` is reported as configured in the Render
  dashboard; repository inspection cannot independently verify
  dashboard-managed secret values, so delivery of safely-sanitised events
  should be confirmed operationally rather than inferred from this file.
- **Secret management** (§4.5) — `.env.example` with 58 variables, placeholder
  values only, no real secrets; production validation in `ecoiq/settings.py`
  refuses to start on `ALLOWED_HOSTS = "*"` or on an `sk_live_` Stripe key
  without a second explicit latch.

The genuine gaps are narrower and more specific than the brief anticipates, and
they are listed below.

---

## Capability matrix

Status is measured, not estimated. "File evidence" is the primary artefact.

| # | Capability | Existing implementation | File evidence | Status | Risk | Recommended change | Pri | Cx | Ext svc |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Backend/frontend structure | Django 5.2 + Wagtail monolith; React SPA at `frontend/web`; build-time islands at `frontend/app`; Remotion offline | `ecoiq/settings.py`, `core/spa.py`, `frontend/*/` | COMPLETE | — | none | — | — | NO |
| 2 | Auth & tenant isolation | Django session auth; `core/access.py` gates 58 surfaces; per-app org FKs | `core/access.py`, `*/models.py` | PARTIAL | **HIGH** | no single tenancy primitive; org scoping is per-app convention, not enforced | P1 | L | NO |
| 3 | Models / migrations / indexes | 82 apps, 626 routes; `models.Index`/`db_index` across high-volume models | `harvester/models.py` (13), `ecoiq_commerce/models.py` (13), `leads/models.py` (8) | COMPLETE | LOW | verify against real plans before adding more | P3 | M | NO |
| 4 | Background jobs (Redis/Celery) | Celery app + settings complete; **services commented out in `render.yaml`** | `ecoiq/celery.py`, `ecoiq/__init__.py`, `backend_intelligence_engine/tasks.py`, `good_agents/tasks.py` | PARTIAL | **HIGH** | code ready, not deployed — a cost decision, not a code gap | P1 | S | **YES** |
| 5 | AI provider calls | `ai_gateway` with router, fallback chain, typed exceptions, provider attempts | `ai_gateway/service.py`, `ai_gateway/exceptions.py` | PARTIAL | MED | no shared timeout/retry policy across providers | P1 | M | NO |
| 6 | Caching | Explicit `CACHES`: Redis when `REDIS_CONFIGURED`, named `LocMemCache` otherwise, always LocMem under tests | `ecoiq/settings.py` (Cache block), `core/tests_cache.py` | **COMPLETE** (config) | LOW | configured; Redis itself still unprovisioned — a Render action, not code | — | — | **YES** (to enable Redis) |
| 7 | Logging | structlog, JSON-capable, request/correlation IDs, `QUIET_PATHS` | `core/logging_setup.py`, `core/logging_middleware.py`, `core/tests_structured_logging.py` | **COMPLETE** | LOW | add task/run/stage fields when Celery is enabled | P2 | S | NO |
| 8 | Error reporting | Sentry, optional, scrubbed, release/environment labelled | `core/sentry_setup.py`, `requirements.txt:129` | **COMPLETE** | LOW | none | — | — | opt |
| 9 | Email | env-driven; console backend default; guard when SMTP user absent | `ecoiq/settings.py:707-737` | COMPLETE | LOW | none | — | — | opt |
| 10 | Rate limiting | DRF throttles: AI chat per-user + per-IP, catalog, API-key tiers | `ai_gateway/throttles.py`, `api/throttles.py` | PARTIAL | **HIGH** | no limits on login/reset/registration/upload; backed by unconfigured cache | P0 | M | NO |
| 11 | Health checks | `/healthz/` liveness, `assertNumQueries(0)`, `never_cache`, SSL-exempt | `core/health.py`, `core/tests_health.py`, `render.yaml` | PARTIAL | MED | **`/readyz/` deliberately absent** — the one clear code gap in §4.1 | P0 | S | NO |
| 12 | Security headers / middleware | HSTS 1y + preload, nosniff, secure cookies, CSRF, `SECURE_PROXY_SSL_HEADER`, XFrame | `ecoiq/settings.py:776-851` | PARTIAL | MED | **no Content-Security-Policy anywhere** | P1 | M | NO |
| 13 | Backup & DR | Render automatic PostgreSQL backups, 7-day retention (starter) | `docs/operations/PRODUCTION_RUNBOOK.md:141-156` | PARTIAL | **HIGH** | runbook already admits: no off-platform copy, **no restore ever tested** | P0 | S | **YES** |
| 14 | CI/CD | ruff, mypy, frontend typecheck/lint/test/build + artefact match, `manage.py check`, `makemigrations --check`, full suite, Gitleaks | `.github/workflows/django.yml`, `secret-scan.yml` | COMPLETE | LOW | **no dependency vulnerability scan**; no `dependabot.yml` | P2 | S | NO |
| 15 | Automated tests | **5,893 test methods**; 5,889 ran green in CI on #289 | repo-wide | COMPLETE | LOW | add tests alongside each new capability | — | — | NO |
| 16 | API versioning | v1 legacy + v2 canonical, separately routed | `api/urls.py`, `api/v2_urls.py` | COMPLETE | LOW | none | — | — | NO |
| 17 | Analysis status / progress | no SSE, no polling contract, no `StreamingHttpResponse` | (no matches repo-wide) | **MISSING** | MED | defer until Celery is actually deployed | P2 | M | NO |
| 18 | Evidence/formula/prompt/methodology versioning | provenance store, metric registry, model identity, confidence bands | `companies/provenance.py`, `companies/metric_registry.py`, `ml/model_identity.py`, `core/unknown.py` | **COMPLETE** | LOW | none — this is the repo's strongest area | — | — | NO |
| 19 | Idempotency & retries | `http_client.fetch`: separate connect/read timeouts, exponential backoff, retries only 429/5xx/conn/timeout, never 4xx | `backend_intelligence_engine/services/http_client.py`, `ingestion/pipeline.py` | PARTIAL | MED | good policy, but scoped to one app; no request-level idempotency keys | P1 | M | NO |
| 20 | Feature flags & product status | `platform_registry/agents.py`: PRODUCTION/BETA/EXPERIMENTAL/SPECIFICATION | `platform_registry/agents.py:55-79` | PARTIAL | LOW | status registry exists; **no runtime feature-flag toggle** | P2 | S | NO |

### Additional findings not in the numbered list

| Capability | Status | Evidence |
|---|---|---|
| SSRF protection | **PARTIAL — real gap** | `company_intelligence/services/url_safety.py` gates URLs at *registration* only. `backend_intelligence_engine/services/http_client.py:61` calls `httpx.Client(follow_redirects=True)` with **no scheme/host validation and no post-redirect revalidation**. Its own docstring says the fetch stack "has NO scheme/host validation at all". |
| Circuit breaker | **MISSING** | no implementation (only a false positive in `heating/seed_data.py` about electrical breakers) |
| Dead-letter handling | PARTIAL | `backend_intelligence_engine` `TaskRun` persists `status`/`failed_at`/`error_summary`; no replay mechanism, no replay audit record |
| Workflow state machine | **MISSING** | no unified PENDING→…→COMPLETED status and no DETECT→…→LEARN stage enum; only ad-hoc per-app statuses (e.g. `digital_twin/models.py:553`) |
| Platform audit log | PARTIAL | audit models exist only in `legacy_safe` and `capital_guardian`; no cross-cutting append-only audit trail |

---

## The finding that connects several others — now configured

**Originally: `CACHES` was never configured**, so Django used `LocMemCache` and
every DRF throttle (`ai_gateway/throttles.py`, `api/throttles.py`) counted in
it. On `--workers 1 --threads 4` (`start.sh:18-20`) the four threads share one
process, so rate limiting was **not** broken — it was fragile in a way that
fails silently: counters reset on each `--max-requests 300` recycle
(`start.sh:22`), and raising `WEB_CONCURRENCY` would multiply every limit with
no error and no log line.

**Now:** `CACHES` is explicit in both directions. Redis is selected when
`REDIS_URL` is set in the environment — the same `REDIS_CONFIGURED` signal
`/readyz/` uses, never `REDIS_URL`'s own truthiness, which is always true
because of its localhost default. Otherwise a named `LocMemCache`, and always
LocMem under tests so no test needs an external service. No new dependency:
Django 5.2's Redis backend runs on the `redis-py` already present for Celery.

**Still outstanding, and it is not code.** No Redis instance is provisioned, so
production still runs on LocMem — now with a startup warning instead of
silence. Provisioning is a paid Render action; see
`docs/architecture/reliability.md`.

Durable rate limiting is the next package. No throttle policy was changed here.

---

## Recommended P0 order (dependency order)

1. **`/readyz/` readiness endpoint** — the one unambiguous, self-contained code
   gap in §4.1. No external service. `core/health.py` already names it.
2. **Backup & restore runbook** + `docs/runbooks/`, `docs/architecture/` —
   documentation of an admitted gap; requires a manual Render action, not code.
3. ~~**Cache configuration**~~ — done: Redis when `REDIS_CONFIGURED`, named
   `LocMemCache` otherwise. Enabling Redis remains a Render action.
4. **Auth-surface rate limiting** — depends on (3) to be durable.

Items 3 and 4 depend on a Redis instance being provisioned, which is a **cost
decision (~$10/month)** and is therefore listed as an external action rather
than silently implemented.

## Explicitly NOT recommended

Per the brief's own constraints and the evidence above: no Supabase, no Clerk,
no Pinecone, no Kubernetes, no Kafka. Additionally — **do not rebuild**
structured logging, Sentry, `.env.example`, API versioning or evidence
provenance. They exist, they are tested, and they are better than a generic
replacement would be.
