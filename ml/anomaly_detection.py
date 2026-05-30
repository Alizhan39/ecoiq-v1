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

    def train(self, companies=None, apply: bool = False) -> dict:
        """
        Train Isolation Forest on all companies with scores.

        contamination=0.05 → flags ~5% as anomalous.
        """
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler
        import joblib
        from league.models import Company
        from ml.features import company_to_vector

        if companies is None:
            companies = list(
                Company.objects.filter(ecoiq_score__gt=0).select_related('profile')
            )

        X_rows, ids = [], []
        for company in companies:
            try:
                vec = company_to_vector(company)
                X_rows.append(vec)
                ids.append(company.pk)
            except Exception as exc:
                logger.debug('Feature extraction failed for %s: %s', company, exc)

        if len(X_rows) < 5:
            return {'error': 'insufficient_data', 'n_samples': len(X_rows)}

        X = np.array(X_rows, dtype=np.float64)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        iforest = IsolationForest(
            n_estimators=200,
            contamination=0.05,
            random_state=42,
            n_jobs=-1,
        )
        iforest.fit(X_scaled)

        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        import joblib as _jl
        _jl.dump(iforest, MODEL_PATH)
        _jl.dump(scaler,  SCALER_PATH)
        self.model   = iforest
        self.scaler  = scaler
        self._loaded = True

        anomaly_scores = iforest.score_samples(X_scaled)   # lower = more anomalous
        flags          = iforest.predict(X_scaled)          # -1=anomaly, 1=normal
        n_anomalies    = int((flags == -1).sum())

        logger.info(
            'IsolationForest trained: n=%d, anomalies=%d (%.1f%%)',
            len(X_rows), n_anomalies, 100 * n_anomalies / max(len(X_rows), 1),
        )

        if apply:
            self._apply(ids, anomaly_scores, flags)

        return {
            'n_samples':   len(X_rows),
            'n_anomalies': n_anomalies,
        }

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
        """Score a single company. Returns anomaly_score and is_anomaly."""
        if not self._load():
            return None
        from ml.features import company_to_vector
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
