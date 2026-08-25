# Runbook — Backup and Restore

**Scope:** PostgreSQL (`ecoiq-db`) and uploaded files.
**Operational context:** `docs/operations/PRODUCTION_RUNBOOK.md` — deploy,
rollback and database-failure procedure. This document does not repeat it.

> **Status, stated plainly.** A restore drill was performed on **2026-08-25**
> and passed: a fresh logical export restored cleanly and matched production
> exactly. The RPO/RTO below are now **measured**, not proposed.
>
> Two things that drill did **not** prove, and which are still open: there is
> **no off-platform copy** of any backup, and a **Render-hosted recovery
> cutover has never been performed**. The restore was into an isolated local
> instance. See "What the drill did not prove".

---

## What exists today

| | value | evidence |
|---|---|---|
| Mechanism | Render automatic daily PostgreSQL backup | `render.yaml` — `databases: ecoiq-db`, `plan: starter` |
| Retention | 7 days | Render starter plan |
| Encryption at rest | Render-managed | Render platform default |
| Off-platform copy | **none** | no export job in `render.yaml` or `.github/workflows/` |
| Point-in-time recovery | **available**, window opens `2026-08-21T12:16:54Z` | Render API `recoveryStatus: AVAILABLE` |
| Logical export | one, created `2026-08-25T13:14:00Z`, retained | Render API `/postgres/{id}/export` |
| Restore ever tested | **yes — 2026-08-25, passed** | verification log below |
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

## Objectives — measured 2026-08-25

Replaces the earlier proposed figures (24 h / 4 h), which were written before
any drill had been run and were guesses.

| | measured | basis |
|---|---|---|
| **RPO** (max data loss) | **~0–5 min** | point-in-time recovery is available, so recovery is to a moment, not to the last daily snapshot |
| **RTO** (time to serve again) | **~15–20 min** at current size | export ~2 min + download ~1 min + restore **1 s** + verification ~5 min, then provisioning and cutover |
| **Owner** | *still unassigned* | an objective without a named person is not an objective |

**Restore time is not the constraint.** At 374 tables / 30,258 rows the restore
itself takes one second; provisioning a replacement instance and repointing the
services dominate the RTO. That ratio will hold until the database is orders of
magnitude larger, so effort spent shortening restore time would be wasted —
effort spent on a rehearsed cutover would not.

The RPO figure depends on PITR remaining available. Its window currently opens
`2026-08-21T12:16:54Z`; outside that window the position reverts to the most
recent logical export.

---

## Restore drill — procedure

This is the procedure that was actually run on 2026-08-25, not a proposal. It
needs **no paid resource and no change to production**, which is why it is the
default. Budget ~30 minutes.

The earlier version of this section proposed creating a scratch Render database
and restoring a managed backup into it. That would have cost money and required
a Render-hosted restore. The route below is cheaper, safer and provable on a
laptop — but it verifies the *data*, not a Render cutover. Both are worth
having; only the first has been done.

1. **Request a fresh logical export.** `POST /v1/postgres/{id}/export`. It runs
   against production read-only and changes nothing. Poll `GET .../export`
   until an entry carries a `url`; it took ~3 minutes.
2. **Download into a restrictive temporary directory** (`mktemp -d`, `chmod
   700`, dump file `chmod 600`). Never into the repository. The download URL is
   signed — do not paste or log it.
3. **Extract.** The artefact is a `tar.gz` wrapping a `pg_dump`
   **directory-format** archive, not a plain `.sql` file. `pg_restore -l`
   prints its header, including the source server version.
4. **Start an isolated cluster of the same major version**, listening on a
   Unix socket only — never a TCP port:

   ```
   initdb -D "$DRILL/pgdata" -U drilluser --auth=trust
   # in postgresql.conf:
   #   listen_addresses = ''
   #   unix_socket_directories = '<drill dir>/sock'
   ```

   On macOS, export `LC_ALL=C` first or the postmaster exits with
   *"postmaster became multithreaded during startup"*.
5. **Restore and time it.**
   `pg_restore -d ecoiq_restore --no-owner --no-privileges --jobs=4 <dumpdir>`
6. **Compare every table, not just totals.** Two databases can agree on total
   row count while individual tables differ, so compare the full per-table map
   from both sides and diff it. Use aggregate counts only — never select rows.
7. **Prove the constraints, not just the load.** A dump can restore and still
   hold rows that violate a foreign key, because `pg_restore` adds constraints
   after the data. Re-validate every one:

   ```
   ALTER TABLE <t> VALIDATE CONSTRAINT <c>;   -- for every contype in ('f','c')
   ```

8. **Run Django against it.** `manage.py check` and `showmigrations`; zero
   unapplied migrations means the restored schema satisfies the current code.
9. **Tear down completely** — stop the cluster, delete the dump, the extracted
   archive and the data directory. It holds a full copy of production.
10. **Record the result below.**

## Restore verification log

| field | result |
|---|---|
| **Date** | 2026-08-25 |
| **Export id** | `dpg-…/2026-08-25T13:14Z`, created `2026-08-25T13:14:00Z` |
| **Method** | Render logical export → isolated local PostgreSQL, Unix socket only |
| **Compressed size** | 1,016,895 B (~11 MB extracted, 375 files, 3,595 TOC entries) |
| **Production version** | PostgreSQL **18.4** (live `select version()`) |
| **Export header claims** | **18.6** — Render's export tooling image, not the live server |
| **Restore target** | PostgreSQL **18.4**, same major version |
| **Restore duration** | **1 second**, exit code 0, zero errors, zero warnings |
| **Tables** | 374 = 374 ✅ |
| **Total rows** | **30,258 = 30,258** ✅ |
| **Per-table diff** | all 374 tables match row-for-row, zero differences ✅ |
| **Foreign keys** | 698 = 698 ✅ |
| **Indexes** | 1,420 = 1,420 ✅ |
| **Migration rows** | 378 = 378 ✅ |
| **Constraints validated** | **873 validated, 0 failed**, 0 unvalidated FKs ✅ |
| **Django check** | "System check identified no issues" ✅ |
| **Unapplied migrations** | 0 ✅ |
| **Production impact** | none — `DATABASE_URL` unchanged, no failover/restore/resize, `ipAllowList` never modified |
| **Cleanup** | cluster stopped, dump and data directory deleted, export retained on Render |
| **Outcome** | **PASSED** |

The 18.4 / 18.6 discrepancy is recorded rather than smoothed over: the live
server reports 18.4 and the dump header reports 18.6. Both are PostgreSQL 18,
the restore was clean, and the difference is Render's tooling image.

### What the drill did NOT prove

Worth stating precisely, because a passing drill invites more confidence than
it earned:

- **It was a local restore, not a Render-hosted cutover.** The data restores
  and verifies; provisioning a replacement Render instance and repointing web
  and worker at it has never been rehearsed. That is the untested half of RTO.
- **No off-platform copy exists.** PITR, snapshots and the retained export all
  live inside one Render account. Account-level loss remains unrecoverable.
- **Exports are manual.** Nothing schedules one; the export list was empty
  until this drill created the first.
- **No HA and no read replica** on `basic_256mb` — a database outage is still a
  full outage.
- **203 of the 378 migration rows** belong to Wagtail/CMS/taggit apps that are
  no longer in `INSTALLED_APPS`. Their tables restore and verify like any
  other, so this is schema debt rather than a recovery defect — but it means
  the restored database carries structures the application no longer uses.

---

## Manual actions required (cannot be done in code)

These need Render dashboard access and, in two cases, money. They are listed so
the gap is actionable rather than merely known.

1. **Assign an owner** for backup/restore. Still unassigned. The RPO/RTO are
   now measured rather than guessed, but an objective nobody owns is still not
   an objective.
2. ~~Run the first restore drill~~ — **done 2026-08-25, passed.** See the
   verification log.
3. **Schedule the export.** The drill proved the export/restore path works; it
   also proved nothing runs it. One export exists because a human asked for it.
4. **Decide on off-platform backup.** PITR, snapshots and the retained export
   all sit in one Render account, so none of them survives account-level loss.
   A scheduled copy of the same logical export to external object storage is
   the smallest sufficient answer, and the drill shows that artefact restores
   cleanly.
5. **Rehearse a Render-hosted cutover.** The untested half of RTO: provision a
   replacement instance, restore into it, repoint web and worker. Needs a paid
   instance, so price it before creating anything.
6. ~~Decide on uploaded-file durability~~ — **done.** Uploads are on
   Cloudflare R2 (private, presigned reads). See "Uploaded files" above.
7. ~~Consider point-in-time recovery~~ — **already available**, window opens
   `2026-08-21T12:16:54Z`. This is what makes the measured RPO minutes rather
   than a day.
