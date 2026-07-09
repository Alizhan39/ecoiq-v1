"""
agent_training_evaluation_lab/services/evaluation_engine.py —
run_agent_evaluation(): the one entrypoint that computes a real
AgentEvaluationRun from an agent's real, already-persisted AgentRun
history. Never runs a new agent execution itself — evaluation is read-only
over existing data (the point of the whole architecture: EcoIQ already
executes agents every day via the Workbench, Backend Intelligence Engine
and Decision Studio; this reads what already happened).
"""
from django.utils import timezone

from agent_training_evaluation_lab.models import AgentEvaluationRun
from agent_training_evaluation_lab.services import metrics


def run_agent_evaluation(agent_entry, evaluation_version='v1'):
    from agent_runtime_model_router.models import AgentRun

    runs = AgentRun.objects.filter(agent=agent_entry, status__in=('completed', 'needs_human_review'))

    metric_results = {name: fn(runs) for name, (fn, _weight) in metrics.SCORED_METRICS.items()}
    metric_results['latency'] = metrics.latency_metrics(runs)
    overall_score = metrics.compute_overall_score(metric_results)

    golden_checked, golden_passed, golden_failures = metrics.check_golden_cases(agent_entry, runs)

    previous = AgentEvaluationRun.objects.filter(agent=agent_entry).order_by('-started_at').first()
    score_delta = {}
    if previous is not None:
        if previous.overall_score is not None and overall_score is not None:
            score_delta['overall_score'] = round(overall_score - previous.overall_score, 1)
        for name, result in metric_results.items():
            prev_result = (previous.metrics or {}).get(name, {})
            prev_score = prev_result.get('score')
            if prev_score is not None and result['score'] is not None:
                score_delta[name] = round(result['score'] - prev_score, 1)

    evaluation = AgentEvaluationRun.objects.create(
        agent=agent_entry, evaluation_version=evaluation_version,
        metrics=metric_results, overall_score=overall_score,
        runs_evaluated_count=runs.count(),
        golden_cases_checked=golden_checked, golden_cases_passed=golden_passed,
        failure_reasons=golden_failures,
        previous_evaluation=previous, score_delta=score_delta,
        completed_at=timezone.now(),
    )

    # Closes a real, pre-existing gap: AgentRegistryEntry.last_evaluation_score
    # has existed since Phase 1 of the AI Agent Workbench, deliberately null
    # until a real evaluation engine existed to populate it honestly.
    if overall_score is not None:
        agent_entry.last_evaluation_score = overall_score
        agent_entry.save(update_fields=['last_evaluation_score'])

    return evaluation
