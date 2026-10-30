"""Situation Intelligence: formula, provenance, and scriptural review safeguards."""
from unittest import TestCase

from ecoiq_os.decision_islah import build_preliminary_brief
from ecoiq_os.situation_guidance import assemble_situation_guidance
from islamic_knowledge.catalog import QuranReference
from islamic_knowledge.principles import DRAFT_PRINCIPLES


def brief(input_value=1000, loss_value=120):
    return build_preliminary_brief(
        case_id="SITE-SYNTH-1", domain="construction",
        process_name="Synthetic delivery", resource_type="material",
        period="2026-10", unit="kg", reported_input=input_value,
        reported_loss=loss_value,
    )


class SituationGuidanceTests(TestCase):
    def test_reported_loss_not_claimed_avoidable_or_savings(self):
        result = assemble_situation_guidance(brief())
        self.assertEqual(result["situation"], "REPORTED_LOSS_REQUIRES_INVESTIGATION")
        self.assertEqual(result["formulas"][0]["value"], 12.0)
        self.assertEqual(result["formulas"][1]["value"], 880.0)
        self.assertIsNone(result["formulas"][2]["value"])
        self.assertFalse(result["ai_model_called"])
        self.assertEqual(result["next_step"], "COLLECT_EVIDENCE")
        safety = result["safety_constraints"]
        for claim in ("causal_conclusion", "religious_approval", "shariah_verdict",
                      "savings_forecast"):
            self.assertIsNone(safety[claim])
        self.assertFalse(safety["implementation_permitted"])
        self.assertFalse(safety["independently_verified"])

    def test_missing_and_zero_are_not_confused(self):
        missing = assemble_situation_guidance(brief(1000, None))
        zero = assemble_situation_guidance(brief(1000, 0))
        self.assertIsNone(missing["formulas"][0]["value"])
        self.assertEqual(missing["situation"], "INSUFFICIENT_REPORTED_DATA")
        self.assertEqual(zero["formulas"][0]["value"], 0.0)
        self.assertEqual(zero["situation"], "NO_REPORTED_LOSS_IN_THIS_BOUNDARY")
        self.assertFalse(any(
            lens["concept"] == "israf" for lens in zero["guidance_lenses"]
        ))

    def test_zero_denominator_does_not_fabricate_rate(self):
        result = assemble_situation_guidance(brief(0, 0))
        self.assertIsNone(result["formulas"][0]["value"])
        self.assertEqual(result["formulas"][1]["value"], 0.0)
        self.assertEqual(result["situation"], "INSUFFICIENT_REPORTED_DATA")

    def test_quran_references_are_exact_canonical_locators_only(self):
        guidance = assemble_situation_guidance(brief())
        definitions = {item.concept: item for item in DRAFT_PRINCIPLES}
        concepts = [row["concept"] for row in guidance["guidance_lenses"]]
        self.assertEqual(concepts, ["amanah", "mizan", "israf", "islah", "adl"])
        for row in guidance["guidance_lenses"]:
            definition = definitions[row["concept"]]
            self.assertEqual(
                [item["locator"] for item in row["references"]],
                [reference.locator for reference in definition.quran_references],
            )
            for item in row["references"]:
                self.assertTrue(item["url"].startswith("https://quran.com/"))
                self.assertNotIn("javascript:", item["url"])
            self.assertEqual(row["review_state"], "SCHOLAR_REVIEW_REQUIRED")
            self.assertFalse(row["verse_text_provided"])
            self.assertFalse(row["tafsir_provided"])
            self.assertIsNone(row["shariah_verdict"])
        self.assertEqual(QuranReference(55, 7, 9).locator, "55:7-9")

    def test_unsafe_approval_and_fake_model_brief_rejected(self):
        for mutation in (
            {"implementation_permitted": True},
            {"engine": "LLM_AGENT_OUTPUT"},
        ):
            case = {**brief(), **mutation}
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                assemble_situation_guidance(case)

    def test_invalid_input_cannot_generate_guidance(self):
        for input_value, loss_value in [
            (1, 2), (-3, 1), (float("nan"), 2),
            (float("inf"), 2), (True, 0),
        ]:
            with self.subTest(values=(input_value, loss_value)):
                if input_value is True:
                    # Validate type without coercing booleans.
                    with self.assertRaises(ValueError):
                        assemble_situation_guidance({**brief(),
                            "observed_input": True})
                else:
                    with self.assertRaises(ValueError):
                        brief(input_value, loss_value)
