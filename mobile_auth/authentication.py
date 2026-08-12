"""
mobile_auth/authentication.py — DRF authentication for the mobile/desktop
app's short-lived access tokens. Separate from api.authentication.APIKeyAuthentication
(B2B keys) and from SessionAuthentication (the website's cookie login).
"""
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from mobile_auth.services import verify_access_token


class MobileTokenAuthentication(BaseAuthentication):
    """
    Authorization: Bearer <access_token> — issued by /api/v1/auth/login/ or
    /refresh/. Access tokens are django.core.signing.dumps() output, which
    is always exactly two colon-separated segments
    (<payload>:<timestamp>:<signature> — see mobile_auth/services.py).
    api.models.APIKey raw keys are plain 64-char hex with no colons, so this
    shape check lets a real API key correctly fall through to
    api.authentication.APIKeyAuthentication instead of being misclaimed
    here (see the DEFAULT_AUTHENTICATION_CLASSES ordering note in settings.py).
    """

    keyword = 'Bearer'

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith(f'{self.keyword} '):
            return None  # let other authenticators (or AllowAny views) handle it
        raw_token = auth_header[len(self.keyword) + 1:].strip()
        if raw_token.count(':') != 2:
            return None  # not shaped like a mobile access token -- defer to APIKeyAuthentication

        session = verify_access_token(raw_token)
        if session is None:
            raise AuthenticationFailed('Invalid, expired, or revoked access token.')

        session.__class__.objects.filter(pk=session.pk).update(last_used_at=timezone.now())
        request.device_session = session
        return (session.user, session)

    def authenticate_header(self, request):
        return self.keyword
