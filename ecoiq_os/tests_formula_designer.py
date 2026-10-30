"""AI formula designer cannot introduce code, unsupported units or forged approval."""
import json
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from ecoiq_os.formula_designer import (
    propose_additional_formula, validate_ai_formula_candidate,
)
from ecoiq_os.formula_registry import InputSpec
from ecoiq_os.grounded_ai import GroundedSource
from evidence_memory.models import EvidenceMemory
from gold_intelligence.models import GoldProject, ProjectMembership


SCHEMA = (
    InputSpec("downtime_hours", "hour", "Unplanned downtime as audited hours"),
    InputSpec("scheduled_hours", "hour", "Total scheduled equipment hours"),
)


def reply(*, expression="downtime_hours / scheduled_hours * 100",
          output_unit="1", key="S1", quote="recorded 12 hours of downtime",
          extra=None):
    result = {
        "title": "Reported equipment downtime percentage",
        "expression": expression,
        "output_unit": output_unit,
        "assumptions": ["Downtime hours are a subset of scheduled hours."],
        "required_evidence": ["Timestamped equipment logs signed by an operator."],
        "citations": [{"key": key, "quote": quote}],
    }
    if extra:
        result.update(extra)
    return json.dumps(result)


class FormulaProposalGuardTests(TestCase):
    def setUp(self):
        self.sources = (GroundedSource(
            key="S1", memory_id=8,
            excerpt="Test log recorded 12 hours of downtime in a scheduled shift.",
            review_tier="independently_verified", content_sha256="a" * 64,
        ),)

    def test_valid_proposal_is_not_approved(self):
        result = validate_ai_formula_candidate(
            reply(), inputs=SCHEMA, source_excerpts=self.sources,
        )
        self.assertEqual(result["status"], "FORMULA_CANDIDATE_REQUIRES_REVIEW")
        self.assertEqual(result["candidate"]["output_unit"], "1")
        self.assertEqual(result["candidate"]["citations"][0]["memory_id"], 8)
        self.assertEqual(result["candidate"]["validation_status"], "AI_PROPOSED_NOT_APPROVED")
        self.assertFalse(result["implementation_permitted"])
        self.assertFalse(result["candidate"]["approved_for_production"])

    def test_malformed_code_fake_quote_fake_unit_or_approval_rejected(self):
        cases = (
            reply(expression="__import__('os').system('id')"),
            reply(expression="downtime_hours ** 50"),
            reply(expression="downtime_hours / secret_hours * 100"),
            reply(output_unit="kg"),
            reply(quote="invented savings were guaranteed"),
            reply(key="S42"),
            reply(extra={"approved_for_implementation": True}),
            "not-json",
            '{"title":"Approved by Shariah council"}',
        )
        for candidate in cases:
            with self.subTest(candidate=candidate):
                result = validate_ai_formula_candidate(
                    candidate, inputs=SCHEMA, source_excerpts=self.sources,
                )
                self.assertEqual(result["status"], "FORMULA_PROPOSAL_REJECTED")
                self.assertIsNone(result["candidate"])
                self.assertFalse(result["implementation_permitted"])


@override_settings(ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=False,
                   ECOIQ_FORMULA_AI_EXTERNAL_ENABLED=False)
class FormulaAIServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(
            name="Synthetic Formula Test", slug="formula-test-site",
            commodity="infrastructure", is_demo=False,
        )
        cls.other = GoldProject.objects.create(
            name="Other Formula Tenant", slug="formula-other",
            commodity="infrastructure", is_demo=False,
        )
        model = get_user_model()
        cls.analyst = model.objects.create_user(username="formula-analyst")
        cls.reviewer = model.objects.create_user(username="formula-reviewer")
        cls.viewer = model.objects.create_user(username="formula-viewer")
        ProjectMembership.objects.create(
            project=cls.project, user=cls.analyst,
            role=ProjectMembership.Role.ANALYST,
        )
        ProjectMembership.objects.create(
            project=cls.project, user=cls.viewer,
            role=ProjectMembership.Role.VIEWER,
        )

    def add_source(self, *, project=None):
        return EvidenceMemory.objects.create(
            project=project or self.project,
            visibility="project_private", source_type="manual",
            source_reference="synthetic:work-order",
            text_chunk="A verified synthetic work order recorded 12 hours of downtime.",
            verification_status="verified",
            review_tier="independently_verified", reviewer=self.reviewer,
            is_demo=False,
        )

    def ask(self, **kwargs):
        return propose_additional_formula(
            project=kwargs.pop("project", self.project),
            user=kwargs.pop("user", self.analyst),
            situation_key=kwargs.pop("situation_key", "equipment_downtime"),
            inputs=kwargs.pop("inputs", SCHEMA),
            **kwargs,
        )

    def test_no_source_and_no_provider_call_by_default(self):
        gateway = Mock()
        with override_settings(
            ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=True,
            ECOIQ_FORMULA_AI_EXTERNAL_ENABLED=True,
        ):
            result = self.ask(external_transfer_approved=True, gateway=gateway)
        self.assertEqual(result["status"], "NO_REVIEWED_SOURCES")
        self.add_source()
        result = self.ask(external_transfer_approved=True, gateway=gateway)
        self.assertEqual(result["status"], "EXTERNAL_MODEL_DISABLED")
        self.assertFalse(result["fallback"]["model_called"])
        gateway.chat.assert_not_called()

    def test_all_three_consent_gates_required(self):
        self.add_source()
        gateway = Mock()
        for first, second, permission in (
            (False, True, True), (True, False, True), (True, True, False),
        ):
            with self.subTest(flags=(first, second, permission)), override_settings(
                ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=first,
                ECOIQ_FORMULA_AI_EXTERNAL_ENABLED=second,
            ):
                result = self.ask(external_transfer_approved=permission, gateway=gateway)
                self.assertEqual(result["status"], "EXTERNAL_MODEL_DISABLED")
        gateway.chat.assert_not_called()

    def test_allowed_gateway_returns_candidate_not_business_permission(self):
        self.add_source()
        gateway = Mock()
        gateway.chat.return_value = {"answer": reply()}
        with override_settings(
            ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=True,
            ECOIQ_FORMULA_AI_EXTERNAL_ENABLED=True,
        ):
            result = self.ask(external_transfer_approved=True, gateway=gateway)
        self.assertEqual(result["status"], "FORMULA_CANDIDATE_REQUIRES_REVIEW")
        self.assertTrue(result["model_called"])
        self.assertFalse(result["implementation_permitted"])
        self.assertIsNone(result["shariah_verdict"])
        self.assertEqual(gateway.chat.call_count, 1)
        args = gateway.chat.call_args.kwargs
        self.assertEqual(args["context"]["module"], "ecoiq_os")
        self.assertNotIn("source_reference", args["message"])
        self.assertIn("text_untrusted", args["message"])

    def test_cross_project_viewer_and_invalid_schema_fail_closed(self):
        self.add_source()
        gateway = Mock()
        for kwargs, status in (
            ({"project": self.other}, "ACCESS_DENIED"),
            ({"user": self.viewer}, "ACCESS_DENIED"),
            ({"situation_key": "../../etc/passwd"}, "INVALID_SCENARIO"),
            ({"inputs": ()}, "INVALID_VARIABLE_SCHEMA"),
        ):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(
                    self.ask(gateway=gateway, **kwargs)["status"], status,
                )
        gateway.chat.assert_not_called()

    def test_bad_ai_result_is_discarded_not_persisted(self):
        self.add_source()
        gateway = Mock()
        gateway.chat.return_value = {"answer": reply(extra={"approve_now": True})}
        with override_settings(
            ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=True,
            ECOIQ_FORMULA_AI_EXTERNAL_ENABLED=True,
        ):
            result = self.ask(external_transfer_approved=True, gateway=gateway)
        self.assertEqual(result["status"], "FORMULA_PROPOSAL_REJECTED")
        self.assertIsNone(result["candidate"])
        self.assertFalse(result["implementation_permitted"])
