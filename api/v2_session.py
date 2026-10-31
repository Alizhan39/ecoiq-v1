"""
api/v2_session.py — the React ↔ Django authentication boundary.

THE DECISION: no new authentication system.

Django's session authentication already works, is already in the DRF
authenticator chain, already sets Secure cookies in production, and already
carries staff permissions. A JWT layer would mean writing token issue, refresh,
revocation and storage — four new ways to be wrong — to replace something that
is correct today. The SPA is served from the same origin as the API, so the
session cookie simply works.

What an SPA needs that a server-rendered page did not:

  1. A way to ASK whether it is signed in. A template knew from `request.user`;
     a static bundle has to ask.
  2. A way to obtain the CSRF cookie before its first unsafe request. Django
     sets it while rendering a form; an SPA may never render a Django view.
  3. Sign-in and sign-out that answer JSON rather than redirecting to HTML.

That is all three, and nothing more.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
It does not replace `/login/`. Django's LoginView still exists and still works;
staff tooling and the admin depend on it. This is an additional JSON surface
over the same `django.contrib.auth` primitives, not a second auth system.

It never returns a password, a token, or a session key. The session lives in
an HttpOnly cookie the JavaScript cannot read, which is the property that makes
this boundary safe and the reason not to move to token-in-localStorage.
"""
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes, throttle_classes,
)
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle


def _identity(user) -> dict:
    """
    What the frontend may know about the signed-in user.

    A deliberately small projection. `is_staff` is included because the SPA
    needs it to decide which navigation to render — but it is a HINT, not a
    permission. Every staff-only endpoint enforces its own check server-side,
    because anything the client is told can be edited by the client.
    """
    if not user or not user.is_authenticated:
        return {'authenticated': False, 'username': None, 'is_staff': False}
    return {
        'authenticated': True,
        'username': user.get_username(),
        'is_staff': bool(user.is_staff),
    }


@ensure_csrf_cookie
@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def session(request):
    """
    GET /api/v2/session/ — who am I, and set the CSRF cookie.

    Anonymous is a valid, successful answer: `{"authenticated": false}` with a
    200. A 401 here would make every anonymous page load look like an error,
    and the public product is anonymous by default.

    `ensure_csrf_cookie` is the reason this endpoint is worth having on its own
    rather than folding it into another: it guarantees the SPA can obtain a
    CSRF token before its first POST without rendering a Django template.
    """
    get_token(request)          # force the cookie even on a cached response
    return Response(_identity(request.user))


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def sign_in(request):
    """
    POST /api/v2/session/sign-in/ — {username, password} → identity.

    Throttled, because an unthrottled JSON login endpoint is a credential
    stuffing target in a way a form behind a template is not.

    The failure response is deliberately identical whether the username exists
    or the password is wrong: distinguishing them turns this into a user
    enumeration oracle.
    """
    username = (request.data or {}).get('username') or ''
    password = (request.data or {}).get('password') or ''

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {'detail': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Django cycles the session key on login, which is what prevents session
    # fixation. Doing this by hand instead of calling login() would lose it.
    login(request, user)
    return Response(_identity(user))


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def sign_out(request):
    """
    POST /api/v2/session/sign-out/ — always succeeds.

    Signing out when already signed out is not an error; it is the state the
    caller asked for. Returning 401 would make a double-click look like a
    failure and tempt the client into retry logic around a no-op.

    POST, not GET: a sign-out reachable by GET can be triggered by an <img> tag
    on someone else's page.
    """
    logout(request)
    return Response(_identity(None))


# ── CSRF, and why this needs an explicit line ────────────────────────────────
#
# DRF's SessionAuthentication enforces CSRF only for requests it actually
# AUTHENTICATES. An anonymous sign-in POST has no session user yet, so the
# check never runs -- and @api_view separately marks the view csrf_exempt.
# The result is an unprotected login endpoint.
#
# That is login-CSRF: an attacker forces a victim's browser to sign in as the
# ATTACKER, and the victim then works inside an account the attacker controls
# and can read. Django's own LoginView prevents it; the JSON surface must too.
#
# Wrapping with @csrf_protect does NOT work here, which is the subtle part:
# functools.wraps copies the csrf_exempt attribute onto the new wrapper, and
# CsrfViewMiddleware skips any view carrying it. So the flag is cleared
# directly, which is the only thing the middleware actually reads.
#
# Found by a test that expected 403 and got 200.
sign_in.csrf_exempt = False
sign_out.csrf_exempt = False
