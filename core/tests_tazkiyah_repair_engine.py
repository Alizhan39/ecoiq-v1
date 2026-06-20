"""
CI/test guardrail for the Tazkiyah 114 Repair Engine architecture
(repair_engine.json). Reuses validate_repair_engine(). No DB access.
"""
import json

from django.test import SimpleTestCase

from core.management.commands.validate_tazkiyah114_seeds import (
    DEFAULT_REPAIR_ENGINE_PATH,
    validate_repair_engine,
)


class Tazkiyah114RepairEngineValidationTests(SimpleTestCase):
    def test_repair_engine_is_valid(self):
        errors = validate_repair_engine()
        self.assertEqual(errors, [], "Repair engine validation found issues:\n" + "\n".join(errors))

    def test_expected_shape(self):
        data = json.loads(DEFAULT_REPAIR_ENGINE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(data["heart_wounds"]), 12)
        self.assertEqual(len(data["repair_flow_steps"]), 9)
        self.assertIn("cycle", data["sin_cycle_breaker"])
        self.assertIn("repair_cycle", data["sin_cycle_breaker"])
        self.assertIs(data["_meta"]["authoritative"], False)

    def test_validator_catches_broken_path(self):
        errors = validate_repair_engine("/nonexistent/repair_engine.json")
        self.assertTrue(errors)
