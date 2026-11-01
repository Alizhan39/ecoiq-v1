# EcoIQ Unfold staging pilot (not a production deployment)

## Why separate settings

Current Render / GitHub CI is Python **3.11.16**, Django **5.2.14**.
Django Unfold **0.110.0** (13 Oct 2026) requires Python >=3.12.
Do not bump the production runtime or introduce a legacy theme package to
solve a cosmetic UI feature. The pilot uses Python 3.12 and a separate
`DJANGO_SETTINGS_MODULE=ecoiq.settings_unfold_preview`.

Production behavior is unchanged: `ecoiq.settings` is the default; no
Unfold app, no dependency, no admin routing changes, no migrations.

## What is actually implemented

- `requirements-unfold-preview.txt` is **CI/staging only**.
- Preview module adds `unfold` before `django.contrib.admin`, and fails
  closed for Python <3.12 and production execution.
- `ecoiq_commerce.FeatureAdmin` conditionally inherits from
  `unfold.admin.ModelAdmin` only under preview settings. Existing Feature
  admin functionality (search, lists, permissions) is unchanged otherwise.
- Test anonymous/staff permissions and render index, feature list and
  add forms. Other installed model admins are not yet migrated to Unfold,
  so some pages will remain partially unstyled.

## How to check on Python 3.12 (isolated local environment)

```bash
python3.12 -m venv .venv-unfold
. .venv-unfold/bin/activate
pip install -r requirements-unfold-preview.txt
DEBUG=True DJANGO_SETTINGS_MODULE=ecoiq.settings_unfold_preview \
  python manage.py check
DEBUG=True DJANGO_SETTINGS_MODULE=ecoiq.settings_unfold_preview \
  python manage.py test ecoiq_commerce.tests_unfold_preview
```

Never run migrations against production for this trial. On a disposable
staging DB you can additionally test the admin UI at /admin/ with a temporary
staff account. Do not use production credentials.

## Before a production admin migration

1. Prove Python 3.12 compatibility across the full EcoIQ suite, all native
   scientific dependencies and the Render build memory/runtime.
2. Audit **every** registered Django ModelAdmin, custom admin template,
   inlines, action and form, especially billing/Stripe and evidence review.
3. Migrate in narrow audited batches with permission and before/after
   screenshots, using only one chosen admin theme.
4. Review release security/maintenance status before final production pin.
5. Change Render PYTHON_VERSION and `.python-version` together only in a
   dedicated deployment PR. Roll back if incompatible.

Wagtail and allauth remain separate projects. Wagtail was removed from
INSTALLED_APPS and schema must be audited on a staging PostgreSQL copy;
allauth must reconcile session/mobile/API-key identities before enabling.
