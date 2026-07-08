"""
intelligence_analytics_engine/services/ranking.py — Modernisation Priority
Ranking.

Uses sklearn.preprocessing.MinMaxScaler to produce a comparable 0-100
percentile alongside the raw score — a transparent linear rescaling, not a
model. Prefers geo_intelligence's real modernisation_priority_score
(country-level Geo Intelligence signal) where it exists, and honestly falls
back to the existing six-pillar modernization_score (always available, but
a different, coarser signal) where it doesn't — every result names which
source was actually used, never silently blending the two into one number.
"""
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from intelligence_analytics_engine.services.features import build_company_features, build_country_features


def _rank(df, top_n=None):
    df = df.copy()
    df['effective_modernisation_score'] = df['modernisation_priority_score']
    df['modernisation_source'] = 'geo_intelligence_country_level_proxy'
    fallback_mask = df['effective_modernisation_score'].isna()
    df.loc[fallback_mask, 'effective_modernisation_score'] = df.loc[fallback_mask, 'modernization_score']
    df.loc[fallback_mask, 'modernisation_source'] = 'six_pillar_modernization_score_fallback'

    ranked = df.dropna(subset=['effective_modernisation_score']).copy()
    if ranked.empty:
        return {'available': False, 'reason': 'No company/country has any modernisation-relevant score yet.'}

    scaler = MinMaxScaler()
    ranked['percentile'] = scaler.fit_transform(ranked[['effective_modernisation_score']]).flatten() * 100
    ranked = ranked.sort_values('effective_modernisation_score', ascending=False)
    ranked['rank'] = range(1, len(ranked) + 1)

    results = []
    selected = ranked if top_n is None else ranked.head(top_n)
    for pk, row in selected.iterrows():
        source_label = (
            'Geo Intelligence country-level modernisation priority'
            if row['modernisation_source'] == 'geo_intelligence_country_level_proxy'
            else 'Six-pillar EcoIQ modernization score (Geo Intelligence data not available)'
        )
        results.append({
            'id': int(pk),
            'name': row['name'],
            'rank': int(row['rank']),
            'score': round(float(row['effective_modernisation_score']), 1),
            'percentile': round(float(row['percentile']), 1),
            'source': row['modernisation_source'],
            'explanation': f'{source_label}: {row["effective_modernisation_score"]:.1f}/100, {row["percentile"]:.0f}th percentile of {len(ranked)} ranked.',
        })

    return {
        'available': True,
        'method': 'sklearn.preprocessing.MinMaxScaler percentile over modernisation_priority_score with an honest fallback to modernization_score',
        'total_ranked': len(ranked),
        'results': results,
    }


def modernisation_priority_ranking(scope='company', top_n=20):
    if scope not in ('company', 'country'):
        raise ValueError("scope must be 'company' or 'country'")
    df = build_company_features() if scope == 'company' else build_country_features()
    return _rank(df, top_n)
