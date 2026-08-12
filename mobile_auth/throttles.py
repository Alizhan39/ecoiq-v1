from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """Per-IP brute-force protection on /api/v1/auth/login/. Scope rate: settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['auth_login']."""

    scope = 'auth_login'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}
