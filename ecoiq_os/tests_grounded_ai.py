"""Stage 6 access, citation, hallucination and gateway consent controls."""
import json
from datetime import date
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from api.models import ProcessAnalysisRun
from ecoiq_os.grounded_ai import (
    GroundedSource, collect_reviewed_sources, prepare_grounded_draft,
    validate_grounded_questions,
)
from evidence_memory.models import EvidenceMemory
from gold_intelligence.models import GoldProject, ProjectMembership


def model_json(quote="recorded receipt of 1000 kg", key="S1"):
    return json.dumps({
        "questions": [{
            "question": "Could stock cutoffs explain the reported discrepancy?",
            "citations": [{"key": key, "quote": quote}],
        }],
    })


@override_settings(ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=False)
class GroundedAIProjectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(
            name="Restricted construction pilot", slug="grounded-pilot",
            commodity="infrastructure", is_demo=False,
        )
        cls.other_project = GoldProject.objects.create(
            name="Other tenant", slug="grounded-other",
            commodity="infrastructure", is_demo=False,
        )
        user_model = get_user_model()
        cls.reviewer = user_model.objects.create_user(username="grounded-reviewer")
        cls.analyst = user_model.objects.create_user(username="grounded-analyst")
        cls.viewer = user_model.objects.create_user(username="grounded-viewer")
        cls.stranger = user_model.objects.create_user(username="grounded-stranger")
        for user, role in [
            (cls.analyst, ProjectMembership.Role.ANALYST),
            (cls.viewer, ProjectMembership.Role.VIEWER),
        ]:
            ProjectMembership.objects.create(
                project=cls.project, user=user, role=role,
            )
        cls.analysis = ProcessAnalysisRun.objects.create(
            project=cls.project, created_by=cls.analyst,
            case_id="CASE-001", domain="construction", process_name="Materials",
            resource_type="material", period="2026-10", unit="kg",
            file_fingerprint="e" * 64,
            summary={"kpi": {
                "numerator": 120, "denominator": 1000,
                "value": 12, "status": "REPORTED",
            }},
        )

    def add_source(self, *, project=None, **changes):
        fields = {
            "project": project or self.project,
            "visibility": "project_private",
            "source_type": "manual",
            "source_reference": "inspection_report:synthetic-001",
            "text_chunk": "A signed synthetic ledger recorded receipt of 1000 kg during October.",
            "verification_status": "verified",
            "review_tier": "independently_verified",
            "reviewer": self.reviewer,
            "is_demo": False,
        }
        fields.update(changes)
        return EvidenceMemory.objects.create(**fields)

    def test_no_sources_blocks_gateway_even_when_flagged_on(self):
        gateway = Mock()
        with override_settings(ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=True):
            out = prepare_grounded_draft(
                project=self.project, user=self.analyst, run=self.analysis,
                external_transfer_approved=True, gateway=gateway,
            )
        self.assertEqual(out["status"], "NO_REVIEWED_SOURCES")
        gateway.chat.assert_not_called()

    def test_no_model_call_by_default_and_manifest_has_real_sha(self):
        source = self.add_source()
        gateway = Mock()
        out = prepare_grounded_draft(
            project=self.project, user=self.analyst, run=self.analysis,
            external_transfer_approved=True, gateway=gateway,
        )
        self.assertEqual(out["status"], "EXTERNAL_MODEL_DISABLED")
        self.assertFalse(out["model_called"])
        self.assertEqual(out["source_manifest"][0]["memory_id"], source.pk)
        self.assertEqual(out["source_manifest"][0]["sha256"], source.integrity_reference)
        self.assertNotIn("text_chunk", str(out))
        gateway.chat.assert_not_called()

    def test_server_flag_alone_is_not_consent(self):
        self.add_source()
        gateway = Mock()
        with override_settings(ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=True):
            out = prepare_grounded_draft(
                project=self.project, user=self.analyst, run=self.analysis,
                external_transfer_approved=False, gateway=gateway,
            )
        self.assertEqual(out["status"], "EXTERNAL_MODEL_DISABLED")
        gateway.chat.assert_not_called()

    def test_explicitly_enabled_gateway_returns_only_exact_quote_questions(self):
        self.add_source()
        gateway = Mock()
        gateway.chat.return_value = {"answer": model_json()}
        with override_settings(ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=True):
            out = prepare_grounded_draft(
                project=self.project, user=self.analyst, run=self.analysis,
                external_transfer_approved=True, gateway=gateway,
            )
        self.assertEqual(out["status"], "REVIEW_REQUIRED")
        self.assertEqual(out["questions"][0]["status"], "UNTESTED")
        self.assertEqual(out["questions"][0]["citations"][0]["key"], "S1")
        self.assertFalse(out["implementation_permitted"])
        self.assertFalse(out["approval_recorded"])
        self.assertIsNone(out["causal_conclusion"])
        self.assertIsNone(out["savings_forecast"])
        self.assertFalse(out["independently_verified_causality"])
        self.assertEqual(ProcessAnalysisRun.objects.count(), 1)
        args = gateway.chat.call_args.kwargs
        self.assertEqual(args["context"]["module"], "ecoiq_os")
        self.assertIn("text_untrusted", args["message"])
        self.assertNotIn("source_reference", args["message"])

    def test_viewer_stranger_revoked_and_wrong_project_are_denied(self):
        self.add_source()
        gateway = Mock()
        for user in (self.viewer, self.stranger):
            out = prepare_grounded_draft(
                project=self.project, user=user, run=self.analysis,
                external_transfer_approved=True, gateway=gateway,
            )
            self.assertEqual(out["status"], "ACCESS_DENIED")
        other = prepare_grounded_draft(
            project=self.other_project, user=self.analyst, run=self.analysis,
            external_transfer_approved=True, gateway=gateway,
        )
        self.assertEqual(other["status"], "ACCESS_DENIED")
        ProjectMembership.objects.filter(
            project=self.project, user=self.analyst,
        ).update(is_active=False)
        self.assertEqual(collect_reviewed_sources(project=self.project, user=self.analyst), ())
        gateway.chat.assert_not_called()

    def test_source_cannot_cross_tenants_even_if_verified(self):
        self.add_source(project=self.other_project)
        self.assertEqual(collect_reviewed_sources(project=self.project, user=self.analyst), ())

    def test_excludes_fake_or_unreviewed_or_expired_sources(self):
        self.add_source(review_tier="uploaded")
        self.add_source(reviewer=None)
        self.add_source(verification_status="pending")
        self.add_source(is_demo=True)
        self.add_source(legal_status="disputed")
        self.add_source(expiry_date=date(2020, 1, 1))
        self.add_source(source_type="agent_output")
        self.add_source(source_reference="")
        self.add_source(visibility="restricted_unresolved")
        item = self.add_source()
        EvidenceMemory.objects.filter(pk=item.pk).update(text_chunk="tampered record")
        self.assertEqual(collect_reviewed_sources(project=self.project, user=self.analyst), ())

    def test_does_not_trust_stored_claim_of_verified_approval(self):
        self.add_source()
        self.analysis.summary["approval_recorded"] = True
        self.analysis.summary["causal_conclusion"] = "proven savings"
        self.analysis.save(update_fields=["summary"])
        gateway = Mock()
        gateway.chat.return_value = {"answer": model_json()}
        with override_settings(ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=True):
            out = prepare_grounded_draft(
                project=self.project, user=self.analyst, run=self.analysis,
                external_transfer_approved=True, gateway=gateway,
            )
        self.assertFalse(out["approval_recorded"])
        self.assertIsNone(out["causal_conclusion"])


class ModelCitationGateTests(TestCase):
    def setUp(self):
        self.refs = (GroundedSource(
            key="S1", memory_id=42, excerpt="A signed ledger recorded receipt of 1000 kg.",
            review_tier="independently_verified", content_sha256="a" * 64,
        ),)

    def test_accepts_exact_reference_and_still_requires_review(self):
        payload = validate_grounded_questions(model_json(), self.refs)
        self.assertEqual(payload["status"], "REVIEW_REQUIRED")
        self.assertEqual(payload["questions"][0]["citations"][0]["memory_id"], 42)
        self.assertFalse(payload["implementation_permitted"])

    def test_blocks_fake_source_and_fabricated_quote(self):
        for answer in (
            model_json(key="S9"),
            model_json(quote="9999 kg of verified savings"),
            '{"questions":[]}', "not JSON",
            json.dumps({"questions": [], "implementation_permitted": True}),
            json.dumps({"questions": [{
                "question": "This process is definitely safe?",
                "citations": [{"key": "S1", "quote": "A signed ledger"}],
                "approval_recorded": True,
            }]}),
        ):
            with self.subTest(answer=answer):
                result = validate_grounded_questions(answer, self.refs)
                self.assertEqual(result["status"], "MODEL_OUTPUT_REJECTED")
                self.assertEqual(result["questions"], [])
                self.assertFalse(result["implementation_permitted"])
