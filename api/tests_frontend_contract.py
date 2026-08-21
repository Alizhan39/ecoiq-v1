"""
The API v2 contract React is built against.

docs/product/FRONTEND_API_CONTRACT.md describes this shape. These tests hold
the API to it, so the document cannot quietly become fiction — which is the
usual fate of a hand-written API doc.

The fixture pair is deliberate: one company that publishes and one that does
not, with IDENTICAL underlying numbers. A contract that only describes the
withheld case would let a regression through on the published one, and vice
versa.
"""
from django.test import Client, SimpleTestCase, TestCase

from companies import provenance as prov
from companies.evidence import PROVENANCE_MEASURED, PROVENANCE_UNKNOWN
from companies.scoring import recalculate_and_save
from companies.testing import populated
from league.models import Company

PILLARS = ('score_pollution_footprint', 'score_reduction_progress',
           'score_investment', 'score_transparency', 'score_community_impact')

LIST_KEYS = {
    'slug', 'name', 'sector', 'country', 'is_public', 'verified',
    'ecoiq_score', 'score_status', 'evidence_coverage', 'confidence',
    'rank', 'url',
}
DETAIL_KEYS = {
    'slug', 'name', 'sector', 'country', 'city', 'website', 'logo_url',
    'description', 'is_public', 'verified', 'ecoiq_score', 'score_status',
    'evidence_coverage', 'confidence', 'evidence_note', 'harm_signals',
}
SCORE_STATUSES = {'PUBLISHED', 'PROVISIONAL', 'INSUFFICIENT_EVIDENCE'}
CONFIDENCES = {'HIGH', 'MEDIUM', 'LOW', 'INSUFFICIENT_EVIDENCE'}


def _company(slug, origin, score=76):
    company = Company.objects.create(
        name=slug, slug=slug, country='UK',
        **{name: score for name in PILLARS})
    profile = populated(company, pollution_level='low')
    for key in sorted(prov.MATERIAL_METRIC_KEYS):
        prov.record(profile, key, origin, written_by='t')
    recalculate_and_save(profile)
    profile.refresh_from_db()
    company.refresh_from_db()
    return company


class ContractShape(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        _company('published-co', PROVENANCE_MEASURED)
        _company('withheld-co', PROVENANCE_UNKNOWN)
        self.client = Client()

    def _rows(self):
        return {r['slug']: r
                for r in self.client.get('/api/v2/companies/').json()['results']}

    def _detail(self, slug):
        return self.client.get(f'/api/v2/companies/{slug}/').json()

    # ── keys ────────────────────────────────────────────────────────────────

    def test_the_list_item_keys_are_exactly_the_documented_set(self):
        for slug, row in self._rows().items():
            with self.subTest(slug=slug):
                self.assertEqual(set(row), LIST_KEYS)

    def test_the_detail_keys_are_exactly_the_documented_set(self):
        self.assertEqual(set(self._detail('withheld-co')), DETAIL_KEYS)

    def test_no_provenance_graph_is_exposed(self):
        """The frontend must not be built assuming an endpoint that is absent."""
        self.assertNotIn('provenance', self._detail('withheld-co'))

    # ── enums ───────────────────────────────────────────────────────────────

    def test_score_status_is_always_a_documented_value(self):
        for slug, row in self._rows().items():
            with self.subTest(slug=slug):
                self.assertIn(row['score_status'], SCORE_STATUSES)

    def test_confidence_is_always_a_documented_value(self):
        for slug, row in self._rows().items():
            with self.subTest(slug=slug):
                self.assertIn(row['confidence'], CONFIDENCES)

    def test_confidence_is_never_a_number(self):
        for slug, row in self._rows().items():
            with self.subTest(slug=slug):
                self.assertIsInstance(row['confidence'], str)

    # ── nullability ─────────────────────────────────────────────────────────

    def test_a_withheld_score_is_null(self):
        row = self._rows()['withheld-co']

        self.assertIsNone(row['ecoiq_score'])
        self.assertEqual(row['score_status'], 'INSUFFICIENT_EVIDENCE')

    def test_a_withheld_rank_is_null(self):
        self.assertIsNone(self._rows()['withheld-co']['rank'])

    def test_coverage_is_present_even_at_zero(self):
        """
        Zero coverage is a MEASUREMENT -- we checked and nothing is evidenced --
        so the field is a number, not null.
        """
        row = self._rows()['withheld-co']

        self.assertIsNotNone(row['evidence_coverage'])
        self.assertEqual(row['evidence_coverage'], 0)

    def test_coverage_is_a_whole_number(self):
        for slug, row in self._rows().items():
            with self.subTest(slug=slug):
                self.assertIsInstance(row['evidence_coverage'], int)

    def test_a_published_score_is_a_number(self):
        row = self._rows()['published-co']

        self.assertEqual(row['score_status'], 'PUBLISHED')
        self.assertIsInstance(row['ecoiq_score'], (int, float))

    def test_the_published_and_withheld_companies_differ_only_in_evidence(self):
        """
        The premise of the pair. Same inputs, same stored numbers -- only the
        provenance differs, and that is what changes the contract's answer.
        """
        rows = self._rows()

        self.assertEqual(rows['published-co']['country'],
                         rows['withheld-co']['country'])
        self.assertNotEqual(rows['published-co']['score_status'],
                            rows['withheld-co']['score_status'])

    # ── the zero that is not missing ────────────────────────────────────────

    def test_a_measured_zero_is_published_as_zero(self):
        """
        The case client code gets wrong by treating 0 as falsy. This is a real
        score, and the contract must carry it.
        """
        _company('zero-co', PROVENANCE_MEASURED, score=0)

        row = self._rows()['zero-co']

        self.assertEqual(row['score_status'], 'PUBLISHED')
        self.assertEqual(row['ecoiq_score'], 0.0)
        self.assertIsNotNone(row['ecoiq_score'])

    # ── harm signals ────────────────────────────────────────────────────────

    def test_harm_signals_carry_an_explicit_insufficient_state(self):
        signals = self._detail('withheld-co')['harm_signals']

        self.assertTrue(signals)
        for signal in signals:
            with self.subTest(signal=signal['id']):
                self.assertIn('status', signal)

    def test_an_unassessable_signal_is_not_clear(self):
        signals = {s['id']: s for s in self._detail('withheld-co')['harm_signals']}
        unassessable = [s for s in signals.values()
                        if s['status'] == 'insufficient_evidence']

        for signal in unassessable:
            with self.subTest(signal=signal['id']):
                self.assertNotEqual(signal['status'], 'clear')

    # ── withheld detail ─────────────────────────────────────────────────────

    def test_a_withheld_detail_explains_itself(self):
        detail = self._detail('withheld-co')

        self.assertIsNone(detail['ecoiq_score'])
        self.assertTrue(detail['evidence_note'])


class TheDocumentMatchesReality(SimpleTestCase):
    """
    A hand-written API document drifts. These assertions are cheap and stop the
    usual failure mode: the doc describing a shape the API stopped serving.
    """

    def _doc(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        return (root / 'docs/product/FRONTEND_API_CONTRACT.md').read_text()

    def test_the_document_exists(self):
        self.assertIn('Frontend API Contract', self._doc())

    def test_it_documents_every_list_key(self):
        doc = self._doc()

        for key in LIST_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, doc)

    def test_it_documents_every_score_status(self):
        doc = self._doc()

        for status in SCORE_STATUSES:
            with self.subTest(status=status):
                self.assertIn(status, doc)

    def test_it_documents_every_confidence_value(self):
        doc = self._doc()

        for value in CONFIDENCES:
            with self.subTest(value=value):
                self.assertIn(value, doc)

    def test_it_forbids_the_coalescing_patterns(self):
        doc = self._doc()

        for pattern in ('score ?? 0', 'score || 0', 'rank || 0'):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, doc)

    def test_it_states_that_zero_is_a_real_score(self):
        self.assertIn('0.0` is a real, publishable score', self._doc())
