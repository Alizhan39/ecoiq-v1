"""
public_need_discovery/services/qualification.py — Phase 14: the
discovery/actionability/outreach tri-state, kept as three separate real
booleans (never collapsed), plus Phase 19's governed promotion into
outreach_readiness. Promotion NEVER bypasses outreach_readiness's own
recipient-responsibility test or suitability review — it only pre-fills
an OutreachCandidateAssessment with what THIS layer already found, for
the SAME kind of human actor to independently re-confirm through the
SAME real PR12 functions.
"""
from django.utils import timezone

from public_need_discovery.models import ACTIONABILITY_PROCEEDABLE_STATES
from public_need_discovery.services.roles import confirmed_justifying_roles


class QualificationNotAllowedError(Exception):
    pass


def recompute_discovery_qualified(candidate):
    """
    Discovery qualification already happened once, upstream, at
    evidence_gate.evaluate_cluster time (a GoodOpportunity only exists
    because that gate returned 'qualify'/'monitor', not 'reject') — this
    just reports that real fact honestly rather than re-deciding it.
    """
    opportunity = candidate.opportunity
    qualified = not opportunity.insufficient_evidence and opportunity.status != 'rejected'
    if candidate.discovery_qualified != qualified:
        candidate.discovery_qualified = qualified
        candidate.save(update_fields=['discovery_qualified', 'updated_at'])
    return qualified


def recompute_actionability_qualified(candidate):
    qualified = candidate.actionability_state in ACTIONABILITY_PROCEEDABLE_STATES
    if candidate.actionability_qualified != qualified:
        candidate.actionability_qualified = qualified
        candidate.save(update_fields=['actionability_qualified', 'updated_at'])
    return qualified


def mark_outreach_suitable(candidate, value, *, actor):
    """
    Set only by the actual promotion action below (or reset if an
    outreach_readiness assessment is later rejected) — never inferred
    merely from actionability_qualified being true, since outreach
    suitability additionally requires PR12's own suitability review.
    """
    if actor is None:
        raise QualificationNotAllowedError('Marking outreach suitability requires a real actor.')
    candidate.outreach_suitable = value
    candidate.save(update_fields=['outreach_suitable', 'updated_at'])
    return candidate


# public_need_discovery role -> outreach_readiness RECIPIENT_ROLE_CHOICES.
# jurisdiction_authority has no outreach_readiness equivalent that alone
# justifies contact (same discipline as evidence_publisher) — mapped to
# 'source_of_information' so PR12's own justification test still applies
# correctly rather than silently upgrading it.
_ROLE_TO_OUTREACH_RECIPIENT_ROLE = {
    'evidence_publisher': 'source_of_information',
    'jurisdiction_authority': 'source_of_information',
    'responsible_authority': 'responsible_authority',
    'potential_implementer': 'potential_implementer',
    'funder': 'funder',
    'resource_provider': 'resource_provider',
    'referral_body': 'referral_body',
}


def promote_to_outreach_readiness(candidate, *, actor, organisation_role):
    """
    Phase 19 — only candidates that passed THIS layer's Actionability Gate
    may enter outreach_readiness at all. `organisation_role` must be one
    of this candidate's own human-CONFIRMED CandidateOrganisationRole rows
    (never an arbitrary/unconfirmed one) — its evidence is copied into a
    fresh outreach_readiness.OutreachCandidateAssessment, which the human
    actor must still independently walk through
    record_recipient_responsibility_test()/set_suitability_state() etc.
    This function pre-fills; it never itself sets suitability_state.
    """
    if actor is None:
        raise QualificationNotAllowedError('Promotion to outreach readiness requires a real actor.')
    if candidate.actionability_state not in ACTIONABILITY_PROCEEDABLE_STATES:
        raise QualificationNotAllowedError(
            f'Candidate is {candidate.get_actionability_state_display()!r} — only actionable/actionable_needs_review '
            f'candidates may be promoted to outreach readiness.'
        )
    if candidate.use_official_process:
        raise QualificationNotAllowedError(
            'This candidate\'s correct action is an existing official process, not EcoIQ outreach — '
            'see official_process_type/official_process_route_reference instead of promoting to outreach readiness.'
        )
    if organisation_role not in confirmed_justifying_roles(candidate):
        raise QualificationNotAllowedError('organisation_role must be one of this candidate\'s own confirmed justifying roles.')

    from outreach_readiness.services.assessment import get_or_create_assessment, record_recipient_responsibility_test
    assessment = get_or_create_assessment(candidate.opportunity)
    assessment.recipient_role = _ROLE_TO_OUTREACH_RECIPIENT_ROLE.get(organisation_role.role, 'source_of_information')
    assessment.organisation = organisation_role.organisation
    assessment.save(update_fields=['recipient_role', 'organisation'])
    record_recipient_responsibility_test(
        assessment, actor=actor, recipient_role=assessment.recipient_role, jurisdiction=candidate.jurisdiction,
        remit_confirmed=organisation_role.confirmed, remit_rationale=organisation_role.rationale,
        geographic_relevance_confirmed=candidate.jurisdiction_resolved,
        capability_evidence_reference=organisation_role.evidence_reference,
        identity_confirmed=organisation_role.confirmed,
    )
    mark_outreach_suitable(candidate, True, actor=actor)
    stamp = f'[{timezone.now():%Y-%m-%d %H:%M}] {actor} promoted this candidate to outreach_readiness (assessment {assessment.pk}) via role {organisation_role.get_role_display()} on {organisation_role.organisation}.'
    candidate.assessment_notes = f'{candidate.assessment_notes}\n\n{stamp}'.strip()
    candidate.save(update_fields=['assessment_notes', 'updated_at'])
    return assessment
