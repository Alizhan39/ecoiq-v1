"""
good_agents/services/circular_economy.py — CircularEconomyMatcher (PR3
Phase 9): a thin specialisation of matcher.py's NeedResourceMatcher for the
specific question "is someone's waste, surplus or idle capacity someone
else's resource?" It does not re-score matches — it reuses
matcher.match_need's real geography/type/evidence scoring, then enriches
qualifying matches with the extra structured fields Phase 9 asks for
(feasibility signal, logistics, regulatory, economics, environmental
benefit) and marks them `is_circular_economy_match=True`.

Never claims technical feasibility "verified" from conceptual similarity
alone — feasibility_signal stays 'unverified' unless the resource itself
carries real supporting evidence_refs.
"""
from good_agents.services.matcher import match_need

CIRCULAR_RESOURCE_TYPES = frozenset({
    'waste_heat', 'food_surplus', 'material_surplus', 'energy_surplus', 'equipment', 'building',
})

# One-line, honest framing per resource type — not a feasibility claim, just
# what benefit dimension a human reviewer should go verify.
ENVIRONMENTAL_BENEFIT_FRAMING = {
    'waste_heat': 'Potential avoided emissions from displaced fossil heating — requires a real energy-balance study to quantify.',
    'food_surplus': 'Potential avoided food waste and associated emissions — requires real volume/logistics data to quantify.',
    'material_surplus': 'Potential avoided virgin-material extraction — requires a real material audit to quantify.',
    'energy_surplus': 'Potential avoided curtailment/waste of generated energy — requires real grid/demand data to quantify.',
    'equipment': 'Potential avoided manufacturing of new equipment — requires a real condition/lifecycle assessment.',
    'building': 'Potential avoided new construction — requires a real suitability/safety assessment.',
}


def match_circular_economy(need, candidate_resources=None, min_score=30.0, max_matches=5):
    """
    Runs the same real matcher.match_need scoring, restricted to circular-
    economy-relevant resource types, then enriches the resulting
    ResourceMatch rows with circular-economy framing and flags them.
    """
    from good_agents.models import AvailableResource

    candidates = candidate_resources if candidate_resources is not None else AvailableResource.objects.filter(
        status='active', resource_type__in=CIRCULAR_RESOURCE_TYPES,
    )
    matches = match_need(need, candidate_resources=candidates, min_score=min_score, max_matches=max_matches)

    for match in matches:
        resource = match.resource
        same_region = bool(
            need.region and resource.region and need.region.strip().lower() == resource.region.strip().lower()
        )
        logistics_note = (
            'Same region — logistics likely feasible, distance not independently measured.'
            if same_region else 'Different region recorded — logistics/distance feasibility unassessed.'
        )
        feasibility_signal = (
            'unverified' if not resource.evidence_refs else 'evidence-supported (see resource.evidence_refs)'
        )
        environmental_note = ENVIRONMENTAL_BENEFIT_FRAMING.get(resource.resource_type, '')

        match.is_circular_economy_match = True
        match.match_reason = (
            f'{match.match_reason}\n\n[Circular economy] Technical feasibility: {feasibility_signal}. '
            f'{logistics_note} Regulatory constraints not assessed — flag for human review before any '
            f'physical action. {environmental_note}'
        )
        match.save(update_fields=['is_circular_economy_match', 'match_reason'])

    return matches
