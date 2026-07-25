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
from django.utils import timezone

from good_agents.models import (
    ActionContact, ActionPathway, AvailableResource, ConnectionCandidate, FundingAction, GoodDiscoveryRun,
    GoodOpportunity, Need, OutreachDraft, ProjectCandidate, ResponsibleParty, SignalProvider, WorldSignal,
)
from good_agents.services import (
    action_gate, action_pathway as action_pathway_service, connection_action, mission_control,
    morning_brief as morning_brief_service, outreach, pilot_launchpad, project_bridge,
    responsible_party as responsible_party_service,
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
        observatory_summary = morning_brief_service.observatory_summary_for_run(latest_run)
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

    # PR11 Phase 15 — Human Command Centre queues. Scoped to a bounded,
    # active real-opportunity set (not every historical row) since each
    # one recomputes blockers()/next_best_action() live.
    active_opportunities = GoodOpportunity.objects.filter(
        status__in=['potential', 'qualified', 'approved', 'in_progress'],
    ).select_related('action_gate', 'project_candidate').order_by('-urgency')[:40]
    command_centre_queues = pilot_launchpad.command_centre_queues(active_opportunities)

    # PR12 Phase 22 — outreach readiness queues, over the same real
    # excludes-controlled-test candidate set the Candidate Review page uses.
    from outreach_readiness.services.queues import command_centre_queues as outreach_command_centre_queues
    outreach_readiness_queues = outreach_command_centre_queues(
        GoodOpportunity.objects.exclude(title__startswith='[CONTROLLED TEST]').order_by('-urgency')[:40],
    )

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
        'command_centre_queues': command_centre_queues,
        'outreach_readiness_queues': outreach_readiness_queues,
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


def _pick_featured_opportunity(mission, requested_pk=None):
    """
    Picks the opportunity Mission Control's truth chain / demo story
    features by default: an explicit `?opportunity=<pk>` wins; otherwise
    the one that has genuinely progressed furthest along the real
    pipeline (never a fabricated "best" score) — a project candidate
    beats a pathway beats a reviewed gate beats "just discovered, highest
    urgency".
    """
    runs = mission.runs.all() if mission else GoodDiscoveryRun.objects.none()
    opportunities = GoodOpportunity.objects.filter(discovery_run__in=runs)
    if requested_pk:
        found = opportunities.filter(pk=requested_pk).first()
        if found:
            return found
    for candidate_qs in (
        opportunities.filter(project_candidate__isnull=False),
        opportunities.filter(action_pathways__isnull=False),
        opportunities.exclude(action_gate__current_state='discovered').filter(action_gate__isnull=False),
    ):
        featured = candidate_qs.order_by('-updated_at').first()
        if featured:
            return featured
    return opportunities.order_by('-urgency', '-created_at').first()


@staff_member_required(login_url='/login/')
def mission_control_view(request):
    """
    PR6 — Global Impact Mission Control, the flagship operating surface.
    Every section is a live read over models/services already built in
    PR2-5; nothing here recomputes a discovery/agent/project/MRV decision
    — see good_agents/services/mission_control.py's own module docstring.
    """
    mission = mission_control.get_flagship_mission()
    opportunity = _pick_featured_opportunity(mission, request.GET.get('opportunity'))

    runs = mission.runs.all() if mission else GoodDiscoveryRun.objects.none()
    mission_opportunities = GoodOpportunity.objects.filter(discovery_run__in=runs)
    latest_run = mission_control.latest_run_for_mission(mission)

    context = {
        'mission': mission,
        'mission_status': mission_control.mission_status(mission),
        'signal_funnel': mission_control.signal_funnel(mission),
        'noise_sample': mission_control.noise_sample(),
        'attention_economy': mission_control.attention_economy(mission),
        'qualified_opportunities': mission_opportunities.filter(status='qualified').order_by('-urgency')[:15],
        'awaiting_review': mission_opportunities.filter(
            action_gate__current_state__in=['discovered', 'needs_review'],
        ).order_by('-urgency')[:15],
        'top_3_actions': morning_brief_service.top_3_actions(list(mission_opportunities)),
        'zero_capital_lane': mission_control.zero_capital_lane(mission),
        'resource_matches': mission_control.resource_matches_lane(mission)[:15],
        'funding_matches': mission_control.funding_matches_lane(mission)[:15],
        'responsible_party_lane': mission_control.responsible_party_lane(mission),
        'outreach_connection_truth': mission_control.outreach_connection_truth(mission),
        'project_candidates': ProjectCandidate.objects.filter(opportunity__in=mission_opportunities).select_related('opportunity', 'created_project'),
        'active_projects': ProjectCandidate.objects.filter(opportunity__in=mission_opportunities, status='created').select_related('created_project'),
        'verified_impact': mission_control.verified_impact_list(mission),
        'impact_receipts': mission_control.impact_receipts_list(mission),
        'mission_health': mission_control.mission_health(),
        'actionable_discovery_summary': mission_control.actionable_discovery_summary(),
        'action_preparation_summary_counts': mission_control.action_preparation_summary_counts(),
        'mission_comparison': mission_control.mission_comparison(),
        'geographic_opportunities': mission_control.geographic_opportunity_list(mission),
        'observatory_summary': morning_brief_service.observatory_summary_for_run(latest_run) if latest_run else None,
        'featured_opportunity': opportunity,
        'truth_chain': mission_control.truth_chain(opportunity) if opportunity else None,
        'agent_transparency': mission_control.agent_transparency(opportunity) if opportunity else None,
        'demo_story': mission_control.demo_story(opportunity) if opportunity else None,
        'project_bridge_chain': mission_control.project_bridge_chain(opportunity) if opportunity else None,
        'execution_mrv': (
            mission_control.execution_mrv_for_project(opportunity.project_candidate.created_project)
            if opportunity and getattr(opportunity, 'project_candidate', None) and opportunity.project_candidate.created_project_id
            else None
        ),
        'impact_velocity': mission_control.impact_velocity(opportunity) if opportunity else None,
        'evidence_memory_records': (
            mission_control.evidence_memory_for_receipt(getattr(opportunity, 'impact_receipt', None))
            if opportunity else []
        ),
        'partner_participation_summary': mission_control.partner_participation_summary(opportunity) if opportunity else None,
        'outreach_readiness_summary': pilot_launchpad.outreach_readiness_summary(opportunity) if opportunity else None,
    }
    return render(request, 'good_agents/mission_control.html', context)


@staff_member_required(login_url='/login/')
def pilot_launchpad_redirect(request):
    """
    PR11 Phase 2 — deterministic flagship pilot selection. Never redirects
    to a fabricated "best" opportunity; if nothing currently clears the
    minimum bar, says so plainly rather than picking an arbitrary one.
    """
    from django.contrib import messages
    opportunity = pilot_launchpad.select_flagship_pilot()
    if opportunity is None:
        messages.info(request, 'NOT_READY_FOR_PILOT — no current opportunity meets the minimum evidence + review criteria.')
        return redirect('good_agents:opportunity_list')
    return redirect('good_agents:pilot_launchpad', pk=opportunity.pk)


@staff_member_required(login_url='/login/')
def pilot_launchpad_view(request, pk):
    """
    PR11 Phase 4 — the one flagship operational screen: truth chain,
    readiness scorecard, 114-principle relevance, Better Way, Capability
    Graph matches, contact/outreach state, blockers, next best action,
    capital/MRV snapshot, collaboration handoff. Every section is a pure
    read over PR2-10 models/services — nothing here recomputes an
    upstream decision.
    """
    opportunity = get_object_or_404(
        GoodOpportunity.objects.select_related('project', 'geography', 'discovery_run'), pk=pk,
    )
    project_candidate = getattr(opportunity, 'project_candidate', None)
    context = {
        'opportunity': opportunity,
        'criteria': pilot_launchpad.flagship_pilot_criteria(opportunity),
        'readiness_scorecard': pilot_launchpad.readiness_scorecard(opportunity),
        'truth_chain': pilot_launchpad.truth_chain_with_provenance(opportunity),
        'principle_relevance': pilot_launchpad.principle_relevance(opportunity),
        'better_way_options': pilot_launchpad.better_way_options(opportunity),
        'capability_graph_matches': pilot_launchpad.capability_graph_matches(opportunity),
        'contact_route_state': pilot_launchpad.contact_route_state(opportunity),
        'outreach_pack': pilot_launchpad.outreach_pack(opportunity),
        'blockers': pilot_launchpad.blockers(opportunity),
        'next_best_action': pilot_launchpad.next_best_action(opportunity),
        'capital_snapshot': pilot_launchpad.capital_snapshot(opportunity),
        'mrv_plan': pilot_launchpad.mrv_plan(opportunity),
        'partner_participation_summary': mission_control.partner_participation_summary(opportunity),
        'demo_story': mission_control.demo_story(opportunity),
        'project_candidate': project_candidate,
        'outreach_readiness_summary': pilot_launchpad.outreach_readiness_summary(opportunity),
        'actionability_summary': pilot_launchpad.actionability_summary(opportunity),
        'action_preparation_summary': pilot_launchpad.action_preparation_summary(opportunity),
    }
    return render(request, 'good_agents/pilot_launchpad.html', context)


@staff_member_required(login_url='/login/')
def pilot_dossier_view(request, pk):
    """PR11 Phase 25 — exportable read-only dossier. Missing stays Missing, never filled with invented prose."""
    opportunity = get_object_or_404(GoodOpportunity, pk=pk)
    return render(request, 'good_agents/pilot_dossier.html', {'dossier': pilot_launchpad.build_dossier(opportunity)})


def pilot_launchpad_public_view(request, pk):
    """
    PR11 Phase 24 — public-safe read view. Deliberately narrow: problem,
    public evidence references, principle relevance, Better Way options
    (rationale only, no internal notes), current honest status, and
    verified impact if it exists. Never exposes organisation contact
    details, outreach content, internal notes, or partner-private data —
    those live only in the staff-only pilot_launchpad_view above.
    """
    opportunity = get_object_or_404(GoodOpportunity, pk=pk)
    return render(request, 'good_agents/pilot_launchpad_public.html', {
        'opportunity': opportunity,
        'truth_chain': pilot_launchpad.truth_chain_with_provenance(opportunity),
        'principle_relevance': pilot_launchpad.principle_relevance(opportunity),
        'better_way_options': [
            {'pathway_type': o['pathway_type'], 'expected_benefit': o['expected_benefit'], 'decision_state': o['decision_state']}
            for o in pilot_launchpad.better_way_options(opportunity)
        ],
        'mrv_plan': pilot_launchpad.mrv_plan(opportunity),
    })


@staff_member_required(login_url='/login/')
def resolve_responsible_party_view(request, pk):
    """
    PR11 Phase 27 — closes the "requires Django admin/shell" gap for
    resolving a responsible organisation. Staff-only, POST-only. Reuses
    the real, existing responsible_party.suggest_from_signal() (PR5/PR7)
    against the opportunity's own real originating signal — never
    guesses an organisation from free text. Suggests 'possible_organisation'
    only; a human must still separately confirm() it.
    """
    opportunity = get_object_or_404(GoodOpportunity, pk=pk)
    if request.method == 'POST':
        from django.contrib import messages
        signal = WorldSignal.objects.filter(title__in=opportunity.detected_signals).first()
        party = responsible_party_service.suggest_from_signal(opportunity, signal) if signal else None
        if party is None:
            messages.error(request, 'No originating signal with a publisher was found to suggest a responsible organisation from.')
    return redirect('good_agents:pilot_launchpad', pk=pk)


@staff_member_required(login_url='/login/')
def create_outreach_draft_view(request, pathway_pk):
    """
    PR11 Phase 10/27 — closes the "requires Django admin/shell" gap for
    creating an OutreachDraft: previously only a demo management command
    could create one. Pre-fills subject/body from the deterministic,
    grounded pilot_launchpad.render_outreach_message() — never an AI
    call — and immediately marks it 'ready_for_review' so it lands in the
    existing outreach_approve/outreach_send governance ladder untouched.
    """
    pathway = get_object_or_404(ActionPathway, pk=pathway_pk)
    if request.method == 'POST':
        message = pilot_launchpad.render_outreach_message(pathway.opportunity)
        contact = ActionContact.objects.filter(responsible_party__opportunity=pathway.opportunity).order_by('-last_verified').first()
        draft = outreach.create_draft(
            pathway, 'email', subject=message['subject'], body=message['body'], contact=contact,
            associated_evidence=pathway.opportunity.evidence_refs,
        )
        outreach.mark_ready_for_review(draft)
    return redirect('good_agents:pilot_launchpad', pk=pathway.opportunity_id)


@staff_member_required(login_url='/login/')
def add_contact_view(request, party_pk):
    """
    PR11 Phase 27 — closes the "requires Django admin" gap for recording a
    real, publicly verifiable contact route. Staff-only, POST-only. Public
    institutional channels only, per ActionContact's own existing
    discipline — never a scraped private personal contact.
    """
    party = get_object_or_404(ResponsibleParty, pk=party_pk)
    if request.method == 'POST':
        channel = request.POST.get('public_contact_channel', '').strip()
        source = request.POST.get('source_of_contact_info', '').strip()
        if channel and source:
            ActionContact.objects.create(
                responsible_party=party, contact_role=request.POST.get('contact_role', '').strip(),
                public_contact_channel=channel, source_of_contact_info=source,
                status='verified' if request.POST.get('verified') == 'true' else 'identified',
                last_verified=timezone.now().date() if request.POST.get('verified') == 'true' else None,
            )
        else:
            from django.contrib import messages
            messages.error(request, 'A public contact channel and its source are both required.')
    return redirect('good_agents:pilot_launchpad', pk=party.opportunity_id)


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
