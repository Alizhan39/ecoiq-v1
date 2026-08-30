# Production Runbook

What actually exists, and what to do when it breaks.

Audited against the RUNNING estate, not against `render.yaml`. That distinction
is the reason this document was wrong for four days: services were created by
hand in the dashboard, the blueprint never learned about them, and every claim
here that cited the blueprint as evidence inherited its blind spot.

---

## What is deployed

Audited against the live estate with the Render CLI on 2026-08-28, not against
`render.yaml` — the blueprint and the running services had drifted apart, and
this document had drifted with the blueprint.

| service | type | state | role |
|---|---|---|---|
| `ecoiq` | web | running | Django 5.2, gunicorn, WhiteNoise static |
| `ecoiq-db` | postgres | running | PostgreSQL, 1 GB |
| `ecoiq-keyvalue` | key value | running | Redis — Django cache AND Celery broker/result backend |
| `ecoiq-celery-worker` | background worker | running | `celery -A ecoiq worker --concurrency=2` |
| `ecoiq-daily-yfinance` | cron | **suspended** | — |
| `ecoiq-ml-retrain` | cron | **suspended** | — |
| `ecoiq-rss-signals` | cron | **suspended** | — |
| `ecoiq-weekly-full-ingest` | cron | **suspended** | — |

### Redis and Celery ARE deployed — this document used to say they were not

Until 2026-08-28 this section read "Redis and Celery are NOT deployed" and
"that is the entire production estate. One web service and one database." Both
statements were false. `ecoiq-keyvalue` was created on 2026-08-24 and
`ecoiq-celery-worker` alongside it, by hand in the Render dashboard rather than
through the blueprint — so `render.yaml`, which still carries them as commented
out, never learned about them, and every document that cited `render.yaml` as
evidence inherited the error.

Measured, not assumed:

```
$ curl -s https://ecoiq.onrender.com/readyz/
{"status": "ready", "checks": {"database": "ok", "redis": "ok"}}

$ render logs -r srv-da69jd2jnfac73a8rceg
celery@srv-da69jd2jnfac73a8rceg-... ready.
Connected to redis://red-da67e6uk1f9s739a9g5g:6379//
concurrency: 2
```

`redis: ok` in the readiness probe is only reported when `REDIS_URL` is set
explicitly in the environment (`settings.REDIS_CONFIGURED`), so the web service
is genuinely configured against it, not falling back to the localhost default.

**What this changes for an operator.** The production cache is Redis, not a
per-process LocMemCache. That means it is SHARED — across threads, across
worker recycles, and across deploys until the TTL expires. A cached response is
not a per-process convenience here; whatever is written to a cache key is what
every subsequent visitor gets. See `companies/throttle.py`, whose keys carry
the audience for exactly this reason.

DRF throttle counters live there too, so they now survive a deploy and a
`--max-requests 300` recycle instead of resetting.

### Nothing runs on a schedule

This part of the old text was right, and stays right.

- There is **no Celery beat schedule** anywhere in the codebase — grep for
  `beat_schedule` or `crontab(` and you will find nothing.
- All four cron jobs are **suspended**.
- Nothing in the request path calls `.delay()` or `.apply_async()`. The two
  call sites are `backend_intelligence_engine/admin.py` (a staff admin action)
  and `backend_intelligence_engine/tasks.py`.

So the worker is running, connected and idle: it will execute a task if one is
ever enqueued, and nothing enqueues one on its own. **"Continuous monitoring"
remains a claim EcoIQ must not make** — being able to run a task is not the
same as running it on a schedule, and the pricing page is correct to say
monitoring is "scheduler-ready rather than running".

### Two open decisions for the owner

Recorded here rather than acted on, because both are cost and product calls:

1. A Key Value instance and a background worker are being paid for while
   nothing schedules work. Either that is deliberate headroom, or one or both
   should be suspended.
2. `render.yaml` does not describe the running estate, and **cannot currently
   sync at all** — which is very likely why the estate drifted in the first
   place. Measured:

   ```
   $ render blueprints validate render.yaml
   {"errors": [{"path": "databases[0].plan",
     "error": "Legacy Postgres plans, including 'starter', are no longer
               supported for new databases."}],
    "valid": false}
   ```

   So the blueprint is presently decorative: no change in it can be applied,
   whatever it contains. Creating a Key Value instance and a worker by hand was
   not someone bypassing the blueprint — it was the only way to add anything.

   Two further mismatches, verified against the live plans:

   | | `render.yaml` | live |
   |---|---|---|
   | `ecoiq` web | `starter` | `standard` |
   | `ecoiq-db` | `starter` (retired) | `basic_256mb` |

   **Sequencing matters here.** PR #220 fixes exactly these two lines and makes
   the blueprint valid again. The moment it merges, a sync becomes possible
   against a file that still does not declare `ecoiq-keyvalue`, the worker or
   the four cron jobs — and the web plan line, uncorrected, would have
   attempted to downgrade production from Standard to Starter. That is the
   order to think about: make the blueprint describe the estate BEFORE making
   the blueprint able to act on it, or at least establish what a sync does to
   services it does not declare. This runbook does not assert what Render does
   with them, because that has not been tested here.

---

## Deploy

Merging to `main` triggers a Render deploy.

```
build.sh       → install deps, collectstatic, build frontend assets
predeploy.sh   → python manage.py migrate
start.sh       → gunicorn
```

Migrations run in `preDeployCommand`, which means **they run before the new
code serves traffic**. A failing migration fails the deploy rather than leaving
a half-migrated database serving requests.

### Verify a deploy

```bash
curl -s -o /dev/null -w '%{http_code}' https://ecoiq.uk/healthz/     # expect 200
curl -s https://ecoiq.uk/api/v2/platform/ | head -c 200
```

Then confirm containment still holds — the check that matters most:

```bash
curl -s https://ecoiq.uk/api/v2/companies/ | grep -c '"ecoiq_score": null'
curl -s https://ecoiq.uk/league/ | grep -c '"score":'      # must be 0
```

---

## Health checks

`/healthz/` returns `200 ok`. It is **exempt from `SECURE_SSL_REDIRECT`** on
purpose: Render probes the internal port, the request never passes the edge
that sets `X-Forwarded-Proto`, and `SecurityMiddleware` would answer `301`.
Render reads a 301 as unhealthy and would replace a perfectly healthy process.

**Do not "fix" that exemption.** It is a correctness requirement.

`/readyz/` returns JSON and checks PostgreSQL (and Redis, only when
`REDIS_URL` is explicitly set — it is not, in production). It is **not** wired
to `healthCheckPath` and must not be: readiness failing means stop sending
traffic, never restart the process.

Use it during an incident. `/healthz/` `200` with `/readyz/` `503` means the
process is fine and a dependency is not — restarting fixes nothing.

    curl -s https://ecoiq.uk/readyz/

It reports check names and outcomes only: no host, port, credential or
traceback. See `docs/architecture/reliability.md`.

---

## Rollback

```bash
git revert -m 1 <merge-sha>
git push origin main
```

Render redeploys automatically.

**For a migration**, revert the code first, then step the database back:

```bash
python manage.py migrate <app> <previous-number>
```

**Before rolling back past a nullability migration**, read
`docs/product/D4_FIELD_CLASSIFICATION.md`. Reversing `companies.0011` or
`league.0007` is safe *while no NULLs exist*; once real unknowns are written,
reversing requires inventing values for them — which is a product decision, not
a migration.

---

## Database failure

1. Check the Render dashboard for `ecoiq-db`.
2. `/healthz/` will still answer `200` — it does not touch the database. That
   is deliberate (it must not fail on a slow query) and means **a green health
   check is not proof the database is up**.
3. Confirm with a query path: `curl -s https://ecoiq.uk/api/v2/companies/`.
4. Restore from Render's automatic daily backups (starter plan retains 7 days).

**There is no read replica and no failover.** A database outage is a full
outage. This is a known limit of the current plan, not an oversight.

---

## Worker failure

There are no workers. If something appears to need one, it is running
synchronously in a request or a management command — find it there.

---

## Environment variables

Set in the Render blueprint; `sync: false` entries are set by hand in the
dashboard.

| variable | purpose |
|---|---|
| `DJANGO_SECRET_KEY` | session and CSRF signing |
| `DATABASE_URL` | from `ecoiq-db` |
| `ANTHROPIC_API_KEY` | ingestion and AI features; absent means those features refuse rather than fabricate |
| `DEBUG` | never true in production |

Secrets are scanned on every commit by Gitleaks. `.env` is gitignored and stays
that way.

---

## Backups

Render's automatic PostgreSQL backups, 7-day retention on the starter plan.

Point-in-time recovery is also available (window opens `2026-08-21T12:16:54Z`),
and one logical export is retained from the restore drill.

**A restore drill was performed on 2026-08-25 and passed:** a fresh logical
export restored into an isolated local PostgreSQL 18 instance in 1 second with
zero errors, matching production exactly — 374 tables, 30,258 rows, 698 foreign
keys, 1,420 indexes, 378 migration rows, and 873 constraints re-validated with
0 failures. Measured **RPO ~0–5 min** (via PITR) and **RTO ~15–20 min** at the
current size.

**Still not in place:** an off-platform backup copy, and a rehearsed
Render-hosted recovery cutover. The drill restored to an isolated local
instance, which proves the data — not the cutover. Exports are also manual;
nothing schedules one.

The full procedure, the verification log and the limitations are in
`docs/runbooks/backup-and-restore.md`. Uploaded files now live in Cloudflare R2
rather than `MEDIA_ROOT` — see the same document.

---

## Known operational limits

Recorded because a runbook listing only procedures implies the rest is covered.

- **Single web instance.** No horizontal scaling, no zero-downtime deploy.
- **No off-platform backup.** The restore path itself is tested (drill passed
  2026-08-25), but PITR, snapshots and the retained export all live in one
  Render account, and a Render-hosted cutover has never been rehearsed.
- **Error tracking integration is complete** (`core/sentry_setup.py`,
  `sentry-sdk` pinned), and `SENTRY_DSN` is reported as configured in the
  Render dashboard. The DSN is intentionally NOT in `render.yaml`: it is a
  dashboard-managed secret, so its absence from the blueprint is not evidence
  that it is unset. **Not yet verified operationally:** that sanitised events
  actually arrive in Sentry, with PII scrubbing behaving as
  `core/sentry_setup.py` intends. Confirm that in the Sentry UI — repository
  inspection cannot establish it.
- **No uptime monitoring** beyond Render's own health check.
- **No staging environment.** Changes go from CI to production.
