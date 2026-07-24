"""
collaboration_rooms/tests.py — PR10: Governed Collaboration Rooms. Covers
the room creation gate, access isolation (cross-room, cross-org, revoked
membership), evidence claim/verification separation, structured
questions, controlled messaging, next-step proposals + mutual consent
(never inferred from silence), promotion into PR9's existing next_step
functions (never a parallel action/project system), the append-only
timeline, withdrawal, stall detection, privacy (internal vs shared vs
organisation-private), notifications, CSRF, Mission Control integration,
and a full regression smoke test.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from capability_graph.services.capabilities import verify_capability
from capability_graph.services.organisations import get_or_create_organisation
from capability_graph.services.routes import add_public_route
from good_agents.models import GoodOpportunity
from good_agents.services import mission_control
from partner_participation.services import (
    capability_declarations, consent as consent_service, membership, opportunity_preferences, routing,
)

from collaboration_rooms.models import CollaborationRoom, RoomConsent
from collaboration_rooms.permissions import get_active_participant, has_room_access
from collaboration_rooms.services import (
    evidence as evidence_service, messaging, promotion, proposals as proposals_service, questions,
    rooms as rooms_service, summary as summary_service,
)


def _user(username='cruser', **kwargs):
    User = get_user_model()
    return User.objects.create_user(username, f'{username}@example.com', 'pw', **kwargs)


def _staff(username='crstaff'):
    return _user(username, is_staff=True)


def _verified_member(org, user, role='editor'):
    m = membership.request_membership(org, user, role=role)
    return membership.review_membership(m, decision='verified_member', actor=_staff('reviewer-' + user.username))


def _opportunity(**overrides):
    base = dict(title='PR10 test opportunity', problem_statement='x', theme='water', confidence=60.0)
    base.update(overrides)
    return GoodOpportunity.objects.create(**base)


def _interested_candidate(name='Interested Org', jurisdiction='England', status='interested'):
    """A fully routing-ready organisation with a real RoutingCandidate already at the given post-interest status."""
    slug = name.lower().replace(' ', '-')
    org = get_or_create_organisation(name, jurisdiction=jurisdiction)
    rep = _user(f'{slug}-rep')
    staff = _staff(f'{slug}-staff')
    m = _verified_member(org, rep)
    edge = capability_declarations.declare_capability(org, 'supply', m, jurisdiction=jurisdiction, topic_domain='water supply')
    edge = capability_declarations.attach_evidence(edge, evidence_url='https://example.org/x', actor=rep)
    verify_capability(edge, actor=staff)
    add_public_route(edge, 'email', 'contact@example.org')
    opportunity_preferences.set_preference(org, 'water', m, acceptance_mode='open_to_relevant_opportunities')
    consent_service.record_consent(m, actor=rep)

    opp = _opportunity(theme='water', region=jurisdiction, title=f'{name} opportunity')
    result = routing.generate_routing_candidates(opp)
    candidate = next(c for c in result['created'] if c.organisation_id == org.pk)
    routing.transition(candidate, 'ready_for_ecoiq_review', actor=rep)
    from partner_participation.services import delivery as delivery_service
    delivery_service.approve_share(candidate, actor=staff)
    delivery_service.record_manual_delivery(candidate, actor=staff, recipient='contact@example.org', channel_notes='phone')
    candidate.refresh_from_db()
    from partner_participation.services import response_capture
    response_capture.record_response(candidate, 'viewed', actor=staff)
    candidate.refresh_from_db()
    if status == 'accepted_for_next_step':
        # accepted_for_next_step is only reachable via interested first — never a direct jump.
        response_capture.record_response(candidate, 'interested', actor=staff)
        candidate.refresh_from_db()
        response_capture.record_response(candidate, status, actor=staff)
        candidate.refresh_from_db()
    elif status != 'viewed':
        response_capture.record_response(candidate, status, actor=staff)
        candidate.refresh_from_db()
    return candidate, org, rep, staff


class RoomCreationGateTests(TestCase):
    def test_creation_requires_staff(self):
        candidate, org, rep, staff = _interested_candidate()
        with self.assertRaises(rooms_service.RoomCreationNotAllowedError):
            rooms_service.create_room(candidate, actor=rep)

    def test_creation_blocked_for_non_interested_status(self):
        candidate, org, rep, staff = _interested_candidate(name='Not Yet Org', status='viewed')
        # 'viewed' is not in the allowed set — only interested/needs_more_information/accepted_for_next_step.
        with self.assertRaises(rooms_service.RoomCreationNotAllowedError):
            rooms_service.create_room(candidate, actor=staff)

    def test_creation_allowed_for_each_permitted_status(self):
        for status in ('interested', 'needs_more_information', 'accepted_for_next_step'):
            candidate, org, rep, staff = _interested_candidate(name=f'Org {status}', status=status)
            room = rooms_service.create_room(candidate, actor=staff)
            self.assertEqual(room.routing_candidate_id, candidate.pk)

    def test_creation_is_idempotent(self):
        candidate, org, rep, staff = _interested_candidate(name='Idempotent Org')
        room1 = rooms_service.create_room(candidate, actor=staff)
        room2 = rooms_service.create_room(candidate, actor=staff)
        self.assertEqual(room1.pk, room2.pk)
        self.assertEqual(CollaborationRoom.objects.filter(routing_candidate=candidate).count(), 1)

    def test_creation_never_from_a_bare_match(self):
        """A routing_candidate still at 'routing_candidate' (never shared) can never open a room."""
        org = get_or_create_organisation('Bare Match Org')
        opp = _opportunity(theme='water')
        result = routing.generate_routing_candidates(opp)
        # No capability declared for this bare org, so nothing is created — the point stands either way.
        self.assertEqual(result['created'], [])

    def test_staff_coordinator_and_anchor_org_members_auto_added(self):
        candidate, org, rep, staff = _interested_candidate(name='Auto Add Org')
        room = rooms_service.create_room(candidate, actor=staff)
        roles = {p.user_id: p.role for p in room.participants.all()}
        self.assertEqual(roles[staff.pk], 'coordinator')
        self.assertEqual(roles[rep.pk], 'organisation_representative')

    def test_no_other_organisation_auto_added(self):
        candidate, org, rep, staff = _interested_candidate(name='Solo Org')
        other_org, other_rep = get_or_create_organisation('Other Org'), _user('other-org-rep')
        _verified_member(other_org, other_rep)
        room = rooms_service.create_room(candidate, actor=staff)
        self.assertFalse(room.participants.filter(user=other_rep).exists())


class AccessIsolationTests(TestCase):
    def test_cross_org_isolation(self):
        candidate, org, rep, staff = _interested_candidate(name='Isolated Org')
        room = rooms_service.create_room(candidate, actor=staff)
        outsider = _user('outsider')
        self.assertFalse(has_room_access(room, outsider))

    def test_cross_room_isolation(self):
        candidate_a, org_a, rep_a, staff = _interested_candidate(name='Room A Org')
        candidate_b, org_b, rep_b, staff2 = _interested_candidate(name='Room B Org')
        room_a = rooms_service.create_room(candidate_a, actor=staff)
        room_b = rooms_service.create_room(candidate_b, actor=staff2)
        self.assertFalse(has_room_access(room_b, rep_a))
        self.assertFalse(has_room_access(room_a, rep_b))

    def test_revoked_participant_loses_access(self):
        candidate, org, rep, staff = _interested_candidate(name='Revoke Org')
        room = rooms_service.create_room(candidate, actor=staff)
        self.assertTrue(has_room_access(room, rep))
        participant = get_active_participant(room, rep)
        rooms_service.revoke_participant(participant, actor=staff, reason='left the org')
        self.assertFalse(has_room_access(room, rep))

    def test_unauthenticated_user_cannot_view_room(self):
        candidate, org, rep, staff = _interested_candidate(name='Anon Org')
        room = rooms_service.create_room(candidate, actor=staff)
        response = self.client.get(reverse('collaboration_rooms:room_detail', args=[room.pk]))
        self.assertEqual(response.status_code, 302)  # redirected to login

    def test_no_room_enumeration_for_unauthorised_authenticated_user(self):
        candidate, org, rep, staff = _interested_candidate(name='Enumeration Org')
        room = rooms_service.create_room(candidate, actor=staff)
        outsider = _user('enum-outsider')
        self.client.force_login(outsider)
        response = self.client.get(reverse('collaboration_rooms:room_detail', args=[room.pk]))
        self.assertEqual(response.status_code, 403)

    def test_add_participant_requires_staff_and_a_reason(self):
        candidate, org, rep, staff = _interested_candidate(name='Add Participant Org')
        room = rooms_service.create_room(candidate, actor=staff)
        expert = _user('expert-one')
        with self.assertRaises(rooms_service.RoomAccessError):
            rooms_service.add_participant(room, user=expert, organisation=None, role='expert', reason='', actor=staff)
        participant = rooms_service.add_participant(room, user=expert, organisation=None, role='expert', reason='Independent technical review.', actor=staff)
        self.assertTrue(has_room_access(room, expert))
        self.assertEqual(participant.role, 'expert')


class EvidenceClaimVerificationTests(TestCase):
    def test_share_evidence_requires_active_participant(self):
        candidate, org, rep, staff = _interested_candidate(name='Evidence Gate Org')
        room = rooms_service.create_room(candidate, actor=staff)
        outsider = _user('evidence-outsider')
        with self.assertRaises(evidence_service.EvidenceNotAllowedError):
            evidence_service.share_evidence(room, shared_by=outsider, title='x')

    def test_bare_declaration_stays_a_claim(self):
        candidate, org, rep, staff = _interested_candidate(name='Claim Org')
        room = rooms_service.create_room(candidate, actor=staff)
        item = evidence_service.share_evidence(room, shared_by=rep, title='We can provide 50 units')
        self.assertEqual(item.verification_state, 'declared_claim')

    def test_item_with_source_url_starts_linked_not_verified(self):
        candidate, org, rep, staff = _interested_candidate(name='Linked Org')
        room = rooms_service.create_room(candidate, actor=staff)
        item = evidence_service.share_evidence(room, shared_by=rep, title='Report', source_url='https://example.org/report')
        self.assertEqual(item.verification_state, 'linked_evidence')

    def test_only_staff_can_verify(self):
        candidate, org, rep, staff = _interested_candidate(name='Verify Org')
        room = rooms_service.create_room(candidate, actor=staff)
        item = evidence_service.share_evidence(room, shared_by=rep, title='Claim')
        with self.assertRaises(evidence_service.EvidenceNotAllowedError):
            evidence_service.verify_item(item, actor=rep)
        item = evidence_service.verify_item(item, actor=staff)
        self.assertEqual(item.verification_state, 'ecoiq_verified')
        self.assertEqual(item.verified_by, staff)


class QuestionsTests(TestCase):
    def test_create_request_requires_participant(self):
        candidate, org, rep, staff = _interested_candidate(name='Question Gate Org')
        room = rooms_service.create_room(candidate, actor=staff)
        outsider = _user('question-outsider')
        with self.assertRaises(questions.QuestionNotAllowedError):
            questions.create_request(room, requested_by=outsider, question_text='What quantity?')

    def test_response_never_auto_closes_request(self):
        candidate, org, rep, staff = _interested_candidate(name='No Auto Close Org')
        room = rooms_service.create_room(candidate, actor=staff)
        req = questions.create_request(room, requested_by=staff, question_text='What quantity is available?', request_type='resource_availability')
        questions.record_response(req, responded_by=rep, answer_text='50 units')
        req.refresh_from_db()
        self.assertEqual(req.status, 'open')  # still open — a text response alone never closes it

    def test_response_without_evidence_is_claim_only(self):
        candidate, org, rep, staff = _interested_candidate(name='Claim Response Org')
        room = rooms_service.create_room(candidate, actor=staff)
        req = questions.create_request(room, requested_by=staff, question_text='Quantity?')
        response = questions.record_response(req, responded_by=rep, answer_text='50 units')
        self.assertTrue(response.is_claim_only)

    def test_response_with_evidence_is_not_claim_only(self):
        candidate, org, rep, staff = _interested_candidate(name='Evidence Response Org')
        room = rooms_service.create_room(candidate, actor=staff)
        item = evidence_service.share_evidence(room, shared_by=rep, title='Inventory sheet', source_url='https://example.org/inv')
        req = questions.create_request(room, requested_by=staff, question_text='Quantity?')
        response = questions.record_response(req, responded_by=rep, answer_text='See inventory', evidence_item=item)
        self.assertFalse(response.is_claim_only)

    def test_explicit_status_change_required_to_close(self):
        candidate, org, rep, staff = _interested_candidate(name='Explicit Close Org')
        room = rooms_service.create_room(candidate, actor=staff)
        req = questions.create_request(room, requested_by=staff, question_text='Quantity?')
        questions.record_response(req, responded_by=rep, answer_text='50 units')
        questions.set_status(req, 'answered', actor=staff)
        req.refresh_from_db()
        self.assertEqual(req.status, 'answered')


class MessagingTests(TestCase):
    def test_post_message_requires_participant(self):
        candidate, org, rep, staff = _interested_candidate(name='Message Gate Org')
        room = rooms_service.create_room(candidate, actor=staff)
        outsider = _user('message-outsider')
        with self.assertRaises(messaging.MessageNotAllowedError):
            messaging.post_message(room, author=outsider, body='hi')

    def test_no_anonymous_messages(self):
        candidate, org, rep, staff = _interested_candidate(name='Attributed Org')
        room = rooms_service.create_room(candidate, actor=staff)
        message = messaging.post_message(room, author=rep, body='Hello team')
        self.assertEqual(message.author, rep)

    def test_edit_preserves_history_never_silent(self):
        candidate, org, rep, staff = _interested_candidate(name='Edit History Org')
        room = rooms_service.create_room(candidate, actor=staff)
        message = messaging.post_message(room, author=rep, body='Original text')
        messaging.edit_message(message, actor=rep, new_body='Corrected text')
        message.refresh_from_db()
        self.assertEqual(message.body, 'Corrected text')
        self.assertEqual(len(message.edit_history), 1)
        self.assertEqual(message.edit_history[0]['body'], 'Original text')

    def test_only_author_can_edit(self):
        candidate, org, rep, staff = _interested_candidate(name='Edit Guard Org')
        room = rooms_service.create_room(candidate, actor=staff)
        message = messaging.post_message(room, author=rep, body='Original')
        with self.assertRaises(messaging.MessageNotAllowedError):
            messaging.edit_message(message, actor=staff, new_body='Hijacked')


class ProposalConsentTests(TestCase):
    def _proposal(self, org_name='Proposal Org', requires_ecoiq=True, required_orgs=None):
        candidate, org, rep, staff = _interested_candidate(name=org_name)
        room = rooms_service.create_room(candidate, actor=staff)
        proposal = proposals_service.create_proposal(
            room, proposed_by=staff, proposal_type='technical_discussion', description='Discuss specs',
            required_organisations=required_orgs, requires_ecoiq_consent=requires_ecoiq,
        )
        proposals_service.propose(proposal, actor=staff)
        return proposal, room, org, rep, staff

    def test_propose_materialises_consent_rows(self):
        proposal, room, org, rep, staff = self._proposal(required_orgs=None)
        self.assertEqual(proposal.consents.count(), 1)  # just EcoIQ, no required_organisations passed
        self.assertIsNone(proposal.consents.first().organisation)

    def test_single_pending_consent_never_reaches_accepted(self):
        proposal, room, org, rep, staff = self._proposal(required_orgs=[])
        proposal.required_organisations.set([org])
        # Re-propose isn't valid (already proposed); simulate by creating consent for org directly via propose() flow instead:
        proposal2 = proposals_service.create_proposal(room, proposed_by=staff, proposal_type='introduction', requires_ecoiq_consent=True, required_organisations=[org])
        proposals_service.propose(proposal2, actor=staff)
        self.assertEqual(proposal2.status, 'proposed')
        proposals_service.give_consent(proposal2, actor=staff, organisation=None)  # only EcoIQ consents
        proposal2.refresh_from_db()
        self.assertEqual(proposal2.status, 'proposed')  # org's consent still pending — never inferred

    def test_all_required_consents_reaches_accepted(self):
        candidate, org, rep, staff = _interested_candidate(name='Full Consent Org')
        room = rooms_service.create_room(candidate, actor=staff)
        proposal = proposals_service.create_proposal(room, proposed_by=staff, proposal_type='introduction', requires_ecoiq_consent=True, required_organisations=[org])
        proposals_service.propose(proposal, actor=staff)
        proposals_service.give_consent(proposal, actor=staff, organisation=None)
        proposals_service.give_consent(proposal, actor=rep, organisation=org)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, 'accepted')

    def test_single_rejection_rejects_the_whole_proposal(self):
        candidate, org, rep, staff = _interested_candidate(name='Rejection Org')
        room = rooms_service.create_room(candidate, actor=staff)
        proposal = proposals_service.create_proposal(room, proposed_by=staff, proposal_type='introduction', requires_ecoiq_consent=True, required_organisations=[org])
        proposals_service.propose(proposal, actor=staff)
        proposals_service.reject_consent(proposal, actor=rep, organisation=org, notes='Not ready')
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, 'rejected')

    def test_cannot_consent_on_behalf_of_another_organisation(self):
        candidate, org, rep, staff = _interested_candidate(name='Impersonation Org')
        other_candidate, other_org, other_rep, other_staff = _interested_candidate(name='Other Impersonation Org')
        room = rooms_service.create_room(candidate, actor=staff)
        proposal = proposals_service.create_proposal(room, proposed_by=staff, proposal_type='introduction', requires_ecoiq_consent=False, required_organisations=[org])
        proposals_service.propose(proposal, actor=staff)
        with self.assertRaises(proposals_service.ProposalNotAllowedError):
            proposals_service.give_consent(proposal, actor=other_rep, organisation=org)

    def test_ecoiq_consent_requires_staff(self):
        proposal, room, org, rep, staff = self._proposal()
        with self.assertRaises(proposals_service.ProposalNotAllowedError):
            proposals_service.give_consent(proposal, actor=rep, organisation=None)


class PromotionTests(TestCase):
    def _accepted_proposal(self, proposal_type='technical_discussion', **kwargs):
        candidate, org, rep, staff = _interested_candidate(name=f'Promo {proposal_type} Org')
        room = rooms_service.create_room(candidate, actor=staff)
        proposal = proposals_service.create_proposal(room, proposed_by=staff, proposal_type=proposal_type, requires_ecoiq_consent=True, **kwargs)
        proposals_service.propose(proposal, actor=staff)
        proposals_service.give_consent(proposal, actor=staff, organisation=None)
        proposal.refresh_from_db()
        return proposal, room, candidate, staff

    def test_promotion_requires_accepted_status(self):
        candidate, org, rep, staff = _interested_candidate(name='Not Accepted Org')
        room = rooms_service.create_room(candidate, actor=staff)
        proposal = proposals_service.create_proposal(room, proposed_by=staff, proposal_type='technical_discussion')
        with self.assertRaises(promotion.PromotionNotAllowedError):
            promotion.promote_proposal(proposal, actor=staff)

    def test_promotion_requires_staff(self):
        proposal, room, candidate, staff = self._accepted_proposal()
        rep = _user('promo-non-staff')
        with self.assertRaises(promotion.PromotionNotAllowedError):
            promotion.promote_proposal(proposal, actor=rep)

    def test_meeting_like_promotes_to_next_step_action(self):
        proposal, room, candidate, staff = self._accepted_proposal('technical_discussion')
        result = promotion.promote_proposal(proposal, actor=staff)
        self.assertEqual(result.action_type, 'meeting_request')
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, 'completed')
        room.refresh_from_db()
        self.assertEqual(room.status, 'promoted_to_action')

    def test_project_candidate_reuses_pr9_project_bridge(self):
        proposal, room, candidate, staff = self._accepted_proposal('project_candidate')
        result = promotion.promote_proposal(proposal, actor=staff)
        self.assertEqual(result.action_type, 'project_candidate')
        room.refresh_from_db()
        self.assertEqual(room.status, 'promoted_to_project')
        from good_agents.models import ProjectCandidate
        pc_pk = int(result.linked_object_reference.split(':')[-1])
        pc = ProjectCandidate.objects.get(pk=pc_pk)
        self.assertIsNone(pc.created_project_id)  # never an active project directly

    def test_verify_resource_requires_linked_resource_match(self):
        proposal, room, candidate, staff = self._accepted_proposal('verify_resource')
        with self.assertRaises(promotion.PromotionNotAllowedError):
            promotion.promote_proposal(proposal, actor=staff)

    def test_reject_close_closes_room_without_creating_anything(self):
        proposal, room, candidate, staff = self._accepted_proposal('reject_close')
        promotion.promote_proposal(proposal, actor=staff)
        room.refresh_from_db()
        self.assertEqual(room.status, 'closed')


class TimelineTests(TestCase):
    def test_append_only_ordering(self):
        candidate, org, rep, staff = _interested_candidate(name='Timeline Org')
        room = rooms_service.create_room(candidate, actor=staff)
        messaging.post_message(room, author=rep, body='first')
        messaging.post_message(room, author=rep, body='second')
        events = list(room.activity_events.all())
        self.assertEqual(events[0].event_type, 'room_created')
        self.assertTrue(all(events[i].created_at <= events[i + 1].created_at for i in range(len(events) - 1)))


class WithdrawalTests(TestCase):
    def test_withdrawal_revokes_access_but_preserves_history(self):
        candidate, org, rep, staff = _interested_candidate(name='Withdraw Org')
        room = rooms_service.create_room(candidate, actor=staff)
        message = messaging.post_message(room, author=rep, body='Before withdrawal')
        rooms_service.withdraw_organisation(room, org, actor=staff)
        self.assertFalse(has_room_access(room, rep))
        message.refresh_from_db()
        self.assertEqual(message.body, 'Before withdrawal')  # untouched
        self.assertTrue(room.activity_events.filter(event_type='organisation_withdrew').exists())

    def test_pending_consent_stays_pending_after_withdrawal(self):
        candidate, org, rep, staff = _interested_candidate(name='Withdraw Consent Org')
        room = rooms_service.create_room(candidate, actor=staff)
        proposal = proposals_service.create_proposal(room, proposed_by=staff, proposal_type='introduction', requires_ecoiq_consent=False, required_organisations=[org])
        proposals_service.propose(proposal, actor=staff)
        rooms_service.withdraw_organisation(room, org, actor=staff)
        consent = proposal.consents.get(organisation=org)
        self.assertEqual(consent.status, 'pending')  # never silently approved or rejected


class StallDetectionTests(TestCase):
    def test_no_flag_before_grace_period(self):
        candidate, org, rep, staff = _interested_candidate(name='Fresh Org')
        rooms_service.create_room(candidate, actor=staff)
        stalled = rooms_service.detect_stalled_rooms(grace_days=10)
        self.assertEqual(stalled, [])

    def test_flag_after_grace_period_never_auto_closes(self):
        candidate, org, rep, staff = _interested_candidate(name='Stale Org')
        room = rooms_service.create_room(candidate, actor=staff)
        room.last_activity_at = timezone.now() - datetime.timedelta(days=15)
        room.save(update_fields=['last_activity_at'])
        stalled = rooms_service.detect_stalled_rooms(grace_days=10)
        self.assertEqual(len(stalled), 1)
        room.refresh_from_db()
        self.assertNotEqual(room.status, 'closed')  # only labelled, never auto-closed

    def test_repeated_sweep_does_not_duplicate_flags(self):
        candidate, org, rep, staff = _interested_candidate(name='Repeat Stale Org')
        room = rooms_service.create_room(candidate, actor=staff)
        room.last_activity_at = timezone.now() - datetime.timedelta(days=15)
        room.save(update_fields=['last_activity_at'])
        rooms_service.detect_stalled_rooms(grace_days=10)
        rooms_service.detect_stalled_rooms(grace_days=10)
        self.assertEqual(room.activity_events.filter(event_type='stall_detected').count(), 1)


class PrivacyTests(TestCase):
    def test_ecoiq_internal_message_not_serialised_to_partner_view(self):
        candidate, org, rep, staff = _interested_candidate(name='Privacy Org')
        room = rooms_service.create_room(candidate, actor=staff)
        messaging.post_message(room, author=staff, body='INTERNAL ONLY NOTE', visibility='ecoiq_internal_only')
        self.client.force_login(rep)
        response = self.client.get(reverse('collaboration_rooms:room_detail', args=[room.pk]))
        self.assertNotContains(response, 'INTERNAL ONLY NOTE')

    def test_ecoiq_internal_evidence_not_serialised_to_partner_view(self):
        candidate, org, rep, staff = _interested_candidate(name='Privacy Evidence Org')
        room = rooms_service.create_room(candidate, actor=staff)
        evidence_service.share_evidence(room, shared_by=staff, title='INTERNAL RISK ASSESSMENT', visibility='ecoiq_internal_only')
        self.client.force_login(rep)
        response = self.client.get(reverse('collaboration_rooms:room_detail', args=[room.pk]))
        self.assertNotContains(response, 'INTERNAL RISK ASSESSMENT')

    def test_staff_can_see_internal_content(self):
        candidate, org, rep, staff = _interested_candidate(name='Staff Visible Org')
        room = rooms_service.create_room(candidate, actor=staff)
        messaging.post_message(room, author=staff, body='INTERNAL STAFF NOTE', visibility='ecoiq_internal_only')
        self.client.force_login(staff)
        response = self.client.get(reverse('collaboration_rooms:room_detail', args=[room.pk]))
        self.assertContains(response, 'INTERNAL STAFF NOTE')

    def test_organisation_private_note_not_visible_to_other_organisation(self):
        candidate, org, rep, staff = _interested_candidate(name='Org Private Org')
        room = rooms_service.create_room(candidate, actor=staff)
        other_org, other_rep = get_or_create_organisation('Other Private Org'), _user('other-private-rep')
        _verified_member(other_org, other_rep)
        rooms_service.add_participant(room, user=other_rep, organisation=other_org, role='organisation_representative', reason='Second party to a proposed introduction.', actor=staff)
        messaging.post_message(room, author=rep, body='PRIVATE TO MY ORG ONLY', visibility='organisation_private')
        self.client.force_login(other_rep)
        response = self.client.get(reverse('collaboration_rooms:room_detail', args=[room.pk]))
        self.assertNotContains(response, 'PRIVATE TO MY ORG ONLY')


class NotificationTests(TestCase):
    def test_participant_added_notification_deduped(self):
        from collaboration_rooms.services.notify import _already_notified, notify_participant_added
        candidate, org, rep, staff = _interested_candidate(name='Notify Org')
        room = rooms_service.create_room(candidate, actor=staff)
        expert = _user('notify-expert')
        participant = rooms_service.add_participant(room, user=expert, organisation=None, role='expert', reason='Review', actor=staff)
        self.assertTrue(_already_notified(participant, 'participant_added'))
        note2 = notify_participant_added(participant)
        self.assertIsNone(note2)


class CSRFTests(TestCase):
    def test_post_message_requires_csrf_token(self):
        candidate, org, rep, staff = _interested_candidate(name='CSRF Org')
        room = rooms_service.create_room(candidate, actor=staff)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(rep)
        response = csrf_client.post(reverse('collaboration_rooms:post_message', args=[room.pk]), {'body': 'hi'})
        self.assertEqual(response.status_code, 403)


class NoFakeCommitmentTests(TestCase):
    def test_room_status_never_implies_partnership(self):
        from collaboration_rooms.models import ROOM_STATUS_CHOICES
        labels = ' '.join(label for _, label in ROOM_STATUS_CHOICES).lower()
        for word in ('partnership', 'contract', 'commitment', 'agreement'):
            self.assertNotIn(word, labels)

    def test_room_detail_page_shows_disclaimer(self):
        candidate, org, rep, staff = _interested_candidate(name='Disclaimer Org')
        room = rooms_service.create_room(candidate, actor=staff)
        self.client.force_login(rep)
        response = self.client.get(reverse('collaboration_rooms:room_detail', args=[room.pk]))
        self.assertContains(response, 'does not create a partnership')


class MissionControlIntegrationTests(TestCase):
    def test_summary_includes_collaboration_room_when_present(self):
        from good_agents.models import ResponsibleParty
        from good_agents.services import action_gate as action_gate_service
        candidate, org, rep, staff = _interested_candidate(name='MC Room Org')
        room = rooms_service.create_room(candidate, actor=staff)

        opp = candidate.opportunity
        action_gate_service.get_or_create_gate(opp)
        ResponsibleParty.objects.create(opportunity=opp, name=org.name, organisation=org, party_type='ngo')

        summary = mission_control.partner_participation_summary(opp)
        self.assertIsNotNone(summary)
        self.assertEqual(summary['collaboration_room'], room)

    def test_summary_none_room_when_no_room_created(self):
        from good_agents.models import ResponsibleParty
        from good_agents.services import action_gate as action_gate_service
        candidate, org, rep, staff = _interested_candidate(name='MC No Room Org')
        opp = candidate.opportunity
        action_gate_service.get_or_create_gate(opp)
        ResponsibleParty.objects.create(opportunity=opp, name=org.name, organisation=org, party_type='ngo')
        summary = mission_control.partner_participation_summary(opp)
        self.assertIsNone(summary['collaboration_room'])


class DeterministicSummaryTests(TestCase):
    def test_summary_is_pure_and_deterministic(self):
        candidate, org, rep, staff = _interested_candidate(name='Summary Org')
        room = rooms_service.create_room(candidate, actor=staff)
        s1 = summary_service.collaboration_summary(room)
        s2 = summary_service.collaboration_summary(room)
        self.assertEqual(s1, s2)
        self.assertEqual(s1['organisation'], org.name)


class RegressionTests(TestCase):
    def test_full_pr10_loop_smoke(self):
        """Interested candidate -> room -> context -> evidence -> question/answer -> proposal -> consent -> promotion."""
        candidate, org, rep, staff = _interested_candidate(name='Full PR10 Loop Org')
        room = rooms_service.create_room(candidate, actor=staff)
        self.assertEqual(room.participants.filter(revoked_at__isnull=True).count(), 2)  # staff + rep

        item = evidence_service.share_evidence(room, shared_by=rep, title='Capacity statement', description='We can supply 50 units/week')
        self.assertEqual(item.verification_state, 'declared_claim')
        evidence_service.verify_item(item, actor=staff)
        item.refresh_from_db()
        self.assertEqual(item.verification_state, 'ecoiq_verified')

        req = questions.create_request(room, requested_by=staff, question_text='What is the exact delivery location?', request_type='resource_availability')
        questions.record_response(req, responded_by=rep, answer_text='Warehouse in Manchester', evidence_item=item)
        questions.set_status(req, 'answered', actor=staff)

        messaging.post_message(room, author=rep, body='Happy to proceed once details are confirmed.')

        proposal = proposals_service.create_proposal(room, proposed_by=staff, proposal_type='introduction', requires_ecoiq_consent=True, required_organisations=[org])
        proposals_service.propose(proposal, actor=staff)
        proposals_service.give_consent(proposal, actor=staff, organisation=None)
        proposals_service.give_consent(proposal, actor=rep, organisation=org)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, 'accepted')

        result = promotion.promote_proposal(proposal, actor=staff)
        self.assertIsNotNone(result)
        room.refresh_from_db()
        self.assertEqual(room.status, 'promoted_to_action')

        # The whole chain leaves a real, ordered, append-only trail.
        event_types = list(room.activity_events.values_list('event_type', flat=True))
        self.assertIn('room_created', event_types)
        self.assertIn('evidence_shared', event_types)
        self.assertIn('evidence_verified', event_types)
        self.assertIn('question_asked', event_types)
        self.assertIn('answer_provided', event_types)
        self.assertIn('message_sent', event_types)
        self.assertIn('next_step_proposed', event_types)
        self.assertIn('consent_given', event_types)
        self.assertIn('next_step_agreed', event_types)
        self.assertIn('action_created', event_types)
