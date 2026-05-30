"""
api/authentication.py — API key authentication for DRF.

Reads key from: Authorization: Bearer <key>
               X-API-Key: <key>

Sets request.auth = APIKey instance on success.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class APIKeyAuthentication(BaseAuthentication):
    """Bearer token / X-API-Key header authentication."""

    def authenticate(self, request):
        from api.models import APIKey

        raw_key = self._extract_key(request)
        if not raw_key:
            return None  # Pass to next authenticator

        key_obj = APIKey.verify(raw_key)
        if not key_obj:
            raise AuthenticationFailed('Invalid or expired API key.')

        # Return (user, auth) — user may be None (anonymous API subscriber)
        user = key_obj.owner
        return (user, key_obj)

    def _extract_key(self, request) -> str | None:
        """Extract raw API key from request headers."""
        # X-API-Key header (preferred)
        raw = request.META.get('HTTP_X_API_KEY', '').strip()
        if raw:
            return raw

        # Authorization: Bearer <key>
        auth_header = request.META.get('HTTP_AUTHORIZATION', '').strip()
        if auth_header.lower().startswith('bearer '):
            return auth_header[7:].strip()

        return None

    def authenticate_header(self, request):
        return 'Bearer realm="EcoIQ API"'
