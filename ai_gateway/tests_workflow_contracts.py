"""Offline contract tests: no provider requests, migrations or workflow execution."""
import json

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from pydantic import ValidationError

from ai_gateway.workflow_contracts import (
    DecisionFlowPreview, preview_decision_flow, validate_decision_draft,
)


class DecisionFlowContractTests(SimpleTestCase):
    def test_preview_is_react_flow_compatible_and_inert(self):
        data = preview_decision_flow()
        self.assertEqual(data["mode"], "preview")
        self.assertIs(data["execution_enabled"], False)
        self.assertEqual(len(data["nodes"]), 7)
        self.assertEqual(len(data["edges"]), 6)
        self.assertEqual(data["nodes"][2]["data"]["kind"], "evidence_retrieval")
        self.assertEqual(data["nodes"][5]["data"]["kind"], "human_review")

    def test_cannot_skip_human_approval(self):
        data = preview_decision_flow()
        data["edges"][4]["target"] = "reviewed_result"
        with self.assertRaises(ValidationError):
            DecisionFlowPreview.model_validate(data)

    def test_cannot_enable_execution_or_add_hidden_steps(self):
        data = preview_decision_flow()
        data["execution_enabled"] = True
        with self.assertRaises(ValidationError):
            DecisionFlowPreview.model_validate(data)
        data = preview_decision_flow()
        data["nodes"][3]["data"]["provider_model_id"] = "unapproved/paid"
        with self.assertRaises(ValidationError):
            DecisionFlowPreview.model_validate(data)

    def test_valid_draft_remains_unverified(self):
        draft = validate_decision_draft(json.dumps({
            "summary": "Proposed efficiency review",
            "uncertainties": ["Missing metered energy data"],
            "proposed_next_steps": ["Request primary records"],
        }))
        self.assertTrue(draft.requires_human_review)
        self.assertEqual(draft.publication_state, "unverified_draft")

    def test_model_cannot_self_approve_or_invent_output_fields(self):
        for bad in (
            {"summary": "x", "requires_human_review": False},
            {"summary": "x", "publication_state": "approved"},
            {"summary": "x", "secret_provider_key": "should-not-be-accepted"},
            {"summary": ""},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_decision_draft(json.dumps(bad))
        with self.assertRaises(ValueError):
            validate_decision_draft("not json")
        with self.assertRaises(ValueError):
            validate_decision_draft("x" * 16001)


class DecisionFlowPreviewPermissionTests(TestCase):
    def test_preview_is_staff_only(self):
        url = "/api/ai/workflow-preview/"
        self.assertIn(self.client.get(url).status_code, (401, 403))
        User = get_user_model()
        ordinary = User.objects.create_user("flow_member", password="notused")
        self.client.force_login(ordinary)
        self.assertEqual(self.client.get(url).status_code, 403)
        staff = User.objects.create_user("flow_staff", password="notused", is_staff=True)
        self.client.force_login(staff)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "preview")
        self.assertFalse(response.json()["execution_enabled"])
        self.assertEqual(self.client.post(url, data={}).status_code, 405)
