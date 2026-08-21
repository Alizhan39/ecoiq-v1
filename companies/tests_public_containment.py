"""
D1.5 — public truthfulness containment.

Invariants A–E from the brief, asserted against the real public surfaces rather
than against the helper in isolation. A test that only exercised
`public_score_state()` would pass while a template still printed the number.

The load-bearing idea: absence of evidence about a company is a fact about
EcoIQ, not a fact about the company. Nothing here may say or imply that an
unevidenced organisation is poor, zero, neutral or bottom-ranked.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from companies.evidence import (
    PENDING_HEADLINE, STATUS_INSUFFICIENT_EVIDENCE, public_score_state,
)
from companies.models import CompanyProfile
from league.models import Company


def _populated(company, **fields):
    """
    A profile whose material inputs are EXPLICIT.

    Before D4C these fixtures set no scores at all and relied on
    default=50.0 to invent sixteen of them. The tests read as though they
    set up a company; they set up nothing. Now the data is stated, and a
    caller that wants an unknown overrides that one field by name.
    """
    from companies.models import CompanyProfile
    from companies.testing import MATERIAL_FIELDS, FIXTURE_VALUE

    values = {name: FIXTURE_VALUE for name in MATERIAL_FIELDS}
    values.update(fields)
    return CompanyProfile.objects.create(company=company, **values)



def _profile(name, slug, **kwargs):
    company = Company.objects.create(
        name=name, slug=slug, country='United Kingdom', ecoiq_score=71.4)
    return _populated(company=company, status='public', ecoiq_total_score=71.4, **kwargs)


class InvariantA_NoPublicScoreWithoutEvidence(TestCase):
    """Zero evidence must not produce a public numerical EcoIQ Score."""

    def setUp(self):
        self.profile = _profile('Unevidenced Ltd', 'unevidenced-ltd')
        self.body = Client().get('/companies/unevidenced-ltd/').content.decode()

    def test_page_still_serves(self):
        """Containment, not removal — the URL must not start 404ing."""
        self.assertEqual(Client().get('/companies/unevidenced-ltd/').status_code, 200)

    def test_the_number_is_absent_from_the_page(self):
        self.assertNotIn('71.4', self.body)

    def test_the_pending_state_is_shown_instead(self):
        self.assertIn(PENDING_HEADLINE, self.body)

    def test_no_score_appears_in_structured_data(self):
        """
        Hiding the number on screen while leaving it in schema.org markup would
        still publish it to every machine reader.
        """
        self.assertNotIn('EcoIQ Score', self.body)
        self.assertNotIn('ratingValue', self.body)

    def test_no_score_appears_in_meta_or_opengraph(self):
        for marker in ('climate intelligence score', 'climate score', '/100'):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, self.body)

    def test_page_makes_no_negative_claim_about_the_company(self):
        """
        The failure mode worth guarding: 'no evidence' must never be rendered as
        'bad', 'zero' or 'unrated'.
        """
        lowered = self.body.lower()
        for forbidden in ('poor score', 'unrated', 'score: 0', 'score 0/100', '0/100'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, lowered)

    def test_helper_agrees_with_the_page(self):
        state = public_score_state(self.profile)
        self.assertFalse(state.available)
        self.assertIsNone(state.score)
        self.assertEqual(state.status, STATUS_INSUFFICIENT_EVIDENCE)


class InvariantB_NoRankWithoutEvidence(TestCase):
    """Zero evidence must not produce a public company rank."""

    def setUp(self):
        for i in range(3):
            _profile(f'Ranked {i} Ltd', f'ranked-{i}-ltd')
        self.body = Client().get('/league/').content.decode()

    def test_unevidenced_companies_are_absent_from_the_league_table(self):
        for i in range(3):
            with self.subTest(i=i):
                self.assertNotIn(f'/league/ranked-{i}-ltd/', self.body)

    def test_no_score_numbers_leak_into_the_table(self):
        self.assertNotIn('71.4', self.body)

    def test_empty_state_explains_evidence_rather_than_filtering(self):
        """
        'No companies found for the selected sector' would be a different and
        untrue explanation for why the table is empty.
        """
        self.assertIn(PENDING_HEADLINE, self.body)
        self.assertNotIn('No companies found for the selected sector', self.body)

    def test_companies_are_not_given_a_bottom_rank_instead(self):
        lowered = self.body.lower()
        for forbidden in ('unranked', 'not ranked', 'rank 0'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, lowered)


class InvariantC_NoFinancingEstimateWithoutEvidence(TestCase):
    """Zero evidence must not produce an authoritative financing estimate."""

    def setUp(self):
        _profile('Finance Ltd', 'finance-ltd')

    def test_company_page_shows_no_capex_or_savings_figures(self):
        body = Client().get('/companies/finance-ltd/').content.decode().lower()
        for marker in ('transition capex', 'annual savings', 'payback', 'investment required'):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, body)

    def test_downloadable_report_is_not_produced(self):
        """
        A PDF leaves the site and carries no context. Gating the page while
        still emitting the same figures as a document would defeat containment.
        """
        self.assertEqual(Client().get('/companies/finance-ltd/report.pdf').status_code, 404)


class InvariantD_MeasuredFiftyIsNotMissing(TestCase):
    """
    A genuine value of exactly 50 must not be treated as missing.

    Evidence status decides truthfulness, not the numeral. This is the invariant
    that forbids a blanket `50 -> NULL` migration.
    """

    def test_evidence_status_not_the_number_decides(self):
        """
        Two identical stored 50s, different provenance — the distinction must
        survive.

        Established against the provenance STORE rather than
        field_provenance(), whose default-comparison heuristic D4C made inert:
        with no model defaults left there is nothing to compare a value
        against. The store is the authority that heuristic was approximating,
        and wiring coverage onto it is D5's first job.
        """
        from companies import provenance as prov
        from companies.evidence import PROVENANCE_MEASURED, PROVENANCE_SEEDED

        evidenced = _profile(
            'Fifty Evidenced', 'fifty-evidenced',
            waste_management_score=50.0,
            public_sources=[{'url': 'https://example.org/audit',
                             'title': 'Waste audit'}])
        bare = _profile('Fifty Bare', 'fifty-bare', waste_management_score=50.0)
        prov.record(evidenced, 'waste_management_score', PROVENANCE_MEASURED,
                    written_by='analyst')
        prov.record(bare, 'waste_management_score', PROVENANCE_SEEDED,
                    written_by='seed:test')

        self.assertEqual(evidenced.waste_management_score,
                         bare.waste_management_score)
        self.assertEqual(prov.current(bare, 'waste_management_score').origin,
                         PROVENANCE_SEEDED)
        self.assertNotEqual(
            prov.current(evidenced, 'waste_management_score').origin,
            PROVENANCE_SEEDED)


class InvariantE_SyntheticDataStaysInternal(TestCase):
    """
    Seeded data remains available internally and is never presented publicly as
    measured evidence.
    """

    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user(
            username='containment-staff', is_staff=True)

    def setUp(self):
        self.profile = _profile('Internal Ltd', 'internal-ltd')

    def test_the_value_is_not_deleted_from_the_database(self):
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.ecoiq_total_score, 71.4)

    def test_staff_still_see_the_full_profile(self):
        client = Client()
        client.force_login(self.staff)
        response = client.get('/companies/internal-ltd/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('71.4', response.content.decode())

    def test_staff_still_see_the_full_league_table(self):
        client = Client()
        client.force_login(self.staff)
        self.assertIn('/league/internal-ltd/', client.get('/league/').content.decode())

    def test_anonymous_visitors_do_not(self):
        self.assertNotIn('71.4', Client().get('/companies/internal-ltd/').content.decode())


class DirectoryCardsTests(TestCase):
    """The directory renders a ring and four pillar bars — all score in disguise."""

    def setUp(self):
        _profile('Card Ltd', 'card-ltd')

    def test_cards_show_no_score_number(self):
        body = Client().get('/companies/').content.decode()
        self.assertNotIn('71.4', body)

    def test_cards_show_the_pending_state(self):
        self.assertIn(PENDING_HEADLINE, Client().get('/companies/').content.decode())


class ApiContractUnchangedTests(TestCase):
    """
    The public API is deliberately NOT changed in this PR, and that decision is
    pinned here so it is a choice rather than an oversight.

    mobile/lib/data/models/company.dart parses the field as

        double.tryParse('${json['ecoiq_score']}') ?? 0

    so emitting null would make the shipped client display 0 — relocating the
    'unknown becomes the worst score' falsehood into the app instead of removing
    it. The API needs a versioned change alongside a client release; see the
    plan's D5.
    """

    def setUp(self):
        _profile('Api Ltd', 'api-ltd')

    def test_leaderboard_endpoint_still_returns_a_numeric_score(self):
        response = Client().get('/api/v1/leaderboard/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('leaderboard', payload)
        if payload['leaderboard']:
            self.assertIsNotNone(payload['leaderboard'][0].get('ecoiq_score'))
