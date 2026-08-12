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


def RequiresFeature(feature_key: str):
    """
    Permission-class factory: requires `feature_key` under the EcoIQ
    commercial entitlement system (ecoiq_commerce.services.entitlements.
    has_entitlement) — the SAME resolution logic used everywhere else in
    the platform, not a re-implementation for the API layer.

    The caller may be EITHER a B2B api.models.APIKey (entitlement resolved
    from the key's plan/organisation) OR a logged-in EcoIQ app user
    authenticated via mobile_auth.authentication.MobileTokenAuthentication
    or the website's SessionAuthentication (entitlement resolved from that
    user's own subscription) — same feature keys, same has_entitlement()
    call, just a different "who is asking".

    Usage:
        permission_classes = [RequiresFeature('api_evidence_access')]
    """

    class _RequiresFeature(BasePermission):
        message = f'Your plan does not include "{feature_key}". Upgrade at /products/.'

        def has_permission(self, request, view):
            from api.models import APIKey
            from ecoiq_commerce.services.entitlements import has_entitlement

            auth = request.auth
            if isinstance(auth, APIKey):
                if not auth.is_active:
                    self.message = ('API key required. Include your key via X-API-Key header or '
                                     'Authorization: Bearer <key>.')
                    return False
                check = has_entitlement(auth.owner, feature_key, organisation=auth.owner_organisation, plan=auth.plan)
            elif request.user is not None and request.user.is_authenticated:
                check = has_entitlement(request.user, feature_key)
            else:
                self.message = ('Sign in or include an API key. Via X-API-Key header, '
                                 'Authorization: Bearer <key>, or a logged-in app session.')
                return False

            if not check.allowed:
                self.message = check.reason or self.message
            return bool(check)

    _RequiresFeature.__name__ = f'RequiresFeature_{feature_key}'
    return _RequiresFeature
