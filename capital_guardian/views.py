"""
capital_guardian/views.py — Capital Guardian: institutional investor
transparency and capital intelligence over a real gold_intelligence.GoldProject.

This is NOT a fundraising platform, investment marketplace, or payment
processor — every view here is read-only monitoring/governance/decision-
intelligence over real, already-stored data. Decision Studio and the AI
Agent Workbench are linked to directly (?q=/?ask=) — no second Q&A or
orchestration path is created here.
"""
from urllib.parse import quote

from django.shortcuts import get_object_or_404, render

from gold_intelligence.models import GoldProject

from capital_guardian.services import red_flag_engine
from capital_guardian.services import investor_dashboard as investor_dashboard_service

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

    return render(request, 'capital_guardian/digital_twin.html', {
        'project': project, 'snapshot': latest_snapshot, 'stages': stages,
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
