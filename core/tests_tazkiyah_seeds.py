"""
CI/test guardrail for the Tazkiyah 114 surah seed dataset.

Reuses the validation logic from the management command so that a broken
content/tazkiyah114/surah_seeds.json fails the test suite. No database access.
"""
from django.test import SimpleTestCase

from core.management.commands.validate_tazkiyah114_seeds import (
    EXPECTED_FIELDS,
    validate_seeds,
)


class Tazkiyah114SeedValidationTests(SimpleTestCase):
    def test_seed_dataset_is_valid(self):
        errors = validate_seeds()
        self.assertEqual(errors, [], "Tazkiyah 114 seed validation found issues:\n" + "\n".join(errors))

    def test_expected_schema_has_18_fields(self):
        # Guards against silent edits to the expected schema shape.
        self.assertEqual(len(EXPECTED_FIELDS), 18)

    def test_validator_catches_broken_data(self):
        # Sanity: the validator actually reports problems for a bad path.
        errors = validate_seeds("/nonexistent/surah_seeds.json")
        self.assertTrue(errors)
