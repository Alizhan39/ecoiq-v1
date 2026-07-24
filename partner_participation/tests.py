"""
partner_participation/tests.py — PR8: consented organisation
participation. Covers: claims/rejection, role permissions, cross-org
isolation, capability declarations (self-declared vs verified), evidence,
opportunity preferences/acceptance modes, routing requirements, public
route history, resource/funding declarations (incl. Sharia flag),
participation verification, incoming routing candidates, consent states,
routing ranking/explanation, conflicting evidence, staleness/
reconfirmation, Mission Control integration, notifications, privacy, and
no-fake-accepted-state guarantees.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from capability_graph.models import CapabilityConflict, OrganisationCapability
from capability_graph.services.capabilities import record_capability, verify_capability
from capability_graph.services.organisations import get_or_create_organisation
from good_agents.models import GoodOpportunity
from good_agents.services import mission_control
from partner_participation.models import (
    FundingProgrammeDeclaration, OpportunityPreference, OrganisationMembership, RoutingCandidate,
)
from partner_participation.services import (
    capability_declarations, conflicts as conflicts_service, funding_declarations, membership,
    opportunity_preferences, routing, staleness,
)
from partner_participation.services.notify import _already_notified


def _user(username='user1', **kwargs):
    User = get_user_model()
    return User.objects.create_user(username, f'{username}@example.com', 'pw', **kwargs)


def _staff(username='staff1'):
    return _user(username, is_staff=True)


def _verified_member(org, user, role='editor'):
    m = membership.request_membership(org, user, role=role)
    return membership.review_membership(m, decision='verified_member', actor=_staff('reviewer-' + user.username))


def _opportunity(**overrides):
    base = dict(title='PR8 test opportunity', problem_statement='x', theme='poverty', confidence=60.0)
    base.update(overrides)
    return GoodOpportunity.objects.create(**base)


class MembershipClaimTests(TestCase):
    def test_claim_starts_at_claim_requested_never_higher(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = membership.request_membership(org, user, role='admin')
        self.assertEqual(m.status, 'claim_requested')

    def test_duplicate_claim_rejected(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        membership.request_membership(org, user)
        with self.assertRaises(membership.AlreadyMemberError):
            membership.request_membership(org, user)

    def test_review_requires_staff_actor(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = membership.request_membership(org, user)
        with self.assertRaises(membership.ReviewNotAllowedError):
            membership.review_membership(m, decision='verified_member', actor=user)

    def test_review_approve(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = membership.request_membership(org, user)
        m = membership.review_membership(m, decision='verified_member', actor=_staff())
        self.assertEqual(m.status, 'verified_member')
        self.assertIsNotNone(m.reviewed_at)

    def test_review_reject(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = membership.request_membership(org, user)
        m = membership.review_membership(m, decision='rejected', actor=_staff())
        self.assertEqual(m.status, 'rejected')

    def test_review_invalid_decision_raises(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = membership.request_membership(org, user)
        with self.assertRaises(ValueError):
            membership.review_membership(m, decision='verified', actor=_staff())

    def test_suspend_requires_staff(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        with self.assertRaises(membership.ReviewNotAllowedError):
            membership.suspend_membership(m, actor=user)
        m = membership.suspend_membership(m, actor=_staff())
        self.assertEqual(m.status, 'suspended')


class RolePermissionTests(TestCase):
    def test_unverified_member_cannot_edit(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        membership.request_membership(org, user, role='admin')  # still claim_requested
        self.assertFalse(membership.can_edit(org, user))

    def test_viewer_cannot_edit(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        _verified_member(org, user, role='viewer')
        self.assertFalse(membership.can_edit(org, user))

    def test_editor_can_edit(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        _verified_member(org, user, role='editor')
        self.assertTrue(membership.can_edit(org, user))

    def test_only_admin_can_manage_critical(self):
        org = get_or_create_organisation('Org A')
        editor = _user('editor1')
        admin = _user('admin1')
        _verified_member(org, editor, role='editor')
        _verified_member(org, admin, role='admin')
        self.assertFalse(membership.can_manage_critical(org, editor))
        self.assertTrue(membership.can_manage_critical(org, admin))

    def test_anonymous_has_no_role(self):
        org = get_or_create_organisation('Org A')
        self.assertIsNone(membership.user_role_for_organisation(org, None))


class CrossOrganisationIsolationTests(TestCase):
    def test_member_of_org_a_cannot_edit_org_b(self):
        org_a = get_or_create_organisation('Org A')
        org_b = get_or_create_organisation('Org B')
        user = _user()
        _verified_member(org_a, user, role='admin')
        self.assertTrue(membership.can_edit(org_a, user))
        self.assertFalse(membership.can_edit(org_b, user))

    def test_portal_view_403_for_non_member(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        self.client.force_login(user)
        response = self.client.get(reverse('partner_participation:organisation_portal', args=[org.pk]))
        self.assertEqual(response.status_code, 403)

    def test_portal_view_403_for_anonymous(self):
        org = get_or_create_organisation('Org A')
        response = self.client.get(reverse('partner_participation:organisation_portal', args=[org.pk]))
        self.assertEqual(response.status_code, 302)  # login redirect

    def test_editor_only_view_403_for_viewer(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        _verified_member(org, user, role='viewer')
        self.client.force_login(user)
        response = self.client.post(reverse('partner_participation:declare_capability', args=[org.pk]), {'capability': 'fund'})
        self.assertEqual(response.status_code, 403)


class CapabilityDeclarationTests(TestCase):
    def test_declare_capability_requires_editor_role(self):
        org = get_or_create_organisation('Org A')
        viewer_user = _user()
        m = _verified_member(org, viewer_user, role='viewer')
        with self.assertRaises(capability_declarations.NotAuthorisedError):
            capability_declarations.declare_capability(org, 'fund', m)

    def test_declare_capability_starts_self_reported_organisation_declared(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        edge = capability_declarations.declare_capability(org, 'fund', m, jurisdiction='England')
        self.assertEqual(edge.verification_state, 'self_reported')
        self.assertEqual(edge.provenance, 'organisation_declared')
        self.assertEqual(edge.declared_by_id, user.pk)
        # Attributable even with no external evidence — never a blank evidence_source.
        self.assertTrue(edge.evidence_source)

    def test_attach_evidence_moves_to_evidence_supported_never_higher(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        edge = capability_declarations.declare_capability(org, 'fund', m)
        edge = capability_declarations.attach_evidence(edge, evidence_url='https://example.org/x', actor=user)
        self.assertEqual(edge.verification_state, 'evidence_supported')
        self.assertNotEqual(edge.verification_state, 'independently_verified')

    def test_attach_evidence_requires_url(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        edge = capability_declarations.declare_capability(org, 'fund', m)
        with self.assertRaises(ValueError):
            capability_declarations.attach_evidence(edge, evidence_url='', actor=user)

    def test_human_review_requires_staff(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        edge = capability_declarations.declare_capability(org, 'fund', m)
        with self.assertRaises(membership.ReviewNotAllowedError):
            capability_declarations.human_review(edge, actor=user)
        edge = capability_declarations.human_review(edge, actor=_staff())
        self.assertEqual(edge.verification_state, 'human_reviewed')

    def test_self_declared_never_displayed_as_independently_verified(self):
        """The core Phase 5 guarantee: a bare declaration with no evidence never reaches independently_verified on its own."""
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        edge = capability_declarations.declare_capability(org, 'fund', m)
        self.assertNotEqual(edge.verification_state, 'independently_verified')
        # Only verify_capability(), with a real actor, can promote it.
        edge = verify_capability(edge, actor=_staff())
        self.assertEqual(edge.verification_state, 'independently_verified')

    def test_dispute_and_expire(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        edge = capability_declarations.declare_capability(org, 'fund', m)
        conflict = capability_declarations.dispute(edge, reason='Conflicts with external evidence.')
        edge.refresh_from_db()
        self.assertEqual(edge.verification_state, 'disputed')
        self.assertIsInstance(conflict, CapabilityConflict)
        edge = capability_declarations.expire(edge)
        self.assertEqual(edge.verification_state, 'expired')


class OpportunityPreferenceTests(TestCase):
    def test_set_preference_requires_editor(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user, role='viewer')
        with self.assertRaises(opportunity_preferences.NotAuthorisedError):
            opportunity_preferences.set_preference(org, 'poverty', m)

    def test_set_preference_is_never_a_guarantee_field(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        pref = opportunity_preferences.set_preference(org, 'poverty', m, acceptance_mode='open_to_relevant_opportunities')
        self.assertEqual(pref.acceptance_mode, 'open_to_relevant_opportunities')

    def test_re_setting_same_theme_updates_not_duplicates(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        opportunity_preferences.set_preference(org, 'poverty', m, acceptance_mode='limited')
        opportunity_preferences.set_preference(org, 'poverty', m, acceptance_mode='not_accepting')
        self.assertEqual(OpportunityPreference.objects.filter(organisation=org, theme='poverty').count(), 1)
        self.assertEqual(OpportunityPreference.objects.get(organisation=org, theme='poverty').acceptance_mode, 'not_accepting')

    def test_routing_requirements_stored_honestly(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        pref = opportunity_preferences.set_preference(
            org, 'financial_inclusion', m, requires_sharia_review=True, min_project_size_usd=1000.0,
        )
        self.assertTrue(pref.requires_sharia_review)
        self.assertEqual(pref.min_project_size_usd, 1000.0)
        self.assertIsNone(pref.max_project_size_usd)  # never invented


class FundingDeclarationTests(TestCase):
    def test_declare_programme_requires_editor(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user, role='viewer')
        with self.assertRaises(funding_declarations.NotAuthorisedError):
            funding_declarations.declare_programme(org, 'Test Programme', 'grant', m)

    def test_sharia_sensitive_funder_type_forces_flag(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        decl = funding_declarations.declare_programme(org, 'Waqf Fund', 'waqf', m)
        self.assertTrue(decl.requires_sharia_review)

    def test_never_claims_halal_only_flags_review(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        decl = funding_declarations.declare_programme(org, 'Grant Programme', 'grant', m)
        self.assertFalse(decl.requires_sharia_review)
        self.assertEqual(decl.status, 'self_declared')

    def test_human_review_requires_staff(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        decl = funding_declarations.declare_programme(org, 'Grant Programme', 'grant', m)
        with self.assertRaises(PermissionError):
            funding_declarations.human_review(decl, actor=user)
        decl = funding_declarations.human_review(decl, actor=_staff())
        self.assertEqual(decl.status, 'human_reviewed')


class PublicRouteHistoryTests(TestCase):
    def test_propose_update_logs_revision_before_mutating(self):
        from capability_graph.services.routes import add_public_route, propose_route_update
        org = get_or_create_organisation('Org A')
        edge = record_capability(org, 'fund', evidence_url='https://example.org/x')
        route = add_public_route(edge, 'email', 'old@example.org')
        user = _user()
        propose_route_update(route, actor=user, route_value='new@example.org', reason='Email changed.')
        route.refresh_from_db()
        self.assertEqual(route.route_value, 'new@example.org')
        self.assertEqual(route.proposed_by_id, user.pk)
        revision = route.revisions.first()
        self.assertEqual(revision.previous_route_value, 'old@example.org')
        self.assertEqual(revision.new_route_value, 'new@example.org')

    def test_proposed_update_never_auto_verifies(self):
        from capability_graph.services.routes import add_public_route, propose_route_update
        org = get_or_create_organisation('Org A')
        edge = record_capability(org, 'fund', evidence_url='https://example.org/x')
        route = add_public_route(edge, 'email', 'old@example.org')
        propose_route_update(route, actor=_user(), route_value='new@example.org')
        route.refresh_from_db()
        self.assertIsNone(route.verified_at)

    def test_propose_update_requires_real_actor(self):
        from capability_graph.services.routes import add_public_route, propose_route_update
        org = get_or_create_organisation('Org A')
        edge = record_capability(org, 'fund', evidence_url='https://example.org/x')
        route = add_public_route(edge, 'email', 'old@example.org')
        with self.assertRaises(ValueError):
            propose_route_update(route, actor=None, route_value='new@example.org')


class ResourceDeclarationTests(TestCase):
    def test_declare_resource_view_attributes_organisation_and_user(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        _verified_member(org, user)
        self.client.force_login(user)
        response = self.client.post(reverse('partner_participation:declare_resource', args=[org.pk]), {
            'title': 'Spare warehouse space', 'resource_type': 'building', 'availability': 'available',
        })
        self.assertEqual(response.status_code, 302)
        from good_agents.models import AvailableResource
        resource = AvailableResource.objects.get(title='Spare warehouse space')
        self.assertEqual(resource.organisation_id, org.pk)
        self.assertEqual(resource.declared_by_id, user.pk)

    def test_availability_choices_include_reserved_and_unavailable(self):
        from good_agents.models import AvailableResource
        values = dict(AvailableResource.AVAILABILITY_CHOICES)
        self.assertIn('reserved', values)
        self.assertIn('unavailable', values)


class RoutingRankingTests(TestCase):
    def test_never_infers_capability_from_org_type(self):
        """An org with no OrganisationCapability rows never appears as a routing candidate."""
        get_or_create_organisation('Silent Org', org_type='regulator')
        opp = _opportunity(theme='justice')
        result = routing.generate_routing_candidates(opp)
        self.assertEqual(result['created'], [])

    def test_strong_verified_match_requires_all_signals(self):
        org = get_or_create_organisation('Org A', jurisdiction='England')
        user = _user()
        m = _verified_member(org, user)
        edge = record_capability(org, 'coordinate', jurisdiction='England', evidence_url='https://example.org/x')
        edge = verify_capability(edge, actor=_staff())
        opportunity_preferences.set_preference(org, 'poverty', m, acceptance_mode='open_to_relevant_opportunities')
        from capability_graph.services.routes import add_public_route
        add_public_route(edge, 'email', 'contact@example.org')

        opp = _opportunity(theme='poverty', region='England')
        result = routing.generate_routing_candidates(opp)
        self.assertEqual(len(result['created']), 1)
        self.assertEqual(result['created'][0].confidence_label, 'strong_verified_match')

    def test_verified_capability_match_without_participation(self):
        """Phase 18: a real, verified public authority with NO partner-portal engagement still ranks well."""
        org = get_or_create_organisation('Silent Regulator', jurisdiction='England')
        edge = record_capability(org, 'coordinate', jurisdiction='England', evidence_url='https://example.org/x')
        verify_capability(edge, actor=_staff())
        opp = _opportunity(theme='poverty', region='England')
        result = routing.generate_routing_candidates(opp)
        self.assertEqual(len(result['created']), 1)
        self.assertEqual(result['created'][0].confidence_label, 'verified_capability_match')

    def test_not_accepting_organisation_skipped_not_created(self):
        org = get_or_create_organisation('Org A', jurisdiction='England')
        user = _user()
        m = _verified_member(org, user)
        record_capability(org, 'coordinate', jurisdiction='England', evidence_url='https://example.org/x')
        opportunity_preferences.set_preference(org, 'poverty', m, acceptance_mode='not_accepting')
        opp = _opportunity(theme='poverty', region='England')
        result = routing.generate_routing_candidates(opp)
        self.assertEqual(result['created'], [])
        self.assertEqual(len(result['skipped']), 1)
        self.assertIn('not_accepting', result['skipped'][0]['reason'].lower().replace(' ', '_'))

    def test_paused_organisation_skipped(self):
        org = get_or_create_organisation('Org A', jurisdiction='England')
        user = _user()
        m = _verified_member(org, user)
        record_capability(org, 'coordinate', jurisdiction='England', evidence_url='https://example.org/x')
        opportunity_preferences.set_preference(org, 'poverty', m, acceptance_mode='paused')
        opp = _opportunity(theme='poverty', region='England')
        result = routing.generate_routing_candidates(opp)
        self.assertEqual(result['created'], [])

    def test_disputed_capability_yields_needs_review(self):
        org = get_or_create_organisation('Org A', jurisdiction='England')
        edge = record_capability(org, 'coordinate', jurisdiction='England', evidence_url='https://example.org/x')
        label, reasons, skip_reason = routing.score_candidate(org, edge, _opportunity(theme='poverty'))
        self.assertIsNone(skip_reason)
        # Now introduce a conflict and re-score.
        conflicts_service.detect_conflicts_for(edge)  # no conflict yet (nothing to conflict with)
        CapabilityConflict.objects.create(capability=edge, description='Test conflict', resolution='unresolved')
        label2, reasons2, _ = routing.score_candidate(org, edge, _opportunity(theme='poverty'))
        self.assertEqual(label2, 'needs_review')

    def test_match_reasons_are_real_facts_not_opaque(self):
        org = get_or_create_organisation('Org A', jurisdiction='England')
        edge = record_capability(
            org, 'coordinate', jurisdiction='England', topic_domain='poverty relief',
            evidence_url='https://example.org/x', limitations='Referrals only.',
        )
        label, reasons, _ = routing.score_candidate(org, edge, _opportunity(theme='poverty', region='England'))
        joined = ' '.join(reasons)
        self.assertIn('Coordinate', joined)
        self.assertIn('England', joined)
        self.assertIn('poverty relief', joined)
        self.assertIn('Referrals only.', joined)
        # Never a bare numeric confidence with no explanation.
        self.assertNotRegex(joined, r'^\d+%$')


class RoutingTransitionGovernanceTests(TestCase):
    def _candidate(self):
        org = get_or_create_organisation('Org A', jurisdiction='England')
        record_capability(org, 'coordinate', jurisdiction='England', evidence_url='https://example.org/x')
        opp = _opportunity(theme='poverty', region='England')
        result = routing.generate_routing_candidates(opp)
        return result['created'][0]

    def test_illegal_jump_blocked(self):
        candidate = self._candidate()
        with self.assertRaises(routing.IllegalRoutingTransitionError):
            routing.transition(candidate, 'shared', actor=_staff())

    def test_approve_to_share_requires_staff(self):
        candidate = self._candidate()
        user, staff = _user(), _staff()
        routing.transition(candidate, 'ready_for_ecoiq_review', actor=user)
        with self.assertRaises(routing.IllegalRoutingTransitionError):
            routing.transition(candidate, 'approved_to_share', actor=user)
        candidate = routing.transition(candidate, 'approved_to_share', actor=staff)
        self.assertEqual(candidate.status, 'approved_to_share')

    def test_shared_requires_staff(self):
        candidate = self._candidate()
        user, staff = _user(), _staff()
        routing.transition(candidate, 'ready_for_ecoiq_review', actor=user)
        routing.transition(candidate, 'approved_to_share', actor=staff)
        with self.assertRaises(routing.IllegalRoutingTransitionError):
            routing.transition(candidate, 'shared', actor=user)

    def test_accepted_for_next_step_never_reachable_without_interest_first(self):
        candidate = self._candidate()
        user, staff = _user(), _staff()
        routing.transition(candidate, 'ready_for_ecoiq_review', actor=user)
        routing.transition(candidate, 'approved_to_share', actor=staff)
        routing.transition(candidate, 'shared', actor=staff)
        with self.assertRaises(routing.IllegalRoutingTransitionError):
            routing.transition(candidate, 'accepted_for_next_step', actor=user)
        routing.transition(candidate, 'viewed', actor=user)
        routing.transition(candidate, 'interested', actor=user)
        candidate = routing.transition(candidate, 'accepted_for_next_step', actor=user)
        self.assertEqual(candidate.status, 'accepted_for_next_step')

    def test_terminal_states_have_no_further_transitions(self):
        from partner_participation.models import ROUTING_ALLOWED_TRANSITIONS
        self.assertEqual(ROUTING_ALLOWED_TRANSITIONS['not_interested'], set())
        self.assertEqual(ROUTING_ALLOWED_TRANSITIONS['accepted_for_next_step'], set())


class IncomingOpportunityCandidatesTests(TestCase):
    def test_portal_never_shows_unshared_candidates(self):
        org = get_or_create_organisation('Org A', jurisdiction='England')
        user = _user()
        _verified_member(org, user)
        record_capability(org, 'coordinate', jurisdiction='England', evidence_url='https://example.org/x')
        opp = _opportunity(theme='poverty', region='England')
        routing.generate_routing_candidates(opp)  # status stays 'routing_candidate'

        self.client.force_login(user)
        response = self.client.get(reverse('partner_participation:organisation_portal', args=[org.pk]))
        self.assertNotContains(response, opp.title)


class ConflictingEvidenceTests(TestCase):
    def test_conflict_detected_between_declared_and_external(self):
        org = get_or_create_organisation('Org A', jurisdiction='England')
        record_capability(
            org, 'regulate', jurisdiction='England', evidence_url='https://example.org/external',
            limitations='External: England only.',
        )  # provenance defaults to 'external_public_evidence'
        user = _user()
        m = _verified_member(org, user)
        declared_edge = capability_declarations.declare_capability(
            org, 'regulate', m, jurisdiction='Scotland', limitations='Declared: Scotland only.',
        )
        conflicts = conflicts_service.detect_conflicts_for(declared_edge)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].resolution, 'unresolved')

    def test_resolve_conflict_requires_staff(self):
        org = get_or_create_organisation('Org A')
        edge = record_capability(org, 'fund', evidence_url='https://example.org/x')
        conflict = CapabilityConflict.objects.create(capability=edge, description='x')
        with self.assertRaises(PermissionError):
            conflicts_service.resolve_conflict(conflict, resolution='declared_claim_upheld', actor=_user())
        conflict = conflicts_service.resolve_conflict(conflict, resolution='declared_claim_upheld', actor=_staff())
        self.assertEqual(conflict.resolution, 'declared_claim_upheld')
        self.assertIsNotNone(conflict.resolved_at)


class StalenessTests(TestCase):
    def test_no_schedule_set_is_honest_not_assumed_fresh(self):
        org = get_or_create_organisation('Org A')
        edge = record_capability(org, 'fund', evidence_url='https://example.org/x')
        self.assertEqual(staleness.staleness_of(edge), 'no_schedule_set')

    def test_reconfirm_requires_real_actor(self):
        org = get_or_create_organisation('Org A')
        edge = record_capability(org, 'fund', evidence_url='https://example.org/x')
        with self.assertRaises(ValueError):
            staleness.reconfirm(edge, actor=None)
        edge = staleness.reconfirm(edge, actor=_user())
        self.assertEqual(staleness.staleness_of(edge), 'current')

    def test_sweep_expires_only_past_grace_period(self):
        import datetime
        from django.utils import timezone
        org = get_or_create_organisation('Org A')
        edge = record_capability(org, 'fund', evidence_url='https://example.org/x')
        edge.reconfirmation_due_at = timezone.now() - datetime.timedelta(days=60)
        edge.save(update_fields=['reconfirmation_due_at'])
        count = staleness.sweep_expire_stale(grace_days=30)
        edge.refresh_from_db()
        self.assertEqual(count, 1)
        self.assertEqual(edge.verification_state, 'expired')


class MissionControlIntegrationTests(TestCase):
    def test_summary_none_without_resolved_organisation(self):
        opp = _opportunity()
        self.assertIsNone(mission_control.partner_participation_summary(opp))

    def test_summary_reflects_real_participation_state(self):
        from good_agents.services import action_gate as action_gate_service
        from good_agents.services import responsible_party as responsible_party_service

        org = get_or_create_organisation('Org A', jurisdiction='England')
        user = _user()
        m = _verified_member(org, user)
        edge = record_capability(org, 'coordinate', jurisdiction='England', evidence_url='https://example.org/x')
        verify_capability(edge, actor=_staff())
        opportunity_preferences.set_preference(org, 'poverty', m, acceptance_mode='open_to_relevant_opportunities')

        opp = _opportunity(theme='poverty', region='England')
        action_gate_service.get_or_create_gate(opp)
        from good_agents.models import ResponsibleParty
        ResponsibleParty.objects.create(opportunity=opp, name=org.name, organisation=org, party_type='ngo')

        summary = mission_control.partner_participation_summary(opp)
        self.assertIsNotNone(summary)
        self.assertTrue(summary['capability_verified'])
        self.assertTrue(summary['participating'])
        self.assertTrue(summary['accepting_opportunities'])

    def test_mission_control_page_renders_partner_section(self):
        from django.core.management import call_command
        call_command('seed_global_monitoring_mission')
        response_staff = _staff('mc-staff')
        self.client.force_login(response_staff)
        response = self.client.get(reverse('good_agents:mission_control'))
        self.assertContains(response, 'Partner Participation')


class NotificationTests(TestCase):
    def test_membership_claim_notification_created_and_deduped(self):
        from partner_participation.services.notify import notify_membership_claim_requires_review
        org = get_or_create_organisation('Org A')
        user = _user()
        m = membership.request_membership(org, user)
        note1 = notify_membership_claim_requires_review(m)
        self.assertIsNotNone(note1)
        self.assertEqual(note1.source_type, 'partner_participation')
        note2 = notify_membership_claim_requires_review(m)
        self.assertIsNone(note2)  # never spams on repeat calls
        self.assertTrue(_already_notified(m, 'membership_claim_requires_review'))

    def test_capability_declaration_notification(self):
        from partner_participation.services.notify import notify_capability_declaration_requires_review
        org = get_or_create_organisation('Org A')
        user = _user()
        m = _verified_member(org, user)
        edge = capability_declarations.declare_capability(org, 'fund', m)
        note = notify_capability_declaration_requires_review(edge)
        self.assertIsNotNone(note)
        self.assertEqual(note.priority, 'normal')


class PrivacyTests(TestCase):
    def test_portal_never_exposes_internal_review_notes(self):
        org = get_or_create_organisation('Org A')
        user = _user()
        m = membership.request_membership(org, user)
        membership.review_membership(m, decision='verified_member', actor=_staff(), notes='SECRET INTERNAL NOTE')
        self.client.force_login(user)
        response = self.client.get(reverse('partner_participation:organisation_portal', args=[org.pk]))
        self.assertNotContains(response, 'SECRET INTERNAL NOTE')

    def test_declaration_review_queue_is_staff_only(self):
        response = self.client.get(reverse('partner_participation:declaration_review_queue'))
        self.assertEqual(response.status_code, 302)


class CSRFTests(TestCase):
    def test_claim_requires_csrf_token(self):
        from django.test import Client
        org = get_or_create_organisation('Org A')
        user = _user()
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(user)
        response = csrf_client.post(reverse('partner_participation:claim_organisation', args=[org.pk]), {'role': 'admin'})
        self.assertEqual(response.status_code, 403)


class RegressionTests(TestCase):
    def test_full_flow_smoke(self):
        """Signal -> organisation -> capability -> evidence -> human review -> preference -> route -> routing -> respond."""
        org = get_or_create_organisation('Full Flow Org', jurisdiction='England')
        user = _user()
        staff = _staff()
        m = _verified_member(org, user)

        edge = capability_declarations.declare_capability(org, 'coordinate', m, jurisdiction='England', topic_domain='poverty relief')
        edge = capability_declarations.attach_evidence(edge, evidence_url='https://example.org/x', actor=user)
        edge = capability_declarations.human_review(edge, actor=staff)
        self.assertEqual(edge.verification_state, 'human_reviewed')

        opportunity_preferences.set_preference(org, 'poverty', m, acceptance_mode='open_to_relevant_opportunities')
        from capability_graph.services.routes import add_public_route
        add_public_route(edge, 'email', 'contact@example.org')

        opp = _opportunity(theme='poverty', region='England')
        result = routing.generate_routing_candidates(opp)
        self.assertEqual(len(result['created']), 1)
        candidate = result['created'][0]

        routing.transition(candidate, 'ready_for_ecoiq_review', actor=user)
        routing.transition(candidate, 'approved_to_share', actor=staff)
        candidate = routing.transition(candidate, 'shared', actor=staff)
        self.assertEqual(candidate.status, 'shared')
        self.assertIsNotNone(candidate.shared_at)
