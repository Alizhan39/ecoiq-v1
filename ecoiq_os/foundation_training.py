"""Offline, reproducible synthetic *operational anomaly triage* training.

This is NOT a Qur'an model, moral classifier, causal inference engine, real
Business Plan score or production candidate. The synthetic latent generator
is artificial; performance does not generalise to real-company outcomes.
The existing deterministic kernel and human approval remain authoritative.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    balanced_accuracy_score, confusion_matrix, precision_score, recall_score,
)
from sklearn.model_selection import GroupShuffleSplit

from ecoiq_os.domains import DOMAINS
from ecoiq_os.foundation_catalog import INITIAL_KPI_KEYS, KPI_KEYS

SEED = 20261030


@dataclass(frozen=True)
class SyntheticDataset:
    values: np.ndarray
    labels: np.ndarray
    project_ids: np.ndarray
    domain_keys: np.ndarray


def generate_synthetic_cases(*, sites_per_domain: int = 48,
                             periods_per_site: int = 3, seed: int = SEED) -> SyntheticDataset:
    """Simulate patterns of imperfect measurement with unknowns as np.nan.

    Each site carries a hidden risk factor; periods from a site MUST NOT
    cross the train/test boundary. No real company, person or scripture is read.
    """
    if type(sites_per_domain) is not int or not 16 <= sites_per_domain <= 100:
        raise ValueError("sites_per_domain must be 16..100")
    if type(periods_per_site) is not int or not 2 <= periods_per_site <= 8:
        raise ValueError("periods_per_site must be 2..8")
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("seed must be a 32-bit unsigned integer")
    rng = np.random.default_rng(seed)
    values, labels, project_ids, domain_keys = [], [], [], []
    feature_count = len(KPI_KEYS)

    for domain_index, domain in enumerate(DOMAINS):
        # Synthetic domain shifts are deliberately small and arbitrary.
        domain_shift = (domain_index % 5 - 2) * 0.025
        for site in range(sites_per_domain):
            project_id = f"SYNTH-{domain.key}-{site:03d}"
            hidden_site_risk = rng.beta(2.3, 3.6)
            for period in range(periods_per_site):
                # Hidden ground truth is simulated, never inferred from faith.
                shock = rng.normal(0, 0.14)
                latent = float(np.clip(hidden_site_risk + domain_shift + shock, 0, 1))
                hazard_probability = float(
                    1.0 / (1.0 + np.exp(-8.0 * (latent - 0.52)))
                )
                simulated_event = int(rng.random() < hazard_probability)
                sensitivities = 0.45 + 0.13 * (np.arange(feature_count) % 5)
                signals = np.clip(
                    0.12 + sensitivities * latent
                    + rng.normal(0, 0.19, feature_count),
                    0, 1,
                )
                # Missing is explicitly not zero. No fake mean imputation.
                missing = rng.random(feature_count) < (0.06 + 0.07 * latent)
                signals[missing] = np.nan
                values.append(signals)
                labels.append(simulated_event)
                project_ids.append(project_id)
                domain_keys.append(domain.key)

    return SyntheticDataset(
        values=np.asarray(values, dtype=np.float64),
        labels=np.asarray(labels, dtype=np.int8),
        project_ids=np.asarray(project_ids),
        domain_keys=np.asarray(domain_keys),
    )


def _feature_matrix(values: np.ndarray, selected: tuple[int, ...]) -> np.ndarray:
    """Signed missing sentinel AND explicit missingness mask. No data leakage."""
    subset = values[:, selected]
    missing = np.isnan(subset)
    return np.column_stack((np.where(missing, -1.0, subset), missing.astype(float)))


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, object]:
    tn, fp, fn, tp = (int(x) for x in confusion_matrix(
        actual, predicted, labels=[0, 1],
    ).ravel())
    return {
        "balanced_accuracy": round(float(balanced_accuracy_score(actual, predicted)), 4),
        "precision_for_simulated_event": round(float(precision_score(actual, predicted, zero_division=0)), 4),
        "recall_for_simulated_event": round(float(recall_score(actual, predicted, zero_division=0)), 4),
        "true_negative": tn, "false_positive": fp,
        "false_negative": fn, "true_positive": tp,
    }


def train_synthetic_foundation(*, seed: int = SEED,
                               sites_per_domain: int = 48) -> dict[str, object]:
    """Compare 20 KPI inputs vs 33; report honest held-out diagnostics.

    No model is persisted; no ML write path or deployment, no network, no
    external provider, no real evidence, no surah embeddings.
    """
    dataset = generate_synthetic_cases(seed=seed, sites_per_domain=sites_per_domain)
    X = dataset.values
    y = dataset.labels
    split = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed)
    train_idx, test_idx = next(split.split(X, y, groups=dataset.project_ids))
    train_sites = set(dataset.project_ids[train_idx])
    test_sites = set(dataset.project_ids[test_idx])
    if train_sites & test_sites:
        raise AssertionError("Data leakage: site present in train and test.")
    if len(np.unique(y[train_idx])) != 2 or len(np.unique(y[test_idx])) != 2:
        raise ValueError("Synthetic target has only one class in a split")

    # 20-item initial baseline is the first candidate subset; 33 is an
    # ablation experiment, not 33x114 scriptural supervision.
    indices = {
        "initial_20": tuple(KPI_KEYS.index(key) for key in INITIAL_KPI_KEYS),
        "expanded_33": tuple(range(len(KPI_KEYS))),
    }
    experiments = {}
    for name, selected in indices.items():
        train_features = _feature_matrix(X[train_idx], selected)
        test_features = _feature_matrix(X[test_idx], selected)

        baseline = DummyClassifier(strategy="most_frequent")
        baseline.fit(train_features, y[train_idx])
        model = RandomForestClassifier(
            n_estimators=64, max_depth=7, min_samples_leaf=5,
            random_state=seed, n_jobs=1,
        )
        model.fit(train_features, y[train_idx])
        predictions = model.predict(test_features)

        # Out-of-domain validation: never train on the construction domain.
        unseen_mask = dataset.domain_keys == "construction"
        other_mask = ~unseen_mask
        domains = set(dataset.domain_keys[other_mask])
        if "construction" in domains or not np.any(unseen_mask):
            raise AssertionError("Holdout domain split invalid")
        domain_model = RandomForestClassifier(
            n_estimators=64, max_depth=7, min_samples_leaf=5,
            random_state=seed, n_jobs=1,
        )
        domain_model.fit(_feature_matrix(X[other_mask], selected), y[other_mask])
        other_predictions = domain_model.predict(_feature_matrix(X[unseen_mask], selected))

        experiments[name] = {
            "feature_count": len(selected),
            "site_group_holdout": _metrics(y[test_idx], predictions),
            "site_group_dummy_baseline": _metrics(
                y[test_idx], baseline.predict(test_features),
            ),
            "construction_domain_holdout": _metrics(y[unseen_mask], other_predictions),
            "out_of_domain_validation_is_synthetic": True,
        }

    digest = hashlib.sha256()
    digest.update(np.nan_to_num(X, nan=-1).astype("<f8").tobytes())
    digest.update(y.tobytes())
    return {
        "training_version": "synthetic_kpi_triage_v1",
        "seed": seed,
        "dataset_sha256": digest.hexdigest(),
        "dataset_rows": len(y),
        "number_of_domains": len(DOMAINS),
        "number_of_independent_sites": len(set(dataset.project_ids)),
        "group_holdout_train_sites": len(train_sites),
        "group_holdout_test_sites": len(test_sites),
        "duplicate_site_ids_across_splits": 0,
        "simulated_event_prevalence": round(float(y.mean()), 4),
        "experiments": experiments,
        "all_data_synthetic": True,
        "model_saved": False,
        "real_world_accuracy_measured": False,
        "scriptural_corpus_used": False,
        "religious_classification_permitted": False,
        "causal_inference_performed": False,
        "automated_business_actions_permitted": False,
        "external_ai_called": False,
    }


def main() -> int:
    from ecoiq_os.foundation_catalog import catalogue_summary

    result = {
        "catalogue": catalogue_summary(),
        "synthetic_training": train_synthetic_foundation(),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
