from django.contrib import admin

from ai_agent_council.models import (
    AgentHandoff, AgentTask, CouncilDecision, CouncilDisagreement, CouncilRun,
    CrossExaminationExchange, DecisionMemoryEntry,
)


@admin.register(CouncilRun)
class CouncilRunAdmin(admin.ModelAdmin):
    list_display = ('title', 'task_category', 'status', 'is_simulated', 'created_at')
    list_filter = ('status', 'is_simulated', 'task_category')
    search_fields = ('title', 'question', 'slug')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display = ('agent_name', 'run', 'collaboration_mode', 'status', 'confidence', 'order')
    list_filter = ('collaboration_mode', 'status', 'agent_name')
    search_fields = ('agent_name', 'position_summary')


@admin.register(AgentHandoff)
class AgentHandoffAdmin(admin.ModelAdmin):
    list_display = ('sender_agent', 'receiver_agent', 'run', 'confidence_at_handoff', 'order')
    list_filter = ('sender_agent', 'receiver_agent')


@admin.register(CouncilDisagreement)
class CouncilDisagreementAdmin(admin.ModelAdmin):
    list_display = ('run', 'conflict_type', 'resolution_method', 'minority_opinion_retained')
    list_filter = ('conflict_type', 'resolution_method', 'minority_opinion_retained')


@admin.register(CrossExaminationExchange)
class CrossExaminationExchangeAdmin(admin.ModelAdmin):
    list_display = ('run', 'questioner_agent', 'target_agent', 'challenge_type', 'sequence')
    list_filter = ('questioner_agent', 'target_agent')


@admin.register(CouncilDecision)
class CouncilDecisionAdmin(admin.ModelAdmin):
    list_display = ('run', 'status', 'confidence', 'human_approval_required', 'human_approved')
    list_filter = ('status', 'human_approval_required', 'human_approved')


@admin.register(DecisionMemoryEntry)
class DecisionMemoryEntryAdmin(admin.ModelAdmin):
    list_display = ('decision', 'reopened', 'reopened_at')
    list_filter = ('reopened',)
