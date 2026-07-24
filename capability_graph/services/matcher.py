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
_VERIFICATION_RANK = {
    'unverified': 0, 'self_reported': 1, 'documented': 2, 'independently_verified': 3,
}


def find_organisations_for_capability(capability, *, jurisdiction=None, topic_domain=None, min_verification='unverified'):
    """
    Returns OrganisationCapability rows matching `capability`, optionally
    narrowed by jurisdiction/topic (substring match — real-world
    jurisdiction strings are inconsistent, e.g. "England" vs "UK", so an
    exact match would silently miss real matches; a human still reviews
    every result before any action is taken, per the governed-action
    pipeline this feeds into) and floored at `min_verification` (never
    returns a claim weaker than the caller says it's willing to act on).
    """
    floor = _VERIFICATION_RANK.get(min_verification, 0)
    acceptable_states = [state for state, rank in _VERIFICATION_RANK.items() if rank >= floor]

    qs = OrganisationCapability.objects.filter(
        capability=capability, verification_state__in=acceptable_states,
    ).select_related('organisation').prefetch_related('public_routes')

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
