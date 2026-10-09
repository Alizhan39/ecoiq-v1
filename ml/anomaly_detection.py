"""
ml/anomaly_detection.py — Isolation Forest anomaly detection for EcoIQ.

Flags companies whose feature vector is unusual relative to the peer set.
Negative anomaly_score = more anomalous (scikit-learn convention).
Threshold: contamination=0.05 (top 5% most anomalous flagged as is_anomaly=True).

Usage:
    from ml.anomaly_detection import AnomalyDetector
    detector = AnomalyDetector()
    detector.train(apply=True)
"""
from __future__ import annotations

import logging
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

MODEL_PATH  = Path(__file__).resolve().parent / 'models' / 'anomaly_iforest.joblib'
SCALER_PATH = Path(__file__).resolve().parent / 'models' / 'anomaly_scaler.joblib'


class AnomalyDetector:
    """Isolation Forest anomaly detector."""

    def __init__(self):
        self.model  = None
        self.scaler = None
        self._loaded = False

    def _load(self) -> bool:
        if self._loaded:
            return True
        try:
            import joblib
            self.model  = joblib.load(MODEL_PATH)
            self.scaler = joblib.load(SCALER_PATH)
            self._loaded = True
            return True
        except Exception as exc:
            logger.warning('Anomaly model not loaded: %s', exc)
            return False

    def train(self, companies=None, apply: bool = False, *, output_dir=None) -> dict:
        """
        Train Isolation Forest on all companies with scores.

        contamination=0.05 → flags ~5% as anomalous.
        """
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler
        from league.models import Company
        from ml.training import (
            artifact_directory, save_training_run, training_metadata, training_rows,
        )

        directory = artifact_directory(output_dir, MODEL_PATH.parent, apply=apply)

        if companies is None:
            companies = list(
                Company.objects.filter(ecoiq_score__gt=0).select_related('profile')
            )

        X, y, ids, skipped = training_rows(companies)
        result = training_metadata(X, y, skipped)
        if len(X) < 5:
            return {**result, 'error': 'insufficient_data'}

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        iforest = IsolationForest(
            n_estimators=200,
            contamination=0.05,
            random_state=42,
            n_jobs=-1,
        )
        iforest.fit(X_scaled)

        self.model   = iforest
        self.scaler  = scaler
        self._loaded = True

        anomaly_scores = iforest.score_samples(X_scaled)   # lower = more anomalous
        flags          = iforest.predict(X_scaled)          # -1=anomaly, 1=normal
        n_anomalies    = int((flags == -1).sum())

        logger.info(
            'IsolationForest trained: n=%d, anomalies=%d (%.1f%%)',
            len(X), n_anomalies, 100 * n_anomalies / max(len(X), 1),
        )

        result.update(n_anomalies=n_anomalies,
                      evaluation={'status': 'NOT_MEASURED', 'reason': 'no_reviewed_anomaly_labels'},
                      findings_basis='statistical_outliers_not_verified_wrongdoing')
        save_training_run({MODEL_PATH.name: iforest, SCALER_PATH.name: scaler},
                          directory, 'anomaly', result, exclusive=output_dir is not None)

        if apply:
            self._apply(ids, anomaly_scores, flags)

        return result

    def _apply(self, ids, anomaly_scores, flags):
        """Write anomaly_score and is_anomaly to Company records."""
        from django.utils import timezone
        from league.models import Company

        for pk, score, flag in zip(ids, anomaly_scores, flags):
            Company.objects.filter(pk=pk).update(
                anomaly_score=float(score),
                is_anomaly=(flag == -1),
                ml_last_run=timezone.now(),
            )

    def score_company(self, company) -> dict | None:
        """
        Score a single company, or None when it cannot honestly be scored.

        FAIL CLOSED ON MISSING MATERIAL INPUTS
        --------------------------------------
        Same rule as EcoIQScoringModel.predict_company and
        CompanyClusterer.assign_company. `company_to_vector` imputes 50.0 for
        unknown inputs, and this result is published as a finding:
        /companies/<slug>/ml-insights.json returns it as `anomaly`.

        An organisation with no data scored -0.45 and `is_anomaly: false` —
        which reads as "we looked and it is unremarkable" when nothing was
        looked at. Both halves are wrong in the same way, and the false one is
        the more reassuring, which makes it the worse one to publish.
        """
        if not self._load():
            return None
        from ml.features import company_to_vector, missing_material_features

        missing = missing_material_features(company)
        if missing:
            logger.info(
                'Anomaly scoring refused for %s — material inputs unknown: %s. '
                'The model would have received imputed 50.0 for each.',
                company, ', '.join(missing),
            )
            return None

        try:
            vec    = company_to_vector(company).reshape(1, -1)
            scaled = self.scaler.transform(vec)
            score  = float(self.model.score_samples(scaled)[0])
            flag   = int(self.model.predict(scaled)[0])
            return {
                'anomaly_score': round(score, 4),
                'is_anomaly':    flag == -1,
            }
        except Exception as exc:
            logger.error('Anomaly scoring failed for %s: %s', company, exc)
            return None
