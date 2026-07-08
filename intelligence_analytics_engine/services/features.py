"""
intelligence_analytics_engine/services/features.py — the one shared feature
frame builder every other service in this app uses. Every other module
(similarity, clustering, ranking, distribution, outliers, recommendations)
calls into build_company_features()/build_country_features() rather than
re-deriving feature values from the underlying models itself — one place to
change if a feature definition needs to change, and every downstream
capability is guaranteed to agree on what "the features" are.

Company features always include the six existing EcoIQ pillar scores
(companies.scoring) — real for every company with a computed profile, not
dependent on sparse geo/evidence linkage. The newer Pandas Scoring Engine
components (evidence_quality, climate_risk, investment_opportunity,
modernisation_priority, geo_exposure) are added as extra columns from each
company's most recent CompanyScoreSnapshot that actually has a value — NaN
where no such snapshot exists yet, not a fabricated number, and every
sklearn-facing function downstream is expected to handle NaN explicitly
(imputed with the column mean and flagged, never silently zero-filled).
"""
import numpy as np
import pandas as pd

COMPANY_CORE_COLUMNS = [
    'public_benefit_score', 'environmental_responsibility_score', 'modernization_score',
    'transparency_anti_corruption_score', 'anti_corruption_score', 'ethical_alignment_score',
    'ecoiq_total_score',
]
COMPANY_INTELLIGENCE_COLUMNS = [
    'evidence_quality_score', 'climate_risk_score', 'investment_opportunity_score',
    'modernisation_priority_score', 'geo_exposure_score', 'intelligence_confidence',
]
COUNTRY_GEO_COLUMNS = [
    'climate_risk_score', 'investment_opportunity_score', 'modernisation_priority_score', 'geo_exposure_score',
]


def build_company_features(queryset=None):
    """
    Returns a pandas DataFrame indexed by CompanyProfile.pk with columns:
    name, sector, country, + COMPANY_CORE_COLUMNS + COMPANY_INTELLIGENCE_COLUMNS.
    """
    from companies.models import CompanyProfile

    queryset = queryset if queryset is not None else CompanyProfile.objects.filter(
        status__in=('public', 'verified'), ecoiq_total_score__isnull=False,
    )
    queryset = queryset.select_related('company')

    rows = []
    for profile in queryset:
        row = {
            'pk': profile.pk,
            'name': profile.company.name if profile.company_id else f'Profile #{profile.pk}',
            'sector': profile.company.sector if profile.company_id else '',
            'country': profile.company.country if profile.company_id else '',
        }
        for col in COMPANY_CORE_COLUMNS:
            row[col] = getattr(profile, col)

        latest_snapshot = (
            profile.score_snapshots.filter(intelligence_score__isnull=False).order_by('-date', '-created_at').first()
        )
        for col in COMPANY_INTELLIGENCE_COLUMNS:
            row[col] = getattr(latest_snapshot, col) if latest_snapshot else np.nan
        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=['pk', 'name', 'sector', 'country'] + COMPANY_CORE_COLUMNS + COMPANY_INTELLIGENCE_COLUMNS).set_index('pk')
    return pd.DataFrame(rows).set_index('pk')


def build_country_features(queryset=None):
    """
    Returns a pandas DataFrame indexed by CountryProfile.pk with columns:
    name, company_count, avg_ecoiq_total_score, + the six pillar averages
    (across companies whose league.Company.country name-matches this
    country — the same real, honestly-labelled linkage
    pandas_scoring_engine.compute_company_intelligence_score() uses) +
    COUNTRY_GEO_COLUMNS (via pandas_scoring_engine.compute_country_geo_components,
    reused rather than reimplemented) + evidence_quality_score (from
    evidence_memory.EvidenceMemory rows scoped to this country).
    """
    from companies.models import CompanyProfile
    from countries.models import CountryProfile
    from evidence_memory.models import EvidenceMemory
    from pandas_scoring_engine.services.scoring import compute_country_geo_components

    queryset = queryset if queryset is not None else CountryProfile.objects.all()
    company_df = build_company_features()

    rows = []
    for country in queryset:
        matched = company_df[company_df['country'].str.lower() == country.name.lower()] if not company_df.empty else company_df
        row = {'pk': country.pk, 'name': country.name, 'company_count': len(matched)}
        for col in COMPANY_CORE_COLUMNS:
            row[col] = matched[col].mean() if not matched.empty else np.nan

        row.update(compute_country_geo_components(country))

        confidences = list(
            EvidenceMemory.objects.filter(country=country).exclude(confidence__isnull=True).values_list('confidence', flat=True),
        )
        row['evidence_quality_score'] = float(np.mean(confidences)) if confidences else np.nan
        rows.append(row)

    if not rows:
        columns = ['pk', 'name', 'company_count'] + COMPANY_CORE_COLUMNS + COUNTRY_GEO_COLUMNS + ['evidence_quality_score']
        return pd.DataFrame(columns=columns).set_index('pk')
    return pd.DataFrame(rows).set_index('pk')
