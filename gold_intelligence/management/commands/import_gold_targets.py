"""Safely stage explicit, sourced exploration GeoJSON into GoldTarget.

No network scraping, discovery claims or automatic licence assessments.
Examples:
  python manage.py import_gold_targets /secure/usgs-transformed.geojson
  python manage.py import_gold_targets /secure/usgs-transformed.geojson --apply --real-records --confirm-data-rights
"""
import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gold_intelligence.models import GoldTarget


REQUIRED = ("name", "feature_kind", "source_name", "source_url",
            "source_reference", "source_observed_on", "source_rights")


class Command(BaseCommand):
    help = "Validate sourced Gold Target GeoJSON; --apply to persist (pending review, rights unknown)."

    def add_arguments(self, parser):
        parser.add_argument("path", type=Path, help="Local GeoJSON FeatureCollection file")
        parser.add_argument("--apply", action="store_true", help="Persist after validating the full file")
        parser.add_argument("--real-records", action="store_true", help="Mark sourced observations non-demo (still pending review)")
        parser.add_argument("--confirm-data-rights", action="store_true", help="Operator attests dataset usage was checked")

    def handle(self, *args, **options):
        if options["real_records"] and not options["confirm_data_rights"]:
            raise CommandError("--real-records requires --confirm-data-rights and documented licence.")
        if options["apply"] and not options["confirm_data_rights"]:
            raise CommandError("--apply requires --confirm-data-rights (dataset redistribution/storage terms).")
        path = options["path"]
        try:
            # Reject unexpectedly large imports; subdivide and review before ingestion.
            if path.stat().st_size > 10_000_000:
                raise CommandError("GeoJSON exceeds 10 MB; split into audited batches.")
            with path.open("r", encoding="utf-8") as handle:
                collection = json.load(handle)
        except (OSError, ValueError) as exc:
            raise CommandError(f"Cannot read GeoJSON: {exc}") from exc
        if not isinstance(collection, dict) or collection.get("type") != "FeatureCollection":
            raise CommandError("Expected a GeoJSON FeatureCollection.")
        features = collection.get("features")
        if not isinstance(features, list) or len(features) > 1000:
            raise CommandError("features must be an array of at most 1000 items.")
        staged = []
        seen = set()
        for index, feature in enumerate(features):
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                raise CommandError(f"Feature {index}: invalid GeoJSON feature.")
            props = feature.get("properties")
            if not isinstance(props, dict):
                raise CommandError(f"Feature {index}: properties must be an object.")
            missing = [key for key in REQUIRED if not props.get(key)]
            if missing:
                raise CommandError(f"Feature {index}: missing {', '.join(missing)}.")
            identifier = str(feature.get("id") or "").strip()
            if not identifier or identifier in seen:
                raise CommandError(f"Feature {index}: missing/duplicate stable id.")
            seen.add(identifier)
            try:
                observed_on = date.fromisoformat(str(props["source_observed_on"]))
                target = GoldTarget(
                    target_id=identifier,
                    name=props["name"],
                    region=props.get("region") or "",
                    feature_kind=props["feature_kind"],
                    geometry=feature.get("geometry"),
                    evidence=props.get("evidence") or {},
                    source_name=props["source_name"],
                    source_url=props["source_url"],
                    source_reference=props["source_reference"],
                    source_observed_on=observed_on,
                    source_rights=props["source_rights"],
                    rights_status="unknown",  # NEVER auto-infer free cadastral rights from geology.
                    rights_reference="",
                    rights_checked_on=None,
                    review_state="pending",    # Human review never copied from input.
                    is_demo=not options["real_records"],
                )
                target.full_clean(validate_unique=False)
            except (ValueError, TypeError, Exception) as exc:
                # Includes Django ValidationError; re-raised as a useful CLI error.
                raise CommandError(f"Feature {index} ({identifier}): {exc}") from exc
            staged.append(target)
        if not options["apply"]:
            self.stdout.write(f"Validated {len(staged)} feature(s); DRY RUN only. No records saved.")
            return
        with transaction.atomic():
            for target in staged:
                payload = {
                    field.name: getattr(target, field.name)
                    for field in GoldTarget._meta.fields
                    if field.name not in {"id", "target_id", "created_at", "updated_at"}
                }
                # Existing target review is invalidated by any data update.
                GoldTarget.objects.update_or_create(target_id=target.target_id, defaults=payload)
        self.stdout.write(self.style.SUCCESS(
            f"Staged {len(staged)} target feature(s) as pending review. Rights remain UNKNOWN."
        ))
