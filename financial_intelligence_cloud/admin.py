from django.contrib import admin

from financial_intelligence_cloud.models import (
    AccountingActivity, AccountingService, AdvisoryOpportunity, ClientPayment,
    ClientReminder, ClientService, InstitutionalAccount, OpportunityFeedItem,
    PaymentReceipt, Portfolio, PortfolioDailyBrief, PortfolioEntity, PortfolioSignal,
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


@admin.register(AccountingService)
class AccountingServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'institutional_account', 'frequency', 'default_fee', 'currency', 'is_active')
    list_filter = ('institutional_account', 'frequency', 'is_active')
    search_fields = ('name', 'code')


@admin.register(ClientService)
class ClientServiceAdmin(admin.ModelAdmin):
    list_display = ('client', 'service', 'assigned_to', 'status', 'next_due_date', 'agreed_fee', 'is_active')
    list_filter = ('status', 'is_active', 'service', 'assigned_to')
    search_fields = ('client__name', 'service__name', 'assigned_to__username')
    list_select_related = ('client', 'service', 'assigned_to')


@admin.register(ClientPayment)
class ClientPaymentAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'service_name', 'amount_due', 'amount_paid', 'currency', 'due_date', 'status')
    list_filter = ('status', 'currency', 'due_date')
    search_fields = ('client_service__client__name', 'client_service__service__name', 'reference')
    list_select_related = ('client_service__client', 'client_service__service')

    @admin.display(description='Client', ordering='client_service__client__name')
    def client_name(self, obj):
        return obj.client_service.client.name

    @admin.display(description='Service', ordering='client_service__service__name')
    def service_name(self, obj):
        return obj.client_service.service.name


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):
    list_display = ('received_at', 'client_name', 'amount', 'currency', 'payment_method', 'reference', 'recorded_by')
    list_filter = ('received_at', 'payment_method')
    search_fields = ('payment__client_service__client__name', 'reference', 'recorded_by__username')
    readonly_fields = ('payment', 'amount', 'received_at', 'payment_method', 'reference', 'recorded_by', 'created_at')

    @admin.display(description='Client')
    def client_name(self, obj):
        return obj.payment.client_service.client.name

    @admin.display(description='Currency')
    def currency(self, obj):
        return obj.payment.currency

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClientReminder)
class ClientReminderAdmin(admin.ModelAdmin):
    list_display = ('title', 'client_name', 'owner', 'due_at', 'priority', 'status')
    list_filter = ('priority', 'status', 'owner')
    search_fields = ('title', 'client__name', 'client_service__client__name')

    @admin.display(description='Client')
    def client_name(self, obj):
        client = obj.client or (obj.client_service.client if obj.client_service_id else None)
        return client.name if client else '—'


@admin.register(AccountingActivity)
class AccountingActivityAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'institutional_account', 'client', 'event_type', 'summary', 'actor')
    list_filter = ('institutional_account', 'event_type', 'created_at')
    search_fields = ('summary', 'client__name', 'actor__username')
    readonly_fields = (
        'institutional_account', 'client', 'client_service', 'actor',
        'event_type', 'summary', 'metadata', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
