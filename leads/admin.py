from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import AccessRequest, ProfileClaim, NewsletterSignup, ReviewRequest


STATUS_COLOURS = {
    'new':           ('#1b4332', '#d8f3dc'),
    'reviewed':      ('#0c3a6b', '#dde5f4'),
    'sample_sent':   ('#4a1d8a', '#ede9fe'),
    'call_booked':   ('#854d0e', '#fef9c3'),
    'proposal_sent': ('#0a4f4a', '#ccfbf1'),
    'won':           ('#fff',    '#10b981'),
    'lost':          ('#7c2020', '#ffe0e0'),
}

REPORT_STATUS_COLOURS = {
    'not_started':  ('#333',    '#e5e7eb'),
    'draft_needed': ('#854d0e', '#fef9c3'),
    'draft_ready':  ('#0c3a6b', '#dde5f4'),
    'sent':         ('#4a1d8a', '#ede9fe'),
    'paid_request': ('#0a4f4a', '#ccfbf1'),
    'closed':       ('#fff',    '#10b981'),
}


@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):

    list_display  = (
        'full_name', 'work_email', 'company', 'country',
        'role', 'product_interest', 'status_badge', 'report_status_badge',
        'created_at',
    )
    list_filter   = ('status', 'report_status', 'role', 'product_interest', 'country', 'created_at')
    search_fields = (
        'full_name', 'work_email', 'company', 'target_entity',
        'sector', 'message', 'internal_notes',
    )
    list_editable = ()
    ordering      = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('draft_preview_link', 'client_preview_link', 'ip_address', 'created_at', 'updated_at')

    fieldsets = (
        ('Lead details', {
            'fields': ('full_name', 'work_email', 'company', 'country', 'role'),
        }),
        ('Project / company to assess', {
            'fields': ('target_entity', 'sector', 'challenge', 'message'),
            'description': 'What the requester wants assessed and any context they provided.',
        }),
        ('Product interest', {
            'fields': ('product_interest',),
        }),
        ('Lead status', {
            'fields': ('status',),
            'description': 'Sales pipeline stage. Not visible to the requester.',
        }),
        ('Draft report preparation', {
            'fields': (
                'draft_preview_link', 'client_preview_link', 'report_status',
                'draft_score_summary', 'draft_risk_summary',
                'draft_recommendations', 'draft_roadmap',
            ),
            'description': 'Prepare the Investor Readiness Report draft from this lead, '
                           'then open the internal draft preview or the client-facing preview.',
        }),
        ('Internal notes', {
            'fields': ('notes', 'internal_notes'),
            'description': 'Internal team / analyst notes — never shown to the requester.',
        }),
        ('Legacy facility profile', {
            'fields': ('industry', 'facility_type', 'company_size'),
            'classes': ('collapse',),
            'description': 'Older industrial-audit fields — optional, retained for back-compatibility.',
        }),
        ('Security & timestamps', {
            'fields': ('ip_address', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Industry', ordering='industry')
    def industry_display(self, obj):
        return obj.get_industry_display()

    @admin.display(description='Lead status', ordering='status')
    def status_badge(self, obj):
        fg, bg = STATUS_COLOURS.get(obj.status, ('#333', '#eee'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 10px;border-radius:12px;'
            'font-size:11px;font-weight:600;white-space:nowrap;">{}</span>',
            bg, fg, obj.get_status_display()
        )

    @admin.display(description='Report status', ordering='report_status')
    def report_status_badge(self, obj):
        fg, bg = REPORT_STATUS_COLOURS.get(obj.report_status, ('#333', '#eee'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 10px;border-radius:12px;'
            'font-size:11px;font-weight:600;white-space:nowrap;">{}</span>',
            bg, fg, obj.get_report_status_display()
        )

    @admin.display(description='Draft report preview')
    def draft_preview_link(self, obj):
        """Read-only link to the staff-only internal draft report preview page."""
        if obj.pk is None:
            return format_html('<span style="color:#888;">Save the lead first to enable preview.</span>')
        url = reverse('admin_report_preview', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank" rel="noopener" '
            'style="background:#1b4332;color:#fff;padding:6px 14px;border-radius:6px;'
            'text-decoration:none;font-weight:600;">View draft report preview ↗</a>',
            url,
        )

    @admin.display(description='Client report preview')
    def client_preview_link(self, obj):
        """Read-only link to the staff-only client-facing report preview page."""
        if obj.pk is None:
            return format_html('<span style="color:#888;">Save the lead first to enable preview.</span>')
        url = reverse('client_report_preview', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank" rel="noopener" '
            'style="background:#c9a84c;color:#0a0f14;padding:6px 14px;border-radius:6px;'
            'text-decoration:none;font-weight:700;">View client report preview ↗</a>',
            url,
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


# ── NewsletterSignup admin ────────────────────────────────────────────────────

@admin.register(NewsletterSignup)
class NewsletterSignupAdmin(admin.ModelAdmin):
    list_display   = ('email', 'name', 'organisation', 'interest', 'source', 'is_active', 'signed_up_at')
    list_filter    = ('interest', 'is_active', 'signed_up_at')
    search_fields  = ('email', 'name', 'organisation')
    list_editable  = ('is_active',)
    ordering       = ('-signed_up_at',)
    date_hierarchy = 'signed_up_at'
    readonly_fields = ('signed_up_at',)


# ── ReviewRequest admin ───────────────────────────────────────────────────────

REVIEW_STATUS_COLOURS = {
    'new':       ('#1b4332', '#d8f3dc'),
    'reviewing': ('#0c3a6b', '#dde5f4'),
    'contacted': ('#4a1d8a', '#ede9fe'),
    'complete':  ('#fff',    '#10b981'),
    'declined':  ('#7c2020', '#ffe0e0'),
}


@admin.register(ReviewRequest)
class ReviewRequestAdmin(admin.ModelAdmin):

    list_display = (
        'name', 'organisation', 'email', 'country',
        'sector_display', 'request_type_display', 'status_badge',
        'status', 'has_report', 'created_at',
    )
    list_filter   = ('status', 'request_type', 'sector', 'created_at')
    search_fields = ('name', 'organisation', 'email', 'country', 'message', 'notes')
    list_editable = ('status',)
    ordering      = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('ip_address', 'created_at', 'updated_at')

    fieldsets = (
        ('Contact', {
            'fields': ('name', 'organisation', 'email', 'country'),
        }),
        ('Review Specification', {
            'fields': ('sector', 'request_type', 'message', 'sustainability_report'),
        }),
        ('CRM', {
            'fields': ('status', 'notes'),
            'description': 'Internal status and team notes — not visible to the submitter.',
        }),
        ('Security & Timestamps', {
            'fields': ('ip_address', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Sector', ordering='sector')
    def sector_display(self, obj):
        return obj.get_sector_display()

    @admin.display(description='Review Type', ordering='request_type')
    def request_type_display(self, obj):
        return obj.get_request_type_display()

    @admin.display(description='Report', boolean=True)
    def has_report(self, obj):
        return bool(obj.sustainability_report)

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        fg, bg = REVIEW_STATUS_COLOURS.get(obj.status, ('#333', '#eee'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 10px;border-radius:12px;'
            'font-size:11px;font-weight:600;white-space:nowrap;">{}</span>',
            bg, fg, obj.get_status_display()
        )
