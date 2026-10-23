"""Standard-library unit tests: python -m unittest gold_intelligence.tests_targeting"""
import unittest

from gold_intelligence.services.gold_targeting import evaluate_target, rank_targets, WEIGHTS


def evidence(value):
    return {
        "value": value, "source": "field survey",
        "reference": "signed-report-2026-01",
        "observed_at": "2026-10-01", "method": "expert-normalized evidence review",
    }


class TargetingTests(unittest.TestCase):
    def test_missing_never_becomes_zero_or_fifty(self):
        result = evaluate_target({"id": "A", "evidence": {"host_rock_favourability": evidence(1)}})
        self.assertIsNone(result["score"])
        self.assertEqual(result["evidence_coverage"], .25)
        self.assertIsNone(result["feature_values"]["structure_favourability"])
        self.assertFalse(result["drilling_authorized"])

    def test_full_evidence_can_produce_descriptive_index(self):
        result = evaluate_target({"id": "B", "rights_status": "held_by_applicant",
                                  "evidence": {k: evidence(.8) for k in WEIGHTS}})
        self.assertEqual(result["score"], 80.)
        self.assertEqual(result["eligibility"], "human_geologist_review_required")
        self.assertFalse(result["score_is_probability"])
        self.assertIsNone(result["resource_estimate"])

    def test_unverified_demo_and_out_of_range_fail(self):
        for bad in (-1, 1.1, True, float("nan")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                evaluate_target({"id": "C", "evidence": {"alteration_support": evidence(bad)}})
        item = evidence(.8)
        item["is_demo"] = True
        with self.assertRaises(ValueError):
            evaluate_target({"id": "D", "evidence": {"alteration_support": item}})

    def test_unknown_rights_not_eligible_for_drilling(self):
        item = evaluate_target({"id": "E", "evidence": {k: evidence(.9) for k in WEIGHTS}})
        self.assertEqual(item["eligibility"], "rights_review_required")
        self.assertFalse(item["drilling_authorized"])

    def test_rank_preserves_unscored(self):
        a = {"id": "A"}
        b = {"id": "B", "evidence": {k: evidence(.5) for k in WEIGHTS}}
        self.assertEqual([x["id"] for x in rank_targets([a, b])], ["B", "A"])


if __name__ == "__main__":
    unittest.main()
