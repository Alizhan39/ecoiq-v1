"""
EcoIQ Quranic Decision Filter — Django Admin.
"""
from django.contrib import admin
from django.utils.html import format_html

from qdf.models import DecisionQuestion, DecisionAssessment, QuestionScore


@admin.register(DecisionQuestion)
class DecisionQuestionAdmin(admin.ModelAdmin):
    list_display  = ('order', 'arabic_term', 'title_en', 'core_question',
                     'weight', 'is_red_line', 'is_active')
    list_editable = ('weight', 'is_red_line', 'is_active')
    list_filter   = ('is_red_line', 'is_active')
    search_fields = ('key', 'arabic_term', 'title_en', 'core_question')
    ordering      = ('order',)
    readonly_fields = ('key',)
    fieldsets = (
        ('Identity', {'fields': ('key', 'order', 'arabic_term', 'title_en',
                                 'core_question', 'weight', 'is_red_line', 'is_active')}),
        ('Content', {'fields': ('definition', 'plain_english', 'scoring_rubric', 'ai_prompt')}),
        ('Evidence & Flags', {'fields': ('evidence_required', 'red_flags', 'low_score_actions')}),
        ('Worked Examples', {'fields': ('example_company', 'example_policy', 'example_investment'),
                             'classes': ('collapse',)}),
    )


class QuestionScoreInline(admin.TabularInline):
    model           = QuestionScore
    extra           = 0
    fields          = ('question', 'score', 'evidence_status', 'rationale')
    readonly_fields = ('question',)
    ordering        = ('question__order',)
    can_delete      = False
    max_num         = 10


@admin.register(DecisionAssessment)
class DecisionAssessmentAdmin(admin.ModelAdmin):
    list_display  = ('subject_name', 'subject_type', 'integrity_col', 'risk_col',
                     'verdict_col', 'evidence_status', 'source', 'analyst_reviewed',
                     'last_computed')
    list_filter   = ('subject_type', 'risk_level', 'verdict', 'evidence_status',
                     'source', 'analyst_reviewed', 'red_line_breached')
    search_fields = ('subject_name', 'subject_ref', 'profile__company__name')
    readonly_fields = ('last_computed', 'created_at', 'red_line_breached',
                       'rizq_without_zulm_summary')
    inlines = [QuestionScoreInline]
    actions = ['action_recompute']

    fieldsets = (
        ('Subject', {'fields': ('subject_type', 'subject_name', 'subject_ref', 'profile')}),
        ('Outcome', {'fields': ('decision_integrity_score', 'risk_level', 'verdict',
                                'evidence_status', 'confidence', 'red_line_breached',
                                'rizq_without_zulm_summary', 'ai_narrative')}),
        ('Workflow', {'fields': ('source', 'analyst_reviewed', 'analyst_notes',
                                 'created_by', 'created_at', 'last_computed')}),
    )

    def integrity_col(self, obj):
        return format_html(
            '<span style="font-weight:800;color:{}">{:.0f}</span>'
            '<span style="color:#666"> /100</span>',
            obj.integrity_color, obj.decision_integrity_score)
    integrity_col.short_description = 'Integrity'

    def risk_col(self, obj):
        return format_html('<span style="color:{};font-weight:700">{}</span>',
                           obj.risk_color, obj.get_risk_level_display())
    risk_col.short_description = 'Risk'

    def verdict_col(self, obj):
        return format_html('<span style="color:{};font-weight:700">{}</span>',
                           obj.verdict_color, obj.verdict_display)
    verdict_col.short_description = 'Verdict'

    def action_recompute(self, request, queryset):
        from qdf.scoring import compute_and_save
        count = 0
        for a in queryset.filter(source='auto', profile__isnull=False):
            try:
                compute_and_save(a.profile)
                count += 1
            except Exception:
                pass
        self.message_user(request, f'Recomputed {count} auto QDF assessment(s).')
    action_recompute.short_description = 'Recompute selected (auto) assessments'
