"""
agent_training_evaluation_lab/services/regression_detection.py —
detect_regressions(): compares a real AgentEvaluationRun against its real
previous_evaluation and records genuine declines as AgentRegression rows.
Never modifies the agent, its training pack, or any production
configuration — a regression is a human-observable finding only.
"""
REGRESSION_THRESHOLDS = {
    'overall_score': 5.0,
    'factual_grounding': 10.0,
    'evidence_coverage': 10.0,
    'evidence_quality': 10.0,
    'confidence_calibration': 15.0,
    'consistency': 15.0,
    'completeness': 10.0,
    'reasoning_trace_completeness': 15.0,
    'reliability': 10.0,
}
LATENCY_INCREASE_THRESHOLD_SECONDS = 2.0


def _metric_value(evaluation_run, metric_name):
    if metric_name == 'overall_score':
        return evaluation_run.overall_score
    return (evaluation_run.metrics or {}).get(metric_name, {}).get('score')


def _severity(change, threshold):
    if change <= -2 * threshold:
        return 'high'
    if change <= -1.5 * threshold:
        return 'medium'
    return 'low'


def detect_regressions(evaluation_run):
    """Returns the list of AgentRegression rows created for this evaluation run."""
    from agent_training_evaluation_lab.models import AgentRegression

    if evaluation_run.previous_evaluation is None:
        return []  # nothing to compare against yet — not a regression, just a first evaluation

    findings = []
    delta = evaluation_run.score_delta or {}

    for metric_name, threshold in REGRESSION_THRESHOLDS.items():
        change = delta.get(metric_name)
        if change is None or change > -threshold:
            continue
        findings.append(AgentRegression.objects.create(
            agent=evaluation_run.agent, evaluation_run=evaluation_run, metric_name=metric_name,
            previous_value=_metric_value(evaluation_run.previous_evaluation, metric_name),
            current_value=_metric_value(evaluation_run, metric_name),
            threshold=threshold, severity=_severity(change, threshold),
        ))

    latency_prev = _metric_value(evaluation_run.previous_evaluation, 'latency')
    latency_current = _metric_value(evaluation_run, 'latency')
    if latency_prev is not None and latency_current is not None and (latency_current - latency_prev) >= LATENCY_INCREASE_THRESHOLD_SECONDS:
        findings.append(AgentRegression.objects.create(
            agent=evaluation_run.agent, evaluation_run=evaluation_run, metric_name='latency',
            previous_value=latency_prev, current_value=latency_current,
            threshold=LATENCY_INCREASE_THRESHOLD_SECONDS, severity='medium',
        ))

    return findings
