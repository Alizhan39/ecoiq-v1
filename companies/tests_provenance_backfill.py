"""
D3B — deterministic legacy provenance labelling.

Covers A–O from the brief. Labels only: no metric value changes, no scoring
changes, no schema change, no live writer wired up.

The test that matters most is F/G/H. D3B writes ~3000 provenance rows across the
whole estate, and if any of those origins satisfied `is_publicly_defensible()`
the result would be scores reappearing publicly on the strength of a backfill
label — the exact failure the containment work in #239–#241 exists to prevent.
"""
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from companies import provenance as prov
from companies.evidence import (
    PROVENANCE_MEASURED, PROVENANCE_NO_VALUE, PROVENANCE_SEEDED, PROVENANCE_UNKNOWN,
)
from companies.management.commands.backfill_metric_provenance import (
    WRITER, Command, seed_lineage_reason,
)
from companies.models import CompanyMetricProvenance, CompanyProfile
from league.models import Company

#: The marker mizan.scoring already relies on to identify seeded profiles.
SEED_SUMMARY = 'Profile seeded by add_400_companies — placeholder text pending research.'


def _profile(slug, **kwargs):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    return CompanyProfile.objects.create(company=company, status='public', **kwargs)


def _run(*args):
    out = StringIO()
    call_command('backfill_metric_provenance', *args, stdout=out, stderr=StringIO())
    return out.getvalue()


class A_DryRunWritesNothing(TestCase):

    def setUp(self):
        self.profile = _profile('dry-run')

    def test_a_dry_run_creates_zero_rows(self):
        _run()

        self.assertEqual(CompanyMetricProvenance.objects.count(), 0)

    def test_a_dry_run_is_the_default(self):
        """Writing must be opted into, not out of."""
        _run()

        self.assertEqual(CompanyMetricProvenance.objects.count(), 0)

    def test_a_dry_run_still_reports_what_it_would_do(self):
        output = _run()

        self.assertIn('DRY RUN', output)
        self.assertIn('Pairs considered', output)
        self.assertIn(str(len(prov.VALID_METRIC_KEYS)), output)


class B_ApplyCreatesDeterministicRecords(TestCase):

    def setUp(self):
        self.profile = _profile('apply')

    def test_b_apply_creates_one_row_per_material_metric(self):
        _run('--apply')

        self.assertEqual(CompanyMetricProvenance.objects.count(),
                         len(prov.VALID_METRIC_KEYS))

    def test_b_every_row_is_tagged_with_the_writer(self):
        _run('--apply')

        self.assertEqual(
            CompanyMetricProvenance.objects.exclude(written_by=WRITER).count(), 0)

    def test_b_every_row_is_current(self):
        _run('--apply')

        self.assertEqual(
            CompanyMetricProvenance.objects.filter(is_current=True).count(),
            len(prov.VALID_METRIC_KEYS))

    def test_b_scoping_to_one_metric_writes_only_that_metric(self):
        _run('--apply', '--metric', 'audit_quality_score')

        rows = CompanyMetricProvenance.objects.all()
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().metric_key, 'audit_quality_score')

    def test_b_an_invalid_metric_scope_is_refused_without_writing(self):
        _run('--apply', '--metric', 'env score')

        self.assertEqual(CompanyMetricProvenance.objects.count(), 0)


class C_Idempotency(TestCase):

    def setUp(self):
        self.profile = _profile('idempotent')

    def test_c_second_apply_creates_zero_rows(self):
        _run('--apply')
        first = CompanyMetricProvenance.objects.count()

        _run('--apply')

        self.assertEqual(CompanyMetricProvenance.objects.count(), first)

    def test_c_second_apply_reports_everything_as_skipped(self):
        _run('--apply')
        output = _run('--apply')

        self.assertIn(f'Existing provenance skipped        {len(prov.VALID_METRIC_KEYS)}',
                      output)
        self.assertIn('Rows written                       0', output)

    def test_c_no_duplicate_current_rows_are_produced(self):
        from django.db.models import Count

        _run('--apply')
        _run('--apply')

        duplicates = (CompanyMetricProvenance.objects
                      .filter(is_current=True)
                      .values('company', 'metric_key')
                      .annotate(n=Count('id')).filter(n__gt=1))

        self.assertEqual(duplicates.count(), 0)

    def test_c_idempotency_is_not_achieved_by_deleting_history(self):
        """
        Re-running must skip, not supersede. A backfill that superseded its own
        rows would grow the history table on every run with no new information.
        """
        _run('--apply')
        _run('--apply')
        _run('--apply')

        self.assertEqual(CompanyMetricProvenance.objects.count(),
                         len(prov.VALID_METRIC_KEYS))
        self.assertEqual(
            CompanyMetricProvenance.objects.filter(is_current=False).count(), 0)


class D_E_ExistingProvenanceIsPreserved(TestCase):
    """
    D/E — an analyst decision or an evidence-backed record outranks a backfill
    label, and this command has no basis to second-guess either.
    """

    def setUp(self):
        self.profile = _profile('preserve')

    def test_d_analyst_provenance_survives_the_backfill(self):
        user = get_user_model().objects.create(username='analyst')
        prov.record(self.profile, 'audit_quality_score', PROVENANCE_MEASURED,
                    review_status='confirmed', reviewed_by=user,
                    written_by='analyst_review')

        _run('--apply')

        row = prov.current(self.profile, 'audit_quality_score')
        self.assertEqual(row.origin, PROVENANCE_MEASURED)
        self.assertEqual(row.written_by, 'analyst_review')
        self.assertEqual(row.reviewed_by, user)

    def test_e_evidence_backed_provenance_survives_the_backfill(self):
        from evidence_memory.models import EvidenceMemory

        evidence = EvidenceMemory.objects.create(
            text_chunk='Audited disclosure.', source_type='company_report')
        prov.record(self.profile, 'audit_quality_score', PROVENANCE_MEASURED,
                    evidence=evidence, written_by='ingestion')

        _run('--apply')

        row = prov.current(self.profile, 'audit_quality_score')
        self.assertEqual(row.evidence, evidence)
        self.assertEqual(row.origin, PROVENANCE_MEASURED)

    def test_d_skips_are_reported_not_silent(self):
        prov.record(self.profile, 'audit_quality_score', PROVENANCE_MEASURED,
                    written_by='analyst_review')

        output = _run('--apply')

        self.assertIn('Existing provenance skipped        1', output)

    def test_d_other_metrics_are_still_labelled_around_the_preserved_one(self):
        prov.record(self.profile, 'audit_quality_score', PROVENANCE_MEASURED,
                    written_by='analyst_review')

        _run('--apply')

        self.assertEqual(
            CompanyMetricProvenance.objects.filter(written_by=WRITER).count(),
            len(prov.VALID_METRIC_KEYS) - 1)


class F_G_H_NothingBecomesPubliclyDefensible(TestCase):
    """
    STEP 7 — the regression that would matter most.

    D3B must not cause a single score to reappear publicly.
    """

    def setUp(self):
        self.profile = _profile('containment', ecoiq_total_score=71.4)

    def test_f_seeded_is_not_publicly_defensible(self):
        self.profile.ai_summary = SEED_SUMMARY
        self.profile.save()
        _run('--apply')

        for metric in sorted(prov.VALID_METRIC_KEYS):
            with self.subTest(metric=metric):
                self.assertFalse(prov.is_publicly_defensible(self.profile, metric))

    def test_g_legacy_unknown_is_not_publicly_defensible(self):
        _run('--apply')

        for metric in sorted(prov.VALID_METRIC_KEYS):
            with self.subTest(metric=metric):
                row = prov.current(self.profile, metric)
                self.assertEqual(row.origin, PROVENANCE_UNKNOWN)
                self.assertFalse(prov.is_publicly_defensible(self.profile, metric))

    def test_h_no_value_provenance_is_not_publicly_defensible(self):
        """
        The UNKNOWN branch cannot be exercised end-to-end yet: water_impact_score
        is still NOT NULL, so a profile with a genuinely missing value cannot be
        SAVED until D4. The classification is therefore driven directly, which
        proves the branch and records why the integration path is unavailable.
        """
        self.profile.water_impact_score = None      # in memory only
        stats = {k: 0 for k in (
            'companies_scanned', 'metrics_scanned', 'pairs_considered',
            'existing_skipped', 'seeded', 'legacy', 'unknown', 'conflicts',
            'errors', 'written')}

        Command()._process_profile(self.profile, ['water_impact_score'], stats, {})

        self.assertEqual(stats['unknown'], 1)
        self.assertEqual(stats['legacy'], 0)

    def test_h_a_recorded_no_value_row_is_never_publicly_defensible(self):
        prov.record(self.profile, 'water_impact_score', PROVENANCE_NO_VALUE,
                    written_by=WRITER)

        self.assertFalse(
            prov.is_publicly_defensible(self.profile, 'water_impact_score'))

    def test_zero_publicly_defensible_pairs_across_the_whole_estate(self):
        for slug in ('c1', 'c2', 'c3'):
            _profile(slug, ecoiq_total_score=61.0)

        _run('--apply')

        defensible = sum(
            1
            for profile in CompanyProfile.objects.all()
            for metric in prov.VALID_METRIC_KEYS
            if prov.is_publicly_defensible(profile, metric)
        )
        self.assertEqual(defensible, 0)

    def test_the_public_company_page_stays_evidence_pending(self):
        from django.test import Client

        from companies.evidence import PENDING_HEADLINE

        _run('--apply')
        body = Client().get('/companies/containment/').content.decode()

        self.assertIn(PENDING_HEADLINE, body)
        self.assertNotIn('71.4', body)


class I_J_K_ValueNeverDeterminesOrigin(TestCase):
    """
    I/J/K — the D2 invariant, now at the provenance layer. Provenance is a fact
    about lineage, not about the number.
    """

    def test_i_a_real_zero_is_labelled_legacy_not_unknown(self):
        profile = _profile('zero-value', anti_corruption_score=0.0)
        _run('--apply')

        row = prov.current(profile, 'anti_corruption_score')
        self.assertEqual(row.value, 0.0)
        self.assertEqual(row.origin, PROVENANCE_UNKNOWN)
        self.assertNotEqual(row.origin, PROVENANCE_NO_VALUE)

    def test_j_a_real_fifty_is_labelled_legacy_not_seeded(self):
        """
        The single most important line in this file. 50 is the old model default
        AND a legitimate measurement, and D3B must not treat the coincidence as
        proof of seeding.
        """
        profile = _profile('fifty-value', anti_corruption_score=50.0)
        _run('--apply')

        row = prov.current(profile, 'anti_corruption_score')
        self.assertEqual(row.value, 50.0)
        self.assertEqual(row.origin, PROVENANCE_UNKNOWN)
        self.assertNotEqual(row.origin, PROVENANCE_SEEDED)

    def test_k_identical_values_get_identical_origins_regardless_of_number(self):
        for slug, value in (('v-0', 0.0), ('v-50', 50.0), ('v-72', 72.0),
                            ('v-100', 100.0)):
            _profile(slug, anti_corruption_score=value)

        _run('--apply')

        origins = {
            CompanyProfile.objects.get(company__slug=slug).metric_provenance
            .get(metric_key='anti_corruption_score').origin
            for slug in ('v-0', 'v-50', 'v-72', 'v-100')
        }
        self.assertEqual(origins, {PROVENANCE_UNKNOWN},
                         'the number must not influence the origin')

    def test_k_seed_lineage_depends_on_the_marker_not_the_value(self):
        seeded = _profile('marked', ai_summary=SEED_SUMMARY, anti_corruption_score=72.0)
        plain = _profile('unmarked', anti_corruption_score=72.0)

        _run('--apply')

        self.assertEqual(
            prov.current(seeded, 'anti_corruption_score').origin, PROVENANCE_SEEDED)
        self.assertEqual(
            prov.current(plain, 'anti_corruption_score').origin, PROVENANCE_UNKNOWN)

    def test_k_a_seed_marker_is_not_enough_if_another_writer_touched_the_profile(self):
        """
        "Company appears in a seed command" is explicitly NOT sufficient — the
        seed must be the ONLY writer that ever touched the profile.
        """
        profile = _profile('marked-but-verified', ai_summary=SEED_SUMMARY)
        profile.is_verified = True
        profile.save()

        self.assertIsNone(seed_lineage_reason(profile))

        _run('--apply')
        self.assertEqual(
            prov.current(profile, 'anti_corruption_score').origin, PROVENANCE_UNKNOWN)

    def test_k_a_cited_source_disqualifies_seed_lineage(self):
        from companies.models import CompanySource

        profile = _profile('marked-with-source', ai_summary=SEED_SUMMARY)
        CompanySource.objects.create(company=profile, url='https://example.org',
                                     title='Annual report')

        self.assertIsNone(seed_lineage_reason(profile))

    def test_k_a_non_seed_snapshot_disqualifies_seed_lineage(self):
        import datetime

        from companies.models import CompanyScoreSnapshot

        profile = _profile('marked-with-snapshot', ai_summary=SEED_SUMMARY)
        CompanyScoreSnapshot.objects.create(
            profile=profile, date=datetime.date.today(), trigger='verification',
            total_score=61.0)

        self.assertIsNone(seed_lineage_reason(profile))

    def test_k_a_seed_snapshot_alone_does_not_disqualify(self):
        """A seed-triggered snapshot is consistent with seed-only lineage."""
        import datetime

        from companies.models import CompanyScoreSnapshot

        profile = _profile('marked-with-seed-snapshot', ai_summary=SEED_SUMMARY)
        CompanyScoreSnapshot.objects.create(
            profile=profile, date=datetime.date.today(), trigger='seed',
            total_score=61.0)

        self.assertIsNotNone(seed_lineage_reason(profile))


class L_M_NothingIsFabricated(TestCase):

    def setUp(self):
        self.profile = _profile('no-fabrication')
        _run('--apply')

    def test_l_observed_at_stays_null(self):
        """
        The backfill time is not the observation time, and nothing here knows
        when the original observation was made.
        """
        self.assertEqual(
            CompanyMetricProvenance.objects.exclude(observed_at__isnull=True).count(), 0)

    def test_m_no_human_review_is_fabricated(self):
        rows = CompanyMetricProvenance.objects.all()

        self.assertEqual(rows.exclude(reviewed_by__isnull=True).count(), 0)
        self.assertEqual(rows.exclude(reviewed_at__isnull=True).count(), 0)
        self.assertEqual(rows.exclude(review_status='proposed').count(), 0)

    def test_m_no_confidence_is_fabricated(self):
        self.assertEqual(
            CompanyMetricProvenance.objects.exclude(confidence__isnull=True).count(), 0)

    def test_m_no_evidence_is_fabricated(self):
        self.assertEqual(
            CompanyMetricProvenance.objects.exclude(evidence__isnull=True).count(), 0)

    def test_m_classification_is_never_marked_verified(self):
        for row in CompanyMetricProvenance.objects.all():
            with self.subTest(metric=row.metric_key):
                self.assertNotIn(row.review_status, ('confirmed', 'verified'))


class N_TransactionPolicy(TestCase):
    """
    N — the unit of work is the COMPANY: all-or-nothing per company, independent
    across companies.
    """

    def test_n_one_company_failing_does_not_stop_the_others(self):
        from unittest.mock import patch

        good = _profile('good-company')
        bad = _profile('bad-company')

        real = CompanyMetricProvenance.objects.bulk_create

        def explode_for_bad(objs, *args, **kwargs):
            if objs and objs[0].company_id == bad.pk:
                raise RuntimeError('simulated failure')
            return real(objs, *args, **kwargs)

        with patch.object(CompanyMetricProvenance.objects, 'bulk_create',
                          side_effect=explode_for_bad):
            output = _run('--apply')

        self.assertEqual(
            CompanyMetricProvenance.objects.filter(company=good).count(),
            len(prov.VALID_METRIC_KEYS))
        self.assertEqual(
            CompanyMetricProvenance.objects.filter(company=bad).count(), 0,
            'the failed company must be all-or-nothing, not half written')
        self.assertIn('Errors                             1', output)

    def test_n_errors_are_reported_not_swallowed(self):
        from unittest.mock import patch

        _profile('will-fail')

        with patch.object(CompanyMetricProvenance.objects, 'bulk_create',
                          side_effect=RuntimeError('boom')):
            output = _run('--apply')

        self.assertIn('Errors                             1', output)
        self.assertIn('Rows written                       0', output)


class O_ReportingAndRollback(TestCase):

    def setUp(self):
        self.profile = _profile('reporting')

    def test_o_counts_are_accurate(self):
        output = _run('--apply')
        n = len(prov.VALID_METRIC_KEYS)

        self.assertIn('Companies scanned                  1', output)
        self.assertIn(f'Metrics scanned                    {n}', output)
        self.assertIn(f'Pairs considered                   {n}', output)
        self.assertIn(f'LEGACY_UNKNOWN_PROVENANCE          {n}', output)
        self.assertIn(f'Rows written                       {n}', output)

    def test_o_counts_reflect_a_mixed_estate(self):
        prov.record(self.profile, 'audit_quality_score', PROVENANCE_MEASURED,
                    written_by='analyst_review')

        output = _run('--apply')
        n = len(prov.VALID_METRIC_KEYS)

        self.assertIn('Existing provenance skipped        1', output)
        self.assertIn(f'LEGACY_UNKNOWN_PROVENANCE          {n - 1}', output)
        # UNKNOWN stays 0 on this estate: no score column is nullable yet, so no
        # profile can actually hold a missing value. That changes at D4.
        self.assertIn('UNKNOWN candidates                 0', output)

    def test_o_rollback_removes_only_backfill_rows(self):
        prov.record(self.profile, 'audit_quality_score', PROVENANCE_MEASURED,
                    written_by='analyst_review')
        _run('--apply')

        _run('--rollback', '--apply')

        remaining = CompanyMetricProvenance.objects.all()
        self.assertEqual(remaining.count(), 1)
        self.assertEqual(remaining.first().written_by, 'analyst_review')

    def test_o_rollback_dry_run_deletes_nothing(self):
        _run('--apply')
        before = CompanyMetricProvenance.objects.count()

        _run('--rollback')

        self.assertEqual(CompanyMetricProvenance.objects.count(), before)

    def test_o_backfill_is_re_runnable_after_rollback(self):
        _run('--apply')
        _run('--rollback', '--apply')
        _run('--apply')

        self.assertEqual(
            CompanyMetricProvenance.objects.filter(written_by=WRITER).count(),
            len(prov.VALID_METRIC_KEYS))


class DeploymentSafety(TestCase):
    """
    STEP 17 — labelling 3000 rows is an operator decision, not a deploy side
    effect. Asserted rather than trusted to review.
    """

    def test_the_backfill_is_not_invoked_by_any_deploy_script(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        for script in ('start.sh', 'predeploy.sh', 'build.sh'):
            path = root / script
            if not path.exists():
                continue
            with self.subTest(script=script):
                self.assertNotIn('backfill_metric_provenance', path.read_text())

    def test_no_migration_invokes_the_backfill(self):
        from pathlib import Path

        migrations = (Path(__file__).resolve().parent / 'migrations')
        for path in migrations.glob('*.py'):
            with self.subTest(migration=path.name):
                self.assertNotIn('backfill_metric_provenance', path.read_text())
