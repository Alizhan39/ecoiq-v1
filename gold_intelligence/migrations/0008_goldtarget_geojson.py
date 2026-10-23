"""Provenance-tagged GeoJSON targets, stored as JSON (JSONB on PostgreSQL).

PostGIS is intentionally not enabled until infrastructure readiness is verified.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("gold_intelligence", "0007_gold_geodata_and_kpis")]
    operations = [
        migrations.CreateModel(
            name="GoldTarget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("target_id", models.CharField(max_length=120, unique=True)),
                ("name", models.CharField(max_length=200)),
                ("region", models.CharField(blank=True, max_length=150)),
                ("feature_kind", models.CharField(
                    choices=[
                        ("candidate_target", "Candidate exploration target"),
                        ("research_area", "Desk-study research area"),
                        ("reference_occurrence", "Historical occurrence (not a target)"),
                    ], default="research_area", max_length=30,
                )),
                ("geometry", models.JSONField(help_text="GeoJSON Point/Polygon/MultiPolygon, EPSG:4326 only")),
                ("evidence", models.JSONField(blank=True, default=dict, help_text="Five independently cited normalized geological features")),
                ("source_name", models.CharField(max_length=200)),
                ("source_url", models.URLField()),
                ("source_reference", models.CharField(max_length=250)),
                ("source_observed_on", models.DateField(null=True, blank=True, help_text="Unknown if the original observation date is not documented")),
                ("source_rights", models.CharField(max_length=250, help_text="Recorded reuse licence or terms for this specific dataset")),
                ("rights_status", models.CharField(
                    choices=[
                        ("unknown", "Unknown / not independently checked"),
                        ("confirmed_available", "Checked available at snapshot date (not guaranteed)"),
                        ("held_by_applicant", "Applicant-held rights"),
                        ("third_party", "Third-party rights"),
                        ("restricted", "Restricted / excluded"),
                    ], default="unknown", max_length=25,
                )),
                ("rights_reference", models.CharField(blank=True, max_length=250)),
                ("rights_checked_on", models.DateField(blank=True, null=True)),
                ("review_state", models.CharField(
                    choices=[("pending", "Pending"), ("reviewed", "Internally reviewed"), ("rejected", "Rejected")],
                    default="pending", max_length=12,
                )),
                ("is_demo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.ForeignKey(
                    to="gold_intelligence.goldproject", null=True, blank=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="exploration_targets",
                    help_text="Unassigned records are staff-only; assigned records follow project permissions",
                )),
            ],
            options={"ordering": ["name"]},
        ),
    ]
