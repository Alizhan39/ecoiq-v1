"""
api/tests_v2_assessment.py — the organisation assessment endpoint.

Two states matter and only one of them exists in production. 467 of 467
organisations are INSUFFICIENT_EVIDENCE, so the published path has never run
against real data — which makes the fixture below the only place its
containment is ever exercised. It is written to be exactly as strict as the
withheld path.
"""
from __future__ import annotations

from django.core.cache import cache
from django.test import TestCase

from companies import provenance as prov
from companies.evidence import PROVENANCE_MEASURED, PROVENANCE_SEEDED
from companies.scoring import recalculate_and_save
from companies.testing import populated
from league.models import Company


def _company(name, slug, origin, **kw):
    company = Company.objects.create(name=name, slug=slug, sector='Energy',
                                     country='UK', **kw)
    profile = populated(company, pollution_level='low')
    for key in sorted(prov.MATERIAL_METRIC_KEYS):
        prov.record(profile, key, origin, written_by='t')
    recalculate_and_save(profile)
    profile.refresh_from_db()
    company.refresh_from_db()
    return company, profile


class WithheldAssessmentTests(TestCase):
    """The state every production organisation is in."""

    def setUp(self):
        cache.clear()
        self.company, self.profile = _company(
            'Seeded Co', 'seeded-co', PROVENANCE_SEEDED)

    def payload(self):
        return self.client.get(
            f'/api/v2/companies/{self.company.slug}/assessment/').json()

    def test_the_score_is_stored_but_not_published(self):
        """Otherwise this class proves nothing."""
        self.assertIsNotNone(self.profile.ecoiq_total_score)
        body = self.payload()
        self.assertIsNone(body['ecoiq_score'])
        self.assertEqual(body['score_status'], 'INSUFFICIENT_EVIDENCE')

    def test_no_panel_key_is_present_at_all(self):
        """
        Absent, not null. `"ethics": null` invites a client to render an empty
        ethics panel, and an empty panel beside a real one is still a statement
        about the organisation.
        """
        body = self.payload()
        for key in ('material_evidence', 'ethics', 'financing_readiness',
                    'shariah', 'decision_risks'):
            with self.subTest(key=key):
                self.assertNotIn(key, body)

    def test_the_withheld_score_appears_nowhere_in_the_payload(self):
        import json

        stored = f'{self.profile.ecoiq_total_score:.1f}'
        self.assertNotIn(stored, json.dumps(self.payload()))

    def test_it_says_why(self):
        body = self.payload()
        self.assertIn('evidence_note', body)
        self.assertTrue(body['evidence_note']['headline'])
        self.assertTrue(body['evidence_note']['detail'])

    def test_gaps_are_present_even_with_nothing_published(self):
        """
        For an organisation with no assessment this IS the useful content, and
        it is the only part a reader can act on.
        """
        gaps = self.payload()['evidence_gaps']
        self.assertEqual(gaps['required'], 16)
        self.assertEqual(gaps['covered'], 0)
        self.assertTrue(gaps['reasons'])


class PublishedAssessmentTests(TestCase):
    """
    The state no production organisation has ever been in.

    Every panel here is code that has never served a real request, which is
    why it is tested at least as hard as the path that has.
    """

    def setUp(self):
        cache.clear()
        self.company, self.profile = _company(
            'Evidenced Co', 'evidenced-co', PROVENANCE_MEASURED)

    def payload(self):
        return self.client.get(
            f'/api/v2/companies/{self.company.slug}/assessment/').json()

    def test_the_fixture_actually_publishes(self):
        """If this fails the rest of the class is vacuous."""
        body = self.payload()
        self.assertEqual(body['score_status'], 'PUBLISHED')
        self.assertIsNotNone(body['ecoiq_score'])
        self.assertEqual(body['evidence_coverage'], 100)

    def test_the_panels_appear(self):
        body = self.payload()
        for key in ('material_evidence', 'decision_risks', 'evidence_gaps'):
            with self.subTest(key=key):
                self.assertIn(key, body)

    def test_material_evidence_reports_six_pillars(self):
        pillars = self.payload()['material_evidence']
        self.assertEqual(len(pillars), 6)
        self.assertTrue(all('key' in p and 'value' in p for p in pillars))

    def test_an_unassessed_pillar_travels_as_null_not_zero(self):
        """
        A zero pillar renders as a bar at the floor. Unknown is not zero, on
        this surface as on every other.
        """
        self.profile.harm_penalty = None
        self.profile.save(update_fields=['harm_penalty'])

        pillars = {p['key']: p['value'] for p in self.payload()['material_evidence']}
        self.assertIsNone(pillars['harm_penalty'])

    def test_demo_controversies_never_leave(self):
        """
        A demo row in a public payload is fixture data presented as analysis —
        the exact confusion the data-status panel existed to prevent.
        """
        from company_intelligence.models import CompanyControversy

        CompanyControversy.objects.create(
            company=self.profile, title='DEMO-ONLY-CONTROVERSY',
            category='environmental', severity='high', status='open',
            is_demo=True)
        CompanyControversy.objects.create(
            company=self.profile, title='Real Controversy',
            category='environmental', severity='high', status='open',
            is_demo=False)

        titles = [c['title'] for c in self.payload()['decision_risks']['controversies']]
        self.assertIn('Real Controversy', titles)
        self.assertNotIn('DEMO-ONLY-CONTROVERSY', titles)

    def test_the_shariah_disclaimer_travels_with_the_result(self):
        """
        In the same object, never as a page footnote. A methodology result
        separated from the statement that it is not a ruling becomes, to a
        reader, a ruling.
        """
        from api.v2_assessment import SHARIAH_DISCLAIMER

        shariah = self.payload().get('shariah')
        if shariah is None:
            self.skipTest('no Shariah screen for this fixture')
        self.assertEqual(shariah['disclaimer'], SHARIAH_DISCLAIMER)
        self.assertIn('not a religious ruling', shariah['disclaimer'].lower())

    def test_the_retired_panels_are_absent(self):
        """
        Four panels were audited and moved behind sign-in or removed. This
        endpoint is public; none of them may appear on it.
        """
        body = self.payload()
        for key in ('financing_matches', 'matched_pathways', 'data_status',
                    'harvest_sources', 'watchlist', 'stock', 'market_data'):
            with self.subTest(key=key):
                self.assertNotIn(key, body)


class AssessmentRoutingTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_unknown_slug_is_404(self):
        self.assertEqual(
            self.client.get('/api/v2/companies/nope/assessment/').status_code,
            404)

    def test_a_company_with_no_profile_is_404(self):
        Company.objects.create(name='No Profile', slug='no-profile-assess')
        self.assertEqual(
            self.client.get(
                '/api/v2/companies/no-profile-assess/assessment/').status_code,
            404)
