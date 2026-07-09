"""
agent_training_evaluation_lab/services/recommendations.py —
generate_recommendations(): deterministic rule table over a real
AgentEvaluationRun's metrics, its regressions, and real human feedback.
Every recommendation names the exact evaluation/regression/feedback rows
that triggered it (based_on) — the system suggests, a human decides;
nothing here ever edits an agent, a prompt, a training pack, or a scoring
formula.
"""
LOW_EVIDENCE_COVERAGE_THRESHOLD = 50.0
LOW_EVIDENCE_QUALITY_THRESHOLD = 50.0
LOW_CALIBRATION_THRESHOLD = 50.0
LOW_RELIABILITY_THRESHOLD = 70.0
LOW_TRACE_COMPLETENESS_THRESHOLD = 50.0
GOLDEN_PASS_RATE_THRESHOLD = 0.7
NEGATIVE_FEEDBACK_RATE_THRESHOLD = 0.4


def _score(evaluation_run, metric_name):
    return (evaluation_run.metrics or {}).get(metric_name, {}).get('score')


def generate_recommendations(evaluation_run):
    """Returns a list of newly-created ImprovementRecommendation rows for this evaluation."""
    from agent_training_evaluation_lab.models import AgentHumanFeedback, ImprovementRecommendation

    recommendations = []

    def _add(recommendation_type, description, based_on):
        rec = ImprovementRecommendation.objects.create(
            agent=evaluation_run.agent, recommendation_type=recommendation_type,
            description=description, based_on=based_on,
        )
        recommendations.append(rec)

    evidence_coverage = _score(evaluation_run, 'evidence_coverage')
    if evidence_coverage is not None and evidence_coverage < LOW_EVIDENCE_COVERAGE_THRESHOLD:
        _add(
            'improve_evidence_retrieval',
            f'Evidence coverage is {evidence_coverage}% (below {LOW_EVIDENCE_COVERAGE_THRESHOLD}%) — many runs cite no evidence at all.',
            {'evaluation_run_ids': [evaluation_run.pk]},
        )

    evidence_quality = _score(evaluation_run, 'evidence_quality')
    if evidence_quality is not None and evidence_quality < LOW_EVIDENCE_QUALITY_THRESHOLD:
        _add(
            'increase_evidence_threshold',
            f'Mean evidence quality is {evidence_quality}/100 (below {LOW_EVIDENCE_QUALITY_THRESHOLD}) — consider requiring stronger sources before an output is accepted.',
            {'evaluation_run_ids': [evaluation_run.pk]},
        )

    calibration = _score(evaluation_run, 'confidence_calibration')
    if calibration is not None and calibration < LOW_CALIBRATION_THRESHOLD:
        _add(
            'review_confidence_calibration',
            f'Confidence calibration checks passed only {calibration}% of the time a risk/missing-data signal was present.',
            {'evaluation_run_ids': [evaluation_run.pk]},
        )

    reliability = _score(evaluation_run, 'reliability')
    if reliability is not None and reliability < LOW_RELIABILITY_THRESHOLD:
        _add(
            'investigate_failure_category',
            f'Reliability score is {reliability}/100 — a recurring failure pattern likely exists across this agent\'s runs.',
            {'evaluation_run_ids': [evaluation_run.pk]},
        )

    trace_completeness = _score(evaluation_run, 'reasoning_trace_completeness')
    if trace_completeness is not None and trace_completeness < LOW_TRACE_COMPLETENESS_THRESHOLD:
        _add(
            'inspect_orchestration_failures',
            f'Only {trace_completeness}% of runs recorded a real execution audit trail — check whether orchestration nodes are failing silently.',
            {'evaluation_run_ids': [evaluation_run.pk]},
        )

    if evaluation_run.golden_cases_checked > 0:
        pass_rate = evaluation_run.golden_cases_passed / evaluation_run.golden_cases_checked
        if pass_rate < GOLDEN_PASS_RATE_THRESHOLD:
            _add(
                'expand_golden_dataset',
                f'Only {evaluation_run.golden_cases_passed}/{evaluation_run.golden_cases_checked} golden case(s) matched a real run — '
                f'either the golden dataset needs more representative cases, or real runs are drifting from documented expectations.',
                {'evaluation_run_ids': [evaluation_run.pk]},
            )

    recent_feedback = AgentHumanFeedback.objects.filter(agent_run__agent=evaluation_run.agent)
    feedback_total = recent_feedback.count()
    if feedback_total > 0:
        negative = recent_feedback.filter(classification__in=('NEEDS_IMPROVEMENT', 'INCORRECT', 'INSUFFICIENT_EVIDENCE')).count()
        if negative / feedback_total >= NEGATIVE_FEEDBACK_RATE_THRESHOLD:
            _add(
                'investigate_failure_category',
                f'{negative}/{feedback_total} human review(s) flagged this agent\'s output as needing improvement, incorrect, or under-evidenced.',
                {'feedback_ids': list(recent_feedback.values_list('pk', flat=True))},
            )

    return recommendations
