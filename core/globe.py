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
from urllib.parse import quote

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

    # A layer toggle is only ever shown if at least one featured country
    # genuinely has data for it — never a toggle for a layer with zero rows
    # anywhere. This is computed once per request (only 4 featured countries).
    intelligence_layers_available = {key: False for key in INTELLIGENCE_LAYERS}
    for slug, iso, clat, clng in FEATURED:
        cp = CountryProfile.objects.filter(iso_code=iso).first()
        if cp is None:
            continue
        layers = _intelligence_layers(cp, iso)
        for key, result in layers.items():
            if result["available"]:
                intelligence_layers_available[key] = True

    return JsonResponse({
        "stats": stats,
        "countries": countries,
        "markers": markers,
        "markers_representative": True,   # honesty flag — not real coordinates
        "layers": ["energy", "infrastructure", "capital", "carbon", "water"],
        "intelligence_layers": INTELLIGENCE_LAYERS,
        "intelligence_layers_available": intelligence_layers_available,
        "disclaimer": ("Markers are representative (country-centroid clusters), "
                       "not precise asset coordinates. All counts are live and real."),
    })


# CountryProfile score field → panel label. Values render "Insufficient evidence"
# when null. No score is computed or invented here — only existing fields surfaced.
_SCORE_FIELDS = [
    ("overall", "Overall (EcoIQ index)", "national_ecoiq_index"),
    ("transition", "Transition readiness", "transition_readiness_score"),
    ("governance", "Governance / policy", "policy_environment_score"),
    ("investment", "Investment climate", "investment_climate_score"),
    ("transparency", "Transparency", "transparency_score"),
    ("industrial", "Industrial modernisation", "industrial_modernization_score"),
]

# The 5 "intelligence layers" a country card/toggle can surface. Each is
# grounded in a real model that already carries a `country` FK — never a new
# score invented for the globe. A layer is `available=False` (never a
# fabricated 0/low) when the country genuinely has no rows in that model yet.
INTELLIGENCE_LAYERS = ["climate_risk", "investment_opportunity", "modernisation_priority", "evidence_strength", "stewardship_impact"]

LIMITED_COVERAGE = "Limited EcoIQ coverage"
EVIDENCE_DEVELOPING = "Evidence still developing"


def _climate_risk_layer(cp):
    from geo_intelligence.models import GeoRiskZone

    zones = list(GeoRiskZone.objects.filter(country=cp))
    if not zones:
        return {"available": False, "label": LIMITED_COVERAGE, "value": None, "is_demo": None}
    order = {"high": 3, "medium": 2, "low": 1}
    worst = max(zones, key=lambda z: order.get(z.severity, 0))
    confidences = [z.confidence for z in zones if z.confidence is not None]
    return {
        "available": True,
        "label": f"{worst.get_severity_display()} risk — {len(zones)} zone{'s' if len(zones) != 1 else ''} tracked",
        "value": worst.severity,
        "confidence": round(sum(confidences) / len(confidences), 1) if confidences else None,
        "is_demo": all(z.is_demo for z in zones),
    }


def _investment_opportunity_layer(cp):
    from geo_intelligence.models import InvestmentGeoOpportunity

    opportunities = list(InvestmentGeoOpportunity.objects.filter(country=cp).order_by("-investment_score"))
    if not opportunities:
        return {"available": False, "label": LIMITED_COVERAGE, "value": None, "is_demo": None, "recommended_action": None}
    top = opportunities[0]
    return {
        "available": True,
        "label": f"{top.title} ({top.get_opportunity_type_display()})",
        "value": top.investment_score,
        "confidence": top.confidence,
        "is_demo": all(o.is_demo for o in opportunities),
        "recommended_action": top.recommended_action or None,
    }


def _modernisation_priority_layer(cp):
    from geo_intelligence.models import GeoAsset

    assets = list(GeoAsset.objects.filter(country=cp).exclude(modernisation_priority="not_assessed"))
    if not assets:
        return {"available": False, "label": LIMITED_COVERAGE, "value": None, "is_demo": None}
    order = {"high": 3, "medium": 2, "low": 1}
    worst = max(assets, key=lambda a: order.get(a.modernisation_priority, 0))
    return {
        "available": True,
        "label": f"{worst.get_modernisation_priority_display()} priority — {len(assets)} asset{'s' if len(assets) != 1 else ''} assessed",
        "value": worst.modernisation_priority,
        "is_demo": all(a.is_demo for a in assets),
    }


def _evidence_strength_layer(cp, iso):
    from harvester.models import Evidence, RegistryCompany

    slugs = list(RegistryCompany.objects.filter(country=iso, is_active=True).values_list("slug", flat=True))
    total = Evidence.objects.filter(company_slug__in=slugs).count() if slugs else 0
    if not total:
        return {"available": False, "label": EVIDENCE_DEVELOPING, "value": None}
    verified = Evidence.objects.filter(company_slug__in=slugs, verification_status="VERIFIED").count()
    rate = round(100 * verified / total, 1)
    return {
        "available": True,
        "label": f"{rate}% verified — {total} evidence item{'s' if total != 1 else ''}",
        "value": rate,
    }


def _stewardship_impact_layer(cp):
    from khalifa_stewardship_tour_operating_system.models import StewardshipTour

    tours = list(StewardshipTour.objects.filter(country=cp))
    if not tours:
        return {"available": False, "label": EVIDENCE_DEVELOPING, "value": None}
    latest = tours[0]
    return {
        "available": True,
        "label": f"{latest.get_status_display()} — {len(tours)} tour{'s' if len(tours) != 1 else ''}, {latest.participant_capacity} participant capacity",
        "value": latest.status,
    }


def _intelligence_layers(cp, iso):
    return {
        "climate_risk": _climate_risk_layer(cp),
        "investment_opportunity": _investment_opportunity_layer(cp),
        "modernisation_priority": _modernisation_priority_layer(cp),
        "evidence_strength": _evidence_strength_layer(cp, iso),
        "stewardship_impact": _stewardship_impact_layer(cp),
    }


def _recommended_next_action(intelligence):
    """Deterministic, rule-based — never an LLM call, never invented text.
    Prefers a real, human-authored InvestmentGeoOpportunity.recommended_action
    when one exists; otherwise a plain rule over the same real layer data."""
    investment = intelligence["investment_opportunity"]
    if investment["available"] and investment.get("recommended_action"):
        return investment["recommended_action"]
    if intelligence["climate_risk"]["available"] and intelligence["climate_risk"]["value"] == "high":
        return "Prioritise climate-risk mitigation for the highest-severity zone before further investment."
    if intelligence["modernisation_priority"]["available"] and intelligence["modernisation_priority"]["value"] == "high":
        return "Review high-priority modernisation assets with the AI Agent Workbench."
    if not intelligence["evidence_strength"]["available"]:
        return "Expand evidence coverage before drawing conclusions for this country."
    return "No specific action yet — evidence still developing for this country."


def globe_country(request, slug):
    """GET /api/globe/country/<slug>/ — Country Twin payload (read-only, real).

    Scores come only from existing CountryProfile fields (null → "insufficient
    evidence"). Companies/evidence/datapoints from the harvester. The 'why'
    checklist is derived from real evidence coverage — never fabricated.
    """
    from countries.models import CountryProfile
    from countries.intelligence import country_intelligence
    from harvester.models import Evidence, Datapoint, RegistryCompany

    cp = CountryProfile.objects.filter(slug=slug).first()
    if cp is None:
        return JsonResponse({"error": "country not found", "slug": slug}, status=404)

    intel = country_intelligence(cp)            # reuse the read-only bridge
    iso = (cp.iso_code or "").upper()
    centroid = next((c for s, i, la, ln in FEATURED if i == iso
                     for c in [{"lat": la, "lng": ln}]), None)

    scores = []
    for key, label, field in _SCORE_FIELDS:
        v = getattr(cp, field, None)
        # 0/None on a 0–100 index = unset/not-computed → render "Insufficient
        # evidence" rather than a misleading zero. Real non-zero values pass through.
        if v in (None, 0, 0.0):
            v = None
        scores.append({"key": key, "label": label, "field": field, "value": v})

    # layer marker counts for this country (same deterministic mapping)
    slugs = [c["slug"] for c in intel["companies"]]
    dp_metrics = set(Datapoint.objects.filter(company_slug__in=slugs)
                     .values_list("metric", flat=True)) if slugs else set()
    layers = {
        "energy": RegistryCompany.objects.filter(country=iso, sector__in=["energy", "utilities"]).count(),
        "infrastructure": RegistryCompany.objects.filter(country=iso, sector__in=["infrastructure", "industrials"]).count(),
        "water": RegistryCompany.objects.filter(country=iso, sector="water").count(),
        "capital": Datapoint.objects.filter(company_slug__in=slugs, metric="capex").values("company_slug").distinct().count() if slugs else 0,
        "carbon": Datapoint.objects.filter(company_slug__in=slugs, metric__in=_CARBON_METRICS).values("company_slug").distinct().count() if slugs else 0,
    }

    # evidence-coverage checklist (the "Why?" backbone) — real presence only
    cat = set(Evidence.objects.filter(company_slug__in=slugs).values_list("category", flat=True)) if slugs else set()
    verified = Evidence.objects.filter(company_slug__in=slugs, verification_status="VERIFIED").exists() if slugs else False
    checklist = [
        {"label": "Financial reports available", "ok": "financial" in cat or "capital_projects" in cat},
        {"label": "Emissions disclosed", "ok": bool(dp_metrics & _CARBON_METRICS) or "emissions" in cat},
        {"label": "Governance / ownership disclosed", "ok": bool({"governance", "board", "ownership"} & cat)},
        {"label": "Climate / transition pathway disclosed", "ok": "climate" in cat},
        {"label": "Independently verified evidence", "ok": verified},
    ]

    intelligence = _intelligence_layers(cp, iso)
    recommended_next_action = _recommended_next_action(intelligence)

    # Every action link points at a real, existing route — never a new one
    # invented for the globe. Decision Studio and Evidence Explorer have no
    # country-level filter today, so they're linked unscoped rather than
    # faking a filter that doesn't exist; the AI Agent Workbench genuinely
    # accepts a free-text `ask` query param (ai_agent_workbench.views.workbench).
    actions = {
        "country_intelligence": "/countries/%s/" % slug,
        "geo_intelligence": "/geo-intelligence/",
        "decision_studio": "/decision-studio/",
        "ai_agents": "/ai-agents/workbench/?ask=" + quote(f"What is the investment opportunity in {cp.name}?"),
        "evidence": "/evidence/" + ("?" if slugs else ""),
    }

    return JsonResponse({
        "slug": slug, "name": cp.name, "iso": iso, "centroid": centroid,
        "published": bool(cp.is_published),
        "scores": scores,
        "score_source": intel.get("data_sources") or "EcoIQ national indicators",
        "stats": {
            "companies": intel["companies_count"],
            "evidence": intel["evidence_count"],
            "datapoints": intel["datapoint_count"],
            "last_updated": intel["last_updated"].isoformat() if intel["last_updated"] else None,
        },
        "layers": layers,
        "intelligence": intelligence,
        "recommended_next_action": recommended_next_action,
        "actions": actions,
        "companies": intel["companies"][:8],
        "why": {"confidence_basis": "evidence verification coverage",
                "checklist": checklist,
                "evidence_url": "/evidence/" + ("?" if slugs else ""),
                "country_url": "/countries/%s/" % slug},
        "data_expansion": intel["data_expansion"],
        "no_registry": intel["no_registry"],
        "disclaimer": ("Scores are existing EcoIQ national indicators; metrics with no "
                       "value show 'Insufficient evidence'. Company figures are evidence-"
                       "backed. Markers are representative, not precise coordinates."),
    })
