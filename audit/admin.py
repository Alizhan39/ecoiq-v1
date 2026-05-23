from django.contrib import admin
from .models import AuditSession, AuditResponse, Finding, Recommendation, ActionPlan, AuditReport


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
