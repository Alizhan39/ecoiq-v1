"""
D3C-3b — ethics score lineage.

Covers A–Y. One calculator: ethics.scoring.compute_and_save, which writes THREE
derived metrics from one assessment.

That is what makes it the right second writer. #249 proved the pattern on a
single output; this proves it where three outputs share a calculation event but
not an input set — and where the failure mode to rule out is a PARTIAL
assessment: a new NEI with lineage, a new TSS without, and a stale RVI.

It also surfaced the derived-on-derived edge #249 deferred. NEI rests mostly on
the six CompanyProfile pillars, which are themselves derived, so its lineage
cites derived provenance rows. The M2M is self-referential, so this needed no
new machinery — only a registry key for the one pillar that had none.
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
from ethics.models import CompanyEthicsProfile
from ethics.scoring import (
    DERIVED_OUTPUTS, ETHICS_METHOD, ETHICS_VERSION, NEI_INPUTS, RVI_INPUTS,
    TSS_INPUTS, compute_and_save,
)
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


ALL_INPUTS = sorted(set(NEI_INPUTS) | set(TSS_INPUTS) | set(RVI_INPUTS))


def _profile(slug, **kwargs):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    return _populated(company=company, status='public',
                                         pollution_level='low', **kwargs)


def _record_inputs(profile, keys=None, origin=PROVENANCE_MEASURED,
                   writer='ingestion'):
    """
    Build the REAL provenance chain beneath the ethics inputs.

    Rewritten in D3C-3c. It used to record the derived pillars directly as
    MODELLED with no inputs — which the transitive defensibility rule now
    correctly rejects: a modelled value that cannot show its lineage cannot be
    defended. The fixture was asserting a state the system should never reach.

    So it records MATERIAL provenance and then runs recalculate_and_save, which
    produces the pillar rows the way production does. The ethics tests now
    exercise the whole pipeline rather than a hand-built approximation of it.
    """
    from companies.scoring import recalculate_and_save

    material = [k for k in (keys if keys is not None else ALL_INPUTS)
               if k in prov.MATERIAL_METRIC_KEYS]
    for key in sorted(set(material) | set(prov.MATERIAL_METRIC_KEYS)):
        if registry.resolve_value(profile, key) is not None:
            prov.record(profile, key, origin, written_by=writer)

    recalculate_and_save(profile)

    return {row.metric_key: row for row in
            CompanyMetricProvenance.objects.filter(company=profile,
                                                   is_current=True)}


class DeclaredInputsAreTraced(SimpleTestCase):
    """
    The three input sets are the basis of every lineage claim here, so they are
    checked against the formulas rather than trusted.
    """

    def _fields_referenced_by(self, func_name):
        import ast
        import inspect

        from ethics import scoring

        tree = ast.parse(inspect.getsource(getattr(scoring, func_name)).lstrip())
        return {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == 'profile'
        }

    def _declared_fields(self, keys):
        """Registry keys -> the CompanyProfile field each resolves from."""
        fields = set()
        for key in keys:
            location = registry.REGISTRY[key].value_location
            fields.add(location.rsplit('.', 1)[-1])
        return fields

    def test_nei_declares_what_it_reads(self):
        referenced = self._fields_referenced_by('compute_net_ethical_impact')
        referenced.discard('pollution_level')      # categorical, no provenance

        self.assertEqual(self._declared_fields(NEI_INPUTS), referenced)

    def test_tss_declares_what_it_reads(self):
        referenced = self._fields_referenced_by('compute_transition_stewardship')
        referenced.discard('pollution_level')

        self.assertEqual(self._declared_fields(TSS_INPUTS), referenced)

    def test_rvi_declares_what_it_reads(self):
        referenced = self._fields_referenced_by('compute_regenerative_value')
        referenced.discard('pollution_level')

        self.assertEqual(self._declared_fields(RVI_INPUTS), referenced)

    def test_the_three_input_sets_are_genuinely_different(self):
        """
        If they were identical, per-metric lineage would be theatre. They are
        not: energy_transition feeds TSS only, jobs_created feeds RVI only.
        """
        self.assertNotEqual(set(NEI_INPUTS), set(TSS_INPUTS))
        self.assertNotEqual(set(TSS_INPUTS), set(RVI_INPUTS))
        self.assertIn('energy_transition_score', TSS_INPUTS)
        self.assertNotIn('energy_transition_score', NEI_INPUTS)
        self.assertIn('jobs_created_score', RVI_INPUTS)
        self.assertNotIn('jobs_created_score', TSS_INPUTS)

    def test_every_declared_key_is_registered(self):
        for key in ALL_INPUTS:
            with self.subTest(key=key):
                self.assertIn(key, registry.VALID_KEYS)

    def test_nei_cites_derived_pillars_not_only_material_inputs(self):
        """
        The derived-on-derived edge. NEI's benefit half IS the six pillars, so
        a lineage of material inputs alone would understate what it rests on.
        """
        derived = {k for k in NEI_INPUTS if k in registry.DERIVED_KEYS}

        self.assertTrue(derived)
        self.assertIn('company.public_benefit', derived)
        self.assertIn('company.ethical_alignment', derived)

    def test_the_missing_pillar_key_was_registered(self):
        """
        company.ethical_alignment had no registry key before D3C-3b, so a
        calculation consuming it could not record complete lineage.
        """
        definition = registry.require_metric_definition('company.ethical_alignment')

        self.assertEqual(definition.kind, registry.DERIVED)
        self.assertEqual(definition.value_location,
                         'companies.CompanyProfile.ethical_alignment_score')

    def test_all_three_outputs_are_registered_derived_metrics(self):
        for key in DERIVED_OUTPUTS:
            with self.subTest(key=key):
                self.assertEqual(registry.REGISTRY[key].kind, registry.DERIVED)


class A_B_C_D_E_ThreeRowsPerAssessment(TestCase):

    def setUp(self):
        self.profile = _profile('three-rows')
        self.inputs = _record_inputs(self.profile)
        compute_and_save(self.profile)

    def _row(self, key):
        return prov.current(self.profile, key)

    def test_a_nei_provenance_is_modelled(self):
        self.assertEqual(self._row('ethics.nei').origin, PROVENANCE_MODELLED)

    def test_b_tss_provenance_is_modelled(self):
        self.assertEqual(self._row('ethics.tss').origin, PROVENANCE_MODELLED)

    def test_c_rvi_provenance_is_modelled(self):
        self.assertEqual(self._row('ethics.rvi').origin, PROVENANCE_MODELLED)

    def test_three_separate_rows_never_one(self):
        """
        Merging them would make it impossible to say that TSS's lineage changed
        while NEI's did not.
        """
        rows = CompanyMetricProvenance.objects.filter(
            company=self.profile, metric_key__in=DERIVED_OUTPUTS, is_current=True)

        self.assertEqual(rows.count(), 3)
        self.assertEqual(set(rows.values_list('metric_key', flat=True)),
                         set(DERIVED_OUTPUTS))

    def test_d_methodology_is_recorded_on_each(self):
        for key in DERIVED_OUTPUTS:
            with self.subTest(key=key):
                self.assertEqual(self._row(key).methodology, ETHICS_METHOD)

    def test_e_calculation_version_is_recorded_on_each(self):
        for key in DERIVED_OUTPUTS:
            with self.subTest(key=key):
                self.assertEqual(self._row(key).calculation_version, ETHICS_VERSION)

    def test_e_the_version_reuses_the_model_s_own_formula_version(self):
        """Not invented — CompanyEthicsProfile.formula_version already existed."""
        field = CompanyEthicsProfile._meta.get_field('formula_version')

        self.assertEqual(ETHICS_VERSION, field.default)

    def test_the_writer_is_named(self):
        self.assertEqual(self._row('ethics.nei').written_by,
                         'ethics.scoring.compute_and_save')

    def test_none_of_them_is_measured(self):
        for key in DERIVED_OUTPUTS:
            with self.subTest(key=key):
                self.assertNotEqual(self._row(key).origin, PROVENANCE_MEASURED)

    def test_the_status_is_reported_per_metric(self):
        profile = _profile('status')
        _record_inputs(profile)
        ethics = compute_and_save(profile)

        self.assertEqual(ethics.provenance_status,
                         {k: 'recorded' for k in DERIVED_OUTPUTS})


class F_G_H_I_PerMetricInputSets(TestCase):

    def setUp(self):
        self.profile = _profile('inputs')
        self.rows = _record_inputs(self.profile)
        compute_and_save(self.profile)

    def _linked(self, key):
        return {r.metric_key for r in prov.lineage(prov.current(self.profile, key))}

    def test_f_nei_gets_exactly_its_declared_inputs(self):
        self.assertEqual(self._linked('ethics.nei'), set(NEI_INPUTS))

    def test_g_tss_gets_exactly_its_declared_inputs(self):
        self.assertEqual(self._linked('ethics.tss'), set(TSS_INPUTS))

    def test_h_rvi_gets_exactly_its_declared_inputs(self):
        self.assertEqual(self._linked('ethics.rvi'), set(RVI_INPUTS))

    def test_i_an_input_of_one_metric_is_not_attached_to_another(self):
        """
        Lineage must mean "this value contributed to THIS calculation", not
        "this metric happened to be available on the company".
        """
        self.assertNotIn('energy_transition_score', self._linked('ethics.nei'))
        self.assertNotIn('jobs_created_score', self._linked('ethics.tss'))
        self.assertNotIn('company.public_benefit', self._linked('ethics.rvi'))

    def test_i_an_unrelated_available_metric_is_not_attached(self):
        profile = _profile('unrelated')
        _record_inputs(profile)
        unrelated = prov.record(profile, 'company.ecoiq_total', PROVENANCE_MODELLED)

        compute_and_save(profile)

        for key in DERIVED_OUTPUTS:
            with self.subTest(key=key):
                self.assertNotIn(
                    unrelated, prov.lineage(prov.current(profile, key)))


class J_MissingProvenanceIsNeverGuessed(TestCase):

    def test_j_no_input_provenance_means_no_derived_rows(self):
        """The production state today: values exist, provenance does not."""
        profile = _profile('no-provenance')

        ethics = compute_and_save(profile)

        self.assertIsNotNone(ethics, 'the ethics values are still computed')
        self.assertEqual(set(ethics.provenance_status.values()), {'incomplete'})
        self.assertEqual(CompanyMetricProvenance.objects.count(), 0)

    def test_j_partial_input_provenance_is_still_incomplete(self):
        profile = _profile('partial')
        rows = _record_inputs(profile)
        rows['controversy_risk_score'].delete()

        ethics = compute_and_save(profile)

        # controversy_risk_score feeds NEI and TSS but not RVI.
        self.assertEqual(ethics.provenance_status['ethics.nei'], 'incomplete')
        self.assertEqual(ethics.provenance_status['ethics.tss'], 'incomplete')
        self.assertEqual(ethics.provenance_status['ethics.rvi'], 'recorded')

    def test_j_no_material_provenance_is_invented_to_fill_the_gap(self):
        profile = _profile('no-invention')

        compute_and_save(profile)

        self.assertEqual(CompanyMetricProvenance.objects.count(), 0,
                         'D3B owns historical labelling, not this writer')

    def test_j_an_empty_input_list_is_never_recorded(self):
        profile = _profile('empty-lineage')
        compute_and_save(profile)

        rows = CompanyMetricProvenance.objects.filter(
            metric_key__in=DERIVED_OUTPUTS)
        self.assertEqual(rows.count(), 0)


class K_L_M_N_Idempotency(TestCase):

    def setUp(self):
        self.profile = _profile('churn')
        self.rows = _record_inputs(self.profile)
        compute_and_save(self.profile)

    def _count(self, key):
        return CompanyMetricProvenance.objects.filter(
            company=self.profile, metric_key=key).count()

    def test_k_an_identical_recalculation_creates_no_churn(self):
        compute_and_save(self.profile)
        compute_and_save(self.profile)

        for key in DERIVED_OUTPUTS:
            with self.subTest(key=key):
                self.assertEqual(self._count(key), 1)

    def test_k_the_status_says_unchanged(self):
        ethics = compute_and_save(self.profile)

        self.assertEqual(set(ethics.provenance_status.values()), {'unchanged'})

    def test_l_a_changed_input_creates_new_lineage_only_where_it_is_consumed(self):
        """
        energy_transition_score feeds TSS alone, so only TSS should get a new
        event. This is the payoff for per-metric input sets.
        """
        prov.record(self.profile, 'energy_transition_score', PROVENANCE_SEEDED)

        ethics = compute_and_save(self.profile)

        self.assertEqual(ethics.provenance_status['ethics.tss'], 'recorded')
        self.assertEqual(ethics.provenance_status['ethics.nei'], 'unchanged')
        self.assertEqual(ethics.provenance_status['ethics.rvi'], 'unchanged')
        self.assertEqual(self._count('ethics.tss'), 2)
        self.assertEqual(self._count('ethics.nei'), 1)

    def test_l_a_shared_input_change_affects_every_consumer(self):
        """transparency_score_detail feeds NEI and RVI, not TSS."""
        prov.record(self.profile, 'transparency_score_detail', PROVENANCE_SEEDED)

        ethics = compute_and_save(self.profile)

        self.assertEqual(ethics.provenance_status['ethics.nei'], 'recorded')
        self.assertEqual(ethics.provenance_status['ethics.rvi'], 'recorded')
        self.assertEqual(ethics.provenance_status['ethics.tss'], 'unchanged')

    def test_m_old_lineage_stays_pinned_to_the_old_input_rows(self):
        first = prov.current(self.profile, 'ethics.tss')
        old_input = self.rows['energy_transition_score']

        prov.record(self.profile, 'energy_transition_score', PROVENANCE_SEEDED)
        compute_and_save(self.profile)

        first.refresh_from_db()
        old_input.refresh_from_db()

        self.assertFalse(first.is_current)
        self.assertFalse(old_input.is_current)
        self.assertIn(old_input, prov.lineage(first),
                      'historical lineage must never drift to the latest inputs')

    def test_m_the_new_row_points_at_the_new_input(self):
        replacement = prov.record(self.profile, 'energy_transition_score',
                                  PROVENANCE_SEEDED)
        compute_and_save(self.profile)

        second = prov.current(self.profile, 'ethics.tss')
        self.assertIn(replacement, prov.lineage(second))

    def test_n_a_version_change_creates_a_new_event_for_all_three(self):
        with patch('ethics.scoring.ETHICS_VERSION', '2.0'):
            ethics = compute_and_save(self.profile)

        self.assertEqual(set(ethics.provenance_status.values()), {'recorded'})
        for key in DERIVED_OUTPUTS:
            with self.subTest(key=key):
                self.assertEqual(self._count(key), 2)

    def test_n_a_methodology_change_creates_a_new_event(self):
        with patch('ethics.scoring.ETHICS_METHOD', 'ecoiq-ethics-assessment-v2'):
            compute_and_save(self.profile)

        self.assertEqual(self._count('ethics.nei'), 2)


class O_P_Q_MultiOutputAtomicity(TestCase):
    """
    O/P/Q — three outputs written together, so a partial assessment must be
    impossible: never a new NEI with lineage, a new TSS without, and a stale RVI.
    """

    def _profile_with_prior_state(self, slug):
        profile = _profile(slug)
        _record_inputs(profile)
        compute_and_save(profile)
        return profile

    def _fail_on(self, metric_key):
        """Make provenance recording blow up for one metric only."""
        from companies import provenance as real_prov

        genuine = real_prov.record_derived

        def selective(profile, key, **kwargs):
            if key == metric_key:
                raise RuntimeError(f'{key} provenance failed')
            return genuine(profile, key, **kwargs)

        return selective

    #: An input each metric ACTUALLY consumes. Perturbing one the metric does
    #: not read would leave its lineage unchanged, so record_derived would
    #: never be called and the injected failure would never fire — the test
    #: would pass by not testing anything.
    PERTURB = {
        'ethics.nei': 'controversy_risk_score',
        'ethics.tss': 'energy_transition_score',
        'ethics.rvi': 'jobs_created_score',
    }

    def _assert_whole_assessment_rolled_back(self, profile, metric_key):
        before = CompanyEthicsProfile.objects.get(profile=profile)
        original = (before.net_ethical_impact, before.transition_stewardship,
                    before.regenerative_value)
        counts = {k: CompanyMetricProvenance.objects.filter(
            company=profile, metric_key=k).count() for k in DERIVED_OUTPUTS}

        perturbed = self.PERTURB[metric_key]
        prov.record(profile, perturbed, PROVENANCE_SEEDED)

        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record_derived',
                       self._fail_on(metric_key)):
                compute_and_save(profile)

        after = CompanyEthicsProfile.objects.get(profile=profile)
        self.assertEqual(
            (after.net_ethical_impact, after.transition_stewardship,
             after.regenerative_value),
            original,
            'the whole assessment must roll back, not just the failed metric')
        for key, count in counts.items():
            with self.subTest(metric=key):
                self.assertEqual(
                    CompanyMetricProvenance.objects.filter(
                        company=profile, metric_key=key).count(), count)

    def test_o_a_nei_provenance_failure_rolls_back_the_assessment(self):
        self._assert_whole_assessment_rolled_back(
            self._profile_with_prior_state('fail-nei'), 'ethics.nei')

    def test_p_a_tss_provenance_failure_rolls_back_the_assessment(self):
        self._assert_whole_assessment_rolled_back(
            self._profile_with_prior_state('fail-tss'), 'ethics.tss')

    def test_q_an_rvi_provenance_failure_rolls_back_the_assessment(self):
        self._assert_whole_assessment_rolled_back(
            self._profile_with_prior_state('fail-rvi'), 'ethics.rvi')

    def test_a_failure_leaves_no_partial_provenance_at_all(self):
        profile = _profile('no-partial')
        _record_inputs(profile)

        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record_derived',
                       self._fail_on('ethics.rvi')):
                compute_and_save(profile)

        self.assertEqual(
            CompanyMetricProvenance.objects.filter(
                metric_key__in=DERIVED_OUTPUTS).count(), 0,
            'NEI and TSS must not survive an RVI failure')

    def test_the_perturbed_input_really_is_consumed_by_its_metric(self):
        """
        Guards the guard: if PERTURB named an input a metric does not read,
        the three rollback tests above would pass without exercising anything.
        """
        declared = {'ethics.nei': NEI_INPUTS, 'ethics.tss': TSS_INPUTS,
                    'ethics.rvi': RVI_INPUTS}
        for metric_key, field in self.PERTURB.items():
            with self.subTest(metric=metric_key):
                self.assertIn(field, declared[metric_key])

    def test_an_ethics_save_failure_leaves_no_provenance(self):
        profile = _profile('save-fails')
        _record_inputs(profile)

        with self.assertRaises(RuntimeError):
            with patch.object(CompanyEthicsProfile.objects, 'update_or_create',
                              side_effect=RuntimeError('save failed')):
                compute_and_save(profile)

        self.assertEqual(
            CompanyMetricProvenance.objects.filter(
                metric_key__in=DERIVED_OUTPUTS).count(), 0)


class R_S_T_PublicDefensibility(TestCase):
    """
    R/S/T — MODELLED describes HOW, never HOW GOOD.
    """

    def test_r_seeded_inputs_make_all_three_not_defensible(self):
        profile = _profile('seeded')
        _record_inputs(profile, origin=PROVENANCE_SEEDED, writer='seed:test')
        compute_and_save(profile)

        for key in DERIVED_OUTPUTS:
            with self.subTest(key=key):
                self.assertEqual(prov.current(profile, key).origin,
                                 PROVENANCE_MODELLED)
                self.assertFalse(prov.is_derived_publicly_defensible(profile, key))

    def test_s_legacy_inputs_make_all_three_not_defensible(self):
        profile = _profile('legacy')
        _record_inputs(profile, origin=PROVENANCE_UNKNOWN, writer='d3b_backfill')
        compute_and_save(profile)

        for key in DERIVED_OUTPUTS:
            with self.subTest(key=key):
                self.assertFalse(prov.is_derived_publicly_defensible(profile, key))

    def test_t_mixed_quality_inputs_are_not_defensible(self):
        """
        Complete lineage, MODELLED origin — and still False, because one
        consumed input is not defensible. No coverage threshold involved.
        """
        profile = _profile('mixed')
        _record_inputs(profile, origin=PROVENANCE_MEASURED)
        prov.record(profile, 'transparency_score_detail', PROVENANCE_SEEDED)
        prov.record(profile, 'jobs_created_score', PROVENANCE_UNKNOWN)

        compute_and_save(profile)

        nei = prov.current(profile, 'ethics.nei')
        self.assertEqual(nei.origin, PROVENANCE_MODELLED)
        self.assertTrue(prov.lineage(nei), 'lineage is complete')
        self.assertFalse(prov.is_derived_publicly_defensible(profile, 'ethics.nei'))
        self.assertFalse(prov.is_derived_publicly_defensible(profile, 'ethics.rvi'))

    def test_t_a_metric_whose_own_inputs_are_all_clean_is_unaffected(self):
        """
        TSS does not consume jobs_created_score, so contaminating that must not
        make TSS undefensible. Per-metric lineage is what makes this knowable.
        """
        profile = _profile('isolated')
        _record_inputs(profile, origin=PROVENANCE_MEASURED)
        prov.record(profile, 'jobs_created_score', PROVENANCE_SEEDED)

        compute_and_save(profile)

        self.assertTrue(prov.is_derived_publicly_defensible(profile, 'ethics.tss'))
        self.assertFalse(prov.is_derived_publicly_defensible(profile, 'ethics.rvi'))

    def test_evidenced_inputs_do_produce_defensible_metrics(self):
        """The mirror — the guard must not reject everything."""
        profile = _profile('evidenced')
        _record_inputs(profile, origin=PROVENANCE_MEASURED)
        compute_and_save(profile)

        for key in DERIVED_OUTPUTS:
            with self.subTest(key=key):
                self.assertTrue(prov.is_derived_publicly_defensible(profile, key))


class U_V_RealValues(TestCase):
    """U/V — the number never decides the provenance."""

    def test_u_a_genuine_zero_input_is_consumed_normally(self):
        profile = _profile('zero-input', jobs_created_score=0.0)
        rows = _record_inputs(profile)

        compute_and_save(profile)
        rvi = prov.current(profile, 'ethics.rvi')

        self.assertIn(rows['jobs_created_score'], prov.lineage(rvi))
        self.assertEqual(rvi.origin, PROVENANCE_MODELLED)

    def test_v_a_genuine_fifty_input_is_consumed_normally(self):
        profile = _profile('fifty-input', jobs_created_score=50.0)
        rows = _record_inputs(profile)

        compute_and_save(profile)
        rvi = prov.current(profile, 'ethics.rvi')

        self.assertIn(rows['jobs_created_score'], prov.lineage(rvi))

    def test_the_same_value_gets_different_origins_from_different_writers(self):
        seeded = _profile('by-seed', jobs_created_score=72.0)
        measured = _profile('by-ingest', jobs_created_score=72.0)
        _record_inputs(seeded, origin=PROVENANCE_SEEDED, writer='seed:test')
        _record_inputs(measured, origin=PROVENANCE_MEASURED)

        compute_and_save(seeded)
        compute_and_save(measured)

        self.assertFalse(prov.is_derived_publicly_defensible(seeded, 'ethics.rvi'))
        self.assertTrue(prov.is_derived_publicly_defensible(measured, 'ethics.rvi'))


class W_UnknownOutput(TestCase):
    """
    W — STEP 14. A calculation that produces no value must not leave provenance
    claiming it did, and must not leave the PREVIOUS row marked current.
    """

    def _blank_for_unknown_nei(self, profile):
        """Make the harm half unknowable, which makes NEI None."""
        profile.pollution_level = None
        profile.controversy_risk_score = None
        profile.transparency_score_detail = None
        return profile

    def test_w_an_unknown_output_creates_no_provenance(self):
        profile = _profile('unknown-out')
        self._blank_for_unknown_nei(profile)

        compute_and_save(profile)

        self.assertIsNone(prov.current(profile, 'ethics.nei'))

    def test_w_a_previously_current_row_is_superseded_when_the_value_goes_away(self):
        """
        The important half. Leaving the old row current would assert that a
        superseded calculation still describes the current state.
        """
        profile = _profile('was-known')
        _record_inputs(profile)
        compute_and_save(profile)
        original = prov.current(profile, 'ethics.nei')
        self.assertIsNotNone(original)

        self._blank_for_unknown_nei(profile)
        ethics = compute_and_save(profile)

        original.refresh_from_db()
        self.assertFalse(original.is_current,
                         'a stale row must not keep claiming to be current')
        self.assertIsNone(prov.current(profile, 'ethics.nei'))
        self.assertEqual(ethics.provenance_status['ethics.nei'], 'unavailable')

    def test_w_the_superseded_row_is_kept_as_history(self):
        profile = _profile('history-kept')
        _record_inputs(profile)
        compute_and_save(profile)
        self._blank_for_unknown_nei(profile)
        compute_and_save(profile)

        rows = prov.history(profile, 'ethics.nei')
        self.assertEqual(rows.count(), 1)
        self.assertFalse(rows.first().is_current)

    def test_w_metrics_that_are_still_computable_are_unaffected(self):
        profile = _profile('partial-unknown')
        _record_inputs(profile)
        compute_and_save(profile)

        self._blank_for_unknown_nei(profile)
        ethics = compute_and_save(profile)

        self.assertEqual(ethics.provenance_status['ethics.nei'], 'unavailable')
        self.assertIsNotNone(prov.current(profile, 'ethics.tss'))


class StaleValueIsADependencyNotAFix(TestCase):
    """
    STEP 15 — the D4 dependency, asserted so it is visible rather than assumed.
    """

    def test_a_stale_ethics_value_remains_because_the_column_is_not_null(self):
        profile = _profile('stale')
        _record_inputs(profile)
        compute_and_save(profile)
        stored = CompanyEthicsProfile.objects.get(profile=profile).net_ethical_impact
        self.assertGreater(stored, 0)

        profile.pollution_level = None
        profile.controversy_risk_score = None
        profile.transparency_score_detail = None
        compute_and_save(profile)

        row = CompanyEthicsProfile.objects.get(profile=profile)
        self.assertEqual(row.net_ethical_impact, stored,
                         'NOT NULL forces the old number to stay — this is D4')
        self.assertNotEqual(row.net_ethical_impact, 0.0)
        self.assertNotEqual(row.net_ethical_impact, 50.0)

    def test_but_its_provenance_no_longer_claims_to_be_current(self):
        """
        The containment that makes the stale value safe until D4: the number is
        stuck in the column, but nothing asserts it describes current state.
        """
        profile = _profile('stale-provenance')
        _record_inputs(profile)
        compute_and_save(profile)

        profile.pollution_level = None
        profile.controversy_risk_score = None
        profile.transparency_score_detail = None
        compute_and_save(profile)

        self.assertIsNone(prov.current(profile, 'ethics.nei'))
        self.assertFalse(
            prov.is_derived_publicly_defensible(profile, 'ethics.nei'))


class NoFabricatedReview(TestCase):
    """STEP 16 — automatic calculation is never human review."""

    def test_no_review_is_fabricated(self):
        profile = _profile('review')
        _record_inputs(profile)
        compute_and_save(profile)

        for key in DERIVED_OUTPUTS:
            with self.subTest(key=key):
                row = prov.current(profile, key)
                self.assertEqual(row.review_status, 'proposed')
                self.assertIsNone(row.reviewed_by)
                self.assertIsNone(row.reviewed_at)
                self.assertIsNone(row.confidence)


class SeedFlowEndToEnd(TestCase):
    """
    STEP 11 — seed values -> SEEDED material -> MODELLED ethics -> not defensible.
    """

    def test_the_full_chain_with_seeded_inputs(self):
        """
        seed values -> SEEDED provenance -> MODELLED ethics -> not defensible.

        Fixture-supplied provenance, because a real seed run cannot complete
        this chain yet — see the test below, which is the finding.
        """
        profile = _profile('seed-chain')
        _record_inputs(profile, origin=PROVENANCE_SEEDED,
                       writer='seed:seed_global_companies')

        compute_and_save(profile)
        nei = prov.current(profile, 'ethics.nei')

        self.assertIsNotNone(nei)
        self.assertEqual(nei.origin, PROVENANCE_MODELLED)

        # NEI's DIRECT inputs are the pillars (MODELLED) plus the material
        # anti_corruption_score (SEEDED). The seeded contamination beneath the
        # pillars is what the transitive check finds.
        direct = {r.origin for r in prov.lineage(nei)}
        self.assertIn(PROVENANCE_MODELLED, direct)

        pillar = prov.current(profile, 'company.public_benefit')
        self.assertEqual({r.origin for r in prov.lineage(pillar)},
                         {PROVENANCE_SEEDED})

        self.assertFalse(
            prov.is_derived_publicly_defensible(profile, 'ethics.nei'),
            'MODELLED over SEEDED is still synthetic, however many layers down')

    def test_y_a_real_seed_run_now_completes_ethics_lineage(self):
        """
        STEP 16 — the gap #250 pinned is CLOSED, and this is the proof.

        #250 could only assert 'incomplete': the seeder wrote SEEDED material
        provenance, but recalculate_and_save recorded the composite alone, so
        the pillars NEI and TSS consume had values and no provenance.

        D3C-3c records the pillars, so the whole chain now forms:

            SEEDED material -> MODELLED pillars -> MODELLED composite
                            -> MODELLED NEI / TSS / RVI

        The assertion is strengthened, not weakened: it now demands complete
        lineage AND still-false defensibility.
        """
        from io import StringIO

        from django.core.management import call_command

        call_command('seed_global_companies', stdout=StringIO(), stderr=StringIO())
        profile = CompanyProfile.objects.select_related('company').first()

        # The pillars the seed run's recalculate_and_save produced.
        self.assertIsNotNone(prov.current(profile, 'company.public_benefit'))
        self.assertIsNotNone(prov.current(profile, 'company.ethical_alignment'))

        ethics = compute_and_save(profile)

        self.assertEqual(set(ethics.provenance_status.values()), {'recorded'},
                         'all three ethics metrics must now have complete lineage')

        for key in DERIVED_OUTPUTS:
            with self.subTest(key=key):
                row = prov.current(profile, key)
                self.assertIsNotNone(row)
                self.assertEqual(row.origin, PROVENANCE_MODELLED)
                self.assertTrue(prov.lineage(row))
                self.assertFalse(
                    prov.is_derived_publicly_defensible(profile, key),
                    'complete lineage over SEEDED inputs is still not publishable')

    def test_y_the_seeded_contamination_is_found_through_the_pillar_layer(self):
        """
        The defect D3C-3c introduced and fixed: NEI cites MODELLED pillars, so
        a single-level defensibility check would see honest inputs and pass
        while SEEDED material sat two layers below. Transitive traversal is
        what makes this False.
        """
        from io import StringIO

        from django.core.management import call_command

        call_command('seed_global_companies', stdout=StringIO(), stderr=StringIO())
        profile = CompanyProfile.objects.select_related('company').first()
        compute_and_save(profile)

        nei = prov.current(profile, 'ethics.nei')
        direct = {r.origin for r in prov.lineage(nei)}

        self.assertIn(PROVENANCE_MODELLED, direct,
                      'NEI cites the pillar layer, which is honest MODELLED')
        self.assertFalse(
            prov.is_derived_publicly_defensible(profile, 'ethics.nei'),
            'and yet it is not defensible, because the traversal goes deeper')


class X_Y_PublicSurfaces(TestCase):
    """X/Y — no ethics score resurrection."""

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
        _record_inputs(self.profile, origin=PROVENANCE_MEASURED)
        compute_and_save(self.profile)

    def test_x_the_company_page_is_still_evidence_pending(self):
        from django.test import Client

        from companies.evidence import PENDING_HEADLINE

        body = Client().get('/companies/public/').content.decode()

        self.assertIn(PENDING_HEADLINE, body)

    def test_x_no_nei_tss_rvi_leaks_into_the_page(self):
        from django.test import Client

        body = Client().get('/companies/public/').content.decode()

        for marker in ('Net Ethical Impact', 'Transition Stewardship',
                       'Regenerative Value', 'Ethical Intelligence Analysis'):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, body)

    def test_x_the_league_page_is_still_fail_closed(self):
        from django.test import Client

        from companies.evidence import PENDING_HEADLINE

        self.assertIn(PENDING_HEADLINE,
                      Client().get('/league/').content.decode())

    def test_y_api_v2_semantics_are_unchanged(self):
        from django.test import Client

        payload = Client().get('/api/v2/companies/public/').json()

        self.assertIsNone(payload['ecoiq_score'])
        self.assertEqual(payload['score_status'], 'INSUFFICIENT_EVIDENCE')
        self.assertNotIn('provenance', payload)

    def test_defensible_provenance_still_does_not_publish(self):
        """
        The distinction: provenance quality and PUBLICATION are separate gates.
        D5 owns the second and this PR did not touch it.
        """
        from companies.evidence import public_score_state

        self.assertTrue(
            prov.is_derived_publicly_defensible(self.profile, 'ethics.nei'))
        self.assertFalse(public_score_state(self.profile).available)


class CallerCompatibility(TestCase):
    """The three callers: ingestion, admin, and the company detail view."""

    def test_the_return_contract_is_unchanged(self):
        profile = _profile('contract')
        result = compute_and_save(profile)

        self.assertIsInstance(result, CompanyEthicsProfile)

    def test_none_is_still_returned_when_no_row_can_be_created(self):
        profile = _profile('returns-none')
        profile.pollution_level = None
        profile.controversy_risk_score = None
        profile.transparency_score_detail = None

        self.assertIsNone(compute_and_save(profile))

    def test_it_works_inside_an_existing_transaction(self):
        profile = _profile('inside-atomic')
        _record_inputs(profile)

        with transaction.atomic():
            compute_and_save(profile)

        self.assertIsNotNone(prov.current(profile, 'ethics.nei'))
