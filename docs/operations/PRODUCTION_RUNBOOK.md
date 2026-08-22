# Production Runbook

What actually exists, and what to do when it breaks. Audited against
`render.yaml` and the running service — not from memory.

---

## What is deployed

| service | plan | role |
|---|---|---|
| `ecoiq` (web) | starter | Django 5.2, gunicorn, WhiteNoise static |
| `ecoiq-db` | starter | PostgreSQL, 1 GB |

**That is the entire production estate.** One web service and one database.

### Redis and Celery are NOT deployed

They are **commented out** in `render.yaml`. This is worth stating plainly
because the code contains `@shared_task` definitions in
`backend_intelligence_engine/tasks.py`, and their presence makes it look like
a worker is running somewhere.

Nothing in the production request path calls `.delay()` or `.apply_async()`.
Tasks are invoked synchronously via `.apply()` from management commands when
they are needed at all.

**Do not claim Redis or Celery as production infrastructure.** If a feature
ever requires asynchronous execution, the blueprint entries are ready to
uncomment — until then, the honest description is that EcoIQ runs
synchronously.

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

There is no separate readiness endpoint. With one web service and synchronous
execution there is nothing a readiness probe would tell you that `/healthz/`
does not.

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

**Not yet in place:** an off-platform backup copy, and a documented restore
drill. Nobody has performed a restore. That is a real gap and it is recorded
here rather than assumed away.

---

## Known operational limits

Recorded because a runbook listing only procedures implies the rest is covered.

- **Single web instance.** No horizontal scaling, no zero-downtime deploy.
- **No off-platform backup**, and no tested restore.
- **No error tracking service.** Failures surface in Render logs only.
- **No uptime monitoring** beyond Render's own health check.
- **No staging environment.** Changes go from CI to production.
