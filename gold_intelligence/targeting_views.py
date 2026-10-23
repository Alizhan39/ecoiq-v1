"""Read-only provenance-aware gold exploration map and GeoJSON endpoint."""
from html import escape

import folium
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from gold_intelligence.access import projects_for
from gold_intelligence.models import GoldTarget
from gold_intelligence.services.target_geojson import feature_collection

MAX_FEATURES = 500


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


@login_required
@require_GET
def targets_map(request):
    """Folium/Leaflet map using the existing map dependency, no new JS build."""
    collection = _collection(request)
    fmap = folium.Map(location=[48.0, 68.0], zoom_start=5, tiles="OpenStreetMap")
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
        if points:
            fmap.fit_bounds([[min(p[0] for p in points), min(p[1] for p in points)],
                             [max(p[0] for p in points), max(p[1] for p in points)]])
    folium.LayerControl().add_to(fmap)
    return render(request, "gold_intelligence/targets_map.html", {
        "map_html": fmap._repr_html_(),
        "feature_count": len(collection["features"]),
        "truncated": collection["metadata"]["truncated"],
        "region_filter": request.GET.get("region", "").strip(),
        "geojson_url": request.get_full_path().split("?")[0].rstrip("/") + "/geojson/",
    })
