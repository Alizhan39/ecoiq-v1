"""Domain crosswalk must reuse existing KPI definitions, never invent approval."""
from unittest import TestCase

from ecoiq_os.formula_registry import FORMULAS_BY_KEY
from islamic_knowledge.governance_domains import GOVERNANCE_DOMAINS
from islamic_knowledge.governance_kpi_crosswalk import (
    candidate_kpis_for_domain,
    governance_crosswalk_coverage,
)


class GovernanceKPICrosswalkTests(TestCase):
    def test_twelve_domains_link_existing_versioned_kpi_candidates(self):
        rows = [candidate_kpis_for_domain(domain.code) for domain in GOVERNANCE_DOMAINS]
        self.assertEqual(len(rows), 12)
        self.assertTrue(all(rows))
        for row in rows:
            for link in row:
                self.assertIn(link["formula_key"], FORMULAS_BY_KEY)
                self.assertEqual(
                    link["formula_validation_status"],
                    FORMULAS_BY_KEY[link["formula_key"]].validation_status,
                )
                self.assertFalse(link["approved_for_implementation"])

    def test_crosswalk_reuses_all_twenty_candidate_definitions(self):
        result = governance_crosswalk_coverage()
        self.assertEqual(result["domain_count"], 12)
        self.assertEqual(result["registry_kpi_count"], 20)
        self.assertEqual(set(result["linked_formula_keys"]), set(FORMULAS_BY_KEY))
        self.assertEqual(result["unlinked_formula_keys"], ())
        self.assertFalse(result["evidence_verified"])
        self.assertEqual(result["link_status"], "RESEARCH_ONLY")

    def test_no_verified_claims_scripture_or_compliance_in_operational_projection(self):
        for domain in GOVERNANCE_DOMAINS:
            for link in candidate_kpis_for_domain(domain.code):
                self.assertEqual(
                    set(link), {
                        "formula_key", "formula_title", "formula_validation_status",
                        "link_type", "evidence_status", "legal_compliance_verdict",
                        "shariah_verdict", "approved_for_implementation",
                    },
                )
                self.assertEqual(link["link_type"], "CONTEXT_INDICATOR_ONLY")
                self.assertEqual(link["evidence_status"], "NOT_ASSESSED")
                self.assertIsNone(link["legal_compliance_verdict"])
                self.assertIsNone(link["shariah_verdict"])
                self.assertTrue(str(link).isascii())
                self.assertNotIn("ال", str(link))

    def test_unknown_domain_fails_closed(self):
        with self.assertRaises(KeyError):
            candidate_kpis_for_domain("99")
