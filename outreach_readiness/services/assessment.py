"""
outreach_readiness/services/assessment.py — Phase 1-4, 6, 7, 13: candidate
suitability review and the recipient responsibility test. Every write here
requires a real actor; nothing here ever infers suitability from a single
aggregate score (Phase 1's own explicit instruction).
"""
from django.utils import timezone

from outreach_readiness.models import (
    ROLES_THAT_JUSTIFY_ACTION_OUTREACH, SUITABILITY_TERMINAL_REJECTED_STATES, OutreachCandidateAssessment,
)


class AssessmentNotAllowedError(Exception):
    pass


def get_or_create_assessment(opportunity):
    assessment, _ = OutreachCandidateAssessment.objects.get_or_create(opportunity=opportunity)
    return assessment


def record_suitability_review(assessment, *, actor, answers, notes=''):
    """
    Records the real Phase 1 review questions (each True/False/None —
    None means genuinely not yet assessed, never defaulted to a pass).
    Does NOT itself set `suitability_state` — that is a separate, explicit
    human judgement call via `set_suitability_state()`, so a reviewer can
    never accidentally promote a candidate just by filling in fields.
    """
    if actor is None:
        raise AssessmentNotAllowedError('Suitability review requires a real actor.')
    fields = [
        'evidence_credible', 'response_genuinely_useful', 'within_recipient_remit', 'route_available',
        'ask_small_and_proportionate', 'plausibly_answerable', 'plausible_next_governed_step',
        'risk_of_appearing_inappropriate', 'more_value_than_public_info_alone',
    ]
    for field in fields:
        if field in answers:
            setattr(assessment, field, answers[field])
    if notes:
        assessment.assessment_notes = notes
    assessment.assessed_by = actor
    assessment.assessed_at = timezone.now()
    assessment.save()
    return assessment


def set_suitability_state(assessment, new_state, *, actor, rationale=''):
    """The one sanctioned way to move suitability_state — always logged via assessment_notes, never silent."""
    if actor is None:
        raise AssessmentNotAllowedError('Setting a suitability verdict requires a real actor.')
    assessment.suitability_state = new_state
    if rationale:
        stamp = f'[{timezone.now():%Y-%m-%d %H:%M}] {actor} set suitability to {new_state}: {rationale}'
        assessment.assessment_notes = f'{assessment.assessment_notes}\n\n{stamp}'.strip()
    assessment.assessed_by = actor
    assessment.assessed_at = timezone.now()
    assessment.save()
    return assessment


def record_recipient_responsibility_test(assessment, *, actor, recipient_role, jurisdiction='',
                                          remit_confirmed=False, remit_rationale='',
                                          geographic_relevance_confirmed=False,
                                          capability_evidence_reference='', limitations='', identity_confirmed=False):
    """
    Phase 4 — the test that stops an evidence PUBLISHER being treated as
    an action RECIPIENT merely because its feed produced the signal
    (Phase 2's key acceptance test). Every field here is a real claim the
    caller must have actually checked, not inferred from the
    organisation's name or sector.
    """
    if actor is None:
        raise AssessmentNotAllowedError('The recipient responsibility test requires a real actor.')
    assessment.recipient_role = recipient_role
    assessment.jurisdiction = jurisdiction
    assessment.identity_confirmed = identity_confirmed
    assessment.remit_confirmed_for_this_issue = remit_confirmed
    assessment.remit_rationale = remit_rationale
    assessment.geographic_relevance_confirmed = geographic_relevance_confirmed
    assessment.capability_evidence_reference = capability_evidence_reference
    assessment.limitations = limitations
    assessment.assessed_by = actor
    assessment.assessed_at = timezone.now()
    assessment.save()

    # Never silently accept a source-only role as action-worthy — this is
    # the exact mechanism that makes Phase 2's acceptance test structural
    # rather than a matter of a reviewer remembering to check.
    if recipient_role not in ROLES_THAT_JUSTIFY_ACTION_OUTREACH and assessment.suitability_state not in SUITABILITY_TERMINAL_REJECTED_STATES:
        set_suitability_state(
            assessment, 'wrong_organisation', actor=actor,
            rationale=(
                f'Recipient role is {assessment.get_recipient_role_display()!r} — a source of information alone '
                f'is not a legitimate outreach recipient for a request for action.'
            ),
        )
    return assessment


def record_sensitivity_review(assessment, *, actor, categories, notes='', outreach_inappropriate=False):
    """Phase 13 — sensitivity gate. Marking a case sensitive never itself blocks it; only `outreach_inappropriate` does."""
    if actor is None:
        raise AssessmentNotAllowedError('Sensitivity review requires a real actor.')
    assessment.is_sensitive = bool(categories)
    assessment.sensitivity_categories = categories
    assessment.sensitivity_notes = notes
    assessment.evidence_valid_but_outreach_inappropriate = outreach_inappropriate
    assessment.assessed_by = actor
    assessment.assessed_at = timezone.now()
    assessment.save()
    if outreach_inappropriate and assessment.suitability_state not in SUITABILITY_TERMINAL_REJECTED_STATES:
        set_suitability_state(
            assessment, 'too_sensitive', actor=actor,
            rationale=f'Evidence remains valid; outreach itself is inappropriate. Categories: {", ".join(categories)}.',
        )
    return assessment


def record_minimum_viable_ask(assessment, *, actor, ask, value_offered=''):
    """Phase 6/7 — the one clear request, plus what EcoIQ offers in return."""
    if actor is None:
        raise AssessmentNotAllowedError('Recording the ask requires a real actor.')
    assessment.minimum_viable_ask = ask
    assessment.value_offered_to_recipient = value_offered
    assessment.assessed_by = actor
    assessment.assessed_at = timezone.now()
    assessment.save()
    return assessment
