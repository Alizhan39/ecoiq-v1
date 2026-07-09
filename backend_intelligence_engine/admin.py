"""
backend_intelligence_engine/admin.py — the Phase 1 admin operations
experience. Django Admin is the smallest stable solution here: a small,
authorised-staff-only list/retry view, not a bespoke dashboard.
"""
from django.contrib import admin, messages

from backend_intelligence_engine.models import BackgroundTaskRun

# task_type -> the Celery task to re-dispatch on retry. A plain dict, not a
# dynamic import-by-string registry — nine tasks total, no need for more.
_RETRY_TASK_BY_TYPE = {}


def _task_registry():
    if not _RETRY_TASK_BY_TYPE:
        from backend_intelligence_engine.tasks import (
            company_intelligence_refresh, detect_agent_regressions, geo_intelligence_refresh,
            ingest_enabled_sources, ingest_source, recalculate_scores_background, refresh_entity_evidence,
            refresh_evidence_memory, run_agent_benchmark, run_agent_evaluation, run_ai_analysis,
            run_langgraph_intelligence_workflow,
        )
        _RETRY_TASK_BY_TYPE.update({
            'company_intelligence_refresh': company_intelligence_refresh,
            'geo_intelligence_refresh': geo_intelligence_refresh,
            'ai_analysis': run_ai_analysis,
            'evidence_memory_refresh': refresh_evidence_memory,
            'intelligence_score_recalculation': recalculate_scores_background,
            'langgraph_intelligence_workflow': run_langgraph_intelligence_workflow,
            'ingest_source': ingest_source,
            'ingest_enabled_sources': ingest_enabled_sources,
            'refresh_entity_evidence': refresh_entity_evidence,
            'run_agent_evaluation': run_agent_evaluation,
            'run_agent_benchmark': run_agent_benchmark,
            'detect_agent_regressions': detect_agent_regressions,
        })
    return _RETRY_TASK_BY_TYPE


@admin.register(BackgroundTaskRun)
class BackgroundTaskRunAdmin(admin.ModelAdmin):
    list_display = (
        'target_repr', 'task_type', 'status', 'queued_at', 'duration_seconds', 'retry_count',
    )
    list_filter = ('task_type', 'status')
    search_fields = ('target_repr', 'target_reference', 'celery_task_id')
    readonly_fields = (
        'task_type', 'celery_task_id', 'target_repr', 'target_reference', 'task_kwargs',
        'queued_at', 'started_at', 'completed_at', 'failed_at', 'duration_seconds',
        'error_summary', 'retry_count', 'result_summary',
    )
    actions = ['retry_failed_tasks']

    def has_add_permission(self, request):
        return False  # rows are only ever created by tasks.py, never by hand

    @admin.action(description='Retry selected failed tasks')
    def retry_failed_tasks(self, request, queryset):
        registry = _task_registry()
        retried, skipped = 0, 0
        for run in queryset:
            if run.status != 'failed':
                skipped += 1
                continue
            task = registry.get(run.task_type)
            if task is None:
                skipped += 1
                continue
            task.delay(**run.task_kwargs)
            retried += 1
        if retried:
            self.message_user(request, f'Re-queued {retried} task(s).', level=messages.SUCCESS)
        if skipped:
            self.message_user(
                request, f'Skipped {skipped} task(s) — only failed tasks with a known type can be retried.',
                level=messages.WARNING,
            )
