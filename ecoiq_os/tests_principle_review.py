"""Inventory coverage is never mistaken for assessed principle compliance."""
from copy import deepcopy
from unittest.mock import patch

from django.test import SimpleTestCase

from core.esg_principles_data import PRINCIPLES
from ecoiq_os.formula_registry import PROVISIONAL_KPI_FORMULAS
from ecoiq_os.principle_review import build_principle_review, require_principle_review
from intelligence_analytics_engine.reform_capabilities import REFORM_CAPABILITIES
from islamic_knowledge.environmental_principles import stewardship_drafts
from islamic_knowledge.governance_domains import GOVERNANCE_DOMAINS
from islamic_knowledge.principles import DRAFT_PRINCIPLES


class PrincipleReviewTests(SimpleTestCase):
    def report(self, **changes):
        return build_principle_review(case_id="CASE-1", subject={
            "status": "REVIEW_REQUIRED", "questions": [], **changes,
        })

    def test_every_canonical_item_is_present_without_claiming_assessment(self):
        result = self.report()
        self.assertEqual(
            [item["principle_id"] for item in result["operational_principles"]],
            [item["id"] for item in PRINCIPLES],
        )
        self.assertEqual(
            [item["formula_key"] for item in result["kpi_candidates"]],
            [item.key for item in PROVISIONAL_KPI_FORMULAS],
        )
        self.assertEqual(
            [item["domain_code"] for item in result["governance_domains"]],
            [item.code for item in GOVERNANCE_DOMAINS],
        )
        self.assertEqual(
            [item["capability"] for item in result["reform_capabilities"]],
            [item.slug for item in REFORM_CAPABILITIES],
        )
        for key, count in result["inventory_counts"].items():
            self.assertEqual(len(result[key]), count)
        self.assertEqual(result["assessed_operational_principles"], 0)
        self.assertFalse(result["all_operational_principles_assessed"])
        for key in ("operational_principles", "kpi_candidates", "governance_domains"):
            self.assertTrue(all(row["status"] == "NOT_ASSESSED" for row in result[key]))

    def test_shared_knowledge_definitions_reuse_the_existing_fail_closed_gate(self):
        result = self.report()
        expected = {d.id for d in (*DRAFT_PRINCIPLES, *stewardship_drafts())}
        self.assertEqual({row["definition_id"] for row in result["knowledge_definitions"]}, expected)
        self.assertEqual(len(result["knowledge_definitions"]), len(expected))
        for item in result["knowledge_definitions"]:
            self.assertIn("MISSING_SOURCES", item["reasons"])
            self.assertIn("SCHOLAR_REVIEW_REQUIRED", item["reasons"])
            self.assertEqual(len(item["definition_sha256"]), 64)

    def test_crosswalks_remain_context_and_missing_metrics_are_explicit(self):
        result = self.report()
        for domain in result["governance_domains"]:
            for link in domain["kpi_links"]:
                self.assertEqual(link["link_type"], "CONTEXT_INDICATOR_ONLY")
                self.assertFalse(link["approved_for_implementation"])
        legal = next(row for row in result["reform_capabilities"] if row["capability"] == "legal_access")
        self.assertTrue(legal["missing_direct_kpi"])
        self.assertEqual(legal["formula_links"], ())
        self.assertTrue(all(not row["decision_ready"] for row in result["reform_capabilities"]))

    def test_server_owned_envelope_cannot_reuse_a_forged_pass(self):
        original = {
            "status": "REVIEW_REQUIRED", "questions": [],
            "decision_ready": True, "publication_permitted": True,
            "implementation_permitted": True, "approval_recorded": True,
            "requires_human_review": False, "causal_conclusion": "proven",
            "savings_forecast": 100, "mizan_score": 99,
            "production_approved": True, "independently_verified_causality": True,
            "shariah_compliant": True,
            "principle_review": {"status": "PASS"},
        }
        before = deepcopy(original)
        result = require_principle_review(original, case_id="CASE-1")
        self.assertEqual(original, before)
        for key in ("decision_ready", "publication_permitted", "implementation_permitted", "approval_recorded",
                    "production_approved", "independently_verified_causality"):
            self.assertIs(result[key], False)
        for key in ("causal_conclusion", "savings_forecast", "mizan_score"):
            self.assertIsNone(result[key])
        self.assertTrue(result["requires_human_review"])
        self.assertNotIn("shariah_compliant", result)
        self.assertEqual(result["principle_review"]["status"], "REVIEW_REQUIRED")

    def test_digests_bind_case_result_and_current_registry_content(self):
        first = self.report()
        self.assertEqual(first, self.report())
        changed = self.report(questions=[{"question": "Different question?"}])
        self.assertNotEqual(first["subject_sha256"], changed["subject_sha256"])
        self.assertEqual(first["inventory_sha256"], changed["inventory_sha256"])
        other_case = build_principle_review(case_id="CASE-2", subject={
            "status": "REVIEW_REQUIRED", "questions": [],
        })
        self.assertNotEqual(first["subject_sha256"], other_case["subject_sha256"])
        registry = deepcopy(PRINCIPLES)
        registry[0]["question"] += " Updated scope."
        with patch("ecoiq_os.principle_review.PRINCIPLES", registry):
            self.assertNotEqual(first["inventory_sha256"], self.report()["inventory_sha256"])

    def test_mutating_one_report_does_not_change_next_report_or_registry(self):
        first = self.report()
        first["operational_principles"][0]["status"] = "PASS"
        first["governance_domains"].clear()
        second = self.report()
        self.assertEqual(second["operational_principles"][0]["status"], "NOT_ASSESSED")
        self.assertEqual(len(second["governance_domains"]), len(GOVERNANCE_DOMAINS))

    def test_report_does_not_emit_internal_sacred_source_metadata(self):
        result = self.report()
        def keys(value):
            if isinstance(value, dict):
                return set(value).union(*(keys(item) for item in value.values()))
            if isinstance(value, (list, tuple)):
                return set().union(*(keys(item) for item in value))
            return set()
        self.assertFalse(keys(result) & {"surah", "ayah", "quran_hints", "quran_references", "name_keys", "arabic"})

    def test_invalid_case_or_duplicate_registry_identifier_stops_report(self):
        for case_id in (None, "", " ", "x" * 129):
            with self.subTest(case_id=case_id), self.assertRaises(ValueError):
                build_principle_review(case_id=case_id, subject={})
        with patch("ecoiq_os.principle_review.PRINCIPLES", [PRINCIPLES[0], PRINCIPLES[0]]):
            with self.assertRaises(ValueError):
                self.report()
