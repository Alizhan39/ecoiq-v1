"""
good_agents/services/responsible_party.py — real-world party resolution
(PR5 Phase 4, extended by PR7's Capability Graph). Never infers contact
details from guesswork: a deterministic suggestion built from the
opportunity's own real signal `publisher` field always starts at
`possible_organisation` — only an explicit human call to `confirm()` can
move it to `known_organisation`.

PR7: every suggestion here now resolves through
`capability_graph.services.organisations.get_or_create_organisation()`
rather than storing a bare name per opportunity — the same real
organisation (e.g. USGS, seen across every earthquake opportunity) is one
`Organisation` row referenced by many `ResponsibleParty` join records, not
one freestanding duplicate per opportunity.
"""
from django.utils import timezone

from capability_graph.services.matcher import find_organisations_for_capability
from capability_graph.services.organisations import get_or_create_organisation
from good_agents.models import ResponsibleParty

# Publishers this repo's real SignalProvider adapters actually emit
# (see provider_adapters.py) mapped to a plausible party_type — a
# deterministic lookup over KNOWN real publisher strings, never a guess
# from free text.
PUBLISHER_TO_PARTY_TYPE = {
    'GOV.UK': 'government_department',
    'UK Environment Agency': 'regulator',
    'USGS (US Geological Survey)': 'research_institution',
}


def suggest_from_signal(opportunity, signal):
    """
    Creates a ResponsibleParty suggestion from a real WorldSignal's own
    `publisher` field — never fabricated, always `possible_organisation`
    until a human confirms it. Returns None if the signal has no publisher
    to go on (an honest "unresolved" case the caller should surface, not paper over).
    """
    if not signal.publisher:
        return None
    party_type = PUBLISHER_TO_PARTY_TYPE.get(signal.publisher, 'other')
    organisation = get_or_create_organisation(
        signal.publisher, org_type=party_type, jurisdiction=signal.region or '',
    )
    party, _ = ResponsibleParty.objects.get_or_create(
        opportunity=opportunity, name=signal.publisher,
        defaults=dict(
            party_type=party_type, resolution_status='possible_organisation',
            evidence_ref=f'good_agents.WorldSignal:{signal.pk}',
            confidence=60.0 if signal.publisher in PUBLISHER_TO_PARTY_TYPE else 30.0,
            notes=f'Suggested from the publisher field of signal "{signal.title}" — not yet human-confirmed.',
            organisation=organisation,
        ),
    )
    return party


def suggest_from_capability_graph(opportunity, capability, *, jurisdiction=None, topic_domain=None):
    """
    Suggests ResponsibleParty candidates from the Capability Graph itself
    — organisations with a real, evidence-backed claim to `capability`
    (e.g. 'respond_to_emergency', 'regulate') rather than a guess from the
    triggering signal's publisher field. Every candidate returned is
    `possible_organisation` (never auto-confirmed) and carries the real
    OrganisationCapability's evidence_source as its evidence_ref, so a
    human reviewer can trace exactly why it was suggested. Returns an
    empty list — never a fabricated candidate — if the graph has no
    evidence-backed match yet.
    """
    edges = find_organisations_for_capability(capability, jurisdiction=jurisdiction, topic_domain=topic_domain)
    parties = []
    for edge in edges:
        party, _ = ResponsibleParty.objects.get_or_create(
            opportunity=opportunity, organisation=edge.organisation,
            defaults=dict(
                name=edge.organisation.name, party_type=edge.organisation.org_type,
                resolution_status='possible_organisation',
                evidence_ref=edge.evidence_source or f'capability_graph.OrganisationCapability:{edge.pk}',
                confidence=40.0 if edge.verification_state in ('unverified', 'self_reported') else 70.0,
                notes=(
                    f'Suggested via Capability Graph: {edge.organisation.name} has an evidence-backed '
                    f'"{edge.get_capability_display()}" capability'
                    f'{f" for {edge.topic_domain}" if edge.topic_domain else ""} '
                    f'({edge.get_verification_state_display()}). '
                    f'{f"Limitations: {edge.limitations}" if edge.limitations else ""}'
                ).strip(),
            ),
        )
        parties.append(party)
    return parties


def confirm(party, *, actor=None, linked_company=None):
    """The only sanctioned way to move a ResponsibleParty to 'known_organisation'."""
    party.resolution_status = 'known_organisation'
    party.confirmed_by = actor
    party.confirmed_at = timezone.now()
    if linked_company is not None:
        party.linked_company = linked_company
    party.save(update_fields=['resolution_status', 'confirmed_by', 'confirmed_at', 'linked_company'])
    return party


def mark_unresolved(party, *, reason=''):
    party.resolution_status = 'unresolved'
    if reason:
        party.notes = f'{party.notes}\n\nMarked unresolved: {reason}'.strip()
    party.save(update_fields=['resolution_status', 'notes'])
    return party
