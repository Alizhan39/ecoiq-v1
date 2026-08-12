from django.contrib import admin

from .models import DeviceSession


@admin.register(DeviceSession)
class DeviceSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_name', 'platform', 'app_version', 'is_active_col',
                     'created_at', 'last_used_at', 'revoked_reason')
    list_filter = ('platform', 'revoked_reason', 'created_at')
    search_fields = ('user__username', 'device_id', 'device_name', 'ip_address')
    readonly_fields = ('refresh_token_hash', 'previous_refresh_token_hash', 'created_at',
                        'last_used_at', 'ip_address', 'user_agent')
    actions = ['revoke_sessions']

    @admin.display(description='Active', boolean=True)
    def is_active_col(self, obj):
        return obj.is_active

    @admin.action(description='Revoke selected sessions')
    def revoke_sessions(self, request, queryset):
        count = 0
        for session in queryset.filter(revoked_at__isnull=True):
            session.revoke(reason='admin_revoked')
            count += 1
        self.message_user(request, f'Revoked {count} session(s).')
