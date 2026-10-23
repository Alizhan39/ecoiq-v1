"""Validated spatial export for GoldTarget records; no score imputation."""
from __future__ import annotations

from math import isfinite

from gold_intelligence.services.gold_targeting import evaluate_target


def validate_geometry(geometry):
    if not isinstance(geometry, dict) or geometry.get("type") not in {"Point", "Polygon", "MultiPolygon"}:
        raise ValueError("Expected GeoJSON Point, Polygon or MultiPolygon.")
    typ = geometry["type"]
    coordinates = geometry.get("coordinates")
    count = [0]

    def point(value):
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError("Coordinates must be [longitude, latitude] in EPSG:4326.")
        lon, lat = value
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not isfinite(v) for v in (lon, lat)):
            raise ValueError("Coordinates must be finite numbers.")
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError("Longitude or latitude outside WGS84 bounds.")
        count[0] += 1
        if count[0] > 10000:
            raise ValueError("Geometry exceeds 10,000 vertices.")

    def polygon(rings):
        if not isinstance(rings, list) or not rings:
            raise ValueError("Polygon must have non-empty rings.")
        for ring in rings:
            if not isinstance(ring, list) or len(ring) < 4:
                raise ValueError("Polygon ring requires four or more positions.")
            for position in ring:
                point(position)
            if ring[0] != ring[-1]:
                raise ValueError("Polygon rings must be closed.")

    if typ == "Point":
        point(coordinates)
    elif typ == "Polygon":
        polygon(coordinates)
    else:
        if not isinstance(coordinates, list) or not coordinates:
            raise ValueError("MultiPolygon requires at least one polygon.")
        for p in coordinates:
            polygon(p)
    return geometry


def target_feature(record):
    # Historical references and research areas may appear on the map,
    # but cannot be ranked as prospective drilling targets.
    eligible_for_index = (
        record.feature_kind == "candidate_target"
        and not record.is_demo
        and record.review_state == "reviewed"
    )
    assessment = evaluate_target({
        "id": record.target_id,
        "name": record.name,
        "rights_status": record.rights_status,
        "rights_reference": record.rights_reference,
        "evidence": record.evidence if eligible_for_index else {},
    })
    if not eligible_for_index:
        assessment["score"] = None
        assessment["score_kind"] = None
        assessment["eligibility"] = "reference_only_or_not_reviewed"
    return {
        "type": "Feature", "id": record.target_id,
        "geometry": validate_geometry(record.geometry),
        "properties": {
            "name": record.name,
            "region": record.region,
            "feature_kind": record.feature_kind,
            "source_name": record.source_name,
            "source_url": record.source_url,
            "source_reference": record.source_reference,
            "source_observed_on": record.source_observed_on.isoformat(),
            "source_rights": record.source_rights,
            "review_state": record.review_state,
            "is_demo": record.is_demo,
            "rights_status": record.rights_status,
            "rights_reference": record.rights_reference or None,
            "rights_checked_on": record.rights_checked_on.isoformat() if record.rights_checked_on else None,
            "screening_score": assessment["score"],
            "evidence_coverage": assessment["evidence_coverage"],
            "missing_features": assessment["missing_features"],
            "drilling_authorized": False,
            "resource_estimate": None,
        },
    }


def feature_collection(records):
    return {
        "type": "FeatureCollection",
        "features": [target_feature(record) for record in records],
        "metadata": {
            "coordinate_reference_system": "EPSG:4326",
            "is_licence_cadastre": False,
            "warning": "Not a licence, discovery, reserve estimate or authorization to drill.",
        },
    }
