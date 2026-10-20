"""Geological provenance and gold KPI contracts, including access and no-claim gates."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from gold_intelligence.models import (
    GeologicalEvidenceSource, GoldAssayInterval, GoldDrillhole,
    GoldProject, MineKPIObservation, ProjectMembership,
)
from gold_intelligence.services.kpi_definitions import MINING_KPIS
from gold_intelligence.services.mine_kpis import evaluate_mine_kpi, mine_kpi_readiness
from gold_intelligence.services.mizan_bridge import build_gold_mizan_readiness
from mizan.system_balance import INSUFFICIENT_DATA


class GeologicalAndKPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user('geology-test-owner')
        cls.stranger = get_user_model().objects.create_user('geology-test-stranger')
        cls.project = GoldProject.objects.create(
            name='Geodata Project', slug='geodata-project', is_demo=False)
        cls.other_project = GoldProject.objects.create(
            name='Unrelated Gold Project', slug='unrelated-gold', is_demo=False)
        ProjectMembership.objects.create(
            project=cls.project, user=cls.owner, role=ProjectMembership.Role.VIEWER)

    def source(self, project=None, source_id='SRC-1', kind='operations', reviewed=False):
        source = GeologicalEvidenceSource.objects.create(
            project=project or self.project, source_id=source_id,
            title='A source with a hash', kind=kind, issuer='Independent Lab',
            citation='Document 01, version 1', licence_terms='Licensed for internal evaluation',
            content_sha256='a' * 64)
        if reviewed:
            source.review_state = 'reviewed'
            source.reviewer = self.owner
            source.reviewed_at = timezone.now()
            source.save()
        return source

    def kpi(self, source, **overrides):
        kwargs = dict(
            project=self.project, source=source, metric_key='gold_recovery_pct',
            period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
            numerator=Decimal('70'), denominator=Decimal('100'),
        )
        kwargs.update(overrides)
        return MineKPIObservation.objects.create(**kwargs)

    def hole(self, src, **overrides):
        kwargs = dict(
            project=self.project, source=src, hole_id='KZ-001',
            latitude=Decimal('49.123456'), longitude=Decimal('82.654321'),
            total_depth_m=Decimal('200.000'),
        )
        kwargs.update(overrides)
        return GoldDrillhole.objects.create(**kwargs)

    def test_registry_has_explicit_units_dimensions_and_versions(self):
        self.assertEqual(len(MINING_KPIS), 9)
        for metric in MINING_KPIS.values():
            self.assertTrue(metric.unit)
            self.assertTrue(metric.numerator)
            self.assertTrue(metric.denominator)
            self.assertEqual(metric.method_version, '1')

    def test_source_must_have_rights_citation_and_hash_to_be_reviewed(self):
        src = GeologicalEvidenceSource.objects.create(
            project=self.project, source_id='MISSING-SHA', title='Missing',
            issuer='Example', kind='assay')
        src.review_state = 'reviewed'
        src.reviewer, src.reviewed_at = self.owner, timezone.now()
        with self.assertRaises(ValidationError):
            src.save()
        src.content_sha256 = 'b' * 64
        src.citation = 'Original lab certificate'
        src.licence_terms = 'Document rights confirmed'
        src.save()
        self.assertEqual(src.review_state, 'reviewed')

    def test_synthetic_or_demo_evidence_never_reviewed(self):
        src = self.source()
        src.review_state = 'reviewed'
        src.is_synthetic = True
        src.reviewer, src.reviewed_at = self.owner, timezone.now()
        with self.assertRaises(ValidationError):
            src.save()

        demo = GoldProject.objects.create(name='demo', slug='geology-demo', is_demo=True)
        demo_src = self.source(project=demo, source_id='DEMO')
        demo_src.review_state = 'reviewed'
        demo_src.reviewer, demo_src.reviewed_at = self.owner, timezone.now()
        with self.assertRaises(ValidationError):
            demo_src.save()

    def test_reviewed_source_payload_is_frozen_until_reopened(self):
        src = self.source(reviewed=True)
        src.issuer = 'Replaced issuer'
        with self.assertRaises(ValidationError):
            src.save()
        src.review_state = 'pending'
        src.save()
        self.assertEqual(src.review_state, 'pending')

    def test_drillhole_rejects_cross_project_and_invalid_coordinates(self):
        src = self.source(kind='drill_log')
        with self.assertRaises(ValidationError):
            self.hole(src, project=self.other_project)
        with self.assertRaises(ValidationError):
            self.hole(src, latitude=Decimal('123'))
        hole = self.hole(src)
        self.assertEqual(hole.total_depth_m, Decimal('200'))
        self.assertEqual(hole.review_state, 'pending')

    def test_assay_rejects_missing_chain_of_custody_and_invalid_intervals(self):
        src = self.source(kind='drill_log')
        hole = self.hole(src)
        lab = self.source(source_id='LAB-1', kind='assay')
        with self.assertRaises(ValidationError):
            GoldAssayInterval.objects.create(
                project=self.project, source=lab, drillhole=hole,
                sample_id='BEYOND', from_m=190, to_m=201, au_g_per_t=2)
        with self.assertRaises(ValidationError):
            GoldAssayInterval.objects.create(
                project=self.other_project, source=lab, drillhole=hole,
                sample_id='FOREIGN', from_m=0, to_m=1, au_g_per_t=2)
        sample = GoldAssayInterval.objects.create(
            project=self.project, source=lab, drillhole=hole, sample_id='001',
            from_m=0, to_m=1, au_g_per_t=Decimal('0.000000'),
            laboratory='Test lab', certificate_id='CERT-01', sample_type='blank')
        self.assertEqual(sample.au_g_per_t, 0)  # actual measured zero is not missing
        sample.review_state = 'reviewed'
        sample.reviewer, sample.reviewed_at = self.owner, timezone.now()
        with self.assertRaises(ValidationError):
            sample.save()

    def test_kpi_calculated_but_unreviewed_is_not_publishable(self):
        src = self.source(reviewed=True)
        record = self.kpi(src)
        result = evaluate_mine_kpi(record)
        self.assertEqual(result['value'], Decimal('70.000000'))
        self.assertEqual(result['status'], 'KPI_REVIEW_REQUIRED')
        self.assertFalse(result['publishable'])
        record.review_state = 'reviewed'
        record.reviewer, record.reviewed_at = self.owner, timezone.now()
        record.save()
        evaluated = evaluate_mine_kpi(record)
        self.assertTrue(evaluated['publishable'])
        self.assertEqual(evaluated['status'], 'INTERNALLY_REVIEWED')
        self.assertEqual(evaluated['mizan_dimension'], 'resource_efficiency')
        self.assertEqual(build_gold_mizan_readiness(self.project)['assessment'].status, INSUFFICIENT_DATA)

    def test_zero_and_missing_are_different(self):
        src = self.source()
        record = self.kpi(src, numerator=Decimal('0.000'))
        result = evaluate_mine_kpi(record)
        self.assertEqual(result['value'], Decimal('0'))
        self.assertFalse(result['publishable'])
        record.numerator = None
        record.save()
        result = evaluate_mine_kpi(record)
        self.assertIsNone(result['value'])
        self.assertEqual(result['status'], 'MISSING_INPUT')

    def test_invalid_percent_and_zero_denominator_rejected(self):
        src = self.source()
        with self.assertRaises(ValidationError):
            self.kpi(src, numerator=101, denominator=100)
        with self.assertRaises(ValidationError):
            self.kpi(src, denominator=0)

    def test_reviewed_kpi_cannot_be_silently_changed(self):
        src = self.source(reviewed=True)
        k = self.kpi(src)
        k.review_state = 'reviewed'
        k.reviewer, k.reviewed_at = self.owner, timezone.now()
        k.save()
        k.numerator = Decimal('99')
        with self.assertRaises(ValidationError):
            k.save()

    def test_unreviewed_source_blocks_kpi_approval(self):
        src = self.source()
        k = self.kpi(src)
        k.review_state = 'reviewed'
        k.reviewer, k.reviewed_at = self.owner, timezone.now()
        with self.assertRaises(ValidationError):
            k.save()

    def test_local_water_safety_kpi_formulas_do_not_invent_values(self):
        src = self.source()
        k = self.kpi(src, metric_key='freshwater_m3_per_t',
                     numerator=Decimal('100'), denominator=Decimal('500'))
        result = evaluate_mine_kpi(k)
        self.assertEqual(result['value'], Decimal('0.200000'))
        self.assertEqual(result['unit'], 'm³/t')
        self.assertEqual(result['status'], 'SOURCE_REVIEW_REQUIRED')
        self.assertFalse(result['publishable'])

    def test_private_project_kpis_are_not_accessible_to_nonmembers(self):
        src = self.source()
        self.kpi(src)
        self.client.force_login(self.stranger)
        response = self.client.get(reverse('gold_intelligence:investor_view', args=[self.project.slug]))
        self.assertEqual(response.status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('gold_intelligence:investor_view', args=[self.project.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['mizan_readiness']['operational_kpis']['observed_count'], 1)
        self.assertContains(response, 'Mine operations')
        self.assertContains(response, 'KPI_REVIEW_REQUIRED')

    def test_never_mutates_resource_tonnes_or_other_financial_data(self):
        src = self.source()
        self.kpi(src)
        before = self.project.resource_tonnes
        output = mine_kpi_readiness(self.project)
        self.assertEqual(output['observed_count'], 1)
        self.project.refresh_from_db()
        self.assertEqual(self.project.resource_tonnes, before)
