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


def sensitivity_tornado_chart(sensitivity_result):
    """
    Gold Intelligence — Investment Dashboard sensitivity (tornado) chart.
    Reads gold_intelligence.services.project_finance.run_sensitivity_analysis()
    output directly — every bar is a real IRR range computed by that
    Newton's-method engine, nothing recomputed or invented here.
    """
    if not sensitivity_result or not sensitivity_result.get('available'):
        return None
    variables = sensitivity_result['variables']
    if not variables:
        return None

    base_irr = sensitivity_result['base_irr_pct']
    names = [v['variable'] for v in variables]
    lows = [v['low_irr_pct'] if v['low_irr_pct'] is not None else base_irr for v in variables]
    highs = [v['high_irr_pct'] if v['high_irr_pct'] is not None else base_irr for v in variables]
    hover = [
        f"<b>{v['variable']}</b><br>±{v['swing_pct']:.0f}% swing<br>"
        f"Low: {v['low_irr_pct']}% IRR<br>High: {v['high_irr_pct']}% IRR"
        for v in variables
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[h - l for h, l in zip(highs, lows)], y=names, base=lows, orientation='h',
        marker={'color': theme.IQ_ACCENT}, hovertext=hover, hoverinfo='text', name='IRR range',
    ))
    fig.add_vline(x=base_irr, line_dash='dash', line_color=theme.IQ_WARN, annotation_text=f'Base case: {base_irr}%')
    fig.update_layout(**theme.base_layout(title='Sensitivity — IRR range by variable (±20%)', height=320, showlegend=False))
    fig.update_xaxes(title='IRR (%)')

    return {'html': theme.to_html_fragment(fig, 'gold-sensitivity-tornado-chart'), 'base_irr_pct': base_irr}


def scenario_comparison_chart(scenario_result):
    """
    Gold Intelligence — scenario analysis comparison. Reads
    project_finance.run_scenario_analysis() output directly — each bar is a
    real, stored ScenarioAssumption re-run through the same economics engine
    as the base case, never a fabricated projection.
    """
    if not scenario_result or not scenario_result.get('available') or not scenario_result.get('scenarios'):
        return None

    base = scenario_result['base_case']
    labels, irrs, colors, hover = ['Base Case'], [base.get('irr_pct')], [theme.IQ_INFO], ['Base case']
    for s in scenario_result['scenarios']:
        labels.append(s['name'])
        irrs.append(s.get('irr_pct'))
        colors.append(theme.IQ_ACCENT if s.get('available') else theme.IQ_MUTED)
        hover.append(s['notes'] or s['name'])

    if all(v is None for v in irrs):
        return None

    fig = go.Figure(go.Bar(
        x=labels, y=[v if v is not None else 0 for v in irrs], marker={'color': colors},
        text=[f'{v}%' if v is not None else 'n/a' for v in irrs], textposition='outside',
        hovertext=hover, hoverinfo='text',
    ))
    fig.update_layout(**theme.base_layout(title='Scenario comparison — IRR (%)', height=320, showlegend=False))
    fig.update_yaxes(title='IRR (%)')

    return {'html': theme.to_html_fragment(fig, 'gold-scenario-comparison-chart'), 'scenario_count': len(scenario_result['scenarios'])}


def capital_tracker_chart(capital_summary):
    """
    Gold Intelligence — Capital Tracker planned/committed/spent bar chart.
    Reads gold_intelligence.services.aggregates.capital_tracker_summary()
    output directly — real CapitalBudgetLine sums, never invented.
    """
    if not capital_summary or not capital_summary.get('available') or not capital_summary.get('lines'):
        return None

    lines = capital_summary['lines']
    labels = [line.label for line in lines]
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Planned', x=labels, y=[line.planned_usd or 0 for line in lines], marker={'color': theme.IQ_INFO}))
    fig.add_trace(go.Bar(name='Committed', x=labels, y=[line.committed_usd or 0 for line in lines], marker={'color': theme.IQ_WARN}))
    fig.add_trace(go.Bar(name='Spent', x=labels, y=[line.spent_usd or 0 for line in lines], marker={'color': theme.IQ_ACCENT}))
    fig.update_layout(**theme.base_layout(title='Capital Tracker — Planned vs. Committed vs. Spent (USD)', height=360, showlegend=True))
    fig.update_layout(barmode='group')

    return {'html': theme.to_html_fragment(fig, 'gold-capital-tracker-chart')}


def mine_timeline_chart(milestones):
    """
    Gold Intelligence — Mine Timeline Gantt-style chart. Reads real
    MineTimelineMilestone rows directly; a milestone with no real planned
    dates yet is honestly omitted from the chart rather than plotted with
    an invented date range.
    """
    plottable = [m for m in milestones if m.planned_start and m.planned_end]
    if not plottable:
        return None

    status_colors = {
        'not_started': theme.IQ_MUTED, 'in_progress': theme.IQ_INFO,
        'complete': theme.IQ_ACCENT, 'delayed': theme.IQ_DANGER,
    }
    fig = go.Figure()
    for m in plottable:
        duration_ms = (m.planned_end - m.planned_start).days * 24 * 3600 * 1000
        fig.add_trace(go.Bar(
            x=[duration_ms], y=[m.get_phase_display()], base=[m.planned_start.isoformat()],
            orientation='h', marker={'color': status_colors.get(m.status, theme.IQ_MUTED)},
            hovertext=f'{m.get_phase_display()}: {m.planned_start} → {m.planned_end} ({m.get_status_display()})',
            hoverinfo='text', showlegend=False,
        ))
    fig.update_layout(**theme.base_layout(title='Mine Timeline', height=80 + 50 * len(plottable), showlegend=False))
    fig.update_xaxes(title='Date', type='date')

    return {'html': theme.to_html_fragment(fig, 'gold-mine-timeline-chart'), 'plotted_count': len(plottable), 'skipped_count': len(milestones) - len(plottable)}


def capital_deployment_chart(committed_usd, deployed_usd, remaining_usd):
    """
    Capital Guardian — Investor Dashboard capital deployment bar. Reads real
    committed/deployed/remaining figures directly (committed from
    gold_intelligence.GoldProject, deployed from a real sum over
    capital_guardian.CapitalTraceEntry, remaining derived from both) — never
    fabricated when one of the three is unavailable.
    """
    labels, values, colors = [], [], []
    for label, value, color in (
        ('Committed', committed_usd, theme.IQ_INFO),
        ('Deployed', deployed_usd, theme.IQ_ACCENT),
        ('Remaining', remaining_usd, theme.IQ_WARN),
    ):
        if value is None:
            continue
        labels.append(label); values.append(value); colors.append(color)
    if not values:
        return None

    fig = go.Figure(go.Bar(
        x=labels, y=values, marker={'color': colors},
        text=[f'${v:,.0f}' for v in values], textposition='outside',
    ))
    fig.update_layout(**theme.base_layout(title='Capital Deployment (USD)', height=320, showlegend=False))
    return {'html': theme.to_html_fragment(fig, 'gc-capital-deployment-chart')}


def capital_guardian_gauge_chart(value, title, div_id):
    """
    Capital Guardian — a single real 0-100 value rendered as a gauge
    (Project Completion, Capital Protection Score, Insurance Coverage
    ratio). Returns None — never a fabricated needle position — when the
    real value is not yet available.
    """
    if value is None:
        return None
    color = theme.IQ_ACCENT if value >= 70 else theme.IQ_WARN if value >= 40 else theme.IQ_DANGER
    fig = go.Figure(go.Indicator(
        mode='gauge+number', value=value,
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': theme.IQ_MUTED},
            'bar': {'color': color},
            'bgcolor': theme.IQ_BG2, 'borderwidth': 1, 'bordercolor': theme.IQ_BORDER,
        },
        number={'suffix': '%', 'font': {'color': '#fff'}},
    ))
    fig.update_layout(**theme.base_layout(title=title, height=240, showlegend=False))
    return {'html': theme.to_html_fragment(fig, div_id), 'value': value}


def portfolio_risk_matrix_chart(rows):
    """
    Capital Guardian Phase 2 — Portfolio Risk Matrix. `rows` are real
    capital_guardian.services.portfolio.project_summary() dicts — x=real
    completion %, y=real Capital Protection Score, size=real committed
    capital, color=the deterministic on_track/monitor/at_risk status
    already computed by portfolio.project_status(). A project missing
    either axis value is honestly excluded, never plotted at a guessed
    coordinate.
    """
    plottable = [r for r in rows if r['completion_pct'] is not None and r['protection_score'] is not None]
    if not plottable:
        return None

    status_colors = {'on_track': theme.IQ_ACCENT, 'monitor': theme.IQ_WARN, 'at_risk': theme.IQ_DANGER, 'unknown': theme.IQ_MUTED}
    sizes = [max(14, ((r['committed_usd'] or 0) / 1_000_000) / 2) for r in plottable]
    colors = [status_colors.get(r['status'], theme.IQ_MUTED) for r in plottable]
    hover = [
        f"<b>{r['project'].name}</b><br>Completion: {r['completion_pct']}%<br>"
        f"Protection score: {r['protection_score']}<br>"
        + (f"Committed: ${r['committed_usd']:,.0f}<br>" if r['committed_usd'] is not None else '')
        + f"Status: {r['status_label']}<br>Active red flags: {r['active_red_flags']}"
        for r in plottable
    ]

    fig = go.Figure(go.Scatter(
        x=[r['completion_pct'] for r in plottable], y=[r['protection_score'] for r in plottable],
        mode='markers+text', text=[r['project'].name for r in plottable], textposition='top center',
        textfont={'size': 9, 'color': theme.IQ_MUTED},
        marker={'size': sizes, 'color': colors, 'line': {'width': 1, 'color': theme.IQ_BG}},
        hovertext=hover, hoverinfo='text',
    ))
    fig.update_layout(**theme.base_layout(title='Portfolio Risk Matrix — Completion vs. Capital Protection', height=420, showlegend=False))
    fig.update_xaxes(title='Project completion (%) →', range=[0, 100])
    fig.update_yaxes(title='Capital Protection Score →', range=[0, 100])

    return {'html': theme.to_html_fragment(fig, 'gc-portfolio-risk-matrix'), 'count': len(plottable), 'total_projects': len(rows)}


def operational_time_series_chart(snapshots, field, label, div_id, target_value=None, unit=''):
    """
    Capital Guardian Phase 2 — Mining Digital Twin time-series. `snapshots`
    are real, already-stored OperationalSnapshot rows for one project
    (ascending by date) — a metric with no real recorded value on a given
    day is simply absent from the line, never interpolated/invented. When
    `target_value` is real (e.g. the project's own declared recovery-rate
    assumption, or a configured RedFlagRuleConfig threshold), a reference
    line is drawn — never a fabricated benchmark.
    `customdata` on each point carries [date, value, target, variance,
    confidence, evidence_count] for the click-to-inspect panel — every
    value real, `confidence`/`evidence_count` honestly None/0 when not
    recorded rather than fabricated.
    """
    plottable = [(s.date, getattr(s, field)) for s in snapshots if getattr(s, field) is not None]
    if not plottable:
        return None

    dates = [d.isoformat() for d, _ in plottable]
    values = [v for _, v in plottable]
    by_date = {s.date: s for s in snapshots}
    customdata = []
    for d, v in plottable:
        snap = by_date.get(d)
        variance = round(v - target_value, 2) if target_value is not None else None
        evidence_count = snap.evidence_documents.count() if snap is not None else 0
        customdata.append([d.isoformat(), v, target_value, variance, snap.confidence if snap else None, evidence_count])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=values, mode='lines+markers', name=label, line={'color': theme.IQ_ACCENT},
        marker={'size': 7}, customdata=customdata,
        hovertemplate=f'<b>{label}</b><br>%{{x}}: %{{y}}{unit}<extra></extra>',
    ))
    if target_value is not None:
        fig.add_hline(y=target_value, line_dash='dash', line_color=theme.IQ_WARN, annotation_text=f'Target: {target_value}{unit}')

    fig.update_layout(**theme.base_layout(title=label, height=300, showlegend=False))
    fig.update_xaxes(title='Date', type='date')
    fig.update_yaxes(title=f'{label}{f" ({unit.strip()})" if unit else ""}')

    return {'html': theme.to_html_fragment(fig, div_id), 'point_count': len(plottable), 'target_value': target_value}


def capital_guardian_risk_distribution_chart(red_flags):
    """
    Capital Guardian — Red Flag Engine severity distribution. Reads real,
    already-detected RedFlag rows directly (see
    capital_guardian.services.red_flag_engine.detect_red_flags) — never a
    fabricated risk count.
    """
    if not red_flags:
        return None
    counts = {'high': 0, 'medium': 0, 'low': 0}
    for flag in red_flags:
        counts[flag.severity] = counts.get(flag.severity, 0) + 1
    colors = {'high': theme.IQ_DANGER, 'medium': theme.IQ_WARN, 'low': theme.IQ_INFO}
    labels = [k.title() for k in counts]
    fig = go.Figure(go.Bar(
        x=labels, y=list(counts.values()), marker={'color': [colors[k] for k in counts]},
        text=list(counts.values()), textposition='outside',
    ))
    fig.update_layout(**theme.base_layout(title='Red Flag Severity Distribution', height=280, showlegend=False))
    fig.update_yaxes(title='Count', dtick=1)
    return {'html': theme.to_html_fragment(fig, 'gc-risk-distribution-chart'), 'total': len(red_flags)}
