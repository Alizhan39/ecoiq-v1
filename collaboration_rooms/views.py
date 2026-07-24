"""
collaboration_rooms/views.py — Partner-facing room access (any active
participant, via room_access_required — never bare @login_required) plus
EcoIQ staff room creation / promotion / centre views. Never exposes
'ecoiq_internal_only' visibility content to a non-staff request.
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render

from capability_graph.models import Organisation
from good_agents.models import FundingMatch, ResourceMatch
from partner_participation.models import RoutingCandidate

from collaboration_rooms.models import (
    CollaborationRoom, InformationRequest, NextStepProposal, RoomEvidenceItem, RoomParticipant,
)
from collaboration_rooms.permissions import acting_participant_required, room_access_required
from collaboration_rooms.services import (
    ai_assist, context as context_service, evidence as evidence_service, messaging, promotion,
    proposals as proposals_service, questions, rooms as rooms_service, summary as summary_service,
)

INTERNAL_VISIBILITY = 'ecoiq_internal_only'


def _visible_items(queryset, *, is_staff, organisation):
    """Phase 31 — never serialise EcoIQ-internal or another organisation's private notes into a partner-facing view."""
    if is_staff:
        return queryset
    from django.db.models import Q
    allowed = Q(visibility='shared_with_room')
    if organisation is not None:
        allowed |= Q(visibility='organisation_private', organisation=organisation)
    return queryset.filter(allowed)


@room_access_required
def room_detail(request, room_pk):
    room = request.room
    participant = request.room_participant
    is_staff = request.user.is_staff

    evidence_items = _visible_items(room.evidence_items.all(), is_staff=is_staff, organisation=participant.organisation)
    room_messages = _visible_items(room.messages.all(), is_staff=is_staff, organisation=participant.organisation)

    return render(request, 'collaboration_rooms/room_detail.html', {
        'room': room,
        'participant': participant,
        'context_package': context_service.build_context_package(room),
        'participants': room.participants.filter(revoked_at__isnull=True).select_related('user', 'organisation'),
        'evidence_items': evidence_items,
        'information_requests': room.information_requests.all().prefetch_related('responses'),
        'messages_list': room_messages,
        'proposals': room.next_step_proposals.all().prefetch_related('consents', 'required_organisations'),
        'summary': summary_service.collaboration_summary(room),
        'can_act': participant.role in ('coordinator', 'organisation_representative', 'expert'),
        'is_staff': is_staff,
    })


@acting_participant_required
def share_evidence_view(request, room_pk):
    if request.method == 'POST':
        try:
            evidence_service.share_evidence(
                request.room, shared_by=request.user, title=request.POST.get('title', ''),
                evidence_type=request.POST.get('evidence_type', 'other'), description=request.POST.get('description', ''),
                source_url=request.POST.get('source_url', ''), visibility=request.POST.get('visibility', 'shared_with_room'),
            )
        except evidence_service.EvidenceNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@staff_member_required(login_url='/login/')
def verify_evidence_view(request, room_pk, item_pk):
    item = get_object_or_404(RoomEvidenceItem, pk=item_pk, room_id=room_pk)
    if request.method == 'POST':
        evidence_service.verify_item(item, actor=request.user)
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@acting_participant_required
def create_request_view(request, room_pk):
    if request.method == 'POST':
        directed_to = request.POST.get('directed_to_organisation') or None
        try:
            questions.create_request(
                request.room, requested_by=request.user, question_text=request.POST.get('question_text', ''),
                request_type=request.POST.get('request_type', 'other'),
                directed_to_organisation=Organisation.objects.filter(pk=directed_to).first() if directed_to else None,
            )
        except questions.QuestionNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@acting_participant_required
def respond_to_request_view(request, room_pk, request_pk):
    info_request = get_object_or_404(InformationRequest, pk=request_pk, room_id=room_pk)
    if request.method == 'POST':
        evidence_pk = request.POST.get('evidence_item') or None
        evidence_item = RoomEvidenceItem.objects.filter(pk=evidence_pk, room_id=room_pk).first() if evidence_pk else None
        try:
            questions.record_response(info_request, responded_by=request.user, answer_text=request.POST.get('answer_text', ''), evidence_item=evidence_item)
        except questions.QuestionNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@room_access_required
def set_request_status_view(request, room_pk, request_pk):
    info_request = get_object_or_404(InformationRequest, pk=request_pk, room_id=room_pk)
    if request.method == 'POST':
        try:
            questions.set_status(info_request, request.POST.get('status', ''), actor=request.user)
        except questions.QuestionNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@room_access_required
def post_message_view(request, room_pk):
    if request.method == 'POST':
        try:
            messaging.post_message(request.room, author=request.user, body=request.POST.get('body', ''), visibility=request.POST.get('visibility', 'shared_with_room'))
        except messaging.MessageNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@acting_participant_required
def create_proposal_view(request, room_pk):
    if request.method == 'POST':
        required_org_pks = request.POST.getlist('required_organisations')
        resource_match_pk = request.POST.get('linked_resource_match') or None
        funding_match_pk = request.POST.get('linked_funding_match') or None
        try:
            proposal = proposals_service.create_proposal(
                request.room, proposed_by=request.user, proposal_type=request.POST.get('proposal_type', ''),
                description=request.POST.get('description', ''),
                required_organisations=Organisation.objects.filter(pk__in=required_org_pks) if required_org_pks else None,
                requires_ecoiq_consent=request.POST.get('requires_ecoiq_consent') == 'on',
                linked_resource_match=ResourceMatch.objects.filter(pk=resource_match_pk).first() if resource_match_pk else None,
                linked_funding_match=FundingMatch.objects.filter(pk=funding_match_pk).first() if funding_match_pk else None,
            )
            proposals_service.propose(proposal, actor=request.user)
        except proposals_service.ProposalNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@room_access_required
def give_consent_view(request, room_pk, proposal_pk):
    proposal = get_object_or_404(NextStepProposal, pk=proposal_pk, room_id=room_pk)
    if request.method == 'POST':
        org_pk = request.POST.get('organisation') or None
        organisation = Organisation.objects.filter(pk=org_pk).first() if org_pk else None
        try:
            proposals_service.give_consent(proposal, actor=request.user, organisation=organisation, notes=request.POST.get('notes', ''))
        except proposals_service.ProposalNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@room_access_required
def reject_consent_view(request, room_pk, proposal_pk):
    proposal = get_object_or_404(NextStepProposal, pk=proposal_pk, room_id=room_pk)
    if request.method == 'POST':
        org_pk = request.POST.get('organisation') or None
        organisation = Organisation.objects.filter(pk=org_pk).first() if org_pk else None
        try:
            proposals_service.reject_consent(proposal, actor=request.user, organisation=organisation, notes=request.POST.get('notes', ''))
        except proposals_service.ProposalNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@staff_member_required(login_url='/login/')
def promote_proposal_view(request, proposal_pk):
    proposal = get_object_or_404(NextStepProposal, pk=proposal_pk)
    if request.method == 'POST':
        try:
            promotion.promote_proposal(proposal, actor=request.user)
            messages.success(request, 'Proposal promoted to a real governed record.')
        except promotion.PromotionNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('collaboration_rooms:room_detail', room_pk=proposal.room_id)


@staff_member_required(login_url='/login/')
def create_room_view(request, candidate_pk):
    candidate = get_object_or_404(RoutingCandidate, pk=candidate_pk)
    if request.method == 'POST':
        try:
            room = rooms_service.create_room(candidate, actor=request.user, title=request.POST.get('title', ''))
            return redirect('collaboration_rooms:room_detail', room_pk=room.pk)
        except rooms_service.RoomCreationNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('partner_participation:network_overview')


@staff_member_required(login_url='/login/')
def add_participant_view(request, room_pk):
    room = get_object_or_404(CollaborationRoom, pk=room_pk)
    if request.method == 'POST':
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(pk=request.POST.get('user_id')).first()
        org_pk = request.POST.get('organisation') or None
        organisation = Organisation.objects.filter(pk=org_pk).first() if org_pk else None
        if user is None:
            messages.error(request, 'No such user.')
        else:
            try:
                rooms_service.add_participant(
                    room, user=user, organisation=organisation, role=request.POST.get('role', 'observer'),
                    reason=request.POST.get('reason', ''), actor=request.user,
                )
            except rooms_service.RoomAccessError as exc:
                messages.error(request, str(exc))
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@staff_member_required(login_url='/login/')
def revoke_participant_view(request, room_pk, participant_pk):
    participant = get_object_or_404(RoomParticipant, pk=participant_pk, room_id=room_pk)
    if request.method == 'POST':
        rooms_service.revoke_participant(participant, actor=request.user, reason=request.POST.get('reason', ''))
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@staff_member_required(login_url='/login/')
def withdraw_organisation_view(request, room_pk, org_pk):
    room = get_object_or_404(CollaborationRoom, pk=room_pk)
    organisation = get_object_or_404(Organisation, pk=org_pk)
    if request.method == 'POST':
        rooms_service.withdraw_organisation(room, organisation, actor=request.user)
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@staff_member_required(login_url='/login/')
def close_room_view(request, room_pk):
    room = get_object_or_404(CollaborationRoom, pk=room_pk)
    if request.method == 'POST':
        rooms_service.close_room(room, actor=request.user, reason=request.POST.get('reason', ''))
    return redirect('collaboration_rooms:staff_centre')


def rooms_list(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    active_room_ids = RoomParticipant.objects.filter(user=request.user, revoked_at__isnull=True).values_list('room_id', flat=True)
    rooms_qs = CollaborationRoom.objects.filter(pk__in=active_room_ids).select_related('routing_candidate__organisation', 'routing_candidate__opportunity')
    return render(request, 'collaboration_rooms/my_rooms.html', {
        'needs_response': rooms_qs.filter(status__in=['waiting_on_partner']),
        'waiting_on_ecoiq': rooms_qs.filter(status='waiting_on_ecoiq'),
        'waiting_on_evidence': rooms_qs.filter(status='waiting_on_evidence'),
        'next_step_proposed': rooms_qs.filter(status__in=['next_step_proposed', 'next_step_agreed']),
        'active': rooms_qs.filter(status='open'),
        'closed': rooms_qs.filter(status__in=['closed', 'archived', 'promoted_to_action', 'promoted_to_project']),
    })


@staff_member_required(login_url='/login/')
def staff_collaboration_centre(request):
    from collaboration_rooms.services.rooms import detect_stalled_rooms
    detect_stalled_rooms()
    rooms_qs = CollaborationRoom.objects.select_related('routing_candidate__organisation', 'routing_candidate__opportunity')
    proposals_awaiting_consent = NextStepProposal.objects.filter(status='proposed').select_related('room')
    ready_for_action = NextStepProposal.objects.filter(status='accepted').exclude(proposal_type='project_candidate').select_related('room')
    ready_for_project = NextStepProposal.objects.filter(status='accepted', proposal_type='project_candidate').select_related('room')
    return render(request, 'collaboration_rooms/staff_centre.html', {
        'active_rooms': rooms_qs.exclude(status__in=['closed', 'archived']),
        'waiting_on_partner': rooms_qs.filter(status='waiting_on_partner'),
        'waiting_on_ecoiq': rooms_qs.filter(status='waiting_on_ecoiq'),
        'missing_evidence': rooms_qs.filter(status='waiting_on_evidence'),
        'proposals_awaiting_consent': proposals_awaiting_consent,
        'ready_for_action': ready_for_action,
        'ready_for_project': ready_for_project,
        'stalled': rooms_qs.filter(activity_events__event_type='stall_detected').distinct(),
    })


@acting_participant_required
def ai_summarise_view(request, room_pk):
    try:
        text = ai_assist.summarise_history(request.room, actor=request.user)
        messages.success(request, f'AI summary (labelled AI-generated): {text}')
    except ai_assist.AIAssistanceUnavailableError as exc:
        messages.warning(request, str(exc))
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@acting_participant_required
def ai_open_questions_view(request, room_pk):
    try:
        text = ai_assist.extract_open_questions(request.room, actor=request.user)
        messages.success(request, f'AI-extracted open questions (labelled AI-generated): {text}')
    except ai_assist.AIAssistanceUnavailableError as exc:
        messages.warning(request, str(exc))
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)


@acting_participant_required
def ai_meeting_brief_view(request, room_pk):
    try:
        text = ai_assist.draft_neutral_meeting_brief(request.room, actor=request.user)
        messages.success(request, f'AI-drafted meeting brief (labelled AI-generated): {text}')
    except ai_assist.AIAssistanceUnavailableError as exc:
        messages.warning(request, str(exc))
    return redirect('collaboration_rooms:room_detail', room_pk=room_pk)
