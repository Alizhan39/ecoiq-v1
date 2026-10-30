"""Synthetic construction pilot: full EcoIQ OS path, no live client data.

This exercises the actual same-origin Django views, role boundary, CSV parser,
stored KPI and Decision/Islah endpoint. It deliberately does not "approve"
an Islah proposal or pretend a ratio demonstrates avoidable loss.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from api.models import ProcessAnalysisRun
from gold_intelligence.models import GoldProject, ProjectMembership


COLUMNS = (
    "record_id,case_id,domain,process_name,resource_type,period,unit,"
    "flow_type,quantity,evidence_ref\n"
)


def _csv(*, loss="120", input_amount="1000", case_id="SYNTHETIC-SITE-001"):
    """Fictional figures and opaque source IDs, not actual source verification."""
    records = (
        f"I-1,{case_id},construction,Concrete delivery,material,2026-10,kg,"
        f"input,{input_amount},TEST-RECEIPT-1\n"
        f"L-1,{case_id},construction,Concrete delivery,material,2026-10,kg,"
        f"loss,{loss},TEST-LOSS-1\n"
    )
    return (COLUMNS + records).encode("utf-8")


def _upload(data):
    return SimpleUploadedFile("synthetic.csv", data, content_type="text/csv")


@override_settings(ALLOWED_HOSTS=["testserver"])
class SyntheticConstructionPilotJourneyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(
            name="Synthetic construction demonstration",
            slug="synthetic-construction-pilot",
            commodity="infrastructure",
            is_demo=True,
        )
        cls.unrelated = GoldProject.objects.create(
            name="Unrelated private site",
            slug="unrelated-private-pilot",
            commodity="infrastructure",
            is_demo=False,
        )
        cls.analyst = get_user_model().objects.create_user(
            username="synthetic-pilot-analyst",
        )
        cls.viewer = get_user_model().objects.create_user(
            username="synthetic-pilot-viewer",
        )
        cls.outsider = get_user_model().objects.create_user(
            username="synthetic-pilot-outsider",
        )
        ProjectMembership.objects.create(
            user=cls.analyst, project=cls.project,
            role=ProjectMembership.Role.ANALYST,
        )
        ProjectMembership.objects.create(
            user=cls.viewer, project=cls.project,
            role=ProjectMembership.Role.VIEWER,
        )

    def setUp(self):
        cache.clear()
        self.collection = reverse(
            "api_v2:process_analyses",
            kwargs={"project_slug": self.project.slug},
        )

    def _new_analysis(self, data):
        self.client.force_login(self.analyst)
        return self.client.post(self.collection, {"file": _upload(data)})

    def _brief_url(self, analysis_id, project=None):
        return reverse("api_v2:process_decision_brief", kwargs={
            "project_slug": (project or self.project).slug,
            "run_id": analysis_id,
        })

    def test_end_to_end_csv_to_mizan_and_human_gate(self):
        """12% reported loss -> untested questions, not a savings promise."""
        self.client.force_login(self.analyst)
        workspace = self.client.get(reverse("process_workspace"))
        self.assertEqual(workspace.status_code, 200)
        self.assertContains(workspace, "Synthetic construction demonstration")
        self.assertNotContains(workspace, "Unrelated private site")

        submitted = self._new_analysis(_csv())
        self.assertEqual(submitted.status_code, 201, submitted.content)
        response = submitted.json()
        analysis = response["analysis"]
        self.assertTrue(response["created"])
        self.assertEqual(analysis["result"]["kpi"]["value"], 12)
        self.assertEqual(analysis["result"]["next_stage"], "COLLECT_EVIDENCE")
        self.assertFalse(analysis["independently_verified"])
        self.assertFalse(analysis["result"]["import"]["raw_csv_stored"])

        stored = ProcessAnalysisRun.objects.get()
        self.assertEqual(stored.project_id, self.project.pk)
        self.assertEqual(stored.created_by_id, self.analyst.pk)
        self.assertNotIn("TEST-RECEIPT-1", str(stored.summary))
        self.assertNotIn("TEST-LOSS-1", str(stored.summary))

        # Viewer sees the saved report and falsifiable studies, but cannot write.
        self.client.force_login(self.viewer)
        history = self.client.get(self.collection)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["count"], 1)
        self.assertEqual(history.json()["results"][0]["id"], stored.pk)
        brief_result = self.client.get(self._brief_url(stored.pk))
        self.assertEqual(brief_result.status_code, 200)
        brief = brief_result.json()["brief"]
        self.assertFalse(brief["implementation_permitted"])
        self.assertFalse(brief["ai_model_called"])
        self.assertFalse(brief["independently_verified"])
        self.assertIsNone(brief["causal_conclusion"])
        self.assertIsNone(brief["savings_forecast"])
        self.assertIsNone(brief["mizan_score"])
        self.assertEqual(brief["hypothesis_status"], "UNTESTED")
        self.assertEqual(len(brief["hypotheses"]), 3)
        self.assertTrue(all(h["disconfirming_observation"]
                            for h in brief["hypotheses"]))
        self.assertTrue(all(s["status"] == "STUDY_ONLY"
                            for s in brief["islah_studies"]))
        self.assertIn("human_approval", brief["missing_evidence"])
        self.assertEqual(
            self.client.post(self.collection, {"file": _upload(_csv())}).status_code,
            404,
        )

        # Neither the private project name nor its brief crosses the role boundary.
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.collection).status_code, 404)
        self.assertEqual(self.client.get(self._brief_url(stored.pk)).status_code, 404)
        self.assertEqual(self.client.get(self._brief_url(
            stored.pk, project=self.unrelated,
        )).status_code, 404)

        # A revoked viewer immediately loses history/decision access.
        ProjectMembership.objects.filter(
            user=self.viewer, project=self.project,
        ).update(is_active=False)
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.collection).status_code, 404)
        self.assertEqual(self.client.get(self._brief_url(stored.pk)).status_code, 404)

    def test_missing_loss_does_not_become_zero_or_savings(self):
        result = self._new_analysis(_csv(loss=""))
        self.assertEqual(result.status_code, 201, result.content)
        analysis = result.json()["analysis"]
        self.assertIsNone(analysis["result"]["kpi"]["value"])
        self.assertEqual(analysis["result"]["kpi"]["status"], "INSUFFICIENT_DATA")
        brief = self.client.get(self._brief_url(analysis["id"])).json()["brief"]
        self.assertEqual(brief["hypotheses"], [])
        self.assertIn("reported_loss_measurement", brief["missing_evidence"])
        self.assertFalse(brief["implementation_permitted"])

    def test_zero_loss_remains_a_real_zero_without_avoided_cost_claim(self):
        result = self._new_analysis(_csv(loss="0"))
        self.assertEqual(result.status_code, 201, result.content)
        analysis = result.json()["analysis"]
        self.assertEqual(analysis["result"]["kpi"]["value"], 0)
        brief = self.client.get(self._brief_url(analysis["id"])).json()["brief"]
        self.assertTrue(brief["observed_zero_loss"])
        self.assertEqual(brief["hypotheses"], [])
        self.assertIsNone(brief["savings_forecast"])

    def test_duplicate_upload_preserves_single_protected_history_record(self):
        first = self._new_analysis(_csv())
        second = self._new_analysis(_csv())
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.json()["created"])
        self.assertEqual(ProcessAnalysisRun.objects.count(), 1)
