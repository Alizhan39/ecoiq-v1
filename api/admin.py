"""
api/admin.py — Admin interface for API keys.

Key generation workflow:
  1. Click "+ Add API Key" in admin
  2. Fill name, tier, owner, organisation
  3. Save — the raw key is shown ONCE in a banner
  4. Copy the key and send it to the subscriber
"""
from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from .models import APIKey


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display   = ('prefix_col', 'name', 'organisation', 'tier_badge',
                      'is_active', 'total_requests', 'last_used', 'created_at')
    list_filter    = ('tier', 'is_active', 'created_at')
    search_fields  = ('name', 'organisation', 'prefix')
    readonly_fields = ('key_hash', 'prefix', 'total_requests', 'created_at',
                       'last_used', 'key_hint')
    list_editable  = ('is_active',)
    ordering       = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Key Identity', {
            'fields': ('key_hint', 'prefix', 'key_hash'),
            'description': (
                'The raw API key is shown ONCE after creation. '
                'The hash is stored for verification — the key cannot be recovered.'
            ),
        }),
        ('Subscriber', {
            'fields': ('name', 'tier', 'owner', 'organisation', 'notes'),
        }),
        ('Lifecycle', {
            'fields': ('is_active', 'expires_at', 'total_requests', 'last_used', 'created_at'),
        }),
    )

    def save_model(self, request, obj, form, change):
        """Generate key on creation; show raw key in a one-time message banner."""
        if not change:
            # New key — generate
            instance, raw_key = APIKey.create_key(
                name=obj.name,
                tier=obj.tier,
                owner=obj.owner,
                organisation=obj.organisation,
                notes=obj.notes,
            )
            # Replace obj with real instance (has key_hash / prefix)
            obj.pk       = instance.pk
            obj.key_hash = instance.key_hash
            obj.prefix   = instance.prefix
            messages.success(
                request,
                format_html(
                    '<strong>API key created.</strong> '
                    'Copy this key now — it will not be shown again:<br>'
                    '<code style="background:#1e293b;color:#00e89a;padding:.4rem .8rem;'
                    'border-radius:4px;font-size:1rem;letter-spacing:.05em">'
                    '{}</code>',
                    raw_key,
                ),
            )
            # Don't call super().save_model — already saved via create_key
            return
        super().save_model(request, obj, form, change)

    @admin.display(description='Prefix', ordering='prefix')
    def prefix_col(self, obj):
        return format_html(
            '<code style="color:#00e89a;font-family:monospace">{}…</code>', obj.prefix
        )

    @admin.display(description='Tier', ordering='tier')
    def tier_badge(self, obj):
        colors = {
            'explorer':     '#58a6ff',
            'professional': '#00e89a',
            'enterprise':   '#f4a261',
        }
        color = colors.get(obj.tier, '#94a3b8')
        return format_html(
            '<span style="color:{};font-weight:600;font-size:.8rem">{}</span>',
            color, obj.get_tier_display(),
        )

    @admin.display(description='Key')
    def key_hint(self, obj):
        if obj.pk:
            return format_html(
                '<code style="color:#64748b">{}…[hidden]</code>', obj.prefix or '?'
            )
        return 'Will be generated on save'
