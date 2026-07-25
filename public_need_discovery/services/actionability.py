"""
public_need_discovery/services/actionability.py — Phase 2: the
Actionability Gate. Deterministic and explainable: every state transition
is traceable to real, inspectable criteria (evidence, jurisdiction,
confirmed justifying role, small action, sensitivity) — never an opaque
aggregate AI score (Phase 2's own explicit instruction).
"""
from django.utils import timezone

from public_need_discovery.models import ACTIONABILITY_TERMINAL_REJECTED_STATES, PilotCandidateAssessment
from public_need_discovery.services.roles import has_confirmed_justifying_role


class ActionabilityNotAllowedError(Exception):
    pass


def get_or_create_candidate(opportunity):
    candidate, _ = PilotCandidateAssessment.objects.get_or_create(opportunity=opportunity)
    return candidate


def set_actionability_state(candidate, new_state, *, actor, rationale=''):
    """The one sanctioned way to move actionability_state — always logged, never silent."""
    if actor is None:
        raise ActionabilityNotAllowedError('Setting an actionability verdict requires a real actor.')
    candidate.actionability_state = new_state
    if rationale:
        stamp = f'[{timezone.now():%Y-%m-%d %H:%M}] {actor} set actionability to {new_state}: {rationale}'
        candidate.assessment_notes = f'{candidate.assessment_notes}\n\n{stamp}'.strip()
    candidate.assessed_by = actor
    candidate.assessed_at = timezone.now()
    candidate.save(update_fields=['actionability_state', 'assessment_notes', 'assessed_by', 'assessed_at', 'updated_at'])
    return candidate


def evaluate_candidate(candidate):
    """
    Read-only evaluation against Phase 2's 8 criteria. Returns
    (recommended_state, reasons: list[str]) — a RECOMMENDATION a human
    reviewer sees and may accept via `set_actionability_state`, never an
    automatic write (Phase 24: human approval always required before
    promoting to actionable).
    """
    reasons = []
    opportunity = candidate.opportunity

    if opportunity.insufficient_evidence or not opportunity.evidence_refs:
        reasons.append('No evidence references recorded on the opportunity.')
        return 'insufficient_evidence', reasons

    if not candidate.jurisdiction_resolved or candidate.jurisdiction == 'NO_JURISDICTION':
        reasons.append('Jurisdiction has not been resolved to a real, known value.')
        return 'no_responsible_body_identified' if candidate.organisation_roles.exists() else 'potentially_actionable', reasons

    if not has_confirmed_justifying_role(candidate):
        if candidate.organisation_roles.filter(confirmed=True).exists():
            reasons.append(
                'Every confirmed organisation role is evidence_publisher/jurisdiction_authority only — '
                'a source of information alone is not a legitimate action recipient.'
            )
            return 'wrong_recipient', reasons
        reasons.append('No organisation role has been human-confirmed yet.')
        return 'no_responsible_body_identified', reasons

    if not candidate.suggested_action_type and not candidate.use_official_process:
        reasons.append('No small legitimate action or official process has been identified yet.')
        return 'no_clear_action', reasons

    if candidate.evidence_valid_but_outreach_inappropriate:
        reasons.append('Sensitivity review found the evidence valid but outreach itself inappropriate.')
        return 'sensitive_review_required', reasons

    if candidate.is_sensitive:
        reasons.append('Flagged sensitive — needs explicit human sign-off even though other criteria pass.')
        return 'actionable_needs_review', reasons

    reasons.append('Jurisdiction resolved, a confirmed justifying organisation role exists, and a small action or official process is identified.')
    return 'actionable', reasons


def blockers(candidate):
    """Phase 15/18 — explicit, human-readable blockers, never a bare boolean."""
    opportunity = candidate.opportunity
    items = []
    if opportunity.insufficient_evidence or not opportunity.evidence_refs:
        items.append({'code': 'INSUFFICIENT_EVIDENCE', 'detail': 'No evidence references recorded.'})
    if not candidate.jurisdiction_resolved:
        items.append({'code': 'NO_JURISDICTION', 'detail': 'Jurisdiction not resolved from any real source.'})
    if not has_confirmed_justifying_role(candidate):
        items.append({'code': 'NO_RESPONSIBLE_BODY_CONFIRMED', 'detail': 'No human-confirmed responsible_authority/potential_implementer/funder/resource_provider/referral_body role.'})
    if not candidate.suggested_action_type and not candidate.use_official_process:
        items.append({'code': 'NO_CLEAR_ACTION', 'detail': 'No small legitimate action or official process identified.'})
    if candidate.evidence_valid_but_outreach_inappropriate:
        items.append({'code': 'SENSITIVE_OUTREACH_INAPPROPRIATE', 'detail': 'Evidence valid; outreach blocked by sensitivity review.'})
    if candidate.actionability_state in ACTIONABILITY_TERMINAL_REJECTED_STATES:
        items.append({'code': 'REJECTED', 'detail': f'Terminal state: {candidate.get_actionability_state_display()}.'})
    return items
