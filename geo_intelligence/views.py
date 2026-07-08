from django.db.models import Q
from django.shortcuts import render

from geo_intelligence.models import GeoAsset, GeoRiskZone, InvestmentGeoOpportunity
from geo_intelligence.services import weather
from geo_intelligence.services.maps import build_kazakhstan_geo_map


def _asset_to_dict(asset):
    return {
        'id': asset.id, 'name': asset.name, 'asset_type': asset.asset_type,
        'asset_type_display': asset.get_asset_type_display(),
        'latitude': asset.latitude, 'longitude': asset.longitude,
        'city': asset.city, 'region': asset.region,
        'country': asset.country.name if asset.country else '',
        'sector': asset.sector, 'climate_exposure_score': asset.climate_exposure_score,
        'modernisation_priority': asset.modernisation_priority,
        'modernisation_priority_display': asset.get_modernisation_priority_display(),
        'is_demo': asset.is_demo,
        'workbench_case_slug': asset.workbench_case_slug, 'workbench_agent_slug': asset.workbench_agent_slug,
    }


def _risk_zone_to_dict(zone):
    return {
        'id': zone.id, 'name': zone.name, 'risk_type': zone.risk_type,
        'risk_type_display': zone.get_risk_type_display(),
        'latitude': zone.latitude, 'longitude': zone.longitude, 'radius_km': zone.radius_km,
        'region': zone.region, 'country': zone.country.name if zone.country else '',
        'severity': zone.severity, 'severity_display': zone.get_severity_display(),
        'confidence': zone.confidence, 'source': zone.source, 'is_demo': zone.is_demo,
    }


def _opportunity_to_dict(opp):
    return {
        'id': opp.id, 'title': opp.title, 'opportunity_type': opp.opportunity_type,
        'opportunity_type_display': opp.get_opportunity_type_display(),
        'latitude': opp.latitude, 'longitude': opp.longitude,
        'region': opp.region, 'country': opp.country.name if opp.country else '',
        'estimated_impact': opp.estimated_impact,
        'risk_level': opp.risk_level, 'risk_level_display': opp.get_risk_level_display(),
        'investment_score': opp.investment_score, 'confidence': opp.confidence,
        'recommended_action': opp.recommended_action, 'is_demo': opp.is_demo,
        'workbench_case_slug': opp.workbench_case_slug, 'workbench_agent_slug': opp.workbench_agent_slug,
    }


def command_centre(request):
    """/geo-intelligence/ — the Kazakhstan Geo Intelligence Command Centre."""
    query = request.GET.get('q', '').strip()
    region_filter = request.GET.get('region', '').strip()
    layer_filter = request.GET.get('layer', '').strip()
    risk_level_filter = request.GET.get('risk_level', '').strip()

    assets_qs = GeoAsset.objects.select_related('country').all()
    zones_qs = GeoRiskZone.objects.select_related('country').all()
    opps_qs = InvestmentGeoOpportunity.objects.select_related('country').all()

    if query:
        assets_qs = assets_qs.filter(Q(name__icontains=query) | Q(city__icontains=query) | Q(region__icontains=query))
        zones_qs = zones_qs.filter(Q(name__icontains=query) | Q(region__icontains=query))
        opps_qs = opps_qs.filter(Q(title__icontains=query) | Q(region__icontains=query))

    if region_filter:
        assets_qs = assets_qs.filter(region=region_filter)
        zones_qs = zones_qs.filter(region=region_filter)
        opps_qs = opps_qs.filter(region=region_filter)
    if risk_level_filter:
        zones_qs = zones_qs.filter(severity=risk_level_filter)
        opps_qs = opps_qs.filter(risk_level=risk_level_filter)

    if layer_filter == 'companies':
        zones_qs, opps_qs = zones_qs.none(), opps_qs.none()
    elif layer_filter == 'climate_risk':
        assets_qs, opps_qs = assets_qs.none(), opps_qs.none()
    elif layer_filter == 'investment':
        assets_qs, zones_qs = assets_qs.none(), zones_qs.none()

    assets = [_asset_to_dict(a) for a in assets_qs]
    zones = [_risk_zone_to_dict(z) for z in zones_qs]
    opportunities = [_opportunity_to_dict(o) for o in opps_qs]

    map_html = build_kazakhstan_geo_map(assets, zones, opportunities)

    almaty = weather.KAZAKHSTAN_CITIES['Almaty']
    almaty_climate = weather.get_city_climate_summary('Almaty', almaty['latitude'], almaty['longitude'], almaty['elevation'])

    all_regions = sorted({
        r for r in list(GeoAsset.objects.values_list('region', flat=True))
        + list(GeoRiskZone.objects.values_list('region', flat=True))
        + list(InvestmentGeoOpportunity.objects.values_list('region', flat=True))
        if r
    })

    return render(request, 'geo_intelligence/command_centre.html', {
        'map_html': map_html,
        'assets': assets, 'risk_zones': zones, 'opportunities': opportunities,
        'almaty_climate': almaty_climate,
        'all_regions': all_regions,
        'query': query, 'region_filter': region_filter, 'layer_filter': layer_filter, 'risk_level_filter': risk_level_filter,
        'asset_count': GeoAsset.objects.count(),
        'risk_zone_count': GeoRiskZone.objects.count(),
        'opportunity_count': InvestmentGeoOpportunity.objects.count(),
    })
