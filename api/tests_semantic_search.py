"""
Regression tests for GET /api/v1/semantic-search/ input validation.

Before this, `?limit=abc` raised ValueError inside the view (HTTP 500) and
`?limit=-5` produced a negative queryset slice. Both are user input and must
produce HTTP 400.
"""
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase

from league.models import Company

SEARCH_URL = '/api/v1/semantic-search/'


class _ThrottleIsolatedTestCase(TestCase):
    """
    Anonymous throttle counters live in one process-wide cache keyed by test
    client IP, so without this they leak between tests and later cases 429
    depending on run order. Mirrors the helper in api/tests.py.
    """
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        super().setUp()


class SemanticSearchValidationTests(_ThrottleIsolatedTestCase):

    @classmethod
    def setUpTestData(cls):
        for i in range(3):
            Company.objects.create(
                name=f'Northwind Energy {i}',
                slug=f'northwind-energy-{i}',
                sector='Energy',
                country='United Kingdom',
                ecoiq_score=Decimal('50.0'),
            )

    # ── Invalid input must be 400, never 500 ──────────────────────────────────

    def test_non_numeric_limit_returns_400(self):
        response = self.client.get(SEARCH_URL, {'q': 'energy', 'limit': 'abc'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('limit', response.json()['detail'])

    def test_negative_limit_returns_400(self):
        response = self.client.get(SEARCH_URL, {'q': 'energy', 'limit': -5})
        self.assertEqual(response.status_code, 400)

    def test_zero_limit_returns_400(self):
        response = self.client.get(SEARCH_URL, {'q': 'energy', 'limit': 0})
        self.assertEqual(response.status_code, 400)

    def test_limit_above_ceiling_returns_400(self):
        response = self.client.get(SEARCH_URL, {'q': 'energy', 'limit': 100000})
        self.assertEqual(response.status_code, 400)

    def test_missing_query_returns_400(self):
        self.assertEqual(self.client.get(SEARCH_URL).status_code, 400)

    def test_single_character_query_returns_400(self):
        response = self.client.get(SEARCH_URL, {'q': 'e'})
        self.assertEqual(response.status_code, 400)

    def test_overlong_query_returns_400(self):
        response = self.client.get(SEARCH_URL, {'q': 'x' * 501})
        self.assertEqual(response.status_code, 400)

    def test_error_response_does_not_leak_internals(self):
        response = self.client.get(SEARCH_URL, {'q': 'energy', 'limit': 'abc'})
        body = response.content.decode()
        for leak in ('Traceback', 'ValueError', 'invalid literal', 'File "'):
            self.assertNotIn(leak, body)

    # ── Valid input keeps working exactly as before ───────────────────────────

    def test_valid_query_returns_200_with_stable_schema(self):
        response = self.client.get(SEARCH_URL, {'q': 'energy'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            set(payload), {'query', 'method', 'count', 'results'})
        self.assertEqual(payload['query'], 'energy')

    def test_limit_is_honoured(self):
        response = self.client.get(SEARCH_URL, {'q': 'northwind', 'limit': 2})
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(response.json()['count'], 2)

    def test_default_limit_applies_when_omitted(self):
        response = self.client.get(SEARCH_URL, {'q': 'northwind'})
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(response.json()['count'], 10)

    def test_query_is_whitespace_trimmed(self):
        response = self.client.get(SEARCH_URL, {'q': '  energy  '})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['query'], 'energy')

    def test_method_is_reported_honestly_as_keyword_search(self):
        """
        The vector path is disabled by default (no sentence-transformers in
        requirements, no `embedding` column). The response must say so rather
        than implying a semantic ranking happened.
        """
        response = self.client.get(SEARCH_URL, {'q': 'energy'})
        self.assertEqual(response.json()['method'], 'text')

    def test_result_entries_have_the_documented_shape(self):
        response = self.client.get(SEARCH_URL, {'q': 'northwind'})
        results = response.json()['results']
        self.assertTrue(results)
        self.assertEqual(
            set(results[0]),
            {'name', 'slug', 'sector', 'country', 'ecoiq_score', 'tier', 'url'})


class SemanticSearchQueryCountTests(_ThrottleIsolatedTestCase):
    """The keyword path must not run a query per result (N+1)."""

    @classmethod
    def setUpTestData(cls):
        for i in range(20):
            Company.objects.create(
                name=f'Querycount Corp {i}',
                slug=f'querycount-corp-{i}',
                sector='Energy',
                country='United Kingdom',
                ecoiq_score=Decimal('50.0'),
            )

    def test_result_count_does_not_change_query_count(self):
        with self.assertNumQueries(1):
            self.client.get(SEARCH_URL, {'q': 'querycount', 'limit': 5})
        with self.assertNumQueries(1):
            self.client.get(SEARCH_URL, {'q': 'querycount', 'limit': 20})
