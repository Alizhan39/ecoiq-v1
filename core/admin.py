from django.contrib import admin
from django.utils.html import format_html
from .models import Assessment, QuestionnaireResponse, Finding


# ── Helpers ───────────────────────────────────────────────────────────────────

def _score_badge(score):
    """Return a coloured HTML badge for a pillar score."""
    if score >= 81:
        colour = '#2d6a4f'; bg = '#d8f3dc'; label = 'Exemplary'
    elif score >= 61:
        colour = '#1d6434'; bg = '#b7e4c7'; label = 'Good'
    elif score >= 41:
        colour = '#7a5c00'; bg = '#fef9c3'; label = 'Developing'
    elif score >= 21:
        colour = '#8b3a00'; bg = '#ffe8cc'; label = 'Minimal'
    else:
        colour = '#7c2020'; bg = '#ffe0e0'; label = 'Critical'
    return format_html(
        '<span style="background:{};color:{};padding:2px 8px;border-radius:12px;'
        'font-size:11px;font-weight:600;">{} · {}</span>',
        bg, colour, score, label
    )


# ── Inlines ───────────────────────────────────────────────────────────────────

class QuestionnaireResponseInline(admin.TabularInline):
    model         = QuestionnaireResponse
    extra         = 0
    fields        = ('question_key', 'question_text', 'answer')
    readonly_fields = ('question_key', 'question_text')
    can_delete    = False
    show_change_link = False
    verbose_name  = 'Q&A Response'
    verbose_name_plural = 'Questionnaire Responses'


class FindingInline(admin.StackedInline):
    model   = Finding
    extra   = 0
    fields  = (
        ('score_environment', 'score_social', 'score_governance',
         'score_ethics', 'score_innovation', 'score_overall'),
        'summary', 'pillar_notes', 'created_at',
    )
    readonly_fields = ('created_at',)


# ── Assessment ────────────────────────────────────────────────────────────────

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display    = ('company_name', 'status_badge', 'overall_score', 'created_at', 'updated_at')
    list_filter     = ('status', 'created_at')
    search_fields   = ('company_name', 'notes', 'extracted_text')
    ordering        = ('-created_at',)
    date_hierarchy  = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    inlines         = [QuestionnaireResponseInline, FindingInline]

    fieldsets = (
        ('Facility', {
            'fields': ('company_name', 'status', 'notes'),
        }),
        ('Document', {
            'fields': ('uploaded_file', 'extracted_text'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colours = {
            'draft':      ('#6c757d', '#e9ecef'),
            'ready':      ('#1b4332', '#d8f3dc'),
            'processing': ('#664d03', '#fff3cd'),
            'complete':   ('#fff',    '#2d6a4f'),
            'error':      ('#7c2020', '#ffe0e0'),
        }
        fg, bg = colours.get(obj.status, ('#333', '#eee'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 10px;border-radius:12px;'
            'font-size:11px;font-weight:600;">{}</span>',
            bg, fg, obj.get_status_display()
        )

    @admin.display(description='Overall Score', ordering='finding__score_overall')
    def overall_score(self, obj):
        try:
            return _score_badge(obj.finding.score_overall)
        except Finding.DoesNotExist:
            return format_html('<span style="color:#aaa;font-size:11px;">—</span>')


# ── Finding ───────────────────────────────────────────────────────────────────

@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display  = (
        'assessment', 'overall_badge',
        'env_badge', 'soc_badge', 'gov_badge', 'eth_badge', 'inn_badge',
        'created_at',
    )
    list_filter   = ('created_at',)
    search_fields = ('assessment__company_name', 'summary')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Assessment', {
            'fields': ('assessment',),
        }),
        ('Pillar Scores', {
            'fields': (
                ('score_environment', 'score_social', 'score_governance'),
                ('score_ethics', 'score_innovation', 'score_overall'),
            ),
        }),
        ('Narrative', {
            'fields': ('summary', 'pillar_notes'),
        }),
        ('Raw', {
            'fields': ('raw_ai_response',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def _badge(self, score, label):
        return _score_badge(score) if score is not None else format_html('—')

    @admin.display(description='Overall')
    def overall_badge(self, obj): return _score_badge(obj.score_overall)

    @admin.display(description='Env')
    def env_badge(self, obj): return _score_badge(obj.score_environment)

    @admin.display(description='Social')
    def soc_badge(self, obj): return _score_badge(obj.score_social)

    @admin.display(description='Gov')
    def gov_badge(self, obj): return _score_badge(obj.score_governance)

    @admin.display(description='Ethics')
    def eth_badge(self, obj): return _score_badge(obj.score_ethics)

    @admin.display(description='Innovation')
    def inn_badge(self, obj): return _score_badge(obj.score_innovation)
