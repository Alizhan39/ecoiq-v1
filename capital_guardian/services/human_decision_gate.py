"""
capital_guardian/services/human_decision_gate.py — feat/human-decision-gate:
the one service responsible for every CapitalAllocationDecision review
transition. Replaces the generic Django admin field edit as the primary
workflow (admin remains available as an emergency/internal tool — see that
app's admin.py — but is no longer where a reviewer is expected to act).

Reuses, never duplicates:
- capital_guardian.services.intervention_safety_gate.classify_intervention_safety()
  to re-verify the intervention is still eligible at approval time — the
  same real safety gate used when the decision was first created
  (capital_decision_bridge.py), not a second copy of that logic.
- capital_guardian.services.capital_decision_bridge.BlockedInterventionError
  — the existing exception, raised again here rather than inventing a
  second "blocked" error type.

Every review action creates exactly one immutable
waste_to_value_capital_allocation_engine.models.DecisionReviewEvent row and,
if the decision's project can be resolved from the URL the caller already
has (never guessed), one capital_guardian.models.AuditLogEntry row — see
that model's docstring for why this one event type is written directly
rather than via the signal-based pattern the rest of the app uses.

CapitalAllocationDecision.approval_status is the only field this service
ever writes on the decision itself — conditions, scores, and every other
field are left exactly as they were when the decision was created. This is
also why "approve" doesn't take an explicit target status: it derives
'approved' vs 'approved_with_conditions' from whether decision.conditions is
already non-empty, so an approval can never accidentally clear or ignore a
condition that was already there.
"""
from dataclasses import dataclass
from typing import Optional

from django.db import transaction

from capital_guardian.services.capital_decision_bridge import BlockedInterventionError
from capital_guardian.services.intervention_safety_gate import classify_intervention_safety
from capital_guardian.services.better_way import extract_classification

# Explicit legal transition graph. Nothing outside this dict is ever
# permitted — an action targeting any other (from_status) is rejected.
# 'approved' and 'rejected' deliberately have no outgoing transitions in
# this PR: reopening a decided case is out of scope here (see PR2 report's
# "known limitations"), so they are correctly terminal for now rather than
# silently reachable from anywhere.
LEGAL_TRANSITIONS = {
    'pending': {'approved', 'approved_with_conditions', 'rejected', 'evidence_requested', 'modification_requested'},
    'evidence_requested': {'pending'},
    'modification_requested': {'pending'},
}

# action -> whether `notes` is required. Approval rationale is optional
# (product policy: a rationale-optional approve is acceptable — the decision
# text and ranking already carry the "why" from The Better Way comparison);
# reject/request_evidence/request_modification must always explain why.
NOTES_REQUIRED = {
    'approve': False,
    'reject': True,
    'request_evidence': True,
    'request_modification': True,
    'resubmit': False,
}

ACTIONS = tuple(NOTES_REQUIRED.keys())


class IllegalTransitionError(Exception):
    """Raised when the requested action is not legal from the decision's
    current approval_status — e.g. trying to 'approve' an already-approved
    or already-rejected decision, or requesting evidence on a decision
    that's already awaiting resubmission."""


class InvalidReviewActionError(Exception):
    """Raised for any action string outside the fixed ACTIONS set — never
    an arbitrary, unvalidated status string reaches the model."""


class MissingRationaleError(Exception):
    """Raised when an action that requires explanatory notes is submitted
    without any."""


@dataclass
class ReviewResult:
    event: object
    decision: object
    new_status: str


def _target_status(decision, action):
    if action == 'approve':
        return 'approved_with_conditions' if decision.conditions else 'approved'
    if action == 'reject':
        return 'rejected'
    if action == 'request_evidence':
        return 'evidence_requested'
    if action == 'request_modification':
        return 'modification_requested'
    if action == 'resubmit':
        return 'pending'
    raise InvalidReviewActionError(action)  # pragma: no cover — ACTIONS already validated by caller


def legal_actions_for(decision):
    """The subset of ACTIONS legal from this decision's current
    approval_status — used by the review page to decide which action
    buttons to render at all (never show an action the current state
    doesn't permit)."""
    allowed_targets = LEGAL_TRANSITIONS.get(decision.approval_status, set())
    return [a for a in ACTIONS if _target_status_safe(decision, a) in allowed_targets]


def _target_status_safe(decision, action):
    try:
        return _target_status(decision, action)
    except InvalidReviewActionError:
        return None


def submit_review(decision, action, actor, notes='', project=None):
    """
    decision: the CapitalAllocationDecision being reviewed.
    action: one of ACTIONS — never trusted blindly; validated here even
    though the view should already have restricted the choices offered.
    actor: the real Django User performing the review, for audit
    attribution. Never guessed; the caller must be authenticated staff.
    notes: rationale (approve/reject) or explanatory notes (request_*).
    project: the gold_intelligence.GoldProject this decision was reached
    through (from the URL, e.g. /capital-guardian/<slug>/decisions/<id>/
    review/) — used only to attribute an AuditLogEntry to the right
    project; never used to authorise the action itself (the view is
    responsible for verifying the decision actually belongs to this
    project before calling this function at all).

    Raises InvalidReviewActionError, IllegalTransitionError,
    MissingRationaleError, or BlockedInterventionError (re-verified safety
    status for 'approve' only) rather than silently no-opping — a caller
    that ignores the return value still can't cause an illegal transition.
    """
    if action not in ACTIONS:
        raise InvalidReviewActionError(action)

    if NOTES_REQUIRED[action] and not notes.strip():
        raise MissingRationaleError(f'"{action}" requires explanatory notes.')

    target_status = _target_status(decision, action)
    allowed_targets = LEGAL_TRANSITIONS.get(decision.approval_status, set())
    if target_status not in allowed_targets:
        raise IllegalTransitionError(
            f'Cannot {action!r} a decision currently {decision.approval_status!r} '
            f'(would target {target_status!r}, which is not a legal transition from here).'
        )

    if action == 'approve':
        # Re-verify eligibility now, not just at decision-creation time —
        # something about the option or its resource-purpose review could
        # have changed since. Blocked options must never be approved,
        # regardless of what the decision's own stored conditions say.
        option = decision.intervention
        loss_project = project
        classification = extract_classification(option.description)
        if loss_project is not None:
            safety = classify_intervention_safety(loss_project, option, classification=classification)
            if safety['status'] == 'blocked':
                raise BlockedInterventionError(safety['reason'])

    from waste_to_value_capital_allocation_engine.models import DecisionReviewEvent

    with transaction.atomic():
        previous_status = decision.approval_status
        event = DecisionReviewEvent.objects.create(
            decision=decision, action=action, actor=actor,
            previous_status=previous_status, new_status=target_status, notes=notes,
        )
        decision.approval_status = target_status
        decision.save(update_fields=['approval_status'])

        if project is not None:
            from capital_guardian.models import AuditLogEntry
            AuditLogEntry.objects.create(
                project=project, event_type='capital_decision',
                object_description=f'Capital Decision: {decision.intervention.title}',
                field_name='approval_status', previous_value=previous_status, new_value=target_status,
                changed_by=actor, reason=notes, approval_status=target_status,
                source_reference=f'waste_to_value_capital_allocation_engine.CapitalAllocationDecision:{decision.pk}',
            )

    return ReviewResult(event=event, decision=decision, new_status=target_status)
