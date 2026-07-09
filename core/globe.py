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


# ---------------------------------------------------------------------------
# Phase 2 — Global Intelligence Command Globe
# ---------------------------------------------------------------------------

def _featured_country_profiles():
    """{iso: CountryProfile} for the 4 featured markets that actually exist."""
    from countries.models import CountryProfile

    profiles = {}
    for _slug, iso, _clat, _clng in FEATURED:
        cp = CountryProfile.objects.filter(iso_code=iso).first()
        if cp is not None:
            profiles[iso] = cp
    return profiles


def _numeric_country_scores(cp, iso):
    """
    Real, numeric (0-100 or None) scores for the heatmap and country
    comparison — reuses pandas_scoring_engine's existing country-level Geo
    Intelligence components (the same function intelligence_analytics_engine
    builds its country feature vectors from) rather than re-deriving a
    second scoring path. Never a fabricated number: None when the underlying
    component has no real data for this country yet.
    """
    from pandas_scoring_engine.services.scoring import compute_country_geo_components

    geo = compute_country_geo_components(cp)
    ecoiq_score = cp.national_ecoiq_index
    if ecoiq_score in (None, 0, 0.0):
        ecoiq_score = None
    return {
        "climate_risk": geo["climate_risk_score"],
        "investment_opportunity": geo["investment_opportunity_score"],
        "modernisation_priority": geo["modernisation_priority_score"],
        "evidence_strength": _evidence_strength_layer(cp, iso)["value"],
        "ecoiq_score": ecoiq_score,
    }


def globe_heatmap(request):
    """
    GET /api/globe/heatmap/ — Phase 7: real numeric scores per featured
    country for 5 heatmap layers. A country with no real data for a given
    metric stays null ("neutral") — the front end must never invent a score
    to fill the map. Includes the real min/max actually observed (over
    non-null values only) so the front end can build an honest colour scale.
    """
    profiles = _featured_country_profiles()
    countries = []
    for slug, iso, _clat, _clng in FEATURED:
        cp = profiles.get(iso)
        if cp is None:
            continue
        countries.append({
            "slug": slug, "iso": iso, "name": cp.name,
            "scores": _numeric_country_scores(cp, iso),
        })

    metrics = ["climate_risk", "investment_opportunity", "modernisation_priority", "evidence_strength", "ecoiq_score"]
    ranges = {}
    for metric in metrics:
        values = [c["scores"][metric] for c in countries if c["scores"][metric] is not None]
        ranges[metric] = {"min": min(values), "max": max(values)} if values else None

    return JsonResponse({
        "countries": countries, "metrics": metrics, "ranges": ranges,
        "disclaimer": "Countries with no real data for a metric are shown neutral, never a fabricated score.",
    })


def globe_compare(request):
    """
    GET /api/globe/compare/?iso=KZ&iso=GB&iso=TR — Phase 3: 2-3 featured
    countries side by side. Headline metrics reuse the same real
    intelligence layers/scores as the country panel; "key differences" call
    into intelligence_analytics_engine's existing Country Similarity Engine
    (compare_countries()) rather than a new comparison engine.
    """
    from intelligence_analytics_engine.services.similarity import compare_countries

    isos = [v.upper() for v in request.GET.getlist("iso") if v]
    featured_isos = {iso for _s, iso, _la, _ln in FEATURED}
    unknown = [iso for iso in isos if iso not in featured_isos]
    if unknown or not (2 <= len(isos) <= 3):
        return JsonResponse({
            "available": False,
            "reason": "Select 2 or 3 of the featured countries (GB, KZ, SA, TR) to compare.",
        }, status=400)

    profiles = _featured_country_profiles()
    countries = []
    for iso in isos:
        cp = profiles.get(iso)
        if cp is None:
            continue
        slug = next(s for s, i, _la, _ln in FEATURED if i == iso)
        intelligence = _intelligence_layers(cp, iso)
        overall = cp.national_ecoiq_index
        if overall in (None, 0, 0.0):
            overall = None
        countries.append({
            "iso": iso, "slug": slug, "name": cp.name, "pk": cp.pk,
            "ecoiq_score": overall,
            "intelligence": intelligence,
        })

    if len(countries) < 2:
        return JsonResponse({"available": False, "reason": "Not enough of the requested countries exist yet."}, status=400)

    key_differences = compare_countries([c["pk"] for c in countries])
    for c in countries:
        del c["pk"]   # internal only, never exposed

    return JsonResponse({"available": True, "countries": countries, "key_differences": key_differences})


PERIOD_DAYS = {"latest": 2, "7d": 7, "30d": 30, "1y": 365}


def _signal(signal_type, iso, title, detail, timestamp, link, severity=None):
    return {
        "type": signal_type, "iso": iso, "title": title, "detail": detail,
        "timestamp": timestamp.isoformat() if timestamp else None, "link": link, "severity": severity,
    }


def _agent_activity_for_country(cp, iso):
    """
    Real "which EcoIQ agent has looked at this country" signal — reuses the
    already-existing, already-seeded workbench_case_slug/workbench_agent_slug
    soft references on GeoAsset/GeoRiskZone/InvestmentGeoOpportunity (a real
    cross-app pointer that already existed for this exact purpose) joined to
    that agent's real, most recent AgentRun. Never fabricates an agent run
    that didn't happen — an agent with a real geo reference but zero real
    AgentRun rows is reported as `has_run=False`, not a fake one.
    """
    from agent_runtime_model_router.models import AgentRegistryEntry, AgentRun
    from geo_intelligence.models import GeoAsset, GeoRiskZone, InvestmentGeoOpportunity

    agent_slugs = set()
    for model in (GeoAsset, GeoRiskZone, InvestmentGeoOpportunity):
        agent_slugs |= set(
            model.objects.filter(country=cp).exclude(workbench_agent_slug="").values_list("workbench_agent_slug", flat=True)
        )

    findings = []
    for agent_slug in sorted(agent_slugs):
        entry = AgentRegistryEntry.objects.filter(agent_id=agent_slug).first()
        if entry is None:
            continue
        last_run = AgentRun.objects.filter(agent=entry).order_by("-created_at").first()
        findings.append({
            "agent_name": entry.agent_name, "agent_slug": agent_slug,
            "has_run": last_run is not None,
            "last_run_id": last_run.pk if last_run else None,
            "last_run_status": last_run.status if last_run else None,
            "last_run_at": last_run.created_at.isoformat() if last_run else None,
            "link": f"/ai-agents/agent/{agent_slug}/",
        })
    return findings


def globe_signals(request):
    """
    GET /api/globe/signals/?period=latest|7d|30d|1y — Phase 1 (signals) +
    Phase 9 (alerts, which are simply the most recent/severe of these same
    signals — no separate notification engine). Every signal is derived
    from a real, already-persisted row; nothing here executes new analysis.
    """
    from datetime import timedelta

    from django.utils import timezone

    from geo_intelligence.models import GeoAsset, GeoRiskZone, InvestmentGeoOpportunity
    from harvester.models import Evidence, RegistryCompany

    period = request.GET.get("period", "latest")
    if period not in PERIOD_DAYS:
        period = "latest"
    since = timezone.now() - timedelta(days=PERIOD_DAYS[period])

    profiles = _featured_country_profiles()
    iso_by_cp_pk = {cp.pk: iso for iso, cp in profiles.items()}
    signals = []
    oldest_timestamp = None

    def _track_oldest(ts):
        nonlocal oldest_timestamp
        if ts is not None and (oldest_timestamp is None or ts < oldest_timestamp):
            oldest_timestamp = ts

    zones = GeoRiskZone.objects.filter(country__pk__in=iso_by_cp_pk.keys())
    for z in zones:
        _track_oldest(z.last_updated)
        if z.last_updated and z.last_updated >= since:
            signals.append(_signal(
                "risk", iso_by_cp_pk[z.country_id], f"{z.get_severity_display()} risk: {z.name}",
                z.get_risk_type_display(), z.last_updated, "/geo-intelligence/", severity=z.severity,
            ))

    opportunities = InvestmentGeoOpportunity.objects.filter(country__pk__in=iso_by_cp_pk.keys())
    for o in opportunities:
        _track_oldest(o.created_at)
        if o.created_at and o.created_at >= since:
            signals.append(_signal(
                "opportunity", iso_by_cp_pk[o.country_id], o.title,
                o.get_opportunity_type_display(), o.created_at, "/geo-intelligence/",
            ))

    assets = GeoAsset.objects.filter(country__pk__in=iso_by_cp_pk.keys()).exclude(modernisation_priority="not_assessed")
    for a in assets:
        _track_oldest(a.updated_at)
        if a.updated_at and a.updated_at >= since:
            signals.append(_signal(
                "change", iso_by_cp_pk[a.country_id], f"{a.get_modernisation_priority_display()} modernisation priority: {a.name}",
                a.get_asset_type_display(), a.updated_at, "/geo-intelligence/",
            ))

    company_country = dict(RegistryCompany.objects.filter(country__in=iso_by_cp_pk.values(), is_active=True).values_list("slug", "country"))
    if company_country:
        evidence_qs = Evidence.objects.filter(company_slug__in=company_country.keys()).order_by("-retrieved_at")[:40]
        for e in evidence_qs:
            _track_oldest(e.retrieved_at)
            if e.retrieved_at and e.retrieved_at >= since:
                signals.append(_signal(
                    "evidence_update", company_country[e.company_slug], e.title or "New evidence",
                    e.get_category_display() if hasattr(e, "get_category_display") else e.category,
                    e.retrieved_at, f"/evidence/{e.company_slug}/",
                ))

    for iso, cp in profiles.items():
        for finding in _agent_activity_for_country(cp, iso):
            if not finding["has_run"]:
                continue
            run_at = finding["last_run_at"]
            from datetime import datetime as _dt
            run_dt = _dt.fromisoformat(run_at) if run_at else None
            _track_oldest(run_dt)
            if run_dt and run_dt >= since:
                signals.append(_signal(
                    "agent_finding", iso, f"{finding['agent_name']} → {cp.name}",
                    f"Status: {finding['last_run_status']}", run_dt,
                    f"/ai-agents/run/{finding['last_run_id']}/",
                ))

    signals.sort(key=lambda s: s["timestamp"] or "", reverse=True)

    historical_coverage_developing = oldest_timestamp is not None and oldest_timestamp >= since and period != "latest"

    return JsonResponse({
        "period": period, "signals": signals[:50], "signal_count": len(signals),
        "oldest_data_timestamp": oldest_timestamp.isoformat() if oldest_timestamp else None,
        "historical_coverage_developing": historical_coverage_developing,
        "disclaimer": "Every signal is derived from a real, already-persisted EcoIQ record — never fabricated activity.",
    })


def globe_agent_activity(request):
    """GET /api/globe/agent-activity/ — Phase 6: real per-country agent
    findings (see _agent_activity_for_country). Honest empty state when a
    country has no real geo-intelligence-to-agent reference at all."""
    profiles = _featured_country_profiles()
    countries = []
    for slug, iso, _clat, _clng in FEATURED:
        cp = profiles.get(iso)
        if cp is None:
            continue
        countries.append({"slug": slug, "iso": iso, "name": cp.name, "findings": _agent_activity_for_country(cp, iso)})
    return JsonResponse({"countries": countries})


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
        "decision_studio": "/decision-studio/?q=" + quote(f"What is the investment opportunity in {cp.name}?"),
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
