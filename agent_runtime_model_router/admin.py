from django.contrib import admin

from agent_runtime_model_router.models import AgentRegistryEntry, AgentRun


@admin.register(AgentRegistryEntry)
class AgentRegistryEntryAdmin(admin.ModelAdmin):
    list_display = ('agent_name', 'maturity_stage', 'enabled', 'is_next_stage', 'updated_at')
    list_filter = ('enabled', 'is_next_stage')
    search_fields = ('agent_name', 'agent_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'agent', 'task_type', 'execution_mode_requested', 'execution_mode_used',
        'status', 'safety_status', 'calibrated_confidence', 'created_at',
    )
    list_filter = ('execution_mode_requested', 'execution_mode_used', 'status', 'safety_status')
    search_fields = ('task_type', 'model_provider', 'model_name', 'idempotency_key')
    readonly_fields = ('created_at',)
