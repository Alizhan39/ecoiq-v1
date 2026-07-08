from django.contrib import admin

from geo_intelligence.models import GeoAsset, GeoRiskZone, InvestmentGeoOpportunity


@admin.register(GeoAsset)
class GeoAssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'asset_type', 'country', 'region', 'modernisation_priority', 'is_demo')
    list_filter = ('asset_type', 'modernisation_priority', 'is_demo', 'country')
    search_fields = ('name', 'city', 'region')


@admin.register(GeoRiskZone)
class GeoRiskZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'risk_type', 'severity', 'country', 'region', 'is_demo')
    list_filter = ('risk_type', 'severity', 'is_demo', 'country')
    search_fields = ('name', 'region')


@admin.register(InvestmentGeoOpportunity)
class InvestmentGeoOpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'opportunity_type', 'risk_level', 'investment_score', 'country', 'is_demo')
    list_filter = ('opportunity_type', 'risk_level', 'is_demo', 'country')
    search_fields = ('title', 'region')
