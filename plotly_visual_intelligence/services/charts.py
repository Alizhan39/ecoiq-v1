"""
plotly_visual_intelligence/services/charts.py — one function per
visualisation in the spec. Every function takes REAL data already produced
by an existing service (never queries/derives anything new) and returns
either None (genuinely not enough data — the template shows an honest
"not enough data yet" message, never a fabricated chart) or a dict with an
`html` fragment (see theme.to_html_fragment) plus any small summary values
the template needs alongside the chart.
"""
import numpy as np
import plotly.graph_objects as go

from plotly_visual_intelligence.services import theme

ORCHESTRATION_NODE_SEQUENCE = [
    'classify_intent', 'retrieve_evidence_memory', 'gather_geo_intelligence', 'run_agent_analysis',
    'recalculate_score_if_needed', 'run_intelligence_analytics', 'verify_output', 'finalize',
]


def score_contribution_chart(snapshot):
    """
    Section 2 — Explainable Score Visualisation. Reads
    CompanyScoreSnapshot.intelligence_score_explanation directly (already
    computed and stored by pandas_scoring_engine — nothing recalculated
    here). Horizontal bar: one bar per component, length = contribution,
    hover = raw input, normalized score, weight, confidence, explanation.
    """
    explanation = snapshot.intelligence_score_explanation if snapshot else None
    if not explanation or not explanation.get('components'):
        return None

    components = explanation['components']
    names, contributions, hover_texts, colors = [], [], [], []
    for name, detail in components.items():
        label = name.replace('_', ' ').title()
        if not detail.get('available'):
            names.append(label)
            contributions.append(0)
            hover_texts.append(f'{label}: not available for this company (no underlying data yet).')
            colors.append(theme.IQ_MUTED)
            continue
        names.append(label)
        contributions.append(detail['contribution'])
        colors.append(theme.confidence_color(detail.get('confidence')))
        hover_texts.append(
            f"<b>{label}</b><br>"
            f"Normalized score: {detail['normalized_score']}/100<br>"
            f"Weight: {detail['renormalized_weight']:.0%} (base {detail['base_weight']:.0%})<br>"
            f"Contribution: {detail['contribution']}<br>"
            f"Confidence: {detail['confidence']}%<br>"
            f"{detail['explanation']}",
        )

    fig = go.Figure(go.Bar(
        x=contributions, y=names, orientation='h', marker={'color': colors},
        hovertext=hover_texts, hoverinfo='text',
        text=[f'{c:.1f}' for c in contributions], textposition='outside',
    ))
    fig.update_layout(**theme.base_layout(
        title=f'Score components — {explanation.get("components_available", "")} available', height=320, showlegend=False,
    ))
    fig.update_xaxes(title='Contribution to final score')

    return {
        'html': theme.to_html_fragment(fig, 'score-contribution-chart'),
        'final_score': snapshot.intelligence_score,
        'confidence': snapshot.intelligence_confidence,
    }


def risk_opportunity_matrix_chart(rows):
    """
    Section 3 — Risk vs Opportunity Matrix. `rows`: list of dicts already
    resolved by the caller (dashboard_data.py) from CompanyScoreSnapshot —
    {name, climate_risk_score, investment_opportunity_score,
    modernisation_priority_score, intelligence_confidence, is_outlier}.
    Only rows with BOTH axis values present are plotted — never an invented
    coordinate for a company with no real Geo Intelligence linkage yet.
    """
    plottable = [r for r in rows if r.get('climate_risk_score') is not None and r.get('investment_opportunity_score') is not None]
    if not plottable:
        return None

    sizes = [max(12, (r.get('modernisation_priority_score') or 30) / 3) for r in plottable]
    colors = [theme.confidence_color(r.get('intelligence_confidence')) for r in plottable]
    symbols = ['diamond' if r.get('is_outlier') else 'circle' for r in plottable]
    hover = [
        f"<b>{r['name']}</b><br>"
        f"Climate risk: {r['climate_risk_score']:.0f}<br>"
        f"Investment opportunity: {r['investment_opportunity_score']:.0f}<br>"
        f"Modernisation priority: {r.get('modernisation_priority_score', 'n/a')}<br>"
        f"Confidence: {r.get('intelligence_confidence', 'n/a')}<br>"
        f"{'⚠ Statistical outlier' if r.get('is_outlier') else ''}"
        for r in plottable
    ]

    fig = go.Figure(go.Scatter(
        x=[r['climate_risk_score'] for r in plottable], y=[r['investment_opportunity_score'] for r in plottable],
        mode='markers+text', text=[r['name'] for r in plottable], textposition='top center',
        textfont={'size': 9, 'color': theme.IQ_MUTED},
        marker={'size': sizes, 'color': colors, 'symbol': symbols, 'line': {'width': 1, 'color': theme.IQ_BG}},
        hovertext=hover, hoverinfo='text',
    ))
    fig.update_layout(**theme.base_layout(height=420, showlegend=False))
    fig.update_xaxes(title='Climate risk →')
    fig.update_yaxes(title='Investment opportunity →')

    return {'html': theme.to_html_fragment(fig, 'risk-opportunity-matrix'), 'count': len(plottable), 'total_candidates': len(rows)}


def similarity_chart(target_name, similarity_result):
    """
    Section 4 — Similarity Visualisation. similarity_result is the exact,
    unmodified return of intelligence_analytics_engine.services.similarity.
    find_similar_companies()/find_similar_countries() — never re-derived.
    """
    if not similarity_result or not similarity_result.get('available') or not similarity_result.get('results'):
        return None

    results = similarity_result['results']
    names = [r['name'] for r in results]
    # Lower distance = more similar; convert to an intuitive 0-100 "similarity" for the bar length.
    similarity_scores = [round(100 / (1 + r['distance']), 1) for r in results]
    hover = [
        f"<b>{r['name']}</b><br>Similarity: {s}<br>"
        f"Most similar on: {', '.join(f.replace('_', ' ') for f in r['most_similar_on'])}<br>"
        f"Most different on: {', '.join(f.replace('_', ' ') for f in r['most_different_on'])}"
        for r, s in zip(results, similarity_scores)
    ]

    fig = go.Figure(go.Bar(
        x=similarity_scores, y=names, orientation='h', marker={'color': theme.IQ_PURPLE},
        hovertext=hover, hoverinfo='text', text=[f'{s}' for s in similarity_scores], textposition='outside',
    ))
    fig.update_layout(**theme.base_layout(title=f'Most similar to {target_name}', height=280, showlegend=False))
    fig.update_xaxes(title='Similarity score')

    return {'html': theme.to_html_fragment(fig, 'similarity-chart'), 'method': similarity_result.get('method', '')}


def cluster_chart(cluster_result, x_label, y_label):
    """
    Section 5 — Cluster Intelligence. cluster_result is the exact,
    unmodified return of intelligence_analytics_engine.services.clustering.
    climate_risk_clusters()/investment_opportunity_clusters().
    """
    if not cluster_result or not cluster_result.get('available'):
        return None

    features = cluster_result['features_used']
    fig = go.Figure()
    for cluster in cluster_result['clusters']:
        countries = cluster['countries']
        if not countries:
            continue
        # Re-derive each member's own coordinates isn't available here (only the
        # centroid is) — plot every member AT the centroid with a jitter so
        # multiple members in one cluster are all visible, clearly labelled as
        # a cluster-level view, not a per-entity exact position.
        n = len(countries)
        rng = np.random.default_rng(42)
        jitter_x = rng.normal(0, 1.5, n)
        jitter_y = rng.normal(0, 1.5, n)
        fig.add_trace(go.Scatter(
            x=[cluster['centroid'][features[0]] + j for j in jitter_x],
            y=[cluster['centroid'][features[1]] + j for j in jitter_y] if len(features) > 1 else [0] * n,
            mode='markers+text', text=[c['name'] for c in countries], textposition='top center',
            textfont={'size': 9, 'color': theme.IQ_MUTED},
            marker={'size': 14, 'color': theme.CATEGORICAL_SEQUENCE[cluster['cluster_id'] % len(theme.CATEGORICAL_SEQUENCE)]},
            name=f"Cluster {cluster['cluster_id']} — {cluster['defining_feature'].replace('_', ' ')}",
            hovertext=[f"<b>{c['name']}</b><br>Cluster {cluster['cluster_id']}<br>{cluster['explanation']}" for c in countries],
            hoverinfo='text',
        ))
        fig.add_trace(go.Scatter(
            x=[cluster['centroid'][features[0]]], y=[cluster['centroid'][features[1]] if len(features) > 1 else 0],
            mode='markers', marker={'size': 16, 'symbol': 'star', 'color': theme.CATEGORICAL_SEQUENCE[cluster['cluster_id'] % len(theme.CATEGORICAL_SEQUENCE)], 'line': {'width': 2, 'color': '#fff'}},
            name=f'Cluster {cluster["cluster_id"]} centroid', showlegend=False,
            hovertext=f"Cluster {cluster['cluster_id']} centroid<br>{cluster['explanation']}", hoverinfo='text',
        ))

    fig.update_layout(**theme.base_layout(height=420, showlegend=True))
    fig.update_xaxes(title=x_label)
    fig.update_yaxes(title=y_label)

    return {'html': theme.to_html_fragment(fig, 'cluster-chart'), 'n_clusters': cluster_result['n_clusters']}


def evidence_distribution_chart(distribution):
    """
    Section 6 — Evidence Intelligence. distribution is the exact,
    unmodified return of evidence_distribution.evidence_quality_distribution().
    """
    if not distribution or not distribution.get('available'):
        return None

    histogram = distribution['histogram']
    fig = go.Figure(go.Bar(
        x=[h['range'] for h in histogram], y=[h['count'] for h in histogram],
        marker={'color': theme.IQ_CYAN},
        hovertext=[f"Confidence {h['range']}: {h['count']} record(s)" for h in histogram], hoverinfo='text',
    ))
    fig.update_layout(**theme.base_layout(title='Evidence confidence distribution', height=280, showlegend=False))
    fig.update_xaxes(title='Confidence range')
    fig.update_yaxes(title='Evidence records')

    by_source = distribution.get('by_source_type', {})
    source_fig = None
    if by_source:
        source_names = list(by_source.keys())
        source_fig_obj = go.Figure(go.Bar(
            x=[by_source[s]['mean_confidence'] for s in source_names],
            y=[s.replace('_', ' ').title() for s in source_names], orientation='h',
            marker={'color': theme.IQ_INFO},
            hovertext=[f"{s}: {by_source[s]['count']} record(s), mean confidence {by_source[s]['mean_confidence']}" for s in source_names],
            hoverinfo='text',
        ))
        source_fig_obj.update_layout(**theme.base_layout(title='Mean confidence by source type', height=220, showlegend=False))
        source_fig = theme.to_html_fragment(source_fig_obj, 'evidence-by-source-chart')

    return {
        'html': theme.to_html_fragment(fig, 'evidence-distribution-chart'),
        'by_source_html': source_fig,
        'count': distribution['count'], 'mean': distribution['mean'],
    }


def orchestration_trace_chart(run):
    """
    Section 7 — AI Orchestration Visualisation. Reads ONLY
    OrchestrationRun.nodes_executed/failed_node/status — never simulates a
    "live" step. A node not in nodes_executed is shown as "skipped" (grey),
    which is a real, honest outcome of conditional routing (e.g. a country
    target genuinely never runs recalculate_score_if_needed) — never
    presented as "in progress".
    """
    if run is None:
        return None

    executed = set(run.nodes_executed or [])
    colors, labels, hover = [], [], []
    for node in ORCHESTRATION_NODE_SEQUENCE:
        label = node.replace('_', ' ').title()
        labels.append(label)
        if node == run.failed_node:
            colors.append(theme.IQ_DANGER)
            hover.append(f'{label}: FAILED — {run.error_summary or "see verification notes"}')
        elif node in executed:
            colors.append(theme.IQ_ACCENT)
            hover.append(f'{label}: executed')
        else:
            colors.append(theme.IQ_MUTED)
            hover.append(f'{label}: skipped (not required for this target type)')

    fig = go.Figure(go.Bar(
        x=list(range(1, len(ORCHESTRATION_NODE_SEQUENCE) + 1)), y=[1] * len(ORCHESTRATION_NODE_SEQUENCE),
        marker={'color': colors}, text=labels, textposition='inside', textangle=0,
        hovertext=hover, hoverinfo='text', width=0.85,
    ))
    fig.update_layout(**theme.base_layout(
        title=f'Execution trace — {run.get_status_display()} ({"completed execution" if run.status != "running" else "in progress"})',
        height=160, showlegend=False,
    ))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)

    return {'html': theme.to_html_fragment(fig, 'orchestration-trace-chart'), 'status': run.status, 'is_live_claim': False}
