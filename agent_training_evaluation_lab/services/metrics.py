"""
agent_training_evaluation_lab/services/metrics.py — every metric computed
from real, already-persisted agent_runtime_model_router.AgentRun fields.
Nothing here executes an agent or invents a number: each function reads a
queryset of real AgentRun rows and returns {'score', 'explanation',
'sample_size'} — score is None (never 0, never a guess) when there isn't
enough real data, matching the "NOT YET MEASURED" convention already used
elsewhere on this platform (e.g. ai_agent_workbench's performance page).
"""
import numpy as np
import pandas as pd

NOT_YET_MEASURED = 'NOT YET MEASURED'


def _result(score, explanation, sample_size):
    return {'score': score, 'explanation': explanation, 'sample_size': sample_size}


def _none(reason, sample_size=0):
    return _result(None, f'{NOT_YET_MEASURED} — {reason}', sample_size)


def factual_grounding_score(runs):
    """Proxy: the real, already-computed safety_status pass rate — a run
    only passes 'pass' when run_safety_assertions() found no unsupported/
    invented/guaranteed claims in its own output."""
    total = runs.count()
    if total == 0:
        return _none('no runs to evaluate.')
    passed = runs.filter(safety_status='pass').count()
    score = round(100 * passed / total, 1)
    return _result(score, f'{passed}/{total} run(s) passed every safety assertion (no unsupported or invented claim detected).', total)


def evidence_coverage_score(runs):
    total = runs.count()
    if total == 0:
        return _none('no runs to evaluate.')
    with_evidence = sum(1 for r in runs if r.evidence_used)
    score = round(100 * with_evidence / total, 1)
    return _result(score, f'{with_evidence}/{total} run(s) cited at least one evidence item.', total)


def evidence_quality_score(runs):
    quality_map = {'strong': 100, 'medium': 60, 'weak': 30, 'missing': 0}
    values = []
    for run in runs:
        for item in (run.evidence_provenance or []):
            quality = item.get('quality')
            if quality in quality_map:
                values.append(quality_map[quality])
    if not values:
        return _none('no evidence provenance has been recorded yet.')
    score = round(float(np.mean(values)), 1)
    return _result(score, f'Mean evidence quality across {len(values)} evidence item(s) actually cited.', len(values))


def confidence_calibration_score(runs):
    """
    A real, checkable directional signal (not just "how big was the
    adjustment"): when a run carries a risk flag or missing-data warning,
    a properly-calibrated confidence should be at or below the raw
    confidence, never above it. Runs with no risk/missing-data signal
    aren't informative for this check either way, so they're excluded
    from the denominator rather than counted as a pass.
    """
    checked, correct = 0, 0
    for run in runs.exclude(calibrated_confidence__isnull=True):
        has_risk_signal = bool(run.risk_flags) or bool(run.missing_data)
        if not has_risk_signal:
            continue
        checked += 1
        if run.calibrated_confidence <= (run.raw_confidence if run.raw_confidence is not None else 100):
            correct += 1
    if checked == 0:
        return _none('no run had a risk flag or missing-data warning to check calibration direction against.')
    score = round(100 * correct / checked, 1)
    return _result(
        score,
        f'{correct}/{checked} run(s) with a risk flag or missing data had calibrated confidence at or below raw confidence, as expected.',
        checked,
    )


def consistency_score(runs):
    """Lower confidence variance for the SAME task_type across repeated runs = more consistent."""
    rows = list(runs.exclude(calibrated_confidence__isnull=True).values('task_type', 'calibrated_confidence'))
    if len(rows) < 2:
        return _none('fewer than two comparable runs exist.', len(rows))
    df = pd.DataFrame(rows)
    grouped_std = df.groupby('task_type')['calibrated_confidence'].std().dropna()
    if grouped_std.empty:
        return _none('no task type has more than one run to compare.', len(rows))
    mean_std = float(grouped_std.mean())
    score = round(float(np.clip(100 - mean_std * 2, 0, 100)), 1)
    return _result(score, f'Mean confidence standard deviation of {mean_std:.1f} points across {len(grouped_std)} repeated task type(s).', len(rows))


def completeness_score(runs):
    total = runs.exclude(schema_valid__isnull=True).count()
    if total == 0:
        return _none('no run has been schema-checked yet.')
    valid = runs.filter(schema_valid=True).count()
    score = round(100 * valid / total, 1)
    return _result(score, f'{valid}/{total} run(s) produced schema-valid structured output.', total)


def reasoning_trace_completeness_score(runs):
    total = runs.count()
    if total == 0:
        return _none('no runs to evaluate.')
    with_trace = sum(1 for r in runs if r.audit_trail)
    score = round(100 * with_trace / total, 1)
    return _result(score, f'{with_trace}/{total} run(s) recorded a real execution audit trail.', total)


def reliability_score(runs):
    """100 minus the real failure rate — higher is better, consistent with every other metric."""
    total = runs.count()
    if total == 0:
        return _none('no runs to evaluate.')
    failed = runs.filter(status='failed').count()
    failure_rate = round(100 * failed / total, 1)
    return _result(round(100 - failure_rate, 1), f'{failed}/{total} run(s) failed (failure rate {failure_rate}%).', total)


def latency_metrics(runs):
    """Informational only (seconds, not a 0-100 score) — excluded from the weighted overall score."""
    durations = []
    for run in runs.exclude(started_at__isnull=True).exclude(completed_at__isnull=True):
        durations.append((run.completed_at - run.started_at).total_seconds())
    if not durations:
        return _none('no run has both a start and completion timestamp.')
    mean_latency = round(float(np.mean(durations)), 2)
    return _result(mean_latency, f'Mean latency across {len(durations)} run(s) with real timestamps, in seconds.', len(durations))


# name -> (function, weight). Weights sum to 1.0 over the metrics that
# contribute to overall_score — latency is deliberately excluded (it's a
# real number, not a 0-100 "better is higher" score).
SCORED_METRICS = {
    'factual_grounding': (factual_grounding_score, 0.20),
    'evidence_coverage': (evidence_coverage_score, 0.15),
    'evidence_quality': (evidence_quality_score, 0.15),
    'confidence_calibration': (confidence_calibration_score, 0.15),
    'consistency': (consistency_score, 0.10),
    'completeness': (completeness_score, 0.10),
    'reasoning_trace_completeness': (reasoning_trace_completeness_score, 0.10),
    'reliability': (reliability_score, 0.05),
}


def check_golden_cases(agent_entry, runs):
    """
    Checks real AgentRun rows against the agent's real golden dataset
    (GoldenDatasetCase, realistic cases only — failure cases describe a
    behaviour, not a comparable score/approval pair). A case "passes" when
    at least one real run's calibrated confidence sits within 20 points of
    the golden expectation and its human_approval_required flag matches —
    a real, deterministic structural check, never a fabricated pass.
    Returns (checked, passed, failure_details).
    """
    from agent_training_evaluation_lab.models import GoldenDatasetCase

    cases = GoldenDatasetCase.objects.filter(agent=agent_entry, case_type='realistic', is_active=True)
    candidates = list(runs.exclude(calibrated_confidence__isnull=True))
    checked, passed, details = 0, 0, []

    for case in cases:
        checked += 1
        expected_confidence = case.expected_properties.get('confidence')
        expected_approval = case.expected_properties.get('human_approval_required')

        matched = False
        for run in candidates:
            conf_ok = expected_confidence is None or abs((run.calibrated_confidence or 0) - expected_confidence) <= 20
            approval_ok = expected_approval is None or run.human_approval_required == expected_approval
            if conf_ok and approval_ok:
                matched = True
                break

        if matched:
            passed += 1
        else:
            details.append(
                f'{case.case_id}: no real run matched expected confidence≈{expected_confidence}, '
                f'human_approval_required={expected_approval}',
            )

    return checked, passed, details


def compute_overall_score(metric_results):
    """pandas-based weighted average over the metrics that had enough data
    to score — weights renormalized over only the available subset, same
    pattern as pandas_scoring_engine._weighted_average()."""
    available = {name: result for name, result in metric_results.items() if name in SCORED_METRICS and result['score'] is not None}
    if not available:
        return None

    df = pd.DataFrame({
        'score': {name: result['score'] for name, result in available.items()},
        'weight': {name: SCORED_METRICS[name][1] for name in available},
    })
    df['weight'] = df['weight'] / df['weight'].sum()
    return round(float((df['score'] * df['weight']).sum()), 1)
