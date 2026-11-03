"""Regression tests: twelve domains are unapproved research, not KPI results."""
from dataclasses import FrozenInstanceError
from unittest import TestCase

from islamic_knowledge.catalog import QuranReference
from islamic_knowledge.contracts import CONCEPTS
from islamic_knowledge.governance_domains import (
    GOVERNANCE_DOMAINS,
    domain_by_code,
    operational_domain_rows,
)


EXPECTED_TAGS = (
    ("adl", "amanah", "shura"),
    ("mal", "rizq", "qist"),
    ("riba", "gharar", "zakat"),
    ("haqq", "ihsan", "amanah"),
    ("maslaha", "sadaqa", "zakat"),
    ("adl", "bayyinah", "insaf"),
    ("ilm", "tabayyun", "tafakkur"),
    ("mizan", "israf", "fasad"),
    ("rahma", "haqq", "masuliyya"),
    ("amanah", "adl", "taharri_as_sidq"),
    ("maslaha", "fiqh_al_maalat"),
    ("taqwa", "muhasaba", "hikmah"),
)


class GovernanceDomainCatalogTests(TestCase):
    def test_all_twelve_domains_have_stable_codes_and_concepts(self):
        self.assertEqual(len(GOVERNANCE_DOMAINS), 12)
        self.assertEqual(
            tuple(domain.code for domain in GOVERNANCE_DOMAINS),
            tuple(f"{i:02d}" for i in range(1, 13)),
        )
        self.assertEqual(
            tuple(tuple(tag.key for tag in domain.tags) for domain in GOVERNANCE_DOMAINS),
            EXPECTED_TAGS,
        )
        self.assertEqual(len({tag.key for domain in GOVERNANCE_DOMAINS for tag in domain.tags}), 28)

    def test_all_domains_are_internal_drafts_not_religious_approvals(self):
        for domain in GOVERNANCE_DOMAINS:
            with self.subTest(domain=domain.code):
                self.assertEqual(domain.research_status, "SCHOLAR_REVIEW_PENDING")
                self.assertGreaterEqual(len(domain.audit_questions), 2)
                self.assertTrue(domain.quran_hints)
                self.assertTrue(all(isinstance(ref, QuranReference) for ref in domain.quran_hints))
                self.assertEqual(
                    set(domain.existing_contract_concepts),
                    {t.key for t in domain.tags if t.key in CONCEPTS},
                )
                self.assertEqual(
                    set(domain.awaiting_contract_mapping),
                    {t.key for t in domain.tags if t.key not in CONCEPTS},
                )
                self.assertEqual(
                    set(domain.existing_contract_concepts)
                    & set(domain.awaiting_contract_mapping), set(),
                )

    def test_sensitive_research_metadata_never_enters_operational_projection(self):
        rows = operational_domain_rows()
        self.assertEqual(len(rows), 12)
        self.assertEqual(
            {tuple(row) for row in rows},
            {("code", "title", "audit_questions", "kpi_links", "evidence_status")},
        )
        self.assertTrue(all(row["kpi_links"] == () for row in rows))
        self.assertTrue(all(row["evidence_status"] == "NOT_ASSESSED" for row in rows))
        self.assertTrue(all(row["title"] != "Islamic Finance Research" for row in rows))
        self.assertTrue(all(row["title"].isascii() for row in rows))
        self.assertTrue(all(str(row).isascii() for row in rows))
        self.assertNotIn("4:58", str(rows))
        self.assertNotIn("Quran", str(rows))
        self.assertNotIn("Shariah", str(rows))

    def test_lookup_returns_same_immutable_object_and_rejects_unknown_codes(self):
        for domain in GOVERNANCE_DOMAINS:
            self.assertIs(domain_by_code(domain.code), domain)
        with self.assertRaises(KeyError):
            domain_by_code("99")
        with self.assertRaises(FrozenInstanceError):
            GOVERNANCE_DOMAINS[0].name_ru = "Changed"
        with self.assertRaises(TypeError):
            GOVERNANCE_DOMAINS[0].tags[0] = GOVERNANCE_DOMAINS[1].tags[0]

    def test_quran_hints_are_valid_research_locators_not_passages(self):
        for domain in GOVERNANCE_DOMAINS:
            for ref in domain.quran_hints:
                self.assertTrue(ref.locator)
                self.assertTrue(ref.surah in range(1, 115))
        self.assertEqual(
            tuple(ref.locator for ref in domain_by_code("08").quran_hints),
            ("7:31", "30:41", "55:7-9"),
        )
