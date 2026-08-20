"""
D3C-1 — seed writes record provenance atomically.

Covers A–O from the brief. The invariant everything here serves:

    SEED VALUE WRITE  and  SEEDED PROVENANCE WRITE  are one logical operation.

Never "save the value, then maybe create provenance". A crash between the two
recreates the exact state D3B measured across the whole estate: 2976 values and
not one whose lineage could be reconstructed.

Tests H and I are the load-bearing pair — they prove the two writes fail
together in both directions.
"""
from django.db import IntegrityError, transaction
from django.test import TestCase

from companies import provenance as prov
from companies.evidence import (
    PROVENANCE_MEASURED, PROVENANCE_MODELLED, PROVENANCE_SEEDED, PROVENANCE_UNKNOWN,
)
from companies.models import CompanyMetricProvenance, CompanyProfile
from companies.provenance import TrustedProvenanceOverwrite, record_seed_write
from league.models import Company

WRITER = 'seed:test_seeder'


def _profile(slug, **kwargs):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    return CompanyProfile.objects.create(company=company, status='public', **kwargs)


class A_B_C_SeedWriteRecordsProvenance(TestCase):

    def setUp(self):
        self.profile = _profile('seed-basic')

    def test_a_a_seed_write_creates_seeded_provenance(self):
        with transaction.atomic():
            self.profile.water_impact_score = 68.0
            self.profile.save()
            record_seed_write(self.profile, ['water_impact_score'], WRITER)

        row = prov.current(self.profile, 'water_impact_score')
        self.assertIsNotNone(row)
        self.assertEqual(row.origin, PROVENANCE_SEEDED)

    def test_b_provenance_carries_the_exact_metric_key(self):
        record_seed_write(self.profile, ['water_impact_score'], WRITER)

        rows = CompanyMetricProvenance.objects.all()
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().metric_key, 'water_impact_score')

    def test_b_non_material_keys_are_ignored_not_rejected(self):
        """
        Callers hand over a whole defaults dict; the service filters. Rejecting
        would force every command to maintain its own copy of the registry.
        """
        record_seed_write(
            self.profile,
            ['water_impact_score', 'ai_summary', 'status', 'ecoiq_total_score'],
            WRITER)

        keys = set(CompanyMetricProvenance.objects.values_list('metric_key', flat=True))
        self.assertEqual(keys, {'water_impact_score'})

    def test_b_a_dict_may_be_passed_directly(self):
        defaults = {'water_impact_score': 68.0, 'status': 'public'}
        record_seed_write(self.profile, defaults, WRITER)

        self.assertEqual(CompanyMetricProvenance.objects.count(), 1)

    def test_c_written_by_names_the_exact_command(self):
        record_seed_write(self.profile, ['water_impact_score'], WRITER)

        row = prov.current(self.profile, 'water_impact_score')
        self.assertEqual(row.written_by, WRITER)
        self.assertNotIn(row.written_by, ('seed', 'script', 'unknown', ''))

    def test_c_all_five_seed_commands_declare_a_named_writer(self):
        """
        STEP 7 — a stable identity per command is what makes future lineage
        reconstructible, which D3B proved is impossible after the fact.
        """
        import importlib
        from pathlib import Path

        expected = {
            'add_400_companies': 'seed:add_400_companies',
            'focus_target_markets': 'seed:focus_target_markets',
        }
        for module_name, writer_id in expected.items():
            with self.subTest(command=module_name):
                module = importlib.import_module(
                    f'companies.management.commands.{module_name}')
                self.assertEqual(module.WRITER_ID, writer_id)

        # The other three pass the identity inline; assert the literal is present
        # so a rename cannot silently degrade it to a generic string.
        commands = Path(__file__).resolve().parent / 'management' / 'commands'
        for name in ('seed_companies', 'seed_global_companies', 'seed_phase2_companies'):
            with self.subTest(command=name):
                source = (commands / f'{name}.py').read_text()
                self.assertIn(f"'seed:{name}'", source)


class D_E_F_G_NothingIsFabricated(TestCase):

    def setUp(self):
        self.profile = _profile('no-fabrication', water_impact_score=68.0)
        record_seed_write(self.profile, ['water_impact_score'], WRITER)
        self.row = prov.current(self.profile, 'water_impact_score')

    def test_d_no_evidence_is_attached(self):
        self.assertIsNone(self.row.evidence)

    def test_e_no_confidence_is_attached(self):
        self.assertIsNone(self.row.confidence)
        self.assertNotEqual(self.row.confidence, 50.0)

    def test_f_no_human_review_is_attached(self):
        self.assertEqual(self.row.review_status, 'proposed')
        self.assertIsNone(self.row.reviewed_by)
        self.assertIsNone(self.row.reviewed_at)

    def test_f_no_observation_date_is_invented(self):
        self.assertIsNone(self.row.observed_at)

    def test_g_seeded_is_not_publicly_defensible(self):
        """
        The value is real-looking — 68.0, not a default. Provenance is what
        makes it unpublishable, which is the entire point of the record.
        """
        self.assertEqual(self.row.value, 68.0)
        self.assertFalse(
            prov.is_publicly_defensible(self.profile, 'water_impact_score'))

    def test_g_a_whole_seeded_profile_is_not_publicly_defensible(self):
        record_seed_write(self.profile, sorted(prov.VALID_METRIC_KEYS), WRITER)

        defensible = sum(
            1 for m in prov.VALID_METRIC_KEYS
            if prov.is_publicly_defensible(self.profile, m))
        self.assertEqual(defensible, 0)


class H_I_Atomicity(TestCase):
    """
    The pair that proves the invariant. Both directions, because a one-way
    guarantee is not a guarantee.
    """

    def test_h_provenance_failure_rolls_back_the_metric_write(self):
        from unittest.mock import patch

        profile = _profile('rollback-prov', water_impact_score=10.0)

        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                profile.water_impact_score = 99.0
                profile.save()
                with patch.object(CompanyMetricProvenance.objects, 'bulk_create',
                                  side_effect=RuntimeError('provenance failed')):
                    record_seed_write(profile, ['water_impact_score'], WRITER)

        profile.refresh_from_db()
        self.assertEqual(profile.water_impact_score, 10.0,
                         'the value must roll back with its provenance')
        self.assertEqual(CompanyMetricProvenance.objects.count(), 0)

    def test_i_metric_write_failure_leaves_no_provenance(self):
        profile = _profile('rollback-value')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                record_seed_write(profile, ['water_impact_score'], WRITER)
                # NOT NULL until D4 — a realistic in-transaction failure.
                profile.water_impact_score = None
                profile.save()

        self.assertEqual(CompanyMetricProvenance.objects.count(), 0,
                         'provenance must not survive a failed value write')

    def test_h_the_service_does_not_open_its_own_transaction(self):
        """
        An inner atomic() would create a savepoint able to commit independently
        of the value write — reintroducing the split this prevents.

        Parsed rather than string-matched: the docstring documents the rule and
        therefore contains the very phrase a naive search would trip on.
        """
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(record_seed_write).lstrip())
        calls = [
            ast.unparse(node.func)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        ]
        withs = [
            ast.unparse(item.context_expr)
            for node in ast.walk(tree)
            if isinstance(node, (ast.With, ast.AsyncWith))
            for item in node.items
        ]

        self.assertNotIn('transaction.atomic', calls + withs)
        self.assertEqual(
            [d for d in getattr(tree.body[0], 'decorator_list', [])], [],
            'an @transaction.atomic decorator would have the same effect')

    def test_i_a_trusted_overwrite_refusal_also_rolls_back_the_value(self):
        profile = _profile('refusal-rollback', water_impact_score=10.0)
        prov.record(profile, 'water_impact_score', PROVENANCE_MEASURED,
                    written_by='ingestion')

        with self.assertRaises(TrustedProvenanceOverwrite):
            with transaction.atomic():
                profile.water_impact_score = 99.0
                profile.save()
                record_seed_write(profile, ['water_impact_score'], WRITER)

        profile.refresh_from_db()
        self.assertEqual(profile.water_impact_score, 10.0)


class J_HistoryIsPreserved(TestCase):

    def setUp(self):
        self.profile = _profile('history', water_impact_score=68.0)

    def test_j_previous_provenance_becomes_historical_not_deleted(self):
        prov.record(self.profile, 'water_impact_score', PROVENANCE_MODELLED,
                    written_by='companies.scoring')

        record_seed_write(self.profile, ['water_impact_score'], WRITER,
                          allow_trusted_overwrite=True)

        rows = prov.history(self.profile, 'water_impact_score')
        self.assertEqual(rows.count(), 2)
        self.assertEqual([r.origin for r in rows],
                         [PROVENANCE_SEEDED, PROVENANCE_MODELLED])
        self.assertEqual([r.is_current for r in rows], [True, False])

    def test_j_the_prior_row_is_superseded_not_mutated(self):
        original = prov.record(self.profile, 'water_impact_score',
                               PROVENANCE_MODELLED, written_by='companies.scoring')

        record_seed_write(self.profile, ['water_impact_score'], WRITER,
                          allow_trusted_overwrite=True)

        original.refresh_from_db()
        self.assertEqual(original.origin, PROVENANCE_MODELLED,
                         'the historical origin must not be rewritten')
        self.assertFalse(original.is_current)

    def test_j_legacy_backfill_rows_are_superseded_not_reclassified(self):
        """
        STEP 9 — D3C-1 fixes future writes. It must not retroactively convert
        D3B's legacy rows merely because the same command now records SEEDED.
        """
        legacy = prov.record(self.profile, 'water_impact_score',
                             PROVENANCE_UNKNOWN, written_by='d3b_backfill')

        record_seed_write(self.profile, ['water_impact_score'], WRITER)

        legacy.refresh_from_db()
        self.assertEqual(legacy.origin, PROVENANCE_UNKNOWN)
        self.assertEqual(legacy.written_by, 'd3b_backfill')
        self.assertFalse(legacy.is_current)

    def test_j_a_legacy_row_is_not_trusted_so_needs_no_override(self):
        """LEGACY_UNKNOWN_PROVENANCE is unevidenced — a seeder may supersede it."""
        prov.record(self.profile, 'water_impact_score', PROVENANCE_UNKNOWN,
                    written_by='d3b_backfill')

        rows = record_seed_write(self.profile, ['water_impact_score'], WRITER)

        self.assertEqual(len(rows), 1)


class K_TrustedDataProtection(TestCase):
    """
    STEP 5 — a seed command must not silently overwrite trusted provenance.

    The check is on PROVENANCE, not on the value: "this number looks real" is
    not a safeguard; "someone recorded where this came from and it was not a
    seeder" is.
    """

    def setUp(self):
        self.profile = _profile('trusted', water_impact_score=68.0)

    def test_k_measured_provenance_blocks_a_seed_overwrite(self):
        prov.record(self.profile, 'water_impact_score', PROVENANCE_MEASURED,
                    written_by='ingestion')

        with self.assertRaises(TrustedProvenanceOverwrite):
            record_seed_write(self.profile, ['water_impact_score'], WRITER)

    def test_k_every_evidenced_origin_blocks_an_overwrite(self):
        from companies.evidence import EVIDENCED_PROVENANCE

        for origin in sorted(EVIDENCED_PROVENANCE):
            with self.subTest(origin=origin):
                profile = _profile(f'trusted-{origin.lower()}', water_impact_score=68.0)
                prov.record(profile, 'water_impact_score', origin,
                            written_by='ingestion')

                with self.assertRaises(TrustedProvenanceOverwrite):
                    record_seed_write(profile, ['water_impact_score'], WRITER)

    def test_k_the_refusal_names_the_blocking_metric(self):
        prov.record(self.profile, 'water_impact_score', PROVENANCE_MEASURED,
                    written_by='ingestion')

        with self.assertRaises(TrustedProvenanceOverwrite) as ctx:
            record_seed_write(self.profile, ['water_impact_score'], WRITER)

        self.assertIn('water_impact_score', str(ctx.exception))

    def test_k_an_explicit_development_override_is_required(self):
        prov.record(self.profile, 'water_impact_score', PROVENANCE_MEASURED,
                    written_by='ingestion')

        rows = record_seed_write(self.profile, ['water_impact_score'], WRITER,
                                 allow_trusted_overwrite=True)

        self.assertEqual(len(rows), 1)
        self.assertEqual(prov.current(self.profile, 'water_impact_score').origin,
                         PROVENANCE_SEEDED)

    def test_k_one_trusted_metric_blocks_the_whole_write(self):
        """
        All-or-nothing per call. Writing the untrusted fifteen and refusing the
        sixteenth would leave the company's provenance half-reflecting a run
        that did not complete.
        """
        prov.record(self.profile, 'water_impact_score', PROVENANCE_MEASURED,
                    written_by='ingestion')

        with self.assertRaises(TrustedProvenanceOverwrite):
            record_seed_write(self.profile, sorted(prov.VALID_METRIC_KEYS), WRITER)

        self.assertEqual(
            CompanyMetricProvenance.objects.filter(origin=PROVENANCE_SEEDED).count(), 0)

    def test_k_seeded_provenance_does_not_block_another_seed_run(self):
        record_seed_write(self.profile, ['water_impact_score'], WRITER)

        record_seed_write(self.profile, ['water_impact_score'], WRITER)  # must not raise

        self.assertEqual(CompanyMetricProvenance.objects.count(), 1)


class L_M_N_ValueNeverDeterminesProvenance(TestCase):

    def test_l_a_genuine_zero_seed_value_stays_zero_and_seeded(self):
        profile = _profile('seed-zero', water_impact_score=0.0)
        record_seed_write(profile, ['water_impact_score'], WRITER)

        row = prov.current(profile, 'water_impact_score')
        self.assertEqual(row.value, 0.0)
        self.assertEqual(row.origin, PROVENANCE_SEEDED)

    def test_m_a_genuine_fifty_seed_value_stays_fifty_and_seeded(self):
        profile = _profile('seed-fifty', water_impact_score=50.0)
        record_seed_write(profile, ['water_impact_score'], WRITER)

        row = prov.current(profile, 'water_impact_score')
        self.assertEqual(row.value, 50.0)
        self.assertEqual(row.origin, PROVENANCE_SEEDED)

    def test_n_every_value_gets_the_same_origin(self):
        for slug, value in (('n-0', 0.0), ('n-50', 50.0), ('n-72', 72.0),
                            ('n-100', 100.0)):
            profile = _profile(slug, water_impact_score=value)
            record_seed_write(profile, ['water_impact_score'], WRITER)

        origins = set(CompanyMetricProvenance.objects.values_list('origin', flat=True))
        self.assertEqual(origins, {PROVENANCE_SEEDED},
                         'the number must not influence the origin')

    def test_n_the_writer_decides_the_origin_not_the_data(self):
        seeded = _profile('by-seeder', water_impact_score=72.0)
        measured = _profile('by-ingestion', water_impact_score=72.0)

        record_seed_write(seeded, ['water_impact_score'], WRITER)
        prov.record(measured, 'water_impact_score', PROVENANCE_MEASURED,
                    written_by='ingestion')

        self.assertEqual(prov.current(seeded, 'water_impact_score').origin,
                         PROVENANCE_SEEDED)
        self.assertEqual(prov.current(measured, 'water_impact_score').origin,
                         PROVENANCE_MEASURED)


class O_RepeatedRunsDoNotChurn(TestCase):
    """
    STEP 10 — a re-run that changed nothing is not a provenance event.

    Recording one anyway would grow history on every run with no new
    information, and bury genuine origin changes in the noise.
    """

    def setUp(self):
        self.profile = _profile('churn', water_impact_score=68.0)

    def test_o_an_identical_repeat_creates_no_new_row(self):
        record_seed_write(self.profile, ['water_impact_score'], WRITER)
        record_seed_write(self.profile, ['water_impact_score'], WRITER)
        record_seed_write(self.profile, ['water_impact_score'], WRITER)

        self.assertEqual(CompanyMetricProvenance.objects.count(), 1)
        self.assertEqual(
            CompanyMetricProvenance.objects.filter(is_current=False).count(), 0)

    def test_o_a_repeat_returns_an_empty_list(self):
        record_seed_write(self.profile, ['water_impact_score'], WRITER)

        self.assertEqual(record_seed_write(self.profile, ['water_impact_score'],
                                           WRITER), [])

    def test_o_a_different_writer_does_create_a_new_event(self):
        """
        Identity is (origin, writer) — a different seeder taking over the metric
        is a real change of lineage.
        """
        record_seed_write(self.profile, ['water_impact_score'], WRITER)
        record_seed_write(self.profile, ['water_impact_score'], 'seed:other_seeder')

        rows = prov.history(self.profile, 'water_impact_score')
        self.assertEqual(rows.count(), 2)
        self.assertEqual(rows.first().written_by, 'seed:other_seeder')

    def test_o_churn_control_keys_on_writer_not_value(self):
        """
        A seeder changing the value it writes does NOT create a new provenance
        event: what the value is changed, but where it came from did not. Value
        history is CompanyScoreSnapshot's job, not provenance's.
        """
        record_seed_write(self.profile, ['water_impact_score'], WRITER)

        self.profile.water_impact_score = 12.0
        self.profile.save()
        record_seed_write(self.profile, ['water_impact_score'], WRITER)

        self.assertEqual(CompanyMetricProvenance.objects.count(), 1)
        self.assertEqual(prov.current(self.profile, 'water_impact_score').value, 12.0)


class SeedCommandIntegration(TestCase):
    """
    End-to-end through a real seed command, on the test database.

    The unit tests above prove the service. This proves the wiring, which is
    where D3C-1 could silently fail: a service nobody calls records nothing.
    """

    def test_a_real_seed_command_records_provenance_for_every_company(self):
        from django.core.management import call_command
        from io import StringIO

        call_command('seed_global_companies', stdout=StringIO(), stderr=StringIO())

        profiles = CompanyProfile.objects.count()
        self.assertGreater(profiles, 0)

        rows = CompanyMetricProvenance.objects.all()
        self.assertEqual(rows.count(), profiles * len(prov.VALID_METRIC_KEYS))
        self.assertEqual(set(rows.values_list('origin', flat=True)),
                         {PROVENANCE_SEEDED})
        self.assertEqual(set(rows.values_list('written_by', flat=True)),
                         {'seed:seed_global_companies'})

    def test_a_real_seed_command_is_idempotent_for_provenance(self):
        from django.core.management import call_command
        from io import StringIO

        call_command('seed_global_companies', stdout=StringIO(), stderr=StringIO())
        first = CompanyMetricProvenance.objects.count()

        call_command('seed_global_companies', stdout=StringIO(), stderr=StringIO())

        self.assertEqual(CompanyMetricProvenance.objects.count(), first)
        self.assertEqual(
            CompanyMetricProvenance.objects.filter(is_current=False).count(), 0)

    def test_nothing_a_seed_command_writes_is_publicly_defensible(self):
        from django.core.management import call_command
        from io import StringIO

        call_command('seed_global_companies', stdout=StringIO(), stderr=StringIO())

        defensible = sum(
            1
            for profile in CompanyProfile.objects.all()
            for metric in prov.VALID_METRIC_KEYS
            if prov.is_publicly_defensible(profile, metric)
        )
        self.assertEqual(defensible, 0)
