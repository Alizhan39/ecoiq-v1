"""
EcoIQ Country Intelligence — Admin.
"""
from django.contrib import admin
from django.utils.html import format_html

from countries.models import CountryProfile


@admin.register(CountryProfile)
class CountryProfileAdmin(admin.ModelAdmin):

    list_display = [
        'flag_name', 'region', 'national_ecoiq_index',
        'transition_readiness_label', 'companies_tracked',
        'is_published', 'featured',
    ]
    list_filter  = ['region', 'transition_readiness_label', 'is_published', 'featured']
    search_fields= ['name', 'iso_code']
    prepopulated_fields = {'slug': ('name',)}
    list_editable= ['is_published', 'featured']

    readonly_fields = ['created_at', 'updated_at']

    fieldsets = [
        ('Identity', {
            'fields': ('name', 'slug', 'iso_code', 'flag_emoji', 'region',
                       'is_published', 'featured'),
        }),
        ('EcoIQ National Scores', {
            'fields': (
                'national_ecoiq_index', 'transition_readiness_score',
                'policy_environment_score', 'investment_climate_score',
                'transparency_score', 'industrial_modernization_score',
                'transition_readiness_label',
            ),
        }),
        ('Macro Context', {
            'fields': (
                'gdp_usd', 'industrial_gdp_share', 'co2_megatonnes',
                'renewable_energy_share', 'fossil_fuel_dependency',
                'companies_tracked',
            ),
        }),
        ('Financing', {
            'fields': ('estimated_transition_gap_usd', 'green_finance_available_usd'),
        }),
        ('AI-Generated Content', {
            'fields': ('ai_overview', 'ai_transition_narrative',
                       'ai_risk_summary', 'ai_investment_thesis'),
            'description': (
                'EcoIQ AI-generated analysis. '
                'All content automatically includes the standard AI disclaimer.'
            ),
        }),
        ('Structured Intelligence', {
            'fields': ('industrial_sectors', 'pollution_hotspots',
                       'financing_gaps', 'policy_highlights', 'upcoming_deadlines'),
            'classes': ['collapse'],
            'description': 'JSON arrays. Use the seed command to populate.',
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ['collapse'],
        }),
    ]

    def flag_name(self, obj):
        return format_html('{} <strong>{}</strong>', obj.flag_emoji, obj.name)
    flag_name.short_description = 'Country'
    flag_name.admin_order_field = 'name'
