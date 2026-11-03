"""Project isolation and honest provenance labels for candidate KPI sources."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import TestCase
from django.utils import timezone

from api.models import ProcessAnalysisRun
from api.process_kpi_evidence_readiness import inspect_candidate_source
from evidence_memory.models import EvidenceMemory
from gold_intelligence.models import GoldProject, ProjectMembership


class ProcessKPISourceReadinessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(
            name="Research project one", slug="evidence-readiness-project-one",
            commodity="infrastructure", is_demo=False,
        )
        cls.other_project = GoldProject.objects.create(
            name="Research project two", slug="evidence-readiness-project-two",
            commodity="infrastructure", is_demo=False,
        )
        cls.analyst = get_user_model().objects.create_user(username="evidence-gate-analyst")
        cls.viewer = get_user_model().objects.create_user(username="evidence-gate-viewer")
        cls.stranger = get_user_model().objects.create_user(username="evidence-gate-stranger")
        cls.reviewer = get_user_model().objects.create_user(username="evidence-gate-reviewer")
        ProjectMembership.objects.create(
            project=cls.project, user=cls.analyst, role="analyst",
        )
        ProjectMembership.objects.create(
            project=cls.project, user=cls.viewer, role="viewer",
        )
        cls.analysis_run = ProcessAnalysisRun.objects.create(
            project=cls.project, created_by=cls.analyst, case_id="TEST",
            domain="research", process_name="Illustrative test process",
            resource_type="material", period="2026-10", unit="kg",
            file_fingerprint="e" * 64, summary={},
        )

    def _memory(self, **overrides):
        values = {
            "text_chunk": "Synthetic document fixture — not a verified KPI measurement.",
            "project": self.project,
            "visibility": "project_private",
            "source_reference": "harvester.Evidence:900",
            "verification_status": "verified",
            "review_tier": "independently_verified",
            "reviewer": self.reviewer,
            "is_demo": False,
        }
        values.update(overrides)
        return EvidenceMemory.objects.create(**values)

    def _check(self, memory, *, user=None, project=None, run=None, formula="revenue",
               input_key="reported_revenue"):
        return inspect_candidate_source(
            user=user or self.analyst, project=project or self.project,
            run_id=run.pk if run is not None else self.analysis_run.pk,
            formula_key=formula, input_key=input_key,
            evidence_memory_id=memory.pk,
        )

    def test_review_metadata_does_not_authenticate_a_numeric_measurement(self):
        result = self._check(self._memory())
        self.assertEqual(result["source_record_status"], "REVIEW_METADATA_PRESENT")
        self.assertTrue(result["source_record_reviewed_metadata"])
        self.assertFalse(result["observed_measurement_verified"])
        self.assertFalse(result["source_value_and_period_bound"])
        self.assertFalse(result["formula_approved"])
        self.assertEqual(result["expected_unit"], "GBP")
        self.assertNotIn("text_chunk", result)
        self.assertNotIn("source_reference", result)

    def test_project_analyst_required_not_viewer_or_stranger(self):
        memory = self._memory()
        for user in (self.viewer, self.stranger, None):
            with self.subTest(user=user), self.assertRaises(PermissionDenied):
                inspect_candidate_source(
                    user=user, project=self.project, run_id=self.analysis_run.pk,
                    formula_key="revenue", input_key="reported_revenue",
                    evidence_memory_id=memory.pk,
                )

    def test_cross_project_and_unknown_evidence_do_not_leak(self):
        external = self._memory(project=self.other_project)
        result = self._check(external)
        self.assertEqual(result["source_record_status"], "NOT_ACCESSIBLE_OR_NOT_FOUND")
        self.assertFalse(result["source_record_reviewed_metadata"])
        missing = inspect_candidate_source(
            user=self.analyst, project=self.project, run_id=self.analysis_run.pk,
            formula_key="revenue", input_key="reported_revenue",
            evidence_memory_id=999999999,
        )
        self.assertEqual(result, missing)

    def test_missing_source_and_review_or_expiry_never_pass(self):
        for overrides, status in (
            ({"source_reference": "", "source_url": ""}, "MISSING_SOURCE_PROVENANCE"),
            ({"verification_status": "pending"}, "SOURCE_REVIEW_INCOMPLETE"),
            ({"review_tier": "uploaded"}, "SOURCE_REVIEW_INCOMPLETE"),
            ({"reviewer": None}, "SOURCE_REVIEW_INCOMPLETE"),
            ({"is_demo": True}, "DEMONSTRATION_SOURCE"),
            ({"verification_status": "rejected"}, "NOT_ACCESSIBLE_OR_NOT_FOUND"),
            ({"expiry_date": timezone.now().date() - timedelta(days=1)}, "EXPIRED_SOURCE"),
        ):
            with self.subTest(status=status, overrides=overrides):
                result = self._check(self._memory(**overrides))
                self.assertEqual(result["source_record_status"], status)
                self.assertFalse(result["source_record_reviewed_metadata"])
                self.assertFalse(result["observed_measurement_verified"])

    def test_modified_text_without_matching_integrity_hash_fails(self):
        memory = self._memory()
        EvidenceMemory.objects.filter(pk=memory.pk).update(text_chunk="Text replaced after review")
        self.assertEqual(
            self._check(memory)["source_record_status"], "INTEGRITY_REFERENCE_MISMATCH",
        )

    def test_incorrect_run_or_parameter_and_ids_fail_closed(self):
        memory = self._memory()
        for formula, input_key in (("unknown", "reported_revenue"),
                                   ("revenue", "not_declared")):
            with self.subTest(formula=formula), self.assertRaises(ValueError):
                self._check(memory, formula=formula, input_key=input_key)
        with self.assertRaises(ValueError):
            inspect_candidate_source(
                user=self.analyst, project=self.project, run_id=True,
                formula_key="revenue", input_key="reported_revenue",
                evidence_memory_id=memory.pk,
            )
        with self.assertRaises(Http404):
            inspect_candidate_source(
                user=self.analyst, project=self.project, run_id=self.analysis_run.pk + 900,
                formula_key="revenue", input_key="reported_revenue",
                evidence_memory_id=memory.pk,
            )
