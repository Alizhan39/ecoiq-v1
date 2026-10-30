"""Foundation synthetic training contracts; no religious supervision or customer data."""
from __future__ import annotations

import unittest

import numpy as np

from ecoiq_os.domains import DOMAINS
from ecoiq_os.foundation_catalog import (
    CATEGORIES, INITIAL_KPI_KEYS, KPI_CATALOG, KPI_KEYS,
    catalogue_summary, review_queue_page,
)
from ecoiq_os.foundation_training import (
    _feature_matrix, generate_synthetic_cases, train_synthetic_foundation,
)
from islamic_knowledge.catalog import divine_names, surahs


class FoundationCatalogueTests(unittest.TestCase):
    def test_candidate_kpis_and_initial_business_plan_subset(self):
        self.assertEqual(len(KPI_CATALOG), 33)
        self.assertEqual(len(KPI_KEYS), len(set(KPI_KEYS)))
        self.assertEqual(len(INITIAL_KPI_KEYS), 20)
        self.assertEqual(set(k.category for k in KPI_CATALOG), set(CATEGORIES))
        self.assertTrue(set(INITIAL_KPI_KEYS) <= set(KPI_KEYS))
        self.assertTrue(all(k.unit_hint and k.principle_lenses for k in KPI_CATALOG))

    def test_reuses_offline_surah_and_name_indexes_without_fabricating_verse_links(self):
        summary = catalogue_summary()
        self.assertEqual(summary["surah_metadata_count"], 114)
        self.assertEqual(summary["divine_name_inventory_count"], 99)
        self.assertEqual(summary["potential_review_cells"], 3762)
        self.assertEqual(summary["reviewed_kpi_surah_links"], 0)
        self.assertEqual(summary["verified_religious_scores"], 0)
        self.assertEqual(len(surahs()), 114)
        self.assertEqual(len(divine_names()), 99)
        self.assertFalse(summary["model_training_permission_from_religious_text"])

    def test_all_unreviewed_pairs_have_no_verse_or_fake_scholarly_authority(self):
        first = review_queue_page(start=0, limit=100)
        last = review_queue_page(start=3761, limit=100)
        self.assertEqual(first["total"], 3762)
        self.assertEqual(first["tasks"][0]["surah"], 1)
        self.assertEqual(first["tasks"][0]["candidate_kpi"], KPI_KEYS[0])
        self.assertEqual(last["tasks"][-1]["surah"], 114)
        self.assertEqual(last["tasks"][-1]["candidate_kpi"], KPI_KEYS[-1])
        self.assertEqual(len(last["tasks"]), 1)
        for item in first["tasks"] + last["tasks"]:
            self.assertEqual(item["status"], "UNREVIEWED")
            self.assertIsNone(item["verse_locator"])
            self.assertIsNone(item["interpretation"])
            self.assertIsNone(item["source_record_id"])
            self.assertIsNone(item["scholarly_receipt"])
            self.assertFalse(item["approved_for_training"])

    def test_review_queue_is_bounded_and_rejects_invalid_inputs(self):
        for options in (
            {"start": -1}, {"start": True}, {"limit": 0},
            {"limit": 101}, {"limit": 2.5}, {"start": "1"},
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                review_queue_page(**options)
        self.assertEqual(review_queue_page(start=3762)["tasks"], [])


class FoundationTrainingTests(unittest.TestCase):
    def test_synthetic_site_periods_domain_count_and_unknown_encoding(self):
        data = generate_synthetic_cases(sites_per_domain=16, periods_per_site=2)
        self.assertEqual(data.values.shape, (len(DOMAINS) * 16 * 2, 33))
        self.assertEqual(len(set(data.project_ids)), len(DOMAINS) * 16)
        self.assertEqual(len(set(data.domain_keys)), len(DOMAINS))
        self.assertTrue(np.isnan(data.values).any())
        self.assertTrue(np.isfinite(data.values[~np.isnan(data.values)]).all())
        self.assertTrue(np.all((data.labels == 0) | (data.labels == 1)))
        self.assertTrue(np.array_equal(
            data.values, generate_synthetic_cases(sites_per_domain=16, periods_per_site=2).values,
            equal_nan=True,
        ))

    def test_unknown_is_not_zero_in_model_features(self):
        values = np.array([[0, np.nan], [0.4, 0]], dtype=float)
        encoded = _feature_matrix(values, (0, 1))
        self.assertEqual(encoded.tolist(), [
            [0, -1, 0, 1], [0.4, 0, 0, 0],
        ])

    def test_training_reports_group_isolation_baseline_and_domain_holdout(self):
        report = train_synthetic_foundation(sites_per_domain=16)
        self.assertEqual(report["number_of_domains"], len(DOMAINS))
        self.assertEqual(report["dataset_rows"], len(DOMAINS) * 16 * 3)
        self.assertEqual(report["duplicate_site_ids_across_splits"], 0)
        self.assertEqual(report["number_of_independent_sites"], len(DOMAINS) * 16)
        self.assertEqual(set(report["experiments"]), {"initial_20", "expanded_33"})
        self.assertEqual(report["experiments"]["initial_20"]["feature_count"], 20)
        self.assertEqual(report["experiments"]["expanded_33"]["feature_count"], 33)
        for metrics in report["experiments"].values():
            for key in (
                "site_group_holdout", "site_group_dummy_baseline",
                "construction_domain_holdout",
            ):
                scores = metrics[key]
                self.assertTrue(0 <= scores["balanced_accuracy"] <= 1)
                self.assertEqual(
                    sum(scores[k] for k in (
                        "true_negative", "false_positive", "false_negative", "true_positive",
                    )),
                    (report["dataset_rows"] // len(DOMAINS) if key == "construction_domain_holdout"
                     else report["group_holdout_test_sites"] * 3),
                )
        self.assertTrue(report["all_data_synthetic"])
        for claim in (
            "model_saved", "real_world_accuracy_measured",
            "scriptural_corpus_used", "religious_classification_permitted",
            "causal_inference_performed", "automated_business_actions_permitted",
            "external_ai_called",
        ):
            self.assertFalse(report[claim])

    def test_repeatability_and_invalid_training_bounds(self):
        a = train_synthetic_foundation(sites_per_domain=16)
        b = train_synthetic_foundation(sites_per_domain=16)
        self.assertEqual(a["dataset_sha256"], b["dataset_sha256"])
        self.assertEqual(a["experiments"], b["experiments"])
        for invalid in (0, 8, 15, 101, True, "50"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                generate_synthetic_cases(sites_per_domain=invalid)


if __name__ == "__main__":
    unittest.main()
