"""
digital_twin/services/baseline.py — the deterministic Baseline Engine.

No LLM involvement anywhere in this module. Every score is plain,
explainable arithmetic over rows that already exist in the database,
following the same additive/capped-at-100 template as
`ethics/scoring.py::compute_data_confidence()`. `BASELINE_FORMULA_VERSION`
must be bumped whenever the weights or method below change, so a stored
`DigitalTwin.model_version` always tells you exactly which formula produced
its scores.
"""
from datetime import timedelta

from django.utils import timezone

BASELINE_FORMULA_VERSION = '1.0.0'

# Completeness: 5 structural sections, 20 points each. Deliberately simple
# and auditable rather than weighted by "importance" — importance differs
# per asset type and is exactly the kind of judgement this formula must not
# fabricate.
COMPLETENESS_SECTIONS = [
    ('components', 'At least one TwinComponent is recorded.'),
    ('process_nodes', 'At least one ProcessNode is recorded.'),
    ('process_edges', 'The process graph has at least one edge connecting two nodes.'),
    ('resource_flows', 'At least one ResourceFlow is recorded.'),
    ('metrics', 'At least one OperationalMetric is recorded.'),
]
POINTS_PER_SECTION = 100 / len(COMPLETENESS_SECTIONS)

FRESHNESS_BANDS = [
    (30, 100),
    (90, 75),
    (180, 50),
    (365, 25),
]

READY_COMPLETENESS_THRESHOLD = 60
READY_CONFIDENCE_THRESHOLD = 50


def _section_counts(twin):
    return {
        'components': twin.components.count(),
        'process_nodes': twin.process_nodes.count(),
        'process_edges': twin.process_edges.count(),
        'resource_flows': twin.resource_flows.count(),
        'metrics': twin.metrics.count(),
    }


def _compute_completeness(counts):
    populated = [key for key, _ in COMPLETENESS_SECTIONS if counts[key] > 0]
    missing = [(key, note) for key, note in COMPLETENESS_SECTIONS if counts[key] == 0]
    score = round(len(populated) * POINTS_PER_SECTION, 2)
    return score, missing


def _confidence_values(twin):
    values = []
    values += [v for v in twin.metrics.values_list('confidence', flat=True) if v is not None]
    values += [v for v in twin.resource_flows.values_list('confidence', flat=True) if v is not None]
    values += [v for v in twin.process_nodes.values_list('confidence', flat=True) if v is not None]
    return values


def _compute_confidence(twin):
    values = _confidence_values(twin)
    if not values:
        return 0.0, 0
    return round(sum(values) / len(values), 2), len(values)


def _compute_evidence_coverage(twin):
    total = 0
    with_evidence = 0
    for qs in (twin.components.all(), twin.process_nodes.all(), twin.resource_flows.all(), twin.metrics.all()):
        for obj in qs:
            total += 1
            if obj.evidence_references:
                with_evidence += 1
    if total == 0:
        return 0.0
    return round((with_evidence / total) * 100, 2)


def _compute_freshness(twin):
    latest = twin.metrics.order_by('-recorded_at').values_list('recorded_at', flat=True).first()
    reference_time = latest or twin.last_observed_at
    if reference_time is None:
        return 0.0, None
    age_days = (timezone.now() - reference_time).days
    for max_days, score in FRESHNESS_BANDS:
        if age_days <= max_days:
            return float(score), age_days
    return 0.0, age_days


def compute_baseline(twin):
    """Pure function — reads the twin's related rows and returns the
    structured baseline result. Never writes to the database."""
    counts = _section_counts(twin)
    completeness_score, missing_sections = _compute_completeness(counts)
    confidence_score, confidence_sample_size = _compute_confidence(twin)
    evidence_coverage = _compute_evidence_coverage(twin)
    freshness_score, freshness_age_days = _compute_freshness(twin)

    critical_gaps = list(
        twin.data_gaps.filter(status='open', severity__in=['high', 'critical'])
        .order_by('-severity')
        .values('id', 'affected_area', 'severity', 'why_it_matters')
    )
    has_blocking_gap = any(g['severity'] == 'critical' for g in critical_gaps)

    warnings = []
    for key, note in missing_sections:
        warnings.append(note)
    if confidence_sample_size == 0:
        warnings.append('No component/metric/resource-flow confidence values recorded yet — confidence score is 0 by default, not fabricated.')
    if freshness_age_days is None:
        warnings.append('No observation timestamp available — freshness score is 0 by default.')
    elif freshness_age_days > 365:
        warnings.append(f'Most recent observation is {freshness_age_days} days old — twin is stale.')

    ready_for_optimisation = (
        completeness_score >= READY_COMPLETENESS_THRESHOLD
        and confidence_score >= READY_CONFIDENCE_THRESHOLD
        and not has_blocking_gap
    )
    status = 'baseline_ready' if ready_for_optimisation else 'incomplete'

    return {
        'status': status,
        'completeness_score': completeness_score,
        'confidence_score': confidence_score,
        'freshness_score': freshness_score,
        'evidence_coverage': evidence_coverage,
        'critical_data_gaps': critical_gaps,
        'warnings': warnings,
        'ready_for_optimisation': ready_for_optimisation,
        'formula_version': BASELINE_FORMULA_VERSION,
        'section_counts': counts,
    }


def generate_data_gaps(twin, result=None):
    """Ensures a TwinDataGap row exists (get_or_create, never duplicated)
    for every structurally-missing section identified by compute_baseline.
    Never deletes a gap a human has already actioned — only creates the
    ones that are honestly still missing."""
    from digital_twin.models import TwinDataGap

    result = result or compute_baseline(twin)
    counts = result['section_counts']
    created = []
    for key, note in COMPLETENESS_SECTIONS:
        if counts[key] > 0:
            continue
        gap, was_created = TwinDataGap.objects.get_or_create(
            twin=twin, affected_area=f'digital_twin.{key}', status='open',
            defaults={
                'required_data': note,
                'why_it_matters': 'The baseline completeness formula cannot score this section without at least one real record.',
                'severity': 'high',
                'recommended_collection_method': 'Add at least one real record for this section, backed by evidence where possible.',
            },
        )
        if was_created:
            created.append(gap)
    return created


def apply_baseline(twin, generate_gaps=True):
    """Computes the baseline, persists the scores onto the twin, advances
    its status among the pre-approval states only (never sets 'active' —
    that requires a human approval, handled elsewhere), and optionally
    creates TwinDataGap rows for missing sections."""
    result = compute_baseline(twin)
    twin.completeness_score = result['completeness_score']
    twin.confidence_score = result['confidence_score']
    twin.data_freshness_score = result['freshness_score']
    twin.model_version = BASELINE_FORMULA_VERSION
    if twin.status in ('draft', 'ingesting', 'incomplete', 'baseline_ready', 'stale'):
        twin.status = result['status']
    twin.save(update_fields=[
        'completeness_score', 'confidence_score', 'data_freshness_score', 'model_version', 'status', 'updated_at',
    ])
    if generate_gaps:
        generate_data_gaps(twin, result)
    return result
