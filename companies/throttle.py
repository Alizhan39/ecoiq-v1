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
import logging

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

ANON_PER_MIN = 10
AUTH_PER_MIN = 30
WINDOW = 60  # seconds


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or 'unknown'


def _limit_for(request):
    """Return the per-window request limit for this user, or None for unlimited."""
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        if user.is_staff:
            return None  # staff: unlimited
        return AUTH_PER_MIN
    return ANON_PER_MIN


def _too_many(name, request):
    """True if this IP has exceeded its limit in the current window."""
    limit = _limit_for(request)
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


def rate_limit(name, json=False):
    """
    Decorator: per-IP rate limit (anon 10/min, auth 30/min, staff unlimited).
    Returns a clean 429 when exceeded. `json=True` returns a JSON 429 body.
    """
    def decorator(view):
        def wrapped(request, *args, **kwargs):
            if _too_many(name, request):
                logger.warning('Rate limit hit: %s by %s', name, _client_ip(request))
                retry = WINDOW - int(time.time()) % WINDOW
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
