"""
EcoIQ Ethics Admin — Analyst Workflow Interface.

Provides admin tools for:
  - Reviewing and approving CompanyEthicsProfile master scores
  - Inspecting per-formula scores (FormulaScore)
  - Managing improvement milestones (ImprovementMilestone)
  - Adding/reviewing analyst notes (AnalystNote)
  - Managing the formula registry (FormulaDefinition)
"""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    FormulaDefinition, CompanyEthicsProfile,
    FormulaScore, ImprovementMilestone, AnalystNote,
)


# ── FormulaDefinition ─────────────────────────────────────────────────────────

@admin.register(FormulaDefinition)
class FormulaDefinitionAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'category', 'master_formula',
                     'maqasid_principle', 'weight', 'is_public', 'is_active', 'order')
    list_filter   = ('category', 'master_formula', 'maqasid_principle',
                     'is_public', 'is_active')
    search_fields = ('code', 'name', 'description')
    ordering      = ('category', 'order', 'code')
    list_editable = ('weight', 'is_public', 'is_active', 'order')

    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'category', 'master_formula',
                       'is_public', 'is_active', 'order', 'weight'),
        }),
        ('Description & Methodology', {
            'fields': ('description', 'methodology_notes'),
        }),
        ('Input Specification', {
            'fields': ('input_fields',),
            'classes': ('collapse',),
        }),
        ('Maqasid Mapping (Internal)', {
            'fields': ('maqasid_principle', 'maqasid_notes'),
            'classes': ('collapse',),
            'description': (
                'Internal mapping to universal preservation principles. '
                'Do NOT expose this terminology in public-facing UI.'
            ),
        }),
    )


# ── Inlines ───────────────────────────────────────────────────────────────────

class FormulaScoreInline(admin.TabularInline):
    model         = FormulaScore
    extra         = 0
    readonly_fields = ('formula', 'raw_value', 'normalized_score', 'confidence',
                       'analyst_adjusted', 'computed_at')
    fields        = ('formula', 'normalized_score', 'confidence',
                     'evidence_verified', 'analyst_adjusted', 'analyst_override',
                     'analyst_reason', 'computed_at')
    ordering      = ('formula__category', 'formula__order')
    can_delete    = False


class MilestoneInline(admin.TabularInline):
    model         = ImprovementMilestone
    extra         = 0
    fields        = ('title', 'pillar', 'expected_score_gain', 'effort_level',
                     'timeline_months', 'status', 'priority')
    ordering      = ('priority', 'order')


class AnalystNoteInline(admin.StackedInline):
    model         = AnalystNote
    extra         = 1
    fields        = ('note_type', 'note', 'formula_score', 'is_public', 'author')
    readonly_fields = ('created_at',)


# ── CompanyEthicsProfile ──────────────────────────────────────────────────────

def _score_bar(score: float, color: str = '#00e89a') -> str:
    """Tiny HTML progress bar for list view."""
    width = max(0, min(100, score))
    return format_html(
        '<div style="display:flex;align-items:center;gap:6px;">'
        '<div style="width:80px;height:6px;background:#21262d;border-radius:3px;overflow:hidden;">'
        '<div style="width:{}%;height:100%;background:{};border-radius:3px;"></div>'
        '</div>'
        '<span style="font-size:0.8rem;font-weight:700;">{:.1f}</span>'
        '</div>',
        width, color, score,
    )


@admin.register(CompanyEthicsProfile)
class CompanyEthicsProfileAdmin(admin.ModelAdmin):
    list_display  = ('company_name', 'nei_bar', 'tss_bar', 'rvi_bar',
                     'composite_score', 'ethics_tier_badge',
                     'analyst_reviewed', 'analyst_approved',
                     'data_confidence_pct', 'last_computed')
    list_filter   = ('analyst_reviewed', 'analyst_approved', 'formula_version',
                     'profile__pollution_level', 'profile__status')
    search_fields = ('profile__company__name',)
    readonly_fields = ('last_computed', 'net_ethical_impact',
                       'transition_stewardship', 'regenerative_value',
                       'total_benefit_score', 'total_harm_score',
                       'composite_ethics_score_display', 'ethics_tier_display_field',
                       'data_confidence')
    ordering      = ('-last_computed',)

    actions = ['action_approve', 'action_recompute']

    fieldsets = (
        ('Company', {
            'fields': ('profile',),
        }),
        ('Master Scores', {
            'fields': (
                'net_ethical_impact', 'transition_stewardship', 'regenerative_value',
                'total_benefit_score', 'total_harm_score',
                'composite_ethics_score_display', 'ethics_tier_display_field',
            ),
        }),
        ('KPI Intelligence', {
            'fields': (
                'key_harms', 'key_benefits', 'next_best_actions',
                'expected_score_improvement', 'data_confidence',
            ),
            'classes': ('collapse',),
        }),
        ('Analyst Workflow', {
            'fields': (
                'analyst_reviewed', 'analyst_approved', 'analyst_reviewed_at',
                'analyst_reviewer', 'analyst_notes_text',
            ),
        }),
        ('Metadata', {
            'fields': ('last_computed', 'formula_version'),
            'classes': ('collapse',),
        }),
    )

    inlines = [FormulaScoreInline, MilestoneInline, AnalystNoteInline]

    # ── Custom list columns ────────────────────────────────────────────────────

    @admin.display(description='Company', ordering='profile__company__name')
    def company_name(self, obj):
        return obj.profile.company.name

    @admin.display(description='NEI')
    def nei_bar(self, obj):
        return format_html(_score_bar(obj.net_ethical_impact, '#00e89a'))

    @admin.display(description='TSS')
    def tss_bar(self, obj):
        return format_html(_score_bar(obj.transition_stewardship, '#58a6ff'))

    @admin.display(description='RVI')
    def rvi_bar(self, obj):
        return format_html(_score_bar(obj.regenerative_value, '#8b5cf6'))

    @admin.display(description='Composite')
    def composite_score(self, obj):
        return f'{obj.composite_ethics_score:.1f}'

    @admin.display(description='Tier')
    def ethics_tier_badge(self, obj):
        color = obj.ethics_tier_color
        return format_html(
            '<span style="background:{};color:#000;padding:2px 8px;'
            'border-radius:10px;font-size:0.72rem;font-weight:700;">{}</span>',
            color, obj.ethics_tier_display,
        )

    @admin.display(description='Confidence')
    def data_confidence_pct(self, obj):
        return f'{obj.data_confidence * 100:.0f}%'

    # ── Readonly display fields ────────────────────────────────────────────────

    @admin.display(description='Composite Ethics Score')
    def composite_ethics_score_display(self, obj):
        return f'{obj.composite_ethics_score:.1f} / 100'

    @admin.display(description='Ethics Tier')
    def ethics_tier_display_field(self, obj):
        return obj.ethics_tier_display

    # ── Admin actions ──────────────────────────────────────────────────────────

    @admin.action(description='✓ Approve selected ethics profiles')
    def action_approve(self, request, queryset):
        updated = 0
        for ep in queryset:
            ep.mark_reviewed(request.user, approve=True)
            updated += 1
        self.message_user(request, f'{updated} ethics profile(s) approved.')

    @admin.action(description='⟳ Recompute ethics scores')
    def action_recompute(self, request, queryset):
        from ethics.scoring import compute_and_save
        updated = 0
        errors  = 0
        for ep in queryset:
            try:
                compute_and_save(ep.profile)
                updated += 1
            except Exception as exc:
                errors += 1
                self.message_user(
                    request,
                    f'Error recomputing {ep.profile.company.name}: {exc}',
                    level='ERROR',
                )
        if updated:
            self.message_user(request, f'{updated} ethics profile(s) recomputed.')


# ── FormulaScore ──────────────────────────────────────────────────────────────

@admin.register(FormulaScore)
class FormulaScoreAdmin(admin.ModelAdmin):
    list_display  = ('formula_code', 'company_name', 'normalized_score',
                     'confidence', 'evidence_verified', 'analyst_adjusted')
    list_filter   = ('formula__category', 'evidence_verified', 'analyst_adjusted')
    search_fields = ('formula__code', 'formula__name',
                     'ethics_profile__profile__company__name')
    readonly_fields = ('computed_at',)

    @admin.display(description='Formula', ordering='formula__code')
    def formula_code(self, obj):
        return obj.formula.code

    @admin.display(description='Company')
    def company_name(self, obj):
        return obj.ethics_profile.profile.company.name


# ── ImprovementMilestone ──────────────────────────────────────────────────────

@admin.register(ImprovementMilestone)
class ImprovementMilestoneAdmin(admin.ModelAdmin):
    list_display  = ('title', 'company_name', 'pillar', 'expected_score_gain',
                     'effort_level', 'timeline_months', 'status', 'priority')
    list_filter   = ('status', 'effort_level', 'formula_category',
                     'maqasid_principle')
    search_fields = ('title', 'ethics_profile__profile__company__name')
    list_editable = ('status', 'priority')
    ordering      = ('priority', 'order')

    @admin.display(description='Company')
    def company_name(self, obj):
        return obj.ethics_profile.profile.company.name


# ── AnalystNote ───────────────────────────────────────────────────────────────

@admin.register(AnalystNote)
class AnalystNoteAdmin(admin.ModelAdmin):
    list_display  = ('note_type', 'company_name', 'author', 'is_public', 'created_at')
    list_filter   = ('note_type', 'is_public')
    search_fields = ('note', 'ethics_profile__profile__company__name')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Company')
    def company_name(self, obj):
        return obj.ethics_profile.profile.company.name
