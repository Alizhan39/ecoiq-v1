"""
public_action_preparation/services/action_type.py — Phase 2: the action
type decision. `recommend_action_type()` is a pure, deterministic READ
over PR13's own real findings (`public_need_discovery.
PilotCandidateAssessment`, `CandidateOrganisationRole`) — it never
recomputes actionability, jurisdiction, or responsible-body evidence,
only reads what PR13 already decided. `record_action_type_decision()` is
the only way to make a choice real, and always requires a human actor —
never auto-selected from the recommendation.

Do not default to email: `prepare_outreach` is recommended only when no
official process exists AND no narrower type (clarification/referral/
data request/funding surface/connection) fits better.
"""
from django.utils import timezone

from public_action_preparation.models import (
    ACTION_TYPES_REQUIRING_REAL_BENEFICIARY, ActionTypeDecision,
)
from public_need_discovery.services.roles import confirmed_justifying_roles


class ActionTypeNotAllowedError(Exception):
    pass


def get_or_create_decision(opportunity):
    decision, _ = ActionTypeDecision.objects.get_or_create(opportunity=opportunity)
    return decision


def recommend_action_type(opportunity):
    """
    Returns (recommended_type, reasons). Reads PR13's
    PilotCandidateAssessment — never available/actionable until that
    layer already found it so.
    """
    candidate = getattr(opportunity, 'pilot_candidate_assessment', None)
    if candidate is None or candidate.actionability_state not in ('actionable', 'actionable_needs_review'):
        return 'no_action', ['This opportunity has not yet been found actionable by public_need_discovery.']

    reasons = []
    if candidate.use_official_process:
        process_type = candidate.official_process_type
        if process_type == 'consultation_submission':
            reasons.append('public_need_discovery marked this candidate as routed to an existing consultation.')
            return 'submit_consultation_response', reasons
        if process_type == 'grant_application':
            reasons.append('public_need_discovery marked this candidate as routed to an existing grant application.')
            return 'surface_funding_route', reasons
        if process_type == 'data_request':
            reasons.append('public_need_discovery marked this candidate as routed to an existing data request process.')
            return 'request_public_data', reasons
        reasons.append(f'public_need_discovery marked this candidate as routed to an existing official process ({candidate.get_official_process_type_display()}).')
        return 'use_official_public_process', reasons

    justifying_roles = list(confirmed_justifying_roles(candidate))
    if not justifying_roles:
        reasons.append('No confirmed justifying organisation role — cannot recommend an action type yet.')
        return 'no_action', reasons

    roles_held = {r.role for r in justifying_roles}
    if 'referral_body' in roles_held:
        reasons.append(
            'A referral_body role is confirmed, but a referral must never be made without a real, evidenced '
            'beneficiary — record has_real_beneficiary explicitly before selecting refer_to_existing_service; '
            'otherwise request_programme_clarification is the correct, smaller action.'
        )
        return 'request_programme_clarification', reasons
    if 'funder' in roles_held:
        reasons.append('A funder role is confirmed — surfacing the real funding route is the smallest useful action.')
        return 'surface_funding_route', reasons
    if 'resource_provider' in roles_held:
        reasons.append('A resource_provider role is confirmed — a zero-capital connection proposal is the smallest useful action.')
        return 'propose_zero_capital_connection', reasons
    if 'potential_implementer' in roles_held or 'responsible_authority' in roles_held:
        reasons.append('A responsible_authority/potential_implementer role is confirmed with no official process — outreach via outreach_readiness is the correct path.')
        return 'prepare_outreach', reasons

    reasons.append('A confirmed role exists but does not map to a specific narrower action type.')
    return 'prepare_outreach', reasons


def record_action_type_decision(opportunity, action_type, *, actor, rationale='',
                                 has_real_beneficiary=False, beneficiary_basis_notes=''):
    """
    The only sanctioned way to set a real action type. Structurally
    blocks `refer_to_existing_service` without `has_real_beneficiary`
    (Phase 13's own explicit fuel-poverty rule) — never bypassable by
    setting the flag without real notes explaining the basis.
    """
    if actor is None:
        raise ActionTypeNotAllowedError('Recording an action type decision requires a real actor.')
    if action_type in ACTION_TYPES_REQUIRING_REAL_BENEFICIARY and not (has_real_beneficiary and beneficiary_basis_notes):
        raise ActionTypeNotAllowedError(
            'refer_to_existing_service requires has_real_beneficiary=True with a real beneficiary_basis_notes '
            'explanation — a real public need is not, by itself, a real beneficiary. Consider '
            'request_programme_clarification or surface_funding_route instead.'
        )
    decision = get_or_create_decision(opportunity)
    decision.action_type = action_type
    decision.rationale = rationale
    decision.has_real_beneficiary = has_real_beneficiary
    decision.beneficiary_basis_notes = beneficiary_basis_notes
    decision.decided_by = actor
    decision.decided_at = timezone.now()
    decision.save()
    return decision
