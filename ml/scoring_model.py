"""
ml/scoring_model.py — GradientBoostingRegressor EcoIQ scorer with SHAP.

Training strategy:
  - Uses existing ecoiq_score as supervision signal (self-supervised refinement)
  - Adds small amount of noise to prevent model just learning identity
  - SHAP TreeExplainer explains feature contributions per company

Usage:
    from ml.scoring_model import EcoIQScoringModel
    model = EcoIQScoringModel()
    model.train()
    result = model.predict_company(company)
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parent / 'models' / 'scoring_gbr.joblib'
SCALER_PATH = Path(__file__).resolve().parent / 'models' / 'scoring_scaler.joblib'


class EcoIQScoringModel:
    """Gradient Boosting Regressor for EcoIQ score prediction."""

    def __init__(self):
        self.model  = None
        self.scaler = None
        self._loaded = False

    def _load(self):
        """Lazy-load saved model + scaler from disk."""
        if self._loaded:
            return True
        try:
            import joblib
            self.model  = joblib.load(MODEL_PATH)
            self.scaler = joblib.load(SCALER_PATH)
            self._loaded = True
            return True
        except Exception as exc:
            logger.warning('Scoring model not loaded: %s', exc)
            return False

    def train(self, companies=None, apply: bool = False) -> dict:
        """
        Train the GBR model on all companies with ecoiq_score > 0.

        Args:
            companies: queryset or None (fetches all)
            apply:     if True, save ml_score back to company records

        Returns:
            dict with training metrics
        """
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import cross_val_score
        import joblib
        from league.models import Company
        from ml.features import company_to_vector, get_feature_names

        if companies is None:
            companies = Company.objects.filter(ecoiq_score__gt=0).select_related('profile')

        X_rows, y_rows, ids = [], [], []
        for company in companies:
            try:
                vec   = company_to_vector(company)
                score = float(company.ecoiq_score)
                if score <= 0:
                    continue
                X_rows.append(vec)
                y_rows.append(score)
                ids.append(company.pk)
            except Exception as exc:
                logger.debug('Feature extraction failed for %s: %s', company, exc)

        if len(X_rows) < 5:
            logger.warning('Not enough training samples (%d). Need at least 5.', len(X_rows))
            return {'error': 'insufficient_data', 'n_samples': len(X_rows)}

        X = np.array(X_rows, dtype=np.float64)
        y = np.array(y_rows, dtype=np.float64)

        # Small noise prevents pure identity memorisation
        rng = np.random.default_rng(42)
        y_noisy = y + rng.normal(0, 1.5, size=len(y))
        y_noisy = np.clip(y_noisy, 0, 100)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        gbr = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=4,
            subsample=0.8,
            min_samples_leaf=2,
            random_state=42,
        )
        gbr.fit(X_scaled, y_noisy)

        # Cross-validation R²
        if len(X_rows) >= 10:
            cv_scores = cross_val_score(gbr, X_scaled, y_noisy, cv=min(5, len(X_rows)), scoring='r2')
            r2_mean = float(cv_scores.mean())
            r2_std  = float(cv_scores.std())
        else:
            r2_mean = float(gbr.score(X_scaled, y_noisy))
            r2_std  = 0.0

        # Persist
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(gbr,    MODEL_PATH)
        joblib.dump(scaler, SCALER_PATH)
        self.model   = gbr
        self.scaler  = scaler
        self._loaded = True

        logger.info('GBR trained: n=%d, R²=%.3f±%.3f', len(X_rows), r2_mean, r2_std)

        if apply:
            self._apply_scores(companies, ids, X_scaled)

        return {
            'n_samples': len(X_rows),
            'r2_mean':   r2_mean,
            'r2_std':    r2_std,
            'features':  get_feature_names(),
        }

    def _apply_scores(self, companies, ids, X_scaled):
        """Write ml_score and ml_score_confidence back to Company records."""
        from django.utils import timezone
        from league.models import Company

        preds = self.model.predict(X_scaled)
        id_to_pred = dict(zip(ids, preds.tolist()))
        id_to_base = {c.pk: float(c.ecoiq_score or 0) for c in companies}

        now = timezone.now()
        for pk, raw_pred in id_to_pred.items():
            pred       = float(np.clip(raw_pred, 0, 100))
            base       = id_to_base.get(pk, 50.0)
            deviation  = abs(pred - base)
            confidence = round(max(0.0, min(1.0, 1.0 - deviation / 50.0)), 3)
            Company.objects.filter(pk=pk).update(
                ml_score=round(pred, 1),
                ml_score_confidence=confidence,
                ml_last_run=now,
            )

    def predict_company(self, company) -> dict | None:
        """
        Predict ml_score for a single company.

        Returns dict with:
            score, confidence, shap_values, top_features
        """
        if not self._load():
            return None

        from ml.features import company_to_vector, get_feature_names
        import shap

        try:
            vec     = company_to_vector(company).reshape(1, -1)
            scaled  = self.scaler.transform(vec)
            pred    = float(self.model.predict(scaled)[0])
            pred    = max(0.0, min(100.0, pred))

            feature_names = get_feature_names()

            # SHAP — TreeExplainer requires the GBR directly (not a Pipeline)
            explainer  = shap.TreeExplainer(self.model)
            shap_vals  = explainer.shap_values(scaled)[0]  # shape: (n_features,)

            # Pair feature names with SHAP values, sort by |impact|
            shap_pairs = sorted(
                zip(feature_names, shap_vals.tolist()),
                key=lambda t: abs(t[1]),
                reverse=True,
            )
            top_features = [
                {'feature': name, 'impact': round(impact, 3)}
                for name, impact in shap_pairs[:8]
            ]

            # Confidence proxy: inverse distance to nearest training neighbour
            # (simple: use raw score deviation from base ecoiq_score)
            base = float(company.ecoiq_score or 0)
            deviation = abs(pred - base)
            confidence = max(0.0, min(1.0, 1.0 - deviation / 50.0))

            return {
                'score':        round(pred, 1),
                'confidence':   round(confidence, 3),
                'shap_values':  shap_pairs[:8],
                'top_features': top_features,
            }

        except Exception as exc:
            logger.error('Prediction failed for %s: %s', company, exc)
            return None
