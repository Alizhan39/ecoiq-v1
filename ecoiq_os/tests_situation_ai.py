"""Internal optional AI mode: only source-grounded questions, never religious rulings."""
import json
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from api.models import ProcessAnalysisRun
from ecoiq_os.situation_ai import prepare_research_situation
from evidence_memory.models import EvidenceMemory
from gold_intelligence.models import GoldProject, ProjectMembership


class SituationAIResearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(
            name="Synthetic Stage 9 site", slug="stage9-synthetic",
            commodity="infrastructure", is_demo=False,
        )
        cls.other = GoldProject.objects.create(
            name="Private site elsewhere", slug="stage9-other",
            commodity="infrastructure", is_demo=False,
        )
        model = get_user_model()
        cls.analyst = model.objects.create_user(username="stage9-analyst")
        cls.reviewer = model.objects.create_user(username="stage9-reviewer")
        cls.viewer = model.objects.create_user(username="stage9-viewer")
        ProjectMembership.objects.create(
            project=cls.project, user=cls.analyst,
            role=ProjectMembership.Role.ANALYST,
        )
        ProjectMembership.objects.create(
            project=cls.project, user=cls.viewer,
            role=ProjectMembership.Role.VIEWER,
        )
        cls.analysis = ProcessAnalysisRun.objects.create(
            project=cls.project, created_by=cls.analyst,
            case_id="SYN-9", domain="construction", process_name="Fictional materials",
            resource_type="material", period="2026-10", unit="kg",
            file_fingerprint="9" * 64,
            summary={"kpi": {"numerator": 120, "denominator": 1000}},
        )

    def source(self):
        return EvidenceMemory.objects.create(
            project=self.project, visibility="project_private",
            verification_status="verified", review_tier="independently_verified",
            reviewer=self.reviewer, is_demo=False,
            source_type="manual", source_reference="fake:receipt-log",
            text_chunk="A signed synthetic ledger recorded receipt of 1000 kg.",
        )

    def test_no_reviewed_sources_or_consent_never_contact_provider(self):
        gateway = Mock()
        with override_settings(ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=True):
            no_sources = prepare_research_situation(
                project=self.project, user=self.analyst, run=self.analysis,
                external_transfer_approved=True, gateway=gateway,
            )
        self.assertEqual(no_sources["status"], "NO_REVIEWED_SOURCES")
        self.source()
        with override_settings(ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=True):
            no_consent = prepare_research_situation(
                project=self.project, user=self.analyst, run=self.analysis,
                external_transfer_approved=False, gateway=gateway,
            )
        self.assertEqual(no_consent["status"], "EXTERNAL_MODEL_DISABLED")
        self.assertFalse(no_consent["model_called"])
        gateway.chat.assert_not_called()

    def test_only_independent_flag_plus_consent_may_generate_untested_questions(self):
        self.source()
        gateway = Mock()
        gateway.chat.return_value = {"answer": json.dumps({"questions": [{
            "question": "Could date cutoffs explain the reported quantity gap?",
            "citations": [{"key": "S1", "quote": "recorded receipt of 1000 kg"}],
        }]})}
        with override_settings(ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=True):
            result = prepare_research_situation(
                project=self.project, user=self.analyst, run=self.analysis,
                external_transfer_approved=True, gateway=gateway,
            )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertTrue(result["model_called"])
        self.assertEqual(result["ai_questions"][0]["status"], "UNTESTED")
        self.assertEqual(result["ai_questions"][0]["citations"][0]["key"], "S1")
        self.assertFalse(result["implementation_permitted"])
        self.assertFalse(result["approval_recorded"])
        self.assertIsNone(result["shariah_verdict"])
        self.assertEqual(result["religious_research_status"], "SCHOLAR_REVIEW_REQUIRED")
        self.assertEqual(gateway.chat.call_count, 1)

    def test_viewer_and_cross_project_fail_without_draft_or_model(self):
        gateway = Mock()
        for user, project in [(self.viewer, self.project),
                              (self.analyst, self.other)]:
            result = prepare_research_situation(
                project=project, user=user, run=self.analysis,
                external_transfer_approved=True, gateway=gateway,
            )
            self.assertEqual(result, {"status": "ACCESS_DENIED", "model_called": False})
        gateway.chat.assert_not_called()

    def test_fake_cached_savings_or_religious_approval_not_trusted(self):
        self.source()
        self.analysis.summary["savings_forecast"] = 400000
        self.analysis.summary["shariah_verdict"] = "approved"
        self.analysis.save(update_fields=["summary"])
        gateway = Mock()
        result = prepare_research_situation(
            project=self.project, user=self.analyst, run=self.analysis,
            gateway=gateway,
        )
        self.assertIsNone(result["shariah_verdict"])
        self.assertIsNone(result["situation_guidance"]["safety_constraints"]["savings_forecast"])
        gateway.chat.assert_not_called()
