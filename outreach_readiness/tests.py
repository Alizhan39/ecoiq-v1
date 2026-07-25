"""outreach_readiness/tests.py — PR12: First Real Outreach Readiness."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from capability_graph.services.organisations import get_or_create_organisation
from good_agents.models import GoodOpportunity, OutreachDraft, ResponsibleParty
from outreach_readiness.models import (
    FounderSendDecision, OutreachCandidateAssessment, OutreachMessageVersion, OutreachRiskReview,
)
from outreach_readiness.services import (
    assessment as assessment_service, dry_run as dry_run_service, founder_review as founder_review_service,
    message as message_service, risk as risk_service, route as route_service,
)
from outreach_readiness.services.candidate_review import candidate_review_list
from outreach_readiness.services.duplicate_check import prior_outreach_history
from outreach_readiness.services.queues import command_centre_queues
from outreach_readiness.services.readiness import compute_readiness_state
from outreach_readiness.services.roles import record_role, role_summary

User = get_user_model()

ALL_RISK_TRUE = {f: True for f in OutreachRiskReview.CHECKLIST_FIELDS}


def _user(username='or-user'):
    return User.objects.create_user(username, f'{username}@example.com', 'password123')


def _staff(username='or-staff'):
    return User.objects.create_user(username, f'{username}@example.com', 'password123', is_staff=True)


def _opportunity(**overrides):
    base = dict(title='Test opportunity', problem_statement='A real problem.', theme='energy', confidence=60.0, evidence_refs=['ref'])
    base.update(overrides)
    return GoodOpportunity.objects.create(**base)


def _org(name='Test Org', **overrides):
    return get_or_create_organisation(name, **overrides)


def _proceedable_assessment(actor, *, opportunity=None, org_name='Proceedable Org'):
    """Builds an assessment already past suitability + recipient responsibility + ask, ready for a message."""
    opportunity = opportunity or _opportunity()
    org = _org(org_name, org_type='funder')
    party = ResponsibleParty.objects.create(opportunity=opportunity, name=org.name, party_type='funder', organisation=org)
    a = assessment_service.get_or_create_assessment(opportunity)
    a.organisation = org
    a.responsible_party = party
    a.save()
    assessment_service.record_recipient_responsibility_test(
        a, actor=actor, recipient_role='funder', remit_confirmed=True, remit_rationale='Test.',
        geographic_relevance_confirmed=True, identity_confirmed=True,
    )
    a.refresh_from_db()
    assessment_service.set_suitability_state(a, 'suitable', actor=actor, rationale='Test setup.')
    assessment_service.record_minimum_viable_ask(a, actor=actor, ask='Confirm the programme exists.', value_offered='Evidence brief.')
    a.refresh_from_db()
    return a


def _add_route(a, actor):
    return route_service.record_route(
        a, actor=actor, contact_page_or_institutional_email='test@example.invalid',
        route_type='email', source_reference='https://example.invalid/contact',
    )


def _create_version(a, actor):
    return message_service.create_message_version(
        a, actor=actor, subject='Subject', fact_points=['fact'], inference_points=['inference'],
        the_request='Confirm the programme exists.', unknowns=['unknown'],
        body_text=' '.join(['word'] * 130), sender_name='Sender', sender_role='Researcher',
        sender_organisation='EcoIQ', reply_to='reply@example.invalid',
    )


class RecipientResponsibilityAcceptanceTests(TestCase):
    """The key acceptance test (Phase 2): never treat a publisher as an action recipient merely because its feed generated the signal."""

    def test_source_of_information_role_is_structurally_rejected(self):
        staff = _staff()
        opp = _opportunity(title='M 6.5 test earthquake')
        org = _org('USGS (test)', org_type='research_institution')
        a = assessment_service.get_or_create_assessment(opp)
        a.organisation = org
        a.save()

        a = assessment_service.record_recipient_responsibility_test(
            a, actor=staff, recipient_role='source_of_information',
            remit_rationale='Publishes data; does not act on individual events.',
        )
        self.assertEqual(a.suitability_state, 'wrong_organisation')
        self.assertTrue(a.is_rejected)

    def test_responsible_authority_role_does_not_reject(self):
        staff = _staff()
        opp = _opportunity()
        org = _org('Real Regulator', org_type='regulator')
        a = assessment_service.get_or_create_assessment(opp)
        a.organisation = org
        a.save()
        a = assessment_service.record_recipient_responsibility_test(
            a, actor=staff, recipient_role='responsible_authority', remit_confirmed=True,
        )
        self.assertNotEqual(a.suitability_state, 'wrong_organisation')

    def test_recipient_responsibility_requires_real_actor(self):
        opp = _opportunity()
        a = assessment_service.get_or_create_assessment(opp)
        with self.assertRaises(assessment_service.AssessmentNotAllowedError):
            assessment_service.record_recipient_responsibility_test(a, actor=None, recipient_role='funder')


class SuitabilityStateTests(TestCase):
    def test_set_suitability_state_requires_actor(self):
        a = assessment_service.get_or_create_assessment(_opportunity())
        with self.assertRaises(assessment_service.AssessmentNotAllowedError):
            assessment_service.set_suitability_state(a, 'suitable', actor=None)

    def test_rejected_states_are_terminal_and_never_proceedable(self):
        staff = _staff()
        a = assessment_service.get_or_create_assessment(_opportunity())
        for state in ('wrong_organisation', 'wrong_route', 'no_clear_ask', 'insufficient_evidence', 'too_sensitive', 'not_actionable', 'rejected'):
            assessment_service.set_suitability_state(a, state, actor=staff)
            self.assertTrue(a.is_rejected)
            self.assertFalse(a.may_proceed_to_message)


class SensitivityGateTests(TestCase):
    def test_outreach_inappropriate_blocks_even_with_valid_evidence(self):
        staff = _staff()
        opp = _opportunity()
        a = assessment_service.get_or_create_assessment(opp)
        assessment_service.set_suitability_state(a, 'suitable', actor=staff)
        a.refresh_from_db()
        a = assessment_service.record_sensitivity_review(
            a, actor=staff, categories=['disaster', 'death_or_injury'], outreach_inappropriate=True,
        )
        self.assertEqual(a.suitability_state, 'too_sensitive')
        self.assertTrue(a.evidence_valid_but_outreach_inappropriate)
        self.assertFalse(a.may_proceed_to_message)

    def test_marked_sensitive_without_inappropriate_flag_does_not_reject(self):
        staff = _staff()
        a = assessment_service.get_or_create_assessment(_opportunity())
        assessment_service.set_suitability_state(a, 'suitable', actor=staff)
        a.refresh_from_db()
        a = assessment_service.record_sensitivity_review(a, actor=staff, categories=['children'], outreach_inappropriate=False)
        self.assertTrue(a.is_sensitive)
        self.assertNotEqual(a.suitability_state, 'too_sensitive')


class RouteTests(TestCase):
    def test_route_requires_real_actor(self):
        a = assessment_service.get_or_create_assessment(_opportunity())
        with self.assertRaises(route_service.RouteNotAllowedError):
            route_service.record_route(a, actor=None, contact_page_or_institutional_email='x', route_type='email', source_reference='y')

    def test_route_requires_contact_and_source(self):
        staff = _staff()
        a = assessment_service.get_or_create_assessment(_opportunity())
        with self.assertRaises(route_service.RouteNotAllowedError):
            route_service.record_route(a, actor=staff, contact_page_or_institutional_email='', route_type='email', source_reference='')

    def test_new_route_supersedes_prior_active_route(self):
        staff = _staff()
        a = assessment_service.get_or_create_assessment(_opportunity())
        route1 = _add_route(a, staff)
        route2 = route_service.record_route(
            a, actor=staff, contact_page_or_institutional_email='new@example.invalid',
            route_type='email', source_reference='https://example.invalid/new',
        )
        route1.refresh_from_db()
        self.assertIsNotNone(route1.superseded_at)
        self.assertIsNone(route2.superseded_at)
        self.assertEqual(route_service.active_route(a).pk, route2.pk)

    def test_no_route_means_blocked_no_verified_route_readiness(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        self.assertEqual(compute_readiness_state(a), 'needs_route')


class MinimumViableAskTests(TestCase):
    def test_cannot_draft_message_without_suitable_verdict(self):
        staff = _staff()
        a = assessment_service.get_or_create_assessment(_opportunity())
        with self.assertRaises(message_service.MessageNotAllowedError):
            _create_version(a, staff)

    def test_ask_recorded_but_still_needs_route_before_message(self):
        staff = _staff()
        opp = _opportunity()
        org = _org('Ask Org', org_type='funder')
        a = assessment_service.get_or_create_assessment(opp)
        a.organisation = org
        a.save()
        assessment_service.set_suitability_state(a, 'suitable', actor=staff)
        a.refresh_from_db()
        assessment_service.record_minimum_viable_ask(a, actor=staff, ask='Confirm eligibility.')
        a.refresh_from_db()
        self.assertEqual(compute_readiness_state(a), 'needs_route')


class MessageVersioningTests(TestCase):
    def test_versions_increment(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        _add_route(a, staff)
        v1 = _create_version(a, staff)
        v2 = _create_version(a, staff)
        self.assertEqual(v1.version_number, 1)
        self.assertEqual(v2.version_number, 2)

    def test_editing_after_founder_approval_invalidates_prior_version(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        _add_route(a, staff)
        v1 = _create_version(a, staff)
        risk_service.record_risk_review(v1, actor=staff, answers=ALL_RISK_TRUE)
        v1.refresh_from_db()
        message_service.mark_reviewed(v1, actor=staff)
        v1.refresh_from_db()
        message_service.founder_approve(v1, actor=staff)
        v1.refresh_from_db()
        self.assertEqual(v1.approval_status, 'approved')

        v2 = _create_version(a, staff)
        v1.refresh_from_db()
        self.assertEqual(v1.approval_status, 'invalidated')
        self.assertIsNotNone(v1.invalidated_at)
        self.assertEqual(v2.version_number, 2)

    def test_cannot_review_invalidated_version(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        _add_route(a, staff)
        v1 = _create_version(a, staff)
        message_service.invalidate_version(v1, reason='test')
        with self.assertRaises(message_service.MessageNotAllowedError):
            message_service.mark_reviewed(v1, actor=staff)

    def test_founder_approve_requires_passing_risk_review(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        _add_route(a, staff)
        v1 = _create_version(a, staff)
        with self.assertRaises(message_service.MessageNotAllowedError):
            message_service.founder_approve(v1, actor=staff)

    def test_word_count_status(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        _add_route(a, staff)
        v1 = _create_version(a, staff)
        status = message_service.word_count_status(v1)
        self.assertTrue(status['in_range'])


class RiskReviewTests(TestCase):
    def test_defaults_to_all_false(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        _add_route(a, staff)
        v1 = _create_version(a, staff)
        review = risk_service.record_risk_review(v1, actor=staff, answers={})
        self.assertFalse(review.all_passed)
        self.assertEqual(len(review.failed_items), len(OutreachRiskReview.CHECKLIST_FIELDS))

    def test_all_passed_requires_every_item(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        _add_route(a, staff)
        v1 = _create_version(a, staff)
        answers = dict(ALL_RISK_TRUE)
        answers['no_do_not_contact_status'] = False
        review = risk_service.record_risk_review(v1, actor=staff, answers=answers)
        self.assertFalse(review.all_passed)
        self.assertEqual(review.failed_items, ['no_do_not_contact_status'])


class DryRunTests(TestCase):
    def test_dry_run_never_calls_send_mail(self):
        """No real transport call exists in this module at all — verified by mocking send_mail and asserting it's never touched."""
        staff = _staff()
        a = _proceedable_assessment(staff)
        _add_route(a, staff)
        v1 = _create_version(a, staff)
        risk_service.record_risk_review(v1, actor=staff, answers=ALL_RISK_TRUE)
        v1.refresh_from_db()
        from unittest.mock import patch
        with patch('django.core.mail.send_mail') as mock_send:
            dr = dry_run_service.run_dry_run(v1, actor=staff)
            mock_send.assert_not_called()
        self.assertEqual(dr.validation_result, 'pass')

    def test_dry_run_fails_without_route(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        # No route recorded — message creation itself requires suitable state only, route is separately needed.
        a.suitability_state = 'suitable'
        a.save()
        from outreach_readiness.models import OutreachMessageVersion as MV
        v1 = MV.objects.create(assessment=a, version_number=1, subject='s', body_text='b', reply_to='r@example.invalid')
        dr = dry_run_service.run_dry_run(v1, actor=staff)
        self.assertEqual(dr.validation_result, 'fail')
        self.assertIn('No active verified contact route recorded.', dr.validation_details)

    def test_dry_run_requires_actor(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        _add_route(a, staff)
        v1 = _create_version(a, staff)
        with self.assertRaises(dry_run_service.DryRunNotAllowedError):
            dry_run_service.run_dry_run(v1, actor=None)

    def test_transport_audit_reports_no_real_email_locally(self):
        audit = dry_run_service.transport_audit()
        self.assertFalse(audit['real_email_transport'])
        self.assertIn('no_transport', audit['available_modes'])


class FounderReviewTests(TestCase):
    def test_recommendation_do_not_send_when_rejected(self):
        staff = _staff()
        a = assessment_service.get_or_create_assessment(_opportunity())
        assessment_service.set_suitability_state(a, 'wrong_organisation', actor=staff)
        a.refresh_from_db()
        rec, reasons = founder_review_service.compute_recommendation(a)
        self.assertEqual(rec, 'do_not_send')

    def test_recommendation_revise_when_no_message(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        rec, reasons = founder_review_service.compute_recommendation(a)
        self.assertEqual(rec, 'revise')

    def test_recommendation_send_when_everything_passes(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        _add_route(a, staff)
        v1 = _create_version(a, staff)
        risk_service.record_risk_review(v1, actor=staff, answers=ALL_RISK_TRUE)
        v1.refresh_from_db()
        message_service.mark_reviewed(v1, actor=staff)
        dry_run_service.run_dry_run(v1, actor=staff)
        rec, reasons = founder_review_service.compute_recommendation(a)
        self.assertEqual(rec, 'send')

    def test_record_decision_requires_real_actor(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        with self.assertRaises(founder_review_service.FounderReviewNotAllowedError):
            founder_review_service.record_decision(a, 'send', actor=None, message_version=None)

    def test_founder_can_override_system_recommendation(self):
        """Even when the system recommends SEND, the founder's real decision (do_not_send) is what's recorded."""
        staff = _staff()
        a = _proceedable_assessment(staff)
        _add_route(a, staff)
        v1 = _create_version(a, staff)
        risk_service.record_risk_review(v1, actor=staff, answers=ALL_RISK_TRUE)
        v1.refresh_from_db()
        message_service.mark_reviewed(v1, actor=staff)
        dry_run_service.run_dry_run(v1, actor=staff)
        rec, _ = founder_review_service.compute_recommendation(a)
        self.assertEqual(rec, 'send')

        decision = founder_review_service.record_decision(a, 'do_not_send', actor=staff, message_version=v1, rationale='Founder override.')
        self.assertEqual(decision.decision, 'do_not_send')
        self.assertEqual(FounderSendDecision.objects.get(assessment=a).decision, 'do_not_send')


class ReadinessStateLadderTests(TestCase):
    def test_not_assessed_for_brand_new_opportunity(self):
        opp = _opportunity()
        self.assertEqual(compute_readiness_state(None), 'not_assessed')
        a = assessment_service.get_or_create_assessment(opp)
        self.assertEqual(compute_readiness_state(a), 'not_assessed')

    def test_needs_evidence_when_insufficient(self):
        staff = _staff()
        opp = _opportunity(evidence_refs=[], insufficient_evidence=True)
        a = assessment_service.get_or_create_assessment(opp)
        assessment_service.set_suitability_state(a, 'suitable', actor=staff)
        a.refresh_from_db()
        self.assertEqual(compute_readiness_state(a), 'needs_evidence')

    def test_needs_recipient_when_no_organisation(self):
        staff = _staff()
        a = assessment_service.get_or_create_assessment(_opportunity())
        assessment_service.set_suitability_state(a, 'suitable', actor=staff)
        a.refresh_from_db()
        self.assertEqual(compute_readiness_state(a), 'needs_recipient')

    def test_ready_for_founder_review_only_after_full_chain(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        _add_route(a, staff)
        v1 = _create_version(a, staff)
        self.assertEqual(compute_readiness_state(a), 'needs_risk_review')
        risk_service.record_risk_review(v1, actor=staff, answers=ALL_RISK_TRUE)
        v1.refresh_from_db()
        self.assertEqual(compute_readiness_state(a), 'ready_for_message_review')
        message_service.mark_reviewed(v1, actor=staff)
        v1.refresh_from_db()
        self.assertEqual(compute_readiness_state(a), 'blocked')
        dry_run_service.run_dry_run(v1, actor=staff)
        self.assertEqual(compute_readiness_state(a), 'ready_for_founder_review')


class DuplicateHistoryTests(TestCase):
    def test_no_history_by_default(self):
        staff = _staff()
        a = _proceedable_assessment(staff)
        self.assertEqual(prior_outreach_history(a), [])

    def test_finds_prior_sent_outreach_draft_for_same_organisation(self):
        from good_agents.models import ActionContact
        from good_agents.services import action_gate as action_gate_service
        from good_agents.services import action_pathway as action_pathway_service

        org = _org('Drafted Org', org_type='funder')
        opp1 = _opportunity(title='Earlier real outreach')
        opp2 = _opportunity(title='New candidate')
        party1 = ResponsibleParty.objects.create(opportunity=opp1, name=org.name, party_type='funder', organisation=org)
        contact1 = ActionContact.objects.create(responsible_party=party1, public_contact_channel='a@example.invalid', source_of_contact_info='site')
        action_gate_service.transition(opp1, 'needs_review')
        action_gate_service.transition(opp1, 'approved_for_contact')
        pathway1 = action_pathway_service.create_pathway(opp1, 'information_request', rationale='r')
        draft1 = OutreachDraft.objects.create(action_pathway=pathway1, contact=contact1, status='sent')

        a2 = assessment_service.get_or_create_assessment(opp2)
        a2.organisation = org
        a2.save()
        history = prior_outreach_history(a2)
        self.assertEqual(len(history), 1)
        self.assertIn(f'#{draft1.pk}', history[0])

    def test_finds_prior_founder_send_decision_for_same_organisation(self):
        staff = _staff()
        org = _org('Repeat Org', org_type='funder')
        opp1 = _opportunity(title='First contact')
        opp2 = _opportunity(title='Second contact')

        a1 = assessment_service.get_or_create_assessment(opp1)
        a1.organisation = org
        a1.save()
        assessment_service.set_suitability_state(a1, 'suitable', actor=staff)
        a1.refresh_from_db()
        founder_review_service.record_decision(a1, 'send', actor=staff, message_version=None)

        a2 = assessment_service.get_or_create_assessment(opp2)
        a2.organisation = org
        a2.save()
        history = prior_outreach_history(a2)
        self.assertEqual(len(history), 1)
        self.assertIn('First contact', history[0])


class RolesTests(TestCase):
    def test_single_reviewer_limitation_detected(self):
        staff = _staff()
        a = assessment_service.get_or_create_assessment(_opportunity())
        record_role(a, staff, 'drafter', actor=staff)
        record_role(a, staff, 'reviewer', actor=staff)
        summary = role_summary(a)
        self.assertTrue(summary['single_reviewer_limitation'])

    def test_no_limitation_when_roles_held_by_different_people(self):
        staff1, staff2 = _staff('r1'), _staff('r2')
        a = assessment_service.get_or_create_assessment(_opportunity())
        record_role(a, staff1, 'drafter', actor=staff1)
        record_role(a, staff2, 'reviewer', actor=staff1)
        summary = role_summary(a)
        self.assertFalse(summary['single_reviewer_limitation'])


class ExternalOutreachSwitchTests(TestCase):
    def test_switch_defaults_false(self):
        self.assertFalse(settings.EXTERNAL_OUTREACH_ENABLED)


class CandidateReviewTests(TestCase):
    def test_candidate_summary_reports_not_assessed_honestly(self):
        opp = _opportunity()
        summaries = candidate_review_list([opp])
        self.assertEqual(summaries[0]['suitability_state_raw'], 'not_ready')


class CommandCentreQueuesTests(TestCase):
    def test_new_opportunity_goes_to_suitability_review_queue(self):
        opp = _opportunity()
        queues = command_centre_queues([opp])
        self.assertIn(opp, queues['needs_suitability_review'])

    def test_rejected_goes_to_rejected_queue_only(self):
        staff = _staff()
        opp = _opportunity()
        a = assessment_service.get_or_create_assessment(opp)
        assessment_service.set_suitability_state(a, 'wrong_organisation', actor=staff)
        queues = command_centre_queues([opp])
        self.assertIn(opp, queues['rejected_for_outreach'])
        self.assertNotIn(opp, queues['needs_suitability_review'])


class PilotLaunchpadIntegrationTests(TestCase):
    def test_outreach_readiness_summary_none_when_no_assessment(self):
        from good_agents.services import pilot_launchpad
        opp = _opportunity()
        self.assertIsNone(pilot_launchpad.outreach_readiness_summary(opp))

    def test_outreach_readiness_summary_present_after_assessment(self):
        from good_agents.services import pilot_launchpad
        staff = _staff()
        opp = _opportunity()
        assessment_service.get_or_create_assessment(opp)
        summary = pilot_launchpad.outreach_readiness_summary(opp)
        self.assertIsNotNone(summary)
        self.assertIn('readiness_label', summary)


class ViewPermissionAndCSRFTests(TestCase):
    def setUp(self):
        self.staff = _staff()
        self.user = _user()
        self.opportunity = _opportunity()

    def test_anonymous_redirected_from_candidate_review_list(self):
        response = self.client.get(reverse('outreach_readiness:candidate_review_list'))
        self.assertEqual(response.status_code, 302)

    def test_non_staff_user_redirected(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('outreach_readiness:candidate_review_list'))
        self.assertEqual(response.status_code, 302)

    def test_staff_gets_200_on_candidate_review_list(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('outreach_readiness:candidate_review_list'))
        self.assertEqual(response.status_code, 200)

    def test_staff_gets_200_on_assessment_detail(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('outreach_readiness:assessment_detail', args=[self.opportunity.pk]))
        self.assertEqual(response.status_code, 200)

    def test_staff_gets_200_on_founder_send_review(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('outreach_readiness:founder_send_review', args=[self.opportunity.pk]))
        self.assertEqual(response.status_code, 200)

    def test_csrf_enforced_on_suitability_post(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        response = csrf_client.post(reverse('outreach_readiness:record_suitability', args=[self.opportunity.pk]), {})
        self.assertEqual(response.status_code, 403)

    def test_csrf_enforced_on_founder_decision_post(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        response = csrf_client.post(
            reverse('outreach_readiness:record_founder_decision', args=[self.opportunity.pk]), {'decision': 'send'},
        )
        self.assertEqual(response.status_code, 403)

    def test_get_does_not_mutate_suitability(self):
        self.client.force_login(self.staff)
        self.client.get(reverse('outreach_readiness:record_suitability', args=[self.opportunity.pk]))
        a = OutreachCandidateAssessment.objects.filter(opportunity=self.opportunity).first()
        self.assertIsNone(a)

    def test_founder_decision_view_records_real_decision(self):
        a = _proceedable_assessment(self.staff, opportunity=self.opportunity)
        self.client.force_login(self.staff)
        self.client.post(
            reverse('outreach_readiness:record_founder_decision', args=[self.opportunity.pk]),
            {'decision': 'do_not_send', 'rationale': 'test'},
        )
        decision = FounderSendDecision.objects.get(assessment=a)
        self.assertEqual(decision.decision, 'do_not_send')
        self.assertEqual(decision.decided_by, self.staff)


class NoFabricatedSendStateTests(TestCase):
    """Regression guard: nothing in this app can ever mark a real send as having happened."""

    def test_message_version_model_has_no_sent_field(self):
        field_names = {f.name for f in OutreachMessageVersion._meta.get_fields()}
        self.assertNotIn('sent_at', field_names)
        self.assertNotIn('sent_status', field_names)

    def test_founder_send_decision_has_no_delivery_confirmation_field(self):
        field_names = {f.name for f in FounderSendDecision._meta.get_fields()}
        self.assertNotIn('delivered_at', field_names)
        self.assertNotIn('message_id', field_names)
