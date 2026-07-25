"""
public_need_discovery/services/jurisdiction.py — Phase 7: deterministic
jurisdiction resolution. Jurisdiction is free-text everywhere else in this
repo (capability_graph.Organisation.jurisdiction,
OutreachCandidateAssessment.jurisdiction) — this module does not invent a
competing structured model, it only resolves a candidate's jurisdiction
string the same deterministic way responsible_party.py already resolves
publisher -> party_type: a fixed lookup over KNOWN real publishers/regions,
never a guess from free text. When nothing real supports a value, the
candidate stays honestly unresolved (NO_JURISDICTION) rather than filled
with an inferred guess.
"""
NO_JURISDICTION = 'NO_JURISDICTION'

# Real publishers this repo's adapters actually emit, mapped to the real
# jurisdiction their institutional remit covers — the same discipline as
# good_agents.services.responsible_party.PUBLISHER_TO_PARTY_TYPE.
PUBLISHER_TO_JURISDICTION = {
    'UK Environment Agency': 'England',
    'GOV.UK': 'United Kingdom',
    'data.gov.uk': 'United Kingdom',
    'USGS (US Geological Survey)': 'Global',
}


def resolve_jurisdiction(opportunity):
    """
    Returns (jurisdiction: str, resolved: bool, notes: str). Prefers the
    opportunity's own real `region` field (set from real adapter data,
    e.g. EA's eaAreaName) when present; falls back to a known publisher's
    institutional jurisdiction; otherwise reports NO_JURISDICTION honestly
    rather than guessing from title/summary free text.
    """
    if opportunity.region:
        return opportunity.region, True, f'Resolved from the opportunity\'s own region field: {opportunity.region!r}.'

    lead_signal = None
    from good_agents.models import WorldSignal
    if opportunity.detected_signals:
        lead_signal = WorldSignal.objects.filter(title__in=opportunity.detected_signals).first()

    if lead_signal is not None and lead_signal.region:
        return lead_signal.region, True, f'Resolved from the originating signal\'s region field: {lead_signal.region!r}.'

    publisher = lead_signal.publisher if lead_signal is not None else ''
    if publisher and publisher in PUBLISHER_TO_JURISDICTION:
        jurisdiction = PUBLISHER_TO_JURISDICTION[publisher]
        return (
            jurisdiction, True,
            f'No region on the signal or opportunity — resolved from the known institutional jurisdiction '
            f'of real publisher {publisher!r}.',
        )

    if publisher:
        return (
            NO_JURISDICTION, False,
            f'Publisher {publisher!r} is not a known publisher with a recorded institutional jurisdiction — '
            f'not guessed from free text.',
        )
    return NO_JURISDICTION, False, 'No region, no originating signal, and no publisher to resolve jurisdiction from.'
