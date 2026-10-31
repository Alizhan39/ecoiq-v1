"""Fetch USGS-hosted MRDS gold records as historical map references.

Public source: USGS-hosted ArcGIS FeatureServer (layer 0). This tool never
checks a Kazakhstan licence, discovers gold, or infers deposit resources.
Run by an operator; no scheduled/network access inside the web request path.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError

from gold_intelligence.management.commands.convert_usgs_mrds_gold import convert_mrds_features

SERVICE = "https://energy.usgs.gov/arcgis/rest/services/Hosted/Mineral_Resource_Data_System/FeatureServer/0/query"
PILOT_BBOX = (74.0, 42.0, 80.0, 46.0)
PAGE_SIZE = 400
MAX_PAGES = 20
MAX_BYTES = 3_000_000
# Fixed query, not user-supplied SQL. Client also checks distinct Au/gold tokens.
COMMODITY_QUERY = "(code_list LIKE '%Au%') OR (code_list LIKE '%gold%')"


def fetch_page(bbox, offset):
    """Bounded, timeout-limited download from exactly the official USGS host."""
    if offset < 0:
        raise ValueError("Offset cannot be negative")
    west, south, east, north = bbox
    params = {
        "where": COMMODITY_QUERY,
        "geometry": json.dumps({
            "xmin": west, "ymin": south, "xmax": east, "ymax": north,
            "spatialReference": {"wkid": 4326},
        }, separators=(",", ":")),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "objectid_1,dep_id,site_name,code_list,dev_stat",
        "outSR": "4326",
        "orderByFields": "objectid_1 ASC",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "f": "geojson",
    }
    url = SERVICE + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "EcoIQ-Gold-Research/0.1 (+https://ecoiq.uk)"})
    try:
        with urlopen(req, timeout=25) as response:
            if response.status != 200:
                raise ValueError("USGS returned non-200 response.")
            data = response.read(MAX_BYTES + 1)
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        raise ValueError(f"Official USGS query unavailable: {exc}") from exc
    if len(data) > MAX_BYTES:
        raise ValueError("USGS result exceeded safe response limit.")
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("USGS returned an invalid JSON response.") from exc
    if not isinstance(parsed, dict) or parsed.get("type") != "FeatureCollection":
        raise ValueError("USGS did not return a GeoJSON FeatureCollection.")
    if not isinstance(parsed.get("features"), list):
        raise ValueError("USGS features not an array.")
    return parsed


def collect_source_pages(bbox=PILOT_BBOX, *, page_loader=fetch_page):
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("WGS84 bbox must be west south east north.")
    raw = []
    seen_pages = set()
    for page in range(MAX_PAGES):
        incoming = page_loader(bbox, page * PAGE_SIZE)
        batch = incoming["features"]
        if len(batch) > PAGE_SIZE:
            raise ValueError("USGS returned more features than requested.")
        if batch:
            # Prevent silently repeating a service page when pagination fails.
            signature = hashlib.sha256(
                json.dumps(batch, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            if signature in seen_pages:
                raise ValueError("USGS repeated a page: abort, not a complete import.")
            seen_pages.add(signature)
            raw.extend(batch)
        if len(batch) < PAGE_SIZE and not incoming.get("exceededTransferLimit"):
            break
    else:
        raise ValueError("Source exceeds maximum pages: narrow the geographic bbox.")
    return {"type": "FeatureCollection", "features": raw}


class Command(BaseCommand):
    help = "Fetch and normalize historical USGS MRDS gold occurrences; output GeoJSON only, not database entries."

    def add_arguments(self, parser):
        parser.add_argument("output_path", type=Path)
        parser.add_argument("--bbox", nargs=4, type=float, metavar=("W", "S", "E", "N"), default=PILOT_BBOX)

    def handle(self, *args, **options):
        out = options["output_path"]
        manifest = Path(str(out) + ".provenance.json")
        if out.exists() or manifest.exists():
            raise CommandError("Output or provenance manifest already exists; refusing to overwrite.")
        bbox = tuple(options["bbox"])
        try:
            source = collect_source_pages(bbox)
            cleaned, skipped = convert_mrds_features(source, bounds=bbox)
            if len(cleaned["features"]) > 1000:
                raise CommandError("More than 1000 matches; narrow bbox or split batch.")
            normalized = json.dumps(cleaned, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
            digest = hashlib.sha256(normalized).hexdigest()
            meta = {
                "source": SERVICE,
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "bbox_wgs84": list(bbox),
                "where": COMMODITY_QUERY,
                "features_returned_by_service": len(source["features"]),
                "historical_gold_records_normalized": len(cleaned["features"]),
                "skipped": skipped,
                "sha256_normalized": digest,
                "assertions": {
                    "verified_exploration_target": False,
                    "licence_checked": False,
                    "kazakhstan_border_clipped": False,
                    "current_operating_status": False,
                },
            }
            # Atomic-ish staging with exclusivity; no auto-import or reporting counts before writing.
            with out.open("xb") as fp:
                fp.write(normalized)
            with manifest.open("x", encoding="utf-8") as fp:
                json.dump(meta, fp, ensure_ascii=False, indent=2)
        except (ValueError, OSError, CommandError) as exc:
            # Delete an incomplete output if a metadata write failed.
            if out.exists() and not manifest.exists():
                out.unlink()
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"Saved {len(cleaned['features'])} historical gold reference(s) from "
            f"{len(source['features'])} USGS records. Rights UNKNOWN. SHA256 {digest}"
        ))
