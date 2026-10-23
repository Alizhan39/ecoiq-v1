"""Official, dated cadastral geometry snapshots (not a live licence status)."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("gold_intelligence", "0008_goldtarget_geojson")]
    operations = [
        migrations.CreateModel(
            name="GoldCadastreSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("parcel_id", models.CharField(max_length=120, help_text="Official record or polygon identifier")),
                ("snapshot_on", models.DateField(help_text="Date of cadastre snapshot, NOT automatic current validity")),
                ("geometry", models.JSONField(help_text="Official GeoJSON Polygon/MultiPolygon in WGS84 EPSG:4326")),
                ("recorded_status", models.CharField(max_length=20, default="unknown", choices=[
                    ("unknown", "Unknown"),
                    ("licenced", "Licensed / granted right in dated source"),
                    ("application", "Application / pending in dated source"),
                    ("withdrawn", "Withdrawn in dated source"),
                    ("expired", "Expired in dated source; check renewal/restrictions"),
                    ("other", "Other official classification"),
                ])),
                ("official_status_text", models.CharField(max_length=250, blank=True)),
                ("source_name", models.CharField(max_length=200)),
                ("source_url", models.URLField()),
                ("source_reference", models.CharField(max_length=250)),
                ("reuse_terms", models.TextField(help_text="Explicit source/redistribution terms checked by operator")),
                ("source_sha256", models.CharField(max_length=64, help_text="SHA256 of operator acquired GeoJSON")),
                ("review_state", models.CharField(max_length=12, default="pending", choices=[
                    ("pending", "Pending"), ("reviewed", "Internally reviewed"), ("rejected", "Rejected"),
                ])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="cadastre_snapshots", to="gold_intelligence.goldproject")),
            ],
            options={
                "ordering": ["-snapshot_on", "parcel_id"],
                "constraints": [models.UniqueConstraint(
                    fields=("parcel_id", "snapshot_on", "source_reference"),
                    name="uniq_gold_cadastre_parcel_snapshot",
                )],
            },
        ),
    ]
