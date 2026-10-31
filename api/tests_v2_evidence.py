"""
API v2 — truthful evidence contract.

Covers invariants A–F and I from the API migration brief. G and H are Flutter
concerns and belong to API-B; there is no Dart test runner in this suite, so
asserting them here would be theatre.

The invariant everything else serves: a consumer must be able to tell "EcoIQ has
no defensible score" from "EcoIQ scored this zero". v1 cannot express that
difference at all — a numeric field has no way to say "unknown" — which is why
v2 exists rather than v1 being edited in place.
"""
from django.core.cache import cache
from django.test import Client, TestCase

from companies.models import CompanyProfile
from league.models import Company


class EvidenceApiTestCase(TestCase):
    """
    Base case that clears the throttle cache between tests.

    DRF rate-limits anonymous callers to 20/day (settings.REST_FRAMEWORK
    DEFAULT_THROTTLE_RATES) and keeps the counter in the default cache, which
    persists for the whole test run. Without this, tests later in the module
    receive 429 and fail for a reason that has nothing to do with what they
    assert.

    Clearing the cache is test isolation, not a relaxation: the throttle itself
    is untouched, and each test starts from the same clean state a real first
    caller would.
    """

    def setUp(self):
        super().setUp()
        cache.clear()


def _company(name, slug, score=71.4, **profile_kwargs):
    company = Company.objects.create(
        name=name, slug=slug, country='United Kingdom', ecoiq_score=score)
    profile_kwargs.setdefault('ecoiq_total_score', score)
    CompanyProfile.objects.create(company=company, status='public', **profile_kwargs)
    return company


class InvariantA_UnevidencedScoreIsNull(EvidenceApiTestCase):

    def setUp(self):
        super().setUp()
        _company('Unevidenced Ltd', 'unevidenced-ltd')
        self.detail = Client().get('/api/v2/companies/unevidenced-ltd/').json()
        self.listing = Client().get('/api/v2/companies/').json()['results'][0]

    def test_detail_score_is_null(self):
        self.assertIsNone(self.detail['ecoiq_score'])

    def test_list_score_is_null(self):
        self.assertIsNone(self.listing['ecoiq_score'])

    def test_score_is_not_a_stand_in_value(self):
        """
        The whole point. Every one of these would be a false statement, and
        `0` is the one the current v1 + Flutter combination actually produces.
        """
        for forbidden in (0, 0.0, 50, 50.0, -1, '', 'N/A', 'null'):
            with self.subTest(forbidden=forbidden):
                self.assertNotEqual(self.detail['ecoiq_score'], forbidden)

    def test_rank_is_also_null(self):
        """A rank asserts a comparison the score is withholding."""
        self.assertIsNone(self.listing['rank'])


class InvariantB_StatusIsExplicit(EvidenceApiTestCase):

    def setUp(self):
        super().setUp()
        _company('Status Ltd', 'status-ltd')
        self.payload = Client().get('/api/v2/companies/status-ltd/').json()

    def test_status_says_insufficient_evidence(self):
        self.assertEqual(self.payload['score_status'], 'INSUFFICIENT_EVIDENCE')

    def test_coverage_is_reported(self):
        self.assertEqual(self.payload['evidence_coverage'], 0)

    def test_a_human_readable_note_is_included(self):
        self.assertIn('sufficient verified evidence', self.payload['evidence_note'])

    def test_note_makes_no_claim_about_the_company(self):
        note = self.payload['evidence_note'].lower()
        for forbidden in ('poor', 'unrated', 'zero', 'bad', 'low score'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, note)


class InvariantsCDE_RealValuesSurvive(EvidenceApiTestCase):
    """
    C: an evidence-backed score stays numeric.
    D: a genuine measured 0 stays 0, not unknown.
    E: a genuine measured 50 stays 50, not unknown.

    D and E are the reason this contract keys on status rather than on the
    numeral. Today no profile can reach PUBLISHED — nothing carries evidence
    provenance yet — so these assert the serializer's behaviour directly, which
    is the honest way to test a path the data cannot yet reach. When D3 lands
    and real provenance exists, the same expectations hold end-to-end.
    """

    def _serialize(self, score):
        from api.v2_serializers import CompanyProfileV2Serializer
        from companies.evidence import PublicScoreState, STATUS_PUBLISHED

        company = _company(f'Real {score}', f'real-{str(score).replace(".", "-")}')
        profile = company.profile
        # Force the published state: this tests the contract, not the gate.
        profile._v2_score_state = PublicScoreState(
            available=True, score=score, status=STATUS_PUBLISHED, coverage_percent=87)
        return CompanyProfileV2Serializer(profile).data

    def test_c_evidenced_score_is_numeric(self):
        data = self._serialize(78.4)
        self.assertEqual(data['ecoiq_score'], 78.4)
        self.assertEqual(data['score_status'], 'PUBLISHED')
        self.assertEqual(data['evidence_coverage'], 87)
        self.assertIsNone(data['evidence_note'])

    def test_d_measured_zero_stays_zero(self):
        data = self._serialize(0.0)
        self.assertEqual(data['ecoiq_score'], 0.0)
        self.assertIsNotNone(data['ecoiq_score'],
                             'a measured 0 was reported as unknown')
        self.assertEqual(data['score_status'], 'PUBLISHED')

    def test_e_measured_fifty_stays_fifty(self):
        data = self._serialize(50.0)
        self.assertEqual(data['ecoiq_score'], 50.0)
        self.assertEqual(data['score_status'], 'PUBLISHED')

    def test_zero_and_unknown_are_distinguishable(self):
        """The single most important line in this file."""
        measured_zero = self._serialize(0.0)
        unknown = Client().get(
            f'/api/v2/companies/{_company("Unknown Co", "unknown-co").slug}/').json()

        self.assertEqual(measured_zero['ecoiq_score'], 0.0)
        self.assertIsNone(unknown['ecoiq_score'])
        self.assertNotEqual(measured_zero['score_status'], unknown['score_status'])


class InvariantI_RankingWithholdsRatherThanZeroes(EvidenceApiTestCase):

    def setUp(self):
        super().setUp()
        for i in range(3):
            _company(f'Rank {i} Ltd', f'rank-{i}-ltd')
        self.payload = Client().get('/api/v2/leaderboard/').json()

    def test_unevidenced_companies_are_not_ranked(self):
        self.assertEqual(self.payload['leaderboard'], [])

    def test_they_are_not_ranked_as_zero_either(self):
        self.assertEqual(self.payload['count'], 0)

    def test_the_response_says_how_many_were_withheld(self):
        """
        Without this a caller cannot tell 'nothing qualifies' from 'nothing
        exists', and would be free to conclude the wrong one.
        """
        self.assertEqual(self.payload['withheld_insufficient_evidence'], 3)


class InvariantF_V1RemainsIntact(EvidenceApiTestCase):
    """
    v1 is untouched. This is the compatibility guarantee that makes shipping v2
    safe, so it is asserted rather than assumed — a later change that quietly
    altered v1 would fail here.
    """

    def setUp(self):
        super().setUp()
        _company('Compat Ltd', 'compat-ltd')

    def test_v1_leaderboard_still_returns_a_numeric_score(self):
        payload = Client().get('/api/v1/leaderboard/').json()
        self.assertIn('leaderboard', payload)
        if payload['leaderboard']:
            self.assertIsNotNone(payload['leaderboard'][0]['ecoiq_score'])

    def test_v1_company_detail_still_responds(self):
        self.assertEqual(Client().get('/api/v1/companies/compat-ltd/').status_code, 200)

    def test_v1_namespace_still_reverses(self):
        from django.urls import reverse
        self.assertTrue(reverse('api:leaderboard').startswith('/api/v1/'))

    def test_v2_namespace_is_separate(self):
        from django.urls import reverse
        self.assertTrue(reverse('api_v2:leaderboard').startswith('/api/v2/'))


class V2IsAnonymousLikeV1Tests(EvidenceApiTestCase):
    """v2 is a truthfulness change, not a privilege change."""

    def setUp(self):
        super().setUp()
        _company('Anon Ltd', 'anon-ltd')

    def test_every_v2_endpoint_answers_anonymously(self):
        anonymous = Client()
        for path in ('/api/v2/', '/api/v2/companies/',
                     '/api/v2/companies/anon-ltd/', '/api/v2/leaderboard/'):
            with self.subTest(path=path):
                self.assertEqual(anonymous.get(path).status_code, 200)


class V2RootDocumentsTheContractTests(EvidenceApiTestCase):

    def test_root_names_v2_canonical_and_v1_legacy(self):
        payload = Client().get('/api/v2/').json()
        self.assertEqual(payload['status'], 'canonical')
        self.assertEqual(payload['v1']['status'], 'legacy-compatibility')

    def test_root_lists_the_status_vocabulary(self):
        payload = Client().get('/api/v2/').json()
        self.assertIn('PUBLISHED', payload['score_status_values'])
        self.assertIn('INSUFFICIENT_EVIDENCE', payload['score_status_values'])


class NoDuplicateStatusFrameworkTests(EvidenceApiTestCase):
    """
    v2 must report companies.evidence's vocabulary, not invent a parallel one.
    """

    def test_status_strings_come_from_the_evidence_module(self):
        from companies.evidence import (
            STATUS_INSUFFICIENT_EVIDENCE, STATUS_PUBLISHED,
        )
        payload = Client().get('/api/v2/').json()
        self.assertEqual(
            sorted(payload['score_status_values']),
            sorted([STATUS_PUBLISHED, STATUS_INSUFFICIENT_EVIDENCE]))
