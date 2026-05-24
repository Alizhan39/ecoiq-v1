from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone as tz

from .models import (
    AuditSession, AuditResponse, Finding, Recommendation, ActionPlan, AuditReport,
    AIAnalysisJob, AIFinding, AIScoreEstimate,
)


class AuditResponseInline(admin.TabularInline):
    model = AuditResponse
    extra = 0


class FindingInline(admin.TabularInline):
    model = Finding
    extra = 0
    readonly_fields = ('loss_usd',)


class RecommendationInline(admin.TabularInline):
    model = Recommendation
    extra = 0
    fields = ('order', 'priority', 'category', 'title', 'savings_usd', 'cost_usd', 'roi_months', 'is_quick_win')


class ActionPlanInline(admin.TabularInline):
    model = ActionPlan
    extra = 0


@admin.register(AuditSession)
class AuditSessionAdmin(admin.ModelAdmin):
    list_display  = ('facility_name', 'sector', 'status', 'created_at')
    list_filter   = ('status', 'sector')
    search_fields = ('facility_name', 'location')
    readonly_fields = ('created_at', 'updated_at', 'extracted_text')
    inlines       = [AuditResponseInline, FindingInline, RecommendationInline, ActionPlanInline]


@admin.register(AuditReport)
class AuditReportAdmin(admin.ModelAdmin):
    list_display  = ('session', 'overall_efficiency_score', 'modernization_score',
                     'total_savings_potential', 'blended_roi_months', 'created_at')
    readonly_fields = ('created_at',)


# ═══════════════════════════════════════════════════════════════════════════════
# AI FINDINGS ENGINE ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

def _conf_badge(score):
    """Coloured confidence badge for admin list views."""
    if score is None: return '—'
    pct = round(score * 100)
    if score >= 0.85:
        color, bg = '#2d6a4f', '#d8f3dc'
    elif score >= 0.60:
        color, bg = '#c87941', '#fce9d4'
    else:
        color, bg = '#c0392b', '#ffe0e3'
    return format_html(
        '<span style="background:{bg};color:{c};border:1px solid {c}44;'
        'padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;">{p}%</span>',
        bg=bg, c=color, p=pct,
    )


def _status_badge(status):
    MAP = {
        'pending':    ('#9a7d0a', '#fef9e7', '⏳'),
        'approved':   ('#2d6a4f', '#d8f3dc', '✓'),
        'rejected':   ('#922b21', '#f9ebea', '✗'),
        'applied':    ('#1a5276', '#d6eaf8', '→'),
        'processing': ('#7d3c98', '#f5eef8', '⟳'),
        'completed':  ('#2d6a4f', '#d8f3dc', '✓'),
        'failed':     ('#922b21', '#f9ebea', '✗'),
    }
    color, bg, icon = MAP.get(status, ('#666', '#f5f5f5', '?'))
    return format_html(
        '<span style="background:{bg};color:{c};border:1px solid {c}44;'
        'padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;">{i} {s}</span>',
        bg=bg, c=color, i=icon, s=status.title(),
    )


# ── Admin actions ─────────────────────────────────────────────────────────────

@admin.action(description='▶ Run AI analysis')
def action_run_analysis(modeladmin, request, queryset):
    from .ai_engine import run_ai_analysis
    for job in queryset.exclude(status='processing'):
        try:
            run_ai_analysis(job)
            modeladmin.message_user(
                request,
                f'✓ {job.original_filename}: {job.finding_count} findings.'
            )
        except Exception as exc:
            job.status        = 'failed'
            job.error_message = str(exc)
            job.save(update_fields=['status', 'error_message'])
            modeladmin.message_user(request, f'✗ {job.original_filename}: {exc}', level='error')


@admin.action(description='✓ Approve all pending findings')
def action_approve_all_findings(modeladmin, request, queryset):
    total = 0
    for job in queryset:
        count = job.findings.filter(status='pending').update(
            status='approved', reviewed_at=tz.now(),
        )
        total += count
    modeladmin.message_user(request, f'{total} finding(s) approved across selected jobs.')


# ── Inlines ───────────────────────────────────────────────────────────────────

class AIFindingInline(admin.TabularInline):
    model  = AIFinding
    extra  = 0
    fields = ('finding_type', 'title', 'confidence_score', 'status', 'analyst_notes')
    readonly_fields = ('finding_type', 'title', 'confidence_score')
    can_delete = False
    max_num = 0  # read-only inline
    show_change_link = True


class AIScoreEstimateInline(admin.StackedInline):
    model       = AIScoreEstimate
    extra       = 0
    can_delete  = False
    max_num     = 1
    fields      = (
        ('est_pollution', 'est_reduction', 'est_investment'),
        ('est_transparency', 'est_community', 'est_ecoiq'),
        'confidence', 'greenwashing_level', 'greenwashing_score',
        'reasoning', 'data_gaps',
        'approved', 'analyst_notes',
    )
    readonly_fields = ('est_ecoiq', 'confidence')


# ── Job admin ─────────────────────────────────────────────────────────────────

@admin.register(AIAnalysisJob)
class AIAnalysisJobAdmin(admin.ModelAdmin):
    list_display  = (
        'id', 'filename_col', 'company', 'status_col',
        'findings_col', 'tokens_col', 'greenwash_col',
        'created_at',
    )
    list_filter   = ('status', 'detected_doc_type', 'detected_year')
    search_fields = ('original_filename', 'detected_company_name', 'company__name')
    ordering      = ('-created_at',)
    actions       = [action_run_analysis, action_approve_all_findings]
    inlines       = [AIScoreEstimateInline, AIFindingInline]

    readonly_fields = (
        'status', 'created_at', 'started_at', 'completed_at',
        'model_used', 'pages_analyzed', 'chars_analyzed',
        'input_tokens', 'output_tokens',
        'detected_company_name', 'detected_doc_type', 'detected_year',
        'executive_summary', 'data_quality_notes',
        'error_message', 'raw_response',
    )

    fieldsets = (
        ('Document', {
            'fields': ('pdf_file', 'original_filename', 'company', 'submitted_by'),
        }),
        ('Status', {
            'fields': ('status', 'created_at', 'started_at', 'completed_at', 'error_message'),
        }),
        ('AI Telemetry', {
            'fields': ('model_used', 'pages_analyzed', 'chars_analyzed',
                       'input_tokens', 'output_tokens'),
            'classes': ('collapse',),
        }),
        ('Extracted Metadata', {
            'fields': ('detected_company_name', 'detected_doc_type', 'detected_year',
                       'executive_summary', 'data_quality_notes'),
        }),
        ('Analyst Notes', {
            'fields': ('analyst_notes',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('findings').select_related('company')

    @admin.display(description='File')
    def filename_col(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-size:12px;">{}</span>',
            obj.original_filename[:50],
        )

    @admin.display(description='Status')
    def status_col(self, obj):
        return _status_badge(obj.status)

    @admin.display(description='Findings')
    def findings_col(self, obj):
        total = obj.findings.count()
        pend  = obj.findings.filter(status='pending').count()
        appr  = obj.findings.filter(status='approved').count()
        return format_html(
            '<span title="{t} total">'
            '<b style="color:#2d6a4f;">{a}✓</b> '
            '<span style="color:#9a7d0a;">{p}⏳</span> '
            '/ {t}'
            '</span>',
            t=total, a=appr, p=pend,
        )

    @admin.display(description='Tokens')
    def tokens_col(self, obj):
        total = obj.input_tokens + obj.output_tokens
        if not total:
            return '—'
        return format_html(
            '<span style="font-size:11px;color:#666;">{:,}</span>', total,
        )

    @admin.display(description='🚨 Greenwash')
    def greenwash_col(self, obj):
        try:
            se = obj.score_estimate
        except AIScoreEstimate.DoesNotExist:
            return '—'
        COLORS = {
            'low': '#2d6a4f', 'medium': '#c87941',
            'high': '#c0392b', 'critical': '#922b21',
        }
        color = COLORS.get(se.greenwashing_level, '#666')
        return format_html(
            '<span style="color:{c};font-weight:700;font-size:11px;">{l}</span>',
            c=color, l=(se.greenwashing_level or '—').title(),
        )


# ── Finding admin ─────────────────────────────────────────────────────────────

@admin.register(AIFinding)
class AIFindingAdmin(admin.ModelAdmin):
    list_display  = (
        'id', 'finding_type', 'title_col', 'confidence_col',
        'status_col', 'reviewed_by', 'job',
    )
    list_filter   = ('finding_type', 'status', 'job')
    search_fields = ('title', 'description', 'source_quote')
    ordering      = ('-confidence_score',)
    actions       = ['approve_findings', 'reject_findings']

    readonly_fields = ('job', 'finding_type', 'created_at', 'reviewed_at')

    fieldsets = (
        ('Finding', {
            'fields': ('job', 'finding_type', 'title', 'description'),
        }),
        ('Quantitative Data', {
            'fields': ('numeric_value', 'unit', 'year'),
        }),
        ('Source (Extraction Highlighting)', {
            'fields': ('source_quote', 'source_location'),
            'description': 'Verbatim text from the document where this finding was extracted.',
        }),
        ('AI Confidence', {
            'fields': ('confidence_score',),
        }),
        ('Review Workflow', {
            'fields': ('status', 'analyst_notes', 'reviewed_by', 'reviewed_at'),
        }),
        ('Extra Data', {
            'fields': ('extra_data',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Title')
    def title_col(self, obj):
        return format_html(
            '<span style="font-size:12px;">{}</span>', obj.title[:70],
        )

    @admin.display(description='Confidence')
    def confidence_col(self, obj):
        return _conf_badge(obj.confidence_score)

    @admin.display(description='Status')
    def status_col(self, obj):
        return _status_badge(obj.status)

    @admin.action(description='✓ Approve selected findings')
    def approve_findings(self, request, queryset):
        count = queryset.update(status='approved', reviewed_by=request.user, reviewed_at=tz.now())
        self.message_user(request, f'{count} finding(s) approved.')

    @admin.action(description='✗ Reject selected findings')
    def reject_findings(self, request, queryset):
        count = queryset.update(status='rejected', reviewed_by=request.user, reviewed_at=tz.now())
        self.message_user(request, f'{count} finding(s) rejected.')


# ── Score estimate admin ───────────────────────────────────────────────────────

@admin.register(AIScoreEstimate)
class AIScoreEstimateAdmin(admin.ModelAdmin):
    list_display  = (
        'job', 'ecoiq_col', 'confidence_col',
        'greenwash_col', 'approved_col', 'applied_at',
    )
    list_filter   = ('approved', 'greenwashing_level')
    readonly_fields = ('job', 'created_at', 'applied_at', 'approved_by')

    fieldsets = (
        ('Score Estimates (0–100)', {
            'fields': (
                ('est_pollution', 'est_reduction', 'est_investment'),
                ('est_transparency', 'est_community', 'est_ecoiq'),
                'confidence', 'reasoning', 'data_gaps',
            ),
        }),
        ('Greenwashing Risk', {
            'fields': (
                'greenwashing_level', 'greenwashing_score',
                'greenwashing_signals', 'greenwashing_verdict',
            ),
        }),
        ('Approval', {
            'fields': ('approved', 'approved_by', 'applied_at', 'analyst_notes'),
        }),
    )

    @admin.display(description='EcoIQ ≈')
    def ecoiq_col(self, obj):
        v = obj.est_ecoiq
        if v is None: return '—'
        return format_html('<b style="color:#2d6a4f;">{}</b>', round(v, 1))

    @admin.display(description='Confidence')
    def confidence_col(self, obj):
        return _conf_badge(obj.confidence)

    @admin.display(description='Greenwash')
    def greenwash_col(self, obj):
        COLORS = {
            'low': '#2d6a4f', 'medium': '#c87941',
            'high': '#c0392b', 'critical': '#922b21',
        }
        color = COLORS.get(obj.greenwashing_level, '#666')
        return format_html(
            '<span style="color:{c};font-weight:700;">{l}</span>',
            c=color, l=(obj.greenwashing_level or '—').title(),
        )

    @admin.display(description='Approved', boolean=True)
    def approved_col(self, obj):
        return obj.approved
