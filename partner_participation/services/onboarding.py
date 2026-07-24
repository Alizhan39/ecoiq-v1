"""
partner_participation/services/onboarding.py — a transparent onboarding
checklist and derived routing-readiness (PR9 Phase 5-6, 18). Every
result here is computed fresh from real rows every call — never a stored,
staleness-prone "100% complete" flag. Nothing here EVER reports a step
complete that isn't genuinely, currently true.

Phase 18's eight distinct trust states are kept genuinely separate below
(IDENTITY VERIFIED / MEMBERSHIP VERIFIED / CAPABILITY SELF-DECLARED /
CAPABILITY EVIDENCE-SUPPORTED / CAPABILITY HUMAN-REVIEWED / ROUTE
VERIFIED / PARTICIPATION CONSENTED / ROUTING READY) — never collapsed
into one "trusted partner" badge.
"""
from capability_graph.models import CapabilityConflict
from partner_participation.services.consent import has_active_consent
from partner_participation.services.staleness import staleness_of


def identity_verified(organisation):
    """Real external evidence exists about this organisation — never inferred from its name alone."""
    return (
        organisation.linked_company_id is not None
        or organisation.capabilities.exclude(verification_state='unverified').exists()
    )


def membership_verified(organisation):
    return organisation.memberships.filter(status='verified_member').exists()


def has_capability_self_declared(organisation):
    return organisation.capabilities.filter(provenance='organisation_declared').exists()


def has_capability_evidence_supported(organisation):
    return organisation.capabilities.filter(
        provenance='organisation_declared', verification_state__in=['evidence_supported', 'human_reviewed', 'independently_verified'],
    ).exists()


def has_capability_human_reviewed(organisation):
    return organisation.capabilities.filter(verification_state__in=['human_reviewed', 'independently_verified']).exists()


def route_verified(organisation):
    return any(cap.public_routes.filter(is_currently_open=True).exists() for cap in organisation.capabilities.all())


def participation_consented(organisation):
    return any(
        has_active_consent(m) for m in organisation.memberships.filter(status='verified_member')
    )


def onboarding_checklist(organisation):
    """
    Real, per-step booleans — never a fabricated 100%. Order matches
    Phase 5's own list.
    """
    has_capability = organisation.capabilities.exists()
    has_service_area = organisation.capabilities.exclude(jurisdiction='').exists()
    has_preference = organisation.opportunity_preferences.exists()

    steps = [
        {'step': 'Organisation identity verified', 'complete': identity_verified(organisation)},
        {'step': 'Membership verified', 'complete': membership_verified(organisation)},
        {'step': 'Capability declared', 'complete': has_capability},
        {'step': 'Capability evidence added', 'complete': has_capability_evidence_supported(organisation)},
        {'step': 'Service area defined', 'complete': has_service_area},
        {'step': 'Opportunity preferences defined', 'complete': has_preference},
        {'step': 'Public route confirmed', 'complete': route_verified(organisation)},
        {'step': 'Participation consent active', 'complete': participation_consented(organisation)},
    ]
    ready, reasons = is_routing_ready(organisation)
    steps.append({'step': 'Routing ready', 'complete': ready})
    return steps


def is_routing_ready(organisation):
    """
    Phase 6 — explicit, minimum requirements. Returns (bool, reasons)
    where `reasons` always lists exactly what's missing when False —
    never a silent "not ready."
    """
    reasons = []

    if not membership_verified(organisation):
        reasons.append('No verified membership.')
    if not participation_consented(organisation):
        reasons.append('No active participation consent.')

    usable_capabilities = organisation.capabilities.exclude(verification_state__in=['disputed', 'expired'])
    if not usable_capabilities.exists():
        reasons.append('No usable (non-disputed, non-expired) capability declared.')
    elif not usable_capabilities.exclude(jurisdiction='').exists():
        reasons.append('No capability has a defined service area (jurisdiction).')
    else:
        stale_all = all(staleness_of(cap) == 'stale' for cap in usable_capabilities)
        if stale_all:
            reasons.append('Every usable capability is stale — reconfirmation required.')

    if not organisation.opportunity_preferences.filter(
        acceptance_mode__in=['open_to_relevant_opportunities', 'limited', 'invitation_only', 'application_required'],
    ).exists():
        reasons.append('No opportunity preference in a routable acceptance mode.')

    if not route_verified(organisation):
        reasons.append('No currently-open public route.')

    unresolved_conflicts = CapabilityConflict.objects.filter(
        capability__organisation=organisation, resolution='unresolved',
    ).exists()
    if unresolved_conflicts:
        reasons.append('Unresolved capability conflict requires review.')

    return (len(reasons) == 0, reasons)
