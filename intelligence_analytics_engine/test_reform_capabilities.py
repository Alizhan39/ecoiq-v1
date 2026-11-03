"""Safety and completeness tests for proposed reform research capabilities."""
from dataclasses import FrozenInstanceError
from unittest import TestCase

from intelligence_analytics_engine.reform_capabilities import (
    REFORM_CAPABILITIES,
    build_research_plan,
    capability_by_slug,
)


EXPECTED_SLUGS = (
    "root_cause",
    "regulatory_conflict",
    "economic_digital_twin",
    "anti_corruption",
    "wealth_distribution",
    "public_budget",
    "legal_access",
    "islamic_finance",
    "future_generations",
    "ai_accountability",
    "reform_experiments",
    "institutional_memory",
)


class ReformCapabilityRegistryTests(TestCase):
    def test_catalogue_has_twelve_unique_stable_capabilities(self):
        self.assertEqual(len(REFORM_CAPABILITIES), 12)
        self.assertEqual(tuple(item.slug for item in REFORM_CAPABILITIES), EXPECTED_SLUGS)
        self.assertEqual(
            tuple(item.code for item in REFORM_CAPABILITIES),
            tuple(f"{i:02d}" for i in range(1, 13)),
        )

    def test_all_items_have_explicit_research_gates_and_reuse_hints(self):
        for item in REFORM_CAPABILITIES:
            with self.subTest(item=item.slug):
                self.assertIs(capability_by_slug(item.slug), item)
                self.assertEqual(item.maturity, "RESEARCH_SPEC_ONLY")
                self.assertGreaterEqual(len(item.required_inputs), 4)
                self.assertGreaterEqual(len(item.safeguards), 2)
                self.assertGreaterEqual(len(item.candidate_outputs), 2)
                self.assertTrue(item.governance_domain_codes)
                self.assertTrue(all(code in {f"{i:02d}" for i in range(1, 13)}
                                    for code in item.governance_domain_codes))
                self.assertTrue(all(path.endswith((".py", ".md"))
                                    for path in item.reuse_candidates))

    def test_no_research_plan_can_claim_approval_even_with_all_inputs(self):
        for item in REFORM_CAPABILITIES:
            with self.subTest(item=item.slug):
                full = {name: True for name in item.required_inputs}
                result = build_research_plan(item.slug, full)
                self.assertEqual(result["missing_inputs"], ())
                self.assertEqual(result["status"], "RESEARCH_PLAN_ONLY")
                self.assertEqual(result["evidence_authentication"], "NOT_PERFORMED")
                self.assertEqual(result["expert_review"], "NOT_PERFORMED")
                self.assertFalse(result["decision_ready"])
                self.assertNotIn("score", result)
                self.assertNotIn("verdict", result)

    def test_missing_or_false_claimed_inputs_remain_missing(self):
        item = capability_by_slug("regulatory_conflict")
        first, second = item.required_inputs[:2]
        result = build_research_plan(item.slug, {first: True, second: False})
        self.assertEqual(result["present_claimed_inputs"], (first,))
        self.assertEqual(result["missing_inputs"], item.required_inputs[1:])
        self.assertFalse(result["decision_ready"])

    def test_rejects_unknown_and_non_boolean_input_claims(self):
        with self.assertRaises(ValueError):
            build_research_plan("root_cause", {"made_up_authority": True})
        with self.assertRaises(ValueError):
            build_research_plan("root_cause", {"problem_definition": 1})
        with self.assertRaises(TypeError):
            build_research_plan("root_cause", ["problem_definition"])
        with self.assertRaises(KeyError):
            build_research_plan("unknown", {})

    def test_catalogue_metadata_is_immutable(self):
        item = REFORM_CAPABILITIES[0]
        with self.assertRaises(FrozenInstanceError):
            item.maturity = "PRODUCTION_READY"
        with self.assertRaises(TypeError):
            item.required_inputs[0] = "fabricated"

    def test_sensitive_domains_never_auto_produce_allegations_or_rulings(self):
        for slug in ("anti_corruption", "islamic_finance", "ai_accountability",
                     "regulatory_conflict", "reform_experiments"):
            result = build_research_plan(slug, {})
            self.assertFalse(result["decision_ready"])
            self.assertEqual(result["expert_review"], "NOT_PERFORMED")
            self.assertTrue(result["review_constraints"])
