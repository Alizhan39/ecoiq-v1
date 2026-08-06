"""Central Notifications admin — one place to triage every incoming submission."""
from datetime import timedelta

from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Count
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
    list_display = ('status_dot', 'title_display', 'spam_badge', 'source_type',
                    'source_endpoint', 'priority_badge', 'contact_name',
                    'email_domain_display', 'duplicate_count', 'created_at', 'open_link')
    list_display_links = ('title_display',)
    list_filter = ('spam_status', 'status', 'source_type', 'source_endpoint',
                   'priority', 'created_at')
    search_fields = ('title', 'message', 'contact_name', 'contact_email', 'phone',
                     'fingerprint')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('source_type', 'source_model', 'source_object_id', 'admin_url',
                       'contact_name', 'contact_email', 'phone', 'metadata',
                       'created_at', 'read_at', 'open_link',
                       'risk_reasons', 'fingerprint', 'source_endpoint',
                       'classified_at', 'classified_by', 'previous_status')
    list_per_page = 50
    actions = ('mark_read', 'mark_unread', 'archive',
               'mark_as_spam', 'mark_legitimate', 'restore_from_review')

    fieldsets = (
        ('Notification', {'fields': ('title', 'message', 'status', 'priority')}),
        ('Contact', {'fields': ('contact_name', 'contact_email', 'phone')}),
        ('Source', {'fields': ('source_type', 'source_model', 'source_object_id', 'open_link', 'admin_url', 'metadata')}),
        ('Abuse screening', {
            'fields': ('spam_status', 'risk_reasons', 'source_endpoint',
                       'fingerprint', 'duplicate_count',
                       'classified_at', 'classified_by', 'previous_status'),
            'description': ('Deterministic screening result. "Unclassified" means the '
                            'record predates screening.'),
        }),
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

    @admin.display(description='Screening', ordering='spam_status')
    def spam_badge(self, obj):
        fg, bg = {
            'accepted':     ('#065f46', '#d1fae5'),
            'legitimate':   ('#065f46', '#a7f3d0'),
            'review':       ('#854d0e', '#fef3c7'),
            'rejected':     ('#fff',    '#dc2626'),
            'archived':     ('#555',    '#e9ecef'),
            'unclassified': ('#555',    '#f3f4f6'),
        }.get(obj.spam_status, ('#333', '#eee'))
        label = obj.get_spam_status_display()
        if obj.risk_reasons:
            label = f'{label} ({len(obj.risk_reasons)})'
        return format_html('<span title="{}" style="background:{};color:{};padding:2px 9px;'
                           'border-radius:11px;font-size:11px;font-weight:700;">{}</span>',
                           ', '.join(obj.risk_reasons or []) or 'no risk signals', bg, fg, label)

    @admin.display(description='Domain')
    def email_domain_display(self, obj):
        return obj.email_domain or '—'

    def changelist_view(self, request, extra_context=None):
        """Counters for the last 24 hours, shown above the list."""
        since = timezone.now() - timedelta(days=1)
        today = AdminNotification.objects.filter(created_at__gte=since)
        counts = dict(today.values_list('spam_status').annotate(n=Count('id')))
        reasons = {}
        for row in today.exclude(risk_reasons=[]).values_list('risk_reasons', flat=True):
            for code in (row or []):
                reasons[code] = reasons.get(code, 0) + 1
        extra_context = extra_context or {}
        extra_context['antispam_counters'] = {
            'accepted_today': counts.get('accepted', 0),
            'reviewed_today': counts.get('review', 0),
            'rejected_today': counts.get('rejected', 0),
            'blocked_turnstile': sum(v for k, v in reasons.items() if k.startswith('turnstile_')),
            'blocked_rate_limit': sum(v for k, v in reasons.items() if k.startswith('rate_limit_')),
            'blocked_duplicate': reasons.get('duplicate_submission', 0),
        }
        return super().changelist_view(request, extra_context)

    def has_delete_permission(self, request, obj=None):
        """
        Only superusers may delete. Ordinary staff triaging 900+ spam records
        must not be one mis-click away from destroying evidence — archiving and
        the spam actions below are non-destructive and fully reversible.
        """
        return bool(request.user and request.user.is_superuser)

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

    def _reclassify(self, request, queryset, *, spam_status, verb):
        """Reversible bulk reclassification: the old status is recorded first."""
        updated = 0
        with transaction.atomic():
            for obj in queryset.select_for_update():
                obj.previous_status = obj.spam_status
                obj.spam_status = spam_status
                obj.classified_at = timezone.now()
                obj.classified_by = request.user.get_username()[:60]
                obj.save(update_fields=['previous_status', 'spam_status',
                                        'classified_at', 'classified_by'])
                updated += 1
        self.message_user(
            request,
            f'{updated} notification(s) {verb}. Nothing was deleted — use '
            f'"Restore previous classification" to undo.',
            level=messages.WARNING if spam_status == 'rejected' else messages.SUCCESS)

    @admin.action(description='Mark selected as SPAM (reversible, no delete)')
    def mark_as_spam(self, request, queryset):
        self._reclassify(request, queryset, spam_status='rejected', verb='marked as spam')

    @admin.action(description='Mark selected as legitimate')
    def mark_legitimate(self, request, queryset):
        self._reclassify(request, queryset, spam_status='legitimate', verb='marked legitimate')

    @admin.action(description='Restore previous classification')
    def restore_from_review(self, request, queryset):
        restored = 0
        with transaction.atomic():
            for obj in queryset.select_for_update().exclude(previous_status=''):
                obj.spam_status, obj.previous_status = obj.previous_status, obj.spam_status
                obj.classified_at = timezone.now()
                obj.classified_by = request.user.get_username()[:60]
                obj.save(update_fields=['spam_status', 'previous_status',
                                        'classified_at', 'classified_by'])
                restored += 1
        self.message_user(request, f'{restored} notification(s) restored.')

    # Auto-mark a notification as read when staff open its detail page.
    def change_view(self, request, object_id, form_url='', extra_context=None):
        try:
            obj = self.get_object(request, object_id)
            if obj and obj.status == 'unread':
                obj.mark_read()
        except Exception:
            pass
        return super().change_view(request, object_id, form_url, extra_context)
