"""
EcoIQ Evidence Harvester — data-acquisition models (Slice 1, additive only).

Four NEW tables, no existing table altered:
  Source      — machine-readable source registry
  HarvestJob  — async-shaped harvest run (mirrors hikma.IngestRefreshJob)
  Evidence    — raw document-level evidence collected from a source
  Datapoint   — normalized structured fact extracted from an Evidence row

This is the acquisition layer ONLY. It collects / verifies / normalizes /
stores evidence. It does NOT score, interpret (SAY/DO/SHOW lives in hikma), or
generate briefs. Company linkage mirrors hikma: a nullable FK into
companies.CompanyProfile (SET_NULL) plus a denormalized company_slug so
evidence survives profile deletion and is queryable by slug.
"""
from __future__ import annotations

import hashlib

from django.db import models

from .constants import (
    SOURCE_TYPES,
    UPDATE_FREQUENCIES,
    EVIDENCE_CATEGORIES,
    VERIFICATION_STATUSES,
    NORMALIZATION_STATUSES,
    REGISTRY_SECTORS,
)


def content_hash(*parts) -> str:
    """Deterministic dedup key (sha1) over the given parts."""
    joined = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


class Source(models.Model):
    """A machine-readable source definition (the Source Registry).

    Global sources (World Bank, IEA, Ofgem) have company=None. Company-specific
    sources (a particular annual report) carry the company FK. Licensed/future
    sources are seeded with is_active=False — catalogued but never harvested.
    """

    name = models.CharField(max_length=200)
    source_type = models.CharField(max_length=40, choices=SOURCE_TYPES)
    source_url = models.URLField(blank=True)
    source_owner = models.CharField(max_length=200, blank=True)
    # Base trust for this source class, 0..1 (feeds the verification engine).
    confidence_base = models.FloatField(default=0.5)
    update_frequency = models.CharField(
        max_length=16, choices=UPDATE_FREQUENCIES, default="adhoc"
    )

    company = models.ForeignKey(
        "companies.CompanyProfile",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="harvest_sources",
        help_text="Null = global source.",
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "harvester_source"
        ordering = ["source_type", "name"]
        indexes = [
            models.Index(fields=["source_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        scope = self.company.company.slug if self.company_id and self.company else "global"
        return f"{self.get_source_type_display()} · {self.name} ({scope})"


class HarvestJob(models.Model):
    """An async-shaped harvest run for a company. Mirrors hikma.IngestRefreshJob
    (status + timestamps + error + stats) so a worker can drain pending jobs."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("done", "Done"),
        ("error", "Error"),
    ]

    company = models.ForeignKey(
        "companies.CompanyProfile",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="harvest_jobs",
    )
    company_slug = models.CharField(max_length=120)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    triggered_by = models.CharField(max_length=80, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # pipeline stats
    sources_discovered = models.IntegerField(default=0)
    documents_downloaded = models.IntegerField(default=0)
    evidence_extracted = models.IntegerField(default=0)
    evidence_verified = models.IntegerField(default=0)
    evidence_normalized = models.IntegerField(default=0)
    evidence_stored = models.IntegerField(default=0)

    class Meta:
        db_table = "harvester_harvest_job"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company_slug", "status"])]

    def __str__(self):
        return f"HarvestJob({self.company_slug}, {self.status})"

    def status_dict(self):
        return {
            "job_id": self.id,
            "company_slug": self.company_slug,
            "status": self.status,
            "stats": {
                "sources_discovered": self.sources_discovered,
                "documents_downloaded": self.documents_downloaded,
                "evidence_extracted": self.evidence_extracted,
                "evidence_verified": self.evidence_verified,
                "evidence_normalized": self.evidence_normalized,
                "evidence_stored": self.evidence_stored,
            },
            "error": self.error_message or None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class Evidence(models.Model):
    """A single raw, document-level piece of evidence collected from a source.

    This is the acquisition record (not the SAY/DO/SHOW interpretation, which
    lives in hikma.Evidence). Verification sub-scores and status are populated
    by the verification engine in a later slice; here they default to UNVERIFIED.
    """

    company = models.ForeignKey(
        "companies.CompanyProfile",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="harvested_evidence",
    )
    company_slug = models.CharField(max_length=120)
    source = models.ForeignKey(
        Source, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="evidence",
    )
    harvest_job = models.ForeignKey(
        HarvestJob, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="evidence",
    )

    title = models.CharField(max_length=400, blank=True)
    url = models.URLField(blank=True)
    publication_date = models.DateField(null=True, blank=True)
    retrieved_at = models.DateTimeField(auto_now_add=True)

    excerpt = models.TextField(blank=True)
    full_text = models.TextField(blank=True)
    document_type = models.CharField(max_length=60, blank=True)
    category = models.CharField(max_length=40, choices=EVIDENCE_CATEGORIES)

    # Verification (populated by the verification engine in a later slice).
    source_quality_score = models.FloatField(default=0.0)
    freshness_score = models.FloatField(default=0.0)
    corroboration_score = models.FloatField(default=0.0)
    confidence_score = models.FloatField(default=0.0)
    # Convenience alias kept distinct from confidence_score for the dashboard.
    confidence = models.FloatField(default=0.0)
    verification_status = models.CharField(
        max_length=24, choices=VERIFICATION_STATUSES, default="UNVERIFIED"
    )

    # Idempotent dedup key (set by the harvester; nullable for manual rows).
    content_hash = models.CharField(max_length=40, blank=True, db_index=True)
    # Source-independent fact key — groups the same fact asserted by different
    # sources into one canonical row (see harvester.dedup). Set by the dedup engine.
    dedup_key = models.CharField(max_length=40, blank=True, db_index=True)
    # Number of additional independent sources corroborating this canonical fact
    # (denormalized from EvidenceSourceRef; feeds corroboration_score).
    corroboration_count = models.IntegerField(default=0)

    class Meta:
        db_table = "harvester_evidence"
        ordering = ["-publication_date", "-retrieved_at"]
        indexes = [
            models.Index(fields=["company_slug", "category"]),
            models.Index(fields=["verification_status"]),
        ]

    def __str__(self):
        return f"[{self.category}] {self.company_slug}: {(self.title or self.url)[:48]}"

    def compute_hash(self):
        """Stable hash for dedup across re-harvests."""
        return content_hash(self.company_slug, self.category, self.url, self.title, self.excerpt)


class Datapoint(models.Model):
    """A normalized, structured fact extracted from an Evidence row.

    e.g. raw "Scope 1 emissions reduced by 12%" → metric=scope1_emissions_change,
    value=-12, unit=percent. Provenance is preserved via the Evidence FK; no
    datapoint exists without a source Evidence row.
    """

    evidence = models.ForeignKey(
        Evidence, on_delete=models.CASCADE, related_name="datapoints"
    )
    company = models.ForeignKey(
        "companies.CompanyProfile",
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="harvested_datapoints",
    )
    company_slug = models.CharField(max_length=120)

    metric = models.CharField(max_length=120)
    value = models.FloatField(null=True, blank=True)
    value_text = models.CharField(max_length=400, blank=True)
    unit = models.CharField(max_length=40, blank=True)
    period_year = models.IntegerField(null=True, blank=True)
    # Reporting-period label (e.g. "2024/25", "FY2025"); period_year holds the
    # numeric year for filtering.
    period = models.CharField(max_length=20, blank=True)
    category = models.CharField(max_length=40, choices=EVIDENCE_CATEGORIES)

    confidence = models.FloatField(default=0.0)
    status = models.CharField(
        max_length=16, choices=NORMALIZATION_STATUSES, default="NORMALIZED"
    )
    extraction_method = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    normalized_at = models.DateTimeField(null=True, blank=True)

    @property
    def source_evidence(self):
        """Provenance alias — the Evidence row this datapoint was extracted from."""
        return self.evidence

    class Meta:
        db_table = "harvester_datapoint"
        ordering = ["company_slug", "metric", "-period_year"]
        indexes = [
            models.Index(fields=["company_slug", "metric"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        v = self.value if self.value is not None else self.value_text
        return f"{self.company_slug}:{self.metric}={v}{self.unit}"


class EvidenceSourceRef(models.Model):
    """A single source that asserted a canonical Evidence fact.

    The dedup engine merges the same fact appearing across annual reports, ESG
    reports, websites, and news into ONE canonical Evidence row; each
    contributing source is recorded here. The count of distinct refs drives the
    verification corroboration score.
    """

    canonical_evidence = models.ForeignKey(
        Evidence, on_delete=models.CASCADE, related_name="source_refs"
    )
    source = models.ForeignKey(
        Source, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="evidence_refs",
    )
    source_type = models.CharField(max_length=40, blank=True)
    source_owner = models.CharField(max_length=200, blank=True)
    url = models.URLField(blank=True)
    publication_date = models.DateField(null=True, blank=True)
    excerpt = models.TextField(blank=True)
    source_quality_score = models.FloatField(default=0.0)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "harvester_evidence_source_ref"
        ordering = ["-source_quality_score", "-publication_date"]
        # Idempotent: the same source+url contributes to a canonical item once.
        constraints = [
            models.UniqueConstraint(
                fields=["canonical_evidence", "source_type", "url"],
                name="uniq_canonical_source_url",
            )
        ]

    def __str__(self):
        return f"ref({self.source_type} → ev#{self.canonical_evidence_id})"


class RegistryCompany(models.Model):
    """A target company in the harvest universe (Slice 6 — registry only).

    Identifying metadata for companies the harvester will later collect evidence
    for. The `slug` is the join key to harvested data (Evidence/Datapoint
    company_slug). This model stores NO evidence and triggers NO harvesting.

    Fields left blank (report URLs, companies_house_number) are intentionally
    unset pending verification — never fabricated.
    """

    company_name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120, unique=True)
    ticker = models.CharField(max_length=16, blank=True)
    sector = models.CharField(max_length=20, choices=REGISTRY_SECTORS)
    subsector = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=2, default="GB")

    website = models.URLField(blank=True)
    investor_relations_url = models.URLField(blank=True)
    annual_report_url = models.URLField(blank=True)
    sustainability_report_url = models.URLField(blank=True)
    companies_house_number = models.CharField(max_length=12, blank=True)

    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "harvester_registry_company"
        ordering = ["priority", "company_name"]
        verbose_name_plural = "registry companies"
        indexes = [
            models.Index(fields=["sector"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.company_name} ({self.sector})"


class BatchHarvestRun(models.Model):
    """Summary of a batch harvest across the registry (Slice 7).

    Persists aggregate stats for one `harvest_registry` run. Per-company detail
    lives on the individual HarvestJob rows; this is the roll-up.
    """

    STATUS_CHOICES = [
        ("running", "Running"),
        ("done", "Done"),
        ("error", "Error"),
    ]

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="running")
    filter_note = models.CharField(max_length=120, blank=True)

    total_companies = models.IntegerField(default=0)
    successful = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    evidence_created = models.IntegerField(default=0)
    datapoints_created = models.IntegerField(default=0)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "harvester_batch_harvest_run"
        ordering = ["-created_at"]

    def __str__(self):
        return (f"BatchHarvestRun({self.created_at:%Y-%m-%d}, "
                f"{self.successful}/{self.total_companies} ok)")

    def summary_dict(self):
        return {
            "total_companies": self.total_companies,
            "successful": self.successful,
            "failed": self.failed,
            "evidence_created": self.evidence_created,
            "datapoints_created": self.datapoints_created,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
