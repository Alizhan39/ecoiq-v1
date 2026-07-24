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
    FundingProgrammeDeclaration, NextStepAction, OpportunityPreference, OrganisationMembership, PartnerInvitation,
    RoutingCandidate, ShareDelivery,
)
from partner_participation.permissions import any_member_required, editor_required
from partner_participation.services import (
    capability_declarations, consent as consent_service, delivery as delivery_service,
    funding_declarations, invitation as invitation_service, membership as membership_service, next_step as next_step_service,
    notify, onboarding, opportunity_preferences, response_capture, routing,
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
    if request.method == 'POST':
        new_status = request.POST.get('status', '')
        try:
            response_capture.partner_self_service_response(
                candidate, new_status, user=request.user, notes=request.POST.get('notes', ''),
            )
        except (routing.IllegalRoutingTransitionError, response_capture.ResponseNotAllowedError) as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:organisation_portal', org_pk=org_pk)


@editor_required
def consent_view(request, org_pk):
    if request.method == 'POST':
        action = request.POST.get('action', 'consent')
        try:
            if action == 'withdraw':
                existing = getattr(request.membership, 'consent', None)
                if existing is not None:
                    consent_service.withdraw_consent(existing, actor=request.user)
            else:
                consent_service.record_consent(request.membership, actor=request.user)
        except consent_service.ConsentNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:organisation_portal', org_pk=org_pk)


@login_required(login_url='/login/')
def accept_invitation_view(request, token):
    """
    Public-facing (any authenticated user), token-gated, single-use. Only
    ever creates a claim_requested membership — still requires real EcoIQ
    staff review before it becomes verified_member (Phase 1's own
    instruction applies even to an invited person).
    """
    invitation = get_object_or_404(PartnerInvitation, token=token)
    if request.method == 'POST':
        try:
            invitation_service.accept_invitation(token, user=request.user)
            messages.success(
                request,
                'Invitation accepted — your membership request has been submitted for EcoIQ review.',
            )
            return redirect('partner_participation:my_organisations')
        except invitation_service.InvalidInvitationError as exc:
            messages.error(request, str(exc))
    return render(request, 'partner_participation/accept_invitation.html', {'invitation': invitation})


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


# ── PR9 — Invitations (staff-only) ────────────────────────────────────────

@staff_member_required(login_url='/login/')
def create_invitation_view(request, org_pk):
    organisation = get_object_or_404(Organisation, pk=org_pk)
    if request.method == 'POST':
        invitation_service.create_invitation(
            organisation, request.POST.get('invitee_email', ''), actor=request.user,
            intended_role=request.POST.get('intended_role', 'viewer'), reason=request.POST.get('reason', ''),
        )
    return redirect('partner_participation:activation_dashboard')


@staff_member_required(login_url='/login/')
def send_invitation_view(request, invitation_pk):
    invitation = get_object_or_404(PartnerInvitation, pk=invitation_pk)
    if request.method == 'POST':
        try:
            invitation_service.send_invitation(invitation, actor=request.user)
            messages.success(request, f'Invitation sent by real email to {invitation.invitee_email}.')
        except invitation_service.ManualDeliveryRequiredError:
            subject, body, link = invitation_service.render_invitation_message(invitation, request=request)
            messages.warning(
                request,
                f'No real mail transport is configured — deliver this manually, then confirm below.\n'
                f'Subject: {subject}\n\n{body}',
            )
        except invitation_service.InvalidInvitationError as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:activation_dashboard')


@staff_member_required(login_url='/login/')
def mark_manually_sent_view(request, invitation_pk):
    invitation = get_object_or_404(PartnerInvitation, pk=invitation_pk)
    if request.method == 'POST':
        try:
            invitation_service.mark_manually_sent(invitation, actor=request.user, evidence=request.POST.get('evidence', ''))
            messages.success(request, 'Invitation recorded as manually delivered.')
        except invitation_service.InvalidInvitationError as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:activation_dashboard')


@staff_member_required(login_url='/login/')
def revoke_invitation_view(request, invitation_pk):
    invitation = get_object_or_404(PartnerInvitation, pk=invitation_pk)
    if request.method == 'POST':
        try:
            invitation_service.revoke_invitation(invitation, actor=request.user)
        except invitation_service.InvalidInvitationError as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:activation_dashboard')


# ── PR9 — Share approval + delivery (staff-only) ──────────────────────────

@staff_member_required(login_url='/login/')
def share_confirm_view(request, candidate_pk):
    """Phase 12 — GET-only inspection screen: recipient, route, message, evidence, rationale, before any approval."""
    candidate = get_object_or_404(RoutingCandidate, pk=candidate_pk)
    from capability_graph.models import PublicRoute
    from partner_participation.services.share_package import build_share_package, render_share_message
    open_routes = PublicRoute.objects.filter(
        organisation_capability__organisation=candidate.organisation, is_currently_open=True,
    )
    subject, body = render_share_message(candidate)
    return render(request, 'partner_participation/share_confirm.html', {
        'candidate': candidate,
        'package': build_share_package(candidate),
        'open_routes': open_routes,
        'subject': subject,
        'body': body,
        'has_real_mail_transport': invitation_service.has_real_mail_transport(),
        'prior_deliveries': ShareDelivery.objects.filter(candidate=candidate),
    })


@staff_member_required(login_url='/login/')
def approve_share_view(request, candidate_pk):
    candidate = get_object_or_404(RoutingCandidate, pk=candidate_pk)
    if request.method == 'POST':
        try:
            delivery_service.approve_share(candidate, actor=request.user)
        except (routing.IllegalRoutingTransitionError, delivery_service.ShareApprovalError) as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:share_confirm', candidate_pk=candidate_pk)


@staff_member_required(login_url='/login/')
def reject_share_view(request, candidate_pk):
    candidate = get_object_or_404(RoutingCandidate, pk=candidate_pk)
    if request.method == 'POST':
        try:
            delivery_service.reject_share(candidate, actor=request.user, reason=request.POST.get('reason', ''))
        except (routing.IllegalRoutingTransitionError, delivery_service.ShareApprovalError) as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:activation_dashboard')


@staff_member_required(login_url='/login/')
def deliver_real_email_view(request, candidate_pk):
    candidate = get_object_or_404(RoutingCandidate, pk=candidate_pk)
    if request.method == 'POST':
        try:
            delivery_service.deliver_via_real_email(candidate, actor=request.user)
            messages.success(request, 'Delivered via real email.')
        except delivery_service.DeliveryError as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:share_confirm', candidate_pk=candidate_pk)


@staff_member_required(login_url='/login/')
def deliver_manual_view(request, candidate_pk):
    candidate = get_object_or_404(RoutingCandidate, pk=candidate_pk)
    if request.method == 'POST':
        try:
            delivery_service.record_manual_delivery(
                candidate, actor=request.user, recipient=request.POST.get('recipient', ''),
                channel_notes=request.POST.get('channel_notes', ''), evidence=request.POST.get('evidence', ''),
            )
            messages.success(request, 'Manual delivery recorded.')
        except delivery_service.DeliveryError as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:share_confirm', candidate_pk=candidate_pk)


@staff_member_required(login_url='/login/')
def record_response_view(request, candidate_pk):
    """Staff recording a real response received through any channel (phone, email reply, in person)."""
    candidate = get_object_or_404(RoutingCandidate, pk=candidate_pk)
    if request.method == 'POST':
        try:
            response_capture.record_response(
                candidate, request.POST.get('status', ''), actor=request.user,
                channel=request.POST.get('channel', ''), summary=request.POST.get('summary', ''),
                reference=request.POST.get('reference', ''),
            )
        except (routing.IllegalRoutingTransitionError, response_capture.ResponseNotAllowedError) as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:activation_dashboard')


@staff_member_required(login_url='/login/')
def create_next_step_view(request, candidate_pk):
    candidate = get_object_or_404(RoutingCandidate, pk=candidate_pk)
    if request.method == 'POST':
        action_type = request.POST.get('action_type', '')
        notes = request.POST.get('notes', '')
        try:
            if action_type == 'data_exchange_request':
                next_step_service.create_data_exchange_request(candidate, actor=request.user, notes=notes)
            elif action_type == 'meeting_request':
                next_step_service.create_meeting_request(candidate, actor=request.user, notes=notes)
            elif action_type == 'project_candidate':
                next_step_service.propose_project_candidate(candidate, actor=request.user, rationale=notes)
            else:
                messages.error(request, f'Unsupported next-step type: {action_type!r}.')
        except next_step_service.NextStepNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:activation_dashboard')


@staff_member_required(login_url='/login/')
def activation_dashboard(request):
    """PR9 Phase 21 — real counts only, no vanity metrics."""
    from partner_participation.services.invitation import sweep_expire_invitations
    sweep_expire_invitations()

    invitations_pending = PartnerInvitation.objects.filter(status__in=['draft', 'sent']).select_related('organisation')
    verified_memberships = OrganisationMembership.objects.filter(status='verified_member').count()
    participating_organisations = Organisation.objects.filter(memberships__status='verified_member').distinct()
    routing_ready_organisations = [org for org in participating_organisations if onboarding.is_routing_ready(org)[0]]

    # PR10 — candidates whose organisation has responded positively but which
    # have no Governed Collaboration Room yet (collaboration_rooms' own
    # creation gate, never triggered from here automatically).
    ready_for_collaboration = RoutingCandidate.objects.filter(
        status__in=['interested', 'needs_more_information', 'accepted_for_next_step'],
        collaboration_room__isnull=True,
    ).select_related('organisation', 'opportunity')

    return render(request, 'partner_participation/activation_dashboard.html', {
        'ready_for_collaboration': ready_for_collaboration,
        'invitations_pending': invitations_pending,
        'verified_memberships': verified_memberships,
        'participating_organisations_count': participating_organisations.count(),
        'routing_ready_count': len(routing_ready_organisations),
        'routing_ready_organisations': routing_ready_organisations,
        'awaiting_share_review': RoutingCandidate.objects.filter(status='ready_for_ecoiq_review').select_related('organisation', 'opportunity'),
        'approved_awaiting_delivery': RoutingCandidate.objects.filter(status='approved_to_share').select_related('organisation', 'opportunity'),
        'shared_count': RoutingCandidate.objects.filter(status__in=['shared', 'no_response', 'viewed']).count(),
        'responses_pending': RoutingCandidate.objects.filter(status__in=['shared', 'no_response']).select_related('organisation', 'opportunity'),
        'interested_count': RoutingCandidate.objects.filter(status='interested').count(),
        'declined_count': RoutingCandidate.objects.filter(status='not_interested').count(),
        'next_step_actions': NextStepAction.objects.exclude(status='completed').select_related('candidate__organisation', 'candidate__opportunity'),
    })
