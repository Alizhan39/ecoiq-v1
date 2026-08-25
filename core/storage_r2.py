"""
core/storage_r2.py — the Cloudflare R2 backend class, in its own module.

SEPARATE FROM core/storage.py ON PURPOSE
----------------------------------------
`core/storage.py` holds the `upload_to` callables, so it is imported by models
in every process — including the test suite and any management command. This
module subclasses `S3Boto3Storage`, which pulls in boto3.

Django imports a `STORAGES['default']['BACKEND']` path only when it actually
instantiates that backend, so keeping the subclass here means a filesystem or
test process never loads boto3 at all. Putting the class next to the callables
would have made an optional dependency mandatory everywhere.
"""
from __future__ import annotations

from storages.backends.s3boto3 import S3Boto3Storage


class R2MediaStorage(S3Boto3Storage):
    """
    Private objects in R2, read through short-lived presigned URLs.

    `default_acl = None` is deliberate and is not the same as omitting it. R2
    implements no per-object ACLs, and django-storages would otherwise send
    `ACL: private`, which R2 rejects. Privacy comes from the bucket never being
    public plus every read being signed — not from an ACL header.
    """

    #: See the class docstring. Do not set this to 'private'.
    default_acl = None

    #: Every generated URL is signed and expires. `querystring_expire` is
    #: supplied from settings (R2_SIGNED_URL_EXPIRY_SECONDS, default 300s).
    querystring_auth = True

    #: Never silently replace an existing object. Combined with the uuid4 in
    #: every key (core.storage.build_key) a collision is already implausible;
    #: this makes an overwrite impossible rather than merely unlikely.
    file_overwrite = False

    #: Uploaded documents are not web assets. Nothing — browser, proxy, or CDN
    #: — should retain a copy after the signed URL expires.
    object_parameters = {'CacheControl': 'private, no-store'}
