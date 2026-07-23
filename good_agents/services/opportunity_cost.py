"""
good_agents/services/opportunity_cost.py — OpportunityCostAgent (Phase 8).

Explicitly a system-level specialist, NOT one of the 114 principle lenses.
Answers: "could this same capital/time/attention create materially more
good elsewhere?" Reuses capital_guardian.services.better_way's already-
computed ranking (`BetterWayResult`, whose `ranked` list holds dicts of
shape {'option': InterventionOption, 'safety_status', 'safety_reason',
**scores}) rather than re-deriving a second scoring system.
"""
from good_agents.models import OpportunityCostAssessment


def assess_from_better_way(opportunity, better_way_result):
    """
    better_way_result: a capital_guardian.services.better_way.BetterWayResult
    already computed for this opportunity's OperationalLoss.
    """
    ranked = better_way_result.ranked or []
    preferred = ranked[0] if ranked else None
    runner_up = ranked[1] if len(ranked) > 1 else None

    alternatives_considered = [
        {
            'title': item['option'].title,
            'intervention_type': item['option'].intervention_type,
            'rank': i + 1,
            'composite_score': item.get('composite_score'),
        }
        for i, item in enumerate(ranked)
    ] + [
        {'title': item['option'].title, 'intervention_type': item['option'].intervention_type, 'blocked_reason': item['reason']}
        for item in (better_way_result.blocked or [])
    ]

    trade_offs = {
        key: {'title': value['option'].title, 'composite_score': value.get('composite_score')}
        for key, value in (better_way_result.trade_offs or {}).items()
    }

    preferred_option = (
        f"{preferred['option'].title} — {better_way_result.why_top_ranked}".strip(' —')
        if preferred else 'No eligible (non-blocked) option was found for this loss.'
    )
    if preferred and better_way_result.baseline_ranked_first:
        preferred_option = f"{preferred['option'].title} — {better_way_result.baseline_warning}"

    assessment, _ = OpportunityCostAssessment.objects.update_or_create(
        opportunity=opportunity,
        defaults=dict(
            alternatives_considered=alternatives_considered,
            preferred_option=preferred_option,
            best_alternative=runner_up['option'].title if runner_up else '',
            trade_offs=trade_offs,
            confidence=70.0 if (preferred and not better_way_result.baseline_ranked_first) else 20.0,
            evidence_that_would_change_recommendation=(
                '; '.join(better_way_result.limitations) if better_way_result.limitations else ''
            ),
        ),
    )
    return assessment
