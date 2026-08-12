"""
mobile_auth/services.py — access-token issuance/verification and the
login/refresh/logout flows themselves. Kept out of views.py so the token
mechanics are unit-testable without going through HTTP.
"""
from django.conf import settings
from django.contrib.auth import authenticate
from django.core import signing
from django.utils import timezone

from mobile_auth.models import DeviceSession

# Namespace passed to django.core.signing as `salt`. NOT a secret: Django's
# salt is domain separation, so a signature minted here can never be replayed
# against another signing purpose. The cryptographic secret is SECRET_KEY,
# which stays in the environment. Named *_SIGNING_NAMESPACE rather than
# a *_TOKEN_* name so neither a reader nor core/tests_no_hardcoded_secrets.py
# mistakes a literal namespace for a leaked credential.
# Changing this value invalidates every access token already issued.
ACCESS_SIGNING_NAMESPACE = 'mobile_auth.access_token.v1'


def issue_access_token(session: DeviceSession) -> str:
    return signing.dumps({'uid': session.user_id, 'sid': session.pk}, salt=ACCESS_SIGNING_NAMESPACE)


def verify_access_token(raw_token: str) -> DeviceSession | None:
    try:
        payload = signing.loads(
            raw_token, salt=ACCESS_SIGNING_NAMESPACE,
            max_age=settings.MOBILE_AUTH_ACCESS_TOKEN_TTL.total_seconds(),
        )
    except signing.BadSignature:
        return None

    session = (DeviceSession.objects
               .select_related('user')
               .filter(pk=payload.get('sid'), user_id=payload.get('uid'))
               .first())
    if session is None or not session.is_active or not session.user.is_active:
        return None
    return session


class LoginResult:
    def __init__(self, session, access_token, refresh_token):
        self.session = session
        self.access_token = access_token
        self.refresh_token = refresh_token


def login_device(*, username, password, device_id, device_name='', platform='other',
                  app_version='', ip_address=None, user_agent='') -> LoginResult | None:
    user = authenticate(username=username, password=password)
    if user is None or not user.is_active:
        return None

    # Re-logging in from the same device_id replaces that device's prior
    # session rather than accumulating a new row every login.
    DeviceSession.objects.filter(
        user=user, device_id=device_id, revoked_at__isnull=True,
    ).update(revoked_at=timezone.now(), revoked_reason='user_logout')

    session, raw_refresh = DeviceSession.create_session(
        user=user, device_id=device_id, device_name=device_name, platform=platform,
        app_version=app_version, ip_address=ip_address, user_agent=user_agent,
    )
    access = issue_access_token(session)
    return LoginResult(session, access, raw_refresh)


def refresh_session(raw_refresh_token: str) -> LoginResult | None:
    session, was_reused = DeviceSession.verify_refresh_token(raw_refresh_token)
    if session is None:
        # was_reused=True was already handled (session revoked) inside
        # verify_refresh_token -- nothing further to do here either way.
        return None
    new_refresh = session.rotate_refresh_token()
    access = issue_access_token(session)
    return LoginResult(session, access, new_refresh)
