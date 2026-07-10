"""
gold_intelligence/views.py — EcoIQ Gold Intelligence (Kazakhstan Gold
Investment Intelligence), the platform's first flagship vertical.

Every view is read-only and reuses existing engines directly:
  mine_map               → geo_intelligence.services.maps.build_kazakhstan_geo_map
                           (the same Folium map builder geo_intelligence
                           itself uses — not a second map)
  investment_dashboard    → gold_intelligence.services.project_finance
  risk_intelligence_view  → gold_intelligence.services.risk_intelligence
  capital_tracker_view /
  equipment_intelligence_view → gold_intelligence.services.aggregates
Decision Studio and the AI Agent Workbench are linked to directly (real
?q=/?ask= query params on their existing routes) — no duplicate Q&A or
agent-orchestration path is created here.
"""
from urllib.parse import quote

from django.shortcuts import get_object_or_404, render

from gold_intelligence.models import GoldProject
from gold_intelligence.services import aggregates, project_finance, risk_intelligence

# Preset questions routed straight into the existing Decision Studio / AI
# Agent Workbench — never a second question-answering path.
DECISION_STUDIO_QUESTIONS = [
    'Should we invest?',
    'Where are the biggest risks?',
    'How much CAPEX is required?',
    'What infrastructure already exists?',
    'How much power is available?',
    'How much water is available?',
    'Which processing technology should be used?',
    'What permits are required?',
]


def _decision_studio_links(project):
    return [
        {'question': q, 'href': f'/decision-studio/?q={quote(q + " — " + project.name)}'}
        for q in DECISION_STUDIO_QUESTIONS
    ]


def _project_or_404(slug):
    return get_object_or_404(GoldProject.objects.select_related('country'), slug=slug)


def directory(request):
    projects = GoldProject.objects.select_related('country').all()
    return render(request, 'gold_intelligence/directory.html', {'projects': projects})


def investor_view(request, slug):
    """The one-page Investor View — every section summarised, nothing
    requiring more than five minutes to read."""
    project = _project_or_404(slug)
    economics = project_finance.compute_project_economics(project)
    risk = risk_intelligence.compute_risk_intelligence(project)
    capital = aggregates.capital_tracker_summary(project)
    equipment = aggregates.equipment_summary(project)
    timeline = aggregates.timeline_summary(project)

    top_risks = sorted(
        [{'key': k, 'label': risk_intelligence.RISK_DIMENSION_LABELS[k], **v} for k, v in risk.items() if v['available']],
        key=lambda r: {'high': 3, 'medium': 2, 'low': 1}.get(r['level'], 0), reverse=True,
    )[:3]

    return render(request, 'gold_intelligence/investor_view.html', {
        'project': project, 'economics': economics, 'risk': risk, 'top_risks': top_risks,
        'capital': capital, 'equipment': equipment, 'timeline': timeline,
        'decision_studio_links': _decision_studio_links(project)[:3],
    })


def mine_map(request):
    """Interactive Gold Mine Map — reuses geo_intelligence's exact map
    builder over GeoAsset/GeoRiskZone/InvestmentGeoOpportunity rows tagged
    for the Gold Intelligence vertical (extended asset_type choices), not a
    second map implementation."""
    from geo_intelligence.models import GeoAsset, GeoRiskZone, InvestmentGeoOpportunity
    from geo_intelligence.services.maps import build_kazakhstan_geo_map
    from geo_intelligence.views import _asset_to_dict, _opportunity_to_dict, _risk_zone_to_dict

    gold_asset_types = [
        'gold_deposit', 'active_mine', 'processing_plant', 'exploration_licence',
        'transport_hub', 'rail', 'road', 'airport', 'water_source', 'power_plant',
    ]
    project_country_ids = list(GoldProject.objects.exclude(country=None).values_list('country_id', flat=True).distinct())

    assets_qs = GeoAsset.objects.filter(asset_type__in=gold_asset_types).select_related('country')
    opportunities_qs = InvestmentGeoOpportunity.objects.filter(
        source_reference__startswith='gold_intelligence.GoldProject:',
    ).select_related('country')
    zones_qs = GeoRiskZone.objects.filter(country_id__in=project_country_ids).select_related('country') if project_country_ids else GeoRiskZone.objects.none()

    assets = [_asset_to_dict(a) for a in assets_qs]
    zones = [_risk_zone_to_dict(z) for z in zones_qs]
    opportunities = [_opportunity_to_dict(o) for o in opportunities_qs]
    map_html = build_kazakhstan_geo_map(assets, zones, opportunities)

    return render(request, 'gold_intelligence/mine_map.html', {
        'map_html': map_html, 'asset_count': len(assets), 'zone_count': len(zones),
        'opportunity_count': len(opportunities), 'projects': GoldProject.objects.all(),
    })


def investment_dashboard(request, slug):
    from plotly_visual_intelligence.services import charts

    project = _project_or_404(slug)
    economics = project_finance.compute_project_economics(project)
    sensitivity = project_finance.run_sensitivity_analysis(project) if economics.get('available') else economics
    scenarios = project_finance.run_scenario_analysis(project)
    return render(request, 'gold_intelligence/investment_dashboard.html', {
        'project': project, 'economics': economics, 'sensitivity': sensitivity, 'scenarios': scenarios,
        'sensitivity_chart': charts.sensitivity_tornado_chart(sensitivity),
        'scenario_chart': charts.scenario_comparison_chart(scenarios),
    })


def risk_intelligence_view(request, slug):
    project = _project_or_404(slug)
    risk = risk_intelligence.compute_risk_intelligence(project)
    rows = [{'key': k, 'label': risk_intelligence.RISK_DIMENSION_LABELS[k], **v} for k, v in risk.items()]
    return render(request, 'gold_intelligence/risk_intelligence.html', {'project': project, 'rows': rows})


def timeline_view(request, slug):
    from plotly_visual_intelligence.services import charts

    project = _project_or_404(slug)
    timeline = aggregates.timeline_summary(project)
    timeline_chart = charts.mine_timeline_chart(timeline['milestones']) if timeline['available'] else None
    return render(request, 'gold_intelligence/timeline.html', {'project': project, 'timeline': timeline, 'timeline_chart': timeline_chart})


def capital_tracker_view(request, slug):
    from plotly_visual_intelligence.services import charts

    project = _project_or_404(slug)
    capital = aggregates.capital_tracker_summary(project)
    capital_chart = charts.capital_tracker_chart(capital) if capital['available'] else None
    return render(request, 'gold_intelligence/capital_tracker.html', {'project': project, 'capital': capital, 'capital_chart': capital_chart})


def equipment_intelligence_view(request, slug):
    project = _project_or_404(slug)
    equipment = aggregates.equipment_summary(project)
    return render(request, 'gold_intelligence/equipment_intelligence.html', {'project': project, 'equipment': equipment})
