# EcoIQ legacy Wagtail CMS — staged recovery assessment

## Scope

**This PR is a migration compatibility audit, not CMS activation.** Existing
`cms/models.py`, `cms/blocks.py`, `cms/wagtail_hooks.py` and their
`0001_initial` / `0002_reportlibrarypage_...` migrations are already
committed. Never run `wagtail start`, overwrite the migrations or
replace existing editorial records.

Official Wagtail compatibility documentation confirms **Wagtail 7.4 LTS**
supports **Django 5.2** and **Python 3.11**, EcoIQ's current major versions.
The audit pins `wagtail==7.4.3` as a standalone `requirements-wagtail-audit.txt`
dependency; production `requirements.txt` remains untouched.

## Stage A — nonproduction compatibility proof (this PR)

- `ecoiq.settings_wagtail_audit` enables Wagtail + existing `cms` models
  only under DEBUG or Django tests; normal settings and Render are unchanged.
- **No** Wagtail URL patterns, admin endpoint, redirect middleware, public
  page rendering, publishing tasks or site entries are enabled.
- Run `manage.py check` and `makemigrations --check --dry-run` with
  Wagtail audit settings on an empty/disposable SQLite database.
- Confirm the historical CMS migration dependencies exist in the supported
  Wagtail tree (including wagtailcore 0097 / wagtailimages 0027), apply
  migrations only to Django's disposable test DB, and verify tables created.
- CI tests prove production defaults do not expose `/cms/` or `/pages/`.

## Stage B — production **read-only inventory** before any real migration

Requires an authorized operator with database backup permissions. **Not
performed by this PR**.

1. Take a tested point-in-time backup/snapshot of the production PostgreSQL
   database and record its restore method. Use a restored, isolated staging
   copy with secrets rotated, no external emails, webhooks or job workers.
2. On the clone, inventory `django_migrations` entries for `cms`,
   `wagtailcore`, `wagtailimages` and `wagtailusers`; compare actual
   `cms_*` tables and Wagtail page counts to migration records.
3. Check for CMS page records, locale, revisions, redirects, collections,
   image/document renditions and dangling references. Verify Wagtail
   migration graph and plan on the clone. Never `--fake-initial`, drop
   tables, delete unrecognised migrations or overwrite history.
4. Produce an explicit **GO / NO-GO** decision based on integrity,
   permissions and recoverability.

## Stage C — restore editorial-only workflows (separate PR)

- Define an editor workspace separate from Django Admin, with precise URL,
  staff permissions, private media access and login tests.
- **Audit existing `cms/wagtail_hooks.py`: it currently surfaces top
  company rankings and counts using raw score fields.** These could
  wrongly imply verified scores; disable or rewrite such panels to use the
  canonical evidence publication gate before allowing editors to rely on
  them.
- Avoid route collisions: EcoIQ currently owns `/`, `/companies/`,
  `/reports/` and its React SPA catch-all. Wagtail must NOT claim them.
- AI-created articles and methodology remain **unpublished drafts** until
  an explicit authorized reviewer approves. Religious or investment
  conclusions must not be published automatically.

## Stage D — enable on production (future, explicit review)

Only after successful real PostgreSQL clone migration, all standard Django
tests, permission regression, media/privacy tests, 375px/768px/1280px browser
review and rollback rehearsal. Do not combine this stage with Unfold,
OAuth, Stripe billing changes, or Python upgrade.

## Repeatable isolated test commands

```bash
python3.11 -m venv .venv-wagtail-audit
. .venv-wagtail-audit/bin/activate
pip install -r requirements-wagtail-audit.txt
DEBUG=True DJANGO_SETTINGS_MODULE=ecoiq.settings_wagtail_audit \
  python manage.py check
DEBUG=True DJANGO_SETTINGS_MODULE=ecoiq.settings_wagtail_audit \
  python manage.py makemigrations --check --dry-run
DEBUG=True DJANGO_SETTINGS_MODULE=ecoiq.settings_wagtail_audit \
  python manage.py test core.tests_wagtail_cms_audit
```
