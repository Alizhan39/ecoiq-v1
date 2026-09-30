from unittest import TestCase

from ecoiq_os.domains import DOMAINS, DOMAIN_REGISTRY
from ecoiq_os.evidence import ASSOCIATION_ONLY, CAUSAL_SUPPORT, REPLICATED_CAUSAL_SUPPORT
from ecoiq_os.flow import FlowEdge, FlowNode, UniversalFlowGraph
from ecoiq_os.kernel import (
    HUMAN_REVIEW_FOR_IMPLEMENTATION,
    HUMAN_REVIEW_REQUIRED,
    REPAIR_FLOW_GRAPH,
    RUN_FALSIFICATION,
    SIMULATE_ISLAH,
    EcoIQOSCase,
    evaluate_case,
)
from mizan.system_balance import (
    HEALTHY,
    IMBALANCED,
    BalanceDimension,
    MizanConflict,
    MizanConstraint,
    assess_balance,
)


def valid_graph():
    return UniversalFlowGraph(
        nodes=(
            FlowNode("source", "Resource", "source"),
            FlowNode("process", "Process", "process"),
        ),
        edges=(
            FlowEdge(
                "input",
                "source",
                "process",
                "energy",
                value=100,
                unit="MWh",
                period="2026",
            ),
        ),
    )


class EcoIQOSKernelTests(TestCase):
    def test_domains_share_one_kernel_registry(self):
        self.assertIn("mining", DOMAIN_REGISTRY)
        self.assertIn("energy", DOMAIN_REGISTRY)
        self.assertIn("oil_gas", DOMAIN_REGISTRY)
        self.assertIn("healthcare", DOMAIN_REGISTRY)
        self.assertIn("education", DOMAIN_REGISTRY)
        self.assertIn("households", DOMAIN_REGISTRY)
        self.assertEqual(len(DOMAINS), len(DOMAIN_REGISTRY))

    def test_association_only_runs_falsification_not_islah(self):
        case = EcoIQOSCase(
            case_id="KZ-TEST-1",
            domain="households",
            objective="Reduce persistent household vulnerability.",
            flow_graph=valid_graph(),
            mizan=assess_balance(
                scope_level="country",
                dimensions=[BalanceDimension("justice", IMBALANCED)],
            ),
            hypothesis_status=ASSOCIATION_ONLY,
        )

        self.assertEqual(evaluate_case(case).next_stage, RUN_FALSIFICATION)

    def test_causal_support_allows_simulation_not_implementation(self):
        case = EcoIQOSCase(
            case_id="KZ-TEST-2",
            domain="energy",
            objective="Reduce avoidable energy loss without shifting harm.",
            flow_graph=valid_graph(),
            mizan=assess_balance(
                scope_level="facility",
                dimensions=[BalanceDimension("energy", IMBALANCED)],
            ),
            hypothesis_status=CAUSAL_SUPPORT,
        )

        decision = evaluate_case(case)

        self.assertEqual(decision.next_stage, SIMULATE_ISLAH)
        self.assertFalse(decision.requires_human_review)

    def test_replicated_support_still_requires_human_implementation_review(self):
        case = EcoIQOSCase(
            case_id="KZ-TEST-3",
            domain="mining",
            objective="Reduce water imbalance.",
            flow_graph=valid_graph(),
            mizan=assess_balance(
                scope_level="region",
                dimensions=[BalanceDimension("water", IMBALANCED)],
            ),
            hypothesis_status=REPLICATED_CAUSAL_SUPPORT,
        )

        decision = evaluate_case(case)

        self.assertEqual(decision.next_stage, HUMAN_REVIEW_FOR_IMPLEMENTATION)
        self.assertTrue(decision.requires_human_review)

    def test_hard_constraint_blocks_even_when_other_dimension_is_healthy(self):
        case = EcoIQOSCase(
            case_id="KZ-TEST-4",
            domain="manufacturing",
            objective="Increase production efficiency.",
            flow_graph=valid_graph(),
            mizan=assess_balance(
                scope_level="facility",
                dimensions=[BalanceDimension("economic", HEALTHY)],
                constraints=[
                    MizanConstraint(
                        key="worker_life_safety",
                        breached=True,
                        category="safety",
                        description="Life-safety limit breached.",
                        source="verified-site-rule",
                    )
                ],
            ),
            hypothesis_status=REPLICATED_CAUSAL_SUPPORT,
        )

        self.assertEqual(
            evaluate_case(case).next_stage,
            HUMAN_REVIEW_REQUIRED,
        )

    def test_explicit_mizan_conflict_stops_automatic_progression(self):
        case = EcoIQOSCase(
            case_id="KZ-TEST-CONFLICT",
            domain="water",
            objective="Balance industrial and household water use.",
            flow_graph=valid_graph(),
            mizan=assess_balance(
                scope_level="region",
                dimensions=[
                    BalanceDimension("economic", HEALTHY),
                    BalanceDimension("water", HEALTHY),
                ],
                conflicts=[
                    MizanConflict(
                        key="industrial_vs_household_water",
                        dimensions=("economic", "water"),
                        description="Two legitimate uses require a human allocation decision.",
                    )
                ],
            ),
            hypothesis_status=REPLICATED_CAUSAL_SUPPORT,
        )

        decision = evaluate_case(case)

        self.assertEqual(decision.next_stage, HUMAN_REVIEW_REQUIRED)
        self.assertTrue(decision.requires_human_review)

    def test_invalid_flow_graph_stops_the_pipeline(self):
        graph = UniversalFlowGraph(
            nodes=(FlowNode("process", "Process", "process"),),
            edges=(FlowEdge("bad", "missing", "process", "water", value=1, unit="m3"),),
        )
        case = EcoIQOSCase(
            case_id="KZ-TEST-5",
            domain="water",
            objective="Reduce water loss.",
            flow_graph=graph,
            mizan=assess_balance(
                scope_level="region",
                dimensions=[BalanceDimension("water", IMBALANCED)],
            ),
            hypothesis_status=CAUSAL_SUPPORT,
        )

        self.assertEqual(evaluate_case(case).next_stage, REPAIR_FLOW_GRAPH)
