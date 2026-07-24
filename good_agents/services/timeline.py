"""
good_agents/services/timeline.py — one immutable timeline per opportunity
(PR5 Phase 14). Rows are never edited or deleted after creation — every
other PR5 service calls `record_event` rather than writing
`ActionTimelineEvent` directly.
"""
from good_agents.models import ActionTimelineEvent


def record_event(opportunity, event_type, *, actor=None, source_object_reference='', notes=''):
    return ActionTimelineEvent.objects.create(
        opportunity=opportunity, event_type=event_type, actor=actor,
        source_object_reference=source_object_reference, notes=notes,
    )
