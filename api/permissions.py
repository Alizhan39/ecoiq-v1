"""
api/permissions.py — DRF permission classes for EcoIQ API.

IsAPIKeyAuthenticated: requires a valid API key (any tier).
IsEnterpriseKey:       requires enterprise tier.
IsPublicEndpoint:      allows unauthenticated read access (for public data).
"""
from rest_framework.permissions import BasePermission


class IsAPIKeyAuthenticated(BasePermission):
    """Allow access if request.auth is a valid APIKey object."""

    message = ('API key required. '
               'Include your key via X-API-Key header or Authorization: Bearer <key>.')

    def has_permission(self, request, view):
        from api.models import APIKey
        return (
            request.auth is not None
            and isinstance(request.auth, APIKey)
            and request.auth.is_active
        )


class IsEnterpriseKey(IsAPIKeyAuthenticated):
    """Require enterprise or admin (staff) access."""

    message = 'Enterprise API key required for this endpoint.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.auth.tier == 'enterprise' or (
            request.user and request.user.is_staff
        )


class IsPublicOrAPIKey(BasePermission):
    """
    Allow GET requests without authentication.
    Write operations (POST/PUT/PATCH/DELETE) require an API key.
    """

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        from api.models import APIKey
        return (
            request.auth is not None
            and isinstance(request.auth, APIKey)
        )
