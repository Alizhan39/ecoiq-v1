"""Admin registrations for the Evidence Harvester (read/inspect convenience)."""
from django.contrib import admin

from .models import Source, HarvestJob, Evidence, Datapoint


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "source_owner", "confidence_base",
                    "update_frequency", "is_active", "company")
    list_filter = ("source_type", "update_frequency", "is_active")
    search_fields = ("name", "source_owner", "source_url")


@admin.register(HarvestJob)
class HarvestJobAdmin(admin.ModelAdmin):
    list_display = ("company_slug", "status", "evidence_stored",
                    "created_at", "completed_at")
    list_filter = ("status",)
    search_fields = ("company_slug",)


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("company_slug", "category", "verification_status",
                    "confidence", "source", "publication_date")
    list_filter = ("category", "verification_status")
    search_fields = ("company_slug", "title", "url")


@admin.register(Datapoint)
class DatapointAdmin(admin.ModelAdmin):
    list_display = ("company_slug", "metric", "value", "unit",
                    "period_year", "category", "confidence")
    list_filter = ("category",)
    search_fields = ("company_slug", "metric")
