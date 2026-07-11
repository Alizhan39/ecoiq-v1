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

Phase 3 adds: per-entry Capital Protection detail (invoice/contract/
insurance/inspection/supplier/approval-chain/audit-trail — never
photos/GPS, since no real capture of either exists), a per-equipment detail
page (with a deterministic remaining-useful-life estimate, never an ML
prediction), a project-independent Supplier Comparison page (synthetic,
heavily-disclaimed ratings — see models.SupplierProfile's docstring), a
Live Cameras page (honest 'no live feed connected' state), a Govern hub,
and an AI Project Director briefing (a narrative template over real data,
not a second AI system).
"""
import datetime
from urllib.parse import quote

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from gold_intelligence.models import GoldProject

from capital_guardian.services import ai_director as ai_director_service
from capital_guardian.services import equipment_health
from capital_guardian.services import evidence as evidence_service
from capital_guardian.services import portfolio as portfolio_service
from capital_guardian.services import red_flag_engine
from capital_guardian.services import supplier_comparison as supplier_comparison_service
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
    # Phase 3 — Live Digital Twin production extras.
    ('dore_inventory_kg', 'Doré Inventory (kg)', ' kg', None),
    ('truck_fleet_utilization_pct', 'Truck Fleet Utilization', '%', None),
    ('tailings_stored_tonnes', 'Tailings Stored (tonnes)', 't', None),
    ('water_stored_m3', 'Water Stored (m³)', ' m³', None),
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
    context['health_gauge'] = charts.capital_guardian_gauge_chart(
        context['project_health']['score'] if context['project_health']['available'] else None,
        'Project Health Score', 'gc-health-gauge',
    )

    return render(request, 'capital_guardian/investor_dashboard.html', context)


def capital_trace_view(request, slug):
    project = _project_or_404(slug)
    entries = list(project.capital_trace_entries.select_related('budget_category', 'related_equipment', 'related_milestone').all())
    return render(request, 'capital_guardian/capital_trace.html', {'project': project, 'entries': entries})


def capital_trace_entry_detail_view(request, slug, entry_id):
    """Phase 3 — 'clicking a payment' detail: Invoice/Contract (evidence
    documents), Insurance, Inspection (equipment.inspection_status),
    Supplier, Approval Chain, Audit Trail (real AuditLogEntry rows for this
    exact entry). Photos/GPS are honestly omitted — no real capture of
    either exists; never a stock photo or fabricated coordinate."""
    from capital_guardian.services import capital_trace as capital_trace_service

    project = _project_or_404(slug)
    entry = get_object_or_404(
        project.capital_trace_entries.select_related('budget_category', 'related_equipment', 'related_milestone'),
        pk=entry_id,
    )
    audit_trail = project.audit_log_entries.filter(source_reference=f'capital_guardian.CapitalTraceEntry:{entry.pk}')
    return render(request, 'capital_guardian/capital_trace_entry_detail.html', {
        'project': project, 'entry': entry,
        'chain': capital_trace_service.capital_protection_chain_for_entry(entry),
        'evidence_documents': list(entry.evidence_documents.all()),
        'audit_trail': list(audit_trail),
    })


def governance_view(request, slug):
    project = _project_or_404(slug)
    governance = getattr(project, 'governance', None)
    controls = []
    ownership_donut = None
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
        from plotly_visual_intelligence.services import charts
        ownership_donut = charts.ownership_donut_chart(governance.founder_holdco_pct, governance.investor_spv_pct)
    return render(request, 'capital_guardian/governance.html', {
        'project': project, 'governance': governance, 'controls': controls, 'ownership_donut': ownership_donut,
    })


def equipment_insurance_view(request, slug):
    project = _project_or_404(slug)
    equipment = list(project.equipment_specs.all())
    return render(request, 'capital_guardian/equipment_insurance.html', {'project': project, 'equipment': equipment})


def equipment_detail_view(request, slug, equipment_id):
    """Phase 3 — per-equipment deep-dive. Live telemetry (temperature/
    vibration/utilization/energy/carbon), live cameras and drone inspection
    are honestly shown as 'no live feed connected' — no fabricated sensor
    readings or stock imagery. The 'AI Prediction / Expected Failure Date'
    field is a deterministic remaining-useful-life estimate (see
    services/equipment_health.py), never a black-box ML prediction."""
    project = _project_or_404(slug)
    equipment = get_object_or_404(project.equipment_specs, pk=equipment_id)
    maintenance_history = project.audit_log_entries.filter(source_reference=f'gold_intelligence.EquipmentSpec:{equipment.pk}')
    return render(request, 'capital_guardian/equipment_detail.html', {
        'project': project, 'equipment': equipment,
        'rul': equipment_health.remaining_useful_life(equipment),
        'maintenance_recommendation': equipment_health.maintenance_recommendation(equipment),
        'maintenance_history': list(maintenance_history),
        'capital_trace_entries': list(equipment.capital_trace_entries.all()),
        'open_red_flags': list(equipment.red_flags.filter(resolution_status='open')),
    })


def supplier_comparison_view(request):
    """Phase 3 — project-independent Supplier Comparison. See
    models.SupplierProfile's docstring: illustrative_* ratings are SYNTHETIC,
    never a real assessment of the named company — the template carries a
    prominent disclaimer on every row."""
    from capital_guardian.models import SupplierProfile

    suppliers = list(SupplierProfile.objects.all())
    rows = [{'supplier': s, 'equipment_in_use': list(supplier_comparison_service.equipment_using_supplier(s.name))} for s in suppliers]
    return render(request, 'capital_guardian/supplier_comparison.html', {'rows': rows})


def live_cameras_view(request, slug):
    """Phase 3 — honest empty state. No real camera/drone/satellite feed
    exists yet; this is the UI shell a future integration would populate,
    never a fake video or stock photo presented as live."""
    project = _project_or_404(slug)
    zones = [
        'Open Pit', 'Crusher', 'Mill', 'Processing Plant', 'Gold Room', 'Warehouse',
        'Control Room', 'Drone View', 'Satellite View',
    ]
    return render(request, 'capital_guardian/live_cameras.html', {'project': project, 'zones': zones})


def govern_hub_view(request, slug):
    """Phase 3 — a hub linking to the real governance/evidence/audit pages
    that already exist, plus real rollups (insurance, approvals) computed
    here, plus honestly-stubbed sections (Legal/Compliance/ESG/Licences)
    for which no real data source is connected yet."""
    project = _project_or_404(slug)
    entries = list(project.capital_trace_entries.all())
    pending_investor_approvals = [e for e in entries if e.investor_approval_status == 'pending']
    uninsured_entries = [e for e in entries if e.insurance_status == 'uninsured']
    return render(request, 'capital_guardian/govern_hub.html', {
        'project': project,
        'governance': getattr(project, 'governance', None),
        'pending_investor_approvals': pending_investor_approvals,
        'uninsured_entries': uninsured_entries,
        'insurance_coverage_usd': project.insurance_coverage_usd,
        'insurance_expiry_date': project.insurance_expiry_date,
    })


def ai_director_view(request, slug):
    """Phase 3 — AI Project Director Morning Briefing. A deterministic
    narrative template over real data already computed elsewhere — never a
    second AI/LLM system. See services/ai_director.py."""
    project = _project_or_404(slug)
    return render(request, 'capital_guardian/ai_director.html', {
        'project': project, 'briefing': ai_director_service.build_morning_briefing(project),
        'decision_studio_links': _decision_studio_links(project)[:4],
    })


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

    from capital_guardian.forms import ProjectEvidenceIntakeForm

    return render(request, 'capital_guardian/evidence_centre.html', {
        'project': project, 'rows': rows, 'summary': summary,
        'status_choices': EvidenceMemory.VERIFICATION_STATUS_CHOICES,
        'selected_status': status_filter,
        # Vertical-slice PR 1 — manual evidence intake. The form is only
        # RENDERED for staff; the actual authorization check lives on
        # add_project_evidence below, never in the template.
        'intake_form': ProjectEvidenceIntakeForm() if request.user.is_staff else None,
        # Vertical-slice PR 2 — "Run Project Analysis" button, staff-only display.
        'can_run_analysis': request.user.is_staff,
    })


@staff_member_required(login_url='/login/')
def run_project_analysis(request, slug):
    """
    Vertical-slice PR 2 — staff-only, POST-only trigger for the real
    mizan.project.score_project() analysis over this project's real
    evidence. Nothing is persisted: this is a deterministic, real-time
    computation over already-stored data, not a live AI call, so re-running
    it (e.g. on refresh) is harmless and never creates duplicate records.
    The project is independently re-resolved from the URL slug.
    """
    project = _project_or_404(slug)
    if request.method != 'POST':
        return redirect('capital_guardian:evidence_centre', slug=slug)

    from capital_guardian.services.project_analysis import analyse_project
    from capital_guardian.services.resource_purpose_review import review_resource_purpose

    try:
        result = analyse_project(project)
        review = review_resource_purpose(project, result)
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            'Unexpected failure running project analysis for GoldProject %s', project.pk,
        )
        messages.error(request, 'Something went wrong running the project analysis. No result was produced.')
        return redirect('capital_guardian:evidence_centre', slug=slug)

    return render(request, 'capital_guardian/project_analysis_result.html', {
        'project': project, 'result': result, 'review': review,
    })


def _build_value_loss_confirmation_form(project, review, data=None):
    from capital_guardian.forms import ValueLossConfirmationForm

    initial = {}
    if review.has_reviewed_profile:
        initial['title'] = f'Avoidable {review.primary_resource.lower()}-based {review.current_use.lower()}' if review.primary_resource and review.current_use else ''
        initial['loss_type'] = 'heat_loss'
    return ValueLossConfirmationForm(data, initial=initial)


@staff_member_required(login_url='/login/')
def create_value_loss_confirm(request, slug):
    """
    Vertical-slice PR 3 — GET-only, read-only confirmation screen. Re-derives
    the project analysis and resource-purpose review from scratch (never
    trusts anything carried over from the analysis page) so the eligibility
    check (a genuine misuse/value-loss condition) is always current.
    """
    project = _project_or_404(slug)

    from capital_guardian.services.project_analysis import analyse_project
    from capital_guardian.services.resource_purpose_review import review_resource_purpose

    analysis_result = analyse_project(project)
    review = review_resource_purpose(project, analysis_result)

    form = _build_value_loss_confirmation_form(project, review)

    return render(request, 'capital_guardian/create_value_loss_confirm.html', {
        'project': project, 'review': review, 'form': form,
    })


@staff_member_required(login_url='/login/')
def create_value_loss_execute(request, slug):
    """
    Vertical-slice PR 3 — POST-only. Independently re-derives the project,
    analysis, and resource-purpose review (never trusts the confirmation
    page's hidden state for eligibility), refuses to create anything if no
    genuine misuse/value-loss condition is indicated, and otherwise creates
    exactly one real OperationalLoss via the existing, unmodified
    loss_intake.create_operational_loss() — no loss-creation logic is
    duplicated here.
    """
    project = _project_or_404(slug)
    if request.method != 'POST':
        return redirect('capital_guardian:evidence_centre', slug=slug)

    from capital_guardian.services.project_analysis import analyse_project
    from capital_guardian.services.resource_purpose_review import review_resource_purpose
    from waste_to_value_capital_allocation_engine.models import LossEvidence
    from waste_to_value_capital_allocation_engine.services.loss_intake import create_operational_loss

    try:
        analysis_result = analyse_project(project)
        review = review_resource_purpose(project, analysis_result)
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            'Unexpected failure re-deriving analysis/review for GoldProject %s', project.pk,
        )
        messages.error(request, 'Something went wrong creating the value-loss record. No record was created.')
        return redirect('capital_guardian:evidence_centre', slug=slug)

    if not review.misuse_or_value_loss_condition_exists:
        messages.error(
            request,
            'No reviewed resource-misuse/value-loss condition is currently indicated for this project — '
            'nothing was created.',
        )
        return redirect('capital_guardian:evidence_centre', slug=slug)

    form = _build_value_loss_confirmation_form(project, review, data=request.POST)
    if not form.is_valid():
        return render(request, 'capital_guardian/create_value_loss_confirm.html', {
            'project': project, 'review': review, 'form': form,
        }, status=400)

    data = form.cleaned_data

    # evidence_quality/confidence are never form-editable — derived
    # server-side from the real review_confidence so a human can't dial up
    # apparent evidence quality beyond what verification status supports.
    quality_by_confidence = {'low': 'weak', 'medium': 'medium', 'high': 'strong'}
    evidence_quality = quality_by_confidence.get(review.review_confidence, 'weak')
    confidence = {'strong': 90, 'medium': 60, 'weak': 30, 'missing': 10}[evidence_quality]

    classification_label = dict(form.fields['classification'].choices)[data['classification']]
    description_parts = [
        f'Human-reviewed value loss created from Project Analysis + Resource Purpose Review for '
        f'"{project.name}".',
        f'Classification: {classification_label}.',
        f'Reviewed by: {request.user.get_username()} at {timezone.now():%Y-%m-%d %H:%M} UTC.',
        'This record is human-confirmed, not automatically verified.',
    ]
    if review.recommended_next_action:
        description_parts.append(f'Review note: {review.recommended_next_action}')

    try:
        loss = create_operational_loss(
            project=project.name,
            country=project.country.name if project.country_id else '',
            location=project.region or '',
            sector='heating / energy transition',
            loss_type=data['loss_type'],
            title=data['title'],
            description='\n'.join(description_parts),
            quantity_lost=data.get('quantity_lost'),
            unit=data.get('unit') or '',
            financial_loss_amount=data['financial_loss_amount'],
            evidence_quality=evidence_quality,
            confidence=confidence,
            avoidability_score=data['avoidability_score'],
            urgency_score=data['urgency_score'],
            status='detected',
        )
        for ref in review.evidence_used:
            LossEvidence.objects.create(
                operational_loss=loss, evidence_reference=ref, evidence_type='project_evidence',
                evidence_quality=evidence_quality, confidence=confidence,
            )
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            'Unexpected failure creating OperationalLoss for GoldProject %s', project.pk,
        )
        messages.error(request, 'Something went wrong creating the value-loss record. No record was created.')
        return redirect('capital_guardian:evidence_centre', slug=slug)

    messages.success(
        request,
        f'Human-reviewed value loss "{loss.title}" created (evidence quality: {loss.get_evidence_quality_display()}).',
    )
    return redirect('capital_guardian:evidence_centre', slug=slug)


@staff_member_required(login_url='/login/')
def add_project_evidence(request, slug):
    """
    Vertical-slice PR 1 — staff-only manual/document-assisted evidence
    intake for one project. POST only; a GET here just lands on the
    Evidence Centre (where the form lives) without creating anything.
    The project is independently re-resolved from the URL slug — nothing
    about identity or authorization is trusted from the submitted form.
    """
    project = _project_or_404(slug)
    if request.method != 'POST':
        return redirect('capital_guardian:evidence_centre', slug=slug)

    from capital_guardian.forms import ProjectEvidenceIntakeForm
    from evidence_memory.services.memory import create_memory_from_manual_project_evidence

    form = ProjectEvidenceIntakeForm(request.POST)
    if not form.is_valid():
        evidence_qs = evidence_service.evidence_for_project(project).select_related('reviewer')
        rows = [{'evidence': e, 'related_label': evidence_service.related_object_label(e.source_reference)} for e in evidence_qs]
        from evidence_memory.models import EvidenceMemory
        return render(request, 'capital_guardian/evidence_centre.html', {
            'project': project, 'rows': rows,
            'summary': evidence_service.verification_summary(evidence_service.evidence_for_project(project)),
            'status_choices': EvidenceMemory.VERIFICATION_STATUS_CHOICES,
            'selected_status': '',
            'intake_form': form,
        }, status=400)

    data = form.cleaned_data
    try:
        memory = create_memory_from_manual_project_evidence(
            project,
            title=data['title'],
            text=data['text'],
            source_url=data['source_url'],
            source_type=data['source_type'],
            document_category=data['document_category'],
            verification_status=data['verification_status'],
            review_tier=data['review_tier'],
            is_demo=(data['classification'] == 'illustrative'),
            reviewer=request.user if data['review_tier'] in ('human_reviewed', 'independently_verified') else None,
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            'Unexpected failure adding manual evidence for GoldProject %s', project.pk,
        )
        messages.error(request, 'Something went wrong adding this evidence. No record was created.')
        return redirect('capital_guardian:evidence_centre', slug=slug)

    messages.success(
        request,
        f'Evidence added ({memory.get_verification_status_display()}'
        f'{", illustrative/demo" if memory.is_demo else ""}).',
    )
    return redirect('capital_guardian:evidence_centre', slug=slug)


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
