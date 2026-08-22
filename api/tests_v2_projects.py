"""
GET /api/v2/projects/

The estate holds zero projects. The endpoint exists anyway, because the
frontend needs a real shape to render an honest empty state against — and
inventing demo rows to make a page look populated is the failure this
programme exists to remove.
"""
from django.test import Client, TestCase


class ProjectsEndpoint(TestCase):

    def setUp(self):
        from django.core.cache import cache
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
