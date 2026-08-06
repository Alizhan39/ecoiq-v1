"""
Signed form-render timestamp.

The rendered form carries a signed token containing the render time. Because it
is signed with SECRET_KEY, a bot cannot forge or back-date it — it must either
fetch the page (and wait) or submit something that fails to verify.
"""
import logging
import time

from django.core import signing

logger = logging.getLogger(__name__)

SALT = 'ecoiq.antispam.formtime'
MIN_SECONDS = 3          # a human cannot read and complete a form faster
MAX_SECONDS = 60 * 60 * 6


def issue(now=None):
    """Signed token embedding the render time. Put this in a hidden field."""
    return signing.dumps({'t': int(now or time.time())}, salt=SALT)


def check(token, *, min_seconds=None, max_seconds=None, now=None):
    """
    Returns (ok, code). Codes: 'ok', 'too_fast', 'expired', 'tampered'.
    A missing token counts as tampered — the form always renders one.
    """
    if not token:
        return False, 'tampered'
    try:
        payload = signing.loads(token, salt=SALT, max_age=max_seconds or MAX_SECONDS)
    except signing.SignatureExpired:
        return False, 'expired'
    except signing.BadSignature:
        return False, 'tampered'
    except Exception:
        return False, 'tampered'

    issued = int(payload.get('t', 0))
    elapsed = int(now or time.time()) - issued
    if elapsed < 0:
        return False, 'tampered'
    if elapsed < (min_seconds if min_seconds is not None else MIN_SECONDS):
        return False, 'too_fast'
    # Age is measured from the embedded render time, not from when the value
    # happened to be signed — otherwise a caller-supplied max_age could not be
    # honoured, and a stale form would slip through.
    if elapsed > (max_seconds if max_seconds is not None else MAX_SECONDS):
        return False, 'expired'
    return True, 'ok'
