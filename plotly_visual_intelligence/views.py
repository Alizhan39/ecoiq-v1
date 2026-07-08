"""
plotly_visual_intelligence/views.py — the one dashboard view. Aggregates
via dashboard_data.py, builds charts via charts.py; contains no scoring/
evidence/geo/analytics logic of its own.
"""
from django.shortcuts import render

from plotly_visual_intelligence.services import charts, dashboard_data


def dashboard(request):
    company_id = request.GET.get('company_id')
    company_id = int(company_id) if company_id and company_id.isdigit() else None
    run_id = request.GET.get('orchestration_run_id')
    run_id = int(run_id) if run_id and run_id.isdigit() else None

    focus_profile = dashboard_data.resolve_focus_company(company_id)
    focus_run = dashboard_data.resolve_focus_orchestration_run(run_id)
    focus_snapshot = dashboard_data.latest_intelligence_snapshot(focus_profile) if focus_profile else None

    kpi_cards = dashboard_data.build_kpi_cards(focus_profile)
    score_chart = charts.score_contribution_chart(focus_snapshot) if focus_snapshot else None

    risk_opportunity_rows = dashboard_data.build_risk_opportunity_rows()
    risk_opportunity_chart = charts.risk_opportunity_matrix_chart(risk_opportunity_rows)

    similarity_result = dashboard_data.build_similarity_context(focus_profile)
    similarity_chart = charts.similarity_chart(
        focus_profile.company.name if focus_profile and focus_profile.company_id else '', similarity_result,
    ) if similarity_result else None

    cluster_result = dashboard_data.build_cluster_context()
    cluster_chart = charts.cluster_chart(cluster_result, 'Climate risk', 'Geo exposure') if cluster_result else None

    evidence_context = dashboard_data.build_evidence_context(focus_profile)
    evidence_chart = charts.evidence_distribution_chart(evidence_context['platform_wide'])
    evidence_scoped_chart = (
        charts.evidence_distribution_chart(evidence_context['scoped']) if evidence_context['scoped'] else None
    )

    orchestration_chart = charts.orchestration_trace_chart(focus_run) if focus_run else None

    recommendations_result = dashboard_data.build_recommendations_context(focus_profile)

    return render(request, 'plotly_visual_intelligence/dashboard.html', {
        'focus_profile': focus_profile,
        'focus_run': focus_run,
        'company_choices': [{'id': r['company_id'], 'name': r['name']} for r in risk_opportunity_rows],
        'kpi_cards': kpi_cards,
        'score_chart': score_chart,
        'risk_opportunity_chart': risk_opportunity_chart,
        'similarity_chart': similarity_chart,
        'cluster_chart': cluster_chart,
        'evidence_context': evidence_context,
        'evidence_chart': evidence_chart,
        'evidence_scoped_chart': evidence_scoped_chart,
        'orchestration_chart': orchestration_chart,
        'recommendations_result': recommendations_result,
    })
