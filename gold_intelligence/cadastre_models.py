"""Cadastre snapshots are separate from geoscience targets and never imply free land.

The model stores independently provided, source-dated *rights records*, not
definitive current legal status. Only internally reviewed records are plotted.
"""
from django.core.exceptions import ValidationError
from django.db import models

from gold_intelligence.services.target_geojson import validate_geometry


class GoldCadastreSnapshot(models.Model):
    STATUS = [
        ("unknown", "Unknown"),
        ("licenced", "Licensed / granted right in dated source"),
        ("application", "Application / pending in dated source"),
        ("withdrawn", "Withdrawn in dated source"),
        ("expired", "Expired in dated source; check renewal/restrictions"),
        ("other", "Other official classification"),
    ]
    REVIEW = [("pending", "Pending"), ("reviewed", "Internally reviewed"), ("rejected", "Rejected")]

    parcel_id = models.CharField(max_length=120, help_text="Official record or polygon identifier")
    snapshot_on = models.DateField(help_text="Date of cadastre snapshot, NOT automatic current validity")
    geometry = models.JSONField(help_text="Official GeoJSON Polygon/MultiPolygon in WGS84 EPSG:4326")
    recorded_status = models.CharField(max_length=20, choices=STATUS, default="unknown")
    official_status_text = models.CharField(max_length=250, blank=True)
    source_name = models.CharField(max_length=200)
    source_url = models.URLField()
    source_reference = models.CharField(max_length=250)
    reuse_terms = models.TextField(help_text="Explicit source/redistribution terms checked by operator")
    source_sha256 = models.CharField(max_length=64, help_text="SHA256 of operator acquired GeoJSON")
    review_state = models.CharField(max_length=12, choices=REVIEW, default="pending")
    project = models.ForeignKey("gold_intelligence.GoldProject", null=True, blank=True,
                                on_delete=models.PROTECT, related_name="cadastre_snapshots")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-snapshot_on", "parcel_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["parcel_id", "snapshot_on", "source_reference"],
                name="uniq_gold_cadastre_parcel_snapshot",
            ),
        ]

    def clean(self):
        super().clean()
        try:
            validate_geometry(self.geometry)
            if self.geometry["type"] not in {"Polygon", "MultiPolygon"}:
                raise ValueError("Cadastre boundary requires Polygon or MultiPolygon.")
        except ValueError as exc:
            raise ValidationError({"geometry": str(exc)}) from exc
        if self.review_state == "reviewed" and (
            not self.reuse_terms or len(self.source_sha256) != 64
        ):
            raise ValidationError("Reviewed cadastre requires data rights statement and SHA256.")
        if not self.source_url.startswith("https://"):
            raise ValidationError({"source_url": "A secure official source URL is required."})

    def __str__(self):
        return f"{self.parcel_id} ({self.snapshot_on})"
