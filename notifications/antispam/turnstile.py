"""
Cloudflare Turnstile server-side verification.

The widget token is only meaningful once verified with Cloudflare, so every
submission is checked through siteverify with an explicit timeout. Tokens are
single-use: Cloudflare rejects a replay, and a local cache marker rejects it
before the network call.

Configuration (never committed):
    TURNSTILE_SITE_KEY    — public, rendered in the form
    TURNSTILE_SECRET_KEY  — secret, server-side only

Behaviour when unconfigured:
    production  -> fail closed (submissions are rejected)
    dev/tests   -> pass through, so local work needs no Cloudflare account
"""
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

SITEVERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
DEFAULT_TIMEOUT = 5.0
REPLAY_CACHE_PREFIX = 'turnstile:seen:'
REPLAY_TTL = 60 * 10


class TurnstileResult:
    __slots__ = ('ok', 'code', 'detail')

    def __init__(self, ok, code='', detail=''):
        self.ok = ok
        self.code = code
        self.detail = detail

    def __bool__(self):
        return self.ok


def is_configured():
    return bool(
        getattr(settings, 'TURNSTILE_SITE_KEY', '')
        and getattr(settings, 'TURNSTILE_SECRET_KEY', '')
    )


def _token_marker(token):
    """Short keyed marker for replay detection — never the token itself."""
    import hashlib
    return REPLAY_CACHE_PREFIX + hashlib.sha256(token.encode('utf-8')).hexdigest()[:32]


def verify(token, *, remote_ip=None, expected_action=None, expected_hostname=None):
    """
    Verify a Turnstile token. Returns TurnstileResult; never raises.

    `token` is never logged: only its presence, length bucket and the outcome.
    """
    if not is_configured():
        if getattr(settings, 'IS_PRODUCTION', False):
            # Fail closed: an unprotected public form in production is the bug
            # this module exists to prevent.
            logger.error('turnstile_not_configured_in_production')
            return TurnstileResult(False, 'not_configured')
        return TurnstileResult(True, 'skipped_unconfigured')

    if not token:
        return TurnstileResult(False, 'missing')

    marker = _token_marker(token)
    if cache.get(marker):
        return TurnstileResult(False, 'replayed')

    data = {
        'secret': getattr(settings, 'TURNSTILE_SECRET_KEY', ''),
        'response': token,
    }
    if remote_ip:
        data['remoteip'] = remote_ip

    try:
        import requests
        response = requests.post(
            SITEVERIFY_URL, data=data,
            timeout=getattr(settings, 'TURNSTILE_TIMEOUT_SECONDS', DEFAULT_TIMEOUT),
        )
        payload = response.json()
    except Exception as exc:
        # Network trouble, DNS, timeout, malformed body. Fail closed in
        # production; a public form must not silently lose its protection.
        logger.warning('turnstile_verify_unavailable', extra={'error': type(exc).__name__})
        return TurnstileResult(False, 'unavailable', type(exc).__name__)

    if not payload.get('success'):
        codes = payload.get('error-codes') or []
        logger.info('turnstile_validation_failed', extra={'codes': codes[:4]})
        return TurnstileResult(False, 'invalid', ','.join(str(c) for c in codes[:4]))

    if expected_action and payload.get('action') and payload['action'] != expected_action:
        return TurnstileResult(False, 'action_mismatch')

    if expected_hostname and payload.get('hostname') and payload['hostname'] != expected_hostname:
        return TurnstileResult(False, 'hostname_mismatch')

    # Consume the token so a replay cannot pass, even before Cloudflare's own
    # single-use check would catch it.
    cache.set(marker, 1, REPLAY_TTL)
    return TurnstileResult(True, 'ok')
