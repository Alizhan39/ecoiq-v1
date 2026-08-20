"""
D3C-3 — composite score lineage.

Covers A–T. One derived writer only: companies.scoring.recalculate_and_save.
Proof-of-pattern for derived calculations; no other calculator is wired up.

The central invariant, tested in E and F:

    LINEAGE AS COMPUTED, not as recomputable.

A derived row names the exact provenance rows the calculation read. When an
input is later superseded, the old derived row keeps pointing at the old input
row. Re-reading current provenance would answer "what would this rest on if
recalculated now?" — a different question, and not an audit trail.
"""
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase

from companies import metric_registry as registry
from companies import provenance as prov
from companies.evidence import (
    PROVENANCE_MEASURED, PROVENANCE_MODELLED, PROVENANCE_SEEDED, PROVENANCE_UNKNOWN,
)
from companies.models import CompanyMetricProvenance, CompanyProfile
from companies.scoring import (
    COMPOSITE_METHOD, COMPOSITE_METRIC_KEY, COMPOSITE_VERSION, DIMENSION_INPUTS,
    HARM_PENALTY_INPUTS, consumed_material_inputs, recalculate_and_save,
)
from league.models import Company


def _profile(slug, **kwargs):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    return CompanyProfile.objects.create(company=company, status='public',
                                         pollution_level='low', **kwargs)


def _record_all_inputs(profile, origin=PROVENANCE_MEASURED, writer='ingestion'):
    """Give every consumed material input a current provenance row."""
    rows = {}
    for key in consumed_material_inputs(profile):
        rows[key] = prov.record(profile, key, origin, written_by=writer)
    return rows


class DeclaredInputsMatchTheFormulas(SimpleTestCase):
    """
    DIMENSION_INPUTS is the basis of every lineage claim in this PR. If it
    drifts from the calculators, the recorded lineage becomes a plausible
    fiction — worse than none. So it is checked against the functions
    themselves rather than trusted.
    """

    def _fields_referenced_by(self, func_name):
        import ast
        import inspect

        from companies import scoring

        source = inspect.getsource(getattr(scoring, func_name))
        tree = ast.parse(source.lstrip())
        return {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == 'p'
        }

    def test_each_dimension_declares_the_fields_it_reads(self):
        calculators = {
            'public_benefit_score': 'calculate_public_benefit',
            'environmental_responsibility_score': 'calculate_environmental_responsibility',
            'modernization_score': 'calculate_modernization',
            'transparency_anti_corruption_score': 'calculate_transparency',
            'anti_corruption_score': 'calculate_anti_corruption',
            'ethical_alignment_score': 'calculate_ethical_alignment',
        }
        for dimension, func_name in calculators.items():
            with self.subTest(dimension=dimension):
                referenced = self._fields_referenced_by(func_name)
                declared = set(DIMENSION_INPUTS[dimension])

                # pollution_level is a categorical with no provenance row, and
                # is documented as a known lineage gap.
                referenced.discard('pollution_level')

                self.assertEqual(declared, referenced,
                                 f'{func_name} reads {referenced}, '
                                 f'DIMENSION_INPUTS declares {declared}')

    def test_harm_penalty_inputs_are_a_subset_of_what_it_reads(self):
        referenced = self._fields_referenced_by('calculate_harm_penalty')

        self.assertTrue(set(HARM_PENALTY_INPUTS) <= referenced)

    def test_every_declared_input_is_a_registered_material_metric(self):
        declared = {f for fields in DIMENSION_INPUTS.values() for f in fields}
        declared |= set(HARM_PENALTY_INPUTS)

        for field in declared:
            with self.subTest(field=field):
                self.assertIn(field, registry.VALID_KEYS)

    def test_the_composite_key_is_registered_and_derived(self):
        definition = registry.require_metric_definition(COMPOSITE_METRIC_KEY)

        self.assertEqual(definition.kind, registry.DERIVED)
        self.assertEqual(definition.value_location,
                         'companies.CompanyProfile.ecoiq_total_score')


class ConsumedInputs(TestCase):
    """
    "Consumed", not "mentioned". _avg and _weighted skip unknown values, so a
    formula naming four inputs may read three.
    """

    def test_a_fully_populated_profile_consumes_every_declared_input(self):
        profile = _profile('all-known')
        declared = {f for fields in DIMENSION_INPUTS.values() for f in fields}
        declared |= set(HARM_PENALTY_INPUTS)

        self.assertEqual(set(consumed_material_inputs(profile)),
                         declared & prov.MATERIAL_METRIC_KEYS)

    def test_an_unknown_input_is_not_reported_as_consumed(self):
        profile = _profile('one-unknown')
        profile.water_impact_score = None      # in memory; NOT NULL until D4

        self.assertNotIn('water_impact_score', consumed_material_inputs(profile))

    def test_duplicated_inputs_appear_once(self):
        """national_value_score feeds two dimensions."""
        consumed = consumed_material_inputs(_profile('dedupe'))

        self.assertEqual(len(consumed), len(set(consumed)))
        self.assertIn('national_value_score', consumed)


class A_B_C_D_DerivedRowContents(TestCase):

    def setUp(self):
        self.profile = _profile('contents')
        self.inputs = _record_all_inputs(self.profile)
        recalculate_and_save(self.profile)
        self.row = prov.current(self.profile, COMPOSITE_METRIC_KEY)

    def test_a_the_composite_gets_modelled_origin(self):
        self.assertIsNotNone(self.row)
        self.assertEqual(self.row.origin, PROVENANCE_MODELLED)

    def test_a_it_is_never_measured(self):
        self.assertNotEqual(self.row.origin, PROVENANCE_MEASURED)

    def test_b_methodology_is_recorded(self):
        self.assertEqual(self.row.methodology, COMPOSITE_METHOD)
        self.assertEqual(COMPOSITE_METHOD, 'ecoiq-company-composite')

    def test_c_calculation_version_is_recorded(self):
        self.assertEqual(self.row.calculation_version, COMPOSITE_VERSION)

    def test_c_the_version_is_not_a_git_sha(self):
        """
        A SHA changes on every unrelated commit, so it cannot answer "did the
        formula change?" — the only question a version on a MODELLED row is for.
        """
        self.assertLess(len(COMPOSITE_VERSION), 8)
        self.assertNotRegex(COMPOSITE_VERSION, r'^[0-9a-f]{7,}$')

    def test_c_the_writer_is_named(self):
        self.assertEqual(self.row.written_by,
                         'companies.scoring.recalculate_and_save')

    def test_d_the_exact_consumed_rows_are_attached(self):
        consumed = consumed_material_inputs(self.profile)

        self.assertEqual({r.pk for r in prov.lineage(self.row)},
                         {self.inputs[key].pk for key in consumed})

    def test_d_no_human_review_is_fabricated(self):
        """Calculation success is not review."""
        self.assertEqual(self.row.review_status, 'proposed')
        self.assertIsNone(self.row.reviewed_by)
        self.assertIsNone(self.row.confidence)

    def test_d_the_value_resolves_rather_than_being_copied(self):
        self.assertIsNone(self.row.recorded_value)
        self.assertEqual(self.row.value, self.profile.ecoiq_total_score)

    def test_the_status_reports_what_happened(self):
        profile = _profile('status')
        _record_all_inputs(profile)
        recalculate_and_save(profile)

        self.assertEqual(profile.provenance_status, 'recorded')


class E_UnconsumedInputsAreNotAttached(TestCase):
    """
    E — a lineage that names inputs the calculation did not read overstates
    what supported the number.
    """

    def test_e_provenance_for_an_unrelated_metric_is_not_attached(self):
        profile = _profile('unrelated')
        _record_all_inputs(profile)
        # A registered metric the composite does not read. All 16 material
        # inputs ARE consumed, so the unrelated one has to be derived.
        unrelated = prov.record(profile, 'ethics.nei', PROVENANCE_MODELLED)

        recalculate_and_save(profile)
        row = prov.current(profile, COMPOSITE_METRIC_KEY)

        self.assertNotIn(unrelated, prov.lineage(row))

    def test_e_all_sixteen_material_inputs_are_consumed_by_the_composite(self):
        """
        Recorded because it is load-bearing for the test above: there is no
        material metric the composite ignores, so an 'unrelated' material row
        cannot be constructed.
        """
        profile = _profile('all-consumed')

        self.assertEqual(set(consumed_material_inputs(profile)),
                         set(prov.MATERIAL_METRIC_KEYS))

    def test_e_only_declared_inputs_appear(self):
        profile = _profile('declared-only')
        _record_all_inputs(profile)
        recalculate_and_save(profile)

        row = prov.current(profile, COMPOSITE_METRIC_KEY)
        linked = {r.metric_key for r in prov.lineage(row)}

        self.assertEqual(linked, set(consumed_material_inputs(profile)))


class F_G_LineageAsComputed(TestCase):
    """
    F/G — the central invariant. THE reason inputs is an M2M to rows rather
    than to metric keys.
    """

    def setUp(self):
        self.profile = _profile('lineage')
        self.original = _record_all_inputs(self.profile)
        recalculate_and_save(self.profile)
        self.first = prov.current(self.profile, COMPOSITE_METRIC_KEY)

    def test_f_a_new_material_event_produces_new_derived_lineage(self):
        replacement = prov.record(self.profile, 'water_impact_score',
                                  PROVENANCE_SEEDED, written_by='analyst')
        self.profile.water_impact_score = 42.0
        self.profile.save()

        recalculate_and_save(self.profile)
        second = prov.current(self.profile, COMPOSITE_METRIC_KEY)

        self.assertNotEqual(second.pk, self.first.pk)
        self.assertIn(replacement, prov.lineage(second))

    def test_g_the_old_derived_row_still_points_at_the_old_input(self):
        old_input = self.original['water_impact_score']
        prov.record(self.profile, 'water_impact_score', PROVENANCE_SEEDED)
        self.profile.water_impact_score = 42.0
        self.profile.save()
        recalculate_and_save(self.profile)

        self.first.refresh_from_db()
        old_input.refresh_from_db()

        self.assertFalse(self.first.is_current)
        self.assertFalse(old_input.is_current)
        self.assertIn(old_input, prov.lineage(self.first),
                      'lineage must be as computed, not as recomputable')

    def test_g_the_superseded_input_keeps_its_origin(self):
        old_input = self.original['water_impact_score']
        prov.record(self.profile, 'water_impact_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)

        preserved = [r for r in prov.lineage(self.first)
                     if r.metric_key == 'water_impact_score'][0]
        self.assertEqual(preserved.origin, PROVENANCE_MEASURED)

    def test_g_derived_history_accumulates(self):
        prov.record(self.profile, 'water_impact_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)

        rows = prov.history(self.profile, COMPOSITE_METRIC_KEY)
        self.assertEqual(rows.count(), 2)
        self.assertEqual([r.is_current for r in rows], [True, False])


class H_I_J_Idempotency(TestCase):

    def setUp(self):
        self.profile = _profile('idempotent')
        _record_all_inputs(self.profile)
        recalculate_and_save(self.profile)

    def _composite_rows(self):
        return CompanyMetricProvenance.objects.filter(
            company=self.profile, metric_key=COMPOSITE_METRIC_KEY)

    def test_h_an_identical_recalculation_creates_no_new_row(self):
        first_pk = prov.current(self.profile, COMPOSITE_METRIC_KEY).pk

        recalculate_and_save(self.profile)
        recalculate_and_save(self.profile)

        self.assertEqual(self._composite_rows().count(), 1)
        self.assertEqual(prov.current(self.profile, COMPOSITE_METRIC_KEY).pk,
                         first_pk)

    def test_h_the_status_says_unchanged(self):
        recalculate_and_save(self.profile)

        self.assertEqual(self.profile.provenance_status, 'unchanged')

    def test_i_a_changed_input_creates_a_new_event(self):
        prov.record(self.profile, 'water_impact_score', PROVENANCE_SEEDED)

        recalculate_and_save(self.profile)

        self.assertEqual(self._composite_rows().count(), 2)
        self.assertEqual(self.profile.provenance_status, 'recorded')

    def test_i_a_value_change_without_a_provenance_event_is_not_a_new_event(self):
        """
        The documented identity rule: (origin, methodology, version, input rows).
        NOT the output number.

        A material value that moved while its provenance row did not means the
        writer that moved it recorded no event — a gap in that writer, not a
        new lineage claim for this one to make. The score itself is still
        rewritten; only the lineage row is left alone, because the lineage did
        not change.
        """
        before = self.profile.ecoiq_total_score
        self.profile.water_impact_score = 12.0
        self.profile.save()

        recalculate_and_save(self.profile)
        self.profile.refresh_from_db()

        self.assertNotEqual(self.profile.ecoiq_total_score, before,
                            'the score must still be recalculated')
        self.assertEqual(self._composite_rows().count(), 1)
        self.assertEqual(self.profile.provenance_status, 'unchanged')

    def test_j_a_changed_calculation_version_creates_a_new_event(self):
        with patch('companies.scoring.COMPOSITE_VERSION', '2'):
            recalculate_and_save(self.profile)

        self.assertEqual(self._composite_rows().count(), 2)
        self.assertEqual(prov.current(self.profile, COMPOSITE_METRIC_KEY)
                         .calculation_version, '2')

    def test_j_a_changed_methodology_creates_a_new_event(self):
        with patch('companies.scoring.COMPOSITE_METHOD', 'ecoiq-company-composite-v2'):
            recalculate_and_save(self.profile)

        self.assertEqual(self._composite_rows().count(), 2)


class K_L_Atomicity(TestCase):

    def test_k_provenance_failure_rolls_back_the_derived_value(self):
        profile = _profile('rollback-prov', ecoiq_total_score=11.1)
        _record_all_inputs(profile)

        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record_derived',
                       side_effect=RuntimeError('provenance failed')):
                recalculate_and_save(profile)

        profile.refresh_from_db()
        self.assertEqual(profile.ecoiq_total_score, 11.1,
                         'the score must roll back with its provenance')
        self.assertEqual(
            CompanyMetricProvenance.objects.filter(
                metric_key=COMPOSITE_METRIC_KEY).count(), 0)

    def test_k_a_failure_after_the_row_and_lineage_exist_still_rolls_back(self):
        """
        The row and its M2M are created, and THEN something fails. Both must
        disappear along with the score — proving the lineage attachment is
        inside the transaction, not merely that creation is.

        A derived row that survived with no inputs would read as "rests on
        nothing", which is exactly the state this PR refuses to write.
        """
        from companies import provenance as real_prov

        profile = _profile('rollback-after', ecoiq_total_score=22.2)
        _record_all_inputs(profile)
        genuine = real_prov.record_derived

        def create_then_fail(*args, **kwargs):
            row = genuine(*args, **kwargs)
            assert row.inputs.exists(), 'lineage should be attached by now'
            raise RuntimeError('failed after lineage was attached')

        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record_derived', create_then_fail):
                recalculate_and_save(profile)

        profile.refresh_from_db()
        self.assertEqual(profile.ecoiq_total_score, 22.2)
        self.assertEqual(
            CompanyMetricProvenance.objects.filter(
                metric_key=COMPOSITE_METRIC_KEY).count(), 0)
        self.assertEqual(
            CompanyMetricProvenance.inputs.through.objects.count(), 0,
            'the M2M rows must roll back too')

    def test_l_a_derived_save_failure_leaves_no_provenance(self):
        profile = _profile('rollback-save')
        _record_all_inputs(profile)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                recalculate_and_save(profile)
                profile.ecoiq_total_score = None   # NOT NULL until D4
                profile.save()

        self.assertEqual(
            CompanyMetricProvenance.objects.filter(
                metric_key=COMPOSITE_METRIC_KEY).count(), 0)


class M_N_O_PublicDefensibility(TestCase):
    """
    M/N/O — provenance existing is not the same as evidence being good.
    """

    def test_m_a_seeded_input_makes_the_composite_not_defensible(self):
        profile = _profile('seeded-inputs')
        _record_all_inputs(profile, origin=PROVENANCE_SEEDED, writer='seed:test')
        recalculate_and_save(profile)

        row = prov.current(profile, COMPOSITE_METRIC_KEY)
        self.assertEqual(row.origin, PROVENANCE_MODELLED)
        self.assertTrue(prov.lineage(row))
        self.assertFalse(
            prov.is_derived_publicly_defensible(profile, COMPOSITE_METRIC_KEY))

    def test_m_one_seeded_input_among_many_is_enough_to_block(self):
        profile = _profile('one-seeded')
        _record_all_inputs(profile, origin=PROVENANCE_MEASURED)
        prov.record(profile, 'water_impact_score', PROVENANCE_SEEDED)
        recalculate_and_save(profile)

        self.assertFalse(
            prov.is_derived_publicly_defensible(profile, COMPOSITE_METRIC_KEY))

    def test_n_a_legacy_input_makes_the_composite_not_defensible(self):
        profile = _profile('legacy-inputs')
        _record_all_inputs(profile, origin=PROVENANCE_UNKNOWN,
                           writer='d3b_backfill')
        recalculate_and_save(profile)

        self.assertFalse(
            prov.is_derived_publicly_defensible(profile, COMPOSITE_METRIC_KEY))

    def test_evidenced_inputs_do_produce_a_defensible_composite(self):
        """The mirror — the guard must not reject everything."""
        profile = _profile('evidenced')
        _record_all_inputs(profile, origin=PROVENANCE_MEASURED)
        recalculate_and_save(profile)

        self.assertTrue(
            prov.is_derived_publicly_defensible(profile, COMPOSITE_METRIC_KEY))

    def test_o_missing_input_provenance_is_never_guessed(self):
        """
        The case that matters today: D3B has not run in production, so most
        profiles have values and no provenance.
        """
        profile = _profile('no-provenance')

        recalculate_and_save(profile)

        self.assertEqual(profile.provenance_status, 'incomplete')
        self.assertIsNone(prov.current(profile, COMPOSITE_METRIC_KEY))
        self.assertEqual(CompanyMetricProvenance.objects.count(), 0,
                         'no material provenance may be invented either')

    def test_o_the_score_is_still_written_when_lineage_is_incomplete(self):
        """Provenance completeness does not gate the calculation."""
        profile = _profile('score-still-written')

        recalculate_and_save(profile)
        profile.refresh_from_db()

        self.assertIsNotNone(profile.ecoiq_total_score)
        self.assertGreater(profile.ecoiq_total_score, 0)

    def test_o_partial_input_provenance_is_still_incomplete(self):
        """One missing row is enough — no half-lineage is recorded."""
        profile = _profile('partial')
        rows = _record_all_inputs(profile)
        rows['water_impact_score'].delete()

        recalculate_and_save(profile)

        self.assertEqual(profile.provenance_status, 'incomplete')
        self.assertIsNone(prov.current(profile, COMPOSITE_METRIC_KEY))

    def test_o_an_empty_input_list_is_never_recorded_as_lineage(self):
        """
        An empty list reads as "rests on nothing", which is indistinguishable
        from "we did not record what it rests on". The second is the truth.
        """
        profile = _profile('empty-lineage')
        recalculate_and_save(profile)

        rows = CompanyMetricProvenance.objects.filter(
            metric_key=COMPOSITE_METRIC_KEY)
        self.assertEqual(rows.count(), 0)


class P_Q_RealValues(TestCase):
    """P/Q — the number never decides the provenance."""

    def test_p_a_zero_input_is_consumed_as_a_number(self):
        profile = _profile('zero-input', water_impact_score=0.0)
        rows = _record_all_inputs(profile)

        recalculate_and_save(profile)
        row = prov.current(profile, COMPOSITE_METRIC_KEY)

        self.assertIn('water_impact_score', consumed_material_inputs(profile))
        self.assertIn(rows['water_impact_score'], prov.lineage(row))
        self.assertEqual(row.origin, PROVENANCE_MODELLED)

    def test_q_a_fifty_input_is_consumed_as_a_number(self):
        profile = _profile('fifty-input', water_impact_score=50.0)
        rows = _record_all_inputs(profile)

        recalculate_and_save(profile)
        row = prov.current(profile, COMPOSITE_METRIC_KEY)

        self.assertIn(rows['water_impact_score'], prov.lineage(row))

    def test_a_zero_input_changes_the_score_but_not_the_origin(self):
        zeroed = _profile('all-zero')
        for key in prov.MATERIAL_METRIC_KEYS:
            setattr(zeroed, key, 0.0)
        zeroed.save()
        _record_all_inputs(zeroed)

        recalculate_and_save(zeroed)
        zeroed.refresh_from_db()

        self.assertEqual(
            prov.current(zeroed, COMPOSITE_METRIC_KEY).origin, PROVENANCE_MODELLED)


class R_SeedFlowEndToEnd(TestCase):
    """
    R — the whole chain, exactly as a seed run executes it.

    seed values -> SEEDED material provenance -> recalculate_and_save ->
    MODELLED composite -> inputs point at SEEDED rows -> not publicly defensible
    """

    def test_r_a_real_seed_command_produces_the_full_chain(self):
        from io import StringIO

        from django.core.management import call_command

        call_command('seed_global_companies', stdout=StringIO(), stderr=StringIO())

        profile = CompanyProfile.objects.select_related('company').first()
        self.assertIsNotNone(profile)

        composite = prov.current(profile, COMPOSITE_METRIC_KEY)
        self.assertIsNotNone(composite, 'the seed run must record composite lineage')
        self.assertEqual(composite.origin, PROVENANCE_MODELLED)

        linked = prov.lineage(composite)
        self.assertTrue(linked)
        self.assertEqual({r.origin for r in linked}, {PROVENANCE_SEEDED})
        self.assertEqual({r.written_by for r in linked},
                         {'seed:seed_global_companies'})

        self.assertFalse(
            prov.is_derived_publicly_defensible(profile, COMPOSITE_METRIC_KEY),
            'a modelled composite over seeded inputs must not be publishable')

    def test_r_every_seeded_company_gets_composite_lineage(self):
        from io import StringIO

        from django.core.management import call_command

        call_command('seed_global_companies', stdout=StringIO(), stderr=StringIO())

        total = CompanyProfile.objects.count()
        with_lineage = CompanyMetricProvenance.objects.filter(
            metric_key=COMPOSITE_METRIC_KEY, is_current=True).count()

        self.assertEqual(with_lineage, total)


class S_T_PublicSurfacesUnchanged(TestCase):
    """
    S/T — no score resurrection. A MODELLED provenance row existing changes
    nothing about what the public sees.
    """

    def setUp(self):
        self.profile = _profile('public', ecoiq_total_score=71.4)
        self.profile.company.ecoiq_score = 71.4
        self.profile.company.save()
        _record_all_inputs(self.profile, origin=PROVENANCE_MEASURED)
        recalculate_and_save(self.profile)

    def test_s_the_company_page_is_still_evidence_pending(self):
        from django.test import Client

        from companies.evidence import PENDING_HEADLINE

        body = Client().get('/companies/public/').content.decode()

        self.assertIn(PENDING_HEADLINE, body)

    def test_s_the_composite_has_defensible_provenance_yet_stays_contained(self):
        """
        The distinction that matters: provenance quality and PUBLICATION are
        separate gates. D5 owns the second, and D3C-3 did not touch it.
        """
        self.assertTrue(
            prov.is_derived_publicly_defensible(self.profile, COMPOSITE_METRIC_KEY))

        from companies.evidence import public_score_state
        self.assertFalse(public_score_state(self.profile).available)

    def test_t_api_v2_is_still_fail_closed(self):
        from django.test import Client

        payload = Client().get('/api/v2/companies/public/').json()

        self.assertIsNone(payload['ecoiq_score'])
        self.assertEqual(payload['score_status'], 'INSUFFICIENT_EVIDENCE')
        self.assertNotIn('provenance', payload)

    def test_t_the_league_page_is_still_fail_closed(self):
        from django.test import Client

        from companies.evidence import PENDING_HEADLINE

        body = Client().get('/league/').content.decode()

        self.assertIn(PENDING_HEADLINE, body)


class CallerCompatibility(TestCase):
    """
    STEP 1 — six callers, some already inside a transaction and some not.
    The return contract must not have changed for any of them.
    """

    def test_the_function_still_returns_the_profile(self):
        profile = _profile('return-contract')

        self.assertIs(recalculate_and_save(profile), profile)

    def test_it_works_inside_an_existing_transaction(self):
        """seed_companies calls it inside its own atomic block."""
        profile = _profile('inside-atomic')
        _record_all_inputs(profile)

        with transaction.atomic():
            recalculate_and_save(profile)

        self.assertEqual(profile.provenance_status, 'recorded')
        self.assertIsNotNone(prov.current(profile, COMPOSITE_METRIC_KEY))

    def test_it_works_outside_a_transaction(self):
        """seed_global_companies calls it after its atomic block."""
        profile = _profile('outside-atomic')
        _record_all_inputs(profile)

        recalculate_and_save(profile)

        self.assertEqual(profile.provenance_status, 'recorded')

    def test_provenance_can_be_switched_off_for_a_caller_that_needs_it(self):
        profile = _profile('opt-out')
        _record_all_inputs(profile)

        recalculate_and_save(profile, record_provenance=False)

        self.assertEqual(profile.provenance_status, 'skipped')
        self.assertIsNone(prov.current(profile, COMPOSITE_METRIC_KEY))

    def test_no_composite_means_nothing_to_attest(self):
        profile = _profile('no-composite')
        _record_all_inputs(profile)
        profile.pollution_level = None
        profile.water_impact_score = None
        profile.waste_management_score = None
        profile.biodiversity_impact_score = None

        recalculate_and_save(profile)

        self.assertEqual(profile.provenance_status, 'no_composite')
        self.assertIsNone(prov.current(profile, COMPOSITE_METRIC_KEY))
