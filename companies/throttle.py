"""
Lightweight per-IP rate limiting + response caching for heavy public endpoints
(PDF reports, certificates, ML-insights JSON, sector reports).

Dependency-free: uses Django's cache framework (default LocMemCache, shared
across threads of the single Render gunicorn worker). No models, no migrations.

Tiers (requests per minute):
  anonymous     → 10
  authenticated → 30
  staff         → unlimited
"""
import time

import structlog
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse

from core import client_origin, events
from core.client_origin import safe_origin_context

logger = structlog.get_logger(__name__)

ANON_PER_MIN = 10
AUTH_PER_MIN = 30
WINDOW = 60  # seconds


def _client_ip(request):
    """
    Trusted client address, or 'unknown'.

    'unknown' is a single shared bucket by design: an origin we cannot identify
    gets throttled together with every other unidentifiable origin, rather than
    being waved through.
    """
    return client_origin.client_ip(request) or 'unknown'


def _resolve(value):
    """
    Resolve a limit that may be an int or the NAME of a setting.

    A setting name is resolved per request, not captured at import. The
    difference matters twice: `override_settings` in a test can reach it, and
    an operator changing the environment variable gets the new ceiling on the
    next request rather than the next restart. A limit captured at import time
    reads as configurable and is not.
    """
    if isinstance(value, str):
        from django.conf import settings
        return getattr(settings, value)
    return value


def _limit_for(request, anon_per_min=None, auth_per_min=None, staff_exempt=True):
    """
    Return the per-window request limit for this user, or None for unlimited.

    The two overrides exist for surfaces whose safe ceiling is not the generic
    heavy-endpoint one — an authentication form is the obvious case, where the
    limit is a brute-force ceiling rather than a cost control.

    `staff_exempt` is deliberately switchable: exempting staff from a PDF
    throttle is sensible, exempting them from a LOGIN throttle is not, because
    the request that needs limiting is the one made by an attacker who is not
    signed in as anybody yet.
    """
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        if user.is_staff and staff_exempt:
            return None  # staff: unlimited
        return _resolve(auth_per_min) if auth_per_min is not None else AUTH_PER_MIN
    return _resolve(anon_per_min) if anon_per_min is not None else ANON_PER_MIN


def _too_many(name, request, anon_per_min=None, auth_per_min=None, staff_exempt=True):
    """True if this IP has exceeded its limit in the current window."""
    limit = _limit_for(request, anon_per_min, auth_per_min, staff_exempt)
    if limit is None:
        return False
    bucket = int(time.time() // WINDOW)
    key = f'rl:{name}:{_client_ip(request)}:{bucket}'
    # Atomic-ish counter on the cache; the key self-expires at window end.
    if cache.add(key, 1, timeout=WINDOW):
        count = 1
    else:
        try:
            count = cache.incr(key)
        except ValueError:  # key expired between add() and incr()
            cache.add(key, 1, timeout=WINDOW)
            count = 1
    return count > limit


def rate_limit(name, json=False, anon_per_min=None, auth_per_min=None, staff_exempt=True):
    """
    Decorator: per-IP rate limit (default anon 10/min, auth 30/min, staff
    unlimited). Returns a clean 429 when exceeded. `json=True` returns a JSON
    429 body.

    Pass `anon_per_min`/`auth_per_min` for a surface with a different safe
    ceiling, and `staff_exempt=False` where being staff must not lift the limit
    (authentication endpoints — see `_limit_for`).

    The identity is `core.client_origin.client_ip`, which is not
    client-forgeable behind Cloudflare. See core/throttling.py for why that
    matters and what it replaced.
    """
    def decorator(view):
        def wrapped(request, *args, **kwargs):
            if _too_many(name, request, anon_per_min, auth_per_min, staff_exempt):
                # Was: logger.warning('Rate limit hit: %s by %s', name,
                # _client_ip(request)) — which wrote the raw client address into
                # a persistent log line on every throttled request.
                #
                # INFO, not WARNING: a limiter turning traffic away is the
                # system working as designed. At WARNING an attack floods the
                # log with warnings exactly when it needs to stay readable.
                retry = WINDOW - int(time.time()) % WINDOW
                logger.info(
                    events.RATE_LIMIT_APPLIED,
                    limit_name=name,
                    limit=_limit_for(request, anon_per_min, auth_per_min, staff_exempt),
                    retry_after=retry,
                    **safe_origin_context(request),
                )
                # Annotated as the base class: the two branches build a
                # JsonResponse and an HttpResponse, and mypy otherwise pins the
                # variable to whichever branch it reads first.
                resp: HttpResponse
                if json:
                    resp = JsonResponse(
                        {'error': 'Rate limit exceeded. Please slow down and try again shortly.'},
                        status=429)
                else:
                    resp = HttpResponse(
                        'Rate limit exceeded. Please try again in a minute.',
                        status=429, content_type='text/plain')
                resp['Retry-After'] = str(retry)
                return resp
            return view(request, *args, **kwargs)
        wrapped.__name__ = getattr(view, '__name__', 'wrapped')
        wrapped.__doc__ = view.__doc__
        return wrapped
    return decorator


def cache_response(name, timeout=600):
    """
    Decorator: cache a successful (200) GET response body by request path so the
    same heavy artifact (PDF/certificate/JSON) is not regenerated on every hit.
    Output depends only on the URL (company/sector data), not the user, so a
    path-keyed cache is safe. Short TTL bounds staleness.
    """
    def decorator(view):
        def wrapped(request, *args, **kwargs):
            if request.method != 'GET':
                return view(request, *args, **kwargs)
            key = f'cr:{name}:{request.get_full_path()}'
            cached = cache.get(key)
            if cached is not None:
                content, content_type = cached
                return HttpResponse(content, content_type=content_type)
            response = view(request, *args, **kwargs)
            if getattr(response, 'status_code', 0) == 200 and hasattr(response, 'content'):
                cache.set(key, (response.content, response.get('Content-Type', 'text/html')), timeout)
            return response
        wrapped.__name__ = getattr(view, '__name__', 'wrapped')
        wrapped.__doc__ = view.__doc__
        return wrapped
    return decorator
