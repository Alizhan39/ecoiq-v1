# Deploying EcoIQ on Render

EcoIQ deploys to Render from a **Blueprint** (`render.yaml`). The most important
rule is below — it caused a production outage once and must not regress.

## ⛔ The build must never touch the database

Render's **build environment has no access to the private database network.**
The database's internal hostname (`dpg-…-a`) only resolves at **runtime**, so any
database command during the build fails with:

```
django.db.utils.OperationalError: could not translate host name
"dpg-…-a" to address: Name or service not known
```

Therefore **`build.sh` must stay database-free.** It only:
1. `pip install -r requirements.txt`
2. `python manage.py compilemessages`
3. `python manage.py collectstatic --no-input`

Never add `migrate`, `bootstrap_*`, or any `seed_*` command to `build.sh`.

## Where database work runs instead (at runtime)

| Phase | Script | Runs | Purpose |
|-------|--------|------|---------|
| Build | `build.sh` | build env (no DB) | deps, translations, static files |
| Pre-Deploy | `predeploy.sh` | runtime net (DB resolves) | `migrate` + all seeds, **once per deploy** |
| Start | `start.sh` | runtime net (DB resolves) | best-effort `migrate` safety net, then Gunicorn |

Both `predeploy.sh` and `start.sh` are **best-effort**: if the database is
temporarily unavailable they log a warning and exit 0 / start the server anyway,
so **a database hiccup can never block a deploy or stop the web service booting.**
The app has no import-time database access, so Gunicorn serves even with the DB down;
schema/data catch up automatically on the next start once the DB is back.

## Render service configuration (must match `render.yaml`)

If the service is driven by the Blueprint, these are applied automatically. If any
were ever set **manually in the Render dashboard**, the dashboard value overrides
`render.yaml` — set them to exactly:

- **Build Command:** `pip install -r requirements.txt && ./build.sh`
- **Pre-Deploy Command:** `./predeploy.sh`
- **Start Command:** `./start.sh`

`preDeployCommand` requires a paid instance type (this service runs on **Starter**).

## Required environment variables (Render dashboard)

Set automatically by the Blueprint: `DATABASE_URL` (from `ecoiq-db`),
`DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL`,
`DEBUG=False`, `DJANGO_SETTINGS_MODULE`, `PYTHON_VERSION`.

Set **manually** (never committed): `ANTHROPIC_API_KEY`, `COMPANIES_HOUSE_API_KEY`.

## Post-deploy smoke check

```
GET /                      → 200  (homepage)
GET /companies/            → 200  (rankings)
GET /companies/<slug>/     → 200  (company profile)
GET /decisions/            → 200  (QDF Stewardship Dashboard)
GET /decisions/<slug>/     → 200  (QDF Decision Engine)
```

## Scripts are committed executable

`build.sh`, `predeploy.sh`, and `start.sh` are tracked with mode `100755`. If you
add another script, `git update-index --chmod=+x <file>` so Render can run it.
