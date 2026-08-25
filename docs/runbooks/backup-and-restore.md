# Runbook — Backup and Restore

**Scope:** PostgreSQL (`ecoiq-db`) and uploaded files.
**Operational context:** `docs/operations/PRODUCTION_RUNBOOK.md` — deploy,
rollback and database-failure procedure. This document does not repeat it.

> **Status, stated plainly.** Render takes automatic PostgreSQL backups. There
> is **no off-platform copy**, and **no restore has ever been performed or
> tested**. Nothing below claims otherwise. The verification section exists to
> be filled in by whoever runs the first drill, and is empty on purpose.

---

## What exists today

| | value | evidence |
|---|---|---|
| Mechanism | Render automatic daily PostgreSQL backup | `render.yaml` — `databases: ecoiq-db`, `plan: starter` |
| Retention | 7 days | Render starter plan |
| Encryption at rest | Render-managed | Render platform default |
| Off-platform copy | **none** | no export job in `render.yaml` or `.github/workflows/` |
| Restore ever tested | **no** | `PRODUCTION_RUNBOOK.md:141-156` |
| Uploaded-file backup | **none — see below** | no object storage configured |

### Uploaded files

`MEDIA_ROOT` was the web service's own disk, which Render replaces on every
deploy. Render's PostgreSQL backup does not cover it, so an uploaded evidence
document survived until the next release while its database row survived
forever — a reference to a file that no longer exists, which the application
reads as "the document is on file".

**Measured on production, 2026-08-25:** `MEDIA_ROOT` did not exist, **0 files,
0 bytes, 0 database references** across all six upload fields
(`core.Assessment`, `leads.ReviewRequest`, `league.Evidence`,
`audit.AuditSession`, `audit.AIAnalysisJob`,
`companies.CompanyGuidanceVideo`). Nothing had been lost because nothing had
been uploaded. There was no migration to perform and none was invented.

**Code status: ready, not enabled.** `MEDIA_STORAGE_BACKEND=r2` switches the
default storage to private Cloudflare R2 with short-lived presigned reads; the
filesystem remains the default everywhere else. If `r2` is selected and any
required variable is missing, settings raise rather than start — falling back
to the ephemeral disk silently is the failure being fixed.

**Blocked on one account action.** R2 is not enabled on the Cloudflare account
(`wrangler r2 bucket list` → error 10042, *"Please enable R2 through the
Cloudflare Dashboard"*), and the current OAuth token carries no `r2` scope.
Enabling R2 requires completing a checkout flow in the dashboard, which is an
account-owner action. Until then uploads still land on the ephemeral disk.

Verify state at any time — before a cutover, after one, or when a row might
point at nothing:

    python manage.py reconcile_media                    # report only
    python manage.py reconcile_media --migrate          # copy into the configured storage

It reports `referenced_and_present`, `referenced_but_missing`,
`present_but_unreferenced`, `copied` and `failed`. It never deletes a source
object, never rewrites a database reference, skips objects already present
(so re-running is a no-op), and prints no file content.

## Objectives — proposed, not yet ratified

These are targets to agree with the owner, not measured guarantees. They are
written as proposals so the first drill has something to test against.

| | proposed | rationale |
|---|---|---|
| **RPO** (max acceptable data loss) | 24 h | daily snapshot cadence; anything tighter needs PITR, a paid tier |
| **RTO** (max acceptable downtime) | 4 h | single instance, no failover, manual restore |
| **Owner** | *unassigned* | must be a named person before this is a real objective |

An RPO of 24 h means up to a full day of evidence ingestion, analyst
declarations and human-review decisions could be lost. Whether that is
acceptable is a **product** decision about the provenance guarantees EcoIQ
makes, not an infrastructure preference.

---

## Restore drill — procedure

Run against a **scratch database**, never production. Budget 60–90 minutes.

1. **Snapshot the current state.** In Render → `ecoiq-db` → Backups, note the
   most recent backup's timestamp and id.
2. **Create a scratch database.** Render → New → PostgreSQL, same region
   (`oregon`), starter plan. Name it `ecoiq-db-restoretest`.
3. **Restore into it** from the chosen backup, using Render's restore flow.
4. **Point a local checkout at the restored copy** — never a deployed service:

   ```
   export DATABASE_URL='<external connection string for ecoiq-db-restoretest>'
   python manage.py check
   python manage.py showmigrations | grep -c '\[X\]'
   ```

5. **Verify integrity against the evidence contract**, not just row counts. The
   point of this system is that unknown values stay unknown, so a restore that
   silently defaulted them would be worse than a failed restore:

   ```
   python manage.py shell -c "
   from companies.models import Company
   print('companies:', Company.objects.count())
   from companies.eligibility import decide
   print('publishable:', sum(1 for c in Company.objects.all()[:50] if decide(c).publishable))
   "
   ```

   Compare both numbers against production. A restored database that reports
   *more* publishable assessments than production has lost provenance.
6. **Record the result** in the table below.
7. **Delete the scratch database.** It holds a full copy of production data;
   leaving it running doubles the attack surface for no benefit.

## Restore verification log

Empty until a drill is actually run. Do not pre-fill.

| date | backup id | restored by | duration | row counts match | publishable counts match | outcome |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | *no drill has been performed* |

---

## Manual actions required (cannot be done in code)

These need Render dashboard access and, in two cases, money. They are listed so
the gap is actionable rather than merely known.

1. **Assign an owner** for backup/restore. Without a name, the RPO/RTO above
   are aspirations.
2. **Run the first restore drill** using the procedure above, and fill in the log.
3. **Decide on off-platform backup.** Render's 7-day retention does not survive
   account-level loss. A weekly `pg_dump` to external object storage is the
   smallest sufficient answer.
4. **Decide on uploaded-file durability** — object storage, or an explicit
   accepted-risk statement that uploaded documents are not backed up.
5. **Consider point-in-time recovery** if a 24 h RPO proves unacceptable. This
   requires a paid Render plan tier.
