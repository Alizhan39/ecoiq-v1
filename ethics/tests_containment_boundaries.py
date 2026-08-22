"""
D2b — the boundaries D2b must NOT have moved.

STEP 10 of the brief. The ethics and company-view changes alter what
`_get_harm_signals` and `_get_institutional_signals` return, and both feed the
public company page, the PDF report, the v1 API and the v2 API. That is a lot of
surface for a calculation-semantics change to reach, so these tests assert the
containment shipped in #238–#241 still holds afterwards:

  J  v1 API compatibility — the legacy contract is unchanged in shape
  K  v2 evidence semantics — null + status, never a stand-in number
  L  public company containment — an unevidenced organisation gets no scores,
     no rankings, no PDF and no ethics panel

These duplicate no assertions from companies/tests_public_containment.py or
api/tests_v2_evidence.py; they cover the specific paths D2b touched.
"""
from django.test import Client, TestCase

from companies.models import CompanyProfile
from companies.views import _get_harm_signals, _get_institutional_signals
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



def _company(name, slug, **kwargs):
    company = Company.objects.create(
        name=name, slug=slug, country='United Kingdom', ecoiq_score=71.4)
    return _populated(company=company, status='public', ecoiq_total_score=71.4, **kwargs)


class J_V1ApiCompatibility(TestCase):

    """
    v1 is the legacy public contract with unknowable integrators. D2b may change
    what a signal SAYS; it may not change the shape a client parses.
    """

    def setUp(self):
        # The API rate-limits anonymous callers to 20 requests/day through the
        # Django cache, which is NOT reset between tests. A full-suite run
        # exhausts it and later API tests receive 429 with a payload that has no
        # score keys -- a test-isolation problem that reads exactly like a
        # containment regression.
        from django.core.cache import cache
        cache.clear()

        self.profile = _company('V1 Compat Ltd', 'v1-compat-ltd')

    def test_j_harm_signal_shape_is_unchanged(self):
        signals = _get_harm_signals(self.profile)

        self.assertTrue(signals)
        for signal in signals:
            with self.subTest(signal=signal.get('id')):
                self.assertEqual(set(signal), {'id', 'label', 'status', 'penalty', 'detail'})
                self.assertIsInstance(signal['penalty'], int)
                self.assertIsInstance(signal['status'], str)
                self.assertIsInstance(signal['detail'], str)

    def test_j_penalty_is_always_a_number_never_null(self):
        """
        A null penalty would break arithmetic in an existing v1 client. Unknown
        is expressed by the STATUS, which is a string field that already carried
        several values — an added value is additive, a changed type is not.
        """
        unknown = _company('No Signals Ltd', 'no-signals-ltd')
        unknown.controversy_risk_score = None
        unknown.transparency_score_detail = None
        unknown.profit_extraction_score = None
        unknown.modernization_score = None

        for signal in _get_harm_signals(unknown):
            with self.subTest(signal=signal['id']):
                self.assertEqual(signal['penalty'], 0)
                self.assertIsNotNone(signal['penalty'])

    def test_j_every_signal_id_still_appears(self):
        """A client keying on `id` must not find one missing."""
        unknown = _company('Ids Intact Ltd', 'ids-intact-ltd')
        unknown.controversy_risk_score = None
        unknown.transparency_score_detail = None
        unknown.profit_extraction_score = None
        unknown.modernization_score = None

        ids = {s['id'] for s in _get_harm_signals(unknown)}
        self.assertEqual(
            ids, {'pollution', 'controversy', 'transparency',
                  'profit_extraction', 'transition_gap'})

    def test_j_unknown_uses_the_existing_repo_vocabulary(self):
        """
        Not a new evidence framework — 'insufficient_evidence' is the term
        company_intelligence and companies.evidence already use.
        """
        from companies.evidence import STATUS_INSUFFICIENT_EVIDENCE

        unknown = _company('Vocab Ltd', 'vocab-ltd')
        unknown.transparency_score_detail = None
        statuses = {s['status'] for s in _get_harm_signals(unknown)}

        self.assertIn('insufficient_evidence', statuses)
        self.assertEqual(STATUS_INSUFFICIENT_EVIDENCE.lower(), 'insufficient_evidence')


class K_V2EvidenceSemantics(TestCase):
    """v2 must still say null + status, and must not inherit a fabricated 0."""

    def setUp(self):
        _company('V2 Semantics Ltd', 'v2-semantics-ltd')

    def test_k_unevidenced_company_still_serialises_as_null(self):
        response = Client().get('/api/v2/companies/v2-semantics-ltd/')

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['ecoiq_score'])
        self.assertEqual(response.json()['score_status'], 'INSUFFICIENT_EVIDENCE')

    def test_k_harm_signals_in_v2_carry_their_own_status(self):
        """
        v2 includes harm_signals precisely because each one states its own
        confidence. An 'insufficient_evidence' signal must survive serialisation
        rather than being flattened into a clean one.

        Serialised in memory rather than through the HTTP client because
        transparency_score_detail is still NOT NULL — an unknown score cannot be
        SAVED until D4 makes these columns nullable. That is the whole reason
        D2b lands before D3/D4: the calculation layer must already handle None
        by the time the schema can produce one.
        """
        from api.v2_serializers import CompanyProfileV2Serializer

        profile = CompanyProfile.objects.get(company__slug='v2-semantics-ltd')
        profile.transparency_score_detail = None

        payload = CompanyProfileV2Serializer(profile).data
        transparency = [s for s in payload['harm_signals'] if s['id'] == 'transparency']

        self.assertEqual(len(transparency), 1)
        self.assertEqual(transparency[0]['status'], 'insufficient_evidence')
        self.assertEqual(transparency[0]['penalty'], 0)

    def test_k_rank_is_still_null_without_a_publishable_score(self):
        payload = Client().get('/api/v2/companies/').json()
        for row in payload['results']:
            with self.subTest(slug=row['slug']):
                if row['score_status'] != 'PUBLISHED':
                    self.assertIsNone(row['rank'])
                    self.assertIsNone(row['ecoiq_score'])


class L_PublicCompanyContainment(TestCase):
    """The D1.5 gate still fires before any of D2b's new output is reached."""

    def setUp(self):
        # The API rate-limits anonymous callers to 20 requests/day through the
        # Django cache, which is NOT reset between tests. A full-suite run
        # exhausts it and later API tests receive 429 with a payload that has no
        # score keys -- a test-isolation problem that reads exactly like a
        # containment regression.
        from django.core.cache import cache
        cache.clear()

        self.profile = _company('Contained Ltd', 'contained-ltd')
        self.body = Client().get('/companies/contained-ltd/').content.decode()

    def test_l_pending_state_still_shown(self):
        """
        The page is React; the wording lives in the assessment payload it
        reads. The document assertions in this class are unchanged and still
        apply — they check the number is absent, which is the half the server
        still owns.
        """
        from django.test import Client

        from companies.evidence import PENDING_HEADLINE

        payload = Client().get(
            '/api/v2/companies/contained-ltd/assessment/').json()
        self.assertIsNone(payload['ecoiq_score'])
        self.assertEqual(payload['evidence_note']['headline'], PENDING_HEADLINE)

    def test_l_the_synthetic_number_is_still_absent(self):
        self.assertNotIn('71.4', self.body)

    def test_l_no_ethics_panel_leaks_onto_the_pending_page(self):
        """
        The ethics layer sits below the gate in company_detail, so none of
        NEI/TSS/RVI may appear — the panel is not merely blanked, it is never
        computed for an organisation without evidence.
        """
        for marker in ('Ethical Intelligence Analysis', 'Net Ethical Impact',
                       'Transition Stewardship', 'Regenerative Value'):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, self.body)

    def test_l_no_institutional_signal_labels_leak(self):
        for marker in ('Governance Risk', 'Financing Compatibility',
                       'Public Benefit Alignment'):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, self.body)

    def test_l_pdf_report_is_still_refused(self):
        self.assertEqual(
            Client().get('/companies/contained-ltd/report/').status_code, 404)

    def test_l_institutional_signals_never_label_an_unknown_negatively(self):
        """
        Below the gate, individual fields can still be unknown. The old `else:`
        branch published 'High Risk', 'Early Stage', 'Limited' and 'Poor' for a
        company that had simply not been measured.
        """
        blank = _company('Unmeasured Ltd', 'unmeasured-ltd')
        for field in ('transparency_score_detail', 'anti_corruption_score',
                      'energy_transition_score', 'future_readiness_score',
                      'modernization_score', 'ecoiq_total_score',
                      'audit_quality_score', 'public_benefit_score'):
            setattr(blank, field, None)

        values = {s['value'] for s in _get_institutional_signals(blank)}
        levels = {s['level'] for s in _get_institutional_signals(blank)}

        for forbidden in ('High Risk', 'Early Stage', 'Limited', 'Poor', 'Developing'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, values)
        self.assertIn('insufficient_evidence', levels)
        self.assertNotIn('critical', levels)

    def test_l_institutional_signals_still_judge_real_evidence(self):
        """The guard must not have made every company unassessable."""
        measured = _company('Measured Ltd', 'measured-ltd')
        measured.transparency_score_detail = 20.0
        measured.anti_corruption_score = 20.0

        governance = next(s for s in _get_institutional_signals(measured)
                          if s['label'] == 'Governance Risk')
        self.assertEqual(governance['value'], 'High Risk')
        self.assertEqual(governance['level'], 'critical')
