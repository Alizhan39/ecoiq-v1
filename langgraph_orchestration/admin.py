from django.contrib import admin

from langgraph_orchestration.models import OrchestrationRun


@admin.register(OrchestrationRun)
class OrchestrationRunAdmin(admin.ModelAdmin):
    list_display = (
        'target_repr', 'target_type', 'status', 'confidence',
        'human_review_required', 'failed_node', 'created_at',
    )
    list_filter = ('status', 'target_type', 'human_review_required')
    search_fields = ('target_repr', 'target_reference', 'user_request', 'celery_task_id')
    readonly_fields = (
        'user_request', 'target_type', 'target_repr', 'target_reference', 'status', 'confidence',
        'human_review_required', 'nodes_executed', 'failed_node', 'error_summary', 'result',
        'celery_task_id', 'created_at', 'completed_at',
    )

    def has_add_permission(self, request):
        return False  # rows are only ever created by the orchestrator, never by hand
