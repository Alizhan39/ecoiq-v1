"""
partner_participation/views.py — Partner Portal (real, authenticated
organisation members — the first non-staff-facing surface in this
lineage) and EcoIQ staff review queues / Network Overview.

Never exposes internal EcoIQ review notes to the partner portal (Phase
15/29's own privacy rule) — every partner-facing template deliberately
omits `review_notes`/`resolution_notes` fields.
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from capability_graph.models import CAPABILITY_CHOICES, CapabilityConflict, Organisation, OrganisationCapability
from capability_graph.services import capabilities as capability_graph_capabilities
from capability_graph.services.routes import add_public_route, propose_route_update
from good_agents.models import AvailableResource, GOOD_TAXONOMY_CHOICES
from partner_participation.models import (
    FundingProgrammeDeclaration, OpportunityPreference, OrganisationMembership, RoutingCandidate,
)
from partner_participation.permissions import any_member_required, editor_required
from partner_participation.services import (
    capability_declarations, funding_declarations, membership as membership_service, notify,
    opportunity_preferences, routing,
)


# ── Organisation claim (any authenticated user) ──────────────────────────

@login_required(login_url='/login/')
def my_organisations(request):
    my_memberships = OrganisationMembership.objects.filter(user=request.user).select_related('organisation')
    organisations = Organisation.objects.all().order_by('name')
    return render(request, 'partner_participation/my_organisations.html', {
        'my_memberships': my_memberships, 'organisations': organisations,
    })


@login_required(login_url='/login/')
def claim_organisation(request, org_pk):
    organisation = get_object_or_404(Organisation, pk=org_pk)
    if request.method == 'POST':
        try:
            m = membership_service.request_membership(
                organisation, request.user, role=request.POST.get('role', 'viewer'),
                justification=request.POST.get('justification', ''),
            )
            notify.notify_membership_claim_requires_review(m)
            messages.success(request, 'Your claim has been submitted for EcoIQ review.')
        except membership_service.AlreadyMemberError as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:my_organisations')


# ── Partner Portal (verified members only) ───────────────────────────────

@any_member_required
def organisation_portal(request, org_pk):
    organisation = request.organisation
    capabilities = organisation.capabilities.select_related('verified_by').prefetch_related('public_routes')
    preferences = organisation.opportunity_preferences.all()
    resources = AvailableResource.objects.filter(organisation=organisation)
    funding_programmes = organisation.funding_programmes.all()
    routing_candidates = organisation.routing_candidates.exclude(
        status__in=['routing_candidate', 'ready_for_ecoiq_review'],
    ).select_related('opportunity')
    members = organisation.memberships.filter(status='verified_member').select_related('user')

    from partner_participation.models import ROUTING_ALLOWED_TRANSITIONS, ROUTING_STATUS_CHOICES
    status_labels = dict(ROUTING_STATUS_CHOICES)
    # Only offer the org a status they can actually reach from here — the
    # org-facing subset of ROUTING_ALLOWED_TRANSITIONS (EcoIQ-only states
    # like approved_to_share/shared are never offered as a candidate's own
    # next choice here). Attached directly on each instance (rather than a
    # separate pk-keyed dict) since Django templates can't do a variable-key
    # dict lookup without a custom filter.
    org_reachable = {'viewed', 'interested', 'not_interested', 'needs_more_information', 'accepted_for_next_step'}
    routing_candidates = list(routing_candidates)
    for candidate in routing_candidates:
        candidate.next_options = [
            (state, status_labels[state])
            for state in ROUTING_ALLOWED_TRANSITIONS.get(candidate.status, set()) if state in org_reachable
        ]

    return render(request, 'partner_participation/organisation_portal.html', {
        'organisation': organisation,
        'membership': request.membership,
        'capabilities': capabilities,
        'capability_choices': CAPABILITY_CHOICES,
        'preferences': preferences,
        'theme_choices': GOOD_TAXONOMY_CHOICES,
        'resources': resources,
        'funding_programmes': funding_programmes,
        'funder_type_choices': FundingProgrammeDeclaration.FUNDER_TYPE_CHOICES,
        'routing_candidates': routing_candidates,
        'members': members,
        'can_edit': request.membership.role in ('admin', 'editor'),
    })


@editor_required
def declare_capability_view(request, org_pk):
    if request.method == 'POST':
        capability_declarations.declare_capability(
            request.organisation, request.POST.get('capability', ''), request.membership,
            jurisdiction=request.POST.get('jurisdiction', ''), topic_domain=request.POST.get('topic_domain', ''),
            limitations=request.POST.get('limitations', ''),
        )
    return redirect('partner_participation:organisation_portal', org_pk=org_pk)


@editor_required
def attach_evidence_view(request, org_pk, capability_pk):
    edge = get_object_or_404(OrganisationCapability, pk=capability_pk, organisation=request.organisation)
    if request.method == 'POST':
        try:
            capability_declarations.attach_evidence(
                edge, evidence_url=request.POST.get('evidence_url', ''), actor=request.user,
            )
            from partner_participation.services.conflicts import detect_conflicts_for
            conflicts = detect_conflicts_for(edge)
            for conflict in conflicts:
                messages.warning(request, f'Conflict detected: {conflict.description}')
            notify.notify_capability_declaration_requires_review(edge)
        except ValueError as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:organisation_portal', org_pk=org_pk)


@editor_required
def set_preference_view(request, org_pk):
    if request.method == 'POST':
        opportunity_preferences.set_preference(
            request.organisation, request.POST.get('theme', ''), request.membership,
            acceptance_mode=request.POST.get('acceptance_mode', 'limited'),
            eligible_beneficiary_type=request.POST.get('eligible_beneficiary_type', ''),
            requires_sharia_review=request.POST.get('requires_sharia_review') == 'on',
            notes=request.POST.get('notes', ''),
        )
    return redirect('partner_participation:organisation_portal', org_pk=org_pk)


@editor_required
def declare_resource_view(request, org_pk):
    if request.method == 'POST':
        resource = AvailableResource.objects.create(
            resource_type=request.POST.get('resource_type', 'other'), title=request.POST.get('title', ''),
            region=request.POST.get('region', ''), availability=request.POST.get('availability', 'unknown'),
            eligibility=request.POST.get('eligibility', ''), capacity=request.POST.get('capacity', ''),
            constraints=request.POST.get('constraints', ''),
            source=f'Declared by {request.organisation.name} via partner portal',
            organisation=request.organisation, declared_by=request.user,
        )
        notify.notify_new_resource_available(resource)
    return redirect('partner_participation:organisation_portal', org_pk=org_pk)


@editor_required
def declare_funding_programme_view(request, org_pk):
    if request.method == 'POST':
        declaration = funding_declarations.declare_programme(
            request.organisation, request.POST.get('programme_name', ''), request.POST.get('funder_type', ''),
            request.membership, official_source_url=request.POST.get('official_source_url', ''),
            geography=request.POST.get('geography', ''), eligibility=request.POST.get('eligibility', ''),
        )
        notify.notify_funding_programme_declared(declaration)
    return redirect('partner_participation:organisation_portal', org_pk=org_pk)


@editor_required
def propose_route_view(request, org_pk, capability_pk):
    edge = get_object_or_404(OrganisationCapability, pk=capability_pk, organisation=request.organisation)
    if request.method == 'POST':
        route_id = request.POST.get('route_id', '')
        if route_id:
            route = get_object_or_404(edge.public_routes, pk=route_id)
            propose_route_update(
                route, actor=request.user, route_value=request.POST.get('route_value') or None,
                is_currently_open=request.POST.get('is_currently_open') == 'on',
                reason=request.POST.get('reason', ''),
            )
        else:
            add_public_route(
                edge, request.POST.get('route_type', 'other'), request.POST.get('route_value', ''),
            )
    return redirect('partner_participation:organisation_portal', org_pk=org_pk)


@any_member_required
def respond_to_routing_candidate_view(request, org_pk, candidate_pk):
    candidate = get_object_or_404(RoutingCandidate, pk=candidate_pk, organisation=request.organisation)
    if request.method == 'POST' and membership_service.can_respond_to_routing(request.organisation, request.user):
        new_status = request.POST.get('status', '')
        try:
            routing.transition(candidate, new_status, actor=request.user, notes=request.POST.get('notes', ''))
            if new_status == 'interested':
                notify.notify_organisation_interested(candidate)
        except routing.IllegalRoutingTransitionError as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:organisation_portal', org_pk=org_pk)


# ── EcoIQ staff review (staff-only) ───────────────────────────────────────

@staff_member_required(login_url='/login/')
def membership_review_queue(request):
    pending = OrganisationMembership.objects.filter(
        status__in=['claim_requested', 'under_review'],
    ).select_related('organisation', 'user')
    return render(request, 'partner_participation/membership_review_queue.html', {'pending': pending})


@staff_member_required(login_url='/login/')
def review_membership_view(request, membership_pk):
    m = get_object_or_404(OrganisationMembership, pk=membership_pk)
    if request.method == 'POST':
        decision = request.POST.get('decision', '')
        try:
            membership_service.review_membership(m, decision=decision, actor=request.user, notes=request.POST.get('notes', ''))
        except (membership_service.ReviewNotAllowedError, ValueError) as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:membership_review_queue')


@staff_member_required(login_url='/login/')
def declaration_review_queue(request):
    pending = OrganisationCapability.objects.filter(
        provenance='organisation_declared', verification_state__in=['self_reported', 'evidence_supported'],
    ).select_related('organisation')
    conflicts = CapabilityConflict.objects.filter(resolution='unresolved').select_related('capability__organisation')
    return render(request, 'partner_participation/declaration_review_queue.html', {
        'pending': pending, 'conflicts': conflicts,
    })


@staff_member_required(login_url='/login/')
def human_review_capability_view(request, capability_pk):
    edge = get_object_or_404(OrganisationCapability, pk=capability_pk)
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'human_review':
            capability_declarations.human_review(edge, actor=request.user, notes=request.POST.get('notes', ''))
        elif action == 'independently_verify':
            capability_graph_capabilities.verify_capability(edge, actor=request.user)
    return redirect('partner_participation:declaration_review_queue')


@staff_member_required(login_url='/login/')
def resolve_conflict_view(request, conflict_pk):
    conflict = get_object_or_404(CapabilityConflict, pk=conflict_pk)
    if request.method == 'POST':
        from partner_participation.services.conflicts import resolve_conflict
        resolve_conflict(
            conflict, resolution=request.POST.get('resolution', 'unresolved'), actor=request.user,
            notes=request.POST.get('notes', ''),
        )
    return redirect('partner_participation:declaration_review_queue')


@staff_member_required(login_url='/login/')
def approve_routing_candidate_view(request, candidate_pk):
    candidate = get_object_or_404(RoutingCandidate, pk=candidate_pk)
    if request.method == 'POST':
        new_status = request.POST.get('status', '')
        try:
            routing.transition(candidate, new_status, actor=request.user)
        except routing.IllegalRoutingTransitionError as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:network_overview')


@staff_member_required(login_url='/login/')
def network_overview(request):
    """PR8 Phase 22 — real counts only, no vanity metrics."""
    verified_orgs = Organisation.objects.filter(memberships__status='verified_member').distinct().count()
    capabilities_declared = OrganisationCapability.objects.filter(provenance='organisation_declared').count()
    capabilities_verified = OrganisationCapability.objects.filter(verification_state='independently_verified').count()
    from capability_graph.models import PublicRoute
    public_routes = PublicRoute.objects.filter(is_currently_open=True).count()
    resources_available = AvailableResource.objects.filter(organisation__isnull=False, availability='available').count()
    funding_programmes = FundingProgrammeDeclaration.objects.count()
    opportunity_preferences_count = OpportunityPreference.objects.count()
    active_routing_candidates = RoutingCandidate.objects.exclude(
        status__in=['not_interested'],
    ).count()
    connections_in_progress = RoutingCandidate.objects.filter(
        status__in=['shared', 'viewed', 'interested', 'needs_more_information'],
    ).count()

    return render(request, 'partner_participation/network_overview.html', {
        'verified_organisations': verified_orgs,
        'participating_organisations': Organisation.objects.filter(memberships__isnull=False).distinct().count(),
        'capabilities_declared': capabilities_declared,
        'capabilities_verified': capabilities_verified,
        'public_routes_open': public_routes,
        'resources_available': resources_available,
        'funding_programmes': funding_programmes,
        'opportunity_preferences': opportunity_preferences_count,
        'active_routing_candidates': active_routing_candidates,
        'connections_in_progress': connections_in_progress,
        'ready_for_review': RoutingCandidate.objects.filter(status='ready_for_ecoiq_review').select_related('organisation', 'opportunity'),
        'approved_awaiting_share': RoutingCandidate.objects.filter(status='approved_to_share').select_related('organisation', 'opportunity'),
    })
