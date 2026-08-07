"""
Shared-cache rate limiting for public submissions.

Counters are keyed by a keyed hash, never a raw IP, and every key carries a TTL
so nothing is retained beyond its window. A shared office or mobile-carrier NAT
address is therefore throttled for an hour at most, never blocked permanently.
"""
import logging

from django.core.cache import cache

from .fingerprint import content_fingerprint, hashed_ip, normalise_email

logger = logging.getLogger(__name__)

HOUR = 60 * 60
DAY = 60 * 60 * 24

# (limit, window_seconds) — overridable via settings.ANTISPAM_LIMITS
DEFAULTS = {
    'ip': (5, HOUR),          # 5 submissions per IP per hour
    'email': (3, DAY),        # 3 per normalised email per day
    'message': (2, DAY),      # 2 identical messages per day
    'global': (200, HOUR),    # emergency ceiling for anonymous submissions
}


def _limits():
    from django.conf import settings
    configured = getattr(settings, 'ANTISPAM_LIMITS', None) or {}
    merged = dict(DEFAULTS)
    merged.update(configured)
    return merged


def _hit(key, limit, window):
    """
    Increment a counter and report whether it is now over the limit.

    cache.add + incr keeps the window fixed from the first hit, so a steady
    stream cannot slide the window forward indefinitely.
    """
    try:
        if cache.add(key, 1, window):
            return False, 1
        try:
            count = cache.incr(key)
        except ValueError:
            # Key expired between add and incr.
            cache.set(key, 1, window)
            return False, 1
        return count > limit, count
    except Exception as exc:  # cache backend trouble must not break the form
        logger.warning('antispam_ratelimit_unavailable', extra={'error': type(exc).__name__})
        return False, 0


def check(*, ip='', email='', message='', form=''):
    """
    Returns a list of exceeded scope names: 'ip', 'email', 'message', 'global'.
    Counters are incremented as a side effect — call once per submission.
    """
    limits = _limits()
    exceeded = []

    limit, window = limits['global']
    over, _ = _hit(f'antispam:global:{form}', limit, window)
    if over:
        exceeded.append('global')

    # An origin we cannot identify shares one bucket with every other
    # unidentifiable origin rather than escaping the limit altogether. This
    # branch used to be `if ip:`, which meant an empty origin got no per-IP
    # limit at all — the exact fail-open this module exists to prevent.
    limit, window = limits['ip']
    bucket = hashed_ip(ip) if ip else 'unknown'
    over, _ = _hit(f'antispam:ip:{form}:{bucket}', limit, window)
    if over:
        exceeded.append('ip')

    if email:
        limit, window = limits['email']
        over, _ = _hit(f'antispam:email:{form}:{normalise_email(email)}', limit, window)
        if over:
            exceeded.append('email')

    if message:
        limit, window = limits['message']
        over, _ = _hit(f'antispam:msg:{content_fingerprint(message, form=form)}', limit, window)
        if over:
            exceeded.append('message')

    return exceeded
