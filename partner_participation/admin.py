from django.contrib import admin

from partner_participation.models import (
    FundingProgrammeDeclaration, OpportunityPreference, OrganisationMembership, RoutingCandidate,
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
