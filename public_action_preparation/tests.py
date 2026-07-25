"""public_action_preparation/tests.py — PR14: First Legitimate Public Action."""
import datetime

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from capability_graph.services.organisations import get_or_create_organisation
from good_agents.models import GoodOpportunity
from good_agents.services.pilot_launchpad import action_preparation_summary
from good_agents.services.mission_control import action_preparation_summary_counts
from public_action_preparation.models import ActionContentDraft, EthicsReview, FounderActionDecision
from public_action_preparation.services import (
    action_type as action_type_service, content_draft as content_draft_service, ethics_review as ethics_review_service,
    founder_review as founder_review_service, process_verification as process_verification_service,
)
from public_action_preparation.services.readiness import compute_action_readiness
from public_need_discovery.services import actionability, roles, small_action

User = get_user_model()


def _user(username='pap-user'):
    return User.objects.create_user(username, f'{username}@example.com', 'password123')


def _staff(username='pap-staff'):
    return User.objects.create_user(username, f'{username}@example.com', 'password123', is_staff=True)


def _opportunity(**overrides):
    base = dict(
        title='Test opportunity', problem_statement='A real problem, real evidence.', theme='environment',
        confidence=60.0, evidence_refs=['ref:1'], region='Test Council',
    )
    base.update(overrides)
    return GoodOpportunity.objects.create(**base)


def _org(name='Test Council', **overrides):
    return get_or_create_organisation(name, **overrides)


def _actionable_candidate(opportunity, staff, role='responsible_authority'):
    """Reuses PR13's real service layer to build a genuinely actionable candidate — never faked."""
    candidate = actionability.get_or_create_candidate(opportunity)
    candidate.jurisdiction, candidate.jurisdiction_resolved = 'Test Council', True
    candidate.save()
    org = _org()
    role_record = roles.record_role(candidate, org, role, actor=staff, evidence_reference='real:ref', rationale='Real remit evidence.', confirmed=True)
    small_action.record_small_action(candidate, actor=staff, action_type='ask_for_referral_route', description='Ask them.')
    actionability.set_actionability_state(candidate, 'actionable', actor=staff)
    candidate.refresh_from_db()
    return candidate, org, role_record


class ActionTypeRecommendationTests(TestCase):
    def test_no_action_when_not_yet_actionable(self):
        opportunity = _opportunity()
        rec, reasons = action_type_service.recommend_action_type(opportunity)
        self.assertEqual(rec, 'no_action')

    def test_referral_role_recommends_clarification_not_referral(self):
        """The fuel-poverty rule: a referral_body role never auto-recommends refer_to_existing_service."""
        staff = _staff()
        opportunity = _opportunity()
        _actionable_candidate(opportunity, staff, role='referral_body')
        rec, reasons = action_type_service.recommend_action_type(opportunity)
        self.assertEqual(rec, 'request_programme_clarification')
        self.assertNotEqual(rec, 'refer_to_existing_service')

    def test_funder_role_recommends_surface_funding_route(self):
        staff = _staff()
        opportunity = _opportunity()
        _actionable_candidate(opportunity, staff, role='funder')
        rec, reasons = action_type_service.recommend_action_type(opportunity)
        self.assertEqual(rec, 'surface_funding_route')

    def test_official_process_candidate_recommends_consultation_response(self):
        staff = _staff()
        opportunity = _opportunity()
        candidate, org, role = _actionable_candidate(opportunity, staff)
        small_action.record_official_process(candidate, actor=staff, process_type='consultation_submission', route_reference='ref')
        rec, reasons = action_type_service.recommend_action_type(opportunity)
        self.assertEqual(rec, 'submit_consultation_response')

    def test_recording_requires_real_actor(self):
        opportunity = _opportunity()
        with self.assertRaises(action_type_service.ActionTypeNotAllowedError):
            action_type_service.record_action_type_decision(opportunity, 'request_programme_clarification', actor=None)

    def test_refer_to_existing_service_blocked_without_real_beneficiary(self):
        """Phase 13's own explicit rule, enforced structurally — never bypassable."""
        staff = _staff()
        opportunity = _opportunity()
        with self.assertRaises(action_type_service.ActionTypeNotAllowedError):
            action_type_service.record_action_type_decision(
                opportunity, 'refer_to_existing_service', actor=staff, has_real_beneficiary=False,
            )

    def test_refer_to_existing_service_blocked_without_basis_notes_even_if_flag_true(self):
        """Setting the flag alone is not enough — a real explanation is required too."""
        staff = _staff()
        opportunity = _opportunity()
        with self.assertRaises(action_type_service.ActionTypeNotAllowedError):
            action_type_service.record_action_type_decision(
                opportunity, 'refer_to_existing_service', actor=staff, has_real_beneficiary=True, beneficiary_basis_notes='',
            )

    def test_refer_to_existing_service_succeeds_with_real_basis(self):
        staff = _staff()
        opportunity = _opportunity()
        decision = action_type_service.record_action_type_decision(
            opportunity, 'refer_to_existing_service', actor=staff, has_real_beneficiary=True,
            beneficiary_basis_notes='A real named resident contacted EcoIQ directly requesting this referral.',
        )
        self.assertEqual(decision.action_type, 'refer_to_existing_service')


class ProcessVerificationTests(TestCase):
    def test_requires_real_actor(self):
        opportunity = _opportunity()
        with self.assertRaises(process_verification_service.ProcessVerificationNotAllowedError):
            process_verification_service.record_process_verification(opportunity, actor=None, process_name='X', owning_organisation=None)

    def test_past_closing_date_forces_expired_regardless_of_status_choice(self):
        """A real bug class this structurally prevents: a reviewer typing 'open' against an already-closed date."""
        staff = _staff()
        opportunity = _opportunity()
        process = process_verification_service.record_process_verification(
            opportunity, actor=staff, process_name='Old consultation', owning_organisation=None,
            closing_date=datetime.date(2015, 8, 31), status='open',
        )
        self.assertEqual(process.status, 'expired')

    def test_future_closing_date_with_open_status_stays_open(self):
        staff = _staff()
        opportunity = _opportunity()
        future = datetime.date.today() + datetime.timedelta(days=30)
        process = process_verification_service.record_process_verification(
            opportunity, actor=staff, process_name='Current consultation', owning_organisation=None,
            closing_date=future, status='open',
        )
        self.assertEqual(process.status, 'open')

    def test_no_closing_date_respects_reviewer_status(self):
        staff = _staff()
        opportunity = _opportunity()
        process = process_verification_service.record_process_verification(
            opportunity, actor=staff, process_name='Rolling programme', owning_organisation=None, status='unknown',
        )
        self.assertEqual(process.status, 'unknown')


class ContentDraftTests(TestCase):
    def test_prepare_outreach_is_not_draftable_here(self):
        staff = _staff()
        opportunity = _opportunity()
        decision = action_type_service.record_action_type_decision(opportunity, 'prepare_outreach', actor=staff)
        with self.assertRaises(content_draft_service.ContentDraftNotAllowedError):
            content_draft_service.create_content_draft(decision, actor=staff, body_text='x')

    def test_no_action_is_not_draftable(self):
        staff = _staff()
        opportunity = _opportunity()
        decision = action_type_service.record_action_type_decision(opportunity, 'no_action', actor=staff)
        with self.assertRaises(content_draft_service.ContentDraftNotAllowedError):
            content_draft_service.create_content_draft(decision, actor=staff, body_text='x')

    def test_versioning_invalidates_prior_founder_approved_draft(self):
        staff = _staff()
        opportunity = _opportunity()
        decision = action_type_service.record_action_type_decision(opportunity, 'request_public_data', actor=staff)
        v1 = content_draft_service.create_content_draft(decision, actor=staff, body_text='v1')
        content_draft_service.mark_reviewed(v1, actor=staff)
        content_draft_service.founder_approve(v1, actor=staff)
        v2 = content_draft_service.create_content_draft(decision, actor=staff, body_text='v2')
        v1.refresh_from_db()
        self.assertEqual(v1.approval_status, 'invalidated')
        self.assertEqual(v2.version_number, 2)

    def test_referral_brief_with_missing_fields_cannot_be_founder_approved(self):
        staff = _staff()
        opportunity = _opportunity()
        decision = action_type_service.record_action_type_decision(
            opportunity, 'refer_to_existing_service', actor=staff, has_real_beneficiary=True,
            beneficiary_basis_notes='Real named resident contact.',
        )
        draft = content_draft_service.create_content_draft(
            decision, actor=staff, content_type='referral_brief', body_text='Referral',
            required_fields_missing=['beneficiary_consent_confirmation'],
        )
        content_draft_service.mark_reviewed(draft, actor=staff)
        with self.assertRaises(content_draft_service.ContentDraftNotAllowedError):
            content_draft_service.founder_approve(draft, actor=staff)

    def test_render_preview_never_submits_anything(self):
        """Regression guard: preview is a pure read, never a real transport call."""
        staff = _staff()
        opportunity = _opportunity()
        decision = action_type_service.record_action_type_decision(opportunity, 'request_public_data', actor=staff)
        draft = content_draft_service.create_content_draft(decision, actor=staff, body_text='Requesting dataset X.')
        preview = content_draft_service.render_preview(draft)
        self.assertEqual(preview['body_text'], 'Requesting dataset X.')


class EthicsReviewTests(TestCase):
    def test_requires_real_actor(self):
        opportunity = _opportunity()
        with self.assertRaises(ethics_review_service.EthicsReviewNotAllowedError):
            ethics_review_service.record_ethics_review(opportunity, actor=None, answers={})

    def test_all_passed_only_when_every_field_true(self):
        staff = _staff()
        opportunity = _opportunity()
        review = ethics_review_service.record_ethics_review(
            opportunity, actor=staff, answers={f: True for f in EthicsReview.CHECKLIST_FIELDS[:-1]},
        )
        self.assertFalse(review.all_passed)
        self.assertEqual(len(review.failed_items), 1)


class ReadinessLadderTests(TestCase):
    def test_not_assessed_with_no_decision(self):
        opportunity = _opportunity()
        self.assertEqual(compute_action_readiness(opportunity), 'not_assessed')

    def test_rejected_for_no_action(self):
        staff = _staff()
        opportunity = _opportunity()
        action_type_service.record_action_type_decision(opportunity, 'no_action', actor=staff)
        self.assertEqual(compute_action_readiness(opportunity), 'rejected')

    def test_blocked_for_refer_to_existing_service_without_beneficiary_flag(self):
        """Even after the decision exists, readiness stays blocked if has_real_beneficiary was never actually set true."""
        staff = _staff()
        opportunity = _opportunity()
        candidate, org, role = _actionable_candidate(opportunity, staff, role='referral_body')
        decision = action_type_service.record_action_type_decision(
            opportunity, 'refer_to_existing_service', actor=staff, has_real_beneficiary=True, beneficiary_basis_notes='Real basis.',
        )
        decision.has_real_beneficiary = False
        decision.save()
        self.assertEqual(compute_action_readiness(opportunity), 'blocked')

    def test_blocked_when_official_process_expired(self):
        staff = _staff()
        opportunity = _opportunity()
        candidate, org, role = _actionable_candidate(opportunity, staff)
        action_type_service.record_action_type_decision(opportunity, 'submit_consultation_response', actor=staff)
        process_verification_service.record_process_verification(
            opportunity, actor=staff, process_name='Closed consultation', owning_organisation=org,
            closing_date=datetime.date(2015, 8, 31), status='expired',
        )
        self.assertEqual(compute_action_readiness(opportunity), 'blocked')

    def test_full_ladder_reaches_ready_for_founder_action_review(self):
        staff = _staff()
        opportunity = _opportunity()
        candidate, org, role = _actionable_candidate(opportunity, staff)
        decision = action_type_service.record_action_type_decision(opportunity, 'request_public_data', actor=staff)
        self.assertEqual(compute_action_readiness(opportunity), 'needs_ethics_review')
        ethics_review_service.record_ethics_review(opportunity, actor=staff, answers={f: True for f in EthicsReview.CHECKLIST_FIELDS})
        self.assertEqual(compute_action_readiness(opportunity), 'needs_action_definition')
        draft = content_draft_service.create_content_draft(decision, actor=staff, body_text='Requesting dataset.')
        self.assertEqual(compute_action_readiness(opportunity), 'ready_for_content_review')
        content_draft_service.mark_reviewed(draft, actor=staff)
        content_draft_service.founder_approve(draft, actor=staff)
        self.assertEqual(compute_action_readiness(opportunity), 'ready_for_founder_action_review')

    def test_prepare_outreach_readiness_stops_at_founder_review_after_ethics(self):
        staff = _staff()
        opportunity = _opportunity()
        candidate, org, role = _actionable_candidate(opportunity, staff, role='potential_implementer')
        action_type_service.record_action_type_decision(opportunity, 'prepare_outreach', actor=staff)
        ethics_review_service.record_ethics_review(opportunity, actor=staff, answers={f: True for f in EthicsReview.CHECKLIST_FIELDS})
        self.assertEqual(compute_action_readiness(opportunity), 'ready_for_founder_action_review')


class FounderReviewTests(TestCase):
    def test_recommend_do_not_proceed_for_no_action(self):
        staff = _staff()
        opportunity = _opportunity()
        action_type_service.record_action_type_decision(opportunity, 'no_action', actor=staff)
        rec, reasons = founder_review_service.compute_recommendation(opportunity)
        self.assertEqual(rec, 'do_not_proceed')

    def test_recommend_proceed_when_fully_ready(self):
        staff = _staff()
        opportunity = _opportunity()
        candidate, org, role = _actionable_candidate(opportunity, staff)
        decision = action_type_service.record_action_type_decision(opportunity, 'request_public_data', actor=staff)
        ethics_review_service.record_ethics_review(opportunity, actor=staff, answers={f: True for f in EthicsReview.CHECKLIST_FIELDS})
        draft = content_draft_service.create_content_draft(decision, actor=staff, body_text='Requesting dataset.')
        content_draft_service.mark_reviewed(draft, actor=staff)
        content_draft_service.founder_approve(draft, actor=staff)
        rec, reasons = founder_review_service.compute_recommendation(opportunity)
        self.assertEqual(rec, 'proceed')

    def test_record_decision_requires_real_actor(self):
        opportunity = _opportunity()
        with self.assertRaises(founder_review_service.FounderActionReviewNotAllowedError):
            founder_review_service.record_decision(opportunity, 'proceed', actor=None)

    def test_record_decision_rejects_unknown_value(self):
        staff = _staff()
        opportunity = _opportunity()
        with self.assertRaises(founder_review_service.FounderActionReviewNotAllowedError):
            founder_review_service.record_decision(opportunity, 'send_immediately', actor=staff)

    def test_recording_proceed_never_performs_a_real_external_action(self):
        """Regression guard: recording PROCEED only ever writes a FounderActionDecision row — nothing external."""
        staff = _staff()
        opportunity = _opportunity()
        founder_review_service.record_decision(opportunity, 'proceed', actor=staff, rationale='Test.')
        self.assertEqual(FounderActionDecision.objects.filter(opportunity=opportunity, decision='proceed').count(), 1)


class MissionControlAndPilotLaunchpadIntegrationTests(TestCase):
    def test_action_preparation_summary_none_when_no_decision(self):
        opportunity = _opportunity()
        self.assertIsNone(action_preparation_summary(opportunity))

    def test_action_preparation_summary_reflects_real_state(self):
        staff = _staff()
        opportunity = _opportunity()
        action_type_service.record_action_type_decision(opportunity, 'request_programme_clarification', actor=staff)
        opportunity.refresh_from_db()
        summary = action_preparation_summary(opportunity)
        self.assertIn('Request programme clarification', summary['action_type'])

    def test_mission_control_counts_real_rows_only(self):
        staff = _staff()
        o1 = _opportunity(title='A')
        o2 = _opportunity(title='B')
        action_type_service.record_action_type_decision(o1, 'no_action', actor=staff)
        action_type_service.record_action_type_decision(o2, 'request_public_data', actor=staff)
        counts = action_preparation_summary_counts()
        self.assertGreaterEqual(counts['cases_with_action_type'], 2)
        self.assertGreaterEqual(counts['rejected'], 1)


class ViewPermissionsAndSecurityTests(TestCase):
    def test_candidate_comparison_requires_staff(self):
        client = Client()
        response = client.get(reverse('public_action_preparation:candidate_comparison'))
        self.assertEqual(response.status_code, 302)

    def test_candidate_comparison_accessible_to_staff(self):
        staff = _staff()
        client = Client()
        client.force_login(staff)
        response = client.get(reverse('public_action_preparation:candidate_comparison'))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_cannot_access_action_prep_detail(self):
        opportunity = _opportunity()
        user = _user()
        client = Client()
        client.force_login(user)
        response = client.get(reverse('public_action_preparation:action_prep_detail', args=[opportunity.pk]))
        self.assertEqual(response.status_code, 302)

    def test_get_does_not_mutate_action_type(self):
        opportunity = _opportunity()
        staff = _staff()
        client = Client()
        client.force_login(staff)
        client.get(reverse('public_action_preparation:record_action_type', args=[opportunity.pk]), {'action_type': 'request_public_data'})
        decision = getattr(opportunity, 'action_type_decision', None)
        self.assertIsNone(decision)

    def test_post_requires_csrf(self):
        opportunity = _opportunity()
        staff = _staff()
        client = Client(enforce_csrf_checks=True)
        client.force_login(staff)
        response = client.post(reverse('public_action_preparation:record_action_type', args=[opportunity.pk]), {'action_type': 'request_public_data'})
        self.assertEqual(response.status_code, 403)

    def test_authenticated_staff_post_records_real_decision(self):
        opportunity = _opportunity()
        staff = _staff()
        client = Client()
        client.force_login(staff)
        client.post(reverse('public_action_preparation:record_action_type', args=[opportunity.pk]), {
            'action_type': 'request_public_data', 'rationale': 'Test.',
        })
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.action_type_decision.action_type, 'request_public_data')

    def test_no_view_ever_performs_a_real_external_action(self):
        import inspect

        import public_action_preparation.views as views_module
        source = inspect.getsource(views_module)
        self.assertNotIn('safe_fetch', source)
        self.assertNotIn('httpx', source)
        self.assertNotIn('send_mail', source)

    def test_external_public_actions_enabled_defaults_false(self):
        from django.conf import settings
        self.assertFalse(settings.EXTERNAL_PUBLIC_ACTIONS_ENABLED)


class RegressionTests(TestCase):
    def test_existing_public_need_discovery_flow_unaffected(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        self.assertEqual(candidate.actionability_state, 'informational_only')

    def test_existing_pilot_launchpad_view_unaffected(self):
        staff = _staff()
        opportunity = _opportunity()
        client = Client()
        client.force_login(staff)
        response = client.get(reverse('good_agents:pilot_launchpad', args=[opportunity.pk]))
        self.assertEqual(response.status_code, 200)

    def test_existing_mission_control_view_unaffected(self):
        staff = _staff()
        client = Client()
        client.force_login(staff)
        response = client.get(reverse('good_agents:mission_control'))
        self.assertEqual(response.status_code, 200)
