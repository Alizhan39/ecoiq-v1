"""
What the review queue says it is filtering, versus what it is really filtering.

A reviewer classifying evidence has to know which queue they are ruling on.
The form and the rows could disagree: browsers refill a text input from a
previous session, so the organisation box could read one company while the
list below held every pending candidate — the controls implying a narrowed
queue that was never applied.

That is not cosmetic on a governance surface. It is a reviewer believing they
ruled on a subset when they ruled on everything.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from companies.models import CompanyProfile
from company_intelligence.models import CompanyKPIAssessment, CompanyKPIEvidenceLink
from company_intelligence.review_views import active_filters
from evidence_memory.models import EvidenceMemory
from league.models import Company

URL = '/companies/review/'


class ActiveFilterDerivationTests(TestCase):
    """Derived from the criteria the SERVER applied, never from form fields."""

    def test_no_criteria_means_no_active_filters(self):
        self.assertEqual(active_filters({
            'company_slug': '', 'kpi_id': None, 'kpi_category': '',
            'relationship': '', 'min_source_tier': None,
            'date_from': None, 'date_to': None, 'review_states': None,
        }), [])

    def test_an_applied_company_is_reported(self):
        active = active_filters({'company_slug': 'walmart'})
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]['label'], 'Organisation')
        self.assertEqual(active[0]['value'], 'walmart')

    def test_review_state_is_not_called_a_filter(self):
        """
        The queue always filters by state. Listing it would make the default
        view look narrowed when it is the normal one.
        """
        active = active_filters({'review_states': ['proposed']})
        self.assertEqual(active, [])

    def test_every_applied_criterion_is_named(self):
        active = active_filters({
            'company_slug': 'walmart', 'kpi_id': 16, 'kpi_category': 'earth',
            'relationship': 'supports', 'min_source_tier': 1,
        })
        self.assertEqual(len(active), 5)

    def test_a_zero_is_not_mistaken_for_absent(self):
        """0 is a real tier value, not a missing one."""
        self.assertEqual(len(active_filters({'min_source_tier': 0})), 1)


class QueuePresentationTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.reviewer = User.objects.create_user(
            username='reviewer', password='x', is_staff=True)
        self.client.force_login(self.reviewer)
        company = Company.objects.create(name='Testco', slug='testco')
        profile = CompanyProfile.objects.create(company=company)
        assessment = CompanyKPIAssessment.objects.create(
            company=profile, kpi_id=16)
        evidence = EvidenceMemory.objects.create(
            text_chunk='Body.', source_reference='harvester.Evidence:1',
            source_type='harvester_evidence', company=profile,
            date_collected=datetime.date(2026, 1, 1), is_demo=False)
        CompanyKPIEvidenceLink.objects.create(
            assessment=assessment, evidence=evidence,
            relationship='supports', review_state='proposed')


class UnfilteredQueueTests(QueuePresentationTestCase):

    def test_an_unfiltered_queue_says_so(self):
        response = self.client.get(URL)
        self.assertContains(response, 'showing the whole queue')

    def test_an_unfiltered_queue_offers_no_clear_control(self):
        """A Clear button with nothing to clear is its own small lie."""
        self.assertNotContains(self.client.get(URL), 'Clear filters')

    def test_the_browser_cannot_invent_filter_state(self):
        """
        Without autocomplete=off a browser refills these from a previous
        session, and the form then implies a filter the server never applied.
        """
        response = self.client.get(URL)
        self.assertContains(response, 'autocomplete="off"')


class FilteredQueueTests(QueuePresentationTestCase):

    def test_a_filtered_queue_names_what_is_filtering_it(self):
        response = self.client.get(URL, {'company': 'testco'})
        self.assertContains(response, 'Filtered by')
        self.assertContains(response, 'Organisation: testco')

    def test_a_filtered_queue_offers_a_way_out(self):
        self.assertContains(self.client.get(URL, {'company': 'testco'}),
                            'Clear filters')

    def test_the_banner_reflects_the_server_not_the_query_string(self):
        """
        An unparseable value is not applied, so it must not be announced as a
        filter. `kpi=abc` narrows nothing; saying otherwise would describe a
        queue that does not exist.
        """
        response = self.client.get(URL, {'kpi': 'abc'})
        self.assertContains(response, 'showing the whole queue')

    def test_an_invalid_review_state_is_ignored_rather_than_shown(self):
        response = self.client.get(URL, {'state': 'not-a-state'})
        self.assertEqual(response.status_code, 200)
