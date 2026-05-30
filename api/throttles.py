"""
api/throttles.py — Per-tier rate limiting for EcoIQ API.

Rates defined in settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']:
    explorer:      100/day
    professional:  2000/day
    enterprise:    50000/day
"""
from rest_framework.throttling import SimpleRateThrottle


class APIKeyRateThrottle(SimpleRateThrottle):
    """Rate limit by API key tier. Falls back to 'anon' rate if no key."""

    scope = 'anon'  # Default scope; overridden per-request in get_cache_key

    def get_cache_key(self, request, view):
        # If authenticated via API key, use key prefix as cache key
        if hasattr(request, 'auth') and request.auth is not None:
            key_obj  = request.auth
            ident    = f'apikey_{key_obj.prefix}_{key_obj.pk}'
            # Set scope to the tier so the right rate is applied
            self.scope = key_obj.tier
            self.rate  = self.get_rate()
            self.num_requests, self.duration = self.parse_rate(self.rate)
            return self.cache_format % {'scope': self.scope, 'ident': ident}

        # Unauthenticated — use IP
        self.scope = 'anon'
        self.rate  = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }
