"""
What a directory page costs, and that making it cheaper changed no answer.

THE PATHOLOGY
-------------
Every row of /api/v2/companies/ carries `ecoiq_score`, `score_status`,
`evidence_coverage` and `confidence`, and all four come from
`eligibility.decide()` — which reads that organisation's provenance, through
both `coverage_for` and `confidence_for`. So a page asked the same question
once per row, twice each. Measured:

    page_size=1     5 queries
    page_size=5    17 queries
    page_size=10   32 queries
    page_size=20   62 queries
    page_size=30   92 queries        exactly three per additional row

/api/v2/leaderboard/ was worse in kind: it evaluates eligibility until it has
filled `top`, so on a table where little is publishable it scans most of it,
three queries a row.

THE RULE THESE TESTS ENFORCE
----------------------------
A performance change to the publication path is only acceptable if it decides
exactly what it decided before. `eligibility.decide()` is the one place that
decides whether a score may be published; a prefetch that quietly changed an
answer would be far worse than a slow page. So these assert the ANSWERS are
identical, not just that the queries went down.
"""
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext, override_settings

from companies.models import CompanyProfile
from companies.provenance import PREFETCHED_ATTRIBUTE, attach_current_maps
from league.models import Company


def build_directory(size=30):
    """A population wide enough that an N+1 is unmistakable."""
    for index in range(size):
        company = Company.objects.create(
            name=f'Perf Co {index:02d}', slug=f'perf-{index:02d}',
            sector='energy', country='US', ecoiq_score=50 + index)
        CompanyProfile.objects.create(
            company=company, status='public', ecoiq_total_score=50 + index)


def queries_for(client, url):
    with CaptureQueriesContext(connection) as captured:
        response = client.get(url)
    return response, len(captured.captured_queries)


@override_settings(ALLOWED_HOSTS=['*'])
class QueryCostTests(TestCase):
    """The cost must not grow with the number of rows on the page."""

    def setUp(self):
        build_directory()

    def test_the_list_costs_the_same_for_one_row_and_thirty(self):
        _, one = queries_for(self.client, '/api/v2/companies/?page_size=1')
        _, thirty = queries_for(self.client, '/api/v2/companies/?page_size=30')
        self.assertEqual(
            one, thirty,
            f'{one} queries for one row and {thirty} for thirty — the page '
            f'still asks per row.')

    def test_the_list_stays_within_a_small_fixed_budget(self):
        _, count = queries_for(self.client, '/api/v2/companies/?page_size=30')
        self.assertLessEqual(
            count, 8,
            f'A thirty-row directory page issued {count} queries. It was 92 '
            f'before the bulk provenance fetch; a number climbing back toward '
            f'that means something is reading per row again.')

    def test_the_leaderboard_does_not_scan_three_queries_at_a_time(self):
        _, count = queries_for(self.client, '/api/v2/leaderboard/')
        self.assertLessEqual(count, 8, f'leaderboard issued {count} queries')

    def test_the_pathology_is_real_and_this_is_what_fixes_it(self):
        """
        Non-vacuous, and self-contained: neutralise the bulk fetch and the old
        cost comes straight back. Without this, a future change that made the
        page cheap for some unrelated reason would leave the assertions above
        passing while measuring nothing.
        """
        import api.v2_views as views

        original = views.attach_current_maps
        views.attach_current_maps = lambda profiles: None
        try:
            _, unprefetched = queries_for(self.client,
                                          '/api/v2/companies/?page_size=30')
        finally:
            views.attach_current_maps = original
        _, prefetched = queries_for(self.client, '/api/v2/companies/?page_size=30')

        self.assertGreater(
            unprefetched, prefetched * 5,
            f'Disabling the bulk fetch cost {unprefetched} queries against '
            f'{prefetched} with it. If those are close, the page is no longer '
            f'reading provenance per row and these tests guard nothing.')


@override_settings(ALLOWED_HOSTS=['*'])
class DecisionsAreUnchangedTests(TestCase):
    """
    The part that actually matters. A prefetch that changed a publication
    decision would be a far worse defect than the slow page it replaced.
    """

    def setUp(self):
        # Deliberately mixed: scored and unscored, profiled and profile-less,
        # so the comparison covers every branch decide() can take.
        build_directory(10)
        no_score = Company.objects.create(name='No Score', slug='no-score',
                                          sector='energy')
        CompanyProfile.objects.create(company=no_score, status='public',
                                      ecoiq_total_score=None)
        Company.objects.create(name='No Profile', slug='no-profile',
                               sector='energy', ecoiq_score=88)

    def decisions(self, prefetched):
        from companies.eligibility import decide

        profiles = list(CompanyProfile.objects.select_related('company')
                        .order_by('pk'))
        if prefetched:
            attach_current_maps(profiles)
        else:
            for profile in profiles:
                if hasattr(profile, PREFETCHED_ATTRIBUTE):
                    delattr(profile, PREFETCHED_ATTRIBUTE)
        return {
            profile.company.slug: (
                decide(profile).is_published,
                decide(profile).status,
                decide(profile).coverage_percent,
                decide(profile).score,
            )
            for profile in profiles
        }

    def test_every_publication_decision_is_identical(self):
        self.assertEqual(self.decisions(prefetched=False),
                         self.decisions(prefetched=True))

    def test_the_payload_is_identical_with_and_without_the_prefetch(self):
        """
        End to end, not just the decision object: what the caller receives.
        """
        with_prefetch = self.client.get('/api/v2/companies/?page_size=30').json()

        import api.v2_views as views
        original = views.attach_current_maps
        views.attach_current_maps = lambda profiles: None
        try:
            without = self.client.get('/api/v2/companies/?page_size=30').json()
        finally:
            views.attach_current_maps = original

        self.assertEqual(with_prefetch, without)

    def test_the_leaderboard_withheld_count_is_unchanged(self):
        payload = self.client.get('/api/v2/leaderboard/').json()

        import api.v2_views as views
        original = views.attach_current_maps
        views.attach_current_maps = lambda profiles: None
        try:
            without = self.client.get('/api/v2/leaderboard/').json()
        finally:
            views.attach_current_maps = original

        self.assertEqual(payload, without)


class BulkFetchTests(TestCase):
    """The helper itself."""

    def setUp(self):
        build_directory(5)

    def test_it_reads_every_profile_in_one_query(self):
        profiles = list(CompanyProfile.objects.all())
        with CaptureQueriesContext(connection) as captured:
            attach_current_maps(profiles)
        self.assertEqual(len(captured.captured_queries), 1)

    def test_current_map_then_costs_nothing(self):
        from companies import provenance as prov

        profiles = list(CompanyProfile.objects.all())
        attach_current_maps(profiles)
        with CaptureQueriesContext(connection) as captured:
            for profile in profiles:
                prov.current_map(profile)
        self.assertEqual(len(captured.captured_queries), 0)

    def test_a_profile_with_no_provenance_gets_an_empty_map_not_a_miss(self):
        """
        An absent key would fall through to a per-row query and quietly restore
        the N+1 for exactly the organisations that have no evidence.
        """
        profiles = list(CompanyProfile.objects.all())
        attach_current_maps(profiles)
        for profile in profiles:
            self.assertEqual(getattr(profile, PREFETCHED_ATTRIBUTE), {})

    def test_it_tolerates_an_empty_list_and_none_entries(self):
        with CaptureQueriesContext(connection) as captured:
            attach_current_maps([])
            attach_current_maps([None, None])
        self.assertEqual(len(captured.captured_queries), 0)

    def test_an_unprefetched_profile_still_reads_its_own_provenance(self):
        """
        The helper is an optimisation, not a requirement. Every caller that
        never heard of it must keep working.
        """
        from companies import provenance as prov

        profile = CompanyProfile.objects.first()
        self.assertFalse(hasattr(profile, PREFETCHED_ATTRIBUTE))
        with CaptureQueriesContext(connection) as captured:
            prov.current_map(profile)
        self.assertEqual(len(captured.captured_queries), 1)
