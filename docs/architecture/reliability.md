# Reliability Architecture

What EcoIQ currently guarantees, what it does not, and the reasoning behind the
choices. Measured against `origin/main` @ `6ac4a2c`. The capability-by-
capability audit is in `docs/platform-hardening-audit.md`.

## Shape

One Django process on Render (`--workers 1 --threads 4`, `start.sh`), one
PostgreSQL instance, WhiteNoise for static files, no workers deployed. The
React SPA is served by the same process from the same origin
(`core/spa.py`) — deliberately, so the session cookie never has to cross an
origin boundary.

Everything below follows from *one process, one database, no queue*.

## Health: two questions, two endpoints

| endpoint | question | touches | wired to |
|---|---|---|---|
| `/healthz/` | Is this process alive? | nothing | `render.yaml` `healthCheckPath` |
| `/readyz/` | Can it serve dependent functionality? | PostgreSQL; Redis when configured | nothing automatic |

The separation is the design, not an accident of naming.

**Liveness must not touch dependencies.** If it did, a brief database blip
would fail the check, Render would replace a web process that was perfectly
healthy, and the monitoring would have caused the outage instead of finding it.
`core/tests_health.py` pins this with `assertNumQueries(0)`.

**Readiness must not be wired to `healthCheckPath`.** Readiness failing means
*stop sending traffic*; it never means *kill the process*. Pointing Render's
restart decision at `/readyz/` would convert every database hiccup into a
restart loop. A test asserts the blueprint does not do this.

**A green `/healthz/` is not evidence the system is working.** That is the
cost of a correct liveness probe, and it is why the incident runbook opens with
a real query path rather than the health check.

### Why readiness checks Redis conditionally

`REDIS_URL` has a localhost default, so its truthiness proves nothing. Readiness
therefore keys off `settings.REDIS_CONFIGURED` — whether `REDIS_URL` was
*explicitly set in the environment*. No Redis is deployed today, so the check
reports `skipped` rather than failing a healthy service forever.

### What readiness refuses to say

The body carries check names and outcomes only. No hostname, port, database
name, user, connection string, driver message or traceback. Driver errors
routinely embed the host and user they failed against, and this endpoint
answers anonymously. Detail goes to the logs; the response gets a stable
category. Two tests assert specific credential fragments never appear in the body.

## Background processing — built, not deployed

Celery and Redis are fully configured (`ecoiq/celery.py`, settings, task
modules in `backend_intelligence_engine` and `good_agents`, bounded time limits
at `CELERY_TASK_SOFT_TIME_LIMIT = 270`). The Render Key Value and worker
services are **commented out in `render.yaml`**.

This is a cost decision (~$10/month Redis + ~$7/month worker) that was
deliberately not made silently. The consequence is honest and worth stating:
**anything long-running is currently happening inside a web request**, bounded
only by Render's request timeout.

Until a worker is deployed, do not describe any EcoIQ capability as
"continuous", "scheduled" or "overnight" — no scheduler is running.

## External calls

`backend_intelligence_engine/services/http_client.py` is the closest thing to a
shared policy: separate connect/read timeouts, exponential backoff, retries on
429/5xx/connection/timeout, and explicitly **no retry on 4xx** — a validation or
auth failure is not transient and retrying it just multiplies the failure.

Two known gaps, both recorded rather than fixed here:

- The policy is scoped to that one app. `ai_gateway` has its own fallback chain
  and typed exceptions but no shared timeout/retry contract.
- `fetch()` sets `follow_redirects=True` with **no SSRF validation**.
  `company_intelligence/services/url_safety.py` gates URLs at *registration*
  time, so a redirect to a private address after acceptance is not revalidated.

## Caching

`CACHES` is configured explicitly, in both directions.

| condition | backend | why |
|---|---|---|
| `REDIS_URL` set in the environment | `django.core.cache.backends.redis.RedisCache` | one shared cache across processes |
| not set | `LocMemCache`, `LOCATION='ecoiq-locmem-default'` | deliberate, documented local state |
| running tests | `LocMemCache`, always | a test run must never need an external service, or touch another process's cache |

**No new dependency.** Django 5.2 ships a Redis backend built on `redis-py`,
which this repository already depends on for Celery. `django-redis` would mean
a second Redis client and a second set of connection semantics for nothing this
needs.

### The signal is `REDIS_CONFIGURED`, never `REDIS_URL`

`REDIS_URL` has a localhost default, so it is *always* truthy. Selecting the
backend on its truthiness would pick Redis in production — where none is
deployed — and every cache read would fail against a healthy service. The cache
and `/readyz/` therefore key off the same `settings.REDIS_CONFIGURED`, so
"readiness enforces Redis" and "the cache is Redis" cannot disagree.

### Why LocMem is not enough for throttling

Every DRF throttle counts in the default cache. Under `LocMemCache` those
counters live in **one process's memory**, which means:

- they reset on every deploy, and on each `--max-requests 300` worker recycle,
  so effective limits are shorter than the configured ones; and
- raising `WEB_CONCURRENCY` above 1 multiplies every limit by the worker count,
  **with no error and no log line**.

On today's `--workers 1 --threads 4` the four threads share one process, so
rate limiting is not broken — it is fragile in a way that fails silently on a
configuration change. That is why production without Redis now prints a startup
warning rather than saying nothing.

**Durable rate limiting is a separate change.** This configuration is its
prerequisite; no throttle policy or rate was altered.

### Connection options

Bounded on purpose: `socket_connect_timeout` and `socket_timeout` at 2s so a
stalled Redis cannot hold a web thread open — a cache is an optimisation, and
waiting indefinitely for one inverts that. `retry_on_timeout` covers a dropped
idle connection; `health_check_interval=30` catches a silently-dead pooled
connection; `max_connections=24` sits above `--workers 1 --threads 4` plus a
worker's concurrency and far below any managed instance's ceiling. A `rediss://`
URL additionally sets `ssl_cert_reqs='required'`.

### Keys, TTL and invalidation

`KEY_PREFIX` is `ecoiq:<environment>`, so a staging service pointed at the same
instance cannot read or overwrite production's entries. Default `TIMEOUT` is
300s, stated rather than inherited.

**The release is deliberately NOT in the prefix.** Release-scoping sounds safer
and is actively wrong here: it would invalidate the whole cache on every deploy,
including every throttle counter — reintroducing the exact fragility this
configuration removes, as a side effect. A value whose correctness depends on a
version must carry that version **in its own key**.

Rules for anything cached from here on:

- **Tenant-sensitive values carry the organisation id.** A cache that can return
  one organisation's figure to another is a data breach with a short TTL.
- **Evidence- or analysis-derived values carry every version they depend on** —
  evidence version, formula version, methodology version, prompt/model version,
  and the analysis run or input hash where applicable. Serving a
  pre-recalculation score as current breaks the provenance guarantee more
  quietly than any outage.
- **Never cache an unknown as a confirmed value.** `null` means "not known",
  and a cached `null` that later reads as a real answer is the failure this
  platform exists to prevent.
- **No confidential user content, and no authentication or permission
  decisions** — the latter until there is a proven invalidation design, because
  a stale permission is a security bug, not a stale page.

**Invalidation:** prefer a short TTL and version-bearing keys over explicit
deletion. A key that includes the versions it depends on is invalidated by a
new version *existing* — nothing has to remember to delete it.

### Failure behaviour and rollback

With Redis configured there is **no fallback to local memory**: Django's
`RedisCache` raises on connection failure. Degrading quietly to per-process
memory during an outage would reintroduce the multiplied-limit bug at the
moment nobody is watching for it.

Without Redis, production starts on LocMem and logs a warning. Refusing to start
would be a self-inflicted outage on a service that runs this way today.

Rollback is removing `REDIS_URL` from the Render dashboard: the next deploy
selects LocMem and warns. No migration, no code change, no data to restore —
nothing in the cache is a source of truth.

### Provisioning — not done in this change

**No Render resource was provisioned by this PR.** Turning this on requires,
by hand:

1. Create a Render Key Value (Redis) instance in `oregon`, `ipAllowList: []`
   (internal only).
2. Set `REDIS_URL` on the `ecoiq` web service from that instance's connection
   string.
3. Redeploy; confirm the startup warning is gone and `/readyz/` reports
   `"redis": "ok"` rather than `"skipped"`.

Cost is a paid add-on — **treat any figure here as unverified until checked in
the Render dashboard**, since plan pricing changes and this repository cannot
observe it.

Environment variables involved, names only: `REDIS_URL`,
`ECOIQ_CACHE_ENVIRONMENT` (optional, defaults to `production`/`development`).

## Python runtime — one version, three declarations

| where | value | role |
|---|---|---|
| `.python-version` | `3.11.16` | the repository's canonical declaration |
| `render.yaml` → `PYTHON_VERSION` | `3.11.16` | sets the env var, which **overrides** the file |
| `.github/workflows/django.yml` | `3.11.16` | the interpreter every test actually runs on |

Render's precedence is `PYTHON_VERSION` env var → `.python-version` → a default
based on when the service was created. The blueprint therefore wins over the
file, which is exactly why they must agree.

**What went wrong before this was pinned.** `render.yaml` said `3.11.0`, CI
resolved a bare `"3.11"` to `3.11.16`, the Celery worker ran 3.11, and the web
service had **no `PYTHON_VERSION` at all** — so it fell through to Render's
default and ran **3.14.3**. Every dependency in production was installed and
exercised on an interpreter no test had ever seen, and nothing in the
repository could show it, because the declarations disagreed with each other
and nothing compared them.

`core/tests_python_runtime.py` now compares them, and fails with a diagnostic
naming each file and its value.

`runtime.txt` was **removed** rather than corrected. Render does not read it, so
it could drift indefinitely without ever taking effect — a declaration that
looks authoritative and is inert is worse than no declaration.

The test cannot see the env var actually set on a running service; that is
dashboard state. To check the live interpreter:

    render logs --resources <service-id> | grep -o 'python3\.[0-9]*'

## Reliability is not only availability

The failure this platform exists to prevent is **publishing something
untrue** — a score without evidence, an unknown rendered as a zero, a demo row
served as analysis. That failure is silent and looks exactly like normal
operation.

Which is why the gate is applied once, at the top
(`companies.eligibility.decide`), why unknown values stay `null` rather than
becoming neutral, and why the incident runbook classes an unevidenced published
score as SEV1 alongside a full outage.

Availability incidents announce themselves. Integrity incidents do not.
