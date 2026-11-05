"""Canonical identity, bounded pagination and honest inventory semantics."""
from copy import deepcopy
from dataclasses import replace
from io import StringIO
import json
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.esg_principles_data import PRINCIPLES
from ecoiq_os.foundation_catalog import KPI_CATALOG, catalogue_summary
from ecoiq_os.formula_registry import PROVISIONAL_KPI_FORMULAS
from ecoiq_os.review_registry import (
    RegistryEntry, canonical_knowledge_definitions, registry_page, registry_summary,
)
from intelligence_analytics_engine.reform_capabilities import REFORM_CAPABILITIES
from islamic_knowledge.catalog import divine_names, surahs
from islamic_knowledge.governance_domains import GOVERNANCE_DOMAINS


class ReviewRegistryTests(SimpleTestCase):
    def test_counts_are_typed_catalogue_counts_not_invented_principle_total(self):
        summary = registry_summary()
        counts = summary["counts_by_kind"]
        self.assertEqual(counts, {
            "operational_principle": len(PRINCIPLES),
            "candidate_kpi": len(KPI_CATALOG),
            "formula_candidate": len(PROVISIONAL_KPI_FORMULAS),
            "knowledge_definition": len(canonical_knowledge_definitions()),
            "governance_domain": len(GOVERNANCE_DOMAINS),
            "reform_capability": len(REFORM_CAPABILITIES),
            "surah_reference": len(surahs()),
            "divine_name_reference": len(divine_names()),
            "kpi_surah_review_pair": catalogue_summary()["potential_review_cells"],
        })
        self.assertEqual(summary["total_entries"], sum(counts.values()))
        self.assertEqual(counts["kpi_surah_review_pair"], 3762)
        self.assertEqual(summary["source_verified_entries"], 0)
        self.assertFalse(summary["decision_ready"])
        self.assertEqual(summary["count_semantics"], "TYPED_INVENTORY_NOT_COMPLETED_ASSESSMENTS")

    def test_all_pages_have_unique_ids_complete_count_and_resolved_links(self):
        rows = []
        start = 0
        digest = None
        while start is not None:
            page = registry_page(start=start, limit=100)
            self.assertLessEqual(len(page["entries"]), 100)
            if digest is None:
                digest = page["registry"]["content_sha256"]
            self.assertEqual(page["registry"]["content_sha256"], digest)
            rows.extend(page["entries"])
            start = page["next_start"]
        ids = {row["id"] for row in rows}
        self.assertEqual(len(rows), len(ids))
        self.assertEqual(len(rows), page["total"])
        self.assertTrue(all(target in ids for row in rows for target in row["related_ids"]))
        self.assertTrue(all(row["source_verified"] is False and row["decision_ready"] is False for row in rows))
        self.assertTrue(all(len(row["content_sha256"]) == 64 and row["source_file"] for row in rows))

    def test_pair_pages_preserve_existing_review_queue_boundary_and_status(self):
        first = registry_page(kind="kpi_surah_review_pair", limit=1)
        self.assertEqual(first["total"], 3762)
        row = first["entries"][0]
        self.assertEqual(row["id"], f"review-kpi-surah:{KPI_CATALOG[0].key}:001")
        self.assertEqual(row["review_status"], "UNREVIEWED")
        self.assertEqual(row["related_ids"], (f"kpi:{KPI_CATALOG[0].key}", "surah:001"))
        next_kpi = registry_page(kind="kpi_surah_review_pair", start=len(surahs()), limit=1)
        self.assertEqual(next_kpi["entries"][0]["id"], f"review-kpi-surah:{KPI_CATALOG[1].key}:001")
        last = registry_page(kind="kpi_surah_review_pair", start=3761, limit=100)
        self.assertEqual(len(last["entries"]), 1)
        self.assertEqual(last["entries"][0]["id"], f"review-kpi-surah:{KPI_CATALOG[-1].key}:114")
        self.assertIsNone(last["next_start"])
        self.assertEqual(registry_page(start=10**9)["entries"], [])

    def test_name_ids_preserve_enumeration_and_do_not_generate_cross_products(self):
        name = next(iter(divine_names().values()))
        page = registry_page(kind="divine_name_reference", limit=100)
        self.assertEqual(page["total"], len(divine_names()))
        self.assertEqual(page["entries"][0]["id"], f"name:{name.enumeration}:{name.key}")
        self.assertEqual(page["entries"][0]["review_status"], name.review_status)
        self.assertNotIn("arabic", page["entries"][0])
        self.assertNotIn("passage", page["entries"][0])
        self.assertNotIn("name_surah_pair", page["registry"]["counts_by_kind"])

    def test_fingerprint_tracks_canonical_content_and_return_values_are_detached(self):
        summary = registry_summary()
        changed = deepcopy(PRINCIPLES)
        changed[0]["question"] += " Revised scope."
        before_id = registry_page(limit=1)["entries"][0]["id"]
        with patch("ecoiq_os.review_registry.PRINCIPLES", changed):
            self.assertNotEqual(summary["content_sha256"], registry_summary()["content_sha256"])
            self.assertEqual(before_id, registry_page(limit=1)["entries"][0]["id"])
        summary["counts_by_kind"].clear()
        self.assertTrue(registry_summary()["counts_by_kind"])

    def test_duplicates_and_dangling_targets_fail_closed(self):
        row = RegistryEntry("kpi:a", "candidate_kpi", "source.py", "a", "a" * 64, "UNREVIEWED")
        for rows in ([row, row], [replace(row, related_ids=("kpi:missing",))]):
            with self.subTest(rows=rows), patch("ecoiq_os.review_registry._entries", return_value=iter(rows)):
                with self.assertRaises(ValueError):
                    registry_summary()

    def test_invalid_or_unbounded_page_requests_are_rejected(self):
        for kwargs in ({"kind": "all-approved"}, {"kind": False}, {"start": True},
                       {"start": -1}, {"limit": True}, {"limit": 0}, {"limit": 101}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                registry_page(**kwargs)

    def test_operator_command_emits_summary_or_bounded_work_items(self):
        output = StringIO()
        call_command("review_registry_inventory", stdout=output)
        self.assertEqual(json.loads(output.getvalue()), registry_summary())
        output = StringIO()
        call_command("review_registry_inventory", "--entries", "--kind", "kpi_surah_review_pair",
                     "--start", "3761", "--limit", "10", stdout=output)
        self.assertEqual(len(json.loads(output.getvalue())["entries"]), 1)
        with self.assertRaises(CommandError):
            call_command("review_registry_inventory", "--entries", "--limit", "101", stdout=StringIO())
        with self.assertRaises(CommandError):
            call_command("review_registry_inventory", "--kind", "candidate_kpi", stdout=StringIO())
