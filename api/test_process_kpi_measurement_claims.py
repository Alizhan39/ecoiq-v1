"""Regression tests: source-linked KPI values remain reported, not verified."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import TestCase
from django.utils import timezone

from api.models import ProcessAnalysisRun, ProcessKPIMeasurementClaim
from api.process_kpi_measurement_claims import (
    claims_for_process, create_process_kpi_measurement_claim,
)
from evidence_memory.models import EvidenceMemory
from gold_intelligence.models import GoldProject, ProjectMembership


class KPIMeasurementClaimTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(
            name="Source binding project", slug="kpi-claim-source-project",
            commodity="other", is_demo=False,
        )
        cls.other = GoldProject.objects.create(
            name="Unrelated project", slug="kpi-claim-unrelated-project",
            commodity="other", is_demo=False,
        )
        user_model = get_user_model()
        cls.analyst = user_model.objects.create_user(username="kpi-claim-analyst")
        cls.viewer = user_model.objects.create_user(username="kpi-claim-viewer")
        cls.stranger = user_model.objects.create_user(username="kpi-claim-stranger")
        cls.reviewer = user_model.objects.create_user(username="kpi-claim-reviewer")
        ProjectMembership.objects.create(
            project=cls.project, user=cls.analyst, role="analyst",
        )
        ProjectMembership.objects.create(
            project=cls.project, user=cls.viewer, role="viewer",
        )
        cls.analysis_run = ProcessAnalysisRun.objects.create(
            project=cls.project, created_by=cls.analyst, case_id="CLAIM-CASE",
            domain="research", process_name="Source-linked KPI input",
            resource_type="material", period="2026-10", unit="kg",
            file_fingerprint="c" * 64, summary={},
        )

    def _source(self, **overrides):
        fields = {
            "text_chunk": "Synthetic source text for an illustrative revenue claim.",
            "project": self.project, "visibility": "project_private",
            "source_reference": "harvester.Evidence:9001",
            "verification_status": "verified",
            "review_tier": "independently_verified",
            "reviewer": self.reviewer, "is_demo": False,
        }
        fields.update(overrides)
        return EvidenceMemory.objects.create(**fields)

    def _create(self, source, *, user=None, run_id=None, formula_key="revenue",
                input_key="reported_revenue", reported_value="1250.25"):
        return create_process_kpi_measurement_claim(
            user=user if user is not None else self.analyst,
            project=self.project,
            run_id=run_id if run_id is not None else self.analysis_run.pk,
            evidence_memory_id=source.pk,
            formula_key=formula_key, input_key=input_key,
            reported_value=reported_value,
        )

    def test_saved_claim_is_traced_but_explicitly_unverified(self):
        source = self._source()
        claim = self._create(source)
        self.assertEqual(claim.project, self.project)
        self.assertEqual(claim.analysis, self.analysis_run)
        self.assertEqual(claim.evidence, source)
        self.assertEqual(claim.created_by, self.analyst)
        self.assertEqual(claim.formula_key, "revenue")
        self.assertEqual(claim.input_key, "reported_revenue")
        self.assertEqual(claim.value_decimal, Decimal("1250.25"))
        self.assertEqual(claim.unit, "GBP")
        self.assertEqual(claim.period, "2026-10")
        self.assertEqual(claim.source_chunk_sha256, source.integrity_reference)
        self.assertEqual(len(claim.formula_spec_sha256), 64)
        self.assertEqual(
            claim.review_status, ProcessKPIMeasurementClaim.ReviewStatus.REPORTED_NOT_VERIFIED,
        )
        self.assertFalse(hasattr(claim, "verified_value"))
        self.assertEqual(
            list(claims_for_process(user=self.viewer, project=self.project,
                                    run_id=self.analysis_run.pk)),
            [claim],
        )

    def test_repeat_submission_appends_a_new_claim_and_never_overwrites_old(self):
        source = self._source()
        first = self._create(source, reported_value="1250.25")
        second = self._create(source, reported_value="1300")
        self.assertNotEqual(first.pk, second.pk)
        first.refresh_from_db()
        self.assertEqual(first.value_decimal, Decimal("1250.25"))
        self.assertEqual(second.value_decimal, Decimal("1300"))
        self.assertEqual(first.formula_spec_sha256, second.formula_spec_sha256)

    def test_private_project_read_vs_analyst_write_permission(self):
        source = self._source()
        for user in (self.viewer, self.stranger):
            with self.subTest(user=user), self.assertRaises(PermissionDenied):
                self._create(source, user=user)
        with self.assertRaises(PermissionDenied):
            claims_for_process(user=self.stranger, project=self.project,
                               run_id=self.analysis_run.pk)
        self.assertEqual(ProcessKPIMeasurementClaim.objects.count(), 0)

    def test_source_from_other_project_is_not_usable_even_if_reviewed(self):
        source = self._source(project=self.other)
        with self.assertRaises(ValueError):
            self._create(source)
        self.assertFalse(ProcessKPIMeasurementClaim.objects.exists())

    def test_missing_or_foreign_analysis_must_fail_closed(self):
        source = self._source()
        with self.assertRaises(Http404):
            self._create(source, run_id=900000)
        other_run = ProcessAnalysisRun.objects.create(
            project=self.other, created_by=self.analyst, case_id="OTHER",
            domain="research", process_name="Other process", resource_type="material",
            period="2026-10", unit="kg", file_fingerprint="d" * 64, summary={},
        )
        with self.assertRaises(Http404):
            self._create(source, run_id=other_run.pk)

    def test_invalid_numeric_units_formula_inputs_and_precision_rejected(self):
        source = self._source()
        for val in ("NaN", "Infinity", "-1", "1e25", "1.1234567890123456789", 1.2, True):
            with self.subTest(value=val), self.assertRaises(ValueError):
                self._create(source, reported_value=val)
        for formula, input_key in (("revenue", "adjusted_reference_pay"),
                                   ("unlisted_formula", "reported_revenue")):
            with self.subTest(formula=formula), self.assertRaises(ValueError):
                self._create(source, formula_key=formula, input_key=input_key)
        self.assertFalse(ProcessKPIMeasurementClaim.objects.exists())

    def test_rejected_expired_demo_or_tampered_source_fails_closed(self):
        source = self._source(is_demo=True)
        with self.assertRaises(ValueError):
            self._create(source)
        source.is_demo = False
        source.expiry_date = timezone.now().date() - timedelta(days=1)
        source.save()
        with self.assertRaises(ValueError):
            self._create(source)
        source.expiry_date = None
        source.save()
        EvidenceMemory.objects.filter(pk=source.pk).update(text_chunk="Changed after review")
        with self.assertRaises(ValueError):
            self._create(source)
        self.assertFalse(ProcessKPIMeasurementClaim.objects.exists())

    def test_source_integrity_snapshot_is_not_rewritten_when_evidence_changes(self):
        source = self._source()
        claim = self._create(source)
        original_hash = claim.source_chunk_sha256
        source.text_chunk = "New document version"
        source.save()
        claim.refresh_from_db()
        self.assertEqual(claim.source_chunk_sha256, original_hash)
        self.assertNotEqual(claim.source_chunk_sha256, source.integrity_reference)
        self.assertEqual(claim.review_status, "REPORTED_NOT_VERIFIED")
