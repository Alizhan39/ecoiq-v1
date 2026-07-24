"""
good_agents/services/action_gate.py — the ONE authoritative "what happens
next" governance layer for a GoodOpportunity (PR5 Phase 1).

No discovered opportunity may become an active action automatically.
Every transition is recorded in ActionGateTransition (actor, timestamp,
previous_state, new_state, reason, evidence_reviewed) and mirrored onto
the opportunity's ActionTimelineEvent — never silent, never bypassed.
Only transitions listed in ActionGate.ALLOWED_TRANSITIONS are permitted;
anything else raises IllegalTransitionError rather than being coerced.
"""
from good_agents.models import ActionGate, ActionGateTransition
from good_agents.services.timeline import record_event


class IllegalTransitionError(Exception):
    """Raised when a requested state transition isn't in ActionGate.ALLOWED_TRANSITIONS."""


def get_or_create_gate(opportunity):
    """
    Lazily creates the gate at 'discovered' the first time it's touched —
    this is model instantiation, not a governed decision, but is still
    logged as the first ActionGateTransition row so the timeline has a
    genuine starting point.
    """
    gate, created = ActionGate.objects.get_or_create(opportunity=opportunity)
    if created:
        ActionGateTransition.objects.create(gate=gate, previous_state='', new_state='discovered', reason='Opportunity discovered.')
        record_event(opportunity, 'discovered', source_object_reference=f'good_agents.ActionGate:{gate.pk}')
    return gate


def transition(opportunity, new_state, *, actor=None, reason='', evidence_reviewed=None):
    """
    The only sanctioned way to change an ActionGate's state. Raises
    IllegalTransitionError for any transition not in ALLOWED_TRANSITIONS —
    callers must handle this, never silently coerce a state.
    """
    gate = get_or_create_gate(opportunity)
    allowed = ActionGate.ALLOWED_TRANSITIONS.get(gate.current_state, set())
    if new_state not in allowed:
        raise IllegalTransitionError(
            f'Cannot transition from {gate.current_state!r} to {new_state!r} for opportunity {opportunity.pk}. '
            f'Allowed next states: {sorted(allowed) or "(none — terminal state)"}'
        )

    previous_state = gate.current_state
    gate.current_state = new_state
    gate.save(update_fields=['current_state', 'updated_at'])

    ActionGateTransition.objects.create(
        gate=gate, previous_state=previous_state, new_state=new_state,
        actor=actor, reason=reason, evidence_reviewed=evidence_reviewed or [],
    )
    record_event(
        opportunity, 'human_reviewed', actor=actor,
        source_object_reference=f'good_agents.ActionGate:{gate.pk}',
        notes=f'{previous_state} -> {new_state}: {reason}'.strip(': '),
    )
    if new_state in ActionGate.APPROVED_STATES:
        record_event(
            opportunity, 'action_approved', actor=actor,
            source_object_reference=f'good_agents.ActionGate:{gate.pk}', notes=reason,
        )
    return gate


def can_transition(opportunity, new_state):
    gate = get_or_create_gate(opportunity)
    return new_state in ActionGate.ALLOWED_TRANSITIONS.get(gate.current_state, set())
