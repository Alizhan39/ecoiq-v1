"""
partner_participation/services/feedback.py — PR9 Phase 24: transparent,
deterministic feedback from real response outcomes into future routing —
never opaque ML. Every adjustment is a real, explained, configurable rule
over already-persisted `RoutingCandidate` history for the SAME
organisation + theme; nothing here is learned or fitted.
"""
# Configurable thresholds — plain module constants, not a config file,
# matching this repo's existing deterministic-scoring convention (see
# good_agents.services.orchestrator's own min_score/max_activated).
REPEATED_NOT_INTERESTED_THRESHOLD = 2
REPEATED_INTERESTED_THRESHOLD = 2
REPEATED_NEEDS_INFO_THRESHOLD = 2

# The confidence tiers feedback is allowed to nudge — deliberately
# excludes 'no_verified_route'/'needs_review', which describe a
# structural fact (no route exists / a conflict is unresolved) that no
# amount of response history should override.
_ADJUSTABLE_TIERS = [
    'possible_responsible_party', 'participation_match', 'verified_capability_match', 'strong_verified_match',
]


def historical_feedback_adjustment(organisation, theme):
    """
    Returns (delta, reason, info_flag) where delta is -1/0/+1 (a single
    tier, never a bigger jump — "modest," per Phase 24's own wording),
    reason is a human-readable explanation (or '' if delta==0), and
    info_flag is a string note when repeated NEEDS_MORE_INFORMATION
    responses suggest required fields may be missing (never itself an
    adjustment).
    """
    from partner_participation.models import RoutingCandidate

    past = RoutingCandidate.objects.filter(organisation=organisation, opportunity__theme=theme)
    not_interested_count = past.filter(status='not_interested').count()
    interested_count = past.filter(status__in=['interested', 'accepted_for_next_step']).count()
    needs_info_count = past.filter(status='needs_more_information').count()

    delta, reason = 0, ''
    if not_interested_count >= REPEATED_NOT_INTERESTED_THRESHOLD:
        delta, reason = -1, (
            f'{not_interested_count} past "not interested" response(s) from this organisation for this theme '
            f'— relevance modestly reduced.'
        )
    elif interested_count >= REPEATED_INTERESTED_THRESHOLD:
        delta, reason = 1, (
            f'{interested_count} past "interested"/"accepted for next step" response(s) from this organisation '
            f'for this theme — relevance modestly boosted.'
        )

    info_flag = ''
    if needs_info_count >= REPEATED_NEEDS_INFO_THRESHOLD:
        info_flag = (
            f'This organisation has requested more information {needs_info_count} time(s) for this theme — '
            f'consider whether required routing fields (evidence, deadline, eligibility) are complete before sharing again.'
        )
    return delta, reason, info_flag


def apply_adjustment(confidence_label, delta):
    if delta == 0 or confidence_label not in _ADJUSTABLE_TIERS:
        return confidence_label
    index = _ADJUSTABLE_TIERS.index(confidence_label)
    new_index = max(0, min(len(_ADJUSTABLE_TIERS) - 1, index + delta))
    return _ADJUSTABLE_TIERS[new_index]
