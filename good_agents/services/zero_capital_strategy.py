"""
good_agents/services/zero_capital_strategy.py — ZeroCapitalStrategy (PR3
Phase 10). Before asking "how much money do we need?", rank what can be
achieved with resources that already exist — derived from real
ResourceMatch rows, never invented independently of a match.
"""
from good_agents.models import ZeroCapitalStrategyAction
from good_agents.services.matcher import ZERO_CAPITAL_RESOURCE_TYPES

# Maps a matched resource_type to the most natural zero-capital action type.
RESOURCE_TYPE_TO_ACTION = {
    'ngo': 'connect', 'implementer': 'connect', 'supplier': 'connect',
    'expertise': 'introduce', 'labour': 'introduce',
    'data': 'share', 'logistics': 'redirect',
    'food_surplus': 'redirect', 'energy_surplus': 'redirect', 'waste_heat': 'redirect', 'material_surplus': 'redirect',
    'equipment': 'reuse', 'building': 'reuse', 'land': 'reuse', 'public_infrastructure': 'reuse',
    'technology': 'match',
    'government_programme': 'identify_programme', 'subsidy': 'identify_subsidy', 'grant': 'identify_grant',
}


def rank_actions_for_opportunity(opportunity):
    """
    Reads every ResourceMatch attached to this opportunity's Needs, ranks
    the zero-capital-eligible ones first (highest match confidence first),
    persists ZeroCapitalStrategyAction rows. Idempotent per
    (opportunity, action_type).
    """
    matches = []
    for need in opportunity.needs.all():
        matches.extend(need.matches.select_related('resource').all())

    zero_capital_matches = [m for m in matches if m.resource.resource_type in ZERO_CAPITAL_RESOURCE_TYPES]
    zero_capital_matches.sort(key=lambda m: -m.confidence)

    actions = []
    rank = 1
    seen_action_types = set()
    for match in zero_capital_matches:
        action_type = RESOURCE_TYPE_TO_ACTION.get(match.resource.resource_type, 'identify_idle_asset')
        if action_type in seen_action_types:
            continue
        seen_action_types.add(action_type)
        action, _ = ZeroCapitalStrategyAction.objects.update_or_create(
            opportunity=opportunity, action_type=action_type,
            defaults=dict(
                rank=rank,
                rationale=f'Matched resource "{match.resource.title}" ({match.confidence:.0f}% match confidence): {match.match_reason[:200]}',
                resource_match=match,
            ),
        )
        actions.append(action)
        rank += 1

    # "reduce_waste" is always a safe, real GREEN action to surface when the
    # opportunity is waste/circular-economy themed, even with no matched
    # resource yet — analysing one's own waste never requires capital.
    if opportunity.theme in ('waste', 'circular_economy') and 'reduce_waste' not in seen_action_types:
        action, _ = ZeroCapitalStrategyAction.objects.update_or_create(
            opportunity=opportunity, action_type='reduce_waste',
            defaults=dict(rank=rank, rationale='Waste/circular-economy themed opportunity — analyse and reduce waste at source first.'),
        )
        actions.append(action)

    if actions:
        opportunity.zero_capital_possible = True
        opportunity.save(update_fields=['zero_capital_possible', 'updated_at'])
    return actions
