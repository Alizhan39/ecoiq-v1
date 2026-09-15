# EcoIQ low-cost Render migration

## Target topology

- `ecoiq`: one Free web service, one Gunicorn process and four threads.
- `ecoiq-db`: the existing durable paid Postgres database.
- No always-on Celery worker.
- No Render Key Value instance after the cutover is verified.
- No suspended Render cron services.

This is the lowest safe Render topology for operational or accounting data. A
Free Render Postgres database expires 30 days after creation, so it must not be
used as the system of record. The web service may sleep after 15 minutes of
inactivity and can take about a minute to wake.

## Why accounting reminders do not need Celery

`/financial-intelligence-cloud/accounting-operations/` calculates overdue and
upcoming reminders directly from indexed database fields whenever a staff user
opens the page. Completing or snoozing a reminder is a normal atomic Django
request. No periodic task, queue or broker is involved.

The existing intelligence task code remains importable for explicit staff
operations and tests. In this topology `CELERY_TASK_ALWAYS_EAGER=True`, so the
two remaining `.delay()` call sites run synchronously and never enqueue work on
an absent broker. They should only be invoked for bounded staff operations.

## Safe cutover order

1. Take and verify a current database backup. Do not change the database plan.
2. Merge and deploy the application change while the current worker and Key
   Value instance still exist.
3. Apply migrations and verify:
   - `/healthz/` returns `200 ok`;
   - `/readyz/` returns database `ok`;
   - a staff user can open Accounting Operations;
   - a reminder can be created, snoozed and completed;
   - a partial payment and its audit event persist after a restart.
4. Remove `REDIS_URL` from the web service environment and redeploy. Confirm
   `/readyz/` still returns `200` with Redis reported as not configured.
5. Suspend the manually-created `ecoiq-celery-worker`. Observe the web service
   for one business day, then delete the worker if no required workflow is
   missing.
6. Delete `ecoiq-keyvalue` only after the worker is gone and the web service is
   confirmed to use the documented process-local cache fallback.
7. Delete the four already-suspended manual cron services after recording their
   names and schedules in the change log.
8. Sync the Blueprint only after reviewing Render's pending-action preview. The
   expected managed change is the `ecoiq` web compute plan to `free`; unmanaged
   services are removed manually, not by Blueprint sync.

## Rollback

If the Free web service exceeds 512 MB, times out during ordinary page loads or
cannot complete migrations reliably, return only `ecoiq` to a paid 512 MB or
larger plan. Keep the same database and do not restore Redis/Celery unless a
specific background workflow has been approved and measured.
