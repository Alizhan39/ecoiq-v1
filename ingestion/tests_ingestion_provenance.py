"""
D3C-4 — trusted ingestion provenance.

The decision under test is a semantic one, not a mechanical one:

    a real source does NOT make a 0-100 EcoIQ score MEASURED.

The pipeline reads filings and news, an LLM turns them into five pillar
signals, and those five are fanned across sixteen material fields. The source
fact may be measured; the number EcoIQ stores is an assessment derived from it.
So every material score ingestion writes is INFERRED, and the tests here exist
mainly to stop that from quietly becoming MEASURED later.
"""
from unittest.mock import patch

from django.db import transaction
from django.test import SimpleTestCase, TestCase

from companies import metric_registry as registry
from companies import provenance as prov
from companies.evidence import (
    PROVENANCE_ESTIMATED, PROVENANCE_INFERRED, PROVENANCE_MEASURED,
    PROVENANCE_MODELLED, PROVENANCE_SEEDED,
)
from companies.models import CompanyMetricProvenance, CompanyProfile
from ingestion import provenance as ing_prov
from league.models import Company


def _company(slug='ingested'):
    return Company.objects.create(name=slug, slug=slug, country='UK')


def _written(**overrides):
    """A profile_data-shaped dict like the one the pipeline builds."""
    data = {key: 60.0 for key in ing_prov.SIGNAL_FOR_METRIC}
    # Non-metric fields the pipeline also writes; must be ignored.
    data.update({'pollution_level': 'medium', 'ai_summary': 'text',
                 'annual_revenue': 1_000_000, 'status': 'public'})
    data.update(overrides)
    return data


class TheOriginDecision(SimpleTestCase):
    """The semantics, pinned so they cannot drift."""

    def test_ingestion_writes_inferred_not_measured(self):
        from pathlib import Path

        source = (Path(__file__).resolve().parent / 'provenance.py').read_text()
        self.assertIn('PROVENANCE_INFERRED', source)
        self.assertNotIn('PROVENANCE_MEASURED', source)

    def test_inferred_is_a_distinct_origin(self):
        self.assertNotEqual(PROVENANCE_INFERRED, PROVENANCE_MEASURED)
        self.assertNotEqual(PROVENANCE_INFERRED, PROVENANCE_MODELLED)

    def test_every_written_key_is_a_registered_material_metric(self):
        for key in ing_prov.SIGNAL_FOR_METRIC:
            with self.subTest(key=key):
                self.assertIn(key, registry.VALID_KEYS)
                self.assertEqual(registry.REGISTRY[key].kind, registry.MATERIAL)

    def test_pollution_level_is_not_recorded(self):
        """Categorical, and not a registered metric. See the context doc."""
        self.assertNotIn('pollution_level', ing_prov.SIGNAL_FOR_METRIC)

    def test_the_five_signals_are_the_pipeline_pillars(self):
        self.assertEqual(set(ing_prov.SIGNAL_FOR_METRIC.values()),
                         {'pollution_footprint', 'reduction_progress',
                          'investment', 'transparency', 'community_impact'})

    def test_sixteen_metrics_from_five_signals(self):
        """
        The fan-out is the point. Recording the signal per metric is what makes
        it visible that three environmental metrics are one assessment.
        """
        self.assertEqual(len(ing_prov.SIGNAL_FOR_METRIC), 16)
        self.assertEqual(len(set(ing_prov.SIGNAL_FOR_METRIC.values())), 5)

    def test_the_duplicated_environmental_metrics_share_one_signal(self):
        signals = ing_prov.SIGNAL_FOR_METRIC
        self.assertEqual(signals['waste_management_score'], 'pollution_footprint')
        self.assertEqual(signals['water_impact_score'], 'pollution_footprint')
        self.assertEqual(signals['biodiversity_impact_score'], 'pollution_footprint')


class RecordingTheWrite(TestCase):

    def setUp(self):
        self.company = _company()
        self.profile = CompanyProfile.objects.create(
            company=self.company, status='public', pollution_level='medium')

    def test_all_sixteen_metrics_are_recorded(self):
        result = ing_prov.record_ingestion_write(self.profile, _written())

        self.assertEqual(result['recorded'], 16)
        rows = CompanyMetricProvenance.objects.filter(
            company=self.profile, is_current=True)
        self.assertEqual(rows.count(), 16)

    def test_every_row_is_inferred(self):
        ing_prov.record_ingestion_write(self.profile, _written())

        origins = set(CompanyMetricProvenance.objects
                      .filter(company=self.profile)
                      .values_list('origin', flat=True))
        self.assertEqual(origins, {PROVENANCE_INFERRED})

    def test_nothing_is_recorded_as_measured(self):
        ing_prov.record_ingestion_write(self.profile, _written())

        self.assertEqual(CompanyMetricProvenance.objects.filter(
            company=self.profile, origin=PROVENANCE_MEASURED).count(), 0)

    def test_the_methodology_names_the_source_signal(self):
        ing_prov.record_ingestion_write(self.profile, _written())

        row = prov.current(self.profile, 'water_impact_score')
        self.assertEqual(row.methodology,
                         'ecoiq-ingestion-llm-assessment:pollution_footprint')

    def test_the_writer_is_named(self):
        ing_prov.record_ingestion_write(self.profile, _written())

        self.assertEqual(prov.current(self.profile, 'audit_quality_score').written_by,
                         'ingestion.pipeline.IngestionPipeline._step_save')

    def test_review_is_proposed_never_confirmed(self):
        ing_prov.record_ingestion_write(self.profile, _written())

        for row in CompanyMetricProvenance.objects.filter(company=self.profile):
            with self.subTest(key=row.metric_key):
                self.assertEqual(row.review_status, 'proposed')
                self.assertIsNone(row.reviewed_by)

    def test_no_confidence_is_fabricated(self):
        ing_prov.record_ingestion_write(self.profile, _written())

        for row in CompanyMetricProvenance.objects.filter(company=self.profile):
            with self.subTest(key=row.metric_key):
                self.assertIsNone(row.confidence,
                                  'an unknown confidence is NULL, never 50')

    def test_non_metric_fields_are_ignored(self):
        ing_prov.record_ingestion_write(self.profile, _written())

        keys = set(CompanyMetricProvenance.objects.filter(company=self.profile)
                   .values_list('metric_key', flat=True))
        for ignored in ('pollution_level', 'ai_summary', 'annual_revenue', 'status'):
            with self.subTest(key=ignored):
                self.assertNotIn(ignored, keys)

    def test_an_unwritten_metric_is_not_recorded(self):
        partial = _written()
        del partial['water_impact_score']

        result = ing_prov.record_ingestion_write(self.profile, partial)

        self.assertEqual(result['recorded'], 15)
        self.assertIsNone(prov.current(self.profile, 'water_impact_score'))

    def test_a_none_value_records_no_origin(self):
        """Recording an origin for an absent value asserts a number never stored."""
        result = ing_prov.record_ingestion_write(
            self.profile, _written(water_impact_score=None))

        self.assertEqual(result['recorded'], 15)
        self.assertEqual(result['skipped'], 1)
        self.assertIsNone(prov.current(self.profile, 'water_impact_score'))

    def test_a_genuine_zero_is_recorded(self):
        ing_prov.record_ingestion_write(self.profile, _written(water_impact_score=0.0))

        row = prov.current(self.profile, 'water_impact_score')
        self.assertIsNotNone(row, 'zero is a finding, not an absence')
        self.assertEqual(row.origin, PROVENANCE_INFERRED)

    def test_re_ingestion_supersedes_rather_than_duplicating(self):
        ing_prov.record_ingestion_write(self.profile, _written())
        ing_prov.record_ingestion_write(self.profile, _written(water_impact_score=71.0))

        rows = prov.history(self.profile, 'water_impact_score')
        self.assertEqual(rows.count(), 2)
        self.assertEqual([r.is_current for r in rows], [True, False])

    def test_only_one_current_row_per_metric(self):
        from django.db.models import Count

        ing_prov.record_ingestion_write(self.profile, _written())
        ing_prov.record_ingestion_write(self.profile, _written())

        dupes = (CompanyMetricProvenance.objects
                 .filter(company=self.profile, is_current=True)
                 .values('metric_key').annotate(n=Count('id')).filter(n__gt=1))
        self.assertEqual(dupes.count(), 0)


class EvidenceLinking(TestCase):
    """
    Linkage runs through `source_reference`, not through a company FK.

    `EvidenceMemory.company` points at CompanyProfile, and
    `create_memory_from_league_evidence` deliberately never sets it — a
    league.Company pk in that column would silently address a different table's
    row. That constraint is the reason this lookup looks the way it does.
    """

    def setUp(self):
        self.company = _company('evidenced')
        self.profile = CompanyProfile.objects.create(
            company=self.company, status='public', pollution_level='medium')

    def _evidence(self, doc_type='audit_report', url='https://example.com/esg.pdf'):
        from league.models import Evidence
        from evidence_memory.services.memory import create_memory_from_league_evidence

        evidence = Evidence.objects.create(
            company=self.company, url=url, doc_type=doc_type,
            title='ESG report', notes='Scope 1 emissions were 1,250,000 t.',
            verification_status='pending')
        create_memory_from_league_evidence(evidence)
        return evidence

    def test_the_row_links_to_the_evidence_memory(self):
        evidence = self._evidence()
        memory = ing_prov.best_evidence_memory([evidence])
        self.assertIsNotNone(memory)

        ing_prov.record_ingestion_write(self.profile, _written(), evidence=memory)

        self.assertEqual(prov.current(self.profile, 'water_impact_score').evidence,
                         memory)

    def test_the_memory_is_found_by_source_reference(self):
        evidence = self._evidence()

        memory = ing_prov.best_evidence_memory([evidence])

        self.assertEqual(memory.source_reference, f'league.Evidence:{evidence.pk}')

    def test_the_strongest_document_type_wins(self):
        news = self._evidence(doc_type='press_release', url='https://example.com/news')
        report = self._evidence(doc_type='audit_report', url='https://example.com/esg')

        memory = ing_prov.best_evidence_memory([news, report])

        self.assertEqual(memory.source_reference, f'league.Evidence:{report.pk}')

    def test_no_sources_means_no_link_and_no_error(self):
        """A run whose sources could not be downloaded still records origins."""
        self.assertIsNone(ing_prov.best_evidence_memory([]))

        result = ing_prov.record_ingestion_write(self.profile, _written())

        self.assertEqual(result['recorded'], 16)
        self.assertFalse(result['evidence_linked'])
        self.assertIsNone(prov.current(self.profile, 'water_impact_score').evidence)

    def test_an_evidence_row_with_no_memory_is_skipped(self):
        from league.models import Evidence

        orphan = Evidence.objects.create(
            company=self.company, url='https://example.com/orphan',
            doc_type='other', title='no memory', verification_status='pending')

        self.assertIsNone(ing_prov.best_evidence_memory([orphan]))

    def test_the_link_survives_re_ingestion(self):
        evidence = self._evidence()
        memory = ing_prov.best_evidence_memory([evidence])
        ing_prov.record_ingestion_write(self.profile, _written(), evidence=memory)
        ing_prov.record_ingestion_write(self.profile, _written(), evidence=memory)

        rows = prov.history(self.profile, 'water_impact_score')
        self.assertEqual(rows.count(), 2)
        for row in rows:
            with self.subTest(pk=row.pk):
                self.assertEqual(row.evidence, memory)


class Atomicity(TestCase):

    def setUp(self):
        self.company = _company('atomic')

    def test_a_provenance_failure_rolls_back_the_profile_write(self):
        """
        The invariant D3C exists to protect, exercised through the same
        transaction shape the pipeline uses.
        """
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                profile = CompanyProfile.objects.create(
                    company=self.company, status='public',
                    pollution_level='medium', water_impact_score=88.0)
                with patch('companies.provenance.record',
                           side_effect=RuntimeError('injected')):
                    ing_prov.record_ingestion_write(profile, _written())

        self.assertFalse(CompanyProfile.objects.filter(company=self.company).exists())
        self.assertEqual(CompanyMetricProvenance.objects.count(), 0)

    def test_no_orphaned_provenance_without_a_value(self):
        try:
            with transaction.atomic():
                profile = CompanyProfile.objects.create(
                    company=self.company, status='public', pollution_level='medium')
                ing_prov.record_ingestion_write(profile, _written())
                raise RuntimeError('later step failed')
        except RuntimeError:
            pass

        self.assertEqual(CompanyMetricProvenance.objects.count(), 0)


class Defensibility(TestCase):
    """
    INFERRED is an evidenced origin, so ingested metrics CAN be defensible —
    unlike SEEDED or LEGACY. That is the whole point of recording it.
    """

    def setUp(self):
        self.company = _company('defensible')
        self.profile = CompanyProfile.objects.create(
            company=self.company, status='public', pollution_level='medium')

    def test_an_ingested_metric_is_defensible(self):
        ing_prov.record_ingestion_write(self.profile, _written())

        self.assertTrue(prov.is_publicly_defensible(self.profile,
                                                    'water_impact_score'))

    def test_a_seeded_metric_is_not(self):
        prov.record(self.profile, 'water_impact_score', PROVENANCE_SEEDED)

        self.assertFalse(prov.is_publicly_defensible(self.profile,
                                                     'water_impact_score'))

    def test_derived_scores_built_on_ingestion_are_defensible(self):
        from companies.scoring import recalculate_and_save

        ing_prov.record_ingestion_write(self.profile, _written())
        recalculate_and_save(self.profile)

        self.assertTrue(prov.is_derived_publicly_defensible(
            self.profile, 'company.ecoiq_total'))

    def test_one_seeded_input_still_disqualifies_the_composite(self):
        from companies.scoring import recalculate_and_save

        ing_prov.record_ingestion_write(self.profile, _written())
        prov.record(self.profile, 'water_impact_score', PROVENANCE_SEEDED)
        recalculate_and_save(self.profile)

        self.assertFalse(prov.is_derived_publicly_defensible(
            self.profile, 'company.ecoiq_total'))


class PipelineWiring(SimpleTestCase):
    """The pipeline actually calls this, in the right order, atomically."""

    def _source(self):
        from pathlib import Path

        return (Path(__file__).resolve().parent / 'pipeline.py').read_text()

    def test_the_pipeline_records_provenance(self):
        self.assertIn('ing_prov.record_ingestion_write', self._source())

    def test_the_write_is_inside_a_transaction(self):
        source = self._source()
        block = source[source.index('with transaction.atomic():'):]
        block = block[:block.index('profile_rescore(profile)')]

        self.assertIn('CompanyProfile.objects.get_or_create', block)
        self.assertIn('ing_prov.record_ingestion_write', block)

    def test_evidence_is_persisted_before_the_profile_write(self):
        source = self._source()

        self.assertLess(source.index('self._persist_source_evidence(company)\n            source_evidence'),
                        source.index('ing_prov.record_ingestion_write'))

    def test_rescoring_runs_outside_the_material_write(self):
        """
        recalculate_and_save records its own MODELLED pillar provenance and
        must see the material rows, not race them.
        """
        source = self._source()

        self.assertLess(source.index('ing_prov.record_ingestion_write'),
                        source.index('profile_rescore(profile)'))

    def test_the_evidence_helper_is_idempotent_by_get_or_create(self):
        source = self._source()
        block = source[source.index('def _persist_source_evidence'):]
        block = block[:block.index('def _step_save')]

        self.assertIn('get_or_create', block)
