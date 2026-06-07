"""Khalifa Heat — admin with starter-report + CSV export actions."""
import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html

from .models import (
    HeatingPackage, HeatingApplication, HomeAssessment,
    CompanySponsorshipLead, PilotProject,
)


def _export_csv(modeladmin, request, queryset, fields, filename):
    """Reusable CSV export for an admin action."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    writer = csv.writer(response)
    writer.writerow(fields)
    for obj in queryset:
        writer.writerow([getattr(obj, f, '') for f in fields])
    return response


def build_starter_report(app):
    """Deterministic starter report text for a heating lead (no external AI)."""
    pkg = app.package.name if app.package else 'package to be confirmed'
    install = app.get_install_type_display() if app.install_type else 'to be confirmed'
    loc = app.location or 'location to be confirmed'
    return (
        f'KHALIFA HEAT — STARTER REPORT (draft)\n'
        f'Lead: {app.full_name} ({app.get_lead_type_display()})\n'
        f'Location: {loc}\n'
        f'Package of interest: {pkg}\n'
        f'Installation type: {install}\n\n'
        f'Next steps:\n'
        f'1. Pre-sale technical check (area, insulation, radiators, electricity '
        f'phase & available kW, wiring, grounding, boiler space).\n'
        f'2. Recommend boiler size and confirm package + installation route.\n'
        f'3. Flag any electricity supply / insulation upgrades before quoting.\n'
        f'4. Issue quote and schedule install in the pre-winter window.\n\n'
        f'Note: indicative only — confirm on site before quoting.'
    )


@admin.register(HeatingPackage)
class HeatingPackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'tier', 'price_min_kzt', 'price_max_kzt', 'install_responsibility', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    list_filter = ('is_active', 'install_responsibility')
    search_fields = ('name', 'slug', 'target_customer')
    ordering = ('sort_order', 'tier')


@admin.register(HeatingApplication)
class HeatingApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'location', 'package', 'lead_type', 'install_type', 'status', 'created_at')
    list_filter = ('lead_type', 'status', 'install_type', 'package')
    search_fields = ('full_name', 'phone', 'email', 'organisation', 'location', 'address', 'message', 'notes')
    list_editable = ('lead_type', 'status')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('ip_address', 'created_at', 'updated_at')
    actions = ('generate_starter_report', 'export_leads_csv')

    fieldsets = (
        ('Lead', {'fields': ('full_name', 'phone', 'email', 'organisation', 'location', 'address', 'lead_type')}),
        ('Request', {'fields': ('package', 'install_type', 'message')}),
        ('Pipeline', {'fields': ('status', 'starter_report', 'notes')}),
        ('Meta', {'fields': ('ip_address', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.action(description='Generate starter report')
    def generate_starter_report(self, request, queryset):
        count = 0
        for app in queryset:
            if not (app.starter_report or '').strip():
                app.starter_report = build_starter_report(app)
                app.save(update_fields=['starter_report', 'updated_at'])
            count += 1
        self.message_user(request, f'Starter report generated for {count} lead(s).')

    @admin.action(description='Export selected leads as CSV')
    def export_leads_csv(self, request, queryset):
        fields = ['id', 'full_name', 'phone', 'email', 'organisation', 'location',
                  'lead_type', 'install_type', 'status', 'created_at']
        return _export_csv(self, request, queryset, fields, 'heating_leads')


@admin.register(HomeAssessment)
class HomeAssessmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'area_m2', 'insulation', 'rooms', 'electricity', 'recommended_kw',
                    'hp_ready_recommended', 'created_at')
    list_filter = ('insulation', 'electricity', 'hp_ready_recommended', 'has_radiators')
    search_fields = ('selected_package', 'warnings')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)


@admin.register(CompanySponsorshipLead)
class CompanySponsorshipLeadAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_name', 'email', 'package', 'status', 'created_at')
    list_filter = ('status', 'package')
    search_fields = ('company_name', 'contact_name', 'email', 'message', 'notes')
    list_editable = ('status',)
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('ip_address', 'created_at', 'updated_at')
    actions = ('export_company_csv',)

    @admin.action(description='Export selected company leads as CSV')
    def export_company_csv(self, request, queryset):
        fields = ['id', 'company_name', 'contact_name', 'email', 'phone', 'package',
                  'budget_band', 'status', 'created_at']
        return _export_csv(self, request, queryset, fields, 'heating_company_leads')


@admin.register(PilotProject)
class PilotProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'scale', 'status', 'homes_target', 'homes_done', 'budget_kzt', 'location')
    list_filter = ('scale', 'status')
    search_fields = ('name', 'location', 'objective', 'notes')
    list_editable = ('status', 'homes_done')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('scale', '-created_at')
