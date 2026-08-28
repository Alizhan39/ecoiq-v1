"""
Public demonstration: visible, and explicitly not a finding.

The distinction under test is that three facts stay separate —

    visibility            can a reader reach this page
    evidence provenance   is the evidence demonstration data
    publication           did the assessment pass the gate

— and that making something visible never moves the other two. A demonstration
mistaken for a finding is a false statement about a real company, so the label
has to be structural rather than editorial.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from companies import eligibility
from companies.models import CompanyProfile
from companies.visibility import (
    DEMONSTRATION_STATUS, PUBLICLY_VISIBLE_STATUSES, is_demonstration,
)
from company_intelligence.models import CompanyKPIAssessment, CompanyKPIEvidenceLink
from evidence_memory.models import EvidenceMemory
from league.models import Company

KPI_URL = '/api/v2/companies/{slug}/kpis/114/'
MATRIX_URL = '/api/v2/companies/{slug}/principles/'
PAGE_URL = '/companies/{slug}/'
INVESTIGATION_URL = '/companies/{slug}/kpis/114/'


class DemonstrationTestCase(TestCase):
    def setUp(self):
        self.demo_company = Company.objects.create(name='Demo Co', slug='demo-co')
        self.demo = CompanyProfile.objects.create(
            company=self.demo_company, status=DEMONSTRATION_STATUS)
        self.demo_assessment = CompanyKPIAssessment.objects.create(
            company=self.demo, kpi_id=114, is_demo=True)
        self._link(self.demo, self.demo_assessment, is_demo=True, ref='demo:1')

        # Real evidence, deliberately NOT public — the Walmart shape.
        self.real_company = Company.objects.create(name='Real Co', slug='real-co')
        self.real = CompanyProfile.objects.create(
            company=self.real_company, status='archived')
        self.real_assessment = CompanyKPIAssessment.objects.create(
            company=self.real, kpi_id=114)
        self._link(self.real, self.real_assessment, is_demo=False,
                   ref='harvester.Evidence:99', state='proposed')

    def _link(self, profile, assessment, *, is_demo, ref, state='confirmed'):
        evidence = EvidenceMemory.objects.create(
            text_chunk='Body.', source_reference=ref,
            source_type='harvester_evidence', source_url='https://example.org/x',
            company=profile, date_collected=datetime.date(2026, 1, 1),
            is_demo=is_demo)
        return CompanyKPIEvidenceLink.objects.create(
            assessment=assessment, evidence=evidence,
            relationship='supports', review_state=state)


class VisibilityIsNotPublicationTests(DemonstrationTestCase):

    def test_a_demonstration_profile_is_publicly_reachable(self):
        for url in (KPI_URL, MATRIX_URL, PAGE_URL, INVESTIGATION_URL):
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url.format(slug='demo-co')).status_code, 200)

    def test_being_visible_does_not_publish_the_assessment(self):
        """
        The whole point. eligibility.decide() never reads status, so a profile
        cannot be published by being made visible.
        """
        decision = eligibility.decide(self.demo)
        self.assertFalse(decision.is_published)

    def test_the_api_reports_visible_and_unpublished_together(self):
        body = self.client.get(KPI_URL.format(slug='demo-co')).json()
        presentation = body['presentation']
        self.assertTrue(presentation['is_demonstration'])
        self.assertFalse(presentation['is_published'])

    def test_demonstration_status_is_publicly_visible_but_not_a_quality_claim(self):
        """
        In the visible set, and deliberately absent from ('public','verified') —
        the pair every scoring and analytics query selects on.
        """
        self.assertIn(DEMONSTRATION_STATUS, PUBLICLY_VISIBLE_STATUSES)
        self.assertNotIn(DEMONSTRATION_STATUS, ('public', 'verified'))

    def test_is_demonstration_is_about_the_profile_not_the_evidence(self):
        self.assertTrue(is_demonstration(self.demo))
        self.assertFalse(is_demonstration(self.real))


class LabelTests(DemonstrationTestCase):

    def test_the_label_is_unmistakable(self):
        presentation = self.client.get(
            KPI_URL.format(slug='demo-co')).json()['presentation']
        self.assertIn('DEMONSTRATION', presentation['label'])
        self.assertIn('not a published EcoIQ assessment', presentation['label'])

    def test_the_explanation_says_what_it_is_not(self):
        presentation = self.client.get(
            KPI_URL.format(slug='demo-co')).json()['presentation']
        for phrase in ('demonstration', 'not a rating'):
            self.assertIn(phrase, presentation['explanation'].lower())

    def test_a_non_demonstration_carries_no_label(self):
        """The notice must not become decoration that appears everywhere."""
        User = get_user_model()
        staff = User.objects.create_user(username='s', password='x', is_staff=True)
        self.client.force_login(staff)
        presentation = self.client.get(
            KPI_URL.format(slug='real-co')).json()['presentation']
        self.assertFalse(presentation['is_demonstration'])
        self.assertEqual(presentation['label'], '')


class DemoEvidenceIsolationTests(DemonstrationTestCase):
    """`is_demo=True` must never reach a real-evidence total."""

    def _stats(self):
        from platform_registry.stats import platform_stats
        return platform_stats()

    def test_demo_evidence_is_excluded_from_real_evidence_counters(self):
        stats = self._stats()
        # One real record exists (real-co); the demonstration one is not counted.
        self.assertEqual(stats['investigation_evidence_records'].value, 1)

    def test_demo_evidence_is_excluded_from_organisations_under_investigation(self):
        self.assertEqual(
            self._stats()['organisations_under_investigation'].value, 1)

    def test_a_confirmed_demo_link_is_not_counted_as_confirmed_real_evidence(self):
        """
        The demonstration link IS confirmed — a worked example needs a verdict
        to demonstrate. It must still not appear in the production tally.
        """
        self.assertEqual(
            CompanyKPIEvidenceLink.objects.filter(
                review_state='confirmed', evidence__is_demo=True).count(), 1)
        self.assertEqual(self._stats()['investigation_evidence_confirmed'].value, 0)

    def test_demo_evidence_never_becomes_evaluation_ground_truth(self):
        """
        A benchmark built from demonstration data would measure the fixture, not
        the reviewer. No review action exists for it, so no case can exist.
        """
        from company_intelligence.models import EvidenceReviewAction
        from company_intelligence.services.evaluation_case import corpus_summary

        summary = corpus_summary(EvidenceReviewAction.objects.all())
        self.assertEqual(summary['reviews_examined'], 0)
        self.assertEqual(summary['benchmark_ready'], 0)


class RealEvidenceStaysPrivateTests(DemonstrationTestCase):
    """Real evidence under review must not appear in the public demonstration."""

    def test_the_real_organisation_is_not_publicly_reachable(self):
        for url in (KPI_URL, MATRIX_URL, PAGE_URL, INVESTIGATION_URL):
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url.format(slug='real-co')).status_code, 404)

    def test_real_evidence_stays_under_review(self):
        link = CompanyKPIEvidenceLink.objects.get(evidence__is_demo=False)
        self.assertEqual(link.review_state, 'proposed')

    def test_no_review_action_was_created_by_any_of_this(self):
        from company_intelligence.models import EvidenceReviewAction
        self.assertEqual(EvidenceReviewAction.objects.count(), 0)

    def test_the_public_demonstration_exposes_no_real_organisation(self):
        raw = self.client.get(KPI_URL.format(slug='demo-co')).content.decode()
        self.assertNotIn('real-co', raw)
        self.assertNotIn('Real Co', raw)


class MatrixTests(DemonstrationTestCase):

    def test_the_matrix_also_declares_the_demonstration(self):
        presentation = self.client.get(
            MATRIX_URL.format(slug='demo-co')).json()['presentation']
        self.assertTrue(presentation['is_demonstration'])
        self.assertFalse(presentation['is_published'])
