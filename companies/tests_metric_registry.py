"""
D3C-2 — derived metric registry.

Covers A–R from the brief. Establishes metric IDENTITY and VALUE LOCATION so
provenance can be recorded for outputs that do not live on CompanyProfile.

Two tests carry most of the weight:

  * J/K — a derived metric may be MODELLED but never MEASURED, and a MODELLED
    composite over SEEDED inputs is not publishable. A perfectly-executed
    calculation over synthetic data is still synthetic.
  * M — lineage is what was consumed AT CALCULATION TIME. Re-reading current
    inputs would answer "what would this be if recomputed now?", which is not
    an audit trail.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import SimpleTestCase, TestCase

from companies import metric_registry as registry
from companies import provenance as prov
from companies.evidence import (
    PROVENANCE_MEASURED, PROVENANCE_MODELLED, PROVENANCE_SEEDED, PROVENANCE_UNKNOWN,
)
from companies.models import CompanyMetricProvenance, CompanyProfile
from companies.provenance import LineageCycle, record_derived
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



def _profile(slug, **kwargs):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    return _populated(company=company, status='public', **kwargs)


class A_B_C_D_RegistryLookup(SimpleTestCase):

    def test_a_a_known_material_metric_resolves(self):
        definition = registry.get_metric_definition('water_impact_score')

        self.assertIsNotNone(definition)
        self.assertEqual(definition.kind, registry.MATERIAL)
        self.assertEqual(definition.value_location,
                         'companies.CompanyProfile.water_impact_score')

    def test_b_a_known_derived_metric_resolves(self):
        definition = registry.get_metric_definition('ethics.nei')

        self.assertIsNotNone(definition)
        self.assertEqual(definition.kind, registry.DERIVED)
        self.assertEqual(definition.value_location,
                         'ethics.CompanyEthicsProfile.net_ethical_impact')

    def test_c_an_arbitrary_key_is_rejected(self):
        for bad in ('NEI Score', 'ethical score 2', 'mizan-score-final',
                    'env score', '', 'nei'):
            with self.subTest(key=bad):
                self.assertIsNone(registry.get_metric_definition(bad))
                with self.assertRaises(ValueError):
                    registry.require_metric_definition(bad)

    def test_c_validation_is_strict_not_any_non_empty_string(self):
        self.assertNotIn('anything', registry.VALID_KEYS)
        self.assertGreater(len(registry.VALID_KEYS), 0)

    def test_d_a_duplicate_key_is_rejected_by_the_builder(self):
        """
        A duplicate would make provenance ambiguous about which metric it
        describes. Exercised against the real builder rather than a re-implemented
        loop, so the guard itself is what is under test.
        """
        duplicate = registry.REGISTRY['ethics.nei']
        original = registry._DERIVED_DEFINITIONS

        registry._DERIVED_DEFINITIONS = original + [duplicate]
        try:
            with self.assertRaises(ValueError) as ctx:
                registry._build_registry()
            self.assertIn('Duplicate metric key', str(ctx.exception))
        finally:
            registry._DERIVED_DEFINITIONS = original

    def test_d_the_live_registry_has_no_duplicates(self):
        keys = [d.key for d in
                registry._MATERIAL_DEFINITIONS + registry._DERIVED_DEFINITIONS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_lookup_is_constant_time_not_a_scan(self):
        """STEP 18 — a dict access, safe to call per row."""
        self.assertIsInstance(registry.REGISTRY, dict)


class E_KindsAreDistinct(SimpleTestCase):

    def test_e_material_and_derived_do_not_overlap(self):
        self.assertEqual(registry.MATERIAL_KEYS & registry.DERIVED_KEYS, frozenset())
        self.assertEqual(registry.MATERIAL_KEYS | registry.DERIVED_KEYS,
                         registry.VALID_KEYS)

    def test_e_only_two_kinds_exist(self):
        """
        'AI', 'FINANCE', 'CLIMATE' are domains, not provenance semantics. The
        registry is about how a value came to exist, not what it is about.
        """
        self.assertEqual(set(registry.KINDS), {'MATERIAL', 'DERIVED'})
        self.assertEqual({d.kind for d in registry.REGISTRY.values()},
                         {'MATERIAL', 'DERIVED'})

    def test_e_metric_keys_are_stable_identifiers_not_display_copy(self):
        for key in registry.DERIVED_KEYS:
            with self.subTest(key=key):
                self.assertRegex(key, r'^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$')
                self.assertNotIn(' ', key)
                self.assertEqual(key, key.lower())

    def test_e_labels_may_change_without_changing_identity(self):
        """Identity must not depend on display copy."""
        definition = registry.REGISTRY['ethics.nei']
        self.assertNotEqual(definition.key, definition.label)


class F_ValueLocationResolution(TestCase):
    """
    F — the problem D3C-1 identified. getattr(profile, key) is wrong for most
    derived metrics, and the registry has to know where each one lives.
    """

    def setUp(self):
        self.profile = _profile('resolve', water_impact_score=68.0,
                                ecoiq_total_score=71.4)

    def test_f_a_material_metric_resolves_from_the_profile(self):
        self.assertEqual(
            registry.resolve_value(self.profile, 'water_impact_score'), 68.0)

    def test_f_a_profile_level_derived_metric_resolves_from_the_profile(self):
        self.assertEqual(
            registry.resolve_value(self.profile, 'company.ecoiq_total'), 71.4)

    def test_f_a_related_model_metric_resolves_through_the_relation(self):
        from ethics.models import CompanyEthicsProfile

        CompanyEthicsProfile.objects.create(profile=self.profile,
                                            net_ethical_impact=61.5)

        self.assertEqual(registry.resolve_value(self.profile, 'ethics.nei'), 61.5)

    def test_f_a_missing_relation_resolves_to_none_not_an_error(self):
        """A company with no ethics profile has not been assessed, not errored."""
        self.assertIsNone(registry.resolve_value(self.profile, 'ethics.nei'))

    def test_f_a_league_company_metric_resolves_through_company(self):
        self.profile.company.ml_score = 64.2
        self.profile.company.save()

        self.assertEqual(
            float(registry.resolve_value(self.profile, 'ml.score')), 64.2)

    def test_f_a_foreign_key_metric_resolves_to_the_latest(self):
        from qdf.models import DecisionAssessment

        # (profile, source) is unique, so distinct sources — which is also the
        # realistic case the 'latest' resolver exists for.
        DecisionAssessment.objects.create(profile=self.profile, subject_type='company',
                                          subject_name='old', source='manual',
                                          decision_integrity_score=40.0)
        DecisionAssessment.objects.create(profile=self.profile, subject_type='company',
                                          subject_name='new', source='auto',
                                          decision_integrity_score=80.0)

        self.assertEqual(
            registry.resolve_value(self.profile, 'qdf.decision_integrity'), 80.0)

    def test_f_an_ephemeral_metric_has_no_resolver(self):
        for key in ('mizan.score', 'ml.responsible_finance', 'greenwashing.risk'):
            with self.subTest(key=key):
                self.assertTrue(registry.REGISTRY[key].is_ephemeral)
                self.assertIsNone(registry.resolve_value(self.profile, key))

    def test_f_resolvers_are_explicit_callables_not_dynamic_imports(self):
        """No import from a stored string; a moved metric fails at import."""
        for key, definition in registry.REGISTRY.items():
            with self.subTest(key=key):
                self.assertTrue(definition.resolver is None or callable(definition.resolver))


class G_H_I_ValuesAreNotReinterpreted(TestCase):

    def setUp(self):
        self.profile = _profile('values')

    def test_g_a_real_zero_derived_value_stays_zero(self):
        self.profile.ecoiq_total_score = 0.0
        self.profile.save()

        self.assertEqual(
            registry.resolve_value(self.profile, 'company.ecoiq_total'), 0.0)
        self.assertIsNotNone(
            registry.resolve_value(self.profile, 'company.ecoiq_total'))

    def test_h_a_real_fifty_derived_value_stays_fifty(self):
        self.profile.ecoiq_total_score = 50.0
        self.profile.save()

        self.assertEqual(
            registry.resolve_value(self.profile, 'company.ecoiq_total'), 50.0)

    def test_i_a_none_derived_value_passes_through_as_none(self):
        """
        Blanked in memory: CompanyEthicsProfile.net_ethical_impact is still NOT
        NULL until D4, so this state cannot be saved. Resolution is what is
        under test, and it must pass None through rather than substitute.
        """
        from ethics.models import CompanyEthicsProfile

        ethics = CompanyEthicsProfile.objects.create(profile=self.profile,
                                                     net_ethical_impact=61.5)
        self.assertEqual(registry.resolve_value(self.profile, 'ethics.nei'), 61.5)

        ethics.net_ethical_impact = None
        self.profile.ethics = ethics          # in-memory relation

        self.assertIsNone(registry.REGISTRY['ethics.nei'].resolve(self.profile))

    def test_i_an_unresolvable_metric_is_none_not_zero(self):
        self.assertIsNone(registry.resolve_value(self.profile, 'ml.predicted_12m'))


class J_K_DerivedOriginPolicy(TestCase):
    """
    J/K — the mislabel D3C-1 flagged as most likely to slip through.

    A composite is a model output however good its inputs. Calling it MEASURED
    claims an observation that never happened.
    """

    def setUp(self):
        self.profile = _profile('origins', ecoiq_total_score=71.4)

    def test_j_modelled_is_allowed_for_a_derived_metric(self):
        row = prov.record(self.profile, 'company.ecoiq_total', PROVENANCE_MODELLED)

        self.assertEqual(row.origin, PROVENANCE_MODELLED)

    def test_j_measured_is_rejected_for_a_derived_metric(self):
        with self.assertRaises(ValueError) as ctx:
            prov.record(self.profile, 'company.ecoiq_total', PROVENANCE_MEASURED)

        self.assertIn('MEASURED', str(ctx.exception))

    def test_j_measured_is_rejected_for_every_derived_metric(self):
        for key in sorted(registry.DERIVED_KEYS):
            with self.subTest(key=key):
                self.assertNotIn(PROVENANCE_MEASURED,
                                 registry.REGISTRY[key].allowed_origins)

    def test_j_the_model_layer_rejects_it_too(self):
        """A script bypassing the service must not evade the policy."""
        row = CompanyMetricProvenance(company=self.profile,
                                      metric_key='company.ecoiq_total',
                                      origin=PROVENANCE_MEASURED)
        with self.assertRaises(ValidationError):
            row.save()

    def test_j_material_metrics_keep_their_shipped_origin_contract(self):
        """
        D3A permits MEASURED on material metrics and tests it. D3C-2 does not
        narrow that — see the note in metric_registry.MATERIAL_ORIGINS.
        """
        self.profile.water_impact_score = 68.0
        self.profile.save()
        row = prov.record(self.profile, 'water_impact_score', PROVENANCE_MEASURED)

        self.assertEqual(row.origin, PROVENANCE_MEASURED)

    def test_k_a_seeded_derived_output_is_not_publicly_defensible(self):
        prov.record(self.profile, 'company.ecoiq_total', PROVENANCE_SEEDED)

        self.assertFalse(
            prov.is_derived_publicly_defensible(self.profile, 'company.ecoiq_total'))

    def test_k_a_modelled_composite_over_seeded_inputs_is_not_defensible(self):
        """
        The rule that stops laundering. A perfectly-executed calculation over
        synthetic data is still synthetic.
        """
        self.profile.water_impact_score = 68.0
        self.profile.save()
        seeded_input = prov.record(self.profile, 'water_impact_score',
                                   PROVENANCE_SEEDED)

        with transaction.atomic():
            record_derived(self.profile, 'company.ecoiq_total',
                           writer='companies.scoring', methodology='six-pillar composite',
                           calculation_version='scoring.v1', inputs=[seeded_input])

        self.assertFalse(
            prov.is_derived_publicly_defensible(self.profile, 'company.ecoiq_total'))

    def test_k_a_modelled_composite_over_evidenced_inputs_is_defensible(self):
        """The mirror — the rule must not reject everything."""
        self.profile.water_impact_score = 68.0
        self.profile.save()
        good_input = prov.record(self.profile, 'water_impact_score',
                                 PROVENANCE_MEASURED)

        with transaction.atomic():
            record_derived(self.profile, 'company.ecoiq_total',
                           writer='companies.scoring', methodology='six-pillar composite',
                           calculation_version='scoring.v1', inputs=[good_input])

        self.assertTrue(
            prov.is_derived_publicly_defensible(self.profile, 'company.ecoiq_total'))

    def test_k_a_derived_row_with_no_recorded_inputs_is_not_defensible(self):
        """
        The honest reading before D3C-4 wires the calculators up: we cannot show
        the lineage, so we cannot defend it.
        """
        prov.record(self.profile, 'company.ecoiq_total', PROVENANCE_MODELLED)

        self.assertFalse(
            prov.is_derived_publicly_defensible(self.profile, 'company.ecoiq_total'))


class L_M_N_InputLineage(TestCase):

    def setUp(self):
        self.profile = _profile('lineage', water_impact_score=68.0,
                                waste_management_score=55.0, ecoiq_total_score=71.4)

    def _derived_with_inputs(self, inputs):
        with transaction.atomic():
            return record_derived(
                self.profile, 'company.ecoiq_total', writer='companies.scoring',
                methodology='six-pillar composite', calculation_version='scoring.v1',
                inputs=inputs)

    def test_l_input_provenance_links_to_derived_provenance(self):
        a = prov.record(self.profile, 'water_impact_score', PROVENANCE_MEASURED)
        b = prov.record(self.profile, 'waste_management_score', PROVENANCE_MEASURED)

        row = self._derived_with_inputs([a, b])

        self.assertEqual(set(prov.lineage(row)), {a, b})

    def test_l_the_reverse_relation_names_the_derived_rows(self):
        a = prov.record(self.profile, 'water_impact_score', PROVENANCE_MEASURED)
        row = self._derived_with_inputs([a])

        self.assertIn(row, a.derived_from.all())

    def test_m_lineage_stays_pinned_to_the_rows_consumed(self):
        """
        THE point of an M2M to rows rather than to metric keys.

        After a newer current row supersedes the input, the derived row must
        still name the row it actually read — not whatever is current now.
        """
        original = prov.record(self.profile, 'water_impact_score', PROVENANCE_MEASURED)
        derived = self._derived_with_inputs([original])

        superseding = prov.record(self.profile, 'water_impact_score',
                                  PROVENANCE_SEEDED)
        original.refresh_from_db()

        self.assertFalse(original.is_current)
        self.assertTrue(superseding.is_current)
        self.assertEqual(prov.lineage(derived), [original],
                         'lineage must be as computed, not as recomputable')
        self.assertNotIn(superseding, prov.lineage(derived))

    def test_m_a_superseded_input_keeps_its_origin(self):
        original = prov.record(self.profile, 'water_impact_score', PROVENANCE_MEASURED)
        derived = self._derived_with_inputs([original])
        prov.record(self.profile, 'water_impact_score', PROVENANCE_SEEDED)

        self.assertEqual(prov.lineage(derived)[0].origin, PROVENANCE_MEASURED)

    def test_n_a_row_cannot_be_its_own_input(self):
        """
        STEP 8. The service compares the new row's pk against every input, so
        handing it a stub carrying that pk is exactly the situation a buggy
        caller would produce — a calculation passing its own output back in.
        """
        from django.db import models as dj_models

        next_pk = (CompanyMetricProvenance.objects.aggregate(
            m=dj_models.Max('id'))['m'] or 0) + 1

        with self.assertRaises(LineageCycle):
            record_derived(self.profile, 'company.ecoiq_total', writer='x',
                           methodology='m', calculation_version='v1',
                           inputs=[_SelfRefStub(next_pk)])

    def test_n_a_prior_row_of_the_same_metric_is_a_legitimate_input(self):
        """
        Not every reference to the same metric is a cycle. A recalculation may
        legitimately cite the previous state it superseded.
        """
        previous = prov.record(self.profile, 'company.ecoiq_total',
                               PROVENANCE_MODELLED)

        with transaction.atomic():
            row = record_derived(self.profile, 'company.ecoiq_total', writer='x',
                                 methodology='m', calculation_version='v2',
                                 inputs=[previous])

        self.assertEqual(prov.lineage(row), [previous])

    def test_n_a_normal_input_is_not_mistaken_for_a_cycle(self):
        a = prov.record(self.profile, 'water_impact_score', PROVENANCE_MEASURED)
        row = self._derived_with_inputs([a])

        self.assertEqual(len(prov.lineage(row)), 1)


class _SelfRefStub:
    """Stands in for a row whose pk collides with the newly created one."""

    def __init__(self, pk):
        self.pk = pk


class O_P_Q_DerivedSemantics(TestCase):

    def setUp(self):
        self.profile = _profile('semantics', ecoiq_total_score=71.4)

    def test_o_no_human_review_is_fabricated_by_a_calculation(self):
        """Calculation success is not review."""
        with transaction.atomic():
            row = record_derived(self.profile, 'company.ecoiq_total',
                                 writer='companies.scoring', methodology='composite',
                                 calculation_version='scoring.v1')

        self.assertEqual(row.review_status, 'proposed')
        self.assertIsNone(row.reviewed_by)
        self.assertIsNone(row.reviewed_at)
        self.assertIsNone(row.confidence)

    def test_p_calculation_version_is_recorded(self):
        with transaction.atomic():
            row = record_derived(self.profile, 'company.ecoiq_total',
                                 writer='companies.scoring',
                                 methodology='six-pillar weighted composite',
                                 calculation_version='scoring.v1')

        self.assertEqual(row.calculation_version, 'scoring.v1')
        self.assertEqual(row.methodology, 'six-pillar weighted composite')

    def test_p_methodology_and_version_are_required(self):
        for methodology, version in (('', 'v1'), ('m', ''), ('', '')):
            with self.subTest(methodology=methodology, version=version):
                with self.assertRaises(ValueError):
                    record_derived(self.profile, 'company.ecoiq_total',
                                   writer='x', methodology=methodology,
                                   calculation_version=version)

    def test_q_an_ephemeral_metric_carries_its_recorded_value(self):
        """
        STEP 9 decision: DERIVED provenance may hold the value when nothing
        persists it, because otherwise the lineage describes a number nobody
        can see again.
        """
        with transaction.atomic():
            row = record_derived(self.profile, 'mizan.score',
                                 writer='mizan.scoring', methodology='six-dimension',
                                 calculation_version='mizan:v1',
                                 recorded_value=62.3)

        self.assertEqual(row.recorded_value, 62.3)
        self.assertEqual(row.value, 62.3)

    def test_q_an_ephemeral_metric_requires_a_recorded_value(self):
        with self.assertRaises(ValueError):
            record_derived(self.profile, 'mizan.score', writer='mizan.scoring',
                           methodology='six-dimension', calculation_version='v1')

    def test_q_a_persisted_metric_rejects_a_recorded_value(self):
        """No duplicate value where one already has a home — D3A's rule stands."""
        with self.assertRaises(ValidationError):
            with transaction.atomic():
                record_derived(self.profile, 'company.ecoiq_total',
                               writer='companies.scoring', methodology='composite',
                               calculation_version='scoring.v1',
                               recorded_value=71.4)

    def test_q_a_persisted_metric_still_resolves_through_the_registry(self):
        with transaction.atomic():
            row = record_derived(self.profile, 'company.ecoiq_total',
                                 writer='companies.scoring', methodology='composite',
                                 calculation_version='scoring.v1')

        self.assertIsNone(row.recorded_value)
        self.assertEqual(row.value, 71.4)

        self.profile.ecoiq_total_score = 80.0
        self.profile.save()
        row.refresh_from_db()
        self.assertEqual(row.value, 80.0, 'resolved, never copied')


class R_MaterialCompatibility(TestCase):
    """
    R — D3C-2 must not destabilise D1 or D3A.
    """

    def test_r_material_inputs_remains_the_canonical_coverage_list(self):
        from companies.evidence import MATERIAL_INPUTS

        self.assertEqual(prov.MATERIAL_METRIC_KEYS,
                         frozenset(i.field_name for i in MATERIAL_INPUTS))

    def test_r_every_material_input_is_registered(self):
        from companies.evidence import MATERIAL_INPUTS

        for item in MATERIAL_INPUTS:
            with self.subTest(field=item.field_name):
                self.assertIn(item.field_name, registry.VALID_KEYS)

    def test_r_material_keys_were_not_renamed(self):
        """
        Renaming them to a dotted namespace would invalidate every provenance
        row D3B and D3C-1 already wrote, for cosmetic consistency.
        """
        self.assertIn('water_impact_score', registry.VALID_KEYS)
        self.assertNotIn('material.water_impact', registry.VALID_KEYS)

    def test_r_coverage_helpers_remain_material_scoped(self):
        profile = _profile('compat')
        summary = prov.summarise(profile)

        self.assertEqual(summary['total_metrics'], len(prov.MATERIAL_METRIC_KEYS))
        self.assertEqual(sorted(prov.unrecorded_metrics(profile)),
                         sorted(prov.MATERIAL_METRIC_KEYS))

    def test_r_the_seed_writer_still_records_only_material_metrics(self):
        from companies.provenance import record_seed_write

        profile = _profile('seed-compat')
        record_seed_write(profile, list(registry.VALID_KEYS), 'seed:test')

        keys = set(CompanyMetricProvenance.objects.values_list('metric_key', flat=True))
        self.assertEqual(keys, set(prov.MATERIAL_METRIC_KEYS))
        self.assertEqual(keys & registry.DERIVED_KEYS, set())

    def test_r_public_surfaces_are_unchanged(self):
        from django.test import Client

        from companies.evidence import PENDING_HEADLINE

        profile = _profile('registry-contained', ecoiq_total_score=71.4)
        prov.record(profile, 'company.ecoiq_total', PROVENANCE_MODELLED)

        body = Client().get('/companies/registry-contained/').content.decode()
        self.assertIn(PENDING_HEADLINE, body)
        self.assertNotIn('71.4', body)

    def test_r_api_v2_exposes_no_provenance_yet(self):
        from django.test import Client

        profile = _profile('registry-v2', ecoiq_total_score=71.4)
        prov.record(profile, 'company.ecoiq_total', PROVENANCE_MODELLED)

        payload = Client().get('/api/v2/companies/registry-v2/').json()

        self.assertNotIn('provenance', payload)
        self.assertIsNone(payload['ecoiq_score'])

    def test_r_legacy_backfill_origins_still_apply_to_derived_metrics(self):
        """
        LINEAGE_ABSENT states describe the absence of lineage, so they are
        honest for any metric — a derived metric can be legacy too.
        """
        profile = _profile('legacy-derived')
        row = prov.record(profile, 'ethics.nei', PROVENANCE_UNKNOWN)

        self.assertEqual(row.origin, PROVENANCE_UNKNOWN)
