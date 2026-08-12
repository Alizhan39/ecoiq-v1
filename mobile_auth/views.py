"""
mobile_auth/views.py — /api/v1/auth/... endpoints for the EcoIQ mobile/
desktop app. Session-cookie auth (the website) and API-key auth (B2B data
licensing) are untouched; this is a third, independent auth surface.
"""
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.client_origin import client_ip as _resolve_client_ip
from mobile_auth.authentication import MobileTokenAuthentication
from mobile_auth.models import PLATFORM_CHOICES, DeviceSession
from mobile_auth.services import LoginResult, login_device, refresh_session
from mobile_auth.throttles import LoginRateThrottle

_VALID_PLATFORMS = {key for key, _ in PLATFORM_CHOICES}


def _client_ip(request):
    """
    The trusted client address, via the single shared resolver.

    Deliberately NOT `X-Forwarded-For.split(',')[0]`. core/client_origin.py
    records the measured production topology: client-supplied (forgeable)
    entries appear on the LEFT and the infrastructure appends exactly two on
    the right, so the real client sits at index len-2. Taking entry [0]
    returns precisely the value an attacker controls — which would let a
    caller forge a different IP per request and walk straight past the
    per-IP login throttle this value feeds.
    """
    return _resolve_client_ip(request)


def _token_response(result: LoginResult, status_code=status.HTTP_200_OK) -> Response:
    return Response({
        'access_token': result.access_token,
        'access_token_expires_in': int(settings.MOBILE_AUTH_ACCESS_TOKEN_TTL.total_seconds()),
        'refresh_token': result.refresh_token,
        'refresh_token_expires_at': result.session.refresh_expires_at.isoformat(),
        'session_id': result.session.pk,
        'token_type': 'Bearer',
    }, status=status_code)


class LoginView(APIView):
    """POST /api/v1/auth/login/ — {username, password, device_id, device_name?, platform?, app_version?}"""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        data = request.data
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        device_id = (data.get('device_id') or '').strip()

        if not username or not password or not device_id:
            return Response(
                {'detail': 'username, password, and device_id are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        platform = data.get('platform') or 'other'
        if platform not in _VALID_PLATFORMS:
            platform = 'other'

        result = login_device(
            username=username, password=password, device_id=device_id,
            device_name=(data.get('device_name') or '')[:200],
            platform=platform, app_version=(data.get('app_version') or '')[:30],
            ip_address=_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        if result is None:
            return Response({'detail': 'Invalid username or password.'}, status=status.HTTP_401_UNAUTHORIZED)
        return _token_response(result, status.HTTP_201_CREATED)


class RefreshView(APIView):
    """POST /api/v1/auth/refresh/ — {refresh_token} -> a new (access_token, refresh_token) pair. Rotates."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = (request.data.get('refresh_token') or '').strip()
        if not raw_refresh:
            return Response({'detail': 'refresh_token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        result = refresh_session(raw_refresh)
        if result is None:
            return Response(
                {'detail': 'Refresh token is invalid, expired, or has been revoked. Please log in again.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return _token_response(result)


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ — revokes the CURRENT device's session only."""
    authentication_classes = [MobileTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.device_session.revoke(reason='user_logout')
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutAllView(APIView):
    """POST /api/v1/auth/logout-all/ — revokes every active session for this user (all devices)."""
    authentication_classes = [MobileTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        DeviceSession.objects.filter(
            user=request.user, revoked_at__isnull=True,
        ).update(revoked_at=timezone.now(), revoked_reason='logout_all_devices')
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionListView(APIView):
    """GET /api/v1/auth/sessions/ — the caller's own active device sessions. Never another user's."""
    authentication_classes = [MobileTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = DeviceSession.objects.filter(user=request.user, revoked_at__isnull=True).order_by('-last_used_at')
        return Response({
            'sessions': [
                {
                    'id': s.pk,
                    'device_name': s.device_name,
                    'platform': s.platform,
                    'app_version': s.app_version,
                    'created_at': s.created_at.isoformat(),
                    'last_used_at': s.last_used_at.isoformat(),
                    'is_current': s.pk == request.device_session.pk,
                }
                for s in sessions
            ],
        })


class SessionRevokeView(APIView):
    """POST /api/v1/auth/sessions/<id>/revoke/ — revoke one of the caller's OWN sessions (IDOR-safe: scoped to owner, 404 otherwise)."""
    authentication_classes = [MobileTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(DeviceSession, pk=session_id, user=request.user, revoked_at__isnull=True)
        session.revoke(reason='user_logout')
        return Response(status=status.HTTP_204_NO_CONTENT)
