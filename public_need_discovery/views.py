"""
public_need_discovery/views.py — PR13: every mutation staff-only +
POST-only. No view here can perform a real external action — the
furthest this app reaches is pre-filling an
outreach_readiness.OutreachCandidateAssessment for a human to
independently walk through PR12's own governance from scratch.
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render

from capability_graph.services.organisations import get_or_create_organisation
from good_agents.models import GoodOpportunity, WorldSignal
from good_agents.services import responsible_party
from public_need_discovery.models import (
    ACTIONABILITY_CLASS_CHOICES, ACTIONABILITY_STATE_CHOICES, CandidateOrganisationRole, ORGANISATION_ROLE_CHOICES,
    PUBLIC_PROCESS_TYPE_CHOICES, SENSITIVITY_CATEGORY_CHOICES, SMALL_ACTION_TYPE_CHOICES,
)
from public_need_discovery.services import actionability, jurisdiction, qualification, roles, sensitivity, small_action


def _lead_signal(opportunity):
    return WorldSignal.objects.filter(title__in=opportunity.detected_signals).first()


@staff_member_required(login_url='/login/')
def candidate_queue(request):
    """
    Phase 17 — sectioned by the actual current blocker, never a bare list.
    Excludes [CONTROLLED TEST] rows from the real queue, same convention
    as outreach_readiness.candidate_review_list.
    """
    opportunities = GoodOpportunity.objects.exclude(title__startswith='[CONTROLLED TEST]').order_by('-urgency')[:50]
    rows = []
    for opportunity in opportunities:
        candidate = actionability.get_or_create_candidate(opportunity)
        rows.append({
            'opportunity': opportunity,
            'candidate': candidate,
            'blockers': actionability.blockers(candidate),
        })

    def section(predicate):
        return [r for r in rows if predicate(r)]

    return render(request, 'public_need_discovery/candidate_queue.html', {
        'ready_for_review': section(lambda r: r['candidate'].actionability_state == 'informational_only' and not r['blockers']),
        'needs_responsible_body': section(lambda r: any(b['code'] == 'NO_RESPONSIBLE_BODY_CONFIRMED' for b in r['blockers'])),
        'needs_jurisdiction': section(lambda r: any(b['code'] == 'NO_JURISDICTION' for b in r['blockers'])),
        'needs_route': section(lambda r: r['candidate'].actionability_state == 'actionable' and not r['candidate'].use_official_process and not r['candidate'].outreach_suitable),
        'use_official_process': section(lambda r: r['candidate'].use_official_process),
        'needs_sensitivity_review': section(lambda r: r['candidate'].is_sensitive and not r['candidate'].evidence_valid_but_outreach_inappropriate and r['candidate'].actionability_state == 'actionable_needs_review'),
        'potentially_suitable': section(lambda r: r['candidate'].actionability_state in ('actionable', 'actionable_needs_review') and not r['candidate'].use_official_process),
        'rejected': section(lambda r: r['candidate'].is_rejected),
    })


@staff_member_required(login_url='/login/')
def candidate_detail(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    candidate = actionability.get_or_create_candidate(opportunity)
    lead_signal = _lead_signal(opportunity)
    return render(request, 'public_need_discovery/candidate_detail.html', {
        'opportunity': opportunity,
        'candidate': candidate,
        'lead_signal': lead_signal,
        'blockers': actionability.blockers(candidate),
        'recommendation': actionability.evaluate_candidate(candidate),
        'organisation_roles': candidate.organisation_roles.select_related('organisation').all(),
        'confirmed_justifying_roles': list(roles.confirmed_justifying_roles(candidate)),
        'actionability_class_choices': ACTIONABILITY_CLASS_CHOICES,
        'actionability_state_choices': ACTIONABILITY_STATE_CHOICES,
        'organisation_role_choices': ORGANISATION_ROLE_CHOICES,
        'small_action_type_choices': SMALL_ACTION_TYPE_CHOICES,
        'public_process_type_choices': PUBLIC_PROCESS_TYPE_CHOICES,
        'sensitivity_category_choices': SENSITIVITY_CATEGORY_CHOICES,
        'suggested_sensitivity_categories': sensitivity.suggest_sensitivity_categories(opportunity),
        'suggested_action': small_action.suggest_action(candidate),
        'outreach_assessment': getattr(opportunity, 'outreach_assessment', None),
    })


@staff_member_required(login_url='/login/')
def resolve_jurisdiction_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        candidate = actionability.get_or_create_candidate(opportunity)
        value, resolved, notes = jurisdiction.resolve_jurisdiction(opportunity)
        candidate.jurisdiction, candidate.jurisdiction_resolved, candidate.jurisdiction_resolution_notes = value, resolved, notes
        candidate.save(update_fields=['jurisdiction', 'jurisdiction_resolved', 'jurisdiction_resolution_notes', 'updated_at'])
    return redirect('public_need_discovery:candidate_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def resolve_responsible_party_view(request, opportunity_pk):
    """Bootstraps a real ResponsibleParty/Organisation from the opportunity's own lead signal, if not already resolved."""
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        signal = _lead_signal(opportunity)
        if signal is not None:
            responsible_party.suggest_from_signal(opportunity, signal)
        else:
            messages.error(request, 'No originating signal on record — cannot resolve a responsible party.')
    return redirect('public_need_discovery:candidate_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def suggest_roles_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        candidate = actionability.get_or_create_candidate(opportunity)
        roles.suggest_roles_from_capability_graph(candidate)
    return redirect('public_need_discovery:candidate_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def confirm_role_view(request, role_pk):
    """Confirms an existing (possibly suggested) role, or edits its rationale/evidence before confirming."""
    role = get_object_or_404(CandidateOrganisationRole, pk=role_pk)
    if request.method == 'POST':
        roles.record_role(
            role.candidate, role.organisation, role.role, actor=request.user,
            evidence_reference=request.POST.get('evidence_reference', role.evidence_reference),
            rationale=request.POST.get('rationale', role.rationale), confirmed=True,
        )
    return redirect('public_need_discovery:candidate_detail', opportunity_pk=role.candidate.opportunity_id)


@staff_member_required(login_url='/login/')
def add_role_view(request, opportunity_pk):
    """Records a NEW role claim for an organisation not yet suggested — e.g. a real org identified by name that the Capability Graph has no capability edge for yet."""
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        candidate = actionability.get_or_create_candidate(opportunity)
        organisation_name = request.POST.get('organisation_name', '').strip()
        role_value = request.POST.get('role', '')
        if not organisation_name or role_value not in dict(ORGANISATION_ROLE_CHOICES):
            messages.error(request, 'A real organisation name and a valid role are both required.')
        else:
            organisation = get_or_create_organisation(
                organisation_name, org_type=request.POST.get('org_type', 'other'),
                jurisdiction=request.POST.get('org_jurisdiction', ''),
            )
            roles.record_role(
                candidate, organisation, role_value, actor=request.user,
                evidence_reference=request.POST.get('evidence_reference', ''),
                rationale=request.POST.get('rationale', ''), confirmed=request.POST.get('confirmed') == 'true',
            )
    return redirect('public_need_discovery:candidate_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def record_small_action_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        candidate = actionability.get_or_create_candidate(opportunity)
        try:
            small_action.record_small_action(
                candidate, actor=request.user, action_type=request.POST.get('action_type', ''),
                description=request.POST.get('description', ''),
            )
        except small_action.SmallActionNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('public_need_discovery:candidate_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def record_official_process_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        candidate = actionability.get_or_create_candidate(opportunity)
        try:
            small_action.record_official_process(
                candidate, actor=request.user, process_type=request.POST.get('process_type', ''),
                route_reference=request.POST.get('route_reference', ''),
                use_official_process=request.POST.get('use_official_process', 'true') == 'true',
            )
        except small_action.SmallActionNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('public_need_discovery:candidate_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def sensitivity_review_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        candidate = actionability.get_or_create_candidate(opportunity)
        categories = request.POST.getlist('categories')
        sensitivity.record_sensitivity_review(
            candidate, actor=request.user, categories=categories, notes=request.POST.get('notes', ''),
            outreach_inappropriate=request.POST.get('outreach_inappropriate') == 'true',
        )
    return redirect('public_need_discovery:candidate_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def set_actionability_state_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        candidate = actionability.get_or_create_candidate(opportunity)
        new_state = request.POST.get('actionability_state', '')
        if new_state:
            actionability.set_actionability_state(candidate, new_state, actor=request.user, rationale=request.POST.get('rationale', ''))
            candidate.actionability_class = request.POST.get('actionability_class', candidate.actionability_class)
            candidate.capital_required_now = request.POST.get('capital_required_now', candidate.capital_required_now)
            candidate.why_real_need = request.POST.get('why_real_need', candidate.why_real_need)
            candidate.why_action_useful = request.POST.get('why_action_useful', candidate.why_action_useful)
            candidate.what_ecoiq_does_not_know = request.POST.get('what_ecoiq_does_not_know', candidate.what_ecoiq_does_not_know)
            candidate.save()
            from public_need_discovery.services.qualification import recompute_actionability_qualified, recompute_discovery_qualified
            recompute_discovery_qualified(candidate)
            recompute_actionability_qualified(candidate)
    return redirect('public_need_discovery:candidate_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def promote_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        candidate = actionability.get_or_create_candidate(opportunity)
        role_pk = request.POST.get('organisation_role_pk', '')
        role = candidate.organisation_roles.filter(pk=role_pk).first()
        if role is None:
            messages.error(request, 'Select one of this candidate\'s own confirmed justifying organisation roles.')
        else:
            try:
                qualification.promote_to_outreach_readiness(candidate, actor=request.user, organisation_role=role)
                messages.success(request, 'Promoted to outreach_readiness — continue the recipient responsibility test there.')
            except qualification.QualificationNotAllowedError as exc:
                messages.error(request, str(exc))
    return redirect('public_need_discovery:candidate_detail', opportunity_pk=opportunity_pk)
