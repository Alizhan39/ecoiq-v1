"""Deterministic Decision & Islah plan: no causal or approval escalation."""
from unittest import TestCase

from ecoiq_os.decision_islah import (
    FalsifiableHypothesis, IslahStudy, build_preliminary_brief,
    check_islah_readiness,
)
from ecoiq_os.evidence import (
    CAUSAL_SUPPORT, REPLICATED_CAUSAL_SUPPORT, ROBUST_ASSOCIATION,
    UNTESTED,
)
from ecoiq_os.flow import FlowEdge, FlowNode, UniversalFlowGraph
from ecoiq_os.islah import IslahProposal
from ecoiq_os.kernel import EcoIQOSCase, COLLECT_EVIDENCE
from mizan.system_balance import (
    CRITICAL, HEALTHY, IMBALANCED, INSUFFICIENT_DATA, BalanceDimension,
    MizanConstraint, assess_balance,
)


def brief(**updates):
    kwargs = dict(
        case_id="CONSTRUCTION-001", domain="construction",
        process_name="Material delivery", resource_type="material",
        period="2026-10", unit="kg", reported_input=1000,
        reported_loss=120,
    )
    kwargs.update(updates)
    return build_preliminary_brief(**kwargs)


def flow():
    return UniversalFlowGraph(
        nodes=(FlowNode("a", "Input", "source"), FlowNode("b", "Process", "process")),
        edges=(FlowEdge("x", "a", "b", "material", value=1000, unit="kg"),),
    )


def case(status, mizan_status=IMBALANCED, constraints=()):
    return EcoIQOSCase(
        case_id="CASE-1", domain="construction",
        objective="Investigate material loss", flow_graph=flow(),
        mizan=assess_balance(
            scope_level="process",
            dimensions=(
                BalanceDimension("resource_efficiency", mizan_status),
                BalanceDimension("worker", HEALTHY),
                BalanceDimension("environment", HEALTHY),
            ),
            constraints=constraints,
        ),
        hypothesis_status=status,
    )


def proposal(**overrides):
    values = dict(
        id="ISLAH-1", title="Test a revised site handling rule",
        intervention_level="process", target_mechanism="loss_in_handling",
        current_rule="Delivery handling method documented by site.",
        proposed_rule="Trial a different handling protocol in a controlled setting.",
        expected_behaviour_change="Different material handling.",
        expected_flow_change="Measure any difference in loss and worker exposure.",
        affected_dimensions=("resource_efficiency", "worker", "environment"),
    )
    values.update(overrides)
    return IslahProposal(**values)


class PreliminaryBriefTests(TestCase):
    def test_120_of_1000_creates_questions_not_facts(self):
        result = brief()
        self.assertEqual(result["observed_loss"], 120)
        self.assertEqual(result["observed_input"], 1000)
        self.assertEqual(len(result["hypotheses"]), 3)
        self.assertEqual(len(result["islah_studies"]), 2)
        self.assertTrue(all(item["status"] == UNTESTED for item in result["hypotheses"]))
        self.assertTrue(all(item["disconfirming_observation"] for item in result["hypotheses"]))
        self.assertTrue(all(item["evidence_needed"] for item in result["hypotheses"]))
        self.assertFalse(result["implementation_permitted"])
        self.assertIsNone(result["causal_conclusion"])
        self.assertIsNone(result["savings_forecast"])
        self.assertIsNone(result["mizan_score"])
        self.assertFalse(result["ai_model_called"])
        self.assertEqual(result["next_stage"], COLLECT_EVIDENCE)
        self.assertFalse(result["independently_verified"])

    def test_missing_loss_generates_only_baseline_study(self):
        result = brief(reported_loss=None)
        self.assertIsNone(result["observed_loss"])
        self.assertEqual(result["hypotheses"], [])
        self.assertEqual(result["islah_studies"][0]["key"], "ESTABLISH_BASELINE")
        self.assertIn("reported_loss_measurement", result["missing_evidence"])

    def test_zero_reported_loss_is_not_an_avoidable_loss(self):
        result = brief(reported_loss=0)
        self.assertTrue(result["observed_zero_loss"])
        self.assertEqual(result["hypotheses"], [])
        self.assertEqual(result["observed_loss"], 0)

    def test_missing_input_and_zero_input_both_block_hypotheses(self):
        for input_value in (0, None):
            with self.subTest(input_value=input_value):
                value = 0 if input_value == 0 else None
                result = brief(reported_input=input_value, reported_loss=value)
                self.assertEqual(result["hypotheses"], [])
                self.assertIn("usable_reported_input", result["missing_evidence"])

    def test_bad_numbers_and_wrong_units_rejected(self):
        for value in (float("nan"), float("inf"), -1, True, "20"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                brief(reported_loss=value)
        with self.assertRaises(ValueError):
            brief(reported_loss=1200)
        with self.assertRaises(ValueError):
            brief(domain="fictional_industry")
        with self.assertRaises(ValueError):
            brief(case_id="")
        with self.assertRaises(ValueError):
            brief(unit="")

    def test_studies_are_not_implementation_permissions(self):
        for item in brief()["islah_studies"]:
            self.assertEqual(item["status"], "STUDY_ONLY")
            self.assertIn("worker", item["affected_dimensions"] if item["key"] == "TEST_HANDLING"
                          else ("worker",))
            self.assertTrue(item["possible_unintended_effects"])

    def test_generated_hypotheses_must_never_be_causal_support(self):
        with self.assertRaises(ValueError):
            FalsifiableHypothesis(
                key="x", question="Could it?", disconfirming_observation="A clear test",
                evidence_needed=("records",), status=CAUSAL_SUPPORT,
            )
        with self.assertRaises(ValueError):
            IslahStudy(
                key="s", question="Should we?", prerequisite="A test",
                affected_dimensions=("worker",), possible_unintended_effects=("strain",),
                status="APPROVED",
            )


class IslahReadinessTests(TestCase):
    def test_untested_and_unknown_mizan_cannot_start_modelling(self):
        for causal_status, balance in (
            (UNTESTED, IMBALANCED),
            (REPLICATED_CAUSAL_SUPPORT, INSUFFICIENT_DATA),
        ):
            with self.subTest(causal_status=causal_status, balance=balance):
                result = check_islah_readiness(
                    case=case(causal_status, balance), proposal=proposal(),
                )
                self.assertFalse(result["design_study_permitted"])
                self.assertFalse(result["simulation_study_permitted"])
                self.assertFalse(result["implementation_permitted"])

    def test_robust_association_only_allows_exploratory_design(self):
        result = check_islah_readiness(
            case=case(ROBUST_ASSOCIATION), proposal=proposal(),
        )
        self.assertTrue(result["design_study_permitted"])
        self.assertFalse(result["simulation_study_permitted"])
        self.assertFalse(result["implementation_permitted"])

    def test_causal_support_allows_simulation_not_implementation(self):
        result = check_islah_readiness(
            case=case(CAUSAL_SUPPORT), proposal=proposal(),
        )
        self.assertTrue(result["simulation_study_permitted"])
        self.assertFalse(result["implementation_permitted"])

    def test_replication_requires_human_review_without_approval(self):
        result = check_islah_readiness(
            case=case(REPLICATED_CAUSAL_SUPPORT), proposal=proposal(),
        )
        self.assertTrue(result["needs_human_implementation_review"])
        self.assertTrue(result["requires_mizan_simulation"])
        self.assertFalse(result["implementation_permitted"])
        self.assertFalse(result["approval_recorded"])

    def test_breached_worker_life_safety_overrides_replication(self):
        result = check_islah_readiness(
            case=case(REPLICATED_CAUSAL_SUPPORT, constraints=(
                MizanConstraint(
                    "worker_life_safety", True, "safety",
                    "Safety obligation breached.", "reviewed-site-safety-report",
                ),
            )), proposal=proposal(),
        )
        self.assertFalse(result["design_study_permitted"])
        self.assertFalse(result["simulation_study_permitted"])
        self.assertIn("worker_life_safety", result["blocked_by"])

    def test_cannot_turn_off_human_or_mizan_reviews(self):
        for mutation in (
            {"requires_mizan_simulation": False},
            {"requires_human_review": False},
        ):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                check_islah_readiness(
                    case=case(CAUSAL_SUPPORT), proposal=proposal(**mutation),
                )
