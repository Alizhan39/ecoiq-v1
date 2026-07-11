"""
capital_guardian/services/capital_decision_bridge.py — vertical-slice PR 5:
the narrow bridge from a human-selected, ranked InterventionOption (PR 4's
Better Way comparison) into a real, governed CapitalAllocationDecision.

Reuses, never duplicates:
- capital_guardian.services.better_way.compare_interventions() for the
  authoritative current rank/scores/safety status of the selected option —
  never a client-submitted or stale value.
- waste_to_value_capital_allocation_engine.services.governance.
  create_governed_investment_case() for the actual decision persistence —
  this module never writes to CapitalAllocationDecision directly.
- waste_to_value_capital_allocation_engine.services.loss_intake.
  EVIDENCE_QUALITY_CONFIDENCE for the same real strong/medium/weak/missing
  -> 0-100 mapping already used elsewhere, rather than inventing a second one.

Never auto-approves: every decision created here begins at approval_status
='pending' — the same real, existing mechanism used everywhere else in this
app. The actual approve/reject/approve-with-conditions action is performed
by a human via the existing, already-staff-gated Django admin change form
for CapitalAllocationDecision (waste_to_value_capital_allocation_engine/
admin.py's CapitalAllocationDecisionAdmin) — this module does not invent a
second approval UI.

Safety gate: a 'blocked' option can never reach create_governed_investment_
case() at all — BlockedInterventionError is raised before anything is
touched. A 'conditional' option's unmet condition is preserved verbatim in
both CapitalAllocationDecision.conditions (a real JSONField) and the
decision narrative text.
"""
from waste_to_value_capital_allocation_engine.models import CapitalAllocationDecision
from waste_to_value_capital_allocation_engine.services.governance import create_governed_investment_case
from waste_to_value_capital_allocation_engine.services.loss_intake import EVIDENCE_QUALITY_CONFIDENCE

from capital_guardian.services.better_way import compare_interventions


class BlockedInterventionError(Exception):
    """Raised when a CapitalAllocationDecision is attempted for an
    intervention the safety gate has blocked. Nothing is created."""


class InterventionNotInComparisonError(Exception):
    """Raised when the given option doesn't belong to the given loss at
    all — an independent re-check, never trusting a client-submitted pair."""


def create_decision_from_better_way(project, loss, option):
    """
    project: the gold_intelligence.GoldProject the loss/evidence are scoped to.
    loss: the real OperationalLoss the option was created against.
    option: the human-selected InterventionOption from the Better Way ranking.

    Idempotent, and safe against accidentally reverting an already-decided
    case: if a CapitalAllocationDecision already exists for this exact
    option (create_governed_investment_case's own (intervention,
    council_case) idempotency key), it is returned UNCHANGED rather than
    regenerated — regenerating would silently reset an already-approved or
    already-rejected decision back to 'pending', which must never happen
    silently.
    """
    existing = CapitalAllocationDecision.objects.filter(intervention=option, council_case=None).first()
    if existing is not None:
        return existing

    result = compare_interventions(project, loss)

    candidate = next((c for c in result.ranked if c['option'].pk == option.pk), None)
    if candidate is None:
        blocked_entry = next((b for b in result.blocked if b['option'].pk == option.pk), None)
        if blocked_entry is not None:
            raise BlockedInterventionError(blocked_entry['reason'])
        raise InterventionNotInComparisonError(
            f'InterventionOption {option.pk} is not part of the current comparison for OperationalLoss {loss.pk}.'
        )

    safety_status = candidate['safety_status']
    safety_reason = candidate['safety_reason']
    conditions = [safety_reason] if safety_status == 'conditional' and safety_reason else []

    confidence = EVIDENCE_QUALITY_CONFIDENCE.get(loss.evidence_quality, 50)

    decision_text = (
        f'Human-selected intervention "{option.title}" (rank #{candidate["rank"]} of {len(result.ranked)}, '
        f'composite score {candidate["composite_score"]}) from The Better Way comparison for "{loss.title}" '
        f'({project.name}). Safety status: {safety_status}.'
        + (f' {safety_reason}' if safety_reason else '')
        + ' This decision begins pending — a recommendation for human review, not an approved or funded outcome.'
    )

    scores = {
        'financial_return_score': candidate['financial_return'],
        'loss_avoidance_score': candidate['loss_avoided'],
        'capital_efficiency_score': candidate['capital_efficiency'],
        'risk_score': candidate['downside_risk'],
        'maqasid_mizan_score': candidate['maqasid_mizan_score'],
        # verified_impact_score is deliberately absent — governance.py's own
        # default (0) applies. Nothing has been independently verified at
        # this stage (estimated != verified); it's only honestly populated
        # once real MRV/Verified Outcome work (a later PR) measures it.
    }

    decision = create_governed_investment_case(
        option, decision_text=decision_text, scores=scores, conditions=conditions,
        confidence=confidence, human_approval_required=True, approval_status='pending',
    )
    decision.ranking = candidate['rank']
    decision.save(update_fields=['ranking'])
    return decision
