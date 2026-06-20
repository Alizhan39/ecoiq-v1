"""
CI/test guardrail for the Tazkiyah 114 pathway mapping (pathways.json).

Reuses validate_pathways() so a broken mapping fails the test suite. No DB access.
"""
import json

from django.test import SimpleTestCase

from core.management.commands.validate_tazkiyah114_seeds import (
    DEFAULT_PATHWAYS_PATH,
    validate_pathways,
)


class Tazkiyah114PathwayValidationTests(SimpleTestCase):
    def test_pathway_mapping_is_valid(self):
        errors = validate_pathways()
        self.assertEqual(errors, [], "Pathway validation found issues:\n" + "\n".join(errors))

    def test_expected_counts(self):
        data = json.loads(DEFAULT_PATHWAYS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(data["pathways"]), 10)
        self.assertEqual(len(data["struggles"]), 12)

    def test_validator_catches_broken_path(self):
        errors = validate_pathways("/nonexistent/pathways.json")
        self.assertTrue(errors)
