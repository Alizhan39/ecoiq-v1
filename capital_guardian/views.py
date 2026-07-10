"""
capital_guardian/views.py — Capital Guardian: institutional investor
transparency and capital intelligence over a real gold_intelligence.GoldProject.

This is NOT a fundraising platform, investment marketplace, or payment
processor — every view here is read-only monitoring/governance/decision-
intelligence over real, already-stored data. Decision Studio and the AI
Agent Workbench are linked to directly (?q=/?ask=) — no second Q&A or
orchestration path is created here.

Phase 2 adds: portfolio_view (multi-project rollup), evidence_centre_view,
audit_history_view, and extends digital_twin_view with historical
time-series ranges — no second orchestration/scoring/evidence system.
"""
import datetime
from urllib.parse import quote

from django.shortcuts import get_object_or_404, render

from gold_intelligence.models import GoldProject

from capital_guardian.services import evidence as evidence_service
from capital_guardian.services import portfolio as portfolio_service
from capital_guardian.services import red_flag_engine
from capital_guardian.services import investor_dashboard as investor_dashboard_service

TIME_SERIES_RANGES = {
    '24h': ('Last 24 Hours', 1), '7d': ('Last 7 Days', 7), '30d': ('Last 30 Days', 30),
    '90d': ('Last 90 Days', 90), '1y': ('Last Year', 365),
}
TIME_SERIES_METRICS = [
    ('ore_mined_tonnes', 'Ore Mined (tonnes)', 't', None),
    ('plant_throughput_tph', 'Plant Throughput (tph)', ' tph', None),
    ('recovery_rate_pct', 'Recovery Rate', '%', 'recovery_rate'),
    ('dore_produced_kg', 'Doré Produced (kg)', ' kg', None),
    ('equipment_availability_pct', 'Equipment Availability', '%', 'equipment_availability'),
    ('energy_use_mwh', 'Energy Use (MWh)', ' MWh', None),
    ('water_recycled_pct', 'Water Recycled', '%', 'water_recycled'),
]

DECISION_INTELLIGENCE_QUESTIONS = [
    'Where has investor capital been deployed?',
    'Which payments have insufficient evidence?',
    'What percentage of deployed capital is connected to verified physical assets?',
    'Which equipment deliveries create the greatest schedule risk?',
    'Which upcoming milestones require additional capital?',
    'What capital is currently uninsured?',
    "What are the project's largest red flags?",
    'Is CAPEX currently within budget?',
    'Which supplier payments require investor approval?',
    'What could delay first gold production?',
]

# MINE → HAULAGE → CRUSHING → GRINDING → PROCESSING → RECOVERY → DORÉ PRODUCTION
PROCESS_STAGES = [
    {'key': 'mine', 'label': 'Mine', 'equipment_types': ['haul_truck', 'excavator']},
    {'key': 'haulage', 'label': 'Haulage', 'equipment_types': ['haul_truck', 'conveyor']},
    {'key': 'crushing', 'label': 'Crushing', 'equipment_types': ['crusher']},
    {'key': 'grinding', 'label': 'Grinding', 'equipment_types': ['mill']},
    {'key': 'processing', 'label': 'Processing', 'equipment_types': ['cil', 'heap_leach', 'flotation', 'autoclave', 'gravity']},
    {'key': 'recovery', 'label': 'Recovery', 'equipment_types': ['thickener', 'filter_press', 'electrowinning']},
    {'key': 'dore_production', 'label': 'Doré Production', 'equipment_types': ['smelting_furnace']},
]


def _decision_studio_links(project):
    return [
        {'question': q, 'href': f'/decision-studio/?q={quote(q + " — " + project.name)}'}
        for q in DECISION_INTELLIGENCE_QUESTIONS
    ]


def _project_or_404(slug):
    return get_object_or_404(GoldProject.objects.select_related('country'), slug=slug)


def directory(request):
    projects = GoldProject.objects.select_related('country').all()
    return render(request, 'capital_guardian/directory.html', {'projects': projects})


def portfolio_view(request):
    """Phase 2 — Multi-Project Investor Portfolio. Every project on the
    platform is included (not just capital_guardian-flagged ones): a
    GoldProject with no Capital Guardian data yet simply shows honest
    'Data source required' cells, matching the rest of the app's convention."""
    projects = list(GoldProject.objects.select_related('country').all())
    rows = portfolio_service.build_portfolio(projects)

    country = request.GET.get('country') or ''
    commodity = request.GET.get('commodity') or ''
    status = request.GET.get('status') or ''
    sort_key = request.GET.get('sort') or ''

    filtered_rows = portfolio_service.filter_rows(rows, country=country, commodity=commodity, status=status)
    if sort_key:
        filtered_rows = portfolio_service.sort_rows(filtered_rows, sort_key)

    totals = portfolio_service.portfolio_totals(rows)

    from plotly_visual_intelligence.services import charts

    return render(request, 'capital_guardian/portfolio.html', {
        'rows': filtered_rows, 'all_rows_count': len(rows), 'totals': totals,
        'countries': sorted({r['project'].country for r in rows if r['project'].country_id}, key=lambda c: c.name),
        'commodities': GoldProject.COMMODITY_CHOICES,
        'statuses': [(k, v) for k, v in portfolio_service.STATUS_LABELS.items() if k != 'unknown'],
        'selected_country': country, 'selected_commodity': commodity, 'selected_status': status, 'selected_sort': sort_key,
        'risk_matrix_chart': charts.portfolio_risk_matrix_chart(rows),
    })


def investor_dashboard(request, slug):
    project = _project_or_404(slug)
    context = investor_dashboard_service.build_dashboard_context(project)
    committed = context['capital_committed_usd']
    deployed = context['capital_deployed_usd']
    context['capital_remaining_usd'] = (
        round(committed - deployed, 2) if committed is not None and deployed is not None else None
    )
    context['project'] = project
    context['decision_studio_links'] = _decision_studio_links(project)[:4]

    from plotly_visual_intelligence.services import charts

    context['capital_deployment_chart'] = charts.capital_deployment_chart(committed, deployed, context['capital_remaining_usd'])
    # Reuses the exact same chart gold_intelligence's own Capital Tracker uses — not a second CAPEX chart.
    context['capex_chart'] = charts.capital_tracker_chart(context['capex_summary'])
    # Reuses the exact same Gantt-style chart gold_intelligence's own Mine Timeline uses.
    context['milestone_chart'] = charts.mine_timeline_chart(list(project.timeline_milestones.all()))
    context['completion_gauge'] = charts.capital_guardian_gauge_chart(
        context['completion_pct'], 'Project Completion', 'gc-completion-gauge',
    )
    context['protection_gauge'] = charts.capital_guardian_gauge_chart(
        context['capital_protection']['score'] if context['capital_protection']['available'] else None,
        'Capital Protection Score', 'gc-protection-gauge',
    )
    insurance_ratio = (
        min(100.0, context['insurance_coverage_usd'] / deployed * 100)
        if context['insurance_coverage_usd'] is not None and deployed else None
    )
    context['insurance_gauge'] = charts.capital_guardian_gauge_chart(
        insurance_ratio, 'Insurance Coverage (% of Deployed Capital)', 'gc-insurance-gauge',
    )
    context['risk_distribution_chart'] = charts.capital_guardian_risk_distribution_chart(context['active_red_flags'])

    return render(request, 'capital_guardian/investor_dashboard.html', context)


def capital_trace_view(request, slug):
    project = _project_or_404(slug)
    entries = list(project.capital_trace_entries.select_related('budget_category', 'related_equipment', 'related_milestone').all())
    return render(request, 'capital_guardian/capital_trace.html', {'project': project, 'entries': entries})


def governance_view(request, slug):
    project = _project_or_404(slug)
    governance = getattr(project, 'governance', None)
    controls = []
    if governance:
        controls = [
            ('Reserved Matters', governance.reserved_matters_active),
            ('Escrow Account', governance.escrow_account_active),
            ('Investor-First Waterfall', governance.investor_first_waterfall_active),
            ('Quarterly Audit', governance.quarterly_audit_active),
            ('Independent Technical Adviser', governance.independent_technical_adviser_active),
            ('Insurance Monitoring', governance.insurance_monitoring_active),
            ('Milestone-Based Capital Release', governance.milestone_based_capital_release_active),
        ]
    return render(request, 'capital_guardian/governance.html', {'project': project, 'governance': governance, 'controls': controls})


def equipment_insurance_view(request, slug):
    project = _project_or_404(slug)
    equipment = list(project.equipment_specs.all())
    return render(request, 'capital_guardian/equipment_insurance.html', {'project': project, 'equipment': equipment})


def digital_twin_view(request, slug):
    project = _project_or_404(slug)
    latest_snapshot = project.operational_snapshots.order_by('-date').first()

    equipment_by_type = {}
    for equipment in project.equipment_specs.all():
        equipment_by_type.setdefault(equipment.equipment_type, []).append(equipment)

    stages = []
    for stage in PROCESS_STAGES:
        stage_equipment = [e for t in stage['equipment_types'] for e in equipment_by_type.get(t, [])]
        capital_for_stage = sum(
            entry.amount_usd for e in stage_equipment for entry in e.capital_trace_entries.all()
        ) or None
        risks_for_stage = [f for e in stage_equipment for f in e.red_flags.filter(resolution_status='open')]
        stages.append({
            **stage, 'equipment': stage_equipment, 'capital_deployed_usd': capital_for_stage,
            'risks': risks_for_stage,
        })

    # --- Phase 2: historical time-series over real OperationalSnapshot rows.
    # OperationalSnapshot is a once-daily reading (see its model docstring),
    # so "24 Hours" honestly means "the latest recorded snapshot", not
    # invented intraday data — never presented as live telemetry.
    range_key = request.GET.get('range', '30d')
    if range_key not in TIME_SERIES_RANGES:
        range_key = '30d'
    range_label, range_days = TIME_SERIES_RANGES[range_key]
    since = datetime.date.today() - datetime.timedelta(days=range_days)
    history = list(project.operational_snapshots.filter(date__gte=since).order_by('date'))

    from capital_guardian.services.red_flag_engine import get_thresholds
    from plotly_visual_intelligence.services import charts

    time_series_charts = []
    for field, label, unit, rule_key in TIME_SERIES_METRICS:
        target_value = None
        if rule_key == 'recovery_rate' and project.recovery_rate_pct is not None:
            warning, _critical = get_thresholds(project, 'recovery_rate')
            target_value = project.recovery_rate_pct
        elif rule_key in ('equipment_availability', 'water_recycled'):
            warning, _critical = get_thresholds(project, rule_key)
            target_value = warning
        chart = charts.operational_time_series_chart(history, field, label, f'gc-ts-{field}', target_value=target_value, unit=unit)
        if chart is not None:
            time_series_charts.append(chart)

    return render(request, 'capital_guardian/digital_twin.html', {
        'project': project, 'snapshot': latest_snapshot, 'stages': stages,
        'range_key': range_key, 'range_label': range_label, 'ranges': TIME_SERIES_RANGES,
        'history_count': len(history), 'time_series_charts': time_series_charts,
    })


def milestone_control_view(request, slug):
    project = _project_or_404(slug)
    milestones = list(project.timeline_milestones.all())
    return render(request, 'capital_guardian/milestone_control.html', {'project': project, 'milestones': milestones})


def red_flag_view(request, slug):
    project = _project_or_404(slug)
    flags = red_flag_engine.detect_red_flags(project)
    all_flags = list(project.red_flags.all())
    return render(request, 'capital_guardian/red_flags.html', {'project': project, 'flags': all_flags, 'refreshed_count': len(flags)})


def decision_intelligence_view(request, slug):
    project = _project_or_404(slug)
    return render(request, 'capital_guardian/decision_intelligence.html', {
        'project': project, 'links': _decision_studio_links(project),
    })


def evidence_centre_view(request, slug):
    """Phase 2 — every real EvidenceMemory row attached to anything
    belonging to this project, with an honest verification-status
    breakdown. Never marks anything verified itself."""
    project = _project_or_404(slug)
    evidence_qs = evidence_service.evidence_for_project(project).select_related('reviewer')
    status_filter = request.GET.get('status') or ''
    if status_filter:
        evidence_qs = evidence_qs.filter(verification_status=status_filter)
    evidence_rows = list(evidence_qs)
    summary = evidence_service.verification_summary(evidence_service.evidence_for_project(project))

    rows = [{'evidence': e, 'related_label': evidence_service.related_object_label(e.source_reference)} for e in evidence_rows]

    from evidence_memory.models import EvidenceMemory

    return render(request, 'capital_guardian/evidence_centre.html', {
        'project': project, 'rows': rows, 'summary': summary,
        'status_choices': EvidenceMemory.VERIFICATION_STATUS_CHOICES,
        'selected_status': status_filter,
    })


def audit_history_view(request, slug):
    """Phase 2 — 'Audit History'/'Change History', not a claim of
    cryptographic immutability. Every row was written automatically by
    capital_guardian/signals.py when a real tracked field actually changed."""
    project = _project_or_404(slug)
    event_type_filter = request.GET.get('event_type') or ''
    entries = project.audit_log_entries.select_related('changed_by').all()
    if event_type_filter:
        entries = entries.filter(event_type=event_type_filter)
    from capital_guardian.models import AuditLogEntry
    return render(request, 'capital_guardian/audit_history.html', {
        'project': project, 'entries': list(entries), 'event_types': AuditLogEntry.EVENT_TYPE_CHOICES,
        'selected_event_type': event_type_filter,
    })
