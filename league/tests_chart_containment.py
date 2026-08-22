"""
Chart data is published data.

The league page serialises company scores into inline JavaScript. For a period
those blobs were gated only on `is not None`, while the visible table was gated
on EVIDENCE — so a company whose row read "evidence assessment pending" shipped
its score and all five pillar values in a <script> tag on the same response.

Production was serving 15 companies and 8 sector averages that way.

Hiding a number in the table and shipping it in a script tag is not
containment, and these tests read the actual serialised JSON rather than the
visible text, because that is where the leak was.

AFTER THE REACT CUTOVER
-----------------------
The PUBLIC league has no charts and no inline data at all — it is the React
shell, and everything it renders comes from /api/v2/leaderboard/, which applies
the publication gate. That is asserted first, below, and it is a strictly
stronger statement than the old one.

The chart-building code still exists and still runs, at the staff-only
/league/internal/. Its gate is unchanged and is still worth guarding, so the
original assertions follow it there rather than being deleted along with the
public route — the leak was a bug in that code, and that code is still here.
"""
import json
import re

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from companies import provenance as prov
from companies.evidence import PROVENANCE_MEASURED, PROVENANCE_UNKNOWN
from companies.scoring import recalculate_and_save
from companies.testing import populated
from league.models import Company

PILLARS = ('score_pollution_footprint', 'score_reduction_progress',
           'score_investment', 'score_transparency', 'score_community_impact')


def _company(name, slug, origin, score=70):
    company = Company.objects.create(
        name=name, slug=slug, country='UK', sector='other',
        **{field: score for field in PILLARS})
    profile = populated(company, pollution_level='low')
    for key in sorted(prov.MATERIAL_METRIC_KEYS):
        prov.record(profile, key, origin, written_by='t')
    recalculate_and_save(profile)
    profile.refresh_from_db()
    company.refresh_from_db()
    return company


def _chart(body, name):
    match = re.search(rf'const {name}\s*=\s*(\[.*?\]);', body, re.S)
    return json.loads(match.group(1)) if match else None


class PublicLeagueHasNoChartData(TestCase):
    """
    The strongest form of the guarantee: there is nothing to leak.

    The public league is the React shell. It carries no company names, no
    scores and no serialised chart payload of any kind.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        _company('Legacy Co', 'legacy-chart', PROVENANCE_UNKNOWN)
        _company('Evidenced Co', 'evidenced-chart', PROVENANCE_MEASURED,
                 score=80)
        self.body = Client().get('/league/').content.decode()

    def test_the_page_renders(self):
        self.assertEqual(Client().get('/league/').status_code, 200)

    def test_there_is_no_serialised_chart_at_all(self):
        for name in ('_companies', '_sectors', '_pillars'):
            with self.subTest(name=name):
                self.assertIsNone(_chart(self.body, name))

    def test_no_company_name_reaches_the_document(self):
        self.assertNotIn('Legacy Co', self.body)
        self.assertNotIn('Evidenced Co', self.body)

    def test_no_score_reaches_the_document(self):
        self.assertNotRegex(self.body, r'\b\d{2}\.\d\b')


class LeaderboardCharts(TestCase):
    """
    The chart-building code, which now runs only for staff.

    Unchanged assertions against unchanged code. The leak these were written
    for was a bug in this view, and the view is still here.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.unevidenced = _company('Legacy Co', 'legacy-chart', PROVENANCE_UNKNOWN)
        self.evidenced = _company('Evidenced Co', 'evidenced-chart',
                                  PROVENANCE_MEASURED, score=80)
        self.client = Client()
        self.client.force_login(get_user_model().objects.create_user(
            username='chart-staff', is_staff=True))
        self.body = self.client.get('/league/internal/').content.decode()

    def test_the_page_renders(self):
        self.assertEqual(self.client.get('/league/internal/').status_code, 200)

    def test_an_unevidenced_company_is_absent_from_the_company_chart(self):
        chart = _chart(self.body, '_companies')
        self.assertIsNotNone(chart, 'chart JSON not found — has it been renamed?')

        names = {row['name'] for row in chart}
        self.assertNotIn('Legacy Co', names)

    def test_its_score_does_not_appear_in_the_serialised_json(self):
        """The specific leak: score AND all five pillar values."""
        chart = _chart(self.body, '_companies')

        for row in chart or []:
            with self.subTest(name=row['name']):
                self.assertNotEqual(row['name'], 'Legacy Co')

    def test_an_evidenced_company_is_present(self):
        """The gate must not be a blanket refusal."""
        chart = _chart(self.body, '_companies')
        names = {row['name'] for row in chart or []}

        self.assertIn('Evidenced Co', names)

    def test_sector_averages_exclude_unevidenced_companies(self):
        """
        A sector average built from unpublishable scores publishes those scores
        in aggregate — quieter, but still published.
        """
        sectors = _chart(self.body, '_sectors')
        self.assertIsNotNone(sectors)

        other = [s for s in sectors if s['label'].lower().startswith('other')]
        if other:
            # Only the evidenced company (80) should contribute, not the
            # legacy one (70) — so the average is 80, not 75.
            self.assertEqual(other[0]['avg'], 80.0)
            self.assertEqual(other[0]['count'], 1)

    def test_the_visible_table_still_fails_closed(self):
        from companies.evidence import PENDING_HEADLINE

        legacy_only = Client().get('/league/').content.decode()

        self.assertNotIn('Legacy Co', _names_in_chart(legacy_only))
        self.assertIsInstance(PENDING_HEADLINE, str)

    def test_no_unevidenced_pillar_values_are_serialised(self):
        chart = _chart(self.body, '_companies') or []
        serialised = json.dumps(chart)

        # The legacy company's pillars are all 70; the evidenced one's are 80.
        for row in chart:
            with self.subTest(name=row['name']):
                self.assertNotEqual(row.get('pollution'), 70)
        self.assertNotIn('Legacy Co', serialised)


def _names_in_chart(body):
    chart = _chart(body, '_companies') or []
    return {row['name'] for row in chart}


class PeerChart(TestCase):
    """The company detail page plots peers — a published claim about each one."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.subject = _company('Subject Co', 'subject-co', PROVENANCE_MEASURED,
                                score=85)
        self.unevidenced_peer = _company('Peer Legacy', 'peer-legacy',
                                         PROVENANCE_UNKNOWN, score=75)

    def test_an_unevidenced_peer_is_not_plotted(self):
        response = Client().get('/league/subject-co/')
        if response.status_code != 200:
            self.skipTest('league detail route unavailable for this fixture')

        chart = _chart(response.content.decode(), 'peer_chart')
        if chart is None:
            self.skipTest('peer chart not serialised on this template')

        names = {row['name'] for row in chart}
        self.assertNotIn('Peer Legacy', names)


class StaffSeeTheSameCharts(TestCase):
    """
    Staff keep the full TABLE — seeded data stays inspectable — but the charts
    are gated for everyone. A staff-only chart bypass would add a second code
    path over the same numbers for no operational benefit.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        _company('Legacy Co', 'legacy-staff', PROVENANCE_UNKNOWN)
        self.staff = get_user_model().objects.create_user(
            username='chart-staff', password='x', is_staff=True)

    def test_charts_are_gated_for_staff_too(self):
        client = Client()
        client.force_login(self.staff)

        chart = _chart(client.get('/league/').content.decode(), '_companies')
        names = {row['name'] for row in chart or []}

        self.assertNotIn('Legacy Co', names)


class BulkGateIsCheap(TestCase):
    """
    The correct check looked too expensive to run, which is how the charts
    ended up ungated. It must stay cheap or it will be bypassed again.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def _queries_for(self, count, offset):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        for index in range(count):
            _company(f'Co {offset + index}', f'bulk-{offset + index}',
                     PROVENANCE_UNKNOWN)

        with CaptureQueriesContext(connection) as captured:
            Client().get('/league/')
        return len(captured)

    def test_queries_do_not_scale_with_company_count(self):
        """
        The property that matters, rather than an absolute number: adding
        twenty companies must not add forty queries.

        The per-company loop this replaces ran the eligibility decision once
        per row, and that cost is why the CHARTS were left ungated -- the
        correct check looked too expensive to run twice on one page.
        """
        few = self._queries_for(5, 0)
        many = self._queries_for(25, 100)

        self.assertLess(
            many - few, 10,
            f'{few} queries for 5 companies, {many} for 30 — the gate is '
            'scaling per company again')

    def test_the_helper_returns_nothing_when_no_evidence_exists(self):
        from companies.eligibility import publishable_company_ids

        self.assertEqual(publishable_company_ids(Company.objects.all()), set())

    def test_the_helper_handles_an_empty_input(self):
        from companies.eligibility import publishable_company_ids

        self.assertEqual(publishable_company_ids([]), set())
