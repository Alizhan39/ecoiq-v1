"""
D3C-3d — financing and QDF lineage.

Two persisted derived writers, neither of which needs `recorded_value`. Covers
A–AL. No Mizan, no ML, no greenwashing, no ingestion.

Both are the first writers to consume the DERIVED layer directly:
financing.readiness reads the composite and two pillars, QDF reads five pillars.
So they are also the first real regression test for the transitive
defensibility rule #251 introduced — contamination now sits two or three layers
beneath the value being judged.
"""
from unittest.mock import patch

from django.db import transaction
from django.test import SimpleTestCase, TestCase

from companies import metric_registry as registry
from companies import provenance as prov
from companies.evidence import (
    PROVENANCE_MEASURED, PROVENANCE_MODELLED, PROVENANCE_SEEDED, PROVENANCE_UNKNOWN,
)
from companies.models import CompanyMetricProvenance, CompanyProfile
from companies.scoring import recalculate_and_save
from financing.matching import (
    FINANCING_INPUTS, FINANCING_METHOD, FINANCING_METRIC_KEY, FINANCING_VERSION,
)
from financing.matching import compute_and_save as financing_save
from league.models import Company


def _populated(company, **fields):
    """
    A profile whose material inputs are EXPLICIT.

    Before D4C these fixtures set no scores at all and relied on
    default=50.0 to invent sixteen of them. The tests read as though they
    set up a company; they set up nothing. Now the data is stated, and a
    caller that wants an unknown overrides that one field by name.
    """
    from companies.testing import MATERIAL_FIELDS, FIXTURE_VALUE

    values = {name: FIXTURE_VALUE for name in MATERIAL_FIELDS}
    values.update(fields)
    return CompanyProfile.objects.create(company=company, **values)

from qdf.scoring import QDF_INPUTS, QDF_METHOD, QDF_METRIC_KEY, QDF_VERSION
from qdf.scoring import compute_and_save as qdf_save

WRITERS = (
    (FINANCING_METRIC_KEY, FINANCING_INPUTS, FINANCING_METHOD, FINANCING_VERSION,
     financing_save, 'financing.matching.compute_and_save'),
    (QDF_METRIC_KEY, QDF_INPUTS, QDF_METHOD, QDF_VERSION,
     qdf_save, 'qdf.scoring.compute_and_save'),
)


def _profile(slug, **kwargs):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    return _populated(company=company, status='public',
                                         pollution_level='low', **kwargs)


def _build_chain(profile, origin=PROVENANCE_MEASURED, writer='ingestion', limit=None):
    """
    Build the real provenance chain: material rows, then the pillars and
    composite that recalculate_and_save produces from them.

    The financing and QDF inputs are mostly DERIVED, so a fixture that recorded
    them by hand would be asserting a shape the pipeline never produces.
    """
    keys = sorted(prov.MATERIAL_METRIC_KEYS)
    for key in (keys if limit is None else keys[:limit]):
        if registry.resolve_value(profile, key) is not None:
            prov.record(profile, key, origin, written_by=writer)
    recalculate_and_save(profile)
    return {row.metric_key: row for row in
            CompanyMetricProvenance.objects.filter(company=profile, is_current=True)}


class RegistryAndSemantics(SimpleTestCase):

    def test_both_metrics_are_registered_derived(self):
        for key in (FINANCING_METRIC_KEY, QDF_METRIC_KEY):
            with self.subTest(key=key):
                self.assertEqual(registry.REGISTRY[key].kind, registry.DERIVED)

    def test_the_registered_keys_are_the_repository_canonical_ones(self):
        """Verified against the registry, not taken from the brief."""
        self.assertEqual(FINANCING_METRIC_KEY, 'financing.readiness')
        self.assertEqual(QDF_METRIC_KEY, 'qdf.decision_integrity')

    def test_financing_provenance_covers_only_readiness(self):
        """
        STEP 3 — CompanyFinancingProfile persists eleven values. Only
        financing.readiness is registered, so this writer attests to that one.
        In particular it must not imply provenance for the capex estimates,
        which #242 found fabricated from an invented $50m revenue.
        """
        from financing.models import CompanyFinancingProfile

        persisted = {f.name for f in CompanyFinancingProfile._meta.get_fields()}
        for uncovered in ('estimated_capex_low_usd', 'estimated_capex_high_usd',
                          'estimated_annual_impact_usd', 'climate_readiness',
                          'governance_readiness'):
            with self.subTest(field=uncovered):
                self.assertIn(uncovered, persisted)
                self.assertNotIn(f'financing.{uncovered}', registry.VALID_KEYS)

    def test_every_declared_input_is_registered(self):
        for _key, inputs, _m, _v, _fn, _w in WRITERS:
            for item in inputs:
                with self.subTest(metric=_key, input=item):
                    self.assertIn(item, registry.VALID_KEYS)

    def test_both_consume_the_derived_layer_directly(self):
        """STEP 7 — the graph should say what the formula does."""
        self.assertIn('company.ecoiq_total', FINANCING_INPUTS)
        self.assertIn('company.modernization', FINANCING_INPUTS)
        self.assertIn('company.public_benefit', QDF_INPUTS)

    def test_the_two_input_sets_are_different(self):
        self.assertNotEqual(set(FINANCING_INPUTS), set(QDF_INPUTS))

    def test_neither_uses_recorded_value(self):
        """STEP 20 — both are persisted, so the canonical value stays on its model."""
        for key in (FINANCING_METRIC_KEY, QDF_METRIC_KEY):
            with self.subTest(key=key):
                self.assertFalse(registry.REGISTRY[key].is_ephemeral)


class NoCircularDependency(SimpleTestCase):
    """
    STEP 19 — if financing consumed QDF and QDF consumed financing, encoding
    that would create a provenance cycle. Checked, not assumed.
    """

    def test_neither_calculator_consumes_the_other(self):
        self.assertNotIn(QDF_METRIC_KEY, FINANCING_INPUTS)
        self.assertNotIn(FINANCING_METRIC_KEY, QDF_INPUTS)

    def test_neither_module_imports_the_other(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        financing_src = (root / 'financing' / 'matching.py').read_text()
        qdf_src = (root / 'qdf' / 'scoring.py').read_text()

        self.assertNotIn('from qdf', financing_src)
        self.assertNotIn('from financing', qdf_src)


class A_B_C_D_E_RowContents(TestCase):

    def setUp(self):
        # The API rate-limits anonymous callers to 20 requests/day through the
        # Django cache, which is NOT reset between tests. A full-suite run
        # exhausts it and later API tests receive 429 with a payload that has no
        # score keys -- a test-isolation problem that reads exactly like a
        # containment regression.
        from django.core.cache import cache
        cache.clear()

        self.profile = _profile('contents')
        self.chain = _build_chain(self.profile)
        financing_save(self.profile)
        qdf_save(self.profile)

    def test_a_r_both_get_modelled_origin(self):
        for key, *_ in WRITERS:
            with self.subTest(key=key):
                row = prov.current(self.profile, key)
                self.assertIsNotNone(row)
                self.assertEqual(row.origin, PROVENANCE_MODELLED)
                self.assertNotEqual(row.origin, PROVENANCE_MEASURED)

    def test_b_s_methodology_recorded(self):
        for key, _i, method, *_ in WRITERS:
            with self.subTest(key=key):
                self.assertEqual(prov.current(self.profile, key).methodology, method)

    def test_c_t_version_recorded_and_not_a_sha(self):
        for key, _i, _m, version, *_ in WRITERS:
            with self.subTest(key=key):
                self.assertEqual(
                    prov.current(self.profile, key).calculation_version, version)
                self.assertNotRegex(version, r'^[0-9a-f]{7,}$')

    def test_d_u_exact_inputs_attached(self):
        for key, inputs, *_ in WRITERS:
            with self.subTest(key=key):
                linked = {r.metric_key
                          for r in prov.lineage(prov.current(self.profile, key))}
                self.assertEqual(linked, set(inputs))

    def test_c_the_writer_is_named(self):
        for key, _i, _m, _v, _fn, writer in WRITERS:
            with self.subTest(key=key):
                self.assertEqual(prov.current(self.profile, key).written_by, writer)

    def test_e_v_unrelated_provenance_is_not_attached(self):
        """QDF does not read financing readiness, and vice versa."""
        financing_linked = {
            r.metric_key for r in
            prov.lineage(prov.current(self.profile, FINANCING_METRIC_KEY))}
        qdf_linked = {
            r.metric_key for r in
            prov.lineage(prov.current(self.profile, QDF_METRIC_KEY))}

        self.assertNotIn(QDF_METRIC_KEY, financing_linked)
        self.assertNotIn(FINANCING_METRIC_KEY, qdf_linked)
        self.assertNotIn('jobs_created_score', financing_linked)

    def test_no_review_is_fabricated(self):
        """STEP 21 — calculation success is not review."""
        for key, *_ in WRITERS:
            with self.subTest(key=key):
                row = prov.current(self.profile, key)
                self.assertEqual(row.review_status, 'proposed')
                self.assertIsNone(row.reviewed_by)
                self.assertIsNone(row.confidence)

    def test_the_value_resolves_rather_than_being_copied(self):
        for key, *_ in WRITERS:
            with self.subTest(key=key):
                row = prov.current(self.profile, key)
                self.assertIsNone(row.recorded_value)
                self.assertIsNotNone(row.value)


class F_W_MissingProvenanceIsNeverGuessed(TestCase):

    def test_f_w_no_input_provenance_means_no_derived_row(self):
        """The production state today: values exist, provenance does not."""
        profile = _profile('no-prov')

        fp = financing_save(profile)
        assessment = qdf_save(profile)

        self.assertEqual(fp.provenance_status, 'incomplete')
        self.assertEqual(assessment.provenance_status, 'incomplete')
        self.assertIsNone(prov.current(profile, FINANCING_METRIC_KEY))
        self.assertIsNone(prov.current(profile, QDF_METRIC_KEY))

    def test_f_w_the_numbers_are_still_computed(self):
        profile = _profile('still-computed')

        fp = financing_save(profile)

        self.assertIsNotNone(fp.financing_readiness)

    def test_f_w_nothing_is_invented_to_fill_the_gap(self):
        profile = _profile('no-invention')
        financing_save(profile)
        qdf_save(profile)

        self.assertEqual(CompanyMetricProvenance.objects.count(), 0,
                         'no LEGACY or SEEDED row may be conjured here')

    def test_partial_provenance_is_still_incomplete(self):
        profile = _profile('partial')
        chain = _build_chain(profile)
        chain['company.modernization'].delete()

        fp = financing_save(profile)

        self.assertEqual(fp.provenance_status, 'incomplete')
        self.assertIsNone(prov.current(profile, FINANCING_METRIC_KEY))


class G_H_I_X_Y_Z_Idempotency(TestCase):

    def setUp(self):
        self.profile = _profile('churn')
        self.chain = _build_chain(self.profile)
        financing_save(self.profile)
        qdf_save(self.profile)

    def _count(self, key):
        return CompanyMetricProvenance.objects.filter(
            company=self.profile, metric_key=key).count()

    def test_g_x_an_identical_recalculation_creates_no_churn(self):
        financing_save(self.profile)
        qdf_save(self.profile)

        for key, *_ in WRITERS:
            with self.subTest(key=key):
                self.assertEqual(self._count(key), 1)

    def test_g_x_the_status_says_unchanged(self):
        self.assertEqual(financing_save(self.profile).provenance_status, 'unchanged')
        self.assertEqual(qdf_save(self.profile).provenance_status, 'unchanged')

    def test_h_y_a_changed_input_creates_a_new_event(self):
        """
        transparency_score_detail feeds a pillar the financing formula consumes,
        so re-running the chain gives financing a new input row to cite.
        """
        prov.record(self.profile, 'transparency_score_detail', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)

        fp = financing_save(self.profile)

        self.assertEqual(fp.provenance_status, 'recorded')
        self.assertEqual(self._count(FINANCING_METRIC_KEY), 2)

    def test_i_z_a_version_change_creates_a_new_event(self):
        with patch('financing.matching.FINANCING_VERSION', '2'):
            financing_save(self.profile)
        with patch('qdf.scoring.QDF_VERSION', '2'):
            qdf_save(self.profile)

        for key, *_ in WRITERS:
            with self.subTest(key=key):
                self.assertEqual(self._count(key), 2)

    def test_a_methodology_change_creates_a_new_event(self):
        with patch('qdf.scoring.QDF_METHOD', 'ecoiq-qdf-decision-integrity-v2'):
            qdf_save(self.profile)

        self.assertEqual(self._count(QDF_METRIC_KEY), 2)


class I_AA_HistoryAsComputed(TestCase):

    def setUp(self):
        self.profile = _profile('history')
        self.chain = _build_chain(self.profile)
        financing_save(self.profile)
        qdf_save(self.profile)
        self.first_financing = prov.current(self.profile, FINANCING_METRIC_KEY)
        self.first_qdf = prov.current(self.profile, QDF_METRIC_KEY)

    def _rebuild(self):
        prov.record(self.profile, 'transparency_score_detail', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)
        financing_save(self.profile)
        qdf_save(self.profile)

    def test_i_financing_lineage_stays_pinned(self):
        old_pillar = self.chain['company.transparency_governance']
        self._rebuild()

        self.first_financing.refresh_from_db()
        old_pillar.refresh_from_db()

        self.assertFalse(self.first_financing.is_current)
        self.assertFalse(old_pillar.is_current)
        self.assertIn(old_pillar, prov.lineage(self.first_financing),
                      'historical lineage must not drift to current rows')

    def test_aa_qdf_lineage_stays_pinned(self):
        old_pillar = self.chain['company.transparency_governance']
        self._rebuild()

        self.first_qdf.refresh_from_db()
        self.assertFalse(self.first_qdf.is_current)
        self.assertIn(old_pillar, prov.lineage(self.first_qdf))

    def test_the_new_rows_point_at_the_new_pillar(self):
        self._rebuild()
        new_pillar = prov.current(self.profile, 'company.transparency_governance')

        for key, *_ in WRITERS:
            with self.subTest(key=key):
                self.assertIn(new_pillar,
                              prov.lineage(prov.current(self.profile, key)))


class J_AB_Atomicity(TestCase):

    def test_j_financing_provenance_failure_rolls_back_the_value(self):
        profile = _profile('rollback-fin')
        _build_chain(profile)
        financing_save(profile)
        from financing.models import CompanyFinancingProfile
        before = CompanyFinancingProfile.objects.get(profile=profile).financing_readiness

        # A changed VALUE is not a changed lineage — the identity rule would
        # return 'unchanged', record_derived would never be called, and the
        # injected failure would never fire. The provenance must change.
        prov.record(profile, 'transparency_score_detail', PROVENANCE_SEEDED)
        recalculate_and_save(profile)

        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record_derived',
                       side_effect=RuntimeError('provenance failed')):
                financing_save(profile)

        after = CompanyFinancingProfile.objects.get(profile=profile).financing_readiness
        self.assertEqual(after, before, 'the value must roll back with its lineage')

    def test_ab_qdf_provenance_failure_rolls_back_the_value(self):
        from qdf.models import DecisionAssessment

        profile = _profile('rollback-qdf')
        _build_chain(profile)
        qdf_save(profile)
        before = DecisionAssessment.objects.get(
            profile=profile, source='auto').decision_integrity_score

        prov.record(profile, 'jobs_created_score', PROVENANCE_SEEDED)
        recalculate_and_save(profile)

        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record_derived',
                       side_effect=RuntimeError('provenance failed')):
                qdf_save(profile)

        after = DecisionAssessment.objects.get(
            profile=profile, source='auto').decision_integrity_score
        self.assertEqual(after, before)

    def test_a_value_save_failure_leaves_no_provenance(self):
        from financing.models import CompanyFinancingProfile

        profile = _profile('save-fails')
        _build_chain(profile)

        with self.assertRaises(RuntimeError):
            with patch.object(CompanyFinancingProfile.objects, 'update_or_create',
                              side_effect=RuntimeError('save failed')):
                financing_save(profile)

        self.assertIsNone(prov.current(profile, FINANCING_METRIC_KEY))


class K_AC_NoneOutput(TestCase):
    """
    STEP 10 — no fake numeric provenance, and the previous row stops claiming
    to describe current state.
    """

    def test_k_ac_supersede_is_used_when_a_value_becomes_unavailable(self):
        profile = _profile('goes-away')
        _build_chain(profile)
        financing_save(profile)
        original = prov.current(profile, FINANCING_METRIC_KEY)
        self.assertIsNotNone(original)

        status = prov.record_calculated(
            profile, FINANCING_METRIC_KEY, None, FINANCING_INPUTS,
            writer='test', methodology=FINANCING_METHOD,
            calculation_version=FINANCING_VERSION)

        original.refresh_from_db()
        self.assertEqual(status, 'unavailable')
        self.assertFalse(original.is_current)
        self.assertIsNone(prov.current(profile, FINANCING_METRIC_KEY))

    def test_the_superseded_row_is_kept_as_history(self):
        profile = _profile('kept')
        _build_chain(profile)
        financing_save(profile)
        prov.record_calculated(
            profile, FINANCING_METRIC_KEY, None, FINANCING_INPUTS, writer='test',
            methodology=FINANCING_METHOD, calculation_version=FINANCING_VERSION)

        rows = prov.history(profile, FINANCING_METRIC_KEY)
        self.assertEqual(rows.count(), 1)
        self.assertFalse(rows.first().is_current)


class L_M_N_AD_AE_AF_AI_Defensibility(TestCase):
    """
    L/M/N + AD/AE/AF + AI — the transitive rule under a deeper graph.

    Financing and QDF sit THREE layers above material: material → pillar →
    composite → financing. Contamination at the bottom must still disqualify.
    """

    def _run(self, profile):
        financing_save(profile)
        qdf_save(profile)

    def test_l_ad_seeded_material_disqualifies_both(self):
        profile = _profile('seeded')
        _build_chain(profile, origin=PROVENANCE_SEEDED, writer='seed:test')
        self._run(profile)

        for key, *_ in WRITERS:
            with self.subTest(key=key):
                row = prov.current(profile, key)
                self.assertEqual(row.origin, PROVENANCE_MODELLED)
                self.assertTrue(prov.lineage(row))
                self.assertFalse(prov.is_derived_publicly_defensible(profile, key))

    def test_m_ae_legacy_material_disqualifies_both(self):
        profile = _profile('legacy')
        _build_chain(profile, origin=PROVENANCE_UNKNOWN, writer='d3b_backfill')
        self._run(profile)

        for key, *_ in WRITERS:
            with self.subTest(key=key):
                self.assertFalse(prov.is_derived_publicly_defensible(profile, key))

    def test_n_af_mixed_lineage_is_not_defensible(self):
        profile = _profile('mixed')
        _build_chain(profile, origin=PROVENANCE_MEASURED)
        prov.record(profile, 'transparency_score_detail', PROVENANCE_SEEDED)
        recalculate_and_save(profile)
        self._run(profile)

        row = prov.current(profile, FINANCING_METRIC_KEY)
        self.assertEqual(row.origin, PROVENANCE_MODELLED)
        self.assertTrue(prov.lineage(row), 'lineage is complete')
        self.assertFalse(
            prov.is_derived_publicly_defensible(profile, FINANCING_METRIC_KEY),
            'complete lineage and good evidence are independent')

    def test_o_ag_fully_defensible_fixtures_behave_per_the_current_guard(self):
        profile = _profile('evidenced')
        _build_chain(profile, origin=PROVENANCE_MEASURED)
        self._run(profile)

        for key, *_ in WRITERS:
            with self.subTest(key=key):
                self.assertTrue(prov.is_derived_publicly_defensible(profile, key))

    def test_ai_the_contamination_is_found_three_layers_down(self):
        """
        The regression #251's transitive rule exists for.

        Contaminating jobs_created_score specifically, because it is NOT a
        direct financing input: it feeds company.public_benefit, which feeds
        company.ecoiq_total, which is. So every one of financing's direct
        inputs is honest MODELLED and the SEEDED row sits three layers down —
        exactly the shape a single-level check would wave through.
        """
        profile = _profile('deep')
        _build_chain(profile, origin=PROVENANCE_MEASURED)
        prov.record(profile, 'jobs_created_score', PROVENANCE_SEEDED)
        recalculate_and_save(profile)
        financing_save(profile)

        row = prov.current(profile, FINANCING_METRIC_KEY)
        direct = {r.origin for r in prov.lineage(row)}

        self.assertIn(PROVENANCE_MODELLED, direct)
        self.assertNotIn(PROVENANCE_SEEDED, direct,
                         'nothing seeded is a DIRECT financing input here')
        self.assertFalse(
            prov.is_derived_publicly_defensible(profile, FINANCING_METRIC_KEY),
            'and yet it is disqualified, because the traversal goes deeper')

    def test_ai_a_single_level_check_would_have_passed_it(self):
        """
        Guards the guard: proves the case above is genuinely a multi-level
        one, by showing the direct inputs alone are all defensible.
        """
        profile = _profile('deep-proof')
        _build_chain(profile, origin=PROVENANCE_MEASURED)
        prov.record(profile, 'jobs_created_score', PROVENANCE_SEEDED)
        recalculate_and_save(profile)
        financing_save(profile)

        row = prov.current(profile, FINANCING_METRIC_KEY)
        from companies.evidence import UNEVIDENCED_PROVENANCE

        self.assertTrue(
            all(r.origin not in UNEVIDENCED_PROVENANCE
                for r in prov.lineage(row)),
            'every direct input is clean — only depth reveals the problem')

    def test_aj_the_cycle_guard_tolerates_a_shared_ancestor(self):
        """
        The deeper graph gives many rows a shared ancestor — the composite is an
        input to financing AND reachable through several pillars. A traversal
        without the `seen` guard would revisit rows repeatedly; with it, a
        diamond resolves correctly rather than being mistaken for a cycle.
        """
        profile = _profile('diamond')
        _build_chain(profile, origin=PROVENANCE_MEASURED)
        financing_save(profile)

        self.assertTrue(
            prov.is_derived_publicly_defensible(profile, FINANCING_METRIC_KEY))


class P_Q_AG_AH_RealValues(TestCase):

    def test_p_ag_a_genuine_zero_input_is_consumed_normally(self):
        profile = _profile('zero', transparency_score_detail=0.0)
        chain = _build_chain(profile)
        financing_save(profile)

        row = prov.current(profile, FINANCING_METRIC_KEY)
        self.assertEqual(row.origin, PROVENANCE_MODELLED)
        self.assertIn(chain['company.transparency_governance'], prov.lineage(row))

    def test_q_ah_a_genuine_fifty_input_is_consumed_normally(self):
        profile = _profile('fifty', transparency_score_detail=50.0)
        _build_chain(profile)
        qdf_save(profile)

        self.assertEqual(
            prov.current(profile, QDF_METRIC_KEY).origin, PROVENANCE_MODELLED)

    def test_the_number_never_decides_the_origin(self):
        for slug, value in (('v0', 0.0), ('v50', 50.0), ('v100', 100.0)):
            profile = _profile(slug, transparency_score_detail=value)
            _build_chain(profile)
            financing_save(profile)
            with self.subTest(value=value):
                self.assertEqual(
                    prov.current(profile, FINANCING_METRIC_KEY).origin,
                    PROVENANCE_MODELLED)


class QdfInputSemantics(TestCase):
    """
    The D2 residual this PR had to fix before lineage could be truthful.

    qdf._f was `float(getattr(profile, name, default) or default)` — the same
    fabrication #242 removed elsewhere, missed by the sweeps because `default`
    is a variable rather than a numeric literal.
    """

    def test_an_unknown_input_no_longer_becomes_fifty(self):
        from qdf.scoring import _f

        profile = _profile('qdf-unknown')
        profile.water_impact_score = None

        self.assertIsNone(_f(profile, 'water_impact_score'))

    def test_a_genuine_zero_survives(self):
        from qdf.scoring import _f

        profile = _profile('qdf-zero', water_impact_score=0.0)

        self.assertEqual(_f(profile, 'water_impact_score'), 0.0)

    def test_a_missing_attribute_is_unknown_not_fifty(self):
        from qdf.scoring import _f

        self.assertIsNone(_f(_profile('qdf-missing'), 'not_a_field'))

    def test_the_averaging_helper_no_longer_invents_a_midpoint(self):
        from qdf.scoring import _avg

        self.assertIsNone(_avg())
        self.assertIsNone(_avg(None, None))
        self.assertEqual(_avg(0.0, 100.0), 50.0)

    def test_explicit_fallbacks_are_named_as_such(self):
        """
        Where the 0-10 question scale genuinely needs a number, the substitution
        goes through _f_or / _avg_or so each one is a visible decision rather
        than a default nobody chose.
        """
        from qdf.scoring import _avg_or, _f_or

        profile = _profile('qdf-fallback')
        profile.water_impact_score = None

        self.assertEqual(_f_or(profile, 'water_impact_score'), 50.0)
        self.assertEqual(_avg_or(50.0), 50.0)


class AK_AL_PublicSurfaces(TestCase):

    """
    STEP 18 — lineage existing does not publish anything.
    """

    # D5 note. Coverage now reads the provenance store, so a fixture whose
    # sixteen material inputs are ALL evidenced reaches 100% coverage and is
    # legitimately PUBLISHED -- which is the outcome the programme exists to
    # make possible, and the opposite of what this class tests.
    #
    # The subject here is CONTAINMENT, so the fixture is partially evidenced:
    # real provenance on some inputs, not enough of it to publish. That is also
    # the state every company in the production estate is actually in.
    PARTIAL_EVIDENCE_LIMIT = 4

    def setUp(self):
        # The API rate-limits anonymous callers to 20 requests/day through the
        # Django cache, which is NOT reset between tests. A full-suite run
        # exhausts it and later API tests receive 429 with a payload that has no
        # score keys -- a test-isolation problem that reads exactly like a
        # containment regression.
        from django.core.cache import cache
        cache.clear()

        self.profile = _profile('public', ecoiq_total_score=71.4)
        self.profile.company.ecoiq_score = 71.4
        self.profile.company.save()
        _build_chain(self.profile, origin=PROVENANCE_MEASURED, limit=self.PARTIAL_EVIDENCE_LIMIT)
        financing_save(self.profile)
        qdf_save(self.profile)

    def test_ak_the_company_page_is_still_evidence_pending(self):
        from django.test import Client

        from companies.evidence import PENDING_HEADLINE

        body = Client().get('/companies/public/').content.decode()
        self.assertIn(PENDING_HEADLINE, body)

    def test_ak_no_financing_estimate_leaks_for_an_ineligible_company(self):
        """
        The fail-closed rule from the Evidence Integrity programme: zero
        evidence, no authoritative financing estimate.
        """
        from django.test import Client

        body = Client().get('/companies/public/').content.decode()

        for marker in ('Financing Readiness', 'estimated capex', 'Estimated Capex',
                       'Decision Integrity'):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, body)

    def test_ak_the_league_page_is_still_fail_closed(self):
        from django.test import Client

        from companies.evidence import PENDING_HEADLINE

        self.assertIn(PENDING_HEADLINE, Client().get('/league/').content.decode())

    def test_al_api_v2_is_unchanged(self):
        from django.test import Client

        payload = Client().get('/api/v2/companies/public/').json()

        self.assertIsNone(payload['ecoiq_score'])
        self.assertEqual(payload['score_status'], 'INSUFFICIENT_EVIDENCE')
        self.assertNotIn('provenance', payload)

    def test_partial_evidence_publishes_nothing(self):
        """
        With four of sixteen inputs evidenced, BOTH gates reject, for two
        independently correct reasons: coverage is under 100%, and the
        financing lineage is ABSENT rather than weak — record_calculated
        declines to write a row when some consumed inputs have no provenance,
        because a lineage listing only the evidenced ones would understate what
        the number rests on.

        Before D5 this passed for a much weaker reason: nothing could be
        published at all, because coverage was inert.
        """
        from companies.evidence import coverage_for, public_score_state

        report = coverage_for(self.profile)

        self.assertGreater(report.coverage_percent, 0)
        self.assertLess(report.coverage_percent, 100)
        self.assertFalse(
            prov.is_derived_publicly_defensible(self.profile, FINANCING_METRIC_KEY),
            'an incomplete lineage is not recorded at all, so it cannot be defended')
        self.assertFalse(public_score_state(self.profile).available)


class CallerCompatibility(TestCase):

    def test_return_contracts_are_unchanged(self):
        from financing.models import CompanyFinancingProfile
        from qdf.models import DecisionAssessment

        profile = _profile('contract')

        self.assertIsInstance(financing_save(profile), CompanyFinancingProfile)
        self.assertIsInstance(qdf_save(profile), DecisionAssessment)

    def test_both_work_inside_an_existing_transaction(self):
        profile = _profile('inside-atomic')
        _build_chain(profile)

        with transaction.atomic():
            financing_save(profile)
            qdf_save(profile)

        self.assertIsNotNone(prov.current(profile, FINANCING_METRIC_KEY))
        self.assertIsNotNone(prov.current(profile, QDF_METRIC_KEY))
