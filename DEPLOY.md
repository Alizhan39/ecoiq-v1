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

Set **manually** (never committed): `ANTHROPIC_API_KEY`, `COMPANIES_HOUSE_API_KEY`,
and the Stripe variables below.

## Stripe billing

Merchant of record: **Stoke Share Ltd**, trading as EcoIQ.

The integration ships **inert**. `ECOIQ_BILLING_PROVIDER=none` and blank Stripe
keys are a safe, supported state: `/billing/plans/` renders with checkout
disabled, and `/billing/webhook/` refuses all traffic rather than trusting
payloads it cannot verify. Nothing below happens by accident.

### Environment variables (all `sync: false` — dashboard only)

| Variable | Purpose |
| --- | --- |
| `STRIPE_SECRET_KEY` | `sk_test_…` during rollout. Secret. |
| `STRIPE_PUBLISHABLE_KEY` | `pk_test_…`. Public by design. |
| `STRIPE_WEBHOOK_SECRET` | `whsec_…`, **per endpoint**. Secret. |
| `STRIPE_PRICE_STARTER_MONTHLY` | `price_…` |
| `STRIPE_PRICE_STARTER_YEARLY` | `price_…` |
| `STRIPE_PRICE_PRO_MONTHLY` | `price_…` |
| `STRIPE_PRICE_PRO_YEARLY` | `price_…` |
| `ECOIQ_BILLING_PROVIDER` | `none` → `stripe` when ready |
| `STRIPE_AUTOMATIC_TAX_ENABLED` | **Leave `false`** — see Stripe Tax below |
| `STRIPE_TAX_ID_COLLECTION_ENABLED` | Leave `false` |
| `STRIPE_LIVE_MODE_ALLOWED` | Leave `false` — see Going live below |

### Webhook endpoint

Register in **Stripe Dashboard → Developers → Webhooks**:

```
https://ecoiq.uk/billing/webhook/
```

Subscribe to exactly these nine events:

```
checkout.session.completed
invoice.paid
invoice.payment_failed
customer.subscription.created
customer.subscription.updated
customer.subscription.deleted
charge.refunded
charge.dispute.created
charge.dispute.closed
```

Copy that endpoint's signing secret into `STRIPE_WEBHOOK_SECRET`. Each endpoint
has its own secret — the test endpoint, the live endpoint and the local
`stripe listen` CLI all differ. A mismatched secret makes every delivery 400.

**Do not change the `/billing/webhook/` path.** It is configured by hand in the
Stripe Dashboard, so a rename breaks payment provisioning in production with no
local test failure to warn you.

### Mapping prices to plans

Stripe prices grant nothing until they are mapped to an `ecoiq_commerce.Plan`.
After setting the price variables, run once in the Render shell:

```bash
python manage.py sync_stripe_prices
```

It matches `Plan.key` against `{tier}-{interval}` (`starter-monthly`,
`pro-yearly`, …) and reports anything it could not map. An unmapped price still
records the subscription with its Stripe ids but grants **no** entitlements —
the webhook logs this rather than guessing. One-time assessment/consulting
prices are set directly on their `Plan.stripe_price_id` in the admin.

### Stripe Tax

Deliberately **disabled**. `automatic_tax` is only attached to Checkout sessions
when `STRIPE_AUTOMATIC_TAX_ENABLED=true`, and it must stay `false` until Stoke
Share Ltd's relevant tax registrations are confirmed and entered in **Stripe
Dashboard → Settings → Tax**. Enabling it before then puts incorrect tax on real
customer invoices. Turning it on later is a configuration change only — no code
change and no deploy are required.

### Going live

Live mode is a two-step act by design. Setting `STRIPE_SECRET_KEY` to an
`sk_live_…` key while `STRIPE_LIVE_MODE_ALLOWED` is false makes Django **refuse
to start** with an explicit error, so a live key can never be enabled by simply
pasting it in. Before flipping the latch, confirm: live API keys set, a live
webhook endpoint registered with its own signing secret, live price ids set and
synced, tax registrations resolved, and the Customer Portal configured in the
live account.

## Post-deploy smoke check

```
GET /                      → 200  (homepage)
GET /companies/            → 200  (rankings)
GET /companies/<slug>/     → 200  (company profile)
GET /decisions/            → 200  (QDF Stewardship Dashboard)
GET /decisions/<slug>/     → 200  (QDF Decision Engine)
GET /billing/plans/        → 200  (self-serve plans; checkout hidden if unconfigured)
GET /billing/manage/       → 302 → /login/  (auth required)
POST /billing/webhook/     → 400  (no valid Stripe signature — this is correct)
```

## Scripts are committed executable

`build.sh`, `predeploy.sh`, and `start.sh` are tracked with mode `100755`. If you
add another script, `git update-index --chmod=+x <file>` so Render can run it.
