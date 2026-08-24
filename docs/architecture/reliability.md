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

## Caching — the one that fails silently

**`CACHES` is never configured.** Django falls back to per-process
`LocMemCache`, and every DRF throttle stores its counters there.

On today's configuration (`--workers 1`) the four threads share one process, so
rate limiting is **not broken**. But:

- counters reset on deploy and on each `--max-requests 300` worker recycle, so
  effective limits are shorter than configured; and
- raising `WEB_CONCURRENCY` above 1 multiplies every limit by the worker count,
  with no error and no log line.

That silence is the problem. It is the highest-leverage remaining fix, and it
is the prerequisite for Redis being useful for anything else.

When a shared cache is added, keys must carry organisation scope plus evidence,
formula and methodology versions. A cache that can return one organisation's
figure to another, or serve a pre-recalculation score as current, breaks the
provenance guarantee more quietly than any outage.

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
