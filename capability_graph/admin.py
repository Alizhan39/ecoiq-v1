from django.contrib import admin

from capability_graph.models import Organisation, OrganisationCapability, PublicRoute


class OrganisationCapabilityInline(admin.TabularInline):
    model = OrganisationCapability
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'org_type', 'jurisdiction', 'linked_company', 'created_at')
    list_filter = ('org_type',)
    search_fields = ('name', 'jurisdiction', 'dedupe_key')
    readonly_fields = ('dedupe_key', 'created_at', 'updated_at')
    inlines = [OrganisationCapabilityInline]


class PublicRouteInline(admin.TabularInline):
    model = PublicRoute
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


@admin.register(OrganisationCapability)
class OrganisationCapabilityAdmin(admin.ModelAdmin):
    list_display = (
        'organisation', 'capability', 'jurisdiction', 'topic_domain',
        'verification_state', 'last_verified_at',
    )
    list_filter = ('capability', 'verification_state')
    search_fields = ('organisation__name', 'jurisdiction', 'topic_domain', 'evidence_source')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PublicRouteInline]


@admin.register(PublicRoute)
class PublicRouteAdmin(admin.ModelAdmin):
    list_display = ('organisation_capability', 'route_type', 'route_value', 'is_currently_open', 'verified_at')
    list_filter = ('route_type', 'is_currently_open')
    readonly_fields = ('created_at', 'updated_at')
