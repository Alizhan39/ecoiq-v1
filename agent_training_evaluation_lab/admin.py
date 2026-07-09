"""
agent_training_evaluation_lab/admin.py — Django Admin visibility for
evaluation runs, golden datasets, regressions, human feedback and
improvement recommendations. The smallest stable solution, matching every
other Phase 1 module in this platform — no second observability dashboard.
"""
from django.contrib import admin, messages

from agent_training_evaluation_lab.models import (
    AgentEvaluationRun, AgentHumanFeedback, AgentRegression, GoldenDatasetCase, ImprovementRecommendation,
)


@admin.register(GoldenDatasetCase)
class GoldenDatasetCaseAdmin(admin.ModelAdmin):
    list_display = ('case_id', 'agent', 'case_type', 'title', 'dataset_version', 'is_active', 'synced_at')
    list_filter = ('case_type', 'is_active', 'agent')
    search_fields = ('case_id', 'title', 'agent__agent_name')
    readonly_fields = ('synced_at',)

    def has_add_permission(self, request):
        return False  # rows are only ever created by sync_golden_dataset(), never by hand


@admin.register(AgentEvaluationRun)
class AgentEvaluationRunAdmin(admin.ModelAdmin):
    list_display = (
        'agent', 'evaluation_version', 'overall_score_display', 'delta_display',
        'runs_evaluated_count', 'golden_pass_display', 'started_at',
    )
    list_filter = ('evaluation_version', 'agent')
    search_fields = ('agent__agent_name',)
    readonly_fields = (
        'agent', 'evaluation_version', 'metrics', 'overall_score', 'runs_evaluated_count',
        'golden_cases_checked', 'golden_cases_passed', 'failure_reasons',
        'previous_evaluation', 'score_delta', 'started_at', 'completed_at',
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description='Overall score')
    def overall_score_display(self, obj):
        return f'{obj.overall_score:.1f}' if obj.overall_score is not None else 'NOT YET MEASURED'

    @admin.display(description='vs previous')
    def delta_display(self, obj):
        delta = (obj.score_delta or {}).get('overall_score')
        if delta is None:
            return '—'
        return f'+{delta}' if delta >= 0 else str(delta)

    @admin.display(description='Golden cases')
    def golden_pass_display(self, obj):
        if obj.golden_cases_checked == 0:
            return '—'
        return f'{obj.golden_cases_passed}/{obj.golden_cases_checked}'


@admin.register(AgentRegression)
class AgentRegressionAdmin(admin.ModelAdmin):
    list_display = ('agent', 'metric_name', 'previous_value', 'current_value', 'threshold', 'severity', 'is_acknowledged', 'detected_at')
    list_filter = ('severity', 'is_acknowledged', 'metric_name', 'agent')
    search_fields = ('agent__agent_name', 'metric_name')
    readonly_fields = ('agent', 'evaluation_run', 'metric_name', 'previous_value', 'current_value', 'threshold', 'severity', 'detected_at')
    actions = ['acknowledge_selected']

    def has_add_permission(self, request):
        return False

    @admin.action(description='Acknowledge selected regressions')
    def acknowledge_selected(self, request, queryset):
        updated = queryset.update(is_acknowledged=True, acknowledged_by=request.user)
        self.message_user(request, f'Acknowledged {updated} regression(s). No production agent was modified.', level=messages.SUCCESS)


@admin.register(AgentHumanFeedback)
class AgentHumanFeedbackAdmin(admin.ModelAdmin):
    list_display = ('agent_run', 'classification', 'reviewer', 'created_at')
    list_filter = ('classification',)
    search_fields = ('agent_run__agent__agent_name', 'notes')
    readonly_fields = ('created_at',)

    def save_model(self, request, obj, form, change):
        if not obj.reviewer_id:
            obj.reviewer = request.user
        super().save_model(request, obj, form, change)


@admin.register(ImprovementRecommendation)
class ImprovementRecommendationAdmin(admin.ModelAdmin):
    list_display = ('agent', 'recommendation_type', 'status', 'created_at')
    list_filter = ('recommendation_type', 'status', 'agent')
    search_fields = ('agent__agent_name', 'description')
    readonly_fields = ('agent', 'recommendation_type', 'description', 'based_on', 'created_at')
    actions = ['mark_acknowledged', 'mark_dismissed']

    def has_add_permission(self, request):
        return False

    @admin.action(description='Mark selected as acknowledged')
    def mark_acknowledged(self, request, queryset):
        queryset.update(status='ACKNOWLEDGED')

    @admin.action(description='Mark selected as dismissed')
    def mark_dismissed(self, request, queryset):
        queryset.update(status='DISMISSED')
