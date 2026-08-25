"""
core/storage.py — durable, private object storage for uploaded files.

THE PROBLEM THIS SOLVES
-----------------------
`MEDIA_ROOT` was `BASE_DIR / 'media'` on the web service's own filesystem. Render
replaces that filesystem on every deploy, so an uploaded evidence document
survived only until the next release while its database row survived forever —
a reference to a file that no longer exists, which reads to the application as
"the document is on file".

Measured before writing this: MEDIA_ROOT did not exist in production, 0 files,
0 bytes, and 0 database references across all six upload fields. Nothing had
been lost yet because nothing had been uploaded yet. That is the good moment to
fix it.

R2 IS FOR BYTES, POSTGRES IS STILL THE TRUTH
--------------------------------------------
Object storage holds file CONTENT. Every piece of metadata — who uploaded it,
which organisation it belongs to, whether it has been reviewed — stays in
PostgreSQL. Nothing here reads or writes evidence state, and no scoring,
eligibility or confidence logic is touched.

PRIVATE BY DEFAULT, AND NOT BY ACL
----------------------------------
R2 has no per-object ACLs, so `default_acl` is None on purpose rather than by
omission: setting `'private'` would make boto3 send an ACL header R2 rejects.
Privacy comes from the bucket never being public and from every read being a
short-lived presigned URL.

`querystring_auth = True` and a ~5 minute expiry mean a URL that leaks — pasted
into a ticket, logged by an intermediary — stops working quickly. The signature
is derived from the credentials; it never contains them.

OPT-IN, AND FAIL CLOSED
-----------------------
The backend is selected only when MEDIA_STORAGE_BACKEND == 'r2'. If it is set
to 'r2' and any required variable is missing, settings raise at import rather
than starting on the local filesystem — silently writing to a disk that will be
destroyed is exactly the failure this module exists to end.
"""
from __future__ import annotations

import os
import posixpath
import re
import unicodedata
import uuid

#: Length of the random component in every stored key. 32 hex characters is
#: collision-resistant enough that `file_overwrite = False` never has to rename
#: anything, and it makes a key unguessable — which matters because a bucket
#: listing is denied but a guessed key plus a signature is not.
_RANDOM_LEN = 32

_SAFE = re.compile(r'[^A-Za-z0-9._-]+')


def sanitise_filename(name: str) -> str:
    """
    Reduce an uploaded filename to a safe, non-identifying basename.

    Uploaded filenames routinely carry personal information — people name files
    after themselves, their client, or an internal case number. The stored key
    keeps only an extension and a short slug of the stem, so the object name
    cannot leak what the document is about to anyone who sees a URL.
    """
    base = posixpath.basename((name or '').replace('\\', '/'))
    stem, ext = os.path.splitext(base)
    stem = unicodedata.normalize('NFKD', stem).encode('ascii', 'ignore').decode()
    ext = unicodedata.normalize('NFKD', ext).encode('ascii', 'ignore').decode()
    stem = _SAFE.sub('-', stem).strip('-.')[:40].lower() or 'file'
    ext = _SAFE.sub('', ext)[:10].lower()
    return f'{stem}{ext}'


def build_key(prefix: str, filename: str, *, scope: str | None = None) -> str:
    """
    `<prefix>/[org/<scope>/]<uuid4hex>-<safe-name>`.

    The random component comes FIRST after the scope so that keys sharing a
    prefix do not sort together by name, and so two people uploading
    `report.pdf` in the same second cannot collide.
    """
    parts = [prefix.strip('/')]
    if scope:
        parts += ['org', _SAFE.sub('-', str(scope)).strip('-')[:64]]
    parts.append(f'{uuid.uuid4().hex[:_RANDOM_LEN]}-{sanitise_filename(filename)}')
    return posixpath.join(*parts)


# ── upload_to callables ───────────────────────────────────────────────────────
#
# Tenant scope lives here rather than in the storage class, and it has to: a
# storage backend is handed a name and a file, and has no idea which
# organisation the row belongs to. Only the model knows that.
#
# Three of the six upload fields reach a company; the other three do not, and
# are given an unscoped — but still random and non-identifying — key rather than
# a fabricated scope.

def _company_scope(instance) -> str | None:
    for attr in ('company_id', 'company'):
        value = getattr(instance, attr, None)
        if value is not None:
            return str(getattr(value, 'pk', value))
    return None


def upload_to_evidence(instance, filename):
    return build_key('league/evidence', filename, scope=_company_scope(instance))


def upload_to_ai_analysis(instance, filename):
    return build_key('ai_analysis', filename, scope=_company_scope(instance))


def upload_to_guidance_thumbnail(instance, filename):
    return build_key('guidance_videos/thumbnails', filename, scope=_company_scope(instance))


def upload_to_assessment(instance, filename):
    return build_key('uploads', filename)


def upload_to_audit(instance, filename):
    return build_key('audit_uploads', filename)


def upload_to_sustainability_report(instance, filename):
    return build_key('sustainability_reports', filename)


def private_media_storage():
    """
    The configured default storage, resolved lazily.

    Returned through a function so a model field never binds a storage instance
    at import time — `override_settings(STORAGES=...)` in a test would otherwise
    be ignored by every field that had already captured one.
    """
    from django.core.files.storage import default_storage

    return default_storage
