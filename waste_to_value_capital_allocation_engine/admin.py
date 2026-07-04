from django.contrib import admin

from waste_to_value_capital_allocation_engine.models import (
    CapitalAllocationDecision, CapitalRouteMatch, FundingGap, InterventionOption,
    InterventionScenario, LossEvidence, OperationalLoss, VerifiedCapitalOutcome,
)


@admin.register(OperationalLoss)
class OperationalLossAdmin(admin.ModelAdmin):
    list_display = ('title', 'loss_type', 'financial_loss_amount', 'currency', 'status', 'created_at')
    list_filter = ('loss_type', 'status', 'evidence_quality', 'finance_readiness', 'mrv_readiness')
    search_fields = ('title', 'organisation', 'asset', 'project')


@admin.register(LossEvidence)
class LossEvidenceAdmin(admin.ModelAdmin):
    list_display = ('evidence_reference', 'operational_loss', 'evidence_quality', 'public_private_status')
    list_filter = ('evidence_quality', 'public_private_status')


@admin.register(InterventionOption)
class InterventionOptionAdmin(admin.ModelAdmin):
    list_display = ('title', 'operational_loss', 'intervention_type', 'capex_estimate', 'estimated_payback_months', 'status')
    list_filter = ('intervention_type', 'status', 'risk_level', 'finance_readiness')


@admin.register(InterventionScenario)
class InterventionScenarioAdmin(admin.ModelAdmin):
    list_display = ('scenario_name', 'intervention', 'sensitivity_case', 'capex', 'payback')
    list_filter = ('sensitivity_case', 'scenario_type')


@admin.register(FundingGap)
class FundingGapAdmin(admin.ModelAdmin):
    list_display = ('intervention', 'total_capital_required', 'remaining_gap', 'status')
    list_filter = ('status',)


@admin.register(CapitalRouteMatch)
class CapitalRouteMatchAdmin(admin.ModelAdmin):
    list_display = ('funding_gap', 'route_type', 'suitability_score', 'eligibility_status', 'outreach_status')
    list_filter = ('route_type', 'eligibility_status', 'outreach_status')


@admin.register(CapitalAllocationDecision)
class CapitalAllocationDecisionAdmin(admin.ModelAdmin):
    list_display = ('intervention', 'ranking', 'approval_status', 'confidence', 'created_at')
    list_filter = ('approval_status',)


@admin.register(VerifiedCapitalOutcome)
class VerifiedCapitalOutcomeAdmin(admin.ModelAdmin):
    list_display = ('intervention', 'mrv_status', 'verified_status', 'public_reporting_ready')
    list_filter = ('mrv_status', 'verified_status', 'public_reporting_ready')
