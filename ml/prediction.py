"""
ml/prediction.py — 12-month EcoIQ score forecast.

Method:
  1. Fetch the last 12 ScoreHistory snapshots for the company.
  2. Fit a simple linear trend (OLS) on dates → scores.
  3. Project forward 12 months from today.
  4. Clamp result to [0, 100].

Fallback: if fewer than 3 data points, returns current ecoiq_score + estimated delta
based on recent DataIngestionLog signals (harm → small negative, positive → small positive).

Usage:
    from ml.prediction import predict_12m
    pred = predict_12m(company)  # returns float or None
"""
from __future__ import annotations

import logging
from datetime import timedelta
import numpy as np

logger = logging.getLogger(__name__)


def predict_12m(company) -> float | None:
    """
    Predict company's EcoIQ score 12 months from today.

    Returns float in [0, 100] or None if prediction isn't possible.
    """
    from django.utils import timezone

    today = timezone.now().date()
    target_date = today + timedelta(days=365)

    # ── Try historical trend first ─────────────────────────────────────────
    history = list(
        company.history.order_by('date').values_list('date', 'ecoiq_score')[:24]
    )

    if len(history) >= 3:
        dates  = np.array([(h[0] - history[0][0]).days for h in history], dtype=np.float64)
        scores = np.array([float(h[1]) for h in history], dtype=np.float64)

        # OLS: score = a * days + b
        A = np.vstack([dates, np.ones(len(dates))]).T
        try:
            slope, intercept = np.linalg.lstsq(A, scores, rcond=None)[0]
        except np.linalg.LinAlgError:
            slope, intercept = 0.0, float(company.ecoiq_score or 50.0)

        days_forward = (target_date - history[0][0]).days
        predicted = slope * days_forward + intercept
        return float(np.clip(predicted, 0, 100))

    # ── Fallback: signal-based delta ──────────────────────────────────────
    base = float(company.ecoiq_score or 50.0)
    delta = 0.0

    try:
        # Look at last 90 days of ingestion signals
        since = timezone.now() - timedelta(days=90)
        recent_logs = company.ingestion_logs.filter(
            ingested_at__gte=since,
            source='rss',
        ).values_list('raw_data', flat=True)[:50]

        for raw in recent_logs:
            sig_type = (raw or {}).get('signal_type', '')
            if sig_type == 'harm':
                delta -= 0.5
            elif sig_type == 'positive':
                delta += 0.3

        # Clamp delta: max ±10 points per year
        delta = max(-10.0, min(10.0, delta))
    except Exception as exc:
        logger.debug('Signal delta computation failed: %s', exc)

    return float(np.clip(base + delta, 0, 100))


def apply_predictions(companies=None) -> dict:
    """
    Compute and write ml_predicted_score_12m for all (or provided) companies.
    """
    from django.utils import timezone
    from league.models import Company

    if companies is None:
        companies = Company.objects.filter(ecoiq_score__gt=0).select_related(
            'profile', 'history'
        ).prefetch_related('history', 'ingestion_logs')

    updated = 0
    failed  = 0
    for company in companies:
        try:
            pred = predict_12m(company)
            if pred is not None:
                Company.objects.filter(pk=company.pk).update(
                    ml_predicted_score_12m=round(pred, 1),
                    ml_last_run=timezone.now(),
                )
                updated += 1
        except Exception as exc:
            logger.error('Prediction failed for %s: %s', company, exc)
            failed += 1

    return {'updated': updated, 'failed': failed}
