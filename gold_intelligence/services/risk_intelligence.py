"""
gold_intelligence/services/risk_intelligence.py — the 11 risk dimensions of
the Gold Intelligence Risk Intelligence page.

Reuses real, already-persisted data wherever it exists — never a second risk
model:
  climate / water / infrastructure  → geo_intelligence.GeoRiskZone, scoped to
                                       the project's country (see
                                       GoldProject.risk_zones)
  political                         → countries.CountryProfile.policy_environment_score
  environmental                     → countries.CountryProfile.fossil_fuel_dependency
  energy                            → geo_intelligence.GeoAsset power_plant rows
                                       in the project's country

community / supply_chain / financial / construction / operational have no
real data source anywhere in this platform today — each returns an honest
"not yet available" reason (the exact convention already used by
core/globe.py's trade_and_revenue_composition), never a fabricated risk
level.
"""
_SEVERITY_ORDER = {'high': 3, 'medium': 2, 'low': 1}


def _unavailable(reason):
    return {'available': False, 'level': None, 'reason': reason}


def _zone_dimension(project, risk_types, not_recorded_reason):
    zones = list(project.risk_zones.filter(risk_type__in=risk_types))
    if not zones:
        return _unavailable(not_recorded_reason)
    worst = max(zones, key=lambda z: _SEVERITY_ORDER.get(z.severity, 0))
    return {
        'available': True, 'level': worst.severity,
        'detail': f'{worst.get_severity_display()} — {worst.name}',
        'zone_count': len(zones), 'is_demo': all(z.is_demo for z in zones),
    }


def _climate_dimension(project):
    return _zone_dimension(
        project, ['extreme_heat', 'flood', 'drought'],
        'No real Geo Intelligence climate risk zone recorded for this project’s country yet.',
    )


def _water_dimension(project):
    return _zone_dimension(
        project, ['water_stress'],
        'No real Geo Intelligence water-stress zone recorded for this project’s country yet.',
    )


def _infrastructure_dimension(project):
    return _zone_dimension(
        project, ['infrastructure_exposure'],
        'No real Geo Intelligence infrastructure-exposure zone recorded for this project’s country yet.',
    )


def _political_dimension(project):
    country = project.country
    if country is None or country.policy_environment_score in (None, 0, 0.0):
        return _unavailable('Data source required for this country’s policy/governance score.')
    score = country.policy_environment_score
    level = 'low' if score >= 60 else 'medium' if score >= 35 else 'high'
    return {
        'available': True, 'level': level,
        'detail': f'Country-level proxy: policy/governance score {score}/100 ({country.name})',
        'score': score,
    }


def _environmental_dimension(project):
    country = project.country
    if country is None or country.fossil_fuel_dependency in (None, 0, 0.0):
        return _unavailable('Data source required for this country’s environmental indicators.')
    value = country.fossil_fuel_dependency
    level = 'high' if value >= 80 else 'medium' if value >= 50 else 'low'
    return {
        'available': True, 'level': level,
        'detail': f'Country-level proxy: fossil fuel dependency {value}% ({country.name})',
        'value': value,
    }


def _energy_dimension(project):
    from geo_intelligence.models import GeoAsset

    if project.country_id is None:
        return _unavailable('Data source required for regional power infrastructure.')
    plants = GeoAsset.objects.filter(country_id=project.country_id, asset_type='power_plant')
    count = plants.count()
    if count == 0:
        return _unavailable('No real power infrastructure recorded in this project’s country yet.')
    return {
        'available': True, 'level': 'low',
        'detail': f'{count} real power asset(s) recorded in-country',
        'asset_count': count,
    }


RISK_DIMENSION_LABELS = {
    'political': 'Political', 'environmental': 'Environmental', 'climate': 'Climate',
    'water': 'Water', 'energy': 'Energy', 'infrastructure': 'Infrastructure',
    'community': 'Community', 'supply_chain': 'Supply Chain', 'financial': 'Financial',
    'construction': 'Construction', 'operational': 'Operational',
}


def compute_risk_intelligence(project):
    """Returns {dimension_key: {'available', 'level', 'detail'|'reason', ...}}
    for all 11 dimensions — never invents a risk level where no real data
    source exists."""
    return {
        'political': _political_dimension(project),
        'environmental': _environmental_dimension(project),
        'climate': _climate_dimension(project),
        'water': _water_dimension(project),
        'energy': _energy_dimension(project),
        'infrastructure': _infrastructure_dimension(project),
        'community': _unavailable('EcoIQ does not yet ingest community / social licence data for this region.'),
        'supply_chain': _unavailable('EcoIQ does not yet ingest supply chain risk data for this region.'),
        'financial': _unavailable('EcoIQ does not yet ingest project-level financial/counterparty risk data.'),
        'construction': _unavailable('EcoIQ does not yet ingest construction/contractor risk data for this project.'),
        'operational': _unavailable('EcoIQ does not yet ingest operational/safety incident data for this project.'),
    }
