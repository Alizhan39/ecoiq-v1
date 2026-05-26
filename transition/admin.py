"""
EcoIQ Industrial Transition Engine — Admin.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import (
    TransitionRoadmap, TransitionPhase, FinancingOpportunity,
    FinancingMatch, TechnologyRecommendation, FacilityRecord,
    GlobalDatasetSource,
)


# ── Inlines ────────────────────────────────────────────────────────────────────

class TransitionPhaseInline(admin.TabularInline):
    model   = TransitionPhase
    extra   = 0
    fields  = ('number', 'name', 'duration_months', 'capex_usd',
                'co2_reduction_tonnes', 'status')
    ordering = ('number',)


class FinancingMatchInline(admin.TabularInline):
    model   = FinancingMatch
    extra   = 0
    fields  = ('opportunity', 'match_score', 'suggested_amount_usd',
                'suggested_pct_of_capex')
    readonly_fields = ('match_score',)


class TechRecInline(admin.TabularInline):
    model   = TechnologyRecommendation
    extra   = 0
    fields  = ('priority', 'category', 'technology_name', 'capex_low_usd',
                'capex_high_usd', 'co2_reduction_pct', 'maturity')


# ── TransitionRoadmap ──────────────────────────────────────────────────────────

@admin.register(TransitionRoadmap)
class TransitionRoadmapAdmin(admin.ModelAdmin):
    list_display  = ('company_link', 'roadmap_type_badge', 'status_badge',
                      'roi_label_col', 'co2_reduction_tonnes', 'confidence_pct',
                      'phase_count', 'created_at')
    list_filter   = ('status', 'roadmap_type', 'data_quality',
                      'company__sector', 'company__country')
    search_fields = ('company__name', 'title')
    readonly_fields = ('created_at', 'updated_at', 'model_used', 'token_count',
                       'roi_label', 'roi_color')
    inlines   = [TransitionPhaseInline, FinancingMatchInline, TechRecInline]
    ordering  = ('-created_at',)

    fieldsets = (
        ('Overview', {
            'fields': ('company', 'roadmap_type', 'status', 'title',
                       'executive_summary', 'confidence', 'data_quality'),
        }),
        ('Financial Projections', {
            'fields': ('total_capex_usd', 'annual_opex_savings_usd',
                       'payback_years', 'irr_pct', 'npv_usd'),
        }),
        ('Environmental Projections', {
            'fields': ('co2_reduction_tonnes', 'co2_reduction_pct',
                       'methane_reduction_pct', 'energy_efficiency_gain_pct'),
        }),
        ('EcoIQ Forecast', {
            'fields': ('projected_ecoiq', 'projected_ecoiq_delta'),
        }),
        ('Strategic Data', {
            'fields': ('current_state_json', 'target_state_json',
                       'recommended_structures_json', 'risks_json',
                       'technology_options_json'),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('total_duration_months', 'model_used', 'token_count',
                       'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def company_link(self, obj):
        url = reverse('admin:league_company_change', args=[obj.company_id])
        return format_html('<a href="{}">{}</a>', url, obj.company.name)
    company_link.short_description = 'Company'
    company_link.admin_order_field = 'company__name'

    def roadmap_type_badge(self, obj):
        colour_map = {
            'coal_gas': '#f4a261', 'methane': '#e63946', 'electrification': '#58a6ff',
            'district_heat': '#f4a261', 'water': '#58a6ff', 'waste_heat': '#f4a261',
            'flare': '#e63946', 'renewable': '#00e89a', 'circular': '#00e89a', 'full': '#888',
        }
        c = colour_map.get(obj.roadmap_type, '#888')
        return format_html(
            '<span style="background:{}22;color:{};padding:2px 8px;border-radius:4px;'
            'font-size:0.75rem;font-weight:700;">{}</span>',
            c, c, obj.get_roadmap_type_display()
        )
    roadmap_type_badge.short_description = 'Type'

    def status_badge(self, obj):
        colour_map = {
            'draft': '#888', 'active': '#00e89a', 'submitted': '#58a6ff',
            'funded': '#f4a261', 'completed': '#00e89a',
        }
        c = colour_map.get(obj.status, '#888')
        return format_html(
            '<span style="color:{};font-weight:700;">{}</span>',
            c, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def roi_label_col(self, obj):
        c = obj.roi_color
        return format_html('<span style="color:{};font-weight:700;">{}</span>',
                           c, obj.roi_label)
    roi_label_col.short_description = 'ROI'

    def confidence_pct(self, obj):
        pct = int(obj.confidence * 100)
        c = '#00e89a' if pct >= 70 else '#f4a261' if pct >= 40 else '#e63946'
        return format_html('<span style="color:{};">{:.0f}%</span>', c, pct)
    confidence_pct.short_description = 'Confidence'

    def phase_count(self, obj):
        return obj.phases.count()
    phase_count.short_description = 'Phases'


# ── FinancingOpportunity ───────────────────────────────────────────────────────

@admin.register(FinancingOpportunity)
class FinancingOpportunityAdmin(admin.ModelAdmin):
    list_display  = ('institution_name', 'acronym_badge', 'source_type_badge',
                      'instrument', 'ticket_range_label', 'is_active', 'verified')
    list_filter   = ('source_type', 'instrument', 'is_active', 'verified',
                      'co_financing_required')
    search_fields = ('institution_name', 'programme_name', 'acronym', 'description')
    list_editable = ('is_active',)
    ordering      = ('source_type', 'institution_name')

    fieldsets = (
        ('Institution', {
            'fields': ('institution_name', 'programme_name', 'acronym',
                       'source_type', 'instrument', 'brand_colour',
                       'url', 'contact_email', 'hq_country'),
        }),
        ('Eligibility', {
            'fields': ('eligible_sectors', 'eligible_countries', 'eligible_regions',
                       'focus_areas'),
        }),
        ('Ticket & Terms', {
            'fields': ('min_ticket_usd', 'max_ticket_usd', 'typical_tenor_years',
                       'typical_interest_rate', 'grace_period_years',
                       'co_financing_required', 'co_financing_pct'),
        }),
        ('Description', {
            'fields': ('description', 'eligibility_criteria',
                       'application_process', 'typical_timeline_days'),
        }),
        ('Status', {
            'fields': ('is_active', 'verified', 'last_verified'),
        }),
    )

    def acronym_badge(self, obj):
        if not obj.acronym:
            return '—'
        c = obj.brand_colour or '#888'
        return format_html(
            '<span style="background:{}22;color:{};padding:2px 8px;border-radius:4px;'
            'font-size:0.75rem;font-weight:800;">{}</span>',
            c, c, obj.acronym
        )
    acronym_badge.short_description = 'Acronym'

    def source_type_badge(self, obj):
        colours = {
            'dfi': '#58a6ff', 'climate_fund': '#00e89a', 'green_bond': '#00e89a',
            'sovereign_fund': '#f4a261', 'carbon_market': '#888',
            'blended': '#58a6ff', 'infra_grant': '#00e89a',
        }
        c = colours.get(obj.source_type, '#888')
        return format_html(
            '<span style="color:{};font-weight:600;">{}</span>',
            c, obj.get_source_type_display()
        )
    source_type_badge.short_description = 'Type'


# ── FinancingMatch ─────────────────────────────────────────────────────────────

@admin.register(FinancingMatch)
class FinancingMatchAdmin(admin.ModelAdmin):
    list_display  = ('roadmap', 'opportunity', 'match_score_pct',
                      'suggested_amount_usd', 'created_at')
    list_filter   = ('opportunity__source_type',)
    search_fields = ('roadmap__company__name', 'opportunity__institution_name')
    ordering      = ('-match_score',)

    def match_score_pct(self, obj):
        pct = int(obj.match_score * 100)
        c = '#00e89a' if pct >= 70 else '#f4a261' if pct >= 40 else '#e63946'
        return format_html('<span style="color:{};">{:.0f}%</span>', c, pct)
    match_score_pct.short_description = 'Match'


# ── TechnologyRecommendation ───────────────────────────────────────────────────

@admin.register(TechnologyRecommendation)
class TechnologyRecommendationAdmin(admin.ModelAdmin):
    list_display  = ('technology_name', 'category', 'provider_name',
                      'maturity_badge', 'co2_reduction_pct', 'payback_years',
                      'priority')
    list_filter   = ('category', 'maturity', 'company__sector')
    search_fields = ('technology_name', 'provider_name', 'description')
    ordering      = ('priority', 'category')

    def maturity_badge(self, obj):
        colours = {
            'proven': '#00e89a', 'commercial': '#58a6ff',
            'emerging': '#f4a261', 'pilot': '#888',
        }
        c = colours.get(obj.maturity, '#888')
        return format_html('<span style="color:{};">{}</span>',
                           c, obj.get_maturity_display())
    maturity_badge.short_description = 'Maturity'


# ── FacilityRecord ─────────────────────────────────────────────────────────────

@admin.register(FacilityRecord)
class FacilityRecordAdmin(admin.ModelAdmin):
    list_display  = ('name', 'company', 'facility_type', 'primary_fuel',
                      'country', 'capacity_mw', 'annual_co2_tonnes',
                      'operational_status', 'verified')
    list_filter   = ('facility_type', 'primary_fuel', 'operational_status',
                      'modernisation_status', 'verified')
    search_fields = ('name', 'company__name', 'location', 'country')
    list_editable = ('verified',)
    ordering      = ('company', 'name')


# ── GlobalDatasetSource ────────────────────────────────────────────────────────

@admin.register(GlobalDatasetSource)
class GlobalDatasetSourceAdmin(admin.ModelAdmin):
    list_display  = ('name', 'source_type', 'is_active', 'last_fetch_status',
                      'companies_found', 'companies_ingested', 'last_fetched_at')
    list_filter   = ('source_type', 'is_active', 'last_fetch_status')
    search_fields = ('name', 'description')
    list_editable = ('is_active',)
    ordering      = ('source_type', 'name')
    readonly_fields = ('last_fetched_at', 'last_fetch_status', 'companies_found',
                       'companies_ingested', 'error_log', 'created_at', 'updated_at')
