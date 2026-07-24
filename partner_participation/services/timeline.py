"""
partner_participation/services/timeline.py — the one append-only
Network Activity Timeline per Organisation (PR9 Phase 17). Mirrors
good_agents.services.timeline.record_event()'s exact convention.
"""
from partner_participation.models import NetworkActivityEvent


def record_event(organisation, event_type, *, actor=None, source_object_reference='', notes=''):
    return NetworkActivityEvent.objects.create(
        organisation=organisation, event_type=event_type, actor=actor,
        source_object_reference=source_object_reference, notes=notes,
    )
