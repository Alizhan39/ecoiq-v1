from unittest import TestCase

from poverty_justice.contracts import (
    ASSOCIATION_ONLY,
    CAUSAL_SUPPORT,
    EXPLORATORY_MODELLING,
    IMPLEMENTATION_PROPOSAL,
    NOT_ALLOWED,
    POLICY_SIMULATION,
    REPLICATED_CAUSAL_SUPPORT,
    ROBUST_ASSOCIATION,
    CausalQuestion,
    CausalTestSpec,
    PopulationScope,
    TestRequirement,
    intervention_permission,
)


class PovertyJusticeContractTests(TestCase):
    def test_association_does_not_unlock_intervention(self):
        self.assertEqual(intervention_permission(ASSOCIATION_ONLY), NOT_ALLOWED)

    def test_evidence_gates_are_monotonic(self):
        self.assertEqual(
            intervention_permission(ROBUST_ASSOCIATION),
            EXPLORATORY_MODELLING,
        )
        self.assertEqual(
            intervention_permission(CAUSAL_SUPPORT),
            POLICY_SIMULATION,
        )
        self.assertEqual(
            intervention_permission(REPLICATED_CAUSAL_SUPPORT),
            IMPLEMENTATION_PROPOSAL,
        )

    def test_causal_spec_keeps_population_and_time_explicit(self):
        spec = CausalTestSpec(
            hypothesis_id="KZ-H06-v2",
            hypothesis_statement=(
                "High debt-service burden relative to household free capacity "
                "may increase financial vulnerability."
            ),
            scope=PopulationScope(
                unit="household",
                country="KZ",
                period_start="2024-01-01",
                period_end="2025-12-31",
            ),
            causal_question=CausalQuestion(
                exposure="debt_service_ratio",
                outcome="poverty_entry",
                estimand="Effect among households with comparable observed characteristics.",
            ),
            confounders=("income", "household_size", "employment"),
            tests=(
                TestRequirement("MULTILEVEL_REGRESSION"),
                TestRequirement("MATCHED_COMPARISON"),
                TestRequirement("PLACEBO"),
                TestRequirement("OUT_OF_SAMPLE"),
            ),
            temporal_order_required=True,
            survey_weights_required=True,
            minimum_sample_size=500,
        )

        payload = spec.to_dict()

        self.assertEqual(payload["scope"]["country"], "KZ")
        self.assertTrue(payload["temporal_order_required"])
        self.assertEqual(payload["intervention_permission"], NOT_ALLOWED)

    def test_confounder_cannot_also_be_mediator(self):
        with self.assertRaises(ValueError):
            CausalTestSpec(
                hypothesis_id="KZ-H02",
                hypothesis_statement="Dependency burden may increase poverty risk.",
                scope=PopulationScope(unit="household", country="KZ"),
                causal_question=CausalQuestion(
                    exposure="dependency_ratio",
                    outcome="official_poverty",
                    estimand="Adjusted household-level effect.",
                ),
                confounders=("income",),
                mediators=("income",),
            )
