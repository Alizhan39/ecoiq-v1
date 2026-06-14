"""
Hikma Intelligence Layer — foundational data models (E.2 slice).

Additive only: introduces two NEW tables (hikma_evidence, hikma_assessment_run)
with nullable FKs into existing models. No existing table is altered.

Design mirrors audit.AIAnalysisJob (status + raw JSON result) and implements the
SAY / DO / SHOW evidence structure from docs/hikma_evidence_layer_spec.json.
Scoring is NOT performed here — it is computed deterministically in
hikma/assessment.py by reusing mizan/scoring.py.
"""
from django.db import models


class Evidence(models.Model):
    """A single SAY / DO / SHOW evidence record about a subject."""

    KIND_CHOICES = [
        ("say", "SAY — stated intent / claim"),
        ("do", "DO — action / capital allocation"),
        ("show", "SHOW — independent evidence / outcome"),
    ]
    CONFIDENCE_TIERS = [
        ("verified", "Verified (audit / regulator)"),
        ("analyst-reviewed", "Analyst-reviewed"),
        ("ai-seeded", "AI-seeded (unreviewed)"),
        ("model-estimate", "Model-estimate"),
    ]

    # Nullable FK — safest: deleting a profile never cascades away evidence,
    # and evidence can exist for non-company subjects (country/project/policy).
    company = models.ForeignKey(
        "companies.CompanyProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hikma_evidence",
    )
    subject_type = models.CharField(max_length=24, default="company")
    subject_ref = models.CharField(max_length=120, blank=True)

    kind = models.CharField(max_length=4, choices=KIND_CHOICES)
    statement = models.TextField()

    metric_name = models.CharField(max_length=120, blank=True)
    metric_value = models.FloatField(null=True, blank=True)
    metric_unit = models.CharField(max_length=32, blank=True)

    source_type = models.CharField(max_length=40, blank=True)
    source_url = models.URLField(blank=True)
    published_at = models.DateField(null=True, blank=True)

    confidence_tier = models.CharField(
        max_length=20, choices=CONFIDENCE_TIERS, default="ai-seeded"
    )
    confidence_score = models.FloatField(default=0.5)
    # Deterministic dedup key (sha1 of subject_ref|kind|statement). Nullable so
    # pre-existing rows are unaffected; new ingested rows always set it.
    content_hash = models.CharField(max_length=40, blank=True, db_index=True)
    scholar_review_required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hikma_evidence"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["subject_type", "subject_ref"]),
            models.Index(fields=["kind"]),
        ]

    def __str__(self):
        return f"[{self.kind.upper()}] {self.subject_ref or self.subject_type}: {self.statement[:48]}"


class AssessmentRun(models.Model):
    """A computed AssessmentResult for a subject. Mirrors audit.AIAnalysisJob:
    status + JSON result. The `result` payload is produced deterministically by
    hikma.assessment.build_assessment (Mizan-backed)."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("done", "Done"),
        ("error", "Error"),
    ]

    company = models.ForeignKey(
        "companies.CompanyProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hikma_assessments",
    )
    subject_type = models.CharField(max_length=24, default="company")
    subject_ref = models.CharField(max_length=120, blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    engine_version = models.CharField(max_length=24, default="hikma-assess-v1")
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hikma_assessment_run"
        ordering = ["-created_at"]

    def __str__(self):
        return f"AssessmentRun({self.subject_ref}, {self.status})"


class IngestRefreshJob(models.Model):
    """Async-shaped job for evidence ingestion + assessment regeneration.
    Mirrors audit.AIAnalysisJob (status + timestamps + error + stats)."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("done", "Done"),
        ("error", "Error"),
    ]

    company = models.ForeignKey(
        "companies.CompanyProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hikma_refresh_jobs",
    )
    subject_ref = models.CharField(max_length=120)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # stats
    sources_seen = models.IntegerField(default=0)
    evidence_created = models.IntegerField(default=0)
    evidence_skipped = models.IntegerField(default=0)
    assessment_run = models.ForeignKey(
        AssessmentRun, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="refresh_jobs",
    )

    class Meta:
        db_table = "hikma_ingest_refresh_job"
        ordering = ["-created_at"]

    def __str__(self):
        return f"IngestRefreshJob({self.subject_ref}, {self.status})"

    def status_dict(self):
        return {
            "job_id": self.id,
            "subject_ref": self.subject_ref,
            "status": self.status,
            "sources_seen": self.sources_seen,
            "evidence_created": self.evidence_created,
            "evidence_skipped": self.evidence_skipped,
            "assessment_run_id": self.assessment_run_id,
            "error": self.error_message or None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
