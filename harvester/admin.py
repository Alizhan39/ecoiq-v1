"""Admin registrations for the Evidence Harvester (read/inspect convenience)."""
from django.contrib import admin

from .models import (
    Source, HarvestJob, Evidence, Datapoint, EvidenceSourceRef, RegistryCompany,
    BatchHarvestRun,
)


@admin.register(BatchHarvestRun)
class BatchHarvestRunAdmin(admin.ModelAdmin):
    list_display = ("created_at", "status", "total_companies", "successful",
                    "failed", "evidence_created", "datapoints_created")
    list_filter = ("status",)


@admin.register(RegistryCompany)
class RegistryCompanyAdmin(admin.ModelAdmin):
    list_display = ("company_name", "slug", "ticker", "sector", "subsector",
                    "country", "is_active", "priority")
    list_filter = ("sector", "country", "is_active")
    search_fields = ("company_name", "slug", "ticker", "companies_house_number")


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


@admin.register(EvidenceSourceRef)
class EvidenceSourceRefAdmin(admin.ModelAdmin):
    list_display = ("canonical_evidence", "source_type", "source_owner",
                    "source_quality_score", "publication_date")
    list_filter = ("source_type",)
    search_fields = ("url", "source_owner")


@admin.register(Datapoint)
class DatapointAdmin(admin.ModelAdmin):
    list_display = ("company_slug", "metric", "value", "unit",
                    "period", "category", "status", "confidence")
    list_filter = ("category", "status")
    search_fields = ("company_slug", "metric")
