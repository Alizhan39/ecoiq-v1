from django.contrib import admin

from partner_participation.models import (
    FundingProgrammeDeclaration, NetworkActivityEvent, NextStepAction, OpportunityPreference,
    OrganisationMembership, ParticipationConsent, PartnerInvitation, RoutingCandidate, ShareDelivery,
)


@admin.register(OrganisationMembership)
class OrganisationMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'organisation', 'role', 'status', 'reviewed_by', 'reviewed_at', 'created_at')
    list_filter = ('role', 'status')
    search_fields = ('user__username', 'organisation__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(OpportunityPreference)
class OpportunityPreferenceAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'theme', 'acceptance_mode', 'requires_sharia_review', 'updated_at')
    list_filter = ('theme', 'acceptance_mode', 'requires_sharia_review')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FundingProgrammeDeclaration)
class FundingProgrammeDeclarationAdmin(admin.ModelAdmin):
    list_display = ('programme_name', 'organisation', 'funder_type', 'status', 'requires_sharia_review', 'deadline')
    list_filter = ('funder_type', 'status', 'requires_sharia_review')
    search_fields = ('programme_name', 'organisation__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RoutingCandidate)
class RoutingCandidateAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'opportunity', 'status', 'confidence_label', 'shared_at', 'responded_at')
    list_filter = ('status', 'confidence_label')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PartnerInvitation)
class PartnerInvitationAdmin(admin.ModelAdmin):
    list_display = ('invitee_email', 'organisation', 'intended_role', 'status', 'send_status', 'expires_at', 'created_at')
    list_filter = ('status', 'send_status', 'intended_role')
    search_fields = ('invitee_email', 'organisation__name')
    readonly_fields = ('token', 'created_at', 'sent_at', 'accepted_at', 'revoked_at')


@admin.register(ParticipationConsent)
class ParticipationConsentAdmin(admin.ModelAdmin):
    list_display = ('membership', 'actor', 'terms_version', 'status', 'consented_at', 'withdrawn_at')
    list_filter = ('status', 'terms_version')
    readonly_fields = ('consented_at',)


@admin.register(ShareDelivery)
class ShareDeliveryAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'delivery_method', 'send_status', 'recipient', 'sent_at')
    list_filter = ('delivery_method', 'send_status')
    readonly_fields = ('sent_at',)


@admin.register(NextStepAction)
class NextStepActionAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'action_type', 'status', 'created_by', 'created_at')
    list_filter = ('action_type', 'status')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(NetworkActivityEvent)
class NetworkActivityEventAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'event_type', 'actor', 'created_at')
    list_filter = ('event_type',)
    search_fields = ('organisation__name',)
    readonly_fields = ('created_at',)
