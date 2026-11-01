# EcoIQ SaaS stack adoption — evidence-driven plan (2026-11-01)

## Intent

Make EcoIQ a commercially operable AI SaaS **without replacing** the currently
working evidence architecture, one-origin React/Django contract, or private
client-permission boundary.

This document is a roadmap and inventory, NOT a claim that all listed tools are
installed. Each new library needs a business feature, pinned release,
staging verification and regression tests before enabling in production.

## Actual codebase (main)

| Requested | State | Decision |
| --- | --- | --- |
| Django | 5.2.14 in requirements.txt | Keep stable and use modular apps |
| Django REST Framework | Installed and serves API v1/v2 | Keep; do **not** replace with Django Ninja just for trend |
| Next.js | **Not installed**; frontend/web uses Vite + React 18 | Keep Vite/React same-origin; SSR needs measured SEO justification |
| Celery and Redis | In requirements.txt | Keep; verify broker, workers, retries and monitoring in deployed environment |
| PostgreSQL | Production configured via DATABASE_URL; SQLite local/test | Keep; PostgreSQL is the truth, not search index |
| AI Gateway, pgvector | Existing modules; branch PR #373 adds proposed contracts | Reuse, don't create duplicate service |
| Stripe Python SDK | Already installed; ecoiq_commerce has billing and webhooks | Preserve live webhook URL and idempotent events |
| django-storages / S3 | Existing R2 optional private storage | Preserve signed access and per-project permissions |
| Wagtail | Previously removed from INSTALLED_APPS, cms tables potentially orphaned | Review schema/migrations on a staging DB **before** re-introducing |
| Unfold, Jazzmin | Neither installed | Choose **one** for pilot; never install both themes together |
| django-allauth | Not installed; custom session, mobile tokens and B2B API keys already exist | Design unified account migration/OAuth threat model before enabling |
| Strawberry GraphQL | Not installed | Defer; REST covers current consumers |
| Meilisearch/OpenSearch | Not installed for this use case | Defer until measured search need; enforce visibility BEFORE retrieving search hits |
| django-tenants | Not installed | Defer; shared PostgreSQL tables include historical tenant data |
| django-filter | Added by this PR (26.2) | Per-view on public companies; no global filters |
| Django Debug Toolbar | Not installed | Local-only, never production |
| pytest-django / Playwright | Existing suite uses Django TestCase, frontend/web Playwright is already present | Preserve unittest + Playwright; avoid changing test runner casually |
| Cookiecutter Django | Not used | Project scaffolding not appropriate for an existing monolith |

## Implementation order

**A. Now — testable, low-risk:**
1. Introduce django-filter only for `/api/v2/companies/` sector/country
   lookups; keep the original tokenised `q` query, permissions, ordering,
   pagination, evidence-null policy and N+1 protection.
2. Verify unchanged public API contract and archived-company visibility.
3. Keep this PR independent from draft PRs #373/#374.

**B. Admin pilot (separate PR and staging):**
- Choose Unfold *or* Jazzmin. For the intended Unfold: latest 0.110.0
  declares Python >=3.12, while current `.github/workflows/django.yml`
  pins Python 3.11.16. **No production/admin package change before
  interpreter compatibility is resolved and checked in CI.**
- Unfold admin model classes must inherit from `unfold.admin.ModelAdmin`;
  installing templates alone yields partially unstyled forms. Test staff
  login, custom permissions, changelists, change forms and admin actions.
- No full admin re-theme in the same PR as a Python major upgrade.

**C. Editorial CMS (separate PR):**
- Use Wagtail 7.4 LTS (documented Django 5.2 compatible) if a real editor
  needs rich publishing, with `/cms/` editor access and an explicitly scoped
  `/knowledge/` public route or API.
- First audit the existing CMS schema and migration history; restore only
  after a staging copy of PostgreSQL can migrate forward without data loss.
- Distinguish Wagtail editorial permissions from AI-generated draft review.
  AI drafts may never publish unsupervised.

**D. Auth/OAuth (separate PR):**
- Map the existing Django session, mobile_auth token, API key and billing-user
  links. Implement allauth only with explicit account-linking policy, CSRF,
  callback allowlist, safe recovery, and tests for duplicate identities.
- No parallel identity stores and no default social-login enablement.

**E. Enterprise SaaS scaling:**
- Tenant-by-tenant RBAC/ABAC and queryset proof before any tenant migrations.
  Avoid introducing django-tenants unless a real customer demands
  schema-level isolation; shared DB row scoping can be safer for MVP.
- Meilisearch/OpenSearch only when index freshness, ACL rechecks, source
  provenance and deletion propagation are testable.
- Stripe webhooks remain the sole source for paid entitlements.
- Add GraphQL only when a consumer proves REST cannot meet a concrete need.

## Acceptance commands

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test api.tests_v2_filtering api.tests_v2_search \
  api.tests_v2_evidence api.tests_v2_query_cost api.tests_frontend_contract
```

For a future admin/CMS milestone, also require a real staging PostgreSQL
migration check, regression tests of permissions, and authenticated browser
smoke tests. Never ship additional public endpoints merely to demonstrate a
new dependency.

## Rollback

For this PR, reverting the dependency, per-view filter class/configuration,
and app registration restores the old two in-method filters. No schema
migration, admin, auth, billing, frontend bundles or production settings
change.
