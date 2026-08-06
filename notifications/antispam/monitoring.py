"""
Volume monitoring for public-form abuse.

Counters live in the shared cache with bounded TTLs. Nothing here records a
message, a full IP, or a token — only counts keyed by event and by keyed
fingerprint.
"""
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('notifications.antispam')

TEN_MINUTES = 60 * 10
DAY = 60 * 60 * 24


def _bump(key, ttl):
    try:
        if cache.add(key, 1, ttl):
            return 1
        try:
            return cache.incr(key)
        except ValueError:
            cache.set(key, 1, ttl)
            return 1
    except Exception:
        return 0


def record(event, *, fingerprint='', form='contact'):
    """Count an event and raise an alert log line when a threshold trips."""
    if event == 'contact_submission_rejected':
        count = _bump(f'antispam:alert:rejected:{form}', TEN_MINUTES)
        threshold = getattr(settings, 'ANTISPAM_ALERT_REJECTIONS_PER_10MIN', 30)
        if count and count == threshold:
            logger.error(
                'antispam_alert_rejection_spike',
                extra={'event': 'antispam_alert_rejection_spike',
                       'form': form, 'count': count, 'window_seconds': TEN_MINUTES},
            )

    if fingerprint:
        count = _bump(f'antispam:alert:fp:{fingerprint}', DAY)
        threshold = getattr(settings, 'ANTISPAM_ALERT_FINGERPRINT_PER_DAY', 100)
        if count and count == threshold:
            logger.error(
                'antispam_alert_fingerprint_flood',
                extra={'event': 'antispam_alert_fingerprint_flood',
                       'form': form, 'fingerprint': fingerprint[:12], 'count': count},
            )
