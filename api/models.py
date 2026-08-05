"""
api/models.py — EcoIQ API key model.

API keys are issued per subscriber tier. The key is a 64-char hex token
stored as SHA-256 hash in the database (never the raw key).

Tiers match the DRF throttle rate names defined in settings.REST_FRAMEWORK.
"""
from __future__ import annotations

import hashlib
import os
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


TIER_CHOICES = [
    ('explorer',      'Explorer    (100 req/day)'),
    ('professional',  'Professional (2,000 req/day)'),
    ('enterprise',    'Enterprise  (50,000 req/day)'),
]

ENVIRONMENT_CHOICES = [
    ('sandbox', 'Sandbox'),
    ('production', 'Production'),
]


class APIScope(models.Model):
    """
    A grantable API capability, e.g. 'companies:read', 'evidence:read',
    'screening:read'. Kept as real rows (not a hard-coded choices list) so
    new scopes can be added without a migration on APIKey itself.
    """
    key = models.SlugField(max_length=60, unique=True)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['key']

    def __str__(self):
        return self.key


def _generate_key() -> str:
    """Return a 64-char hex API key (32 random bytes)."""
    return os.urandom(32).hex()


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of the raw key."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


class APIKey(models.Model):
    """
    Issued API key for institutional subscribers.

    The raw key is shown ONCE at creation — it is never stored.
    Only the SHA-256 hash is persisted for verification.
    """
    name        = models.CharField(max_length=200, help_text='Descriptive label (client name / purpose)')
    key_hash    = models.CharField(max_length=64, unique=True, editable=False)
    prefix      = models.CharField(max_length=8, editable=False,
                                   help_text='First 8 chars of raw key — for identification in logs')
    tier        = models.CharField(max_length=20, choices=TIER_CHOICES, default='explorer')
    owner       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='api_keys')
    organisation = models.CharField(max_length=200, blank=True,
                                    help_text='Free-text label — see owner_organisation for the real FK link')

    # ── Commercial platform linkage (added on top of the pre-existing model) ──
    owner_organisation = models.ForeignKey(
        'ecoiq_commerce.Organisation', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='api_keys', help_text='Organisation this key bills/entitles against, if any')
    plan = models.ForeignKey(
        'ecoiq_commerce.Plan', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='api_keys', help_text='Commercial plan governing this key\'s entitlements')
    scopes = models.ManyToManyField(APIScope, blank=True, related_name='keys')
    environment = models.CharField(max_length=10, choices=ENVIRONMENT_CHOICES, default='sandbox')

    notes       = models.TextField(blank=True)

    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    last_used   = models.DateTimeField(null=True, blank=True)
    expires_at  = models.DateTimeField(null=True, blank=True,
                                       help_text='Null = never expires')
    revoked_at  = models.DateTimeField(null=True, blank=True,
                                       help_text='Explicit revocation timestamp — distinct from is_active so '
                                                  'the audit trail shows WHEN a key stopped working, not just that it did')
    rotated_from = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='rotated_to', help_text='The key this one replaced, if rotated')

    # Usage counters (updated by throttle backend)
    total_requests = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'

    def __str__(self):
        return f'{self.prefix}… ({self.tier}) — {self.name}'

    def revoke(self):
        from django.utils import timezone
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=['is_active', 'revoked_at'])

    def rotate(self) -> tuple['APIKey', str]:
        """
        Revokes this key and issues a replacement with identical tier/owner/
        organisation/scopes/environment/plan. Returns (new_key, raw_key) —
        same one-time-reveal contract as create_key().
        """
        new_key, raw_key = APIKey.create_key(
            name=self.name, tier=self.tier, owner=self.owner,
            owner_organisation=self.owner_organisation, plan=self.plan,
            environment=self.environment, organisation=self.organisation,
            rotated_from=self,
        )
        new_key.scopes.set(self.scopes.all())
        self.revoke()
        return new_key, raw_key

    @classmethod
    def create_key(cls, name: str, tier: str = 'explorer', **kwargs) -> tuple['APIKey', str]:
        """
        Create and return (APIKey instance, raw_key).
        The raw_key is the ONLY time the plain key is available — store it securely.
        """
        raw_key  = _generate_key()
        instance = cls.objects.create(
            name=name,
            tier=tier,
            key_hash=_hash_key(raw_key),
            prefix=raw_key[:8],
            **kwargs,
        )
        return instance, raw_key

    @classmethod
    def verify(cls, raw_key: str) -> 'APIKey | None':
        """Return the active APIKey for a raw key string, or None."""
        from django.utils import timezone
        key_hash = _hash_key(raw_key)
        try:
            key = cls.objects.get(key_hash=key_hash, is_active=True)
        except cls.DoesNotExist:
            return None

        # Check expiry
        if key.expires_at and key.expires_at < timezone.now():
            return None

        # Update last_used asynchronously-ish (non-critical, allowed to fail)
        try:
            cls.objects.filter(pk=key.pk).update(
                last_used=timezone.now(),
                total_requests=models.F('total_requests') + 1,
            )
        except Exception:
            pass

        return key


class APIRequestLog(models.Model):
    """
    Per-request audit trail for commercially-metered endpoints. Populated by
    api.logging_mixin.APIRequestLoggingMixin — applied to the new PART 4
    endpoints (api/commercial_views.py) rather than retrofitted onto every
    pre-existing view, to avoid changing established endpoints' behaviour.
    """
    key = models.ForeignKey(APIKey, on_delete=models.SET_NULL, null=True, blank=True, related_name='request_logs')
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    status_code = models.PositiveSmallIntegerField()
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['key', 'created_at'])]

    def __str__(self):
        return f'{self.method} {self.endpoint} -> {self.status_code}'
