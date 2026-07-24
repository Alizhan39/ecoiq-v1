"""
partner_participation/services/response_capture.py — PR9 Phase 14-15:
real response recording, either by EcoIQ staff (any channel: phone,
email reply, in-person) or by the organisation itself through the
Partner Portal (self-service). Never fabricates a reply — every call
requires the specific real facts a human is asserting.

Self-service (Phase 15) is deliberately narrow: a partner member can only
ever move a candidate through the SAME real ROUTING_ALLOWED_TRANSITIONS
state machine everyone else uses (interested / not_interested / needs_
more_information / accepted_for_next_step) — never anything that
resembles approving funding or claiming impact, which stay exclusively
EcoIQ-staff or Capital-Guardian-governed actions elsewhere in this repo.
"""
from django.utils import timezone

from partner_participation.services import routing
from partner_participation.services.membership import can_respond_to_routing
from partner_participation.services.timeline import record_event

# The only statuses a real response (staff-recorded OR partner
# self-service) may ever set — never 'approved_to_share'/'shared', which
# stay exclusively EcoIQ-staff actions via services/delivery.py.
RESPONSE_STATUSES = frozenset({'viewed', 'interested', 'not_interested', 'needs_more_information', 'accepted_for_next_step'})


class ResponseNotAllowedError(Exception):
    pass


def record_response(candidate, new_status, *, actor, channel='', summary='', reference=''):
    """EcoIQ staff recording a real response received through any channel (phone, email reply, in person)."""
    if new_status not in RESPONSE_STATUSES:
        raise ResponseNotAllowedError(f'{new_status!r} is not a valid response state.')
    notes = summary
    if channel:
        notes = f'[{channel}] {notes}'.strip()
    if reference:
        notes = f'{notes}\n\nReference: {reference}'.strip()
    candidate = routing.transition(candidate, new_status, actor=actor, notes=notes)
    _record_network_event(candidate, new_status, actor)
    return candidate


def partner_self_service_response(candidate, new_status, *, user, notes=''):
    """
    The organisation's own verified member responding directly through
    the Partner Portal. Requires the exact same role check as any other
    editing action on this organisation.
    """
    if new_status not in RESPONSE_STATUSES:
        raise ResponseNotAllowedError(f'{new_status!r} is not a valid response state.')
    if not can_respond_to_routing(candidate.organisation, user):
        raise ResponseNotAllowedError(f'{user} is not authorised to respond on behalf of {candidate.organisation}.')
    candidate = routing.transition(candidate, new_status, actor=user, notes=notes)
    _record_network_event(candidate, new_status, user)
    return candidate


def _record_network_event(candidate, new_status, actor):
    from partner_participation.services import notify

    event_type = {
        'interested': 'interested', 'not_interested': 'declined',
    }.get(new_status, 'responded')
    record_event(
        candidate.organisation, event_type, actor=actor,
        source_object_reference=f'partner_participation.RoutingCandidate:{candidate.pk}',
    )
    if new_status == 'interested':
        notify.notify_organisation_interested(candidate)
    elif new_status == 'needs_more_information':
        notify.notify_needs_more_information(candidate)
    else:
        notify.notify_partner_responded(candidate)


def mark_no_response_if_stale(candidate, *, grace_days=7):
    """
    Honest labelling, not a fabricated reply: once a candidate has been
    'shared' for longer than `grace_days` with no reply, it becomes
    'no_response' — an accurate description of reality, never an
    assumption of disinterest.
    """
    if candidate.status != 'shared':
        return candidate
    if candidate.shared_at is None:
        return candidate
    if (timezone.now() - candidate.shared_at).days < grace_days:
        return candidate
    return routing.transition(candidate, 'no_response', actor=None)
