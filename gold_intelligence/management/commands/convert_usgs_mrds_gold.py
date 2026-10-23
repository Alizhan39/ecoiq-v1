"""Convert operator-acquired USGS MRDS ArcGIS GeoJSON to staged reference occurrences.

Requires the operator to obtain the source file legally; no hidden network
calls, no conversion of occurrences into exploration discoveries or rights.
USGS MRDS coverage beyond USA is incomplete and mine/right status is old.
"""
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from gold_intelligence.services.target_geojson import validate_geometry

USGS_REFERENCE = "https://www.usgs.gov/publications/mineral-resources-data-system-mrds"
USGS_DOI = "https://doi.org/10.3133/ds20"
GOLD_CODES = re.compile(r"(?i)(?:^|[^a-z])(?:au|gold)(?:$|[^a-z])")


def convert_mrds_features(raw, *, bounds=None):
    """Normalize supported, clearly gold-tagged MRDS points, with no fake dates."""
    if not isinstance(raw, dict) or raw.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection exported from USGS MRDS.")
    features = raw.get("features")
    if not isinstance(features, list) or len(features) > 25000:
        raise ValueError("Expected no more than 25,000 source records in one batch.")
    result = []
    skipped = 0
    ids = set()
    for f in features:
        if not isinstance(f, dict) or f.get("type") != "Feature":
            skipped += 1
            continue
        props = f.get("properties") or {}
        if not isinstance(props, dict):
            skipped += 1
            continue
        # MRDS code_list is a historical commodity description, not a grade.
        code = str(props.get("code_list") or props.get("CODE_LIST") or "")
        if not GOLD_CODES.search(code):
            skipped += 1
            continue
        geometry = f.get("geometry")
        try:
            validate_geometry(geometry)
        except ValueError:
            skipped += 1
            continue
        if geometry["type"] != "Point":
            skipped += 1
            continue
        lon, lat = geometry["coordinates"]
        if bounds and not (bounds[0] <= lon <= bounds[2] and bounds[1] <= lat <= bounds[3]):
            skipped += 1
            continue
        deposit_id = str(props.get("dep_id") or props.get("DEP_ID") or "").strip()
        if not deposit_id or deposit_id in ids:
            skipped += 1
            continue
        ids.add(deposit_id)
        result.append({
            "type": "Feature",
            "id": f"USGS-MRDS-{deposit_id}",
            "geometry": geometry,
            "properties": {
                "name": str(props.get("site_name") or props.get("SITE_NAME") or "Unnamed MRDS record")[:200],
                "region": str(props.get("region") or props.get("REGION") or "")[:150],
                "feature_kind": "reference_occurrence",
                "source_name": "United States Geological Survey, MRDS",
                "source_url": USGS_REFERENCE,
                "source_reference": f"MRDS deposit {deposit_id}; {USGS_DOI}",
                # Observation timestamp is unknown unless a report gives it.
                "source_observed_on": None,
                "source_rights": "USGS MRDS public domain; attribution requested; verify source distribution terms.",
                "evidence": {},
            },
        })
    return {"type": "FeatureCollection", "features": result}, skipped


class Command(BaseCommand):
    help = "Convert already-exported USGS MRDS GeoJSON gold records into EcoIQ reference occurrences."

    def add_arguments(self, parser):
        parser.add_argument("input_path", type=Path)
        parser.add_argument("output_path", type=Path)
        parser.add_argument("--bbox", type=float, nargs=4, metavar=("MINLON", "MINLAT", "MAXLON", "MAXLAT"),
                            help="Optional lon/lat envelope; NOT a national border or licence check.")

    def handle(self, *args, **options):
        source, dest = options["input_path"], options["output_path"]
        if options["bbox"]:
            xmin, ymin, xmax, ymax = options["bbox"]
            if not (xmin < xmax and ymin < ymax and -180 <= xmin <= 180 and -180 <= xmax <= 180
                    and -90 <= ymin <= 90 and -90 <= ymax <= 90):
                raise CommandError("Invalid WGS84 bounding box.")
        try:
            if source.stat().st_size > 40_000_000:
                raise CommandError("Input exceeds 40MB; split into batches.")
            with source.open("r", encoding="utf-8") as fp:
                raw = json.load(fp)
            converted, skipped = convert_mrds_features(raw, bounds=options["bbox"])
        except (OSError, ValueError) as exc:
            raise CommandError(f"Cannot convert MRDS data: {exc}") from exc
        if dest.exists():
            raise CommandError("Output already exists; refusing to overwrite it.")
        with dest.open("x", encoding="utf-8") as fp:
            json.dump(converted, fp, ensure_ascii=False, indent=2)
        self.stdout.write(
            f"Converted {len(converted['features'])} historical MRDS gold records; "
            f"skipped {skipped}. Output is NOT a prospect map or licence check."
        )
