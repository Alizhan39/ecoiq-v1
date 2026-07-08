"""
pandas_scoring_engine/services/scoring.py — the EcoIQ Intelligence Score.

A separate, additive composite score — NOT a replacement for the existing
six-pillar governance/ESG engine (companies/scoring.py), which remains the
one thing rankings pages order by (CompanyProfile.ecoiq_total_score). This
module reuses that score as one input rather than recomputing it.

Six components, each independently explainable:
  governance_esg           25%  — companies.scoring's existing total score, reused
  evidence_quality         20%  — evidence_memory.EvidenceMemory rows for this company
  climate_risk             20%  — geo_intelligence.GeoRiskZone, country-level
  investment_opportunity   15%  — geo_intelligence.InvestmentGeoOpportunity, country-level
  modernisation_priority   10%  — geo_intelligence.GeoAsset.modernisation_priority, country-level
  geo_exposure             10%  — geo_intelligence.GeoAsset.climate_exposure_score, country-level

"Country-level" here is a real, honestly-labelled limitation, not a
shortcut: geo_intelligence's Phase 1 models (GeoAsset/GeoRiskZone/
InvestmentGeoOpportunity) FK to countries.CountryProfile, not to a specific
company — there is no per-company geocoding yet (see geo_intelligence's own
models.py docstring). A company's real country of operation (league.Company.
country, matched by name to CountryProfile) is a genuine geographic signal,
just a coarser one than a per-asset measurement would be — the explanation
for each of these three components says so explicitly.

Every component that has no real underlying data resolves to None rather
than a fabricated number, and is excluded from the final weighted average —
weights are renormalized over only the components that were actually
computed (see _weighted_average). pandas/numpy do the actual normalization
and weighting arithmetic, not just decorative imports: components are
assembled into a DataFrame so contribution/weight bookkeeping is done in one
consistent, auditable place rather than as scattered per-component code.
"""
import numpy as np
import pandas as pd

COMPONENT_WEIGHTS = {
    'governance_esg':         0.25,
    'evidence_quality':       0.20,
    'climate_risk':           0.20,
    'investment_opportunity': 0.15,
    'modernisation_priority': 0.10,
    'geo_exposure':           0.10,
}

_SEVERITY_TO_SCORE = {'low': 30.0, 'medium': 60.0, 'high': 90.0}
_PRIORITY_TO_SCORE = {'low': 30.0, 'medium': 60.0, 'high': 90.0}


def _resolve_country_profile(company_profile):
    """
    league.Company.country is a plain CharField (e.g. 'Kazakhstan'), not a
    FK — matched here by exact name against countries.CountryProfile. If
    the company has no linked league.Company or no country name matches,
    returns None honestly rather than guessing.
    """
    if not company_profile.company_id:
        return None
    country_name = company_profile.company.country
    if not country_name:
        return None
    from countries.models import CountryProfile
    return CountryProfile.objects.filter(name__iexact=country_name).first()


def _component_governance_esg(company_profile):
    score = company_profile.ecoiq_total_score
    if score is None:
        return None
    return {
        'raw': {'ecoiq_total_score': score},
        'normalized': round(float(score), 1),
        'confidence': 90.0,  # mature, well-established existing engine
        'explanation': (
            f'Reused directly from the existing six-pillar EcoIQ governance/ESG score '
            f'(companies.scoring.compute_ecoiq_profile_score): {score:.1f}/100.'
        ),
    }


def _component_evidence_quality(company_profile):
    from evidence_memory.models import EvidenceMemory

    memories = EvidenceMemory.objects.filter(company=company_profile)
    total = memories.count()
    if total == 0:
        return None

    embedded = memories.filter(embedding_status='embedded').count()
    confidences = list(memories.exclude(confidence__isnull=True).values_list('confidence', flat=True))
    avg_confidence = float(np.mean(confidences)) if confidences else 50.0
    embedded_ratio = embedded / total

    normalized = float(np.clip(avg_confidence * 0.7 + embedded_ratio * 100 * 0.3, 0, 100))
    # More corroborating evidence records = more confidence in this component
    # itself (capped — ten or more records is already a strong signal).
    component_confidence = float(np.clip(total * 10, 0, 90))

    return {
        'raw': {'evidence_count': total, 'embedded_count': embedded, 'avg_confidence': round(avg_confidence, 1)},
        'normalized': round(normalized, 1),
        'confidence': round(component_confidence, 1),
        'explanation': (
            f'{total} evidence memory record(s) for this company, {embedded} embedded, '
            f'average recorded confidence {avg_confidence:.1f}%.'
        ),
    }


def _component_climate_risk(country_profile):
    if country_profile is None:
        return None
    from geo_intelligence.models import GeoRiskZone

    zones = list(GeoRiskZone.objects.filter(country=country_profile).values('severity', 'confidence'))
    if not zones:
        return None

    df = pd.DataFrame(zones)
    df['severity_score'] = df['severity'].map(_SEVERITY_TO_SCORE)
    normalized = float(df['severity_score'].mean())
    confidences = df['confidence'].dropna()
    avg_confidence = float(confidences.mean()) if not confidences.empty else 40.0

    return {
        'raw': {'risk_zone_count': len(df), 'severities': df['severity'].value_counts().to_dict()},
        'normalized': round(normalized, 1),
        'confidence': round(avg_confidence, 1),
        'explanation': (
            f'Country-level proxy (via {country_profile.name}) from {len(df)} Geo Intelligence risk '
            f'zone(s) — not a per-asset measurement for this specific company.'
        ),
    }


def _component_investment_opportunity(country_profile):
    if country_profile is None:
        return None
    from geo_intelligence.models import InvestmentGeoOpportunity

    rows = list(
        InvestmentGeoOpportunity.objects.filter(country=country_profile, investment_score__isnull=False)
        .values('investment_score', 'confidence'),
    )
    if not rows:
        return None

    df = pd.DataFrame(rows)
    normalized = float(np.clip(df['investment_score'].mean(), 0, 100))
    confidences = df['confidence'].dropna()
    avg_confidence = float(confidences.mean()) if not confidences.empty else 40.0

    return {
        'raw': {'opportunity_count': len(df), 'avg_investment_score': round(normalized, 1)},
        'normalized': round(normalized, 1),
        'confidence': round(avg_confidence, 1),
        'explanation': (
            f'Country-level proxy (via {country_profile.name}) from {len(df)} Geo Intelligence '
            f'investment opportunity/ies — not specific to this company\'s own assets.'
        ),
    }


def _component_modernisation_priority(country_profile):
    if country_profile is None:
        return None
    from geo_intelligence.models import GeoAsset

    priorities = list(
        GeoAsset.objects.filter(country=country_profile).exclude(modernisation_priority='not_assessed')
        .values_list('modernisation_priority', flat=True),
    )
    if not priorities:
        return None

    series = pd.Series(priorities).map(_PRIORITY_TO_SCORE)
    normalized = float(series.mean())

    return {
        'raw': {'assets_assessed': len(priorities), 'distribution': pd.Series(priorities).value_counts().to_dict()},
        'normalized': round(normalized, 1),
        'confidence': 55.0,  # categorical, not a measured continuous value
        'explanation': (
            f'Country-level proxy (via {country_profile.name}) from {len(priorities)} Geo Intelligence '
            f'asset(s) with an assessed modernisation priority.'
        ),
    }


def _component_geo_exposure(country_profile):
    if country_profile is None:
        return None
    from geo_intelligence.models import GeoAsset

    scores = list(
        GeoAsset.objects.filter(country=country_profile, climate_exposure_score__isnull=False)
        .values_list('climate_exposure_score', flat=True),
    )
    if not scores:
        return None

    normalized = float(np.clip(np.mean(scores), 0, 100))
    return {
        'raw': {'assets_scored': len(scores)},
        'normalized': round(normalized, 1),
        'confidence': 50.0,
        'explanation': (
            f'Country-level proxy (via {country_profile.name}) from {len(scores)} Geo Intelligence '
            f'asset(s) with a real computed climate exposure score.'
        ),
    }


def _weighted_average(components):
    """
    components: {name: {'normalized': float, 'confidence': float, ...} | None}
    Renormalizes weights over only the non-None components — pandas does the
    actual weighting arithmetic so it's identical (and auditable) for both
    the final score and the aggregate confidence.
    """
    available = {name: c for name, c in components.items() if c is not None}
    if not available:
        return None, None

    df = pd.DataFrame({
        'normalized': {n: c['normalized'] for n, c in available.items()},
        'confidence': {n: c['confidence'] for n, c in available.items()},
        'weight': {n: COMPONENT_WEIGHTS[n] for n in available},
    })
    df['weight'] = df['weight'] / df['weight'].sum()  # renormalize over available components only
    df['contribution'] = df['normalized'] * df['weight']

    final_score = float(df['contribution'].sum())
    final_confidence = float(np.average(df['confidence'], weights=df['weight']))
    return round(final_score, 1), round(final_confidence, 1)


def compute_company_intelligence_score(company_profile):
    """
    Returns a dict ready to pass as `intelligence_scores=` to
    CompanyScoreSnapshot.create_from_profile(), with a full explanation
    trace: {component: {raw, normalized, weight, contribution, confidence,
    explanation}} for every component that had real data to compute from.
    """
    country_profile = _resolve_country_profile(company_profile)

    components = {
        'governance_esg':         _component_governance_esg(company_profile),
        'evidence_quality':       _component_evidence_quality(company_profile),
        'climate_risk':           _component_climate_risk(country_profile),
        'investment_opportunity': _component_investment_opportunity(country_profile),
        'modernisation_priority': _component_modernisation_priority(country_profile),
        'geo_exposure':           _component_geo_exposure(country_profile),
    }
    final_score, final_confidence = _weighted_average(components)

    available_count = sum(1 for c in components.values() if c is not None)
    explanation = {
        'country_resolved': country_profile.name if country_profile else None,
        'components_available': f'{available_count} of {len(components)}',
        'components': {},
    }
    for name, component in components.items():
        if component is None:
            explanation['components'][name] = {'available': False, 'weight': COMPONENT_WEIGHTS[name]}
            continue
        renormalized_weight = COMPONENT_WEIGHTS[name] / sum(
            COMPONENT_WEIGHTS[n] for n, c in components.items() if c is not None
        )
        explanation['components'][name] = {
            'available': True,
            'raw': component['raw'],
            'normalized_score': component['normalized'],
            'base_weight': COMPONENT_WEIGHTS[name],
            'renormalized_weight': round(renormalized_weight, 3),
            'contribution': round(component['normalized'] * renormalized_weight, 1),
            'confidence': component['confidence'],
            'explanation': component['explanation'],
        }

    return {
        'intelligence_score': final_score,
        'climate_risk_score': components['climate_risk']['normalized'] if components['climate_risk'] else None,
        'evidence_quality_score': components['evidence_quality']['normalized'] if components['evidence_quality'] else None,
        'investment_opportunity_score': components['investment_opportunity']['normalized'] if components['investment_opportunity'] else None,
        'modernisation_priority_score': components['modernisation_priority']['normalized'] if components['modernisation_priority'] else None,
        'geo_exposure_score': components['geo_exposure']['normalized'] if components['geo_exposure'] else None,
        'confidence': final_confidence,
        'explanation': explanation,
    }


def compute_country_geo_components(country_profile):
    """
    Public entry point reusing the exact same country-level Geo Intelligence
    component functions compute_company_intelligence_score() uses internally
    — so intelligence_analytics_engine's country feature vectors are built
    from identical logic, not a second reimplementation. Returns
    {climate_risk_score, investment_opportunity_score,
    modernisation_priority_score, geo_exposure_score}, each None if that
    component has no real underlying Geo Intelligence data for this country.
    """
    climate_risk = _component_climate_risk(country_profile)
    investment_opportunity = _component_investment_opportunity(country_profile)
    modernisation_priority = _component_modernisation_priority(country_profile)
    geo_exposure = _component_geo_exposure(country_profile)
    return {
        'climate_risk_score': climate_risk['normalized'] if climate_risk else None,
        'investment_opportunity_score': investment_opportunity['normalized'] if investment_opportunity else None,
        'modernisation_priority_score': modernisation_priority['normalized'] if modernisation_priority else None,
        'geo_exposure_score': geo_exposure['normalized'] if geo_exposure else None,
    }
