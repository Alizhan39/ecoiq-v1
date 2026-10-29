"""Contract tests: observed KPI never becomes invented evidence or action."""
from unittest import TestCase

from ecoiq_os.evidence import CAUSAL_SUPPORT, UNTESTED
from ecoiq_os.kernel import COLLECT_EVIDENCE, HUMAN_REVIEW_REQUIRED, RUN_FALSIFICATION
from ecoiq_os.process_diagnostic import (
    ProcessMeasurement,
    ProcessSnapshot,
    diagnose_process,
)
from mizan.system_balance import (
    IMBALANCED,
    BalanceDimension,
    MizanConstraint,
    assess_balance,
)


def snapshot(total=1000, loss=120, input_refs=("invoice-001",), loss_refs=("weighbridge-002",)):
    return ProcessSnapshot(
        case_id="CONSTRUCTION-001",
        domain="construction",
        process_name="Material receiving and waste",
        resource_type="material",
        input_measurement=ProcessMeasurement(total, "kg", "2026-10", input_refs),
        loss_measurement=ProcessMeasurement(loss, "kg", "2026-10", loss_refs),
    )


class ProcessDiagnosticTests(TestCase):
    def test_reported_loss_rate_and_flow_graph(self):
        result = diagnose_process(snapshot())
        payload = result.to_dict()

        self.assertEqual(payload["kpi"]["value"], 12.0)
        self.assertEqual(payload["kpi"]["status"], "CALCULATED_FROM_REPORTED_INPUTS")
        self.assertEqual(payload["kpi"]["evidence_refs"], ["invoice-001", "weighbridge-002"])
        self.assertFalse(payload["kpi"]["independently_verified"])
        self.assertTrue(payload["read_only"])
        self.assertTrue(result.flow_graph.is_valid)
        self.assertEqual(result.flow_graph.losses()[0].value, 120)
        self.assertEqual(payload["next_step"]["next_stage"], COLLECT_EVIDENCE)
        self.assertIn("avoidable", payload["investigation_question"])

    def test_unknown_is_null_not_zero(self):
        result = diagnose_process(snapshot(loss=None, loss_refs=()))
        payload = result.to_dict()
        self.assertIsNone(payload["kpi"]["value"])
        self.assertIsNone(payload["kpi"]["numerator"])
        self.assertEqual(payload["kpi"]["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(result.flow_graph.losses()[0].value)

    def test_measured_zero_remains_zero(self):
        result = diagnose_process(snapshot(loss=0, loss_refs=("meter-0",)))
        self.assertEqual(result.loss_rate_percent, 0)
        self.assertIsNone(result.to_dict()["investigation_question"])

    def test_zero_denominator_stays_unknown(self):
        result = diagnose_process(snapshot(total=0, loss=0))
        self.assertIsNone(result.loss_rate_percent)
        self.assertEqual(result.to_dict()["kpi"]["status"], "INSUFFICIENT_DATA")

    def test_partial_evidence_never_produces_a_rate(self):
        result = diagnose_process(snapshot(total=None, loss=50, input_refs=()))
        self.assertIsNone(result.loss_rate_percent)
        self.assertEqual(result.to_dict()["kpi"]["numerator"], 50)

    def test_invalid_numeric_inputs_are_rejected(self):
        for value in (-1, True, float("nan"), float("inf"), "50"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ProcessMeasurement(value, "kg", "2026-10", ("source",))

    def test_known_quantity_requires_source_reference(self):
        with self.assertRaises(ValueError):
            ProcessMeasurement(100, "kg", "2026-10")
        with self.assertRaises(ValueError):
            ProcessMeasurement(100, "kg", "2026-10", ("",))

    def test_incompatible_observations_are_rejected(self):
        base = snapshot()
        with self.assertRaises(ValueError):
            ProcessSnapshot(
                base.case_id, base.domain, base.process_name, base.resource_type,
                base.input_measurement,
                ProcessMeasurement(1, "litres", "2026-10", ("meter",)),
            )
        with self.assertRaises(ValueError):
            ProcessSnapshot(
                base.case_id, base.domain, base.process_name, base.resource_type,
                base.input_measurement,
                ProcessMeasurement(1, "kg", "2026-09", ("meter",)),
            )
        with self.assertRaises(ValueError):
            snapshot(total=100, loss=101)

    def test_unreviewed_causality_does_not_authorise_improvement(self):
        mizan = assess_balance(
            scope_level="process",
            dimensions=(BalanceDimension("resource_efficiency", IMBALANCED),),
        )
        result = diagnose_process(snapshot(), mizan=mizan, hypothesis_status=UNTESTED)
        self.assertEqual(result.decision.next_stage, RUN_FALSIFICATION)
        self.assertFalse(result.decision.requires_human_review)

    def test_a_breached_safety_constraint_overrides_causal_support(self):
        mizan = assess_balance(
            scope_level="process",
            dimensions=(BalanceDimension("resource_efficiency", IMBALANCED),),
            constraints=(
                MizanConstraint(
                    "worker_life_safety", True, "safety",
                    "Verified worker risk.", "safety-audit-123",
                ),
            ),
        )
        result = diagnose_process(snapshot(), mizan=mizan, hypothesis_status=CAUSAL_SUPPORT)
        self.assertEqual(result.decision.next_stage, HUMAN_REVIEW_REQUIRED)
        self.assertTrue(result.decision.requires_human_review)

    def test_invalid_domain_is_rejected(self):
        original = snapshot()
        with self.assertRaises(ValueError):
            ProcessSnapshot(
                original.case_id, "made_up", original.process_name, "material",
                original.input_measurement, original.loss_measurement,
            )

    def test_unknown_hypothesis_is_rejected(self):
        with self.assertRaises(ValueError):
            diagnose_process(snapshot(), hypothesis_status="TRUE")

    def test_no_compliance_claim_or_master_score(self):
        result = diagnose_process(snapshot()).to_dict()
        self.assertNotIn("score", result)
        self.assertNotIn("religious_compliance", result)
        self.assertNotIn("implementation_approved", result)
