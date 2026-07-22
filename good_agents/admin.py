from django.contrib import admin

from good_agents.models import (
    AgentActivationRecord, AvailableResource, CrossBorderAssessment, FundingMatch, GoodAgentDefinition,
    GoodDeedAction, GoodDiscoveryRun, GoodMission, GoodOpportunity, HumanReviewDecision, ImpactReceipt, Need,
    OpportunityCostAssessment, RedTeamReview, ResourceMatch, ResourceStatusChange, SignalCluster, SignalProvider,
    WorldSignal, ZeroCapitalStrategyAction,
)


@admin.register(GoodAgentDefinition)
class GoodAgentDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        'principle_id', 'name', 'category', 'definition_quality', 'requires_human_review',
        'activation_status', 'arabic_name_review_status', 'is_active',
    )
    list_filter = ('category', 'definition_quality', 'requires_human_review', 'activation_status', 'is_active')
    search_fields = ('name', 'mission')


class AgentActivationRecordInline(admin.TabularInline):
    model = AgentActivationRecord
    extra = 0
    readonly_fields = ('agent', 'reason_activated', 'position', 'confidence', 'cost_usd', 'latency_ms')
    can_delete = False


class GoodDeedActionInline(admin.TabularInline):
    model = GoodDeedAction
    extra = 0


@admin.register(GoodOpportunity)
class GoodOpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'theme', 'status', 'confidence', 'urgency', 'zero_capital_possible', 'created_at')
    list_filter = ('theme', 'status', 'zero_capital_possible', 'insufficient_evidence')
    search_fields = ('title', 'problem_statement')
    inlines = [AgentActivationRecordInline, GoodDeedActionInline]


@admin.register(GoodDiscoveryRun)
class GoodDiscoveryRunAdmin(admin.ModelAdmin):
    list_display = (
        'mission', 'status', 'signals_reviewed', 'opportunities_detected',
        'qualified_opportunities', 'zero_capital_opportunities', 'estimated_run_cost_usd', 'created_at',
    )
    list_filter = ('status',)
    readonly_fields = (
        'signals_reviewed', 'agents_activated', 'opportunities_detected', 'qualified_opportunities',
        'zero_capital_opportunities', 'estimated_run_cost_usd', 'errors', 'started_at', 'completed_at',
    )


@admin.register(OpportunityCostAssessment)
class OpportunityCostAssessmentAdmin(admin.ModelAdmin):
    list_display = ('opportunity', 'preferred_option', 'confidence', 'created_at')


@admin.register(RedTeamReview)
class RedTeamReviewAdmin(admin.ModelAdmin):
    list_display = ('opportunity', 'cleared', 'reviewer', 'reviewed_at')
    list_filter = ('cleared',)


@admin.register(GoodDeedAction)
class GoodDeedActionAdmin(admin.ModelAdmin):
    list_display = ('opportunity', 'action_type', 'autonomy_class', 'status', 'human_approved')
    list_filter = ('autonomy_class', 'status', 'action_type')


@admin.register(ImpactReceipt)
class ImpactReceiptAdmin(admin.ModelAdmin):
    list_display = ('opportunity', 'confidence', 'created_at')


@admin.register(GoodMission)
class GoodMissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'enabled', 'run_cost_budget_usd', 'min_confidence', 'max_opportunities')
    list_filter = ('enabled', 'risk_tolerance')


@admin.register(SignalProvider)
class SignalProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider_type', 'trust_tier', 'status', 'last_refresh_at')
    list_filter = ('provider_type', 'trust_tier', 'status')


@admin.register(SignalCluster)
class SignalClusterAdmin(admin.ModelAdmin):
    list_display = ('representative_title', 'signal_type', 'geography', 'status', 'confidence_boost')
    list_filter = ('signal_type', 'status')


@admin.register(WorldSignal)
class WorldSignalAdmin(admin.ModelAdmin):
    list_display = ('title', 'signal_type', 'content_classification', 'status', 'confidence', 'created_at')
    list_filter = ('signal_type', 'content_classification', 'status')
    search_fields = ('title', 'summary')


@admin.register(Need)
class NeedAdmin(admin.ModelAdmin):
    list_display = ('title', 'need_type', 'status', 'urgency', 'region')
    list_filter = ('need_type', 'status')


@admin.register(AvailableResource)
class AvailableResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'resource_type', 'availability', 'status', 'confidence', 'region')
    list_filter = ('resource_type', 'availability', 'status')


@admin.register(ResourceMatch)
class ResourceMatchAdmin(admin.ModelAdmin):
    list_display = ('need', 'resource', 'confidence', 'is_circular_economy_match', 'created_at')
    list_filter = ('is_circular_economy_match',)


@admin.register(ResourceStatusChange)
class ResourceStatusChangeAdmin(admin.ModelAdmin):
    list_display = ('resource', 'previous_status', 'new_status', 'changed_at')


@admin.register(FundingMatch)
class FundingMatchAdmin(admin.ModelAdmin):
    list_display = ('opportunity', 'funder_type', 'eligibility_status', 'created_at')
    list_filter = ('funder_type', 'eligibility_status')


@admin.register(ZeroCapitalStrategyAction)
class ZeroCapitalStrategyActionAdmin(admin.ModelAdmin):
    list_display = ('opportunity', 'action_type', 'rank')


@admin.register(HumanReviewDecision)
class HumanReviewDecisionAdmin(admin.ModelAdmin):
    list_display = ('opportunity', 'decision', 'reviewer', 'created_at')
    list_filter = ('decision',)


@admin.register(CrossBorderAssessment)
class CrossBorderAssessmentAdmin(admin.ModelAdmin):
    list_display = ('opportunity', 'origin_geography', 'candidate_geography', 'confidence')
