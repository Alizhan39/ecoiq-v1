from unittest import TestCase

from mizan.system_balance import (
    CRITICAL,
    HEALTHY,
    IMBALANCED,
    INSUFFICIENT_DATA,
    WATCH,
    BalanceDimension,
    MizanConflict,
    MizanConstraint,
    assess_balance,
)


class MizanSystemBalanceTests(TestCase):
    def test_unknown_dimensions_remain_insufficient_data(self):
        result = assess_balance(
            scope_level="company",
            dimensions=[
                BalanceDimension("energy", INSUFFICIENT_DATA),
                BalanceDimension("water", INSUFFICIENT_DATA),
            ],
        )

        self.assertEqual(result.status, INSUFFICIENT_DATA)
        self.assertFalse(result.requires_islah)

    def test_worst_known_dimension_controls_status_without_averaging(self):
        result = assess_balance(
            scope_level="facility",
            dimensions=[
                BalanceDimension("economic", HEALTHY),
                BalanceDimension("energy", WATCH),
                BalanceDimension("water", IMBALANCED),
            ],
        )

        self.assertEqual(result.status, IMBALANCED)
        self.assertTrue(result.requires_islah)

    def test_hard_constraint_blocks_local_optimisation(self):
        result = assess_balance(
            scope_level="facility",
            dimensions=[BalanceDimension("economic", HEALTHY)],
            constraints=[
                MizanConstraint(
                    key="worker_life_safety",
                    breached=True,
                    category="safety",
                    description="A verified life-safety constraint was breached.",
                    source="site-safety-standard-v1",
                )
            ],
        )

        self.assertEqual(result.status, CRITICAL)
        self.assertTrue(result.human_decision_required)
        self.assertEqual(len(result.breached_constraints), 1)

    def test_conflict_requires_human_decision(self):
        result = assess_balance(
            scope_level="region",
            dimensions=[
                BalanceDimension("economic", HEALTHY),
                BalanceDimension("water", WATCH),
            ],
            conflicts=[
                MizanConflict(
                    key="industrial_vs_household_water",
                    dimensions=("economic", "water"),
                    description="Industrial output and household water security conflict.",
                )
            ],
        )

        self.assertTrue(result.human_decision_required)

    def test_numeric_threshold_requires_a_source(self):
        with self.assertRaises(ValueError):
            BalanceDimension(
                "water",
                WATCH,
                current_value=82,
                threshold=90,
            )
