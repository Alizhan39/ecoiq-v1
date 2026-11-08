# EcoIQ — durable uploads across Render deploys

## Invariant

A new release can replace Django/React code, but must **not** replace uploaded
evidence, inspection photos, videos, or documents. Database references must
continue to point to actual objects.

Render Free web instances have ephemeral filesystems: local uploads can vanish
on redeploy, restart or idle spin-down. PostgreSQL persists database records
separately, but **does not store the binary content of FileField uploads**.

## Storage decision

- **Application code and static bundle**: GitHub -> Render deploy.
- **Database records, KPI calculations, history**: managed PostgreSQL.
- **Uploaded private media**: Cloudflare R2 via `core.storage_r2.R2MediaStorage`.
- **Backups**: database export and independent copy of uploaded objects,
  protected by separate credentials. R2 objects are not PostgreSQL backups.

Do not use `MEDIA_ROOT` on a Render Free instance for production uploads.
A paid Render persistent disk is a possible alternative, but it changes
availability and scalability characteristics and is **not configured here**.

## Deployment protection

`ecoiq/settings.py` selects filesystem only for local development/tests.
In production it defaults to R2 and rejects an explicit filesystem setting.
If R2 credentials are missing, Django refuses to start rather than silently
writing files to temporary storage. This is a **breaking deployment guard**:
do not merge and deploy it until the existing production environment has
usable R2 credentials, or until an explicitly reviewed durable alternative
has been implemented.

Configure these in Render web-service environment (values must remain secret):

- `MEDIA_STORAGE_BACKEND=r2`
- `R2_ACCOUNT_ID`
- `R2_BUCKET_NAME`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

The bucket must be private. Do not set public read ACLs. Use separate
least-privilege credentials for the app and backups. Never commit credentials.

## Cutover checklist — no deletion

1. Resolve any suspended Render web/database services; confirm actual database
   contents and whether the currently configured default storage is R2 or
   filesystem. Do **not** use a blank database to verify production.
2. Check which storage contains actual objects, and run `python manage.py
   reconcile_media` in an environment with production database and storage
   access. Its counts are only meaningful for the environment being checked.
3. If production currently has local media, arrange an explicit
   `reconcile_media --migrate` copy **before redeploy/restart** while the
   source files still exist. This command does not delete source files; ensure
   it reads from the correct source root. A prior ephemeral instance's lost
   files cannot be recreated by enabling R2.
4. Verify credentials can list/read/write a test object in the intended bucket
   without making it public; ensure all existing referenced files are present.
5. Set the Render environment variables above, then deploy the guard only
   once connectivity and migration are verified. A code push to `main` can
   automatically redeploy the service.
6. Upload a harmless test file through the normal authenticated application,
   read it back, then redeploy and verify the **same URL/key** remains readable.
   Check a previously uploaded file as well.
7. Record the result, reconciliation counts, retention and restore procedure.
   Back up both the PostgreSQL database and R2; test recovery separately.
8. Only then retire any old storage. Never delete an R2 bucket as a side
   effect of changing a Render variable.

## Rollback

If the new deployment fails, revert the application commit or redeploy the
last known-good release **without deleting the object store or database**.
Keep the old credentials and bucket available until all file references
have been verified and the rollback window has closed.

A successful GitHub CI test or Render build does not prove files survived a
deploy; the end-to-end upload/read/redeploy/read check above is mandatory.
