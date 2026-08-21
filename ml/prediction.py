"""
ml/prediction.py — 12-month EcoIQ score forecast.

Method:
  1. Fetch the last 12 ScoreHistory snapshots for the company.
  2. Fit a simple linear trend (OLS) on dates → scores.
  3. Project forward 12 months from today.
  4. Clamp result to [0, 100].

Fallback: if fewer than 3 data points, returns current ecoiq_score + estimated delta
based on recent DataIngestionLog signals (harm → small negative, positive → small positive).
Returns None if the company has no current score — a forecast is a projection
FROM something, and there is nothing to project from.

Usage:
    from ml.prediction import predict_12m
    pred = predict_12m(company)  # returns float or None
"""
from __future__ import annotations

import logging
from datetime import timedelta
import numpy as np

from core.unknown import known

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
            # Was `company.ecoiq_score or 50.0` — a degenerate fit fell back to
            # forecasting an average company. With no current score there is
            # nothing to project from, so refuse.
            fallback = known(company.ecoiq_score)
            if fallback is None:
                return None
            slope, intercept = 0.0, fallback

        days_forward = (target_date - history[0][0]).days
        predicted = slope * days_forward + intercept
        return float(np.clip(predicted, 0, 100))

    # ── Fallback: signal-based delta ──────────────────────────────────────
    #
    # Was `float(company.ecoiq_score or 50.0)`. That produced a 12-month
    # FORECAST for a company with no score at all — anchored on an invented
    # average, nudged by news signals, and written to ml_predicted_score_12m as
    # though it projected something. `or` also rewrote a genuine 0.0 to 50,
    # forecasting the worst-scoring company as an average one.
    base = known(company.ecoiq_score)
    if base is None:
        return None
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


# ── Derived provenance (D3C-3f) ───────────────────────────────────────────────

PREDICTION_METHOD = 'ecoiq-forecast-ols-12m'
PREDICTION_VERSION = '1'
PREDICTION_METRIC_KEY = 'ml.predicted_12m'

#: The ONLY registered metric this forecast consumes.
#:
#: Read this before treating the lineage as complete. predict_12m has two
#: paths and neither is well described by metric provenance:
#:
#:   * PRIMARY (>= 3 history points) — an OLS fit over ScoreHistory rows. It
#:     does not read company.ecoiq_total at all. The declared input below is
#:     therefore NOT the thing that produced the number; it is the closest
#:     provenance-bearing relative of it, since the history rows are snapshots
#:     of that same composite over time. ScoreHistory is a record, not a
#:     metric, and has no provenance rows to point at.
#:
#:   * FALLBACK (< 3 points) — anchored on company.ecoiq_score, nudged by up to
#:     +/-10 points of DataIngestionLog RSS signal. The anchor IS this input;
#:     the signals are again records with no provenance.
#:
#: So the recorded lineage understates both paths, in different ways. This is
#: stated here, asserted in the tests, and tracked in
#: docs/product/CALCULATION_CONTEXT_PROVENANCE.md rather than papered over.
#:
#: The forecast is MODELLED regardless. It must never inherit the provenance of
#: the current score: a projection about the future is a model output even when
#: every input to it was measured.
PREDICTION_INPUTS: tuple[str, ...] = (
    'company.ecoiq_total',
)


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
                _write_prediction(company, round(pred, 1), timezone.now())
                updated += 1
        except Exception as exc:
            logger.error('Prediction failed for %s: %s', company, exc)
            failed += 1

    return {'updated': updated, 'failed': failed}


def _write_prediction(company, prediction: float, now) -> str:
    """
    Persist one 12-month forecast together with its provenance, atomically.

    ml.predicted_12m IS persisted (league.Company.ml_predicted_score_12m), so
    the provenance row stores no recorded_value.

    Value write and provenance write share a transaction: a provenance failure
    rolls back the forecast rather than leaving a persisted projection with no
    recorded origin.

    Returns the provenance status, or 'no-profile' when there is nothing to
    attach lineage to.
    """
    from django.db import transaction
    from league.models import Company
    from companies import provenance as prov

    profile = getattr(company, 'profile', None)

    with transaction.atomic():
        Company.objects.filter(pk=company.pk).update(
            ml_predicted_score_12m=prediction,
            ml_last_run=now,
        )
        if profile is None:
            return 'no-profile'
        return prov.record_calculated(
            profile, PREDICTION_METRIC_KEY, prediction, PREDICTION_INPUTS,
            writer='ml.prediction.apply_predictions',
            methodology=PREDICTION_METHOD,
            calculation_version=PREDICTION_VERSION,
        )
