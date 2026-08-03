"""
ai_gateway/permissions.py — access rules for the AI gateway, built on EcoIQ's
existing authentication mechanisms rather than a new one.

`IsEcoIQAuthenticated` accepts any of the three schemes already wired into
`REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`:
  * a logged-in website session or mobile device session (a real Django user);
  * a valid, active B2B `api.models.APIKey` — which may legitimately have no
    owner user, so plain `IsAuthenticated` would wrongly reject it.
"""
from rest_framework.permissions import BasePermission


class IsEcoIQAuthenticated(BasePermission):
    message = 'Sign in to use the EcoIQ assistant.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            return True

        from api.models import APIKey
        auth = getattr(request, 'auth', None)
        return isinstance(auth, APIKey) and auth.is_active


class IsEcoIQStaff(BasePermission):
    """Staff-only — used by the AI health endpoint."""
    message = 'Staff access required.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(user is not None and user.is_authenticated and user.is_staff)
