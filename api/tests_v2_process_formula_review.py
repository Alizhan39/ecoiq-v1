"""All 20 candidate KPIs examined for a real project-owned process.

No external AI/model calls, no durable source data, no approval state writes.
"""
import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from api.models import ProcessAnalysisRun
from ecoiq_os.formula_registry import PROVISIONAL_KPI_FORMULAS
from gold_intelligence.models import GoldProject, ProjectMembership


@override_settings(ALLOWED_HOSTS=["testserver"], DEBUG=True)
class ProcessFormulaReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(
            name="Project A", slug="formula-process-a", commodity="infrastructure",
        )
        cls.other = GoldProject.objects.create(
            name="Project B", slug="formula-process-b", commodity="infrastructure",
        )
        User = get_user_model()
        cls.analyst = User.objects.create_user("process-formula-analyst")
        cls.viewer = User.objects.create_user("process-formula-viewer")
        cls.stranger = User.objects.create_user("process-formula-stranger")
        ProjectMembership.objects.create(
            project=cls.project, user=cls.analyst, role=ProjectMembership.Role.ANALYST,
        )
        ProjectMembership.objects.create(
            project=cls.project, user=cls.viewer, role=ProjectMembership.Role.VIEWER,
        )
        cls.analysis_run = ProcessAnalysisRun.objects.create(
            project=cls.project, created_by=cls.analyst,
            case_id="CASE-TEST-01", domain="construction", process_name="Site Delivery",
            resource_type="material", period="2026-10", unit="kg",
            file_fingerprint="a" * 64,
            summary={"kpi": {"value": 12, "status": "REPORTED_NOT_VERIFIED"}},
        )
        cls.other_run = ProcessAnalysisRun.objects.create(
            project=cls.other, created_by=cls.stranger,
            case_id="OTHER-PRIVATE", domain="construction", process_name="Private",
            resource_type="material", period="2026-10", unit="kg",
            file_fingerprint="b" * 64,
        )

    def setUp(self):
        cache.clear()
        self.url = reverse("api_v2:process_formula_review", kwargs={
            "project_slug": self.project.slug, "run_id": self.analysis_run.pk,
        })

    def post(self, payload, url=None):
        return self.client.post(url or self.url, data=json.dumps(payload),
                                content_type="application/json")

    @staticmethod
    def measurement(value, unit, source="SOURCE-1"):
        return {"value": value, "unit": unit, "source_ref": source}

    def test_anonymous_and_unauthorised_cannot_discover_saved_processes(self):
        self.assertIn(self.client.get(self.url).status_code, (401, 403))
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.post({"measurements": {}}).status_code, 404)

    def test_viewer_gets_shared_parameter_contract_but_not_execution(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        info = response.json()
        self.assertEqual(info["process_analysis_id"], self.analysis_run.pk)
        self.assertEqual(info["period"], "2026-10")
        self.assertFalse(info["can_preview_calculate"])
        self.assertFalse(info["source_measurements_stored_in_process_analysis"])
        self.assertEqual(len(info["formulas"]), 20)
        self.assertEqual(
            [s["key"] for s in info["formulas"]],
            [f.key for f in PROVISIONAL_KPI_FORMULAS],
        )
        self.assertEqual(
            sorted(p["key"] for p in info["parameters"]),
            sorted({inp.key for f in PROVISIONAL_KPI_FORMULAS for inp in f.inputs}),
        )
        self.assertIn("energy_intensity", next(p for p in info["parameters"]
                                             if p["key"] == "produced_units")["used_by"])
        self.assertIn("water_intensity", next(p for p in info["parameters"]
                                            if p["key"] == "produced_units")["used_by"])
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.post({"measurements": {}}).status_code, 404)

    def test_every_formula_visited_when_no_measurements_supplied(self):
        self.client.force_login(self.analyst)
        data = self.post({"measurements": {}}).json()
        self.assertTrue(data["all_formulas_visited"])
        self.assertEqual(data["formula_count"], 20)
        self.assertEqual(len(data["results"]), 20)
        self.assertEqual(data["counts"]["needs_measurements"], 20)
        self.assertTrue(all(r["status"] == "NEEDS_MEASUREMENTS" for r in data["results"]))
        self.assertTrue(all(r["value_decimal"] is None for r in data["results"]))
        self.assertTrue(all(r["missing_inputs"] for r in data["results"]))
        self.assertFalse(data["automated_publication"])
        self.assertFalse(data["source_identifiers_verified"])
        self.assertTrue(data["review_required"])

    def test_common_measurements_reused_without_chaining_outputs(self):
        self.client.force_login(self.analyst)
        measurements = {
            "reported_revenue": self.measurement("150.25", "GBP"),
            "revenue": self.measurement("150.25", "GBP"),
            "cost_of_goods_sold": self.measurement("50.25", "GBP"),
            "produced_units": self.measurement("10", "unit", "count-sheet"),
            "total_energy": self.measurement("500", "kWh", "meter-1"),
            "water_withdrawal": self.measurement("20", "m3", "meter-2"),
            "reported_emissions": self.measurement("5", "tCO2e", "ledger-3"),
        }
        result = self.post({"measurements": measurements})
        self.assertEqual(result.status_code, 200, result.content)
        body = result.json()
        by_key = {r["formula_key"]: r for r in body["results"]}
        self.assertEqual(len(by_key), 20)
        self.assertEqual(by_key["revenue"]["value_decimal"], "150.25")
        self.assertEqual(by_key["energy_intensity"]["value_decimal"], "50")
        self.assertEqual(by_key["water_intensity"]["value_decimal"], "2")
        self.assertEqual(by_key["ghg_intensity"]["value_decimal"], "0.5")
        self.assertEqual(by_key["gross_margin"]["status"], "REPORTED_NOT_VERIFIED")
        self.assertEqual(by_key["operating_cash_flow"]["status"], "NEEDS_MEASUREMENTS")
        self.assertIn("operating_cash_inflows", by_key["operating_cash_flow"]["missing_inputs"])
        self.assertEqual(body["counts"]["reported_not_verified"], 5)
        self.assertEqual(body["counts"]["needs_measurements"], 15)
        self.assertFalse(body["model_called"])
        self.assertEqual(ProcessAnalysisRun.objects.count(), 2)

    def test_complete_shared_parameter_set_evaluates_every_candidate_once(self):
        from api.v2_process_formula_review import parameter_contract

        self.client.force_login(self.analyst)
        _, parameters = parameter_contract()
        measurements = {
            item["key"]: self.measurement("1", item["unit"], f"source-{item['key']}")
            for item in parameters
        }
        response = self.post({"measurements": measurements})
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["formula_count"], 20)
        self.assertEqual(body["counts"], {
            "reported_not_verified": 20,
            "needs_measurements": 0,
            "blocked": 0,
        })
        self.assertEqual(
            [item["formula_key"] for item in body["results"]],
            [spec.key for spec in PROVISIONAL_KPI_FORMULAS],
        )
        self.assertTrue(all(item["status"] == "REPORTED_NOT_VERIFIED"
                            and item["value_decimal"] is not None
                            and item["approved_for_implementation"] is False
                            for item in body["results"]))
        self.assertEqual(len(measurements), len(parameters))

    def test_zero_denominator_is_undefined_not_zero_or_ready(self):
        self.client.force_login(self.analyst)
        measurements = {
            "revenue": self.measurement("0", "GBP"),
            "cost_of_goods_sold": self.measurement("20", "GBP"),
        }
        response = self.post({"measurements": measurements})
        self.assertEqual(response.status_code, 200)
        by_key = {r["formula_key"]: r for r in response.json()["results"]}
        self.assertIsNone(by_key["gross_margin"]["value_decimal"])
        self.assertEqual(by_key["gross_margin"]["status"], "UNDEFINED_DENOMINATOR_OR_RESULT")
        self.assertEqual(response.json()["counts"]["blocked"], 1)

    def test_unknown_wrong_units_bad_values_or_fake_approvals_fail_closed(self):
        self.client.force_login(self.analyst)
        variants = [
            {"measurements": {"unknown": self.measurement("1", "GBP")}},
            {"measurements": {"total_energy": self.measurement("10", "GBP")}},
            {"measurements": {"total_energy": self.measurement(True, "kWh")}},
            {"measurements": {"total_energy": self.measurement(1.3, "kWh")}},
            {"measurements": {"total_energy": self.measurement("-5", "kWh")}},
            {"measurements": {"total_energy": self.measurement("NaN", "kWh")}},
            {"measurements": {"total_energy": self.measurement("1", "kWh", "")}},
            {"measurements": {"total_energy": self.measurement("1", "kWh", "s" * 121)}},
            {"measurements": {"total_energy": self.measurement("1", "kWh")}, "approved": True},
            {"measurements": [], "period": "2030-12"},
        ]
        for payload in variants:
            with self.subTest(payload=payload):
                self.assertEqual(self.post(payload).status_code, 400)

    def test_process_identity_and_period_are_server_owned(self):
        self.client.force_login(self.analyst)
        result = self.post({"measurements": {
            "reported_revenue": self.measurement("99", "GBP"),
        }}).json()
        self.assertEqual(result["period"], "2026-10")
        self.assertEqual(result["case_id"], "CASE-TEST-01")
        self.assertEqual(result["process_name"], "Site Delivery")
        self.assertFalse(result["production_approved"])

    def test_process_from_other_project_is_not_discoverable(self):
        self.client.force_login(self.analyst)
        foreign = reverse("api_v2:process_formula_review", kwargs={
            "project_slug": self.project.slug, "run_id": self.other_run.pk,
        })
        self.assertEqual(self.client.get(foreign).status_code, 404)
        self.assertEqual(self.post({"measurements": {}}, url=foreign).status_code, 404)
