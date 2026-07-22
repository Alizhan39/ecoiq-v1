"""
good_agents/services/matcher.py — NeedResourceMatcher (PR3 Phase 8).

Deterministic multi-factor scoring, not semantic similarity: type
compatibility, geography, timing/expiry, capacity, and confidence
carry-over. A resource whose type cannot plausibly satisfy a need's type is
never matched at all, regardless of how similar the text sounds.
"""
from dataclasses import dataclass, field

from good_agents.models import ResourceMatch

# Which resource types can plausibly satisfy which need type. Deliberately
# conservative — a type not listed here never scores above 0 for that need,
# no matter how textually similar the titles are.
NEED_TYPE_TO_RESOURCE_TYPES = {
    'energy': {'energy_surplus', 'waste_heat', 'grant', 'subsidy', 'government_programme', 'technology', 'capital', 'public_infrastructure'},
    'water': {'public_infrastructure', 'technology', 'ngo', 'capital', 'government_programme'},
    'food': {'food_surplus', 'ngo', 'logistics', 'philanthropy'},
    'housing': {'building', 'land', 'government_programme', 'grant', 'capital'},
    'health': {'ngo', 'expertise', 'philanthropy', 'government_programme'},
    'education': {'expertise', 'technology', 'ngo', 'philanthropy'},
    'employment': {'labour', 'expertise', 'government_programme', 'implementer'},
    'justice': {'expertise', 'ngo', 'government_programme'},
    'environment': {'technology', 'expertise', 'ngo', 'government_programme', 'capital'},
    'biodiversity': {'ngo', 'expertise', 'government_programme'},
    'waste': {'waste_heat', 'material_surplus', 'technology', 'equipment', 'implementer'},
    'climate': {'technology', 'capital', 'government_programme', 'expertise'},
    'infrastructure': {'public_infrastructure', 'capital', 'equipment', 'government_programme'},
    'digital_access': {'technology', 'data', 'government_programme', 'implementer'},
    'financial_inclusion': {'capital', 'impact_investment', 'islamic_finance', 'government_programme'},
    'community_resilience': {'ngo', 'philanthropy', 'government_programme', 'labour', 'implementer'},
}

# Resource types that typically enable a zero-capital next action (an
# introduction/identification) rather than a funding application.
ZERO_CAPITAL_RESOURCE_TYPES = frozenset({
    'ngo', 'implementer', 'expertise', 'labour', 'data', 'logistics', 'supplier',
    'food_surplus', 'energy_surplus', 'waste_heat', 'material_surplus', 'equipment',
    'building', 'land', 'public_infrastructure', 'technology',
})


@dataclass
class MatchScore:
    score: float
    reasons: list = field(default_factory=list)
    missing_evidence: list = field(default_factory=list)
    next_action: str = ''


def score_match(need, resource):
    if resource.resource_type not in NEED_TYPE_TO_RESOURCE_TYPES.get(need.need_type, set()):
        return None  # not a plausible match at all — never scored, never persisted

    if resource.is_expired():
        # Temporal memory (Phase 28): a resource that was open and is now
        # closed/expired must never be offered as a new match — hard reject,
        # not a soft penalty. Its ResourceStatusChange history (if any)
        # remains intact; only NEW matches are blocked.
        return None

    score = 40.0
    reasons = [f'"{resource.get_resource_type_display()}" is a plausible resource for a "{need.get_need_type_display()}" need.']
    missing_evidence = []

    need_geo = (need.region or (need.geography.name if need.geography_id else '')).strip().lower()
    resource_geo = (resource.region or (resource.geography.name if resource.geography_id else '')).strip().lower()
    if need_geo and resource_geo:
        if need_geo == resource_geo or need_geo in resource_geo or resource_geo in need_geo:
            score += 25
            reasons.append(f'Geography aligns ({resource.region or resource.geography}).')
        else:
            score += 5
            reasons.append('Geography differs — cross-border match, see CrossBorderAssessment if pursued.')
    else:
        score += 10
        missing_evidence.append('Geography not fully specified on one side — relevance unconfirmed.')

    score += 15

    if resource.capacity:
        score += 10
    else:
        missing_evidence.append('Resource capacity not specified.')

    if not resource.evidence_refs:
        missing_evidence.append('Resource availability has no evidence reference.')
    else:
        score += 10 * min(resource.confidence, 100) / 100

    next_action = 'connect' if resource.resource_type in ZERO_CAPITAL_RESOURCE_TYPES else 'find_funding'

    return MatchScore(score=round(min(score, 100.0), 1), reasons=reasons, missing_evidence=missing_evidence, next_action=next_action)


def match_need(need, candidate_resources=None, min_score=30.0, max_matches=5):
    """
    Scores `need` against candidate AvailableResource rows (defaults to all
    active, non-expired resources), persists a ResourceMatch for every
    result at/above `min_score`, capped at `max_matches`. Returns the list
    of created/updated ResourceMatch rows, best score first.
    """
    from good_agents.models import AvailableResource

    candidates = candidate_resources if candidate_resources is not None else AvailableResource.objects.filter(status='active')
    scored = []
    for resource in candidates:
        result = score_match(need, resource)
        if result is not None and result.score >= min_score:
            scored.append((resource, result))

    scored.sort(key=lambda pair: -pair[1].score)
    matches = []
    for resource, result in scored[:max_matches]:
        match, _ = ResourceMatch.objects.update_or_create(
            need=need, resource=resource,
            defaults=dict(
                match_reason='; '.join(result.reasons), confidence=result.score,
                missing_evidence=result.missing_evidence, next_action=result.next_action,
            ),
        )
        matches.append(match)

    if matches:
        need.status = 'matched'
        need.save(update_fields=['status', 'updated_at'])
    return matches
