"""
ai_gateway/throttles.py — per-user and per-IP rate limiting for AI generation.

Both apply to every chat request, deliberately: the per-user limit stops one
account burning the free allowance, and the per-IP limit stops many accounts
behind one host doing the same. Rates live in
`settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']` alongside the existing
EcoIQ API tiers, not hard-coded here.

These are additional to (not a replacement for) the project-wide
`APIKeyRateThrottle` — a request has to satisfy all of them.
"""
from rest_framework.throttling import SimpleRateThrottle


class AIChatUserThrottle(SimpleRateThrottle):
    """Per authenticated identity (Django user, or API key when there is no user)."""
    scope = 'ai_chat_user'

    def get_cache_key(self, request, view):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            ident = f'user:{user.pk}'
        else:
            from api.models import APIKey
            auth = getattr(request, 'auth', None)
            if isinstance(auth, APIKey):
                ident = f'apikey:{auth.pk}'
            else:
                # Unauthenticated callers are rejected by the permission class
                # before this runs; fall back to IP so the throttle is never a
                # silent no-op if that ever changes.
                ident = f'ip:{self.get_ident(request)}'
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class AIChatIPThrottle(SimpleRateThrottle):
    """Per source IP, regardless of which account is being used."""
    scope = 'ai_chat_ip'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class AICatalogThrottle(SimpleRateThrottle):
    """
    Bounds catalogue polling. The registry itself is cached for
    AI_MODEL_CATALOG_CACHE_SECONDS, so this protects EcoIQ's own workers
    rather than the upstream providers.
    """
    scope = 'ai_catalog'

    def get_cache_key(self, request, view):
        user = getattr(request, 'user', None)
        ident = f'user:{user.pk}' if (user is not None and user.is_authenticated) \
            else f'ip:{self.get_ident(request)}'
        return self.cache_format % {'scope': self.scope, 'ident': ident}
