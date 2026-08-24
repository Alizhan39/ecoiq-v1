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

`MEDIA_ROOT` is on the web service's disk. Render's PostgreSQL backup does
**not** cover it, and a service replacement does not preserve it. Any uploaded
evidence document is therefore currently at risk in a way the database is not.

This is a real gap. It is not fixed here because fixing it properly means
choosing an object store (S3/R2 + `django-storages`), which is a cost and
architecture decision, not a runbook entry.

---

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
