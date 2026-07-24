"""
good_agents/views.py — minimal read views over the Good Agents pipeline.
No dead ends: every opportunity links through to its real activations,
red-team review, opportunity-cost assessment, actions, capital decision and
impact receipt, all of which are real rows created by the pipeline in
services/pipeline.py — nothing here is a static mockup.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from good_agents.models import (
    ActionPathway, AvailableResource, ConnectionCandidate, FundingAction, GoodDiscoveryRun, GoodOpportunity,
    Need, OutreachDraft, ProjectCandidate, SignalProvider,
)
from good_agents.services import (
    action_gate, action_pathway as action_pathway_service, connection_action, morning_brief as morning_brief_service,
    outreach, project_bridge,
)


def opportunity_list(request):
    opportunities = GoodOpportunity.objects.select_related('project', 'geography').order_by('-created_at')
    status = request.GET.get('status', '')
    if status:
        opportunities = opportunities.filter(status=status)
    return render(request, 'good_agents/opportunity_list.html', {
        'opportunities': opportunities,
        'status_choices': GoodOpportunity.STATUS_CHOICES,
        'active_status': status,
    })


def opportunity_detail(request, pk):
    opportunity = get_object_or_404(
        GoodOpportunity.objects.select_related('project', 'geography', 'operational_loss', 'discovery_run'),
        pk=pk,
    )
    activations = opportunity.agent_activations.select_related('agent').all()
    actions = opportunity.actions.all()
    cost_assessment = getattr(opportunity, 'opportunity_cost_assessment', None)
    red_team_review = getattr(opportunity, 'red_team_review', None)
    impact_receipt = getattr(opportunity, 'impact_receipt', None)
    decisions = []
    if opportunity.operational_loss_id:
        decisions = [
            d for loss_option in opportunity.operational_loss.interventions.all()
            for d in loss_option.allocation_decisions.all()
        ]

    # PR5 — governed action network context.
    gate = action_gate.get_or_create_gate(opportunity)
    gate_transitions = gate.transitions.select_related('actor').all()
    state_labels = dict(gate.STATE_CHOICES)
    allowed_next_states = sorted(gate.ALLOWED_TRANSITIONS.get(gate.current_state, set()))
    allowed_next_state_choices = [(state, state_labels[state]) for state in allowed_next_states]
    pathways = opportunity.action_pathways.select_related('owner').prefetch_related('outreach_drafts', 'responsible_parties')
    responsible_parties = opportunity.responsible_parties.all()
    project_candidate = getattr(opportunity, 'project_candidate', None)
    timeline_events = opportunity.timeline_events.select_related('actor').all()

    return render(request, 'good_agents/opportunity_detail.html', {
        'opportunity': opportunity,
        'activations': activations,
        'actions': actions,
        'cost_assessment': cost_assessment,
        'red_team_review': red_team_review,
        'impact_receipt': impact_receipt,
        'decisions': decisions,
        'gate': gate,
        'gate_transitions': gate_transitions,
        'allowed_next_states': allowed_next_states,
        'allowed_next_state_choices': allowed_next_state_choices,
        'gate_state_labels': state_labels,
        'pathways': pathways,
        'pathway_type_choices': ActionPathway.PATHWAY_TYPE_CHOICES,
        'responsible_parties': responsible_parties,
        'project_candidate': project_candidate,
        'timeline_events': timeline_events,
    })


@staff_member_required(login_url='/login/')
def gate_transition(request, pk):
    """Staff-only, POST-only — the only way an ActionGate's state can change. Never silent, always logged."""
    opportunity = get_object_or_404(GoodOpportunity, pk=pk)
    if request.method == 'POST':
        new_state = request.POST.get('new_state', '')
        reason = request.POST.get('reason', '')
        try:
            action_gate.transition(opportunity, new_state, actor=request.user, reason=reason)
        except action_gate.IllegalTransitionError as exc:
            from django.contrib import messages
            messages.error(request, str(exc))
    return redirect('good_agents:opportunity_detail', pk=pk)


@staff_member_required(login_url='/login/')
def pathway_create(request, pk):
    """Staff-only, POST-only. Requires the opportunity's ActionGate to already be in an approved state."""
    opportunity = get_object_or_404(GoodOpportunity, pk=pk)
    if request.method == 'POST':
        try:
            action_pathway_service.create_pathway(
                opportunity, request.POST.get('pathway_type', 'other'),
                rationale=request.POST.get('rationale', ''), owner=request.user, actor=request.user,
            )
        except action_pathway_service.PathwayNotAllowedError as exc:
            from django.contrib import messages
            messages.error(request, str(exc))
    return redirect('good_agents:opportunity_detail', pk=pk)


@staff_member_required(login_url='/login/')
def outreach_approve(request, draft_pk):
    draft = get_object_or_404(OutreachDraft, pk=draft_pk)
    if request.method == 'POST':
        outreach.approve(draft, actor=request.user)
    return redirect('good_agents:opportunity_detail', pk=draft.action_pathway.opportunity_id)


@staff_member_required(login_url='/login/')
def outreach_send(request, draft_pk):
    """
    Staff-only, POST-only. Real send via the existing configured
    EMAIL_BACKEND — refuses unless the draft is already 'approved' and has
    a real, email-shaped contact channel (see services/outreach.py).
    """
    draft = get_object_or_404(OutreachDraft, pk=draft_pk)
    if request.method == 'POST':
        from django.contrib import messages
        try:
            outreach.send_outreach(draft, actor=request.user)
        except (outreach.OutreachNotApprovedError, outreach.NoContactChannelError) as exc:
            messages.error(request, str(exc))
    return redirect('good_agents:opportunity_detail', pk=draft.action_pathway.opportunity_id)


@staff_member_required(login_url='/login/')
def connection_approve(request, candidate_pk):
    candidate = get_object_or_404(ConnectionCandidate, pk=candidate_pk)
    if request.method == 'POST':
        connection_action.approve_for_introduction(candidate, actor=request.user)
    opportunity_id = candidate.resource_match.need.opportunity_id
    return redirect('good_agents:opportunity_detail', pk=opportunity_id) if opportunity_id else redirect('good_agents:opportunity_list')


@staff_member_required(login_url='/login/')
def project_candidate_propose(request, pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=pk)
    if request.method == 'POST':
        project_bridge.propose_candidate(opportunity, rationale=request.POST.get('rationale', ''))
    return redirect('good_agents:opportunity_detail', pk=pk)


@staff_member_required(login_url='/login/')
def project_candidate_approve(request, candidate_pk):
    candidate = get_object_or_404(ProjectCandidate, pk=candidate_pk)
    if request.method == 'POST':
        project_bridge.approve_candidate(candidate, actor=request.user)
    return redirect('good_agents:opportunity_detail', pk=candidate.opportunity_id)


@staff_member_required(login_url='/login/')
def project_candidate_create_confirm(request, candidate_pk):
    """GET-only, read-only confirmation screen — mirrors capital_guardian's confirm/execute pattern."""
    candidate = get_object_or_404(ProjectCandidate, pk=candidate_pk)
    return render(request, 'good_agents/project_candidate_create_confirm.html', {'candidate': candidate})


@staff_member_required(login_url='/login/')
def project_candidate_create_execute(request, candidate_pk):
    """POST-only. Creates the one real GoldProject for this candidate — is_demo must be explicit, never assumed."""
    candidate = get_object_or_404(ProjectCandidate, pk=candidate_pk)
    if request.method == 'POST':
        from django.contrib import messages
        try:
            project_bridge.create_project_from_candidate(
                candidate,
                slug=request.POST.get('slug', ''), name=request.POST.get('name', ''),
                is_demo=(request.POST.get('is_demo') == 'true'),
                region=request.POST.get('region', ''), description=request.POST.get('description', ''),
            )
        except project_bridge.ProjectCandidateNotApprovedError as exc:
            messages.error(request, str(exc))
    return redirect('good_agents:opportunity_detail', pk=candidate.opportunity_id)


def morning_brief(request):
    """PR2 Phase 13 + PR3/PR4 Phase 16-18 — assembled entirely from stored run/opportunity data, never fabricated numbers."""
    latest_run = GoodDiscoveryRun.objects.filter(status='completed').order_by('-created_at').first()
    top_opportunities = []
    awaiting_review = []
    top_3_actions = []
    observatory_summary = None
    provider_health = list(SignalProvider.objects.all())
    if latest_run is not None:
        top_opportunities = list(
            latest_run.opportunities.order_by('-urgency', '-confidence')[:5]
        )
        awaiting_review = list(
            GoodOpportunity.objects.filter(status__in=['potential', 'qualified']).order_by('-urgency')[:10]
        )
        top_3_actions = morning_brief_service.top_3_actions(list(latest_run.opportunities.all()))
        observatory_summary = morning_brief_service.build_brief(latest_run).get('observatory_summary')
    return render(request, 'good_agents/morning_brief.html', {
        'latest_run': latest_run,
        'top_opportunities': top_opportunities,
        'awaiting_review': awaiting_review,
        'observatory_summary': observatory_summary,
        'provider_health': provider_health,
        'top_3_actions': top_3_actions,
    })


@staff_member_required(login_url='/login/')
def impact_action_centre(request):
    """
    PR5 Phase 15 — staff-facing "what good can EcoIQ help move forward
    today?" dashboard. Every section is a real, live query — no static
    mockup sections.
    """
    new_awaiting_review = GoodOpportunity.objects.filter(
        action_gate__current_state__in=['discovered', 'needs_review'],
    ).order_by('-urgency')[:15]
    approved_actions = ActionPathway.objects.filter(status__in=['open', 'in_progress']).select_related('opportunity', 'owner')[:15]
    zero_capital_actions = ActionPathway.objects.filter(capital_required='no', status__in=['open', 'in_progress']).select_related('opportunity')[:15]
    connections = ConnectionCandidate.objects.exclude(status__in=['not_suitable', 'declined', 'expired']).select_related('resource_match__need', 'resource_match__resource')[:15]
    funding_candidates = FundingAction.objects.exclude(status__in=['rejected', 'expired']).select_related('funding_match__opportunity')[:15]
    project_candidates = ProjectCandidate.objects.filter(status__in=['proposed', 'approved']).select_related('opportunity')[:15]
    outreach_awaiting_approval = OutreachDraft.objects.filter(status='ready_for_review').select_related('action_pathway__opportunity')[:15]
    active_projects = ProjectCandidate.objects.filter(status='created').select_related('created_project', 'opportunity')[:15]
    outcome_verification_pending = GoodOpportunity.objects.filter(
        project_candidate__status='created', status__in=['approved', 'in_progress'],
    ).select_related('project_candidate')[:15]
    recent_verified_impact = GoodOpportunity.objects.filter(status='verified').order_by('-updated_at')[:10]

    return render(request, 'good_agents/impact_action_centre.html', {
        'new_awaiting_review': new_awaiting_review,
        'approved_actions': approved_actions,
        'zero_capital_actions': zero_capital_actions,
        'connections': connections,
        'funding_candidates': funding_candidates,
        'project_candidates': project_candidates,
        'outreach_awaiting_approval': outreach_awaiting_approval,
        'active_projects': active_projects,
        'outcome_verification_pending': outcome_verification_pending,
        'recent_verified_impact': recent_verified_impact,
    })


def good_map_api(request):
    """
    PR3 Phase 21 — backend/data support for a future /good/map. Read-only
    JSON; the map UI itself is explicitly out of scope for this PR. Never
    exposes precise coordinates or individual identifiers — only the
    region-level fields already on each model.
    """
    theme = request.GET.get('theme', '')
    status = request.GET.get('status', '')
    zero_capital = request.GET.get('zero_capital', '')
    min_confidence = request.GET.get('min_confidence', '')

    opportunities = GoodOpportunity.objects.select_related('geography')
    if theme:
        opportunities = opportunities.filter(theme=theme)
    if status:
        opportunities = opportunities.filter(status=status)
    if zero_capital:
        opportunities = opportunities.filter(zero_capital_possible=(zero_capital == 'true'))
    if min_confidence:
        opportunities = opportunities.filter(confidence__gte=float(min_confidence))

    needs = Need.objects.select_related('geography').filter(status='open')
    resources = AvailableResource.objects.select_related('geography').filter(status='active')

    return JsonResponse({
        'opportunities': [
            {
                'id': o.pk, 'title': o.title, 'theme': o.theme, 'status': o.status,
                'region': o.region, 'country': o.geography.name if o.geography_id else '',
                'urgency': o.urgency, 'confidence': o.confidence,
                'zero_capital_possible': o.zero_capital_possible, 'capital_required_usd': o.capital_required_usd,
            }
            for o in opportunities[:200]
        ],
        'needs': [
            {
                'id': n.pk, 'title': n.title, 'need_type': n.need_type, 'status': n.status,
                'region': n.region, 'country': n.geography.name if n.geography_id else '', 'urgency': n.urgency,
            }
            for n in needs[:200]
        ],
        'resources': [
            {
                'id': r.pk, 'title': r.title, 'resource_type': r.resource_type, 'availability': r.availability,
                'region': r.region, 'country': r.geography.name if r.geography_id else '', 'confidence': r.confidence,
            }
            for r in resources[:200]
        ],
    })


def observatory_health_api(request):
    """PR3 Phase 31 — operational visibility over SignalProvider health. No silent ingestion failures."""
    providers = SignalProvider.objects.all()
    return JsonResponse({
        'providers': [
            {
                'slug': p.slug, 'name': p.name, 'status': p.status, 'trust_tier': p.trust_tier,
                'last_refresh_at': p.last_refresh_at.isoformat() if p.last_refresh_at else None,
                'last_failure_reason': p.last_failure_reason, 'is_stale': p.is_stale(),
            }
            for p in providers
        ],
        'active_count': providers.filter(status='active').count(),
        'failed_count': providers.filter(status='failed').count(),
        'stale_count': sum(1 for p in providers if p.is_stale()),
    })
