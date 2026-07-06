from django.contrib import admin

from khalifa_stewardship_tour_operating_system.models import (
    StewardshipIntervention, StewardshipProblem, StewardshipTour, TourFundingPlan,
    TourLegacyRecord, TourLocalPartner, TourMRVPlan, TourParticipantRole,
)


@admin.register(StewardshipTour)
class StewardshipTourAdmin(admin.ModelAdmin):
    list_display = ('title', 'tour_type', 'status', 'country', 'safety_level', 'created_at')
    list_filter = ('tour_type', 'status', 'safety_level')
    search_fields = ('title', 'region')


@admin.register(StewardshipProblem)
class StewardshipProblemAdmin(admin.ModelAdmin):
    list_display = ('title', 'tour', 'problem_type', 'evidence_quality', 'urgency_score', 'status')
    list_filter = ('problem_type', 'evidence_quality', 'status')


@admin.register(StewardshipIntervention)
class StewardshipInterventionAdmin(admin.ModelAdmin):
    list_display = ('title', 'problem', 'intervention_type', 'capex_estimate', 'status')
    list_filter = ('intervention_type', 'status', 'implementation_complexity')


@admin.register(TourFundingPlan)
class TourFundingPlanAdmin(admin.ModelAdmin):
    list_display = ('tour', 'total_required', 'funding_gap', 'status')
    list_filter = ('status',)


@admin.register(TourParticipantRole)
class TourParticipantRoleAdmin(admin.ModelAdmin):
    list_display = ('role_name', 'tour', 'supervision_required')


@admin.register(TourLocalPartner)
class TourLocalPartnerAdmin(admin.ModelAdmin):
    list_display = ('partner_name', 'tour', 'partner_type', 'due_diligence_status', 'approval_status')
    list_filter = ('partner_type', 'due_diligence_status', 'approval_status')


@admin.register(TourMRVPlan)
class TourMRVPlanAdmin(admin.ModelAdmin):
    list_display = ('tour', 'verification_status', 'public_reporting_ready')
    list_filter = ('verification_status',)


@admin.register(TourLegacyRecord)
class TourLegacyRecordAdmin(admin.ModelAdmin):
    list_display = ('tour', 'mrv_status', 'public_private_status', 'financial_value_recovered')
    list_filter = ('mrv_status', 'public_private_status')
