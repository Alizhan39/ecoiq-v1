"""Decision & Islah briefing: isolation, no invented causality or approvals."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from api.models import ProcessAnalysisRun
from gold_intelligence.models import GoldProject, ProjectMembership


@override_settings(ALLOWED_HOSTS=["testserver"])
class DecisionIslahAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(
            name="Private construction", slug="private-islah",
            commodity="infrastructure", is_demo=False,
        )
        cls.other = GoldProject.objects.create(
            name="Other private construction", slug="other-private-islah",
            commodity="infrastructure", is_demo=False,
        )
        cls.viewer = get_user_model().objects.create_user(username="islah-reader")
        cls.analyst = get_user_model().objects.create_user(username="islah-analyst")
        cls.stranger = get_user_model().objects.create_user(username="islah-stranger")
        ProjectMembership.objects.create(
            project=cls.project, user=cls.viewer,
            role=ProjectMembership.Role.VIEWER,
        )
        ProjectMembership.objects.create(
            project=cls.project, user=cls.analyst,
            role=ProjectMembership.Role.ANALYST,
        )
        cls.run = ProcessAnalysisRun.objects.create(
            project=cls.project, created_by=cls.analyst,
            case_id="CASE-1", domain="construction", process_name="Site materials",
            resource_type="material", unit="kg", period="2026-10",
            file_fingerprint="a" * 64,
            summary={
                "kpi": {
                    "key": "recorded_loss_rate", "numerator": 120.0,
                    "denominator": 1000.0, "value": 12.0, "unit": "%",
                    "independently_verified": False,
                },
                "next_stage": "COLLECT_EVIDENCE",
                "import": {"source_authentication": "NOT_VERIFIED"},
            },
        )

    def setUp(self):
        cache.clear()
        self.url = reverse("api_v2:process_decision_brief", kwargs={
            "project_slug": self.project.slug, "run_id": self.run.pk,
        })

    def test_read_only_user_receives_falsifiable_questions(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        value = response.json()["brief"]
        self.assertEqual(value["case_id"], "CASE-1")
        self.assertEqual(value["observed_loss"], 120)
        self.assertEqual(len(value["hypotheses"]), 3)
        self.assertTrue(all(item["status"] == "UNTESTED" for item in value["hypotheses"]))
        self.assertEqual(value["next_stage"], "COLLECT_EVIDENCE")
        self.assertFalse(value["implementation_permitted"])
        self.assertFalse(value["ai_model_called"])
        self.assertIsNone(value["savings_forecast"])
        self.assertIsNone(value["causal_conclusion"])
        self.assertEqual(response["Cache-Control"], "private, no-store, max-age=0")
        self.assertNotIn("file_fingerprint", response.content.decode())

    def test_unlogged_and_unauthorised_users_fail_closed(self):
        self.assertIn(self.client.get(self.url).status_code, (401, 403))
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_cross_project_slug_does_not_expose_another_project(self):
        self.client.force_login(self.viewer)
        other_url = reverse("api_v2:process_decision_brief", kwargs={
            "project_slug": self.other.slug, "run_id": self.run.pk,
        })
        self.assertEqual(self.client.get(other_url).status_code, 404)

    def test_revoked_reader_loses_decision_brief_access(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        ProjectMembership.objects.filter(project=self.project, user=self.viewer).update(
            is_active=False,
        )
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_invalid_analysis_id_never_reveals_data(self):
        self.client.force_login(self.viewer)
        url = reverse("api_v2:process_decision_brief", kwargs={
            "project_slug": self.project.slug, "run_id": self.run.pk + 100,
        })
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_cannot_turn_a_get_into_implementation_approval(self):
        self.client.force_login(self.analyst)
        for method in (self.client.post, self.client.delete):
            self.assertEqual(method(self.url).status_code, 405)
        self.assertEqual(ProcessAnalysisRun.objects.count(), 1)

    def test_stored_kernel_approval_is_not_trusted(self):
        self.run.summary["next_stage"] = "HUMAN_REVIEW_FOR_IMPLEMENTATION"
        self.run.summary["hypothesis_status"] = "REPLICATED_CAUSAL_SUPPORT"
        self.run.summary["verified"] = True
        self.run.save(update_fields=["summary"])
        self.client.force_login(self.viewer)
        brief = self.client.get(self.url).json()["brief"]
        self.assertEqual(brief["next_stage"], "COLLECT_EVIDENCE")
        self.assertEqual(brief["hypothesis_status"], "UNTESTED")
        self.assertFalse(brief["implementation_permitted"])
        self.assertFalse(brief["independently_verified"])

    def test_incomplete_history_has_no_invented_brief(self):
        self.run.summary["kpi"]["denominator"] = "invalid_number"
        self.run.save(update_fields=["summary"])
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.url).status_code, 422)

    def test_missing_loss_generates_baseline_questions_only(self):
        self.run.summary["kpi"]["numerator"] = None
        self.run.save(update_fields=["summary"])
        self.client.force_login(self.viewer)
        brief = self.client.get(self.url).json()["brief"]
        self.assertEqual(brief["hypotheses"], [])
        self.assertEqual(brief["islah_studies"][0]["key"], "ESTABLISH_BASELINE")
