"""
Phase 11 — every public surface, verified against one fixture pair.

Two companies, identical stored numbers, different evidence:

    EVIDENCED   16 of 16 material inputs MEASURED   -> publishes
    LEGACY      16 of 16 LEGACY_UNKNOWN_PROVENANCE  -> publishes nothing

The pair matters more than either half. A surface that hides everything passes
half of these; a surface that shows everything passes the other half. Only a
surface that distinguishes them passes both — which is the entire claim of this
programme.
"""
from django.test import Client, TestCase

from companies import provenance as prov
from companies.eligibility import decide
from companies.evidence import (
    PENDING_HEADLINE, PROVENANCE_MEASURED, PROVENANCE_UNKNOWN,
)
from companies.scoring import recalculate_and_save
from companies.testing import populated
from league.models import Company

SCORE = 76.4


def _company(slug, origin):
    # The legacy league pillars are what Company.save() computes ecoiq_score
    # FROM, so a fixture that only passes ecoiq_score= has it recomputed away.
    company = Company.objects.create(
        name=slug.title(), slug=slug, country='UK',
        score_pollution_footprint=76, score_reduction_progress=76,
        score_investment=76, score_transparency=76, score_community_impact=76)
    profile = populated(company, ecoiq_total_score=SCORE, pollution_level='low')
    for key in sorted(prov.MATERIAL_METRIC_KEYS):
        prov.record(profile, key, origin, written_by='t')
    recalculate_and_save(profile)
    profile.refresh_from_db()
    profile.ecoiq_total_score = SCORE
    profile.save()
    company.refresh_from_db()
    return profile


class PublicSurfaces(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

        self.evidenced = _company('evidenced-co', PROVENANCE_MEASURED)
        self.legacy = _company('legacy-co', PROVENANCE_UNKNOWN)
        self.client = Client()

    # ── the premise ──────────────────────────────────────────────────────────

    def test_both_hold_the_same_stored_number(self):
        self.assertEqual(self.evidenced.ecoiq_total_score,
                         self.legacy.ecoiq_total_score)

    def test_only_one_is_publishable(self):
        self.assertTrue(decide(self.evidenced).is_published)
        self.assertFalse(decide(self.legacy).is_published)

    # ── company page ─────────────────────────────────────────────────────────

    def test_the_legacy_company_page_is_evidence_pending(self):
        body = self.client.get('/companies/legacy-co/').content.decode()

        self.assertIn(PENDING_HEADLINE, body)
        self.assertNotIn(str(SCORE), body)

    def test_the_evidenced_company_page_shows_its_score(self):
        body = self.client.get('/companies/evidenced-co/').content.decode()

        self.assertNotIn(PENDING_HEADLINE, body)
        self.assertIn(str(SCORE), body)

    def test_no_score_leaks_into_legacy_page_metadata(self):
        import re

        body = self.client.get('/companies/legacy-co/').content.decode()
        metas = ' '.join(re.findall(r'<meta[^>]*>', body))

        self.assertNotIn(str(SCORE), metas)

    def test_no_score_leaks_into_legacy_json_ld(self):
        """
        A number left in structured data is still published even when the
        visible one is hidden — and it is the copy machines read.
        """
        import re

        body = self.client.get('/companies/legacy-co/').content.decode()
        blocks = re.findall(
            r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', body, re.S)

        for block in blocks:
            with self.subTest(block=block[:60]):
                self.assertNotIn(str(SCORE), block)

    # ── directory ────────────────────────────────────────────────────────────

    def test_the_directory_renders(self):
        self.assertEqual(self.client.get('/companies/').status_code, 200)

    def test_the_directory_does_not_show_the_legacy_score(self):
        body = self.client.get('/companies/').content.decode()
        # The evidenced company may legitimately show SCORE, so this asserts on
        # the legacy row specifically.
        self.assertIn('Legacy-Co', body)
        legacy_row = body[body.index('Legacy-Co') - 600:body.index('Legacy-Co') + 600]
        self.assertNotIn(str(SCORE), legacy_row)

    # ── league ───────────────────────────────────────────────────────────────

    def test_the_league_renders(self):
        self.assertEqual(self.client.get('/league/').status_code, 200)

    def test_the_league_does_not_rank_the_legacy_company(self):
        """
        Asserted on the legacy ROW, not on the page. The evidenced company now
        legitimately appears with a score, so a page-wide "everything is
        pending" assertion would only pass while nothing could be published --
        which is the state this programme exists to leave behind.
        """
        body = self.client.get('/league/').content.decode()

        self.assertIn('Legacy-Co', body)
        at = body.index('Legacy-Co')
        row = body[max(0, at - 800):at + 800]
        self.assertNotIn(str(SCORE), row)

    def test_the_league_does_show_the_evidenced_company(self):
        body = self.client.get('/league/').content.decode()

        self.assertIn('Evidenced-Co', body)

    # ── API v2 ───────────────────────────────────────────────────────────────

    def test_api_v2_detail_is_null_for_legacy(self):
        payload = self.client.get('/api/v2/companies/legacy-co/').json()

        self.assertIsNone(payload['ecoiq_score'])
        self.assertEqual(payload['score_status'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(payload['evidence_coverage'], 0)
        self.assertEqual(payload['confidence'], 'INSUFFICIENT_EVIDENCE')

    def test_api_v2_detail_publishes_the_evidenced_company(self):
        payload = self.client.get('/api/v2/companies/evidenced-co/').json()

        self.assertEqual(payload['score_status'], 'PUBLISHED')
        self.assertEqual(payload['ecoiq_score'], SCORE)
        self.assertEqual(payload['evidence_coverage'], 100)
        self.assertNotEqual(payload['confidence'], 'INSUFFICIENT_EVIDENCE')

    def test_api_v2_list_carries_both_fields(self):
        rows = self.client.get('/api/v2/companies/').json()['results']

        for row in rows:
            with self.subTest(slug=row['slug']):
                self.assertIn('evidence_coverage', row)
                self.assertIn('confidence', row)

    def test_api_v2_withholds_the_rank_of_an_unpublishable_score(self):
        rows = {r['slug']: r for r in
                self.client.get('/api/v2/companies/').json()['results']}

        self.assertIsNone(rows['legacy-co']['rank'])

    def test_coverage_and_confidence_are_separate_fields(self):
        payload = self.client.get('/api/v2/companies/evidenced-co/').json()

        self.assertIsInstance(payload['evidence_coverage'], int)
        self.assertIsInstance(payload['confidence'], str)

    # ── financing ────────────────────────────────────────────────────────────

    def test_no_financing_claim_for_the_legacy_company(self):
        from companies.views import _get_financing_eligibility

        self.assertEqual(_get_financing_eligibility(self.legacy), [])

    def test_the_evidenced_company_may_receive_financing_claims(self):
        from companies.views import _get_financing_eligibility

        self.assertTrue(_get_financing_eligibility(self.evidenced))

    # ── mobile contract ──────────────────────────────────────────────────────

    def test_the_mobile_contract_is_null_aware(self):
        """
        Mobile reads API v2. The contract it depends on is that a withheld
        score is null with a status beside it, never a substituted number.
        """
        payload = self.client.get('/api/v2/companies/legacy-co/').json()

        self.assertIn('score_status', payload)
        self.assertIsNone(payload['ecoiq_score'])

    # ── seeded data can never qualify ────────────────────────────────────────

    def test_seeded_data_can_never_satisfy_eligibility(self):
        from companies.evidence import PROVENANCE_SEEDED

        seeded = _company('seeded-co', PROVENANCE_SEEDED)

        self.assertFalse(decide(seeded).is_published)
        self.assertIn(PENDING_HEADLINE,
                      self.client.get('/companies/seeded-co/').content.decode())
