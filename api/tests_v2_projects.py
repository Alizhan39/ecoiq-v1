"""
GET /api/v2/projects/

The estate holds zero projects. The endpoint exists anyway, because the
frontend needs a real shape to render an honest empty state against — and
inventing demo rows to make a page look populated is the failure this
programme exists to remove.
"""
import re

from django.core.cache import cache
from django.test import Client, TestCase


class ProjectsEndpoint(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_it_responds_when_there_are_no_projects(self):
        response = self.client.get('/api/v2/projects/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 0)
        self.assertEqual(response.json()['results'], [])

    def test_it_reports_verified_separately_from_total(self):
        """
        "12 projects" and "12 projects, 0 independently verified" are very
        different statements, and a frontend computing the second from the
        first will eventually forget to.
        """
        payload = self.client.get('/api/v2/projects/').json()

        self.assertIn('count', payload)
        self.assertIn('verified_count', payload)

    def test_it_is_anonymous(self):
        self.assertEqual(Client().get('/api/v2/projects/').status_code, 200)


class ProjectQuantities(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        from league.models import Company, EnvironmentalProject

        company = Company.objects.create(name='Proj Co', slug='proj-co',
                                         country='UK')
        self.recorded = EnvironmentalProject.objects.create(
            company=company, name='Recorded', project_type='renewable',
            status='completed', investment_usd=1_000_000,
            co2_reduction_tonnes=5_000, households_helped=100, verified=True)
        self.unrecorded = EnvironmentalProject.objects.create(
            company=company, name='Unrecorded', project_type='renewable',
            status='planned')
        self.client = Client()

    def _by_name(self):
        return {p['name']: p
                for p in self.client.get('/api/v2/projects/').json()['results']}

    def test_a_recorded_quantity_is_returned(self):
        self.assertEqual(self._by_name()['Recorded']['co2_reduction_tonnes'], 5000)

    def test_an_unrecorded_quantity_is_null_not_zero(self):
        """
        A project with no recorded CO2 figure did not reduce zero tonnes. The
        difference is the whole point.
        """
        project = self._by_name()['Unrecorded']

        self.assertIsNone(project['co2_reduction_tonnes'])
        self.assertIsNone(project['investment_usd'])

    def test_verification_is_carried_separately_from_status(self):
        """
        A project can be complete and unverified. Collapsing the two would let
        "we finished it" read as "someone checked".
        """
        projects = self._by_name()

        self.assertTrue(projects['Recorded']['verified'])
        self.assertFalse(projects['Unrecorded']['verified'])

    def test_the_counts_reflect_reality(self):
        payload = self.client.get('/api/v2/projects/').json()

        self.assertEqual(payload['count'], 2)
        self.assertEqual(payload['verified_count'], 1)

    def test_no_company_score_is_exposed(self):
        """This is the projects resource; score containment lives elsewhere."""
        import json

        body = json.dumps(self.client.get('/api/v2/projects/').json())

        self.assertNotIn('ecoiq_score', body)


class ProjectConceptTests(TestCase):
    """
    Programme concepts travel in their own key, and are never counted.

    Five concepts rendered next to zero recorded projects becomes "five
    projects" the moment they share a list — the same substitution as a score
    standing in for evidence, and more tempting, because the merged page looks
    finished.
    """

    def setUp(self):
        cache.clear()

    def payload(self):
        return self.client.get('/api/v2/projects/').json()

    def test_concepts_are_returned(self):
        """
        They are real founder content. Migrating the frontend must not delete
        them, and re-typing them into React would fork the source of truth.
        """
        self.assertGreater(len(self.payload()['concepts']), 0)

    def test_concepts_read_from_the_same_module_the_templates_used(self):
        from projects.data import PROJECTS

        concepts = self.payload()['concepts']
        self.assertEqual(len(concepts), len(PROJECTS))
        self.assertEqual({c['slug'] for c in concepts},
                         {p['slug'] for p in PROJECTS})

    def test_count_counts_recorded_projects_only(self):
        from league.models import EnvironmentalProject

        body = self.payload()
        self.assertEqual(body['count'], EnvironmentalProject.objects.count())
        self.assertNotEqual(body['count'], len(body['concepts']))

    def test_concepts_are_not_in_results(self):
        body = self.payload()
        concept_slugs = {c['slug'] for c in body['concepts']}
        result_slugs = {r['slug'] for r in body['results']}
        self.assertEqual(concept_slugs & result_slugs, set())

    def test_no_concept_claims_to_be_complete_or_verified(self):
        """
        A concept has no verification state, because there is nothing to have
        verified. If one ever acquired a `verified` field, a UI that renders
        both lists with the same component would show a badge saying so.
        """
        for concept in self.payload()['concepts']:
            with self.subTest(slug=concept['slug']):
                self.assertNotIn('verified', concept)
                self.assertNotIn(concept['status_key'],
                                 ('complete', 'completed', 'delivered'))

    def test_every_funding_figure_travels_with_its_qualifier(self):
        """
        A CURRENCY FIGURE must never appear without the words that qualify it.
        A bare "£15,000" on a concept page reads as committed capital; the same
        figure beside "pilot (indicative)" does not.

        Scoped to figures, not to the field: one concept carries the text
        "Concept stage" in `funding_amount`, which is a qualifier already and
        needs no second one.
        """
        for concept in self.payload()['concepts']:
            with self.subTest(slug=concept['slug']):
                amount = concept['funding_amount']
                if not re.search(r'[£$€]\s?\d', amount):
                    continue
                qualifiers = (concept['funding_label'] + ' '
                              + concept['funding_note']).lower()
                self.assertIn('indicative', qualifiers,
                              f'{concept["slug"]} publishes {amount} with no '
                              'qualifier.')
