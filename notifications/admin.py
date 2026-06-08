"""Central Notifications admin — one place to triage every incoming submission."""
from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import AdminNotification


PRIORITY_COLOURS = {
    'low':    ('#555',    '#e9ecef'),
    'normal': ('#0c3a6b', '#dde5f4'),
    'high':   ('#854d0e', '#fef3c7'),
    'urgent': ('#fff',    '#dc2626'),
}


@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    list_display = ('status_dot', 'title_display', 'source_type', 'priority_badge',
                    'contact_name', 'contact_email', 'created_at', 'open_link')
    list_display_links = ('title_display',)
    list_filter = ('status', 'source_type', 'priority', 'created_at')
    search_fields = ('title', 'message', 'contact_name', 'contact_email', 'phone')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('source_type', 'source_model', 'source_object_id', 'admin_url',
                       'contact_name', 'contact_email', 'phone', 'metadata',
                       'created_at', 'read_at', 'open_link')
    list_per_page = 50
    actions = ('mark_read', 'mark_unread', 'archive')

    fieldsets = (
        ('Notification', {'fields': ('title', 'message', 'status', 'priority')}),
        ('Contact', {'fields': ('contact_name', 'contact_email', 'phone')}),
        ('Source', {'fields': ('source_type', 'source_model', 'source_object_id', 'open_link', 'admin_url', 'metadata')}),
        ('Timestamps', {'fields': ('created_at', 'read_at'), 'classes': ('collapse',)}),
    )

    # ── Display helpers ─────────────────────────────────────────────────
    @admin.display(description='')
    def status_dot(self, obj):
        colour = {'unread': '#dc2626', 'read': '#9ca3af', 'archived': '#d1d5db'}.get(obj.status, '#9ca3af')
        return format_html('<span title="{}" style="display:inline-block;width:10px;height:10px;'
                           'border-radius:50%;background:{};"></span>', obj.get_status_display(), colour)

    @admin.display(description='Notification', ordering='title')
    def title_display(self, obj):
        weight = '700' if obj.status == 'unread' else '400'
        colour = '#111' if obj.status == 'unread' else '#6b7280'
        return format_html('<span style="font-weight:{};color:{};">{}</span>', weight, colour, obj.title)

    @admin.display(description='Priority', ordering='priority')
    def priority_badge(self, obj):
        fg, bg = PRIORITY_COLOURS.get(obj.priority, ('#333', '#eee'))
        return format_html('<span style="background:{};color:{};padding:2px 9px;border-radius:11px;'
                           'font-size:11px;font-weight:700;text-transform:uppercase;">{}</span>',
                           bg, fg, obj.get_priority_display())

    @admin.display(description='Open')
    def open_link(self, obj):
        if obj.admin_url:
            return format_html('<a class="button" href="{}" style="background:#1b4332;color:#fff;'
                               'padding:3px 10px;border-radius:5px;text-decoration:none;">Open →</a>', obj.admin_url)
        return '—'

    # ── Bulk actions ────────────────────────────────────────────────────
    @admin.action(description='Mark selected as read')
    def mark_read(self, request, queryset):
        n = queryset.filter(status='unread').update(status='read', read_at=timezone.now())
        self.message_user(request, f'{n} notification(s) marked as read.')

    @admin.action(description='Mark selected as unread')
    def mark_unread(self, request, queryset):
        n = queryset.update(status='unread', read_at=None)
        self.message_user(request, f'{n} notification(s) marked as unread.')

    @admin.action(description='Archive selected')
    def archive(self, request, queryset):
        n = queryset.update(status='archived')
        self.message_user(request, f'{n} notification(s) archived.')

    # Auto-mark a notification as read when staff open its detail page.
    def change_view(self, request, object_id, form_url='', extra_context=None):
        try:
            obj = self.get_object(request, object_id)
            if obj and obj.status == 'unread':
                obj.mark_read()
        except Exception:
            pass
        return super().change_view(request, object_id, form_url, extra_context)
