"""
capability_graph/tests.py — the evidence-backed Capability Graph.

Covers: organisation deduplication (the core fix for the "flat directory"
problem — the same real org must never become a fresh duplicate row),
evidence-required capability recording, human-gated independent
verification, jurisdiction/topic-scoped matching (never inferring a
capability from an organisation's name or sector alone), deterministic
need->capability mapping, public routes, staff-only views, and CSRF.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from capability_graph.models import Organisation, OrganisationCapability, PublicRoute
from capability_graph.services.capabilities import (
    NoEvidenceError, VerificationNotAllowedError, record_capability, verify_capability,
)
from capability_graph.services.matcher import find_organisations_for_capability, find_organisations_for_need_type
from capability_graph.services.needs import (
    DEFAULT_CAPABILITIES, REQUIRED_CAPABILITIES_BY_THEME, required_capabilities_for_need_type,
    required_capabilities_for_theme,
)
from capability_graph.services.organisations import find_organisation, get_or_create_organisation
from capability_graph.services.routes import add_public_route


def _staff_user(username='cg-staff'):
    User = get_user_model()
    return User.objects.create_user(username, f'{username}@example.com', 'password123', is_staff=True)


class OrganisationDeduplicationTests(TestCase):
    def test_same_name_and_jurisdiction_resolves_to_one_row(self):
        org1 = get_or_create_organisation('USGS', jurisdiction='Global')
        org2 = get_or_create_organisation('USGS', jurisdiction='Global')
        self.assertEqual(org1.pk, org2.pk)
        self.assertEqual(Organisation.objects.count(), 1)

    def test_case_and_whitespace_insensitive_dedup(self):
        org1 = get_or_create_organisation('USGS', jurisdiction='Global')
        org2 = get_or_create_organisation('usgs', jurisdiction='global')
        self.assertEqual(org1.pk, org2.pk)

    def test_different_jurisdiction_is_a_different_organisation(self):
        org1 = get_or_create_organisation('Environment Agency', jurisdiction='England')
        org2 = get_or_create_organisation('Environment Agency', jurisdiction='Scotland')
        self.assertNotEqual(org1.pk, org2.pk)

    def test_find_organisation_never_creates(self):
        self.assertIsNone(find_organisation('Nonexistent Org'))
        self.assertEqual(Organisation.objects.count(), 0)

    def test_later_call_enriches_missing_linked_company_without_overwriting(self):
        from companies.models import CompanyProfile
        from league.models import Company
        company = Company.objects.create(name='Real Co', slug='real-co')
        profile = CompanyProfile.objects.create(company=company)

        org = get_or_create_organisation('Real Co Org')
        self.assertIsNone(org.linked_company_id)
        org = get_or_create_organisation('Real Co Org', linked_company=profile)
        self.assertEqual(org.linked_company_id, profile.pk)


class CapabilityRecordingTests(TestCase):
    def test_refuses_to_record_with_no_evidence(self):
        org = get_or_create_organisation('Test Org')
        with self.assertRaises(NoEvidenceError):
            record_capability(org, 'fund')

    def test_records_with_evidence_url(self):
        org = get_or_create_organisation('Test Org')
        edge = record_capability(org, 'fund', evidence_url='https://example.gov/funding-page')
        self.assertEqual(edge.verification_state, 'documented')
        self.assertEqual(OrganisationCapability.objects.count(), 1)

    def test_cannot_directly_set_independently_verified(self):
        org = get_or_create_organisation('Test Org')
        with self.assertRaises(VerificationNotAllowedError):
            record_capability(org, 'fund', evidence_url='https://example.gov/x', verification_state='independently_verified')

    def test_update_or_create_never_duplicates_same_edge(self):
        org = get_or_create_organisation('Test Org')
        record_capability(org, 'fund', jurisdiction='England', evidence_url='https://example.gov/x')
        record_capability(org, 'fund', jurisdiction='England', evidence_url='https://example.gov/x-updated')
        self.assertEqual(OrganisationCapability.objects.count(), 1)
        edge = OrganisationCapability.objects.get()
        self.assertEqual(edge.evidence_url, 'https://example.gov/x-updated')

    def test_different_jurisdiction_is_a_distinct_edge(self):
        org = get_or_create_organisation('Test Org')
        record_capability(org, 'regulate', jurisdiction='England', evidence_url='https://example.gov/x')
        record_capability(org, 'regulate', jurisdiction='Scotland', evidence_url='https://example.gov/y')
        self.assertEqual(OrganisationCapability.objects.count(), 2)


class VerificationGatingTests(TestCase):
    def test_verify_requires_a_real_actor(self):
        org = get_or_create_organisation('Test Org')
        edge = record_capability(org, 'fund', evidence_url='https://example.gov/x')
        with self.assertRaises(VerificationNotAllowedError):
            verify_capability(edge, actor=None)
        edge.refresh_from_db()
        self.assertEqual(edge.verification_state, 'documented')

    def test_verify_with_real_actor_sets_state_and_timestamp(self):
        org = get_or_create_organisation('Test Org')
        edge = record_capability(org, 'fund', evidence_url='https://example.gov/x')
        staff = _staff_user()
        verify_capability(edge, actor=staff)
        edge.refresh_from_db()
        self.assertEqual(edge.verification_state, 'independently_verified')
        self.assertIsNotNone(edge.last_verified_at)
        self.assertEqual(edge.verified_by_id, staff.pk)


class MatcherTests(TestCase):
    def test_never_infers_capability_from_org_type_alone(self):
        """An organisation with org_type='regulator' but no recorded capability must never match a query for 'regulate'."""
        get_or_create_organisation('Some Regulator', org_type='regulator', jurisdiction='England')
        matches = find_organisations_for_capability('regulate', jurisdiction='England')
        self.assertEqual(len(matches), 0)

    def test_jurisdiction_scoping_a_local_authority_example(self):
        """
        Mirrors the brief's own example: a local authority may have
        regulatory authority in one jurisdiction but not another.
        """
        org_a = get_or_create_organisation('Council A', jurisdiction='Borough A')
        org_b = get_or_create_organisation('Council B', jurisdiction='Borough B')
        record_capability(org_a, 'authorise', jurisdiction='Borough A', evidence_url='https://example.gov/a')
        record_capability(org_b, 'authorise', jurisdiction='Borough B', evidence_url='https://example.gov/b')

        matches = find_organisations_for_capability('authorise', jurisdiction='Borough A')
        self.assertEqual([m.organisation_id for m in matches], [org_a.pk])

    def test_min_verification_floor_excludes_weaker_claims(self):
        org = get_or_create_organisation('Test Org')
        record_capability(org, 'fund', evidence_url='https://example.gov/x', verification_state='self_reported')
        self.assertEqual(len(find_organisations_for_capability('fund', min_verification='documented')), 0)
        self.assertEqual(len(find_organisations_for_capability('fund', min_verification='self_reported')), 1)

    def test_topic_domain_narrows_results(self):
        org = get_or_create_organisation('Test Org')
        record_capability(org, 'measure', topic_domain='seismic activity', evidence_url='https://example.gov/x')
        self.assertEqual(len(find_organisations_for_capability('measure', topic_domain='seismic')), 1)
        self.assertEqual(len(find_organisations_for_capability('measure', topic_domain='flood')), 0)

    def test_find_organisations_for_need_type_covers_every_mapped_capability(self):
        results = find_organisations_for_need_type('energy')
        self.assertEqual(set(results.keys()), set(required_capabilities_for_need_type('energy')))


class NeedToCapabilityMappingTests(TestCase):
    def test_known_need_type_returns_specific_capabilities(self):
        caps = required_capabilities_for_need_type('waste')
        self.assertIn('collect', caps)
        self.assertIn('recycle', caps)

    def test_unknown_need_type_falls_back_to_default_never_crashes(self):
        self.assertEqual(required_capabilities_for_need_type('totally_unknown_need_type'), DEFAULT_CAPABILITIES)

    def test_unknown_theme_falls_back_to_default(self):
        self.assertEqual(required_capabilities_for_theme('totally_unknown_theme'), DEFAULT_CAPABILITIES)

    def test_theme_only_keys_are_covered(self):
        self.assertIn('poverty', REQUIRED_CAPABILITIES_BY_THEME)


class PublicRouteTests(TestCase):
    def test_refuses_empty_route_value(self):
        org = get_or_create_organisation('Test Org')
        edge = record_capability(org, 'fund', evidence_url='https://example.gov/x')
        with self.assertRaises(ValueError):
            add_public_route(edge, 'email', '')

    def test_add_route_idempotent(self):
        org = get_or_create_organisation('Test Org')
        edge = record_capability(org, 'fund', evidence_url='https://example.gov/x')
        add_public_route(edge, 'email', 'contact@example.gov')
        add_public_route(edge, 'email', 'contact@example.gov')
        self.assertEqual(PublicRoute.objects.count(), 1)


class CapabilityGraphViewTests(TestCase):
    def test_anonymous_redirected_from_list(self):
        response = self.client.get(reverse('capability_graph:organisation_list'))
        self.assertEqual(response.status_code, 302)

    def test_staff_gets_200_on_list(self):
        staff = _staff_user()
        self.client.force_login(staff)
        response = self.client.get(reverse('capability_graph:organisation_list'))
        self.assertEqual(response.status_code, 200)

    def test_capability_filter_narrows_list(self):
        org = get_or_create_organisation('Test Org')
        record_capability(org, 'fund', evidence_url='https://example.gov/x')
        other = get_or_create_organisation('Other Org')
        record_capability(other, 'audit', evidence_url='https://example.gov/y')

        staff = _staff_user()
        self.client.force_login(staff)
        response = self.client.get(reverse('capability_graph:organisation_list') + '?capability=fund')
        self.assertContains(response, 'Test Org')
        self.assertNotContains(response, 'Other Org')

    def test_detail_requires_staff(self):
        org = get_or_create_organisation('Test Org')
        response = self.client.get(reverse('capability_graph:organisation_detail', args=[org.pk]))
        self.assertEqual(response.status_code, 302)

    def test_verify_view_is_post_only_and_staff_gated(self):
        org = get_or_create_organisation('Test Org')
        edge = record_capability(org, 'fund', evidence_url='https://example.gov/x')
        url = reverse('capability_graph:verify_capability', args=[edge.pk])

        anon_response = self.client.get(url)
        self.assertEqual(anon_response.status_code, 302)
        edge.refresh_from_db()
        self.assertEqual(edge.verification_state, 'documented')

        staff = _staff_user()
        self.client.force_login(staff)
        self.client.post(url)
        edge.refresh_from_db()
        self.assertEqual(edge.verification_state, 'independently_verified')
        self.assertEqual(edge.verified_by_id, staff.pk)

    def test_verify_view_requires_csrf_token(self):
        org = get_or_create_organisation('Test Org')
        edge = record_capability(org, 'fund', evidence_url='https://example.gov/x')
        url = reverse('capability_graph:verify_capability', args=[edge.pk])

        staff = _staff_user()
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(staff)
        response = csrf_client.post(url)
        self.assertEqual(response.status_code, 403)
        edge.refresh_from_db()
        self.assertEqual(edge.verification_state, 'documented')
