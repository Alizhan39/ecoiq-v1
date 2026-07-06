from django.contrib import admin

from financial_intelligence_cloud.models import (
    AdvisoryOpportunity, InstitutionalAccount, OpportunityFeedItem, Portfolio,
    PortfolioDailyBrief, PortfolioEntity, PortfolioSignal,
)


@admin.register(InstitutionalAccount)
class InstitutionalAccountAdmin(admin.ModelAdmin):
    list_display = ('firm_name', 'account_type', 'subscription_tier', 'is_demo', 'created_at')
    list_filter = ('account_type', 'subscription_tier', 'is_demo')
    search_fields = ('firm_name', 'slug')


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('name', 'institutional_account', 'portfolio_type', 'entity_count', 'assets_under_analysis', 'currency_display')
    list_filter = ('portfolio_type',)
    search_fields = ('name',)

    def currency_display(self, obj):
        return obj.assets_under_analysis_currency
    currency_display.short_description = 'Currency'


@admin.register(PortfolioEntity)
class PortfolioEntityAdmin(admin.ModelAdmin):
    list_display = ('name', 'portfolio', 'entity_type', 'relationship_stage', 'is_flagship')
    list_filter = ('entity_type', 'relationship_stage', 'is_flagship')
    search_fields = ('name', 'sector')


@admin.register(PortfolioSignal)
class PortfolioSignalAdmin(admin.ModelAdmin):
    list_display = ('title', 'portfolio_entity', 'signal_type', 'capital_at_risk', 'evidence_quality', 'status')
    list_filter = ('signal_type', 'evidence_quality', 'status', 'human_approval_required')


@admin.register(AdvisoryOpportunity)
class AdvisoryOpportunityAdmin(admin.ModelAdmin):
    list_display = ('headline', 'portfolio_entity', 'opportunity_type', 'priority_score', 'status')
    list_filter = ('opportunity_type', 'status')


@admin.register(OpportunityFeedItem)
class OpportunityFeedItemAdmin(admin.ModelAdmin):
    list_display = ('headline', 'institutional_account', 'item_type', 'occurred_at')
    list_filter = ('item_type',)


@admin.register(PortfolioDailyBrief)
class PortfolioDailyBriefAdmin(admin.ModelAdmin):
    list_display = ('institutional_account', 'brief_date', 'new_signals_count', 'human_approvals_pending')
    list_filter = ('brief_date',)
