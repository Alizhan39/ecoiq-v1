"""
EcoIQ Financing Intelligence — Django Admin.
"""
from django.contrib import admin
from django.utils.html import format_html

from financing.models import CompanyFinancingProfile, DirectFinancingMatch


# ── DirectFinancingMatch inline (FK is to CompanyProfile, used in that admin) ──

class DirectFinancingMatchInline(admin.TabularInline):
    """
    Used in CompanyProfile admin (companies app).
    DirectFinancingMatch.profile → CompanyProfile.
    """
    model           = DirectFinancingMatch
    fk_name         = 'profile'
    extra           = 0
    readonly_fields = (
        'opportunity', 'match_score', 'match_tier', 'match_rationale',
        'recommended_amount_usd', 'computed_at',
    )
    fields = readonly_fields
    can_delete = False
    show_change_link = True
    ordering = ('-match_score',)
    max_num = 10


# ── CompanyFinancingProfile admin ──────────────────────────────────────────────

@admin.register(CompanyFinancingProfile)
class CompanyFinancingProfileAdmin(admin.ModelAdmin):
    list_display = (
        'company_name', 'readiness_tier', 'financing_bar',
        'modernization_bar', 'transparency_bar', 'match_count_col',
        'funding_urgency', 'analyst_reviewed',
    )
    list_filter  = ('readiness_tier', 'funding_urgency', 'analyst_reviewed')
    search_fields = ('profile__company__name',)
    readonly_fields = (
        'last_computed', 'financing_readiness', 'modernization_readiness',
        'transparency_readiness', 'climate_readiness', 'governance_readiness',
        'evidence_completeness', 'capex_range_label', 'impact_label',
    )
    # Note: DirectFinancingMatch FK is to CompanyProfile, not CompanyFinancingProfile
    # so we don't use the inline here — view matches via DirectFinancingMatchAdmin

    fieldsets = (
        ('Company', {
            'fields': ('profile',),
        }),
        ('Readiness Scores', {
            'fields': (
                'financing_readiness', 'modernization_readiness', 'transparency_readiness',
                'climate_readiness', 'governance_readiness', 'evidence_completeness',
            ),
        }),
        ('Tier & Urgency', {
            'fields': ('readiness_tier', 'funding_urgency', 'confidence'),
        }),
        ('Financial Intelligence', {
            'fields': (
                'estimated_capex_low_usd', 'estimated_capex_high_usd',
                'estimated_annual_impact_usd', 'capex_range_label', 'impact_label',
            ),
        }),
        ('Gap Analysis', {
            'fields': ('missing_requirements', 'next_actions'),
            'classes': ('collapse',),
        }),
        ('AI Narrative', {
            'fields': ('ai_financing_narrative', 'ai_gap_analysis'),
            'classes': ('collapse',),
        }),
        ('Analyst Workflow', {
            'fields': ('analyst_reviewed', 'analyst_notes', 'last_computed'),
        }),
    )

    actions = ['action_recompute']

    def company_name(self, obj):
        return obj.profile.company.name
    company_name.short_description = 'Company'

    def _bar(self, val, color='#00e89a'):
        pct = min(max(float(val or 0), 0), 100)
        return format_html(
            '<div style="display:flex;align-items:center;gap:4px">'
            '<div style="width:70px;height:6px;background:#222;border-radius:3px;overflow:hidden">'
            '<div style="width:{}%;height:100%;background:{};border-radius:3px"></div></div>'
            '<span style="font-size:11px;color:#aaa">{:.0f}</span></div>',
            pct, color, pct,
        )

    def financing_bar(self, obj): return self._bar(obj.financing_readiness, '#00e89a')
    financing_bar.short_description = 'Financing'

    def modernization_bar(self, obj): return self._bar(obj.modernization_readiness, '#58a6ff')
    modernization_bar.short_description = 'Modernization'

    def transparency_bar(self, obj): return self._bar(obj.transparency_readiness, '#8b5cf6')
    transparency_bar.short_description = 'Transparency'

    def match_count_col(self, obj):
        eligible = obj.profile.financing_matches.filter(
            match_tier__in=['eligible', 'likely']
        ).count()
        total    = obj.profile.financing_matches.count()
        return format_html(
            '<span style="font-weight:700;color:#00e89a">{}</span>'
            '<span style="color:#555"> / {}</span>', eligible, total,
        )
    match_count_col.short_description = 'Eligible / Total'

    def capex_range_label(self, obj): return obj.capex_range_label
    capex_range_label.short_description = 'Capex Range'

    def impact_label(self, obj): return obj.impact_label
    impact_label.short_description = 'Est. Annual Impact'

    def action_recompute(self, request, queryset):
        from financing.matching import compute_and_save
        count = 0
        for fp in queryset:
            try:
                compute_and_save(fp.profile)
                count += 1
            except Exception:
                pass
        self.message_user(request, f'Recomputed financing profiles for {count} companies.')
    action_recompute.short_description = 'Recompute financing profiles'


# ── DirectFinancingMatch standalone admin ──────────────────────────────────────

@admin.register(DirectFinancingMatch)
class DirectFinancingMatchAdmin(admin.ModelAdmin):
    list_display  = (
        'company_name', 'opportunity', 'match_tier', 'score_col',
        'recommended_amount_label', 'computed_at',
    )
    list_filter   = ('match_tier', 'opportunity__source_type', 'is_featured')
    search_fields = ('profile__company__name', 'opportunity__institution_name')
    readonly_fields = ('computed_at',)

    def company_name(self, obj): return obj.profile.company.name
    company_name.short_description = 'Company'

    def score_col(self, obj):
        color = obj.tier_color
        return format_html(
            '<span style="font-weight:800;color:{}">{:.0f}</span>',
            color, obj.match_score,
        )
    score_col.short_description = 'Score'

    def recommended_amount_label(self, obj): return obj.recommended_amount_label
    recommended_amount_label.short_description = 'Est. Amount'
