from django.contrib import admin
from django.utils.html import format_html
from .models import AccessRequest, ProfileClaim


STATUS_COLOURS = {
    'new':            ('#1b4332', '#d8f3dc'),
    'contacted':      ('#0c3a6b', '#dde5f4'),
    'qualified':      ('#4a1d8a', '#ede9fe'),
    'demo_scheduled': ('#854d0e', '#fef9c3'),
    'pilot_active':   ('#fff',    '#10b981'),
    'declined':       ('#7c2020', '#ffe0e0'),
}


@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):

    list_display  = (
        'full_name', 'company', 'work_email',
        'industry_display', 'company_size', 'status', 'status_badge',
        'created_at',
    )
    list_filter   = ('status', 'industry', 'company_size', 'created_at')
    search_fields = ('full_name', 'company', 'work_email', 'challenge', 'message', 'notes')
    list_editable = ('status',)   # inline status update — useful for bulk pipeline management
    ordering      = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('ip_address', 'created_at', 'updated_at')

    fieldsets = (
        ('Contact', {
            'fields': ('full_name', 'company', 'work_email'),
        }),
        ('Facility Profile', {
            'fields': ('industry', 'facility_type', 'company_size'),
        }),
        ('Qualification', {
            'fields': ('challenge', 'message'),
            'description': 'Operational challenge and additional context provided by the applicant.',
        }),
        ('CRM', {
            'fields': ('status', 'notes'),
            'description': 'Internal status tracking and team notes. Not visible to the applicant.',
        }),
        ('Security & Timestamps', {
            'fields': ('ip_address', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Industry', ordering='industry')
    def industry_display(self, obj):
        return obj.get_industry_display()

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        fg, bg = STATUS_COLOURS.get(obj.status, ('#333', '#eee'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 10px;border-radius:12px;'
            'font-size:11px;font-weight:600;white-space:nowrap;">{}</span>',
            bg, fg, obj.get_status_display()
        )


# ── ProfileClaim admin ────────────────────────────────────────────────────────

CLAIM_STATUS_COLOURS = {
    'pending':   ('#854d0e', '#fef9c3'),
    'approved':  ('#fff',    '#10b981'),
    'rejected':  ('#7c2020', '#ffe0e0'),
    'duplicate': ('#333',    '#e5e7eb'),
}


@admin.register(ProfileClaim)
class ProfileClaimAdmin(admin.ModelAdmin):

    list_display = (
        'ref', 'full_name', 'work_email', 'job_title',
        'company_name_reported', 'company_slug',
        'status_badge', 'status', 'created_at',
    )
    list_filter   = ('status', 'created_at')
    search_fields = ('ref', 'full_name', 'work_email', 'job_title',
                     'company_slug', 'company_name_reported', 'message', 'notes')
    list_editable = ('status',)
    ordering      = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('ref', 'ip_address', 'created_at', 'updated_at')

    fieldsets = (
        ('Claim Reference', {
            'fields': ('ref',),
        }),
        ('Company Being Claimed', {
            'fields': ('company_slug', 'company_name_reported'),
            'description': 'EcoIQ slug (auto-populated from company page) and name as entered by the claimant.',
        }),
        ('Claimant Contact', {
            'fields': ('full_name', 'work_email', 'job_title', 'phone'),
        }),
        ('Justification', {
            'fields': ('message',),
            'description': 'Why the claimant believes they are entitled to manage this profile.',
        }),
        ('CRM', {
            'fields': ('status', 'notes'),
            'description': 'Internal status and team notes. Not visible to the claimant.',
        }),
        ('Security & Timestamps', {
            'fields': ('ip_address', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        fg, bg = CLAIM_STATUS_COLOURS.get(obj.status, ('#333', '#eee'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 10px;border-radius:12px;'
            'font-size:11px;font-weight:600;white-space:nowrap;">{}</span>',
            bg, fg, obj.get_status_display()
        )
