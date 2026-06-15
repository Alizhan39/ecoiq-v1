"""
Living Infrastructure Earth — read-only globe data endpoint (Phase 0).

Serves the homepage globe from REAL models only (RegistryCompany / Evidence /
Datapoint / CountryProfile). No new models, no scoring, no fabrication.

Markers are REPRESENTATIVE: positioned at a country centroid plus a deterministic
per-slug offset (clearly flagged representative=True). Real asset coordinates
arrive only in a later phase with verified geodata. Layer membership is derived
deterministically:
  energy         → sector in {energy, utilities}
  infrastructure → sector in {infrastructure, industrials}
  water          → sector == water
  capital        → company has a capex datapoint   (evidence-grounded)
  carbon         → company has a scope-emissions datapoint (evidence-grounded)
"""
from __future__ import annotations

import hashlib

from django.http import JsonResponse

# Featured markets: (country slug, ISO-2, centroid lat, centroid lng)
FEATURED = [
    ("united-kingdom", "GB", 54.0, -2.0),
    ("kazakhstan", "KZ", 48.0, 68.0),
    ("saudi-arabia", "SA", 24.0, 45.0),
    ("turkey", "TR", 39.0, 35.0),
]

_SECTOR_LAYER = {
    "energy": "energy", "utilities": "energy",
    "infrastructure": "infrastructure", "industrials": "infrastructure",
    "water": "water",
}
_CARBON_METRICS = {"scope1_emissions", "scope2_emissions", "scope3_emissions"}
_CAPITAL_METRICS = {"capex"}


def _offset(slug: str):
    """Deterministic small lat/lng jitter from the slug (representative scatter)."""
    h = hashlib.sha1(slug.encode("utf-8")).digest()
    dlat = (h[0] / 255.0 - 0.5) * 6.0   # ±3°
    dlng = (h[1] / 255.0 - 0.5) * 8.0   # ±4°
    return round(dlat, 3), round(dlng, 3)


def globe_layers(request):
    """GET /api/globe/layers/ — featured-country markers + live platform stats."""
    from harvester.models import RegistryCompany, Evidence, Datapoint
    from countries.models import CountryProfile
    from django.db.models import Max
    from datetime import datetime, timezone

    # ── live platform stats (all real) ──
    total_ev = Evidence.objects.count()
    verified = Evidence.objects.filter(verification_status="VERIFIED").count()
    last_ret = Evidence.objects.aggregate(m=Max("retrieved_at"))["m"]
    freshness_days = None
    if last_ret:
        freshness_days = (datetime.now(timezone.utc) - last_ret).days

    stats = {
        "companies": RegistryCompany.objects.filter(is_active=True).count(),
        "datapoints": Datapoint.objects.count(),
        "evidence": total_ev,
        "countries": CountryProfile.objects.filter(is_published=True).count(),
        "verification_rate": round(verified / total_ev * 100, 1) if total_ev else None,
        "freshness_days": freshness_days,
    }

    # ── representative markers per featured country ──
    countries, markers = [], []
    for slug, iso, clat, clng in FEATURED:
        cp = CountryProfile.objects.filter(iso_code=iso).first()
        countries.append({
            "slug": slug, "iso": iso, "lat": clat, "lng": clng,
            "name": cp.name if cp else slug.replace("-", " ").title(),
            "published": bool(cp and cp.is_published),
        })
        cos = RegistryCompany.objects.filter(country=iso, is_active=True)
        for c in cos:
            dp_metrics = set(Datapoint.objects.filter(company_slug=c.slug)
                             .values_list("metric", flat=True))
            layers = set()
            base = _SECTOR_LAYER.get(c.sector)
            if base:
                layers.add(base)
            if dp_metrics & _CAPITAL_METRICS:
                layers.add("capital")
            if dp_metrics & _CARBON_METRICS:
                layers.add("carbon")
            if not layers:
                layers.add("infrastructure")  # default visible layer
            dlat, dlng = _offset(c.slug)
            markers.append({
                "slug": c.slug, "name": c.company_name, "country": iso,
                "sector": c.sector, "layers": sorted(layers),
                "lat": round(clat + dlat, 3), "lng": round(clng + dlng, 3),
                "evidence_count": Evidence.objects.filter(company_slug=c.slug).count(),
                "datapoint_count": len(dp_metrics),
            })

    return JsonResponse({
        "stats": stats,
        "countries": countries,
        "markers": markers,
        "markers_representative": True,   # honesty flag — not real coordinates
        "layers": ["energy", "infrastructure", "capital", "carbon", "water"],
        "disclaimer": ("Markers are representative (country-centroid clusters), "
                       "not precise asset coordinates. All counts are live and real."),
    })
