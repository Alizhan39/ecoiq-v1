"""Project isolation and deterministic formula sequencing, without remote model calls."""
import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from ecoiq_os.formula_registry import PROVISIONAL_KPI_FORMULAS
from gold_intelligence.models import GoldProject, ProjectMembership


@override_settings(ALLOWED_HOSTS=["testserver"], DEBUG=True)
class FormulaFlowAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(
            name="Pilot process", slug="formula-flow-pilot",
            commodity="infrastructure", is_demo=False,
        )
        cls.other = GoldProject.objects.create(
            name="Other private process", slug="other-formula-flow",
            commodity="infrastructure", is_demo=False,
        )
        cls.viewer = get_user_model().objects.create_user(username="formula-flow-viewer")
        cls.analyst = get_user_model().objects.create_user(username="formula-flow-analyst")
        cls.stranger = get_user_model().objects.create_user(username="formula-flow-stranger")
        ProjectMembership.objects.create(
            project=cls.project, user=cls.viewer, role=ProjectMembership.Role.VIEWER)
        ProjectMembership.objects.create(
            project=cls.project, user=cls.analyst, role=ProjectMembership.Role.ANALYST)

    def setUp(self):
        cache.clear()
        self.url = reverse("api_v2:project_formula_flow", kwargs={
            "project_slug": self.project.slug,
        })

    def post(self, payload, *, url=None):
        return self.client.post(
            url or self.url, data=json.dumps(payload), content_type="application/json",
        )

    @staticmethod
    def valid_payload():
        return {
            "period": "2026-10",
            "observations": {
                "revenue": {
                    "reported_revenue": {"value": "150.25", "source_ref": "invoice-ledger-1"},
                },
                "gross_margin": {
                    "revenue": {"value": "150.25", "source_ref": "invoice-ledger-1"},
                    "cost_of_goods_sold": {"value": "50.25", "source_ref": "costs-2"},
                },
            },
        }

    def test_denied_user_cannot_see_project_existence_or_inputs(self):
        self.assertIn(self.client.get(self.url).status_code, (401, 403))
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.post(self.valid_payload()).status_code, 404)

    def test_viewer_can_view_but_not_execute_preview(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["formula_count"], 20)
        self.assertEqual(len(body["nodes"]), 20)
        self.assertEqual(len(body["edges"]), 19)
        self.assertEqual([x["id"] for x in body["nodes"]],
                         [x.key for x in PROVISIONAL_KPI_FORMULAS])
        self.assertFalse(body["execution_enabled"])
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.post(self.valid_payload()).status_code, 404)

    def test_analyst_runs_in_canonical_sequence_without_verification(self):
        self.client.force_login(self.analyst)
        response = self.post(self.valid_payload())
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(len(body["results"]), 20)
        self.assertEqual(body["results"][0]["formula_key"], "revenue")
        self.assertEqual(body["results"][0]["value_decimal"], "150.25")
        self.assertEqual(body["results"][1]["formula_key"], "gross_margin")
        self.assertEqual(body["results"][1]["value_decimal"], "66.55574043261231281198003328")
        self.assertEqual(body["results"][2]["status"], "NOT_SUPPLIED")
        self.assertFalse(body["source_ids_verified"])
        self.assertFalse(body["automated_publication"])
        self.assertFalse(body["model_called"])
        self.assertEqual(body["results"][1]["status"], "REPORTED_NOT_VERIFIED")
        self.assertFalse(body["results"][1]["approved_for_implementation"])

    def test_undefined_denominator_is_not_zero(self):
        self.client.force_login(self.analyst)
        body = self.valid_payload()
        body["observations"]["gross_margin"]["revenue"]["value"] = "0"
        response = self.post(body)
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][1]
        self.assertIsNone(result["value_decimal"])
        self.assertEqual(result["status"], "UNDEFINED_DENOMINATOR_OR_RESULT")

    def test_bad_inputs_reject_all_without_execution(self):
        self.client.force_login(self.analyst)
        variants = []
        base = self.valid_payload()
        for key, value in (
            ("unknown", {"a": {"value": "10", "source_ref": "S"}}),
        ):
            item = self.valid_payload()
            item["observations"][key] = value
            variants.append(item)
        for wrong in (True, 1.25, "-5", "NaN", "Infinity", "x" * 150):
            item = self.valid_payload()
            item["observations"]["revenue"]["reported_revenue"]["value"] = wrong
            variants.append(item)
        item = self.valid_payload()
        item["observations"]["gross_margin"].pop("cost_of_goods_sold")
        variants.append(item)
        item = self.valid_payload()
        item["observations"]["revenue"]["reported_revenue"]["source_ref"] = ""
        variants.append(item)
        item = self.valid_payload()
        item["approve"] = True
        variants.append(item)
        for case in variants:
            with self.subTest(case=case):
                self.assertEqual(self.post(case).status_code, 400)

    def test_private_shell_project_gate(self):
        path = reverse("formula_flow_shell", args=[self.project.slug])
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.client.force_login(self.viewer)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertEqual(self.client.post(path).status_code, 405)

    def test_cross_project_boundary(self):
        self.client.force_login(self.analyst)
        other_url = reverse("api_v2:project_formula_flow", kwargs={
            "project_slug": self.other.slug,
        })
        self.assertEqual(self.client.get(other_url).status_code, 404)
        self.assertEqual(self.post(self.valid_payload(), url=other_url).status_code, 404)
