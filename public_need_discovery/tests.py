"""public_need_discovery/tests.py — PR13: Actionable Public-Need Discovery."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from capability_graph.services.organisations import get_or_create_organisation
from good_agents.models import GoodDiscoveryRun, GoodOpportunity, SignalProvider, WorldSignal
from good_agents.services import mission_control
from good_agents.services.pilot_launchpad import actionability_summary
from good_agents.services.provider_adapters import PROVIDER_ADAPTERS
from outreach_readiness.models import OutreachCandidateAssessment
from public_need_discovery.models import (
    ACTIONABILITY_TERMINAL_REJECTED_STATES, CandidateOrganisationRole, PilotCandidateAssessment, ProviderRunMetrics,
)
from public_need_discovery.services import actionability, jurisdiction, qualification, roles, sensitivity, small_action
from public_need_discovery.services.provider_metrics import record_run_metrics

User = get_user_model()


def _user(username='pnd-user'):
    return User.objects.create_user(username, f'{username}@example.com', 'password123')


def _staff(username='pnd-staff'):
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


def _signal(**overrides):
    base = dict(
        signal_type='public_need', title='Test signal', summary='A real need.', publisher='Test Council',
        region='Test Council', source_url='https://example.gov.uk/x', raw_evidence_ref='test:1',
    )
    base.update(overrides)
    return WorldSignal.objects.create(**base)


class JurisdictionResolutionTests(TestCase):
    def test_resolves_from_opportunity_region(self):
        opportunity = _opportunity(region='Leicester City Council')
        value, resolved, notes = jurisdiction.resolve_jurisdiction(opportunity)
        self.assertEqual(value, 'Leicester City Council')
        self.assertTrue(resolved)

    def test_resolves_from_known_publisher_when_no_region(self):
        opportunity = _opportunity(region='', detected_signals=['Sig'])
        _signal(title='Sig', publisher='UK Environment Agency', region='')
        value, resolved, notes = jurisdiction.resolve_jurisdiction(opportunity)
        self.assertEqual(value, 'England')
        self.assertTrue(resolved)

    def test_unresolved_for_unknown_publisher_never_guesses(self):
        opportunity = _opportunity(region='', detected_signals=['Sig'])
        _signal(title='Sig', publisher='Some Unknown Org', region='')
        value, resolved, notes = jurisdiction.resolve_jurisdiction(opportunity)
        self.assertEqual(value, jurisdiction.NO_JURISDICTION)
        self.assertFalse(resolved)

    def test_unresolved_with_no_signal_at_all(self):
        opportunity = _opportunity(region='', detected_signals=[])
        value, resolved, notes = jurisdiction.resolve_jurisdiction(opportunity)
        self.assertEqual(value, jurisdiction.NO_JURISDICTION)
        self.assertFalse(resolved)


class OrganisationRoleTests(TestCase):
    def test_record_role_is_idempotent_per_candidate_org_role(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        org = _org()
        r1 = roles.record_role(candidate, org, 'responsible_authority', actor=None, rationale='first')
        r2 = roles.record_role(candidate, org, 'responsible_authority', actor=None, rationale='second')
        self.assertEqual(r1.pk, r2.pk)
        self.assertEqual(CandidateOrganisationRole.objects.filter(candidate=candidate, organisation=org).count(), 1)
        r2.refresh_from_db()
        self.assertEqual(r2.rationale, 'second')

    def test_confirming_a_role_requires_real_actor(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        org = _org()
        with self.assertRaises(roles.RoleNotAllowedError):
            roles.record_role(candidate, org, 'funder', actor=None, confirmed=True)

    def test_evidence_publisher_alone_never_justifies_actionability(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        org = _org()
        staff = _staff()
        roles.record_role(candidate, org, 'evidence_publisher', actor=staff, confirmed=True)
        self.assertFalse(roles.has_confirmed_justifying_role(candidate))

    def test_jurisdiction_authority_alone_never_justifies_actionability(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        org = _org()
        staff = _staff()
        roles.record_role(candidate, org, 'jurisdiction_authority', actor=staff, confirmed=True)
        self.assertFalse(roles.has_confirmed_justifying_role(candidate))

    def test_responsible_authority_confirmed_justifies_actionability(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        org = _org()
        staff = _staff()
        roles.record_role(candidate, org, 'responsible_authority', actor=staff, confirmed=True)
        self.assertTrue(roles.has_confirmed_justifying_role(candidate))

    def test_unconfirmed_role_does_not_justify_actionability(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        org = _org()
        roles.record_role(candidate, org, 'responsible_authority', actor=None, confirmed=False)
        self.assertFalse(roles.has_confirmed_justifying_role(candidate))

    def test_same_org_can_hold_multiple_independent_roles(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        org = _org()
        staff = _staff()
        roles.record_role(candidate, org, 'jurisdiction_authority', actor=staff, confirmed=True)
        roles.record_role(candidate, org, 'responsible_authority', actor=staff, confirmed=True)
        self.assertEqual(candidate.organisation_roles.filter(organisation=org).count(), 2)

    def test_suggest_roles_from_capability_graph_creates_evidence_publisher_from_responsible_party(self):
        from good_agents.models import ResponsibleParty
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        org = _org()
        ResponsibleParty.objects.create(opportunity=opportunity, name=org.name, party_type='other', organisation=org, evidence_ref='ref')
        suggestions = roles.suggest_roles_from_capability_graph(candidate)
        self.assertTrue(any(s.role == 'evidence_publisher' and not s.confirmed for s in suggestions))

    def test_suggest_roles_maps_capability_to_role_deterministically(self):
        from good_agents.models import ResponsibleParty
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        org = _org()
        ResponsibleParty.objects.create(opportunity=opportunity, name=org.name, party_type='regulator', organisation=org)
        org.capabilities.create(capability='regulate', verification_state='documented', evidence_source='real-source')
        suggestions = roles.suggest_roles_from_capability_graph(candidate)
        self.assertTrue(any(s.role == 'responsible_authority' for s in suggestions))

    def test_disputed_capability_never_suggests_a_role(self):
        from good_agents.models import ResponsibleParty
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        org = _org()
        ResponsibleParty.objects.create(opportunity=opportunity, name=org.name, party_type='regulator', organisation=org)
        org.capabilities.create(capability='regulate', verification_state='disputed', evidence_source='real-source')
        suggestions = roles.suggest_roles_from_capability_graph(candidate)
        self.assertFalse(any(s.role == 'responsible_authority' for s in suggestions))


class ActionabilityGateTests(TestCase):
    def test_insufficient_evidence_when_no_evidence_refs(self):
        opportunity = _opportunity(evidence_refs=[])
        candidate = actionability.get_or_create_candidate(opportunity)
        state, reasons = actionability.evaluate_candidate(candidate)
        self.assertEqual(state, 'insufficient_evidence')

    def test_no_responsible_body_when_no_jurisdiction_and_no_roles(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        state, reasons = actionability.evaluate_candidate(candidate)
        self.assertIn(state, ('potentially_actionable', 'no_responsible_body_identified'))

    def test_wrong_recipient_when_only_evidence_publisher_confirmed(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        candidate.jurisdiction, candidate.jurisdiction_resolved = 'Test', True
        candidate.save()
        org = _org()
        staff = _staff()
        roles.record_role(candidate, org, 'evidence_publisher', actor=staff, confirmed=True)
        state, reasons = actionability.evaluate_candidate(candidate)
        self.assertEqual(state, 'wrong_recipient')

    def test_no_clear_action_when_role_confirmed_but_no_action(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        candidate.jurisdiction, candidate.jurisdiction_resolved = 'Test', True
        candidate.save()
        org = _org()
        staff = _staff()
        roles.record_role(candidate, org, 'responsible_authority', actor=staff, confirmed=True)
        state, reasons = actionability.evaluate_candidate(candidate)
        self.assertEqual(state, 'no_clear_action')

    def test_sensitive_review_required_blocks_even_when_everything_else_passes(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        candidate.jurisdiction, candidate.jurisdiction_resolved = 'Test', True
        candidate.suggested_action_type = 'ask_for_referral_route'
        candidate.suggested_action_description = 'Ask them.'
        candidate.evidence_valid_but_outreach_inappropriate = True
        candidate.save()
        org = _org()
        staff = _staff()
        roles.record_role(candidate, org, 'responsible_authority', actor=staff, confirmed=True)
        state, reasons = actionability.evaluate_candidate(candidate)
        self.assertEqual(state, 'sensitive_review_required')

    def test_actionable_when_all_real_criteria_pass(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        candidate.jurisdiction, candidate.jurisdiction_resolved = 'Test', True
        candidate.suggested_action_type = 'ask_for_referral_route'
        candidate.suggested_action_description = 'Ask them.'
        candidate.save()
        org = _org()
        staff = _staff()
        roles.record_role(candidate, org, 'responsible_authority', actor=staff, confirmed=True)
        state, reasons = actionability.evaluate_candidate(candidate)
        self.assertEqual(state, 'actionable')

    def test_set_actionability_state_requires_real_actor(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        with self.assertRaises(actionability.ActionabilityNotAllowedError):
            actionability.set_actionability_state(candidate, 'actionable', actor=None)

    def test_blockers_lists_every_unmet_criterion(self):
        opportunity = _opportunity(evidence_refs=[])
        candidate = actionability.get_or_create_candidate(opportunity)
        codes = {b['code'] for b in actionability.blockers(candidate)}
        self.assertIn('INSUFFICIENT_EVIDENCE', codes)
        self.assertIn('NO_JURISDICTION', codes)
        self.assertIn('NO_RESPONSIBLE_BODY_CONFIRMED', codes)
        self.assertIn('NO_CLEAR_ACTION', codes)

    def test_rejected_terminal_state_shows_as_blocker(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        staff = _staff()
        actionability.set_actionability_state(candidate, 'no_clear_action', actor=staff)
        codes = {b['code'] for b in actionability.blockers(candidate)}
        self.assertIn('REJECTED', codes)
        self.assertTrue(candidate.is_rejected)


class SmallActionAndOfficialProcessTests(TestCase):
    def test_record_small_action_requires_description(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        staff = _staff()
        with self.assertRaises(small_action.SmallActionNotAllowedError):
            small_action.record_small_action(candidate, actor=staff, action_type='ask_for_referral_route', description='')

    def test_record_small_action_requires_real_actor(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        with self.assertRaises(small_action.SmallActionNotAllowedError):
            small_action.record_small_action(candidate, actor=None, action_type='ask_for_referral_route', description='Ask.')

    def test_official_process_preference_over_outreach(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        staff = _staff()
        small_action.record_official_process(
            candidate, actor=staff, process_type='consultation_submission', route_reference='https://example.gov.uk/consult',
        )
        candidate.refresh_from_db()
        self.assertTrue(candidate.use_official_process)
        self.assertEqual(candidate.official_process_type, 'consultation_submission')

    def test_suggest_action_returns_none_for_unmapped_class(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        action_type, process_type = small_action.suggest_action(candidate)
        self.assertIsNone(action_type)
        self.assertIsNone(process_type)

    def test_suggest_action_maps_public_consultation_class(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        candidate.actionability_class = 'public_consultation'
        candidate.save()
        action_type, process_type = small_action.suggest_action(candidate)
        self.assertEqual(action_type, 'submit_evidence_to_consultation')
        self.assertEqual(process_type, 'consultation_submission')


class SensitivityGateTests(TestCase):
    def test_outreach_inappropriate_forces_sensitive_review_required_state(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        staff = _staff()
        sensitivity.record_sensitivity_review(candidate, actor=staff, categories=['children'], outreach_inappropriate=True)
        candidate.refresh_from_db()
        self.assertEqual(candidate.actionability_state, 'sensitive_review_required')
        self.assertTrue(candidate.evidence_valid_but_outreach_inappropriate)

    def test_marking_sensitive_alone_does_not_block(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        staff = _staff()
        sensitivity.record_sensitivity_review(candidate, actor=staff, categories=['health'], outreach_inappropriate=False)
        candidate.refresh_from_db()
        self.assertTrue(candidate.is_sensitive)
        self.assertNotEqual(candidate.actionability_state, 'sensitive_review_required')

    def test_sensitivity_review_requires_real_actor(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        with self.assertRaises(sensitivity.SensitivityReviewNotAllowedError):
            sensitivity.record_sensitivity_review(candidate, actor=None, categories=[])

    def test_suggest_sensitivity_categories_keyword_match(self):
        opportunity = _opportunity(title='Major earthquake response', problem_statement='A significant earthquake hit the region.')
        categories = sensitivity.suggest_sensitivity_categories(opportunity)
        self.assertIn('disaster', categories)

    def test_suggest_sensitivity_categories_empty_for_routine_case(self):
        opportunity = _opportunity(title='Local Plan Consultation', problem_statement='Routine planning policy update.')
        categories = sensitivity.suggest_sensitivity_categories(opportunity)
        self.assertEqual(categories, [])


class QualificationAndPromotionTests(TestCase):
    def test_discovery_qualified_reflects_evidence_and_status(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        self.assertTrue(qualification.recompute_discovery_qualified(candidate))

    def test_discovery_not_qualified_when_insufficient_evidence(self):
        opportunity = _opportunity(insufficient_evidence=True)
        candidate = actionability.get_or_create_candidate(opportunity)
        self.assertFalse(qualification.recompute_discovery_qualified(candidate))

    def test_actionability_qualified_only_when_proceedable_state(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        self.assertFalse(qualification.recompute_actionability_qualified(candidate))
        staff = _staff()
        actionability.set_actionability_state(candidate, 'actionable', actor=staff)
        self.assertTrue(qualification.recompute_actionability_qualified(candidate))

    def _actionable_candidate_with_role(self, *, official_process=False):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        staff = _staff()
        org = _org()
        role = roles.record_role(candidate, org, 'responsible_authority', actor=staff, confirmed=True)
        if official_process:
            small_action.record_official_process(candidate, actor=staff, process_type='consultation_submission', route_reference='ref')
        else:
            small_action.record_small_action(candidate, actor=staff, action_type='ask_for_referral_route', description='Ask.')
        actionability.set_actionability_state(candidate, 'actionable', actor=staff, rationale='test')
        candidate.refresh_from_db()
        return candidate, role, staff

    def test_promotion_requires_real_actor(self):
        candidate, role, staff = self._actionable_candidate_with_role()
        with self.assertRaises(qualification.QualificationNotAllowedError):
            qualification.promote_to_outreach_readiness(candidate, actor=None, organisation_role=role)

    def test_promotion_blocked_when_not_actionable(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        staff = _staff()
        org = _org()
        role = roles.record_role(candidate, org, 'responsible_authority', actor=staff, confirmed=True)
        with self.assertRaises(qualification.QualificationNotAllowedError):
            qualification.promote_to_outreach_readiness(candidate, actor=staff, organisation_role=role)

    def test_promotion_blocked_when_use_official_process(self):
        candidate, role, staff = self._actionable_candidate_with_role(official_process=True)
        with self.assertRaises(qualification.QualificationNotAllowedError):
            qualification.promote_to_outreach_readiness(candidate, actor=staff, organisation_role=role)

    def test_promotion_blocked_with_unconfirmed_role(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        staff = _staff()
        org = _org()
        role = roles.record_role(candidate, org, 'responsible_authority', actor=None, confirmed=False)
        small_action.record_small_action(candidate, actor=staff, action_type='ask_for_referral_route', description='Ask.')
        actionability.set_actionability_state(candidate, 'actionable', actor=staff)
        candidate.refresh_from_db()
        with self.assertRaises(qualification.QualificationNotAllowedError):
            qualification.promote_to_outreach_readiness(candidate, actor=staff, organisation_role=role)

    def test_promotion_succeeds_and_prefills_outreach_assessment(self):
        candidate, role, staff = self._actionable_candidate_with_role()
        assessment = qualification.promote_to_outreach_readiness(candidate, actor=staff, organisation_role=role)
        self.assertIsInstance(assessment, OutreachCandidateAssessment)
        self.assertEqual(assessment.recipient_role, 'responsible_authority')
        self.assertEqual(assessment.organisation_id, role.organisation_id)
        # Promotion never sets suitability itself — PR12's own gate still applies untouched.
        self.assertEqual(assessment.suitability_state, 'not_ready')
        candidate.refresh_from_db()
        self.assertTrue(candidate.outreach_suitable)

    def test_promotion_never_auto_confirms_remit_beyond_what_was_already_true(self):
        """A promoted role that was never independently remit-checked stays honestly unconfirmed downstream."""
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        staff = _staff()
        org = _org()
        role = roles.record_role(candidate, org, 'responsible_authority', actor=staff, confirmed=True, rationale='')
        small_action.record_small_action(candidate, actor=staff, action_type='ask_for_referral_route', description='Ask.')
        actionability.set_actionability_state(candidate, 'actionable', actor=staff)
        candidate.refresh_from_db()
        assessment = qualification.promote_to_outreach_readiness(candidate, actor=staff, organisation_role=role)
        self.assertEqual(assessment.remit_rationale, '')


class ProviderMetricsTests(TestCase):
    def test_new_providers_are_registered(self):
        self.assertIn('govuk-consultations', PROVIDER_ADAPTERS)
        self.assertIn('data-gov-uk-datasets', PROVIDER_ADAPTERS)

    def test_record_run_metrics_creates_one_row_per_provider_report(self):
        provider = SignalProvider.objects.create(slug='govuk-consultations', name='Test', status='active')
        run = GoodDiscoveryRun.objects.create(mission='Test mission')
        reports = [{'slug': 'govuk-consultations', 'name': 'Test', 'success': True, 'error': '', 'items_fetched': 5, 'items_after_validation': 4}]
        rows = record_run_metrics(run, reports)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].records_fetched, 5)
        self.assertEqual(rows[0].duplicates, 1)
        self.assertEqual(rows[0].errors, 0)

    def test_record_run_metrics_is_idempotent_per_provider_run(self):
        provider = SignalProvider.objects.create(slug='govuk-consultations', name='Test', status='active')
        run = GoodDiscoveryRun.objects.create(mission='Test mission')
        reports = [{'slug': 'govuk-consultations', 'name': 'Test', 'success': True, 'error': '', 'items_fetched': 5, 'items_after_validation': 4}]
        record_run_metrics(run, reports)
        record_run_metrics(run, reports)
        self.assertEqual(ProviderRunMetrics.objects.filter(provider=provider, run=run).count(), 1)

    def test_unknown_provider_slug_in_report_is_skipped_not_crashed(self):
        run = GoodDiscoveryRun.objects.create(mission='Test mission')
        reports = [{'slug': 'nonexistent-provider', 'name': 'X', 'success': False, 'error': 'nope', 'items_fetched': 0, 'items_after_validation': 0}]
        rows = record_run_metrics(run, reports)
        self.assertEqual(rows, [])


class MissionControlAndPilotLaunchpadIntegrationTests(TestCase):
    def test_actionability_summary_none_when_no_candidate(self):
        opportunity = _opportunity()
        self.assertIsNone(actionability_summary(opportunity))

    def test_actionability_summary_reflects_real_state(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        staff = _staff()
        actionability.set_actionability_state(candidate, 'actionable', actor=staff)
        opportunity.refresh_from_db()
        summary = actionability_summary(opportunity)
        self.assertEqual(summary['actionability_state_raw'], 'actionable')

    def test_mission_control_actionable_discovery_summary_counts_real_rows(self):
        o1 = _opportunity(title='A')
        o2 = _opportunity(title='B')
        staff = _staff()
        c1 = actionability.get_or_create_candidate(o1)
        actionability.set_actionability_state(c1, 'actionable', actor=staff)
        c2 = actionability.get_or_create_candidate(o2)
        actionability.set_actionability_state(c2, 'no_clear_action', actor=staff)
        summary = mission_control.actionable_discovery_summary()
        self.assertGreaterEqual(summary['sensitive_or_rejected'], 1)


class ViewPermissionsAndSecurityTests(TestCase):
    def test_candidate_queue_requires_staff(self):
        client = Client()
        response = client.get(reverse('public_need_discovery:candidate_queue'))
        self.assertEqual(response.status_code, 302)

    def test_candidate_queue_accessible_to_staff(self):
        staff = _staff()
        client = Client()
        client.force_login(staff)
        response = client.get(reverse('public_need_discovery:candidate_queue'))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_user_cannot_access_candidate_detail(self):
        opportunity = _opportunity()
        user = _user()
        client = Client()
        client.force_login(user)
        response = client.get(reverse('public_need_discovery:candidate_detail', args=[opportunity.pk]))
        self.assertEqual(response.status_code, 302)

    def test_set_actionability_state_get_does_not_mutate(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        staff = _staff()
        client = Client()
        client.force_login(staff)
        client.get(reverse('public_need_discovery:set_actionability_state', args=[opportunity.pk]), {'actionability_state': 'actionable'})
        candidate.refresh_from_db()
        self.assertEqual(candidate.actionability_state, 'informational_only')

    def test_set_actionability_state_post_requires_csrf(self):
        opportunity = _opportunity()
        staff = _staff()
        client = Client(enforce_csrf_checks=True)
        client.force_login(staff)
        response = client.post(reverse('public_need_discovery:set_actionability_state', args=[opportunity.pk]), {'actionability_state': 'actionable'})
        self.assertEqual(response.status_code, 403)

    def test_post_updates_via_authenticated_staff_client(self):
        opportunity = _opportunity()
        candidate = actionability.get_or_create_candidate(opportunity)
        staff = _staff()
        client = Client()
        client.force_login(staff)
        client.post(reverse('public_need_discovery:set_actionability_state', args=[opportunity.pk]), {
            'actionability_state': 'potentially_actionable', 'actionability_class': 'public_need',
            'capital_required_now': 'no',
        })
        candidate.refresh_from_db()
        self.assertEqual(candidate.actionability_state, 'potentially_actionable')

    def test_promote_view_reports_error_without_crashing_when_no_role_selected(self):
        opportunity = _opportunity()
        staff = _staff()
        client = Client()
        client.force_login(staff)
        response = client.post(reverse('public_need_discovery:promote_to_outreach_readiness', args=[opportunity.pk]), {'organisation_role_pk': '99999'})
        self.assertEqual(response.status_code, 302)

    def test_no_view_ever_performs_a_real_external_action(self):
        """Regression guard: no view in this app imports safe_fetch/httpx — this app only reads/writes local rows."""
        import inspect

        import public_need_discovery.views as views_module
        source = inspect.getsource(views_module)
        self.assertNotIn('safe_fetch', source)
        self.assertNotIn('httpx', source)
        self.assertNotIn('send_mail', source)


class RegressionTests(TestCase):
    def test_existing_outreach_readiness_flow_unaffected_by_new_app(self):
        """PR12's own suite covers this fully — this is a light smoke check that installing PR13 doesn't break it."""
        opportunity = _opportunity()
        from outreach_readiness.services.assessment import get_or_create_assessment
        assessment = get_or_create_assessment(opportunity)
        self.assertEqual(assessment.suitability_state, 'not_ready')

    def test_existing_pilot_launchpad_view_unaffected(self):
        opportunity = _opportunity()
        staff = _staff()
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
