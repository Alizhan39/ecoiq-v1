"""
capability_graph/services/matcher.py — the core reusable query other apps
call: given a required capability (and optionally a jurisdiction/topic),
which real, evidence-backed organisations can plausibly do it. Pure read,
deterministic, no ML/embeddings — matches PR3's own scoring discipline.

This is the ONE function good_agents, FundingMatch routing, Capital
Guardian, and any future consumer should call rather than each
re-implementing its own "who can do X" heuristic.
"""
from capability_graph.models import OrganisationCapability

# Ordinal so "at least documented" comparisons are simple integer checks
# rather than repeating the choice list everywhere a caller wants a floor.
# PR8 extended VERIFICATION_STATE_CHOICES with four new states on the SAME
# ladder ('evidence_supported', 'human_reviewed') or as side-states that
# break monotonicity ('disputed', 'expired' — see below) — every rankable
# state must be listed here or it silently vanishes from every query
# result regardless of `min_verification` (the exact regression PR8's own
# routing engine smoke-test caught before this fix).
_VERIFICATION_RANK = {
    'unverified': 0, 'self_reported': 1, 'evidence_supported': 2,
    'documented': 3, 'human_reviewed': 4, 'independently_verified': 5,
}
# 'disputed'/'expired' are not "weaker" or "stronger" than the ladder above
# — they are side-states meaning "do not treat this claim as currently
# reliable at all." Always excluded here regardless of `min_verification`,
# never silently ranked as if they were just a low-confidence match.
_NEVER_MATCHABLE_STATES = frozenset({'disputed', 'expired'})


def find_organisations_for_capability(capability, *, jurisdiction=None, topic_domain=None, min_verification='unverified'):
    """
    Returns OrganisationCapability rows matching `capability`, optionally
    narrowed by jurisdiction/topic (substring match — real-world
    jurisdiction strings are inconsistent, e.g. "England" vs "UK", so an
    exact match would silently miss real matches; a human still reviews
    every result before any action is taken, per the governed-action
    pipeline this feeds into) and floored at `min_verification` (never
    returns a claim weaker than the caller says it's willing to act on).
    Disputed/expired claims are never returned regardless of the floor.
    """
    floor = _VERIFICATION_RANK.get(min_verification, 0)
    acceptable_states = [state for state, rank in _VERIFICATION_RANK.items() if rank >= floor]

    qs = OrganisationCapability.objects.filter(
        capability=capability, verification_state__in=acceptable_states,
    ).exclude(verification_state__in=_NEVER_MATCHABLE_STATES).select_related('organisation').prefetch_related('public_routes')

    if jurisdiction:
        qs = qs.filter(jurisdiction__icontains=jurisdiction)
    if topic_domain:
        qs = qs.filter(topic_domain__icontains=topic_domain)

    return qs.order_by('-verification_state', 'organisation__name')


def find_organisations_for_need_type(need_type, **kwargs):
    """Convenience wrapper: required capabilities for a Need -> matching organisations for each."""
    from capability_graph.services.needs import required_capabilities_for_need_type
    results = {}
    for capability in required_capabilities_for_need_type(need_type):
        results[capability] = list(find_organisations_for_capability(capability, **kwargs))
    return results
