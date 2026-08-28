"""
Server-side smoke gate for the journeys a browser cannot decide alone.

PAIRED WITH frontend/web/src/app/journeys.smoke.test.tsx
--------------------------------------------------------
That file walks the rendered React journeys in jsdom. This one covers what
jsdom has no view of: HTTP status codes, who may see which organisation, and
whether a counter moved. Between them they cover the classes of defect that
reached production in this programme.

Deliberately thin. Every assertion here is a JOURNEY-level fact — a reader
arrives at a URL and gets the right answer — rather than a re-test of the unit
behaviour that already has its own file. A smoke gate that duplicates the suite
below it costs runtime and catches nothing new.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from companies.models import CompanyProfile
from company_intelligence.models import CompanyKPIAssessment, CompanyKPIEvidenceLink
from evidence_memory.models import EvidenceMemory
from league.models import Company


class JourneySmokeTestCase(TestCase):
    """
    The production shape: one public demonstration, one real organisation whose
    evidence is still under review.
    """

    def setUp(self):
        User = get_user_model()
        self.reviewer = User.objects.create_user(
            username='reviewer', password='x', is_staff=True)

        self.demo_company = Company.objects.create(name='Demo Co', slug='demo-co')
        self.demo = CompanyProfile.objects.create(
            company=self.demo_company, status='public_demo')
        demo_assessment = CompanyKPIAssessment.objects.create(
            company=self.demo, kpi_id=114, is_demo=True)
        self._link(self.demo, demo_assessment, is_demo=True,
                   ref='European Commission — a real citation', state='confirmed')

        self.real_company = Company.objects.create(name='Real Co', slug='real-co')
        self.real = CompanyProfile.objects.create(
            company=self.real_company, status='archived')
        real_assessment = CompanyKPIAssessment.objects.create(
            company=self.real, kpi_id=16)
        self._link(self.real, real_assessment, is_demo=False,
                   ref='harvester.Evidence:501', state='proposed')

    def _link(self, profile, assessment, *, is_demo, ref, state):
        evidence = EvidenceMemory.objects.create(
            text_chunk='Body.', source_reference=ref,
            source_type='harvester_evidence', source_url='https://example.org/x',
            company=profile, date_collected=datetime.date(2026, 1, 1),
            is_demo=is_demo)
        return CompanyKPIEvidenceLink.objects.create(
            assessment=assessment, evidence=evidence,
            relationship='supports', review_state=state)


class VisibilityJourneyTests(JourneySmokeTestCase):

    def test_the_demonstration_is_publicly_reachable(self):
        for url in ('/companies/demo-co/', '/companies/demo-co/kpis/114/',
                    '/api/v2/companies/demo-co/kpis/114/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_a_real_organisation_under_review_is_not_public(self):
        for url in ('/companies/real-co/', '/companies/real-co/kpis/16/',
                    '/api/v2/companies/real-co/kpis/16/',
                    '/api/v2/companies/real-co/principles/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_a_reviewer_can_reach_what_the_public_cannot(self):
        """Not public must not mean not reviewable."""
        self.client.force_login(self.reviewer)
        self.assertEqual(
            self.client.get('/api/v2/companies/real-co/kpis/16/').status_code, 200)
        self.assertEqual(
            self.client.get('/companies/real-co/kpis/16/').status_code, 200)

    def test_the_review_queue_is_staff_only(self):
        self.assertEqual(self.client.get('/companies/review/').status_code, 302)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get('/companies/review/').status_code, 200)


class PublicationJourneyTests(JourneySmokeTestCase):

    def test_visible_does_not_mean_published(self):
        body = self.client.get('/api/v2/companies/demo-co/kpis/114/').json()
        self.assertTrue(body['presentation']['is_demonstration'])
        self.assertFalse(body['presentation']['is_published'])

    def test_the_demonstration_label_reaches_the_payload(self):
        body = self.client.get('/api/v2/companies/demo-co/kpis/114/').json()
        self.assertIn('DEMONSTRATION', body['presentation']['label'])


class CounterJourneyTests(JourneySmokeTestCase):
    """Demonstration data must not move a real-evidence number."""

    def _stats(self):
        from platform_registry.stats import platform_stats
        return platform_stats()

    def test_demo_evidence_is_absent_from_real_totals(self):
        stats = self._stats()
        self.assertEqual(stats['investigation_evidence_records'].value, 1)
        self.assertEqual(stats['organisations_under_investigation'].value, 1)

    def test_a_confirmed_demo_link_is_not_confirmed_real_evidence(self):
        """
        The demonstration link IS confirmed — a worked example needs a verdict.
        It must still not appear in the production tally.
        """
        self.assertEqual(self._stats()['investigation_evidence_confirmed'].value, 0)

    def test_proposed_real_evidence_counts_as_awaiting_not_confirmed(self):
        stats = self._stats()
        self.assertEqual(stats['investigation_evidence_awaiting_review'].value, 1)
        self.assertEqual(stats['investigation_evidence_confirmed'].value, 0)

    def test_nothing_is_published(self):
        self.assertEqual(self._stats()['companies_published'].value, 0)


class UrlJourneyTests(JourneySmokeTestCase):
    """
    Every SPA route once answered 404 without its trailing slash — the form a
    reader copies out of the address bar after client-side navigation.
    """

    def test_canonical_routes_serve(self):
        for url in ('/', '/principles/', '/companies/', '/trust/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_slashless_routes_redirect_rather_than_404(self):
        for url in ('/principles', '/companies', '/trust', '/about'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response['Location'], f'{url}/')

    def test_a_deep_investigation_url_redirects_too(self):
        response = self.client.get('/companies/demo-co/kpis/114')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/companies/demo-co/kpis/114/')

    def test_an_unknown_page_is_still_a_404(self):
        self.assertEqual(self.client.get('/no-such-page').status_code, 404)

    def test_an_unknown_api_route_stays_json(self):
        response = self.client.get('/api/v2/typo/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response['Content-Type'], 'application/json')


class ProvenanceJourneyTests(JourneySmokeTestCase):
    """The idempotency key must never surface as a title."""

    def test_a_human_written_reference_is_shown_as_the_title(self):
        body = self.client.get('/api/v2/companies/demo-co/kpis/114/').json()
        self.assertEqual(body['evidence'][0]['title'],
                         'European Commission — a real citation')

    def test_the_harvester_key_never_becomes_a_title(self):
        self.client.force_login(self.reviewer)
        body = self.client.get('/api/v2/companies/real-co/kpis/16/').json()
        self.assertIsNone(body['evidence'][0]['title'])
        self.assertNotIn('harvester.Evidence:',
                         body['evidence'][0]['title'] or '')
