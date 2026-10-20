"""Read-only, versioned mining KPI calculations; no scores or guessed data."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from gold_intelligence.services.kpi_definitions import MINING_KPIS


def evaluate_mine_kpi(observation):
    """Evaluate raw numerator/denominator for one stated, period-matched method.

    Value can be calculated for a pending observation, but *publishable* is
    false until an internally reviewed, non-synthetic, matched source and
    non-demo project exist. Internal review != independent mining certification.
    """
    definition = MINING_KPIS.get(observation.metric_key)
    if not definition:
        return {'status': 'UNKNOWN_METHOD', 'value': None, 'publishable': False}

    result = {
        'key': definition.key,
        'label': definition.label,
        'unit': definition.unit,
        'mizan_dimension': definition.mizan_dimension,
        'method_version': definition.method_version,
        'period_start': observation.period_start,
        'period_end': observation.period_end,
        'value': None,
        'publishable': False,
    }
    if observation.method_version != definition.method_version:
        return {**result, 'status': 'UNSUPPORTED_VERSION'}
    if observation.numerator is None or observation.denominator is None:
        return {**result, 'status': 'MISSING_INPUT'}
    try:
        numerator, denominator = Decimal(str(observation.numerator)), Decimal(str(observation.denominator))
        if (not numerator.is_finite() or not denominator.is_finite()
                or numerator < 0 or denominator <= 0
                or definition.percent and numerator > denominator):
            return {**result, 'status': 'INVALID_INPUT'}
        value = (numerator / denominator * definition.multiplier).quantize(
            Decimal('0.000001'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError, ZeroDivisionError):
        return {**result, 'status': 'INVALID_INPUT'}

    result['value'] = value
    source = observation.source
    if observation.project_id != source.project_id:
        return {**result, 'status': 'PROJECT_MISMATCH', 'value': None}
    if observation.project.is_demo or source.is_synthetic:
        return {**result, 'status': 'DEMO_UNVERIFIED'}
    if (source.review_state != 'reviewed' or not source.reviewer_id
            or not source.reviewed_at or not source.content_sha256):
        return {**result, 'status': 'SOURCE_REVIEW_REQUIRED'}
    if observation.review_state != 'reviewed' or not observation.reviewer_id or not observation.reviewed_at:
        return {**result, 'status': 'KPI_REVIEW_REQUIRED'}

    # Not a reserve, environmental compliance certificate or universal Mizan score.
    return {**result, 'status': 'INTERNALLY_REVIEWED', 'publishable': True}


def mine_kpi_readiness(project):
    """Project-local query; caller must have independently checked project access."""
    rows = project.mine_kpi_observations.select_related('source', 'project').all()
    evaluated = [evaluate_mine_kpi(row) for row in rows]
    return {
        'observations': evaluated,
        'reviewed_count': sum(x['publishable'] for x in evaluated),
        'observed_count': len(evaluated),
        'note': (
            'Internally reviewed KPI values are not independently certified. '
            'No site-specific Mizan thresholds or reserves are inferred.'
        ),
    }
