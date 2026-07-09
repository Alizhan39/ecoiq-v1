"""Admin registrations for the Evidence Harvester (read/inspect convenience)."""
from django.contrib import admin, messages

from .models import (
    Source, HarvestJob, Evidence, Datapoint, EvidenceSourceRef, RegistryCompany,
    BatchHarvestRun, IngestionRun,
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
                    "update_frequency", "is_active", "company",
                    "last_success_at", "last_failure_at")
    list_filter = ("source_type", "update_frequency", "is_active")
    search_fields = ("name", "source_owner", "source_url")
    readonly_fields = ("last_success_at", "last_failure_at", "last_failure_reason")
    actions = ["action_ingest_selected"]

    @admin.action(description='Ingest selected source(s) now')
    def action_ingest_selected(self, request, queryset):
        from harvester.services.ingestion_pipeline import ingest_source

        results = {}
        for source in queryset:
            run = ingest_source(source, triggered_by=f'admin:{request.user.username}')
            results[run.status] = results.get(run.status, 0) + 1
        self.message_user(request, f'Ingestion complete: {results}', level=messages.SUCCESS)


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = ("source", "status", "evidence_created_count", "evidence_updated_count",
                     "memory_records_created", "duration_seconds", "retry_count", "created_at")
    list_filter = ("status",)
    search_fields = ("source__name",)
    readonly_fields = (
        "source", "status", "triggered_by", "started_at", "completed_at",
        "evidence_created_count", "evidence_updated_count", "refs_attached_count",
        "memory_records_created", "error_message", "retry_count", "created_at",
    )
    actions = ["action_retry_failed"]

    def has_add_permission(self, request):
        return False

    @admin.action(description='Retry selected failed ingestion runs')
    def action_retry_failed(self, request, queryset):
        from harvester.services.ingestion_pipeline import ingest_source

        retried, skipped = 0, 0
        for run in queryset:
            if run.status != 'failed' or run.source is None:
                skipped += 1
                continue
            new_run = ingest_source(run.source, triggered_by=f'admin_retry:{request.user.username}')
            new_run.retry_count = run.retry_count + 1
            new_run.save(update_fields=['retry_count'])
            retried += 1
        self.message_user(request, f'Retried {retried}, skipped {skipped} (only failed runs with a known source can be retried).', level=messages.SUCCESS)


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
