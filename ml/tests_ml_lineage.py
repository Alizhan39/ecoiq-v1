"""
D3C-3f — ML and greenwashing lineage.

Four metrics, and they do NOT share a shape. That is the point of this suite:

  greenwashing.risk        ephemeral, output in identity, refuses to record
                           when the assessment is not assessable
  ml.responsible_finance   ephemeral, same rule, independent of
                           financing.readiness (#252) despite the subject
  ml.score                 PERSISTED, version = feature-set + artefact digest,
                           lineage is a true subset of the model's features
  ml.predicted_12m         PERSISTED, lineage is admittedly partial — the
                           primary path reads ScoreHistory, which has no
                           provenance at all

The tests that matter most here are the ones asserting what the lineage does
NOT cover. A provenance graph that quietly overstates itself is worse than one
that is absent, because it invites reliance.
"""
from unittest.mock import patch

import numpy as np
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from companies import metric_registry as registry
from companies import provenance as prov
from companies.evidence import (
    PROVENANCE_MEASURED, PROVENANCE_MODELLED, PROVENANCE_SEEDED, PROVENANCE_UNKNOWN,
)
from companies.models import CompanyMetricProvenance, CompanyProfile
from companies.scoring import recalculate_and_save
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


from ml.ethics.greenwashing_risk import (
    GREENWASHING_INPUTS, GREENWASHING_METHOD, GREENWASHING_METRIC_KEY,
    GREENWASHING_VERSION, RISK_INSUFFICIENT_EVIDENCE, assess_and_record,
    consumed_inputs, greenwashing_from_profile,
)
from ml.prediction import (
    PREDICTION_INPUTS, PREDICTION_METHOD, PREDICTION_METRIC_KEY, PREDICTION_VERSION,
    _write_prediction, apply_predictions,
)
from ml.responsible_finance import (
    RESPONSIBLE_FINANCE_INPUTS, RESPONSIBLE_FINANCE_METHOD,
    RESPONSIBLE_FINANCE_METRIC_KEY, RESPONSIBLE_FINANCE_VERSION,
    compute_and_record, compute_responsible_finance_score,
)
from ml.scoring_model import (
    ML_SCORE_INPUTS, ML_SCORE_METHOD, ML_SCORE_METRIC_KEY, EcoIQScoringModel,
    ml_score_version,
)


def _profile(slug, **kwargs):
    company = Company.objects.create(name=slug, slug=slug, country='UK',
                                     ecoiq_score=64.0)
    return _populated(company=company, status='public',
                                         pollution_level='low', **kwargs)


def _chain(profile, origin=PROVENANCE_MEASURED, writer='ingestion', limit=None):
    """Material provenance, then the derived pillars."""
    keys = sorted(prov.MATERIAL_METRIC_KEYS)
    for key in (keys if limit is None else keys[:limit]):
        if registry.resolve_value(profile, key) is not None:
            prov.record(profile, key, origin, written_by=writer)
    recalculate_and_save(profile)


# ═══════════════════════════════════════════════════════════════════════════
# Inventory — what exists, asserted so the audit does not rot
# ═══════════════════════════════════════════════════════════════════════════

class Inventory(SimpleTestCase):

    def test_the_four_metrics_are_registered_derived(self):
        for key in (GREENWASHING_METRIC_KEY, RESPONSIBLE_FINANCE_METRIC_KEY,
                    ML_SCORE_METRIC_KEY, PREDICTION_METRIC_KEY):
            with self.subTest(key=key):
                self.assertEqual(registry.REGISTRY[key].kind, registry.DERIVED)

    def test_ephemeral_and_persisted_are_correctly_split(self):
        self.assertTrue(registry.REGISTRY[GREENWASHING_METRIC_KEY].is_ephemeral)
        self.assertTrue(registry.REGISTRY[RESPONSIBLE_FINANCE_METRIC_KEY].is_ephemeral)
        self.assertFalse(registry.REGISTRY[ML_SCORE_METRIC_KEY].is_ephemeral)
        self.assertFalse(registry.REGISTRY[PREDICTION_METRIC_KEY].is_ephemeral)

    def test_every_declared_input_is_a_registered_key(self):
        for name, keys in (('greenwashing', GREENWASHING_INPUTS),
                           ('responsible_finance', RESPONSIBLE_FINANCE_INPUTS),
                           ('ml.score', ML_SCORE_INPUTS),
                           ('ml.predicted_12m', PREDICTION_INPUTS)):
            for key in keys:
                with self.subTest(writer=name, key=key):
                    self.assertIn(key, registry.VALID_KEYS)

    def test_derived_inputs_are_not_flattened(self):
        """A pillar input links to the pillar, never to its own ancestors."""
        self.assertIn('company.transparency_governance', GREENWASHING_INPUTS)
        self.assertIn('company.public_benefit', RESPONSIBLE_FINANCE_INPUTS)
        self.assertIn('company.harm_penalty', ML_SCORE_INPUTS)

    def test_responsible_finance_is_not_financing_readiness(self):
        """
        Different metric, different module, different persistence. #252 covers
        financing.readiness; neither module references the other.
        """
        from pathlib import Path

        self.assertNotEqual(RESPONSIBLE_FINANCE_METRIC_KEY, 'financing.readiness')
        source = Path(__file__).resolve().parent / 'responsible_finance.py'
        self.assertNotIn('financing.matching', source.read_text())

    def test_no_provenance_is_claimed_for_unregistered_ml_outputs(self):
        """
        ml_cluster, ml_cluster_label, anomaly_score and is_anomaly are written
        by ml/clustering.py and ml/anomaly_detection.py but are not registered
        metrics. Inventing keys for them would be fabricating a graph.
        """
        for absent in ('ml.cluster', 'ml.cluster_label', 'ml.anomaly',
                       'ml.anomaly_score'):
            with self.subTest(key=absent):
                self.assertNotIn(absent, registry.VALID_KEYS)


# ═══════════════════════════════════════════════════════════════════════════
# GREENWASHING
# ═══════════════════════════════════════════════════════════════════════════

class GreenwashingLineage(TestCase):

    def setUp(self):
        # The API rate-limits anonymous callers to 20 requests/day through the
        # Django cache, which is NOT reset between tests. A full-suite run
        # exhausts it and later API tests receive 429 with a payload that has no
        # score keys -- a test-isolation problem that reads exactly like a
        # containment regression.
        from django.core.cache import cache
        cache.clear()

        self.profile = _profile('gw')
        _chain(self.profile)
        self.result = assess_and_record(self.profile)
        self.row = prov.current(self.profile, GREENWASHING_METRIC_KEY)

    def test_origin_is_modelled(self):
        self.assertIsNotNone(self.row)
        self.assertEqual(self.row.origin, PROVENANCE_MODELLED)

    def test_the_ephemeral_value_is_recorded(self):
        self.assertEqual(self.row.recorded_value,
                         self.result.greenwashing_risk_score)

    def test_methodology_and_version(self):
        self.assertEqual(self.row.methodology, GREENWASHING_METHOD)
        self.assertEqual(self.row.calculation_version, GREENWASHING_VERSION)

    def test_exact_lineage(self):
        linked = {r.metric_key for r in prov.lineage(self.row)}
        self.assertEqual(linked, set(consumed_inputs(self.profile)))

    def test_the_transparency_pillar_link_is_the_derived_row(self):
        linked = {r.metric_key: r for r in prov.lineage(self.row)}
        self.assertEqual(linked['company.transparency_governance'].origin,
                         PROVENANCE_MODELLED)

    def test_unrelated_metrics_are_not_attached(self):
        linked = {r.metric_key for r in prov.lineage(self.row)}
        for unrelated in ('company.ecoiq_total', 'jobs_created_score',
                          'water_impact_score'):
            with self.subTest(key=unrelated):
                self.assertNotIn(unrelated, linked)

    def test_the_pure_function_records_nothing(self):
        before = CompanyMetricProvenance.objects.count()
        greenwashing_from_profile(self.profile)
        self.assertEqual(CompanyMetricProvenance.objects.count(), before)

    def test_a_verified_company_does_not_declare_the_audit_score(self):
        """
        is_verified short-circuits both assurance channels to flat 90/85, so
        audit_quality_score is never read. Attaching it would assert that an
        audit score supported a number it never touched.
        """
        verified = _profile('gw-verified', is_verified=True)
        _chain(verified)
        assess_and_record(verified)

        linked = {r.metric_key for r in
                  prov.lineage(prov.current(verified, GREENWASHING_METRIC_KEY))}
        self.assertNotIn('audit_quality_score', linked)
        self.assertIn('audit_quality_score', consumed_inputs(self.profile))


class GreenwashingInsufficientEvidence(TestCase):
    """
    STEP 6 — the distinction the whole module exists to protect.
    """

    def _unassessable(self, slug):
        """
        No claims signal and no evidence channel: the claim-to-evidence gap is
        the primary term and cannot be measured.

        The unknowns are set IN MEMORY and deliberately not saved. Every one of
        these columns is NOT NULL with a default of 50.0, so the database
        cannot currently represent "unknown" at all — that is what D4 is for.
        In-memory is how the calculators actually receive unknown today.
        """
        profile = _profile(slug)
        _chain(profile)
        profile.energy_transition_score = None
        profile.future_readiness_score = None
        profile.audit_quality_score = None
        profile.infrastructure_upgrade_score = None
        profile.is_verified = False
        return profile

    def test_insufficient_evidence_is_not_low_risk(self):
        profile = self._unassessable('gw-none')
        result = assess_and_record(profile)

        self.assertIsNone(result.greenwashing_risk_score)
        self.assertEqual(result.risk_level, RISK_INSUFFICIENT_EVIDENCE)
        self.assertNotEqual(result.risk_level, 'low')

    def test_insufficient_evidence_is_not_high_risk(self):
        result = assess_and_record(self._unassessable('gw-none-2'))
        for adverse in ('high', 'severe', 'medium'):
            self.assertNotEqual(result.risk_level, adverse)

    def test_no_provenance_row_is_created_for_an_unassessable_profile(self):
        profile = self._unassessable('gw-none-3')
        assess_and_record(profile)

        self.assertIsNone(prov.current(profile, GREENWASHING_METRIC_KEY))
        self.assertEqual(
            CompanyMetricProvenance.objects.filter(
                company=profile, metric_key=GREENWASHING_METRIC_KEY).count(), 0)

    def test_a_previous_row_stops_claiming_current_state(self):
        profile = _profile('gw-was-assessable')
        _chain(profile)
        assess_and_record(profile)
        original = prov.current(profile, GREENWASHING_METRIC_KEY)
        self.assertIsNotNone(original)

        profile.energy_transition_score = None
        profile.future_readiness_score = None
        profile.audit_quality_score = None
        profile.infrastructure_upgrade_score = None
        profile.is_verified = False
        result = assess_and_record(profile)

        original.refresh_from_db()
        self.assertEqual(result.provenance_status, 'unavailable')
        self.assertFalse(original.is_current)

    def test_the_narrative_refuses_to_read_as_favourable(self):
        result = assess_and_record(self._unassessable('gw-narrative'))
        text = (result.explanation + ' ' + result.investor_warning).lower()

        self.assertIn('not', text)
        self.assertNotIn('low risk', text)

    def test_narrative_fields_are_not_stored_as_metrics(self):
        """STEP 8 — flags and warnings are not independent derived outputs."""
        profile = _profile('gw-no-narrative-metric')
        _chain(profile)
        assess_and_record(profile)

        keys = set(CompanyMetricProvenance.objects.filter(company=profile)
                   .values_list('metric_key', flat=True))
        for invented in ('greenwashing.flags', 'greenwashing.warning',
                         'greenwashing.explanation', 'greenwashing.risk_level'):
            with self.subTest(key=invented):
                self.assertNotIn(invented, keys)


class GreenwashingValues(TestCase):
    """STEP 7 — zero is a finding, not an absence."""

    def _record_with_score(self, slug, score):
        profile = _profile(slug)
        _chain(profile)
        real = greenwashing_from_profile(profile)
        real.greenwashing_risk_score = score
        with patch('ml.ethics.greenwashing_risk.greenwashing_from_profile',
                   return_value=real):
            assess_and_record(profile)
        return prov.current(profile, GREENWASHING_METRIC_KEY)

    def test_zero_is_recorded_as_zero(self):
        row = self._record_with_score('gw-zero', 0.0)
        self.assertIsNotNone(row)
        self.assertEqual(row.recorded_value, 0.0)

    def test_zero_is_not_treated_as_missing(self):
        self.assertIsNotNone(self._record_with_score('gw-zero-2', 0.0))

    def test_fifty_is_recorded_as_fifty(self):
        self.assertEqual(self._record_with_score('gw-fifty', 50.0).recorded_value,
                         50.0)

    def test_none_creates_no_numerical_row(self):
        profile = _profile('gw-null')
        _chain(profile)
        real = greenwashing_from_profile(profile)
        real.greenwashing_risk_score = None
        with patch('ml.ethics.greenwashing_risk.greenwashing_from_profile',
                   return_value=real):
            assess_and_record(profile)

        self.assertIsNone(prov.current(profile, GREENWASHING_METRIC_KEY))


class GreenwashingHistory(TestCase):

    def setUp(self):
        self.profile = _profile('gw-history')
        _chain(self.profile)
        assess_and_record(self.profile)
        self.first = prov.current(self.profile, GREENWASHING_METRIC_KEY)
        self.first_value = self.first.recorded_value

    def _count(self):
        return CompanyMetricProvenance.objects.filter(
            company=self.profile, metric_key=GREENWASHING_METRIC_KEY).count()

    def test_identical_recalculation_does_not_churn(self):
        assess_and_record(self.profile)
        result = assess_and_record(self.profile)

        self.assertEqual(result.provenance_status, 'unchanged')
        self.assertEqual(self._count(), 1)

    def test_changed_feature_provenance_creates_a_new_event(self):
        prov.record(self.profile, 'energy_transition_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)

        self.assertEqual(assess_and_record(self.profile).provenance_status,
                         'recorded')
        self.assertEqual(self._count(), 2)

    def test_history_is_pinned_to_the_old_feature_rows(self):
        old = prov.current(self.profile, 'energy_transition_score')
        prov.record(self.profile, 'energy_transition_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)
        assess_and_record(self.profile)

        self.first.refresh_from_db()
        self.assertFalse(self.first.is_current)
        self.assertEqual(self.first.recorded_value, self.first_value)
        self.assertIn(old, prov.lineage(self.first))

    def test_a_version_change_creates_a_new_event(self):
        with patch('ml.ethics.greenwashing_risk.GREENWASHING_VERSION', '2'):
            assess_and_record(self.profile)
        self.assertEqual(self._count(), 2)

    def test_an_unrepresented_context_change_still_creates_an_event(self):
        """pollution_level moves the fossil-fuel proxy but has no row."""
        before = self.first.recorded_value
        self.profile.pollution_level = 'severe'
        self.profile.save()

        result = assess_and_record(self.profile)

        self.assertNotEqual(result.greenwashing_risk_score, before)
        self.assertEqual(result.provenance_status, 'recorded')


class GreenwashingDefensibility(TestCase):

    def _assess(self, slug, origin, writer, contaminate=None):
        profile = _profile(slug)
        _chain(profile, origin=origin, writer=writer)
        if contaminate:
            prov.record(profile, contaminate, PROVENANCE_SEEDED)
            recalculate_and_save(profile)
        assess_and_record(profile)
        return profile

    def test_fully_evidenced_is_defensible(self):
        profile = self._assess('gw-def', PROVENANCE_MEASURED, 'ingestion')
        self.assertTrue(
            prov.is_derived_publicly_defensible(profile, GREENWASHING_METRIC_KEY))

    def test_seeded_lineage_fails(self):
        profile = self._assess('gw-seeded', PROVENANCE_SEEDED, 'seed:test')
        self.assertFalse(
            prov.is_derived_publicly_defensible(profile, GREENWASHING_METRIC_KEY))

    def test_legacy_lineage_fails(self):
        profile = self._assess('gw-legacy', PROVENANCE_UNKNOWN, 'd3b_backfill')
        self.assertFalse(
            prov.is_derived_publicly_defensible(profile, GREENWASHING_METRIC_KEY))

    def test_mixed_lineage_fails(self):
        profile = self._assess('gw-mixed', PROVENANCE_MEASURED, 'ingestion',
                               contaminate='energy_transition_score')
        self.assertFalse(
            prov.is_derived_publicly_defensible(profile, GREENWASHING_METRIC_KEY))

    def test_contamination_below_the_pillar_still_fails(self):
        """
        STEP 16 — no laundering through the model layer.
        regional_development_score reaches greenwashing only via the
        transparency/public-benefit pillars, three layers down.
        """
        profile = self._assess('gw-deep', PROVENANCE_MEASURED, 'ingestion',
                               contaminate='procurement_transparency_score')
        self.assertFalse(
            prov.is_derived_publicly_defensible(profile, GREENWASHING_METRIC_KEY))


class GreenwashingAtomicity(TestCase):

    def test_a_provenance_failure_leaves_no_inconsistent_history(self):
        profile = _profile('gw-atomic')
        _chain(profile)
        assess_and_record(profile)
        original = prov.current(profile, GREENWASHING_METRIC_KEY)
        original_value = original.recorded_value

        prov.record(profile, 'energy_transition_score', PROVENANCE_SEEDED)
        recalculate_and_save(profile)

        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record_derived',
                       side_effect=RuntimeError('injected')):
                assess_and_record(profile)

        original.refresh_from_db()
        self.assertTrue(original.is_current)
        self.assertEqual(original.recorded_value, original_value)
        self.assertEqual(
            CompanyMetricProvenance.objects.filter(
                company=profile, metric_key=GREENWASHING_METRIC_KEY).count(), 1)

    def test_the_guard_actually_fires(self):
        """
        Guards the guard. A changed material VALUE is not a changed lineage, so
        record_derived would never be called and the test above would pass
        vacuously. It is the provenance row that must change.
        """
        profile = _profile('gw-guard')
        _chain(profile)
        assess_and_record(profile)
        prov.record(profile, 'energy_transition_score', PROVENANCE_SEEDED)
        recalculate_and_save(profile)

        with patch('companies.provenance.record_derived') as spy:
            spy.side_effect = RuntimeError('injected')
            with self.assertRaises(RuntimeError):
                assess_and_record(profile)

        self.assertTrue(spy.called, 'the injected failure must be reachable')


# ═══════════════════════════════════════════════════════════════════════════
# RESPONSIBLE FINANCE
# ═══════════════════════════════════════════════════════════════════════════

class ResponsibleFinanceLineage(TestCase):

    def setUp(self):
        self.profile = _profile('rf')
        _chain(self.profile)
        self.result = compute_and_record(self.profile)
        self.row = prov.current(self.profile, RESPONSIBLE_FINANCE_METRIC_KEY)

    def test_origin_and_identity(self):
        self.assertEqual(self.row.origin, PROVENANCE_MODELLED)
        self.assertEqual(self.row.methodology, RESPONSIBLE_FINANCE_METHOD)
        self.assertEqual(self.row.calculation_version, RESPONSIBLE_FINANCE_VERSION)

    def test_ephemeral_value_recorded(self):
        self.assertEqual(self.row.recorded_value,
                         self.result['responsible_finance_score'])

    def test_lineage_is_the_declared_inputs(self):
        linked = {r.metric_key for r in prov.lineage(self.row)}
        self.assertEqual(linked, set(RESPONSIBLE_FINANCE_INPUTS))

    def test_the_pure_function_records_nothing(self):
        before = CompanyMetricProvenance.objects.count()
        compute_responsible_finance_score(self.profile)
        self.assertEqual(CompanyMetricProvenance.objects.count(), before)

    def test_no_churn_then_a_new_event_on_changed_lineage(self):
        self.assertEqual(compute_and_record(self.profile)['provenance_status'],
                         'unchanged')

        prov.record(self.profile, 'anti_corruption_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)
        self.assertEqual(compute_and_record(self.profile)['provenance_status'],
                         'recorded')

    def test_seeded_lineage_is_not_defensible(self):
        seeded = _profile('rf-seeded')
        _chain(seeded, origin=PROVENANCE_SEEDED, writer='seed:test')
        compute_and_record(seeded)

        self.assertFalse(prov.is_derived_publicly_defensible(
            seeded, RESPONSIBLE_FINANCE_METRIC_KEY))

    def test_fully_evidenced_is_defensible(self):
        self.assertTrue(prov.is_derived_publicly_defensible(
            self.profile, RESPONSIBLE_FINANCE_METRIC_KEY))

    def test_atomicity(self):
        original = prov.current(self.profile, RESPONSIBLE_FINANCE_METRIC_KEY)
        prov.record(self.profile, 'anti_corruption_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)

        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record_derived',
                       side_effect=RuntimeError('injected')):
                compute_and_record(self.profile)

        original.refresh_from_db()
        self.assertTrue(original.is_current)


class ResponsibleFinanceMissingEvidence(TestCase):

    def _bare(self, slug):
        # In memory only — the columns are NOT NULL with a 50.0 default, so
        # unknown has no database representation before D4.
        profile = _profile(slug)
        for field in ('public_benefit_score', 'environmental_responsibility_score',
                      'modernization_score', 'transparency_anti_corruption_score',
                      'anti_corruption_score', 'ethical_alignment_score'):
            setattr(profile, field, None)
        return profile

    def test_no_pillars_means_no_score_and_no_row(self):
        profile = self._bare('rf-bare')
        result = compute_and_record(profile)

        self.assertIsNone(result['responsible_finance_score'])
        self.assertIsNone(result['ethical_grade'])
        self.assertEqual(result['provenance_status'], 'unavailable')
        self.assertIsNone(prov.current(profile, RESPONSIBLE_FINANCE_METRIC_KEY))

    def test_the_refusal_is_not_an_f_grade(self):
        result = compute_and_record(self._bare('rf-not-f'))
        self.assertNotEqual(result['ethical_grade'], 'F')
        self.assertNotEqual(result['responsible_finance_score'], 0)


class ResponsibleFinancePollutionResidual(TestCase):
    """
    STEP 20 — D2 residual found in this PR.

    `getattr(profile, 'pollution_level', 'medium') or 'medium'` docked 5 points
    from every unclassified company: an adverse finding invented from an
    absence. greenwashing_from_profile had already fixed the identical pattern.
    """

    def _score(self, level):
        """
        `level` of '' is the realistic unclassified case: pollution_level is
        NOT NULL with a default of 'medium', so an empty string is how an
        unclassified company is actually stored today. None is the post-D4
        shape and is exercised in memory.
        """
        profile = _profile(f'rf-poll-{level or "none"}')
        profile.pollution_level = level
        if level:
            profile.save()
        return compute_responsible_finance_score(profile)

    def test_an_empty_pollution_level_applies_no_penalty(self):
        """The case that actually exists in the database today."""
        self.assertEqual(self._score('')['pollution_penalty'], 0)

    def test_an_unknown_pollution_level_applies_no_penalty(self):
        self.assertEqual(self._score(None)['pollution_penalty'], 0)

    def test_unknown_is_not_silently_treated_as_medium(self):
        unknown = self._score(None)
        medium = self._score('medium')

        self.assertEqual(medium['pollution_penalty'], -5)
        self.assertNotEqual(unknown['pollution_penalty'],
                            medium['pollution_penalty'])
        self.assertGreater(unknown['responsible_finance_score'],
                           medium['responsible_finance_score'])

    def test_a_known_level_still_penalises(self):
        self.assertEqual(self._score('severe')['pollution_penalty'], -30)
        self.assertEqual(self._score('low')['pollution_penalty'], 0)

    def test_the_unknown_is_surfaced_not_swallowed(self):
        factors = ' '.join(self._score(None)['summary_factors']).lower()
        self.assertIn('not classified', factors)

    def test_unknown_is_distinguishable_from_a_measured_low(self):
        """Both score 0 penalty, so the narrative is the only signal."""
        unknown = ' '.join(self._score(None)['summary_factors']).lower()
        low = ' '.join(self._score('low')['summary_factors']).lower()
        self.assertNotEqual(unknown, low)


# ═══════════════════════════════════════════════════════════════════════════
# ML SCORE — persisted
# ═══════════════════════════════════════════════════════════════════════════

class MlScoreVersioning(SimpleTestCase):

    def test_the_version_combines_feature_set_and_artefact_digest(self):
        version = ml_score_version()
        self.assertIsNotNone(version, 'committed artefacts should be readable')
        self.assertRegex(version, r'^fs\d+\+[0-9a-f]{12}$')

    def test_it_is_not_a_git_sha(self):
        import subprocess

        version = ml_score_version()
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True,
                              text=True).stdout.strip()
        self.assertNotIn(head[:12], version)

    def test_a_changed_artefact_changes_the_version(self):
        from ml.model_identity import artefact_digest
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a', Path(tmp) / 'b'
            a.write_bytes(b'model-one')
            b.write_bytes(b'model-two')
            self.assertNotEqual(artefact_digest(a), artefact_digest(b))

    def test_an_unreadable_artefact_yields_no_version(self):
        from ml.model_identity import model_version
        from pathlib import Path

        self.assertIsNone(model_version(Path('/nonexistent/model.joblib')))

    def test_the_feature_set_version_is_part_of_the_identity(self):
        from ml.model_identity import model_version
        from ml.scoring_model import MODEL_PATH, SCALER_PATH

        self.assertNotEqual(model_version(MODEL_PATH, SCALER_PATH, feature_set='1'),
                            model_version(MODEL_PATH, SCALER_PATH, feature_set='2'))


class MlScorePersistedLineage(TestCase):

    def setUp(self):
        self.profile = _profile('mls')
        _chain(self.profile)
        self.model = EcoIQScoringModel()

    def _write(self, score=72.5, confidence=0.8):
        self.model._write_score(self.profile.company.pk, score, confidence,
                                timezone.now(), self.profile.company)
        self.profile.company.refresh_from_db()
        return prov.current(self.profile, ML_SCORE_METRIC_KEY)

    def test_the_value_is_persisted(self):
        self._write(score=72.5)
        self.assertEqual(self.profile.company.ml_score, 72.5)

    def test_a_persisted_metric_stores_no_recorded_value(self):
        row = self._write()
        self.assertIsNotNone(row)
        self.assertIsNone(row.recorded_value,
                          'the model field is the value source, per #248')

    def test_origin_methodology_and_model_version(self):
        row = self._write()
        self.assertEqual(row.origin, PROVENANCE_MODELLED)
        self.assertEqual(row.methodology, ML_SCORE_METHOD)
        self.assertEqual(row.calculation_version, ml_score_version())

    def test_the_prediction_is_modelled_not_measured(self):
        row = self._write()
        self.assertNotEqual(row.origin, PROVENANCE_MEASURED)
        self.assertNotIn(row.origin, ('MEASURED', 'INFERRED'))

    def test_feature_lineage_is_exact(self):
        row = self._write()
        linked = {r.metric_key for r in prov.lineage(row)}
        self.assertEqual(linked, set(ML_SCORE_INPUTS))

    def test_the_lineage_is_a_true_subset_of_the_model_features(self):
        """
        Asserted rather than assumed. 15 of 29 features have provenance; the
        rest are legacy Company score_* fields and runtime context.
        """
        from ml.features import get_feature_names

        self.assertEqual(len(ML_SCORE_INPUTS), 15)
        self.assertLess(len(ML_SCORE_INPUTS), len(get_feature_names()))

    def test_no_churn_for_the_same_model_and_inputs(self):
        self._write()
        self._write()
        self.assertEqual(
            CompanyMetricProvenance.objects.filter(
                company=self.profile, metric_key=ML_SCORE_METRIC_KEY).count(), 1)

    def test_a_changed_model_version_creates_a_new_event(self):
        """
        STEP 15 — the same number from a new model is NOT the same event.
        The score is deliberately held constant here.
        """
        self._write(score=72.5)
        with patch('ml.scoring_model.ml_score_version', return_value='fs9+deadbeef0000'):
            self._write(score=72.5)

        rows = CompanyMetricProvenance.objects.filter(
            company=self.profile, metric_key=ML_SCORE_METRIC_KEY)
        self.assertEqual(rows.count(), 2)
        self.assertEqual({r.calculation_version for r in rows},
                         {ml_score_version(), 'fs9+deadbeef0000'})

    def test_changed_feature_provenance_creates_a_new_event(self):
        self._write()
        prov.record(self.profile, 'waste_management_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)
        self._write()

        self.assertEqual(
            CompanyMetricProvenance.objects.filter(
                company=self.profile, metric_key=ML_SCORE_METRIC_KEY).count(), 2)

    def test_no_provenance_is_recorded_without_a_readable_artefact(self):
        with patch('ml.scoring_model.ml_score_version', return_value=None):
            self.model._write_score(self.profile.company.pk, 60.0, 0.5,
                                    timezone.now(), self.profile.company)

        self.profile.company.refresh_from_db()
        self.assertEqual(self.profile.company.ml_score, 60.0)
        self.assertIsNone(prov.current(self.profile, ML_SCORE_METRIC_KEY),
                          'a version naming no model is worse than no row')

    def test_seeded_features_are_not_defensible(self):
        seeded = _profile('mls-seeded')
        _chain(seeded, origin=PROVENANCE_SEEDED, writer='seed:test')
        EcoIQScoringModel()._write_score(seeded.company.pk, 70.0, 0.9,
                                         timezone.now(), seeded.company)

        self.assertFalse(
            prov.is_derived_publicly_defensible(seeded, ML_SCORE_METRIC_KEY))

    def test_transitive_contamination_fails(self):
        deep = _profile('mls-deep')
        _chain(deep, origin=PROVENANCE_MEASURED)
        prov.record(deep, 'regional_development_score', PROVENANCE_SEEDED)
        recalculate_and_save(deep)
        EcoIQScoringModel()._write_score(deep.company.pk, 70.0, 0.9,
                                         timezone.now(), deep.company)

        self.assertFalse(
            prov.is_derived_publicly_defensible(deep, ML_SCORE_METRIC_KEY))

    def test_a_provenance_failure_rolls_back_the_persisted_score(self):
        """STEP 14 — the invariant D3C exists to protect."""
        self._write(score=72.5)
        prov.record(self.profile, 'waste_management_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)

        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record_derived',
                       side_effect=RuntimeError('injected')):
                self.model._write_score(self.profile.company.pk, 88.8, 0.4,
                                        timezone.now(), self.profile.company)

        self.profile.company.refresh_from_db()
        self.assertEqual(self.profile.company.ml_score, 72.5,
                         'the value must roll back with its provenance')

    def test_no_orphaned_current_provenance(self):
        from django.db.models import Count

        self._write()
        prov.record(self.profile, 'waste_management_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)
        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record_derived',
                       side_effect=RuntimeError('injected')):
                self._write(score=90.0)

        dupes = (CompanyMetricProvenance.objects
                 .filter(is_current=True, metric_key=ML_SCORE_METRIC_KEY)
                 .values('company').annotate(n=Count('id')).filter(n__gt=1))
        self.assertEqual(dupes.count(), 0)

    def test_a_company_without_a_profile_still_gets_its_value(self):
        bare = Company.objects.create(name='bare', slug='bare-co', country='UK',
                                      ecoiq_score=50.0)
        self.model._write_score(bare.pk, 55.0, 0.5, timezone.now(), bare)

        bare.refresh_from_db()
        self.assertEqual(bare.ml_score, 55.0)


class MlScoreMaterialGate(TestCase):
    """
    STEP 20 — D2 residual found in this PR.

    predict_company() refuses when material features are unknown (#244), but
    the batch _apply_scores path did not, so the same company could have a
    persisted ml_score the API would decline to produce — and the persisted one
    wins on every page that reads the field.
    """

    def _model_with_fake_estimator(self, prediction=70.0):
        model = EcoIQScoringModel()
        model.model = type('Fake', (), {
            'predict': staticmethod(lambda X: np.full(len(X), prediction))
        })()
        return model

    def test_a_company_with_unknown_material_features_is_skipped(self):
        profile = _profile('gate-missing')
        _chain(profile)
        profile.public_benefit_score = None      # in memory: column is NOT NULL
        profile.company.profile = profile        # so the gate sees this instance

        model = self._model_with_fake_estimator()
        model._apply_scores([profile.company], [profile.company.pk],
                            np.zeros((1, 29)))

        profile.company.refresh_from_db()
        self.assertIsNone(profile.company.ml_score)
        self.assertIsNone(prov.current(profile, ML_SCORE_METRIC_KEY))

    def test_a_fully_known_company_is_written(self):
        profile = _profile('gate-known')
        _chain(profile)

        model = self._model_with_fake_estimator(prediction=70.0)
        model._apply_scores([profile.company], [profile.company.pk],
                            np.zeros((1, 29)))

        profile.company.refresh_from_db()
        self.assertEqual(profile.company.ml_score, 70.0)
        self.assertIsNotNone(prov.current(profile, ML_SCORE_METRIC_KEY))

    def test_a_skipped_company_is_not_erased(self):
        """The gate declines to write; it does not null an existing score."""
        profile = _profile('gate-preserve')
        _chain(profile)
        profile.company.ml_score = 61.0
        profile.company.save()
        profile.public_benefit_score = None
        profile.company.profile = profile

        model = self._model_with_fake_estimator()
        model._apply_scores([profile.company], [profile.company.pk],
                            np.zeros((1, 29)))

        profile.company.refresh_from_db()
        self.assertEqual(profile.company.ml_score, 61.0)

    def test_the_two_paths_now_agree(self):
        from ml.features import missing_material_features

        profile = _profile('gate-agree')
        profile.public_benefit_score = None
        profile.company.profile = profile

        self.assertTrue(missing_material_features(profile.company),
                        'predict_company would refuse this company')
        model = self._model_with_fake_estimator()
        model._apply_scores([profile.company], [profile.company.pk],
                            np.zeros((1, 29)))
        profile.company.refresh_from_db()
        self.assertIsNone(profile.company.ml_score,
                          'so the batch path must refuse it too')


# ═══════════════════════════════════════════════════════════════════════════
# ML PREDICTED 12M — persisted, lineage admittedly partial
# ═══════════════════════════════════════════════════════════════════════════

class PredictionLineage(TestCase):

    def setUp(self):
        self.profile = _profile('pred')
        _chain(self.profile)

    def test_the_value_and_provenance_are_both_written(self):
        status = _write_prediction(self.profile.company, 68.0, timezone.now())
        self.profile.company.refresh_from_db()

        self.assertEqual(status, 'recorded')
        self.assertEqual(self.profile.company.ml_predicted_score_12m, 68.0)

    def test_a_forecast_is_modelled(self):
        _write_prediction(self.profile.company, 68.0, timezone.now())
        row = prov.current(self.profile, PREDICTION_METRIC_KEY)

        self.assertEqual(row.origin, PROVENANCE_MODELLED)
        self.assertEqual(row.methodology, PREDICTION_METHOD)
        self.assertEqual(row.calculation_version, PREDICTION_VERSION)

    def test_it_stores_no_recorded_value(self):
        _write_prediction(self.profile.company, 68.0, timezone.now())
        self.assertIsNone(
            prov.current(self.profile, PREDICTION_METRIC_KEY).recorded_value)

    def test_it_does_not_inherit_the_current_score_provenance(self):
        """
        STEP 10. company.ecoiq_total may be perfectly evidenced; a projection
        about next year is still a model output.
        """
        _write_prediction(self.profile.company, 68.0, timezone.now())
        forecast = prov.current(self.profile, PREDICTION_METRIC_KEY)
        composite = prov.current(self.profile, 'company.ecoiq_total')

        self.assertNotEqual(forecast.pk, composite.pk)
        self.assertEqual(forecast.origin, PROVENANCE_MODELLED)
        self.assertIn(composite, prov.lineage(forecast))

    def test_the_declared_lineage_is_documented_as_partial(self):
        """
        The primary OLS path reads ScoreHistory, not company.ecoiq_total. The
        single declared input is the closest provenance-bearing relative, and
        the module says so rather than implying completeness.
        """
        from pathlib import Path

        self.assertEqual(len(PREDICTION_INPUTS), 1)
        source = (Path(__file__).resolve().parent / 'prediction.py').read_text()
        self.assertIn('understates both paths', source)

    def test_no_churn_then_a_new_event_on_changed_lineage(self):
        _write_prediction(self.profile.company, 68.0, timezone.now())
        self.assertEqual(
            _write_prediction(self.profile.company, 68.0, timezone.now()),
            'unchanged')

        prov.record(self.profile, 'jobs_created_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)
        self.assertEqual(
            _write_prediction(self.profile.company, 68.0, timezone.now()),
            'recorded')

    def test_seeded_lineage_is_not_defensible(self):
        seeded = _profile('pred-seeded')
        _chain(seeded, origin=PROVENANCE_SEEDED, writer='seed:test')
        _write_prediction(seeded.company, 68.0, timezone.now())

        self.assertFalse(
            prov.is_derived_publicly_defensible(seeded, PREDICTION_METRIC_KEY))

    def test_a_provenance_failure_rolls_back_the_forecast(self):
        _write_prediction(self.profile.company, 68.0, timezone.now())
        prov.record(self.profile, 'jobs_created_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)

        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record_derived',
                       side_effect=RuntimeError('injected')):
                _write_prediction(self.profile.company, 99.9, timezone.now())

        self.profile.company.refresh_from_db()
        self.assertEqual(self.profile.company.ml_predicted_score_12m, 68.0)

    def test_a_company_without_a_score_gets_no_forecast_and_no_row(self):
        """STEP 5 — a forecast is a projection FROM something."""
        blank = Company.objects.create(name='blank', slug='blank-co',
                                       country='UK')
        _populated(company=blank, status='public')
        # league.Company.ecoiq_score is NOT NULL with a default of 0.0, so
        # "no score" and "a score of exactly zero" are indistinguishable in the
        # database today. Unknown is set in memory, which is what predict_12m
        # actually receives from a caller that knows the score is absent.
        blank.ecoiq_score = None

        apply_predictions(companies=[blank])

        blank.refresh_from_db()
        self.assertIsNone(blank.ml_predicted_score_12m)
        self.assertEqual(
            CompanyMetricProvenance.objects.filter(
                metric_key=PREDICTION_METRIC_KEY).count(), 0)

    def test_apply_predictions_records_through_the_writer(self):
        result = apply_predictions(companies=[self.profile.company])

        self.assertEqual(result['updated'], 1)
        self.assertIsNotNone(prov.current(self.profile, PREDICTION_METRIC_KEY))


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC CONTAINMENT
# ═══════════════════════════════════════════════════════════════════════════

class PublicContainment(TestCase):


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

        self.profile = _profile('ml-public', ecoiq_total_score=71.4)
        _chain(self.profile, origin=PROVENANCE_MEASURED, limit=self.PARTIAL_EVIDENCE_LIMIT)
        assess_and_record(self.profile)
        compute_and_record(self.profile)
        EcoIQScoringModel()._write_score(self.profile.company.pk, 73.0, 0.9,
                                         timezone.now(), self.profile.company)
        _write_prediction(self.profile.company, 75.0, timezone.now())

    def _page(self):
        from django.test import Client
        return Client().get('/companies/ml-public/').content.decode()

    def test_the_company_page_is_still_evidence_pending(self):
        from companies.evidence import PENDING_HEADLINE
        self.assertIn(PENDING_HEADLINE, self._page())

    def test_no_ml_or_greenwashing_value_leaks_to_the_page(self):
        body = self._page()
        for marker in ('greenwashing', 'ml_score', 'ml_predicted',
                       'responsible_finance', '73.0', '75.0'):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, body)

    def test_api_v2_remains_fail_closed(self):
        from django.test import Client

        payload = Client().get('/api/v2/companies/ml-public/').json()

        self.assertIsNone(payload['ecoiq_score'])
        self.assertEqual(payload['score_status'], 'INSUFFICIENT_EVIDENCE')
        for leaked in ('ml_score', 'greenwashing_risk', 'ml_predicted_score_12m',
                       'responsible_finance_score', 'provenance'):
            with self.subTest(key=leaked):
                self.assertNotIn(leaked, payload)

    def test_the_league_page_remains_fail_closed(self):
        from django.test import Client
        from companies.evidence import PENDING_HEADLINE

        self.assertIn(PENDING_HEADLINE,
                      Client().get('/league/').content.decode())

    def test_partial_evidence_publishes_nothing(self):
        """
        With four of sixteen material inputs evidenced, BOTH gates reject.

        Coverage is under 100%, so the publication gate refuses — and the
        derived lineage is ABSENT rather than weak, because record_calculated
        declines to write a row when some consumed inputs have no provenance:
        a lineage listing only the evidenced ones would understate what the
        number rests on.

        Before D5 this passed for a much weaker reason — coverage was inert, so
        nothing could ever be published.
        """
        from companies.evidence import coverage_for, public_score_state

        report = coverage_for(self.profile)

        self.assertGreater(report.coverage_percent, 0)
        self.assertLess(report.coverage_percent, 100)
        self.assertFalse(
            prov.is_derived_publicly_defensible(self.profile, GREENWASHING_METRIC_KEY))
        self.assertFalse(public_score_state(self.profile).available)

    def test_page_metadata_does_not_leak(self):
        import re

        metas = re.findall(r'<meta[^>]*>', self._page())
        joined = ' '.join(metas).lower()
        for marker in ('greenwashing', 'ml_score', '73.0', '75.0'):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, joined)


class PersistedDefensibilityIsInstanceSensitive(TestCase):
    """
    A sharp edge found while measuring STEP 17, worth pinning down.

    `_row_is_defensible` rejects a row whose value resolves to None, on the
    reasoning that a row over a NULL field is a contradiction. For ml.score and
    ml.predicted_12m the value resolves LIVE through `profile.company`, and
    both writers persist with a queryset `.update()` — which leaves any
    in-memory Company instance stale.

    So the advisory guard answers False for a metric that is in fact fully
    defensible, purely because the caller is holding a stale object. Nothing on
    a public path calls it, so no user-visible behaviour depends on this today.

    Recorded rather than "fixed": refreshing inside the guard would hide a
    caller bug, and relaxing the None check would weaken a rule that is correct
    for every other metric.
    """

    def setUp(self):
        self.profile = _profile('stale')
        _chain(self.profile)
        EcoIQScoringModel()._write_score(self.profile.company.pk, 73.0, 0.9,
                                         timezone.now(), self.profile.company)

    def test_a_stale_instance_reports_not_defensible(self):
        self.assertIsNone(self.profile.company.ml_score)
        self.assertFalse(prov.is_derived_publicly_defensible(
            self.profile, ML_SCORE_METRIC_KEY))

    def test_a_refreshed_instance_reports_defensible(self):
        self.profile.company.refresh_from_db()

        self.assertEqual(float(self.profile.company.ml_score), 73.0)
        self.assertTrue(prov.is_derived_publicly_defensible(
            self.profile, ML_SCORE_METRIC_KEY))

    def test_the_lineage_itself_was_never_in_doubt(self):
        """The rows are sound either way — only the live value resolution moved."""
        row = prov.current(self.profile, ML_SCORE_METRIC_KEY)

        self.assertEqual(len(prov.lineage(row)), len(ML_SCORE_INPUTS))
        for item in prov.lineage(row):
            with self.subTest(key=item.metric_key):
                self.assertTrue(prov._row_is_defensible(item, set()))

    def test_ephemeral_metrics_are_immune(self):
        """
        greenwashing.risk resolves from recorded_value on the row itself, so no
        instance anywhere can be stale enough to change the answer.
        """
        assess_and_record(self.profile)
        self.assertTrue(prov.is_derived_publicly_defensible(
            self.profile, GREENWASHING_METRIC_KEY))
