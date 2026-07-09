"""
decision_studio/services/visualization.py — builds ONLY the chart(s)
relevant to a specific question, reusing plotly_visual_intelligence.
services.charts directly (no new chart-building code, no new theme).
Every chart function already returns None when there's no real data to
plot — this module never overrides that with a fabricated chart.
"""
from plotly_visual_intelligence.services import charts


def _snapshot_row(profile):
    from plotly_visual_intelligence.services.dashboard_data import latest_intelligence_snapshot

    snapshot = latest_intelligence_snapshot(profile)
    if snapshot is None:
        return None
    return {
        'company_id': profile.pk, 'name': profile.company.name if profile.company_id else f'Profile #{profile.pk}',
        'climate_risk_score': snapshot.climate_risk_score,
        'investment_opportunity_score': snapshot.investment_opportunity_score,
        'modernisation_priority_score': snapshot.modernisation_priority_score,
        'intelligence_confidence': snapshot.intelligence_confidence,
        'is_outlier': False,
    }, snapshot


def build_visualizations(intent, profiles, ranking):
    visualizations = []

    if len(profiles) == 1:
        outcome = _snapshot_row(profiles[0])
        if outcome:
            _, snapshot = outcome
            chart = charts.score_contribution_chart(snapshot)
            if chart:
                name = profiles[0].company.name if profiles[0].company_id else profiles[0].pk
                visualizations.append({'title': f'Score breakdown — {name}', 'chart': chart})

    if len(profiles) > 1:
        rows = []
        for profile in profiles:
            outcome = _snapshot_row(profile)
            if outcome:
                rows.append(outcome[0])
        chart = charts.risk_opportunity_matrix_chart(rows)
        if chart:
            visualizations.append({'title': 'Risk vs Opportunity', 'chart': chart})

    return visualizations
