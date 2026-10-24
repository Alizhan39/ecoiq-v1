"""Read-only provenance-aware gold exploration map and GeoJSON endpoint."""
from html import escape

import folium
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from gold_intelligence.access import projects_for
from gold_intelligence.models import GoldTarget, GoldCadastreSnapshot
from gold_intelligence.services.target_geojson import feature_collection, validate_geometry
from gold_intelligence.services.chu_ili_research import pilot_reference_geojson, pilot_research_queue, PILOT_ID

MAX_FEATURES = 500
MAX_CADASTRE = 250


def _visible_targets(request):
    qs = GoldTarget.objects.all() if request.user.is_staff else GoldTarget.objects.filter(
        project__in=projects_for(request.user)
    )
    region = request.GET.get("region", "").strip()
    kind = request.GET.get("kind", "").strip()
    if region:
        qs = qs.filter(region__iexact=region)
    if kind in {"candidate_target", "research_area", "reference_occurrence"}:
        qs = qs.filter(feature_kind=kind)
    return qs.order_by("name", "pk")


def _collection(request):
    records = list(_visible_targets(request)[:MAX_FEATURES + 1])
    clipped = len(records) > MAX_FEATURES
    collection = feature_collection(records[:MAX_FEATURES])
    collection["metadata"]["truncated"] = clipped
    collection["metadata"]["limit"] = MAX_FEATURES
    return collection


@login_required
@require_GET
def targets_geojson(request):
    """Private GeoJSON. Unassigned targets remain staff-only."""
    return JsonResponse(_collection(request))



def _cadastre_collection(request):
    """Only reviewed dated rights snapshots. Never imply land is free."""
    qs = GoldCadastreSnapshot.objects.filter(review_state="reviewed")
    if not request.user.is_staff:
        qs = qs.filter(project__in=projects_for(request.user))
    qs = qs.order_by("-snapshot_on", "parcel_id")
    if request.GET.get("region", "").strip():
        # Region text filters are not an official spatial relationship.
        qs = qs.none()
    records = list(qs[:MAX_CADASTRE + 1])
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": f"{r.parcel_id}:{r.snapshot_on.isoformat()}",
                "geometry": validate_geometry(r.geometry),
                "properties": {
                    "parcel_id": r.parcel_id,
                    "snapshot_on": r.snapshot_on.isoformat(),
                    "recorded_status": r.recorded_status,
                    "official_status_text": r.official_status_text,
                    "source_name": r.source_name,
                    "source_url": r.source_url,
                    "source_reference": r.source_reference,
                    "review_state": r.review_state,
                    "current_status_verified": False,
                    "available_for_application": None,
                    "drilling_authorized": False,
                },
            } for r in records[:MAX_CADASTRE]
        ],
        "metadata": {
            "truncated": len(records) > MAX_CADASTRE,
            "as_of": "Each feature's snapshot_on date, not today's status",
            "is_current_authoritative_licence_registry": False,
            "limitation": "Staff-reviewed historical snapshots only. Check live E-Qazyna.",
        },
    }


@login_required
@require_GET
def cadastre_geojson(request):
    return JsonResponse(_cadastre_collection(request))


@login_required
@require_GET
def pilot_research_queue_json(request):
    """Public bibliography, restricted to signed-in EcoIQ users."""
    return JsonResponse(pilot_research_queue())


@login_required
@require_GET
def targets_map(request):
    """Folium/Leaflet map using the existing map dependency, no new JS build."""
    collection = _collection(request)
    cadastre = _cadastre_collection(request)
    active_pilot = request.GET.get("pilot") == PILOT_ID
    fmap = folium.Map(
        location=[44.0, 76.6] if active_pilot else [48.0, 68.0],
        zoom_start=7 if active_pilot else 5,
        tiles="OpenStreetMap",
    )
    if active_pilot:
        pilot_layer = folium.FeatureGroup(
            name="Desk-study envelope and orientation ONLY (not gold)", show=True,
        )
        envelope, *anchors = pilot_reference_geojson()["features"]
        folium.GeoJson(
            envelope,
            name="Operator-defined research envelope — not a mineral target",
            style_function=lambda _: {
                "color": "#2563eb", "weight": 3, "dashArray": "10 7", "fillOpacity": 0.06,
            },
            tooltip="Desk-study envelope only: no gold grade or licensed status implied",
        ).add_to(pilot_layer)
        for anchor in anchors:
            lon, lat = anchor["geometry"]["coordinates"]
            folium.Marker(
                location=[lat, lon],
                tooltip=anchor["properties"]["name"],
                icon=folium.Icon(color="blue", icon="info-sign"),
            ).add_to(pilot_layer)
        pilot_layer.add_to(fmap)
    if collection["features"]:
        # Folium emits raw data inside map JavaScript. Escape all properties
        # before handing it to Folium (API still returns their original values).
        safe_collection = {
            "type": "FeatureCollection",
            "features": [
                {
                    **feature,
                    "properties": {
                        key: escape(value) if isinstance(value, str) else value
                        for key, value in feature["properties"].items()
                    },
                } for feature in collection["features"]
            ],
        }
        def style(feature):
            kind = feature["properties"]["feature_kind"]
            color = {
                "candidate_target": "#e6b54a",
                "research_area": "#3b82f6",
                "reference_occurrence": "#64748b",
            }.get(kind, "#64748b")
            return {"color": color, "weight": 3, "fillOpacity": 0.20}
        geo_layer = folium.GeoJson(
            safe_collection,
            name="Gold exploration evidence",
            style_function=style,
            tooltip=folium.GeoJsonTooltip(
                fields=["name", "feature_kind", "region", "rights_status", "review_state", "source_name"],
                aliases=["Name", "Layer", "Region", "Rights", "Review", "Source"],
                sticky=False,
            ),
        )
        geo_layer.add_to(fmap)
        # Fit only bounded validated geometries, never inferred targets.
        points = []
        def collect(positions):
            if isinstance(positions, list) and len(positions) == 2 and all(isinstance(v, (int, float)) for v in positions):
                points.append([positions[1], positions[0]])
            elif isinstance(positions, list):
                for item in positions:
                    collect(item)
        for f in collection["features"]:
            collect(f["geometry"]["coordinates"])
        if points and not active_pilot:
            fmap.fit_bounds([[min(p[0] for p in points), min(p[1] for p in points)],
                             [max(p[0] for p in points), max(p[1] for p in points)]])

    if cadastre["features"]:
        safe_cadastre = {
            "type": "FeatureCollection",
            "features": [
                {
                    **feature,
                    "properties": {
                        key: escape(value) if isinstance(value, str) else value
                        for key, value in feature["properties"].items()
                    },
                } for feature in cadastre["features"]
            ],
        }
        # No green "available" paint; expired does not mean unencumbered.
        def licence_style(feature):
            status = feature["properties"]["recorded_status"]
            color = {
                "licenced": "#e23d46",
                "application": "#e19d37",
                "withdrawn": "#838b99",
                "expired": "#838b99",
                "other": "#7c3aed",
                "unknown": "#64748b",
            }.get(status, "#64748b")
            return {"color": color, "fillColor": color, "weight": 2, "fillOpacity": 0.10}
        folium.GeoJson(
            safe_cadastre,
            name="Dated cadastral snapshots (NOT live rights)",
            style_function=licence_style,
            tooltip=folium.GeoJsonTooltip(
                fields=["parcel_id", "snapshot_on", "recorded_status", "source_reference"],
                aliases=["Official record", "Snapshot date", "Recorded status", "Source"],
            ),
        ).add_to(fmap)
    folium.LayerControl().add_to(fmap)

    return render(request, "gold_intelligence/targets_map.html", {
        "map_html": fmap._repr_html_(),
        "feature_count": len(collection["features"]),
        "cadastre_count": len(cadastre["features"]),
        "pilot_active": active_pilot,
        "pilot_queue": pilot_research_queue()["ranked_research_workstreams"] if active_pilot else [],
        "cadastre_truncated": cadastre["metadata"]["truncated"],
        "truncated": collection["metadata"]["truncated"],
        "region_filter": request.GET.get("region", "").strip(),
        "geojson_url": request.get_full_path().split("?")[0].rstrip("/") + "/geojson/",
    })
