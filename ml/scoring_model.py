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

from core.unknown import known

MODEL_PATH = Path(__file__).resolve().parent / 'models' / 'scoring_gbr.joblib'
SCALER_PATH = Path(__file__).resolve().parent / 'models' / 'scoring_scaler.joblib'


# ── Derived provenance (D3C-3f) ───────────────────────────────────────────────

ML_SCORE_METHOD = 'ecoiq-ml-gbr-score'
ML_SCORE_METRIC_KEY = 'ml.score'

#: The model features that ARE registered metrics, so their lineage can be
#: stated. Six derived pillars plus nine material scores, in feature order.
#:
#: This is 15 of the 29 features. The other 14 — the five legacy
#: league.Company.score_* fields, pollution_level_enc, evidence_coverage,
#: score_variance, score_trend, sector_enc, is_public, verified,
#: employee_count_log and annual_revenue_log — have no provenance rows, so the
#: recorded lineage is a TRUE SUBSET of what the model consumed, not the whole
#: of it. Said plainly here rather than left for a reader to discover:
#: docs/product/CALCULATION_CONTEXT_PROVENANCE.md tracks the gap.
ML_SCORE_INPUTS: tuple[str, ...] = (
    'company.public_benefit',
    'company.environmental',
    'company.modernization',
    'company.transparency_governance',
    'company.ethical_alignment',
    'anti_corruption_score',
    'company.harm_penalty',
    'waste_management_score',
    'water_impact_score',
    'biodiversity_impact_score',
    'energy_transition_score',
    'digitalization_score',
    'future_readiness_score',
    'audit_quality_score',
    'controversy_risk_score',
)


def ml_score_version() -> str | None:
    """calculation_version for ml.score: feature-set version + artefact digest."""
    from ml.model_identity import model_version

    return model_version(MODEL_PATH, SCALER_PATH)


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
        """
        Write ml_score and ml_score_confidence back to Company records.

        SKIPS companies with unknown material inputs, for the same reason
        predict_company() refuses them (#244): ml.features imputes 50.0 to
        satisfy the dense-matrix contract, and the model reads that as an
        average company.

        Without this the two paths disagree about the same company — the API
        would decline to predict while the batch job had already persisted a
        number for it, and the persisted one wins on every page that reads the
        field. The gate belongs on both paths or neither.

        A skipped company is left untouched rather than written as null: this
        method has no mandate to erase a score some other run produced.
        """
        from django.utils import timezone
        from league.models import Company
        from ml.features import missing_material_features

        preds = self.model.predict(X_scaled)
        id_to_pred = dict(zip(ids, preds.tolist()))
        id_to_base = {c.pk: known(c.ecoiq_score) for c in companies}
        id_to_company = {c.pk: c for c in companies}

        now = timezone.now()
        skipped = 0
        for pk, raw_pred in id_to_pred.items():
            company = id_to_company.get(pk)
            missing = (missing_material_features(company)
                       if company is not None else ['<company not in batch>'])
            if missing:
                logger.info(
                    'ml_score not applied for pk=%s — material inputs unknown: %s. '
                    'The model received an imputed 50.0 for each.',
                    pk, ', '.join(missing),
                )
                skipped += 1
                continue

            pred = float(np.clip(raw_pred, 0, 100))
            # Two fabrications in one line previously: `ecoiq_score or 0` made
            # an unknown base zero, and `.get(pk, 50.0)` made an absent one
            # average. Confidence is a claim about how much to trust the
            # prediction; without a base there is nothing to compare against.
            base = id_to_base.get(pk)
            confidence = (None if base is None
                          else round(max(0.0, min(1.0, 1.0 - abs(pred - base) / 50.0)), 3))
            self._write_score(pk, round(pred, 1), confidence, now,
                              id_to_company.get(pk))

        if skipped:
            logger.warning(
                'ml_score applied to %d of %d companies; %d skipped for unknown '
                'material inputs.', len(id_to_pred) - skipped, len(id_to_pred), skipped,
            )

    def _write_score(self, pk, score, confidence, now, company):
        """
        Persist one ml_score together with its provenance, atomically.

        ml.score IS persisted (league.Company.ml_score), so the provenance row
        stores no recorded_value — the field is the value source, per #248.

        The value write and the provenance write share one transaction. A
        provenance failure rolls the score back rather than leaving a persisted
        number whose origin nothing records; the next D3B pass would relabel
        such a number LEGACY_UNKNOWN_PROVENANCE, laundering a known model
        output into an unknown one.

        A company with no profile gets the value write only. There is nothing
        to hang provenance on, and refusing to store the score would be a
        larger behaviour change than this method is entitled to make.
        """
        from django.db import transaction
        from league.models import Company
        from companies import provenance as prov

        version = ml_score_version()
        profile = getattr(company, 'profile', None) if company is not None else None

        with transaction.atomic():
            Company.objects.filter(pk=pk).update(
                ml_score=score,
                ml_score_confidence=confidence,
                ml_last_run=now,
            )
            if profile is None or version is None:
                # version is None when the artefact cannot be read. Recording a
                # version string that names no model would be worse than
                # recording nothing.
                if version is None:
                    logger.warning(
                        'ml_score provenance not recorded for pk=%s — model '
                        'artefact could not be digested.', pk)
                return

            # No refresh needed: record_calculated resolves the declared
            # INPUTS, and the output is passed in explicitly — so the queryset
            # update above leaving `company` stale does not affect it.
            prov.record_calculated(
                profile, ML_SCORE_METRIC_KEY, score, ML_SCORE_INPUTS,
                writer='ml.scoring_model.EcoIQScoringModel._apply_scores',
                methodology=ML_SCORE_METHOD,
                calculation_version=version,
            )

    def predict_company(self, company) -> dict | None:
        """
        Predict ml_score for a single company.

        Returns dict with:
            score, confidence, shap_values, top_features
        or None when no prediction can honestly be made.

        FAIL CLOSED on missing material inputs. The estimator is a
        GradientBoostingRegressor that requires a dense float matrix, and
        ml.features imputes 50.0 to satisfy it — a value the model reads as an
        average company. Predicting from that would return a confident number,
        a confidence figure and a SHAP attribution, all describing a company
        assembled from defaults.

        Refusing is not a degraded outcome, it is the correct one, and it costs
        nothing at the call sites: None is already this method's documented
        "unavailable" return and every caller handles it.

        Proper imputation would require retraining — see the note at the top of
        ml/features.py. That is deliberately not attempted here.
        """
        if not self._load():
            return None

        from ml.features import (
            company_to_vector, get_feature_names, missing_material_features,
        )
        import shap

        missing = missing_material_features(company)
        if missing:
            logger.info(
                'Prediction refused for %s — material inputs unknown: %s. '
                'The model would have received imputed 50.0 for each.',
                company, ', '.join(missing),
            )
            return None

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
            # (simple: use raw score deviation from base ecoiq_score).
            #
            # Was `float(company.ecoiq_score or 0)`: with no base score the
            # deviation was measured from zero, so a company with an unknown
            # score got the LOWEST confidence — a statement about the model's
            # certainty derived entirely from our own missing data. Without a
            # base there is nothing to deviate from, so confidence is None.
            base = known(company.ecoiq_score)
            if base is None:
                confidence = None
            else:
                confidence = max(0.0, min(1.0, 1.0 - abs(pred - base) / 50.0))

            return {
                'score':        round(pred, 1),
                'confidence':   None if confidence is None else round(confidence, 3),
                'shap_values':  shap_pairs[:8],
                'top_features': top_features,
            }

        except Exception as exc:
            logger.error('Prediction failed for %s: %s', company, exc)
            return None
