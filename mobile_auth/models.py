"""
mobile_auth/models.py — end-user device sessions for the EcoIQ mobile/desktop
app (iOS, Android, Windows). Deliberately separate from `api.APIKey`, which
is a long-lived B2B licensing credential for institutional data access, not
a per-device end-user login.

Token design (no new third-party auth dependency — reuses what's already in
the stack):
  - Access token: a short-lived, self-contained token signed with Django's
    own `django.core.signing` (HMAC over settings.SECRET_KEY, the same
    primitive Django uses for password-reset tokens and signed cookies).
    Verified without a DB hit for the signature itself, then confirmed
    against a live, non-revoked DeviceSession — so revocation still takes
    effect immediately rather than waiting for the token to expire.
  - Refresh token: an opaque random token, same "store only the SHA-256
    hash" pattern as api.models.APIKey. Rotates on every use (the previous
    hash is kept for one generation so a replayed, already-rotated refresh
    token is detected as reuse and the whole session is revoked — see
    verify_refresh_token()).
"""
from __future__ import annotations

import hashlib
import os

from django.conf import settings
from django.db import models
from django.utils import timezone

PLATFORM_CHOICES = [
    ('ios', 'iOS'),
    ('android', 'Android'),
    ('windows', 'Windows'),
    ('other', 'Other'),
]

REVOKED_REASON_CHOICES = [
    ('', 'Not revoked'),
    ('user_logout', 'User logged out'),
    ('logout_all_devices', 'User logged out of all devices'),
    ('refresh_token_reuse_detected', 'Refresh token reuse detected (possible theft)'),
    ('admin_revoked', 'Revoked by staff'),
    ('expired', 'Expired'),
]


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _generate_raw_token() -> str:
    return os.urandom(32).hex()


class DeviceSession(models.Model):
    """One row per logged-in device/app-install. The unit of 'logout from this device'."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='device_sessions')

    device_id = models.CharField(max_length=200, help_text='Stable client-generated device identifier')
    device_name = models.CharField(max_length=200, blank=True, help_text='e.g. "Ali\'s iPhone 15"')
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default='other')
    app_version = models.CharField(max_length=30, blank=True)

    refresh_token_hash = models.CharField(max_length=64, unique=True)
    previous_refresh_token_hash = models.CharField(
        max_length=64, blank=True,
        help_text='Prior rotation\'s hash, kept one generation to detect refresh-token reuse',
    )

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now_add=True)
    refresh_expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=30, choices=REVOKED_REASON_CHOICES, blank=True, default='')

    class Meta:
        ordering = ['-last_used_at']
        indexes = [models.Index(fields=['user', 'device_id'])]

    def __str__(self):
        return f'{self.user.get_username()} — {self.device_name or self.platform} ({self.pk})'

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.refresh_expires_at > timezone.now()

    @classmethod
    def create_session(cls, *, user, device_id, device_name='', platform='other',
                        app_version='', ip_address=None, user_agent='') -> tuple['DeviceSession', str]:
        raw_refresh = _generate_raw_token()
        session = cls.objects.create(
            user=user, device_id=device_id, device_name=device_name, platform=platform,
            app_version=app_version, ip_address=ip_address, user_agent=user_agent[:300],
            refresh_token_hash=_hash_token(raw_refresh),
            refresh_expires_at=timezone.now() + settings.MOBILE_AUTH_REFRESH_TOKEN_TTL,
        )
        return session, raw_refresh

    def rotate_refresh_token(self) -> str:
        """Issue a new refresh token, keeping the old hash for one generation (reuse detection)."""
        raw_refresh = _generate_raw_token()
        self.previous_refresh_token_hash = self.refresh_token_hash
        self.refresh_token_hash = _hash_token(raw_refresh)
        self.last_used_at = timezone.now()
        self.save(update_fields=['refresh_token_hash', 'previous_refresh_token_hash', 'last_used_at'])
        return raw_refresh

    def revoke(self, reason: str = 'user_logout'):
        self.revoked_at = timezone.now()
        self.revoked_reason = reason
        self.save(update_fields=['revoked_at', 'revoked_reason'])

    @classmethod
    def verify_refresh_token(cls, raw_token: str) -> tuple['DeviceSession | None', bool]:
        """
        Returns (session, was_reused). `session` is None if the token matches
        nothing live. `was_reused=True` means the token matched a session's
        PREVIOUS (already-rotated-away) hash -- a strong signal of token
        theft/replay -- and that session has just been revoked as a result.
        """
        token_hash = _hash_token(raw_token)
        session = cls.objects.filter(refresh_token_hash=token_hash, revoked_at__isnull=True).first()
        if session is not None:
            if session.refresh_expires_at <= timezone.now():
                session.revoke(reason='expired')
                return None, False
            return session, False

        reused = cls.objects.filter(previous_refresh_token_hash=token_hash, revoked_at__isnull=True).first()
        if reused is not None:
            reused.revoke(reason='refresh_token_reuse_detected')
            return None, True

        return None, False
