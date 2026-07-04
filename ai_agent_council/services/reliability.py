"""
ai_agent_council/services/reliability.py — real Agent Reliability stats.

Every number here is computed from currently-seeded demonstration runs in
this database, not production telemetry — there is no production traffic
for these agents yet. The Reliability page must caption these figures that
way; this module never invents a historical statistic.
"""
from django.db.models import Avg, Q


def compute_reliability(agent_name):
    from ai_agent_council.models import AgentTask, CouncilDisagreement, CrossExaminationExchange

    tasks = AgentTask.objects.filter(agent_name=agent_name)
    average_confidence = tasks.aggregate(avg=Avg('confidence'))['avg']

    disagreement_appearance_count = CouncilDisagreement.objects.filter(
        Q(position_a__agent_name=agent_name) | Q(position_b__agent_name=agent_name)
    ).count()

    cross_examination_count = CrossExaminationExchange.objects.filter(
        Q(questioner_agent=agent_name) | Q(target_agent=agent_name)
    ).count()

    return {
        'agent_name': agent_name,
        'agent_task_count': tasks.count(),
        'average_confidence': round(average_confidence, 1) if average_confidence is not None else None,
        'disagreement_appearance_count': disagreement_appearance_count,
        'cross_examination_count': cross_examination_count,
    }
