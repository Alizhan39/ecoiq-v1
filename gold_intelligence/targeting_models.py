"""Evidence-preserving GeoJSON geometry records for exploratory gold targets.

Django JSONField is compatible with SQLite and PostgreSQL JSONB. Native
PostGIS geometry/indexes are deliberately NOT enabled on this deployment.
"""
from django.core.exceptions import ValidationError
from django.db import models

from gold_intelligence.services.target_geojson import validate_geometry


class GoldTarget(models.Model):
    KINDS = [
        ("candidate_target", "Candidate exploration target"),
        ("research_area", "Desk-study research area"),
        ("reference_occurrence", "Historical occurrence (not a target)"),
    ]
    RIGHTS = [
        ("unknown", "Unknown / not independently checked"),
        ("confirmed_available", "Checked available at snapshot date (not guaranteed)"),
        ("held_by_applicant", "Applicant-held rights"),
        ("third_party", "Third-party rights"),
        ("restricted", "Restricted / excluded"),
    ]
    REVIEW = [("pending", "Pending"), ("reviewed", "Internally reviewed"), ("rejected", "Rejected")]

    target_id = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=200)
    region = models.CharField(max_length=150, blank=True)
    feature_kind = models.CharField(max_length=30, choices=KINDS, default="research_area")
    geometry = models.JSONField(help_text="GeoJSON Point/Polygon/MultiPolygon, EPSG:4326 only")
    evidence = models.JSONField(default=dict, blank=True, help_text="Five independently cited normalized geological features")
    source_name = models.CharField(max_length=200)
    source_url = models.URLField()
    source_reference = models.CharField(max_length=250)
    source_observed_on = models.DateField(null=True, blank=True, help_text='Unknown if the original observation date is not documented')
    source_rights = models.CharField(max_length=250, help_text="Recorded reuse licence or terms for this specific dataset")
    rights_status = models.CharField(max_length=25, choices=RIGHTS, default="unknown")
    rights_reference = models.CharField(max_length=250, blank=True)
    rights_checked_on = models.DateField(null=True, blank=True)
    review_state = models.CharField(max_length=12, choices=REVIEW, default="pending")
    is_demo = models.BooleanField(default=True)
    project = models.ForeignKey(
        "gold_intelligence.GoldProject", null=True, blank=True, on_delete=models.PROTECT,
        related_name="exploration_targets",
        help_text="Unassigned records are staff-only; assigned records follow project permissions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        super().clean()
        try:
            validate_geometry(self.geometry)
        except ValueError as exc:
            raise ValidationError({"geometry": str(exc)}) from exc
        if self.rights_status not in {"unknown", "third_party", "restricted"}:
            if not self.rights_reference or not self.rights_checked_on:
                raise ValidationError("Positive rights status requires source reference and checked date.")
        if self.review_state == "reviewed" and self.is_demo:
            raise ValidationError("Synthetic/demo records cannot be marked reviewed.")
        from gold_intelligence.services.gold_targeting import evaluate_target
        try:
            # A source must exist for every supplied normalized numerical feature.
            evaluate_target({
                "id": self.target_id or "?",
                "evidence": self.evidence,
                "rights_status": self.rights_status,
                "rights_reference": self.rights_reference,
            })
        except ValueError as exc:
            raise ValidationError({"evidence": str(exc)}) from exc

    def __str__(self):
        return self.name
