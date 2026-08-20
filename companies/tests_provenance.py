"""
D3A — provenance foundation.

Covers A–M from the brief. D3 answers one question — *where did this value come
from?* — and these tests are as much about what it must NOT do as what it does.

Two invariants matter more than the rest:

  * There is no implicit MEASURED. A value whose origin nobody stated must not
    acquire the strongest claim in the vocabulary by default (test B).
  * SEEDED never satisfies public eligibility, enforced in code rather than only
    in prose (test D). "Synthetic data may exercise the system. It must not
    impersonate evidence."
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from companies import provenance as prov
from companies.evidence import (
    EVIDENCED_PROVENANCE, PROVENANCE_CHOICES, PROVENANCE_ESTIMATED,
    PROVENANCE_INFERRED, PROVENANCE_MEASURED, PROVENANCE_MODELLED,
    PROVENANCE_NO_VALUE, PROVENANCE_SEEDED, PROVENANCE_UNKNOWN,
    UNEVIDENCED_PROVENANCE,
)
from companies.models import CompanyMetricProvenance, CompanyProfile
from league.models import Company


def _profile(slug):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    return CompanyProfile.objects.create(company=company, status='public')


class A_CanonicalStates(SimpleTestCase):

    def test_a_all_seven_canonical_states_exist(self):
        codes = {code for code, _ in PROVENANCE_CHOICES}

        self.assertEqual(codes, {
            'MEASURED', 'ESTIMATED', 'MODELLED', 'INFERRED',
            'SEEDED', 'LEGACY_UNKNOWN_PROVENANCE', 'UNKNOWN',
        })

    def test_a_the_brief_synthetic_state_is_this_repository_seeded(self):
        """
        The brief asked whether SYNTHETIC should be a seventh state. The
        repository had already made that decision in D1 and called it SEEDED.
        Adding SYNTHETIC beside it would be the duplicate vocabulary D3 exists
        to avoid.
        """
        codes = {code for code, _ in PROVENANCE_CHOICES}

        self.assertIn(PROVENANCE_SEEDED, codes)
        self.assertNotIn('SYNTHETIC', codes)

    def test_a_legacy_and_no_value_are_distinct_states(self):
        """
        Not synonyms. LEGACY_UNKNOWN_PROVENANCE means a number exists whose
        lineage we cannot reconstruct; UNKNOWN means there is no number.
        Collapsing them would undo three PRs of D2 work.
        """
        self.assertNotEqual(PROVENANCE_UNKNOWN, PROVENANCE_NO_VALUE)
        self.assertEqual(PROVENANCE_UNKNOWN, 'LEGACY_UNKNOWN_PROVENANCE')
        self.assertEqual(PROVENANCE_NO_VALUE, 'UNKNOWN')

    def test_a_evidenced_and_unevidenced_partition_the_vocabulary(self):
        """
        Every state must fall on one side. Adding an eighth without classifying
        it fails here rather than silently defaulting to publishable.
        """
        codes = {code for code, _ in PROVENANCE_CHOICES}

        self.assertEqual(EVIDENCED_PROVENANCE | UNEVIDENCED_PROVENANCE, codes)
        self.assertEqual(EVIDENCED_PROVENANCE & UNEVIDENCED_PROVENANCE, frozenset())


class B_NoImplicitMeasured(TestCase):
    """The single most important guarantee in D3A."""

    def setUp(self):
        self.profile = _profile('no-implicit')

    def test_b_origin_has_no_model_default(self):
        field = CompanyMetricProvenance._meta.get_field('origin')

        self.assertFalse(field.has_default(),
                         'a default origin would be a claim nobody made')

    def test_b_a_metric_with_no_row_is_not_measured(self):
        self.assertIsNone(prov.current(self.profile, 'anti_corruption_score'))

    def test_b_a_metric_with_no_row_is_not_publicly_defensible(self):
        self.assertFalse(
            prov.is_publicly_defensible(self.profile, 'anti_corruption_score'))

    def test_b_every_material_metric_starts_unrecorded(self):
        """The honest starting state for the whole estate."""
        self.assertEqual(sorted(prov.unrecorded_metrics(self.profile)),
                         sorted(prov.VALID_METRIC_KEYS))

    def test_b_an_invalid_origin_is_rejected(self):
        with self.assertRaises(ValueError):
            prov.record(self.profile, 'anti_corruption_score', 'PROBABLY_FINE')


class C_D_HistoricalAndSynthetic(TestCase):

    def setUp(self):
        self.profile = _profile('legacy-synth')

    def test_c_legacy_provenance_is_representable(self):
        row = prov.record(self.profile, 'anti_corruption_score', PROVENANCE_UNKNOWN)

        self.assertEqual(row.origin, PROVENANCE_UNKNOWN)
        self.assertTrue(row.is_current)

    def test_c_legacy_is_not_publicly_defensible(self):
        prov.record(self.profile, 'anti_corruption_score', PROVENANCE_UNKNOWN)

        self.assertFalse(
            prov.is_publicly_defensible(self.profile, 'anti_corruption_score'))

    def test_c_no_value_provenance_is_representable(self):
        row = prov.record(self.profile, 'water_impact_score', PROVENANCE_NO_VALUE)

        self.assertEqual(row.origin, PROVENANCE_NO_VALUE)
        self.assertFalse(
            prov.is_publicly_defensible(self.profile, 'water_impact_score'))

    def test_d_synthetic_is_representable_as_seeded(self):
        row = prov.record(self.profile, 'jobs_created_score', PROVENANCE_SEEDED,
                          written_by='seed_companies')

        self.assertEqual(row.origin, PROVENANCE_SEEDED)
        self.assertEqual(row.written_by, 'seed_companies')

    def test_d_seeded_never_satisfies_public_eligibility(self):
        """
        Enforced by code, not only by documentation — the brief's STEP 7.
        "Synthetic data may exercise the system. It must not impersonate
        evidence."
        """
        self.profile.jobs_created_score = 72.0
        self.profile.save()
        prov.record(self.profile, 'jobs_created_score', PROVENANCE_SEEDED)

        self.assertIsNotNone(self.profile.jobs_created_score)
        self.assertFalse(
            prov.is_publicly_defensible(self.profile, 'jobs_created_score'),
            'a real-looking number with SEEDED provenance must not be publishable',
        )

    def test_d_every_unevidenced_state_is_rejected_by_the_hook(self):
        for origin in sorted(UNEVIDENCED_PROVENANCE):
            with self.subTest(origin=origin):
                prov.record(self.profile, 'audit_quality_score', origin)
                self.assertFalse(
                    prov.is_publicly_defensible(self.profile, 'audit_quality_score'))

    def test_every_evidenced_state_is_accepted_by_the_hook(self):
        """The mirror — the hook must not reject everything."""
        self.profile.audit_quality_score = 61.0
        self.profile.save()

        for origin in sorted(EVIDENCED_PROVENANCE):
            with self.subTest(origin=origin):
                prov.record(self.profile, 'audit_quality_score', origin)
                self.assertTrue(
                    prov.is_publicly_defensible(self.profile, 'audit_quality_score'))


class E_F_RealValuesKeepTheirProvenance(TestCase):
    """
    E/F — the whole D2 programme in one place. Provenance must never be inferred
    from the number, so 0 and 50 must both be able to be MEASURED.
    """

    def setUp(self):
        self.profile = _profile('real-values')

    def test_e_a_genuine_zero_can_be_measured(self):
        self.profile.anti_corruption_score = 0.0
        self.profile.save()
        row = prov.record(self.profile, 'anti_corruption_score', PROVENANCE_MEASURED)

        self.assertEqual(row.value, 0.0)
        self.assertEqual(row.origin, PROVENANCE_MEASURED)
        self.assertTrue(
            prov.is_publicly_defensible(self.profile, 'anti_corruption_score'),
            'a measured zero is a finding and is publishable',
        )

    def test_f_a_genuine_fifty_can_be_measured(self):
        self.profile.anti_corruption_score = 50.0
        self.profile.save()
        row = prov.record(self.profile, 'anti_corruption_score', PROVENANCE_MEASURED)

        self.assertEqual(row.value, 50.0)
        self.assertTrue(
            prov.is_publicly_defensible(self.profile, 'anti_corruption_score'))

    def test_provenance_is_never_inferred_from_the_value(self):
        """
        50 does not imply unknown; 72 does not imply modelled; 0 does not imply
        measured. Same number, three different origins, all valid.
        """
        for origin in (PROVENANCE_MEASURED, PROVENANCE_MODELLED, PROVENANCE_SEEDED):
            with self.subTest(origin=origin):
                self.profile.anti_corruption_score = 50.0
                self.profile.save()
                row = prov.record(self.profile, 'anti_corruption_score', origin)
                self.assertEqual(row.origin, origin)
                self.assertEqual(row.value, 50.0)

    def test_a_measured_row_over_a_null_field_is_not_defensible(self):
        """
        A contradiction: an origin can only defend a value that exists. The safe
        reading of a contradiction is that there is nothing to publish.
        """
        self.profile.anti_corruption_score = None
        prov.record(self.profile, 'anti_corruption_score', PROVENANCE_MEASURED)

        self.assertFalse(
            prov.is_publicly_defensible(self.profile, 'anti_corruption_score'))

    def test_the_value_is_resolved_not_copied(self):
        """
        No second copy to drift. Change the field, and provenance reports the
        new number without being rewritten.
        """
        self.profile.anti_corruption_score = 40.0
        self.profile.save()
        row = prov.record(self.profile, 'anti_corruption_score', PROVENANCE_MEASURED)
        self.assertEqual(row.value, 40.0)

        self.profile.anti_corruption_score = 88.0
        self.profile.save()
        row.refresh_from_db()

        self.assertEqual(row.value, 88.0)
        self.assertFalse(hasattr(row, 'stored_value'))


class G_H_Isolation(TestCase):
    """G/H — provenance is metric-specific and company-specific."""

    def setUp(self):
        self.profile = _profile('iso-a')
        self.other = _profile('iso-b')

    def test_g_provenance_is_metric_specific(self):
        prov.record(self.profile, 'anti_corruption_score', PROVENANCE_MEASURED)

        self.assertIsNotNone(prov.current(self.profile, 'anti_corruption_score'))
        self.assertIsNone(prov.current(self.profile, 'water_impact_score'))

    def test_g_recording_one_metric_does_not_disturb_another(self):
        prov.record(self.profile, 'anti_corruption_score', PROVENANCE_MEASURED)
        prov.record(self.profile, 'water_impact_score', PROVENANCE_MODELLED)

        self.assertEqual(
            prov.current(self.profile, 'anti_corruption_score').origin,
            PROVENANCE_MEASURED)
        self.assertEqual(
            prov.current(self.profile, 'water_impact_score').origin,
            PROVENANCE_MODELLED)

    def test_h_one_company_provenance_does_not_leak_to_another(self):
        prov.record(self.profile, 'anti_corruption_score', PROVENANCE_MEASURED)

        self.assertIsNone(prov.current(self.other, 'anti_corruption_score'))
        self.assertFalse(
            prov.is_publicly_defensible(self.other, 'anti_corruption_score'))

    def test_h_current_map_is_scoped_to_one_company(self):
        prov.record(self.profile, 'anti_corruption_score', PROVENANCE_MEASURED)
        prov.record(self.other, 'water_impact_score', PROVENANCE_SEEDED)

        self.assertEqual(set(prov.current_map(self.profile)), {'anti_corruption_score'})
        self.assertEqual(set(prov.current_map(self.other)), {'water_impact_score'})


class I_EvidenceRelationship(TestCase):

    def setUp(self):
        self.profile = _profile('evidence-link')

    def _evidence(self):
        from evidence_memory.models import EvidenceMemory

        return EvidenceMemory.objects.create(
            text_chunk='Independently audited emissions inventory, FY2025.',
            source_url='https://example.org/report.pdf',
            source_type='company_report',
        )

    def test_i_provenance_can_reference_real_evidence(self):
        evidence = self._evidence()
        row = prov.record(self.profile, 'audit_quality_score',
                          PROVENANCE_MEASURED, evidence=evidence)

        self.assertEqual(row.evidence, evidence)
        self.assertEqual(row.evidence.source_url, 'https://example.org/report.pdf')

    def test_i_evidence_is_referenced_not_duplicated(self):
        """
        Source URL, type, verification status and reviewer already live on
        EvidenceMemory. Copying them here would create two records free to drift.
        """
        local_fields = {f.name for f in CompanyMetricProvenance._meta.get_fields()}

        for duplicated in ('source_url', 'source_type', 'verification_status',
                           'review_tier', 'expiry_date'):
            with self.subTest(field=duplicated):
                self.assertNotIn(duplicated, local_fields)

    def test_i_losing_the_evidence_does_not_erase_the_provenance(self):
        """
        SET_NULL, not CASCADE. That the value once had a stated origin is itself
        a fact worth keeping.
        """
        evidence = self._evidence()
        row = prov.record(self.profile, 'audit_quality_score',
                          PROVENANCE_MEASURED, evidence=evidence)
        evidence.delete()
        row.refresh_from_db()

        self.assertIsNone(row.evidence)
        self.assertEqual(row.origin, PROVENANCE_MEASURED)


class J_ConfidenceMayBeUnknown(TestCase):

    def setUp(self):
        self.profile = _profile('confidence')

    def test_j_confidence_is_nullable_with_no_default(self):
        field = CompanyMetricProvenance._meta.get_field('confidence')

        self.assertTrue(field.null)
        self.assertFalse(field.has_default(),
                         'a default confidence is the fabrication D2 removed')

    def test_j_unknown_confidence_is_null_not_fifty(self):
        row = prov.record(self.profile, 'audit_quality_score', PROVENANCE_MEASURED)

        self.assertIsNone(row.confidence)
        self.assertNotEqual(row.confidence, 50.0)

    def test_j_a_genuine_zero_confidence_is_distinguishable_from_unknown(self):
        zero = prov.record(self.profile, 'audit_quality_score',
                           PROVENANCE_MEASURED, confidence=0.0)
        self.assertEqual(zero.confidence, 0.0)

        unknown = prov.record(self.profile, 'audit_quality_score',
                              PROVENANCE_MEASURED)
        self.assertIsNone(unknown.confidence)


class K_ReviewIsSeparateFromOrigin(TestCase):

    def setUp(self):
        self.profile = _profile('review')

    def test_k_measured_is_not_auto_reviewed(self):
        row = prov.record(self.profile, 'audit_quality_score', PROVENANCE_MEASURED)

        self.assertEqual(row.review_status, 'proposed')
        self.assertIsNone(row.reviewed_by)
        self.assertIsNone(row.reviewed_at)

    def test_k_modelled_is_not_auto_distrusted(self):
        """A model output is not untrustworthy by construction."""
        modelled = prov.record(self.profile, 'audit_quality_score',
                               PROVENANCE_MODELLED, review_status='confirmed')

        self.assertEqual(modelled.review_status, 'confirmed')

    def test_k_origin_and_review_vary_independently(self):
        user = get_user_model().objects.create(username='reviewer')
        now = timezone.now()

        for origin in (PROVENANCE_MEASURED, PROVENANCE_MODELLED,
                       PROVENANCE_ESTIMATED, PROVENANCE_INFERRED):
            with self.subTest(origin=origin):
                row = prov.record(self.profile, 'audit_quality_score', origin,
                                  review_status='confirmed', reviewed_by=user,
                                  reviewed_at=now)
                self.assertEqual(row.origin, origin)
                self.assertEqual(row.review_status, 'confirmed')
                self.assertEqual(row.reviewed_by, user)

    def test_k_review_uses_the_existing_repository_vocabulary(self):
        """Not a sixth review enum."""
        from company_intelligence.models import CompanyKPIEvidenceLink

        states = {code for code, _ in CompanyKPIEvidenceLink.REVIEW_STATE_CHOICES}
        self.assertIn('proposed', states)
        self.assertIn('confirmed', states)


class L_InvalidCombinationsRejected(TestCase):

    def setUp(self):
        self.profile = _profile('invalid')

    def test_l_an_unknown_metric_key_is_rejected(self):
        with self.assertRaises(ValueError):
            prov.record(self.profile, 'env score', PROVENANCE_MEASURED)

    def test_l_a_near_miss_metric_name_is_rejected(self):
        """The exact failure mode the brief named: three spellings, one metric."""
        for wrong in ('environmental', 'environment_score', 'env_score'):
            with self.subTest(wrong=wrong):
                with self.assertRaises(ValueError):
                    prov.record(self.profile, wrong, PROVENANCE_MEASURED)

    def test_l_model_level_validation_catches_a_bypass_of_the_service(self):
        """A script writing the model directly must not evade validation."""
        row = CompanyMetricProvenance(
            company=self.profile, metric_key='not_a_metric',
            origin=PROVENANCE_MEASURED)

        with self.assertRaises(ValidationError):
            row.save()

    def test_l_an_unknown_metric_is_never_publicly_defensible(self):
        self.assertFalse(prov.is_publicly_defensible(self.profile, 'env score'))

    def test_l_only_one_current_row_per_company_and_metric(self):
        prov.record(self.profile, 'audit_quality_score', PROVENANCE_SEEDED)
        prov.record(self.profile, 'audit_quality_score', PROVENANCE_MEASURED)

        current = CompanyMetricProvenance.objects.filter(
            company=self.profile, metric_key='audit_quality_score', is_current=True)

        self.assertEqual(current.count(), 1)
        self.assertEqual(current.first().origin, PROVENANCE_MEASURED)

    def test_l_superseded_rows_are_kept_for_audit(self):
        """Append-only: the previous answer stays answerable."""
        prov.record(self.profile, 'audit_quality_score', PROVENANCE_SEEDED)
        prov.record(self.profile, 'audit_quality_score', PROVENANCE_MEASURED)

        rows = prov.history(self.profile, 'audit_quality_score')

        self.assertEqual(rows.count(), 2)
        self.assertEqual([r.origin for r in rows],
                         [PROVENANCE_MEASURED, PROVENANCE_SEEDED])
        self.assertEqual([r.is_current for r in rows], [True, False])


class M_MigrationSafety(TestCase):
    """
    M — the migration is additive and reversible.

    The forward/backward/forward cycle was also run against a disposable
    database before this PR; these assertions pin the properties that make that
    cycle safe, so a later edit to the migration cannot quietly break them.
    """

    def test_m_the_migration_only_creates(self):
        from importlib import import_module

        module = import_module('companies.migrations.0009_companymetricprovenance')
        operation_types = {type(op).__name__ for op in module.Migration.operations}

        self.assertEqual(operation_types, {'CreateModel'})
        for destructive in ('AlterField', 'RemoveField', 'DeleteModel', 'RenameField'):
            with self.subTest(operation=destructive):
                self.assertNotIn(destructive, operation_types)

    def test_m_no_existing_score_field_was_altered(self):
        """
        D3A must not touch the 39 score fields. Spot-checking the six composite
        pillars: still NOT NULL, still defaulted. Nullability is D4's decision,
        not a side effect of adding provenance.
        """
        for name in ('public_benefit_score', 'environmental_responsibility_score',
                     'modernization_score', 'transparency_anti_corruption_score',
                     'anti_corruption_score', 'ethical_alignment_score'):
            with self.subTest(field=name):
                field = CompanyProfile._meta.get_field(name)
                self.assertFalse(field.null, f'{name} became nullable — that is D4')
                self.assertTrue(field.has_default())

    def test_m_rollback_removes_only_the_new_table(self):
        module_deps = __import__(
            'companies.migrations.0009_companymetricprovenance',
            fromlist=['Migration']).Migration.dependencies

        self.assertIn(('companies', '0008_investmentrelevancereport'), module_deps)


class QueryPatterns(TestCase):
    """
    STEP 20 — provenance must not turn a company list into an N+1.

    D3A injects provenance into no existing page, but the helper a future page
    will reach for has to be the batched one, so it is asserted now.
    """

    def test_current_map_is_a_single_query(self):
        profile = _profile('n-plus-one')
        for metric in sorted(prov.VALID_METRIC_KEYS)[:6]:
            prov.record(profile, metric, PROVENANCE_MODELLED)

        with self.assertNumQueries(1):
            rows = prov.current_map(profile)

        self.assertEqual(len(rows), 6)

    def test_summarise_distinguishes_unrecorded_from_stated_unknown(self):
        """
        Two different facts: "nobody has said where this came from" and "we have
        said there is no value". Reporting them as one number would hide how
        much of the estate D3B still has to label.
        """
        profile = _profile('summary')
        profile.water_impact_score = None
        prov.record(profile, 'audit_quality_score', PROVENANCE_MEASURED)

        summary = prov.summarise(profile)

        self.assertEqual(summary['total_metrics'], len(prov.VALID_METRIC_KEYS))
        self.assertEqual(summary['by_origin'].get(PROVENANCE_MEASURED), 1)
        self.assertGreater(summary['unrecorded_with_value'], 0)
        self.assertEqual(summary['by_origin'].get(PROVENANCE_NO_VALUE), 1)


class PublicSurfacesUnchanged(TestCase):
    """
    D3A is infrastructure. It must not have moved anything the user can see.
    """

    def test_public_eligibility_is_unchanged_by_provenance(self):
        """
        is_publicly_defensible() is advisory in D3A. Recording MEASURED
        provenance must NOT make an unevidenced company's score appear.
        """
        from django.test import Client

        from companies.evidence import PENDING_HEADLINE

        company = Company.objects.create(name='Still Contained', slug='still-contained',
                                         country='UK', ecoiq_score=71.4)
        profile = CompanyProfile.objects.create(
            company=company, status='public', ecoiq_total_score=71.4)
        for metric in sorted(prov.VALID_METRIC_KEYS):
            prov.record(profile, metric, PROVENANCE_MEASURED)

        body = Client().get('/companies/still-contained/').content.decode()

        self.assertIn(PENDING_HEADLINE, body)
        self.assertNotIn('71.4', body)

    def test_api_v2_is_unchanged_by_provenance(self):
        from django.test import Client

        company = Company.objects.create(name='V2 Unchanged', slug='v2-unchanged',
                                         country='UK', ecoiq_score=71.4)
        profile = CompanyProfile.objects.create(
            company=company, status='public', ecoiq_total_score=71.4)
        prov.record(profile, 'audit_quality_score', PROVENANCE_MEASURED)

        payload = Client().get('/api/v2/companies/v2-unchanged/').json()

        self.assertIsNone(payload['ecoiq_score'])
        self.assertEqual(payload['score_status'], 'INSUFFICIENT_EVIDENCE')
        self.assertNotIn('provenance', payload,
                         'D3A must not expose provenance publicly yet')
