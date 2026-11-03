"""Existing formula registry is the only source of KPI definitions for reform work."""
from unittest import TestCase

from ecoiq_os.formula_registry import FORMULAS_BY_KEY
from intelligence_analytics_engine.reform_capabilities import REFORM_CAPABILITIES
from intelligence_analytics_engine.reform_kpi_crosswalk import proposed_kpi_context


class ReformCrosswalkTests(TestCase):
    def test_all_twelve_capabilities_have_declared_context_not_approvals(self):
        for capability in REFORM_CAPABILITIES:
            with self.subTest(slug=capability.slug):
                result = proposed_kpi_context(capability.slug)
                self.assertEqual(result["capability"], capability.slug)
                self.assertEqual(result["kpi_relation"], "CONTEXT_ONLY_NOT_OUTCOME_MEASURE")
                self.assertEqual(result["source_authentication"], "NOT_PERFORMED")
                self.assertEqual(result["professional_review"], "NOT_PERFORMED")
                self.assertFalse(result["decision_ready"])
                for link in result["formula_links"]:
                    spec = FORMULAS_BY_KEY[link["formula_key"]]
                    self.assertEqual(link["formula_title"], spec.title)
                    self.assertEqual(link["validation_status"], spec.validation_status)
                    self.assertFalse(link["measured"])

    def test_legal_access_missing_direct_kpi_is_not_fabricated(self):
        result = proposed_kpi_context("legal_access")
        self.assertTrue(result["missing_direct_kpi"])
        self.assertEqual(result["formula_links"], ())
        self.assertFalse(result["decision_ready"])

    def test_contextual_procurement_ratio_is_not_corruption_finding(self):
        result = proposed_kpi_context("anti_corruption")
        self.assertIn(
            "fair_procurement",
            [link["formula_key"] for link in result["formula_links"]],
        )
        self.assertFalse(result["decision_ready"])
        self.assertNotIn("verdict", result)
        self.assertNotIn("suspects", result)

    def test_unknown_capability_fails_closed(self):
        with self.assertRaises(KeyError):
            proposed_kpi_context("unknown")
