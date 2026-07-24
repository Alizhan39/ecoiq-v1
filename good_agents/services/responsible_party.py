"""
good_agents/services/responsible_party.py — real-world party resolution
(PR5 Phase 4). Never infers contact details from guesswork: a deterministic
suggestion built from the opportunity's own real signal `publisher` field
always starts at `possible_organisation` — only an explicit human call to
`confirm()` can move it to `known_organisation`.
"""
from django.utils import timezone

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
    party, _ = ResponsibleParty.objects.get_or_create(
        opportunity=opportunity, name=signal.publisher,
        defaults=dict(
            party_type=party_type, resolution_status='possible_organisation',
            evidence_ref=f'good_agents.WorldSignal:{signal.pk}',
            confidence=60.0 if signal.publisher in PUBLISHER_TO_PARTY_TYPE else 30.0,
            notes=f'Suggested from the publisher field of signal "{signal.title}" — not yet human-confirmed.',
        ),
    )
    return party


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
