"""
D3C-3e — Mizan lineage. The first EPHEMERAL derived metric.

Covers A–W. mizan.score has no canonical persisted field: it is recomputed per
request and discarded. So its provenance must carry `recorded_value` — the
column #248 added and no writer has used until now — or the lineage describes a
number nobody can see again.

Two things make this writer different from every previous one:

  * score_company() is PURE and is called from views on every request, so Mizan
    needed a new explicit write path rather than gaining one on an existing save.
  * The ephemeral identity rule includes the OUTPUT, because the calculator
    reads four inputs that are not registered metrics — pollution_level,
    is_verified, status, ai_summary — and those can move the number without
    moving the lineage.
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
from league.models import Company
from mizan.scoring import (
    MIZAN_INPUTS, MIZAN_METHOD, MIZAN_METRIC_KEY, MIZAN_VERSION, score_and_record,
    score_company,
)


def _profile(slug, **kwargs):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    return CompanyProfile.objects.create(company=company, status='public',
                                         pollution_level='low', **kwargs)


def _build_chain(profile, origin=PROVENANCE_MEASURED, writer='ingestion'):
    """Material provenance, then the pillars recalculate_and_save derives."""
    for key in sorted(prov.MATERIAL_METRIC_KEYS):
        if registry.resolve_value(profile, key) is not None:
            prov.record(profile, key, origin, written_by=writer)
    recalculate_and_save(profile)
    return {row.metric_key: row for row in
            CompanyMetricProvenance.objects.filter(company=profile, is_current=True)}


class DependencyGate(SimpleTestCase):
    """
    THE BLOCKING CHECK, asserted so it cannot silently change.

    mizan.score does NOT consume greenwashing.risk. `final` is computed at
    scoring.py:463; greenwashing_from_profile is not called until line 505 —
    forty-two lines later — and its result reaches only a narrative risk_flags
    string and a passthrough dict on the result object.

    Classification: ADVISORY / FLAG ONLY. That is why Mizan could proceed
    without a greenwashing provenance writer existing first.
    """

    def _source(self):
        from pathlib import Path

        return (Path(__file__).resolve().parent / 'scoring.py').read_text()

    def test_the_score_is_computed_before_greenwashing_is_called(self):
        source = self._source()
        final_at = source.index('final = _clamp(_weighted(')
        greenwashing_at = source.index('gw_result = greenwashing_from_profile')

        self.assertLess(final_at, greenwashing_at,
                        'if this reverses, greenwashing becomes a real input and '
                        'Mizan lineage is incomplete until it has provenance')

    def test_greenwashing_is_not_a_declared_mizan_input(self):
        self.assertNotIn('greenwashing.risk', MIZAN_INPUTS)

    def test_greenwashing_reaches_only_narrative_and_passthrough(self):
        """
        Its two uses: a string appended to risk_flags, and to_dict() carried on
        the result. Neither touches final_mizan_score.
        """
        source = self._source()
        after = source[source.index('gw_result = greenwashing_from_profile'):]
        uses = [line.strip() for line in after.splitlines()
                if 'gw_result' in line and not line.strip().startswith('#')]

        self.assertTrue(uses)
        for use in uses:
            with self.subTest(use=use):
                self.assertNotIn('final', use)
                self.assertNotIn('_weighted', use)


class RegistryAndShape(SimpleTestCase):

    def test_the_metric_is_registered_derived_and_ephemeral(self):
        definition = registry.require_metric_definition(MIZAN_METRIC_KEY)

        self.assertEqual(definition.kind, registry.DERIVED)
        self.assertTrue(definition.is_ephemeral)
        self.assertIsNone(definition.resolver)

    def test_the_key_is_the_repository_canonical_one(self):
        self.assertEqual(MIZAN_METRIC_KEY, 'mizan.score')

    def test_every_declared_input_is_registered(self):
        for key in MIZAN_INPUTS:
            with self.subTest(key=key):
                self.assertIn(key, registry.VALID_KEYS)

    def test_derived_inputs_are_declared_as_derived(self):
        """Not flattened to their own material inputs."""
        derived = {k for k in MIZAN_INPUTS if k in registry.DERIVED_KEYS}

        self.assertEqual(derived, {'company.public_benefit',
                                   'company.transparency_governance',
                                   'company.ethical_alignment'})

    def test_the_declared_inputs_match_what_the_formula_reads(self):
        """
        Parsed from the function up to the line that computes the score, so a
        formula that gains an input and a declaration that does not will fail
        here rather than producing plausible fiction.
        """
        from pathlib import Path

        source = (Path(__file__).resolve().parent / 'scoring.py').read_text()
        start = source.index('def score_company(')
        end = source.index('final = _clamp(_weighted(')
        read = set()
        for token in source[start:end].split('profile.')[1:]:
            read.add(token.split()[0].strip('),:.'))

        # Not registered metrics, documented as gaps in MIZAN_INPUTS.
        read -= {'pollution_level', 'is_verified', 'status', 'ai_summary'}

        declared_fields = {
            registry.REGISTRY[k].value_location.rsplit('.', 1)[-1]
            for k in MIZAN_INPUTS
        }
        self.assertEqual(declared_fields, read)


class A_B_C_D_E_EphemeralRow(TestCase):

    def setUp(self):
        self.profile = _profile('ephemeral')
        self.chain = _build_chain(self.profile)
        self.result = score_and_record(self.profile)
        self.row = prov.current(self.profile, MIZAN_METRIC_KEY)

    def test_a_origin_is_modelled(self):
        self.assertIsNotNone(self.row)
        self.assertEqual(self.row.origin, PROVENANCE_MODELLED)
        self.assertNotEqual(self.row.origin, PROVENANCE_MEASURED)

    def test_b_the_ephemeral_value_is_recorded(self):
        """The whole reason recorded_value exists."""
        self.assertIsNotNone(self.row.recorded_value)
        self.assertEqual(self.row.recorded_value, self.result.final_mizan_score)

    def test_b_the_value_property_reads_the_recorded_one(self):
        self.assertEqual(self.row.value, self.result.final_mizan_score)

    def test_b_no_persisted_field_holds_this_value(self):
        """
        Contrast with company.ecoiq_total, whose provenance stores nothing
        because the number has a home.
        """
        self.assertIsNone(registry.REGISTRY[MIZAN_METRIC_KEY].resolver)
        composite = prov.current(self.profile, 'company.ecoiq_total')
        self.assertIsNone(composite.recorded_value)

    def test_c_methodology_recorded(self):
        self.assertEqual(self.row.methodology, MIZAN_METHOD)

    def test_d_version_recorded_and_not_a_sha(self):
        self.assertEqual(self.row.calculation_version, MIZAN_VERSION)
        self.assertNotRegex(MIZAN_VERSION, r'^[0-9a-f]{7,}$')

    def test_e_exact_inputs_attached(self):
        linked = {r.metric_key for r in prov.lineage(self.row)}

        self.assertEqual(linked, set(MIZAN_INPUTS))

    def test_f_derived_inputs_point_at_derived_rows(self):
        linked = {r.metric_key: r for r in prov.lineage(self.row)}

        self.assertEqual(linked['company.public_benefit'].origin, PROVENANCE_MODELLED)
        self.assertEqual(linked['company.public_benefit'].pk,
                         self.chain['company.public_benefit'].pk)

    def test_g_unrelated_provenance_is_not_attached(self):
        linked = {r.metric_key for r in prov.lineage(self.row)}

        self.assertNotIn('company.ecoiq_total', linked)
        self.assertNotIn('company.harm_penalty', linked)

    def test_the_writer_is_named(self):
        self.assertEqual(self.row.written_by, 'mizan.scoring.score_and_record')

    def test_no_review_is_fabricated(self):
        self.assertEqual(self.row.review_status, 'proposed')
        self.assertIsNone(self.row.reviewed_by)
        self.assertIsNone(self.row.confidence)

    def test_score_company_stays_pure(self):
        """
        It is called from views on every request; recording there would write
        rows on every page view.
        """
        before = CompanyMetricProvenance.objects.count()

        score_company(self.profile)

        self.assertEqual(CompanyMetricProvenance.objects.count(), before)


class H_I_J_ValuesAndAbsence(TestCase):

    def test_h_a_genuine_zero_is_recorded_as_zero(self):
        profile = _profile('zero-out')
        _build_chain(profile)

        with patch('mizan.scoring.score_company') as fake:
            fake.return_value = score_company(profile)
            fake.return_value.final_mizan_score = 0.0
            score_and_record(profile)

        row = prov.current(profile, MIZAN_METRIC_KEY)
        self.assertEqual(row.recorded_value, 0.0)
        self.assertIsNotNone(row.recorded_value, 'a real zero is not absence')

    def test_i_a_genuine_fifty_is_recorded_as_fifty(self):
        profile = _profile('fifty-out')
        _build_chain(profile)

        with patch('mizan.scoring.score_company') as fake:
            fake.return_value = score_company(profile)
            fake.return_value.final_mizan_score = 50.0
            score_and_record(profile)

        self.assertEqual(
            prov.current(profile, MIZAN_METRIC_KEY).recorded_value, 50.0)

    def test_a_fractional_value_is_recorded_exactly(self):
        profile = _profile('fractional')
        _build_chain(profile)
        result = score_and_record(profile)

        self.assertEqual(prov.current(profile, MIZAN_METRIC_KEY).recorded_value,
                         result.final_mizan_score)

    def test_j_an_unavailable_score_creates_no_row(self):
        profile = _profile('no-score')
        for field in ('public_benefit_score', 'jobs_created_score',
                      'regional_development_score', 'national_value_score',
                      'infrastructure_contribution_score', 'controversy_risk_score',
                      'energy_transition_score', 'transparency_anti_corruption_score',
                      'anti_corruption_score', 'audit_quality_score',
                      'procurement_transparency_score', 'transparency_score_detail',
                      'future_readiness_score', 'water_impact_score',
                      'biodiversity_impact_score', 'ethical_alignment_score',
                      'waste_management_score'):
            setattr(profile, field, None)
        profile.pollution_level = None

        result = score_and_record(profile)

        self.assertIsNone(result.final_mizan_score)
        self.assertEqual(result.provenance_status, 'unavailable')
        self.assertIsNone(prov.current(profile, MIZAN_METRIC_KEY))

    def test_j_no_neutral_risk_is_fabricated(self):
        profile = _profile('no-fabrication')
        for field in ('public_benefit_score', 'jobs_created_score',
                      'regional_development_score', 'national_value_score',
                      'infrastructure_contribution_score', 'controversy_risk_score',
                      'energy_transition_score', 'transparency_anti_corruption_score',
                      'anti_corruption_score', 'audit_quality_score',
                      'procurement_transparency_score', 'transparency_score_detail',
                      'future_readiness_score', 'water_impact_score',
                      'biodiversity_impact_score', 'ethical_alignment_score',
                      'waste_management_score'):
            setattr(profile, field, None)
        profile.pollution_level = None

        score_and_record(profile)

        rows = CompanyMetricProvenance.objects.filter(metric_key=MIZAN_METRIC_KEY)
        self.assertEqual(rows.count(), 0)

    def test_a_previously_current_row_is_superseded_when_the_score_goes_away(self):
        profile = _profile('goes-away')
        _build_chain(profile)
        score_and_record(profile)
        original = prov.current(profile, MIZAN_METRIC_KEY)
        self.assertIsNotNone(original)

        status = prov.record_calculated(
            profile, MIZAN_METRIC_KEY, None, MIZAN_INPUTS, writer='test',
            methodology=MIZAN_METHOD, calculation_version=MIZAN_VERSION)

        original.refresh_from_db()
        self.assertEqual(status, 'unavailable')
        self.assertFalse(original.is_current)
        self.assertIsNone(prov.current(profile, MIZAN_METRIC_KEY))

    def test_missing_input_provenance_is_never_guessed(self):
        profile = _profile('no-prov')

        result = score_and_record(profile)

        self.assertIsNotNone(result.final_mizan_score, 'the score is still computed')
        self.assertEqual(result.provenance_status, 'incomplete')
        self.assertEqual(CompanyMetricProvenance.objects.count(), 0)


class K_L_M_N_V_Identity(TestCase):
    """
    K/L/M/N/V — the ephemeral identity rule, which is the substantive
    architectural decision in this PR.
    """

    def setUp(self):
        self.profile = _profile('identity')
        self.chain = _build_chain(self.profile)
        score_and_record(self.profile)

    def _count(self):
        return CompanyMetricProvenance.objects.filter(
            company=self.profile, metric_key=MIZAN_METRIC_KEY).count()

    def test_k_an_identical_recalculation_creates_no_churn(self):
        score_and_record(self.profile)
        score_and_record(self.profile)

        self.assertEqual(self._count(), 1)

    def test_k_the_status_says_unchanged(self):
        self.assertEqual(score_and_record(self.profile).provenance_status,
                         'unchanged')

    def test_l_a_changed_input_creates_a_new_event(self):
        prov.record(self.profile, 'jobs_created_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)

        result = score_and_record(self.profile)

        self.assertEqual(result.provenance_status, 'recorded')
        self.assertEqual(self._count(), 2)

    def test_n_a_version_change_creates_a_new_event(self):
        with patch('mizan.scoring.MIZAN_VERSION', '2'):
            score_and_record(self.profile)

        self.assertEqual(self._count(), 2)

    def test_a_methodology_change_creates_a_new_event(self):
        with patch('mizan.scoring.MIZAN_METHOD', 'ecoiq-mizan-balance-v2'):
            score_and_record(self.profile)

        self.assertEqual(self._count(), 2)

    def test_v_an_unregistered_input_change_still_creates_a_new_event(self):
        """
        THE reason ephemeral identity includes the output.

        is_verified is not a registered metric, so changing it moves no
        provenance row — but it changes the transparency uplift and the
        evidence-confidence dimension, so the score moves. A lineage-only
        identity would call this 'unchanged' and silently collapse two
        genuinely different calculations into one event.
        """
        before = prov.current(self.profile, MIZAN_METRIC_KEY).recorded_value

        self.profile.is_verified = True
        self.profile.save()
        result = score_and_record(self.profile)

        self.assertNotEqual(result.final_mizan_score, before,
                            'is_verified must actually move the score')
        self.assertEqual(result.provenance_status, 'recorded')
        self.assertEqual(self._count(), 2)

    def test_v_a_lineage_only_identity_would_have_missed_it(self):
        """Guards the guard: the lineage really is unchanged in that case."""
        original = prov.current(self.profile, MIZAN_METRIC_KEY)
        original_inputs = {r.pk for r in prov.lineage(original)}

        self.profile.is_verified = True
        self.profile.save()
        score_and_record(self.profile)

        new_row = prov.current(self.profile, MIZAN_METRIC_KEY)
        self.assertEqual({r.pk for r in prov.lineage(new_row)}, original_inputs,
                         'identical lineage — only the output distinguishes them')

    def test_persisted_metrics_deliberately_exclude_the_output(self):
        """
        The asymmetry is intentional. For a persisted metric the comparison is
        impossible — value resolves live and the new number is already written —
        and unnecessary, because the formula is deterministic over input rows.
        """
        composite = prov.current(self.profile, 'company.ecoiq_total')

        self.assertIsNone(composite.recorded_value)
        self.profile.water_impact_score = 12.0
        self.profile.save()
        recalculate_and_save(self.profile)

        self.assertEqual(
            CompanyMetricProvenance.objects.filter(
                company=self.profile, metric_key='company.ecoiq_total').count(), 1)


class M_HistoryIsImmutable(TestCase):

    def setUp(self):
        self.profile = _profile('history')
        self.chain = _build_chain(self.profile)
        score_and_record(self.profile)
        self.first = prov.current(self.profile, MIZAN_METRIC_KEY)
        self.first_value = self.first.recorded_value

    def test_m_the_historical_recorded_value_never_changes(self):
        prov.record(self.profile, 'jobs_created_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)
        score_and_record(self.profile)

        self.first.refresh_from_db()

        self.assertFalse(self.first.is_current)
        self.assertEqual(self.first.recorded_value, self.first_value,
                         'an ephemeral output is the only record of what was '
                         'computed — it must be immutable')

    def test_m_the_old_row_keeps_its_old_inputs(self):
        old_input = self.chain['jobs_created_score']
        prov.record(self.profile, 'jobs_created_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)
        score_and_record(self.profile)

        self.first.refresh_from_db()
        self.assertIn(old_input, prov.lineage(self.first))

    def test_m_the_new_row_has_its_own_value_and_inputs(self):
        prov.record(self.profile, 'jobs_created_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)
        result = score_and_record(self.profile)

        second = prov.current(self.profile, MIZAN_METRIC_KEY)
        self.assertNotEqual(second.pk, self.first.pk)
        self.assertEqual(second.recorded_value, result.final_mizan_score)

    def test_m_both_rows_survive_as_history(self):
        prov.record(self.profile, 'jobs_created_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)
        score_and_record(self.profile)

        rows = prov.history(self.profile, MIZAN_METRIC_KEY)
        self.assertEqual(rows.count(), 2)
        self.assertEqual([r.is_current for r in rows], [True, False])


class O_P_Q_R_S_T_Defensibility(TestCase):

    def test_o_seeded_lineage_is_not_defensible(self):
        profile = _profile('seeded')
        _build_chain(profile, origin=PROVENANCE_SEEDED, writer='seed:test')
        score_and_record(profile)

        row = prov.current(profile, MIZAN_METRIC_KEY)
        self.assertEqual(row.origin, PROVENANCE_MODELLED)
        self.assertIsNotNone(row.recorded_value)
        self.assertFalse(prov.is_derived_publicly_defensible(profile, MIZAN_METRIC_KEY))

    def test_p_legacy_lineage_is_not_defensible(self):
        profile = _profile('legacy')
        _build_chain(profile, origin=PROVENANCE_UNKNOWN, writer='d3b_backfill')
        score_and_record(profile)

        self.assertFalse(prov.is_derived_publicly_defensible(profile, MIZAN_METRIC_KEY))

    def test_q_mixed_lineage_is_not_defensible(self):
        profile = _profile('mixed')
        _build_chain(profile, origin=PROVENANCE_MEASURED)
        prov.record(profile, 'water_impact_score', PROVENANCE_SEEDED)
        score_and_record(profile)

        row = prov.current(profile, MIZAN_METRIC_KEY)
        self.assertTrue(prov.lineage(row), 'lineage is complete')
        self.assertFalse(prov.is_derived_publicly_defensible(profile, MIZAN_METRIC_KEY))

    def test_r_fully_defensible_fixtures_follow_the_current_guard(self):
        profile = _profile('evidenced')
        _build_chain(profile, origin=PROVENANCE_MEASURED)
        score_and_record(profile)

        self.assertTrue(prov.is_derived_publicly_defensible(profile, MIZAN_METRIC_KEY))

    def test_s_the_check_reaches_through_three_layers(self):
        """
        jobs_created_score is a DIRECT Mizan input, so contaminate something
        that is not: waste_management_score feeds no Mizan-declared pillar
        directly... it does. Use a material input that reaches Mizan only via
        company.public_benefit — regional_development_score.
        """
        profile = _profile('deep')
        _build_chain(profile, origin=PROVENANCE_MEASURED)
        prov.record(profile, 'regional_development_score', PROVENANCE_SEEDED)
        recalculate_and_save(profile)
        score_and_record(profile)

        row = prov.current(profile, MIZAN_METRIC_KEY)
        direct = {r.metric_key: r.origin for r in prov.lineage(row)}

        self.assertEqual(direct.get('company.public_benefit'), PROVENANCE_MODELLED)
        self.assertFalse(prov.is_derived_publicly_defensible(profile, MIZAN_METRIC_KEY))

    def test_t_the_cycle_guard_still_resolves_a_shared_ancestor(self):
        """
        Mizan's graph has diamonds: several declared pillars share material
        ancestors. Without the `seen` guard the traversal would revisit them;
        with it a diamond resolves rather than being mistaken for a cycle.
        """
        profile = _profile('diamond')
        _build_chain(profile, origin=PROVENANCE_MEASURED)
        score_and_record(profile)

        self.assertTrue(prov.is_derived_publicly_defensible(profile, MIZAN_METRIC_KEY))


class U_Atomicity(TestCase):

    def test_u_a_provenance_failure_leaves_no_inconsistent_history(self):
        profile = _profile('rollback')
        _build_chain(profile)
        score_and_record(profile)
        original = prov.current(profile, MIZAN_METRIC_KEY)
        original_value = original.recorded_value

        prov.record(profile, 'jobs_created_score', PROVENANCE_SEEDED)
        recalculate_and_save(profile)

        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record_derived',
                       side_effect=RuntimeError('provenance failed')):
                score_and_record(profile)

        original.refresh_from_db()
        self.assertTrue(original.is_current,
                        'the previous row must not be left superseded with no '
                        'replacement')
        self.assertEqual(original.recorded_value, original_value)
        self.assertEqual(
            CompanyMetricProvenance.objects.filter(
                metric_key=MIZAN_METRIC_KEY).count(), 1)

    def test_u_a_failure_partway_leaves_exactly_one_current_row(self):
        from django.db.models import Count

        profile = _profile('one-current')
        _build_chain(profile)
        score_and_record(profile)

        prov.record(profile, 'jobs_created_score', PROVENANCE_SEEDED)
        recalculate_and_save(profile)
        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record_derived',
                       side_effect=RuntimeError('boom')):
                score_and_record(profile)

        duplicates = (CompanyMetricProvenance.objects
                      .filter(is_current=True, metric_key=MIZAN_METRIC_KEY)
                      .values('company').annotate(n=Count('id')).filter(n__gt=1))
        self.assertEqual(duplicates.count(), 0)


class W_PublicSurfaces(TestCase):

    def setUp(self):
        self.profile = _profile('public', ecoiq_total_score=71.4)
        self.profile.company.ecoiq_score = 71.4
        self.profile.company.save()
        _build_chain(self.profile, origin=PROVENANCE_MEASURED)
        score_and_record(self.profile)

    def test_w_the_company_page_is_still_evidence_pending(self):
        from django.test import Client

        from companies.evidence import PENDING_HEADLINE

        self.assertIn(PENDING_HEADLINE,
                      Client().get('/companies/public/').content.decode())

    def test_w_no_mizan_score_leaks_for_an_ineligible_company(self):
        from django.test import Client

        body = Client().get('/companies/public/').content.decode()

        for marker in ('Mizan', 'mizan_score', 'final_mizan_score'):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, body)

    def test_w_the_league_page_is_still_fail_closed(self):
        from django.test import Client

        from companies.evidence import PENDING_HEADLINE

        self.assertIn(PENDING_HEADLINE, Client().get('/league/').content.decode())

    def test_w_api_v2_is_unchanged(self):
        from django.test import Client

        payload = Client().get('/api/v2/companies/public/').json()

        self.assertIsNone(payload['ecoiq_score'])
        self.assertEqual(payload['score_status'], 'INSUFFICIENT_EVIDENCE')
        self.assertNotIn('provenance', payload)

    def test_defensible_lineage_still_does_not_publish(self):
        from companies.evidence import public_score_state

        self.assertTrue(
            prov.is_derived_publicly_defensible(self.profile, MIZAN_METRIC_KEY))
        self.assertFalse(public_score_state(self.profile).available)


class CallerCompatibility(TestCase):

    def test_score_company_signature_is_unchanged(self):
        profile = _profile('unchanged')
        result = score_company(profile)

        self.assertIsNotNone(result.final_mizan_score)
        self.assertFalse(hasattr(result, 'provenance_status'))

    def test_score_and_record_returns_the_same_result_type(self):
        from mizan.scoring import MizanResult

        profile = _profile('same-type')
        self.assertIsInstance(score_and_record(profile), MizanResult)

    def test_it_works_inside_an_existing_transaction(self):
        profile = _profile('inside-atomic')
        _build_chain(profile)

        with transaction.atomic():
            score_and_record(profile)

        self.assertIsNotNone(prov.current(profile, MIZAN_METRIC_KEY))

    def test_views_still_use_the_pure_function(self):
        """
        The write path is explicit and opt-in. If a view started calling
        score_and_record, every page view would write provenance rows.
        """
        from pathlib import Path

        views = (Path(__file__).resolve().parent / 'views.py').read_text()
        self.assertNotIn('score_and_record', views)
