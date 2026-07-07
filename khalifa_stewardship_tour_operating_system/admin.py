from django.contrib import admin

from khalifa_stewardship_tour_operating_system.models import (
    ConsentRecord, IncidentReport, LaunchChecklistItem, StewardshipIntervention,
    StewardshipProblem, StewardshipTour, SupplierQuote, TourBeneficiary, TourFundingPlan,
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
    list_display = (
        'partner_name', 'tour', 'partner_type', 'due_diligence_status', 'approval_status',
        'safeguarding_review_status', 'insurance_evidence_status', 'human_approved',
    )
    list_filter = (
        'partner_type', 'due_diligence_status', 'approval_status',
        'safeguarding_review_status', 'insurance_evidence_status', 'conflict_of_interest_status',
    )


@admin.register(TourMRVPlan)
class TourMRVPlanAdmin(admin.ModelAdmin):
    list_display = ('tour', 'verification_status', 'public_reporting_ready')
    list_filter = ('verification_status',)


@admin.register(TourLegacyRecord)
class TourLegacyRecordAdmin(admin.ModelAdmin):
    list_display = ('tour', 'mrv_status', 'public_private_status', 'financial_value_recovered')
    list_filter = ('mrv_status', 'public_private_status')


@admin.register(TourBeneficiary)
class TourBeneficiaryAdmin(admin.ModelAdmin):
    list_display = ('display_reference', 'stewardship_problem', 'household_or_beneficiary_type', 'consent_status', 'eligibility_status', 'intake_status')
    list_filter = ('household_or_beneficiary_type', 'consent_status', 'eligibility_status', 'intake_status')
    search_fields = ('display_reference',)


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ('beneficiary', 'tour', 'consent_type', 'status', 'consent_method', 'granted_at', 'withdrawn_at')
    list_filter = ('consent_type', 'status', 'consent_method')


@admin.register(SupplierQuote)
class SupplierQuoteAdmin(admin.ModelAdmin):
    list_display = ('supplier_name', 'intervention', 'amount', 'currency', 'verification_status', 'approval_status')
    list_filter = ('verification_status', 'approval_status')
    search_fields = ('supplier_name', 'quote_reference')


@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    list_display = ('tour', 'incident_type', 'severity', 'status', 'occurred_at', 'escalated_to')
    list_filter = ('incident_type', 'severity', 'status')


@admin.register(LaunchChecklistItem)
class LaunchChecklistItemAdmin(admin.ModelAdmin):
    list_display = ('label', 'tour', 'checklist_category', 'required', 'status', 'reviewed_by', 'reviewed_at')
    list_filter = ('checklist_category', 'required', 'status')
