"""Stage operator-acquired, dated official cadastre polygons; no website scraping.

A human must verify the licensed data rights before --apply, and a staff
reviewer must explicitly mark records reviewed before the map displays them.
Dated statuses do not amount to current availability or permission to drill.
"""
import hashlib
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gold_intelligence.models import GoldCadastreSnapshot

MAX_BYTES = 10_000_000
MAX_FEATURES = 1000
OFFICIAL_HOSTS = {"minerals.e-qazyna.kz", "minerals-map.e-qazyna.kz"}
STATUSES = {"unknown", "licenced", "application", "withdrawn", "expired", "other"}


class Command(BaseCommand):
    help = "Stage explicitly licensed E-Qazyna official cadastre GeoJSON polygons in pending-review state."

    def add_arguments(self, parser):
        parser.add_argument("path", type=Path, help="Operator acquired official GeoJSON FeatureCollection")
        parser.add_argument("--snapshot-date", required=True, help="Official as-of date YYYY-MM-DD")
        parser.add_argument("--source-url", required=True, help="Official page/export reference URL")
        parser.add_argument("--source-reference", required=True, help="Stable record or dataset reference")
        parser.add_argument("--terms-file", required=True, type=Path, help="Text file documenting authorized data reuse")
        parser.add_argument("--confirm-permission", action="store_true", help="Operator has checked storage/reuse rights")
        parser.add_argument("--apply", action="store_true", help="Persist all records pending staff review")

    def handle(self, *args, **opt):
        parsed_url = urlsplit(opt["source_url"])
        if parsed_url.scheme != "https" or parsed_url.hostname not in OFFICIAL_HOSTS:
            raise CommandError("Source URL must be an official E-Qazyna HTTPS hostname.")
        try:
            snapshot = date.fromisoformat(opt["snapshot_date"])
            raw = opt["path"].read_bytes()
            if len(raw) > MAX_BYTES:
                raise CommandError("Dataset exceeds 10MB; split audited source batches.")
            rights_statement = opt["terms_file"].read_text(encoding="utf-8").strip()
            if not rights_statement:
                raise CommandError("Reuse terms file must be nonempty.")
            collection = json.loads(raw)
        except (ValueError, OSError, UnicodeDecodeError) as exc:
            raise CommandError(f"Invalid source package: {exc}") from exc
        if not isinstance(collection, dict) or collection.get("type") != "FeatureCollection":
            raise CommandError("Source must be GeoJSON FeatureCollection.")
        features = collection.get("features")
        if not isinstance(features, list) or len(features) > MAX_FEATURES:
            raise CommandError(f"Expected up to {MAX_FEATURES} polygons.")
        digest = hashlib.sha256(raw).hexdigest()
        rows, seen = [], set()
        for i, feature in enumerate(features):
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                raise CommandError(f"Feature #{i}: expected a GeoJSON Feature.")
            props = feature.get("properties")
            if not isinstance(props, dict):
                raise CommandError(f"Feature #{i}: expected properties object.")
            parcel = str(props.get("official_id") or feature.get("id") or "").strip()
            if not parcel or parcel in seen:
                raise CommandError(f"Feature #{i}: nonempty, unique official id required.")
            seen.add(parcel)
            reported_status = str(props.get("recorded_status") or "unknown").strip().lower()
            if reported_status not in STATUSES:
                # Do not pretend legal status can be inferred from text.
                reported_status = "unknown"
            row = GoldCadastreSnapshot(
                parcel_id=parcel,
                snapshot_on=snapshot,
                geometry=feature.get("geometry"),
                recorded_status=reported_status,
                official_status_text=str(props.get("official_status_text") or "")[:250],
                source_name="Kazakhstan E-Qazyna Minerals (operator-acquired dataset)",
                source_url=opt["source_url"],
                source_reference=opt["source_reference"],
                reuse_terms=rights_statement,
                source_sha256=digest,
                review_state="pending",
            )
            try:
                row.full_clean()
            except Exception as exc:
                raise CommandError(f"Feature #{i} ({parcel}): {exc}") from exc
            rows.append(row)
        self.stdout.write(
            f"Validated {len(rows)} dated polygons, SHA256 {digest}, "
            "review=PENDING. No rights are inferred to be currently available."
        )
        if not opt["apply"]:
            self.stdout.write("DRY RUN: nothing was saved.")
            return
        if not opt["confirm_permission"]:
            raise CommandError("--apply also requires --confirm-permission after reviewing dataset terms.")
        with transaction.atomic():
            GoldCadastreSnapshot.objects.bulk_create(rows)  # Explicitly rejects duplicate version keys.
        self.stdout.write(self.style.SUCCESS(
            f"Saved {len(rows)} pending cadastre snapshots. Staff review is required before map display."
        ))
