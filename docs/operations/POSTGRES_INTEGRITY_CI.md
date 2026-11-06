# PostgreSQL integrity and backup/restore CI

## Purpose

Production EcoIQ uses PostgreSQL with pgvector. The broad Django test suite
currently runs on SQLite, so a green default CI job alone cannot certify
PostgreSQL migrations, extension availability, or recoverability.

The [PostgreSQL integrity workflow](../../.github/workflows/postgres-integrity.yml)
adds a separate, disposable PostgreSQL 18 + pgvector service for changes to
models, migrations, Django settings, dependencies and the workflow itself.
It does not modify the existing 7,000+ test gate.

## Checks performed

1. Install the current application requirements with Python 3.11.16.
2. Run Django system and migration-drift checks against PostgreSQL.
3. Apply all migrations on an empty PostgreSQL 18 database, including
   `evidence_memory`'s pgvector extension migration.
4. Verify the `vector` extension exists and no migrations remain pending.
5. Add a clearly labelled **synthetic** marker to the disposable CI database.
6. Create a compressed custom-format archive with PostgreSQL 18 `pg_dump`.
7. Restore that archive via PostgreSQL 18 `pg_restore` into a **different**
   empty CI database, with `--exit-on-error`.
8. Verify the restored marker and non-empty `django_migrations` history and
   recheck for pending migrations on the restored database.
9. Run focused evidence-memory and provenance Django tests with PostgreSQL as
   the test backend.

The workflow uses the `pgvector/pgvector:0.8.7-pg18-bookworm` CI service image;
no PostgreSQL, Redis, cloud storage, or background worker is provisioned on Render.

## What this does **not** prove

- A real production backup exists, is recent, is encrypted, and is stored away
  from the primary database.
- A production-sized restore can meet a stated RTO/RPO.
- Render credentials, secrets, network connections or the current live
  PostgreSQL cluster are configured correctly.
- Postgres performance on actual customer or geological datasets is sufficient.
- The entire Django suite has run on PostgreSQL (the dedicated job uses focused
  tests; the existing comprehensive suite still uses SQLite).

Those require a separately approved operations drill: take a real backup under
production access controls, restore it to an isolated environment, verify data
and permissions, time the operation, then securely destroy the isolated copy.
**Do not upload production dumps to GitHub Actions or commit them to Git.**

## Follow-up priorities

- Configure durable private R2/S3-compatible media storage on Render before
  accepting persistent uploads. Never swap storage without verifying every
  existing file and the restore/migration path.
- Add an independently tested PostgreSQL backup retention and encrypted
  restore policy with named RPO/RTO values.
- Expand typing in small audited surfaces (no blanket `type: ignore`).
- Add repeatable dependency vulnerability checks and a reviewed lock strategy.
- Confirm SMTP and Redis/cache topology in the intended Render workspace;
  local CI warnings are not evidence of the live configuration.
