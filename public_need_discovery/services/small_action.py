"""
public_need_discovery/services/small_action.py — Phases 9-10: the smallest
legitimate next action, and whether an existing official public process
should be preferred over EcoIQ outreach. Both are human-recorded decisions
(never auto-selected from a score) — this module only offers a
deterministic SUGGESTION a reviewer can accept, edit, or reject.
"""
from django.utils import timezone

from public_need_discovery.models import PilotCandidateAssessment


class SmallActionNotAllowedError(Exception):
    pass


def record_small_action(candidate, *, actor, action_type, description):
    if actor is None:
        raise SmallActionNotAllowedError('Recording the small action requires a real actor.')
    if not description:
        raise SmallActionNotAllowedError('A small action needs a real description — never a generic "solve this problem" ask.')
    candidate.suggested_action_type = action_type
    candidate.suggested_action_description = description
    candidate.assessed_by = actor
    candidate.assessed_at = timezone.now()
    candidate.save(update_fields=['suggested_action_type', 'suggested_action_description', 'assessed_by', 'assessed_at', 'updated_at'])
    return candidate


def record_official_process(candidate, *, actor, process_type, route_reference, use_official_process=True):
    """
    Phase 10 — when the correct action is already an official process
    (consultation submission, grant application, incident report, ...),
    prefer routing the user there over drafting unsolicited outreach.
    """
    if actor is None:
        raise SmallActionNotAllowedError('Recording the official process requires a real actor.')
    candidate.use_official_process = use_official_process
    candidate.official_process_type = process_type
    candidate.official_process_route_reference = route_reference
    candidate.assessed_by = actor
    candidate.assessed_at = timezone.now()
    candidate.save(update_fields=[
        'use_official_process', 'official_process_type', 'official_process_route_reference',
        'assessed_by', 'assessed_at', 'updated_at',
    ])
    return candidate


# Deterministic actionability_class -> suggested action type, used only as
# a starting recommendation for a human reviewer (Phase 9's own examples).
_CLASS_TO_ACTION_TYPE = {
    'public_consultation': 'submit_evidence_to_consultation',
    'funding_available': 'surface_matching_grant',
    'policy_implementation_gap': 'clarify_programme_eligibility',
    'data_request_opportunity': 'request_missing_dataset',
    'resource_available': 'connect_resource_to_need',
    'regulatory_or_compliance_notice': 'notify_data_inconsistency',
    'service_gap': 'refer_to_existing_programme',
    'community_support_need': 'refer_to_existing_programme',
}
_CLASS_TO_PROCESS_TYPE = {
    'public_consultation': 'consultation_submission',
    'funding_available': 'grant_application',
    'data_request_opportunity': 'data_request',
    'regulatory_or_compliance_notice': 'incident_report',
}


def suggest_action(candidate):
    """
    Read-only suggestion — (action_type, process_type_if_official) — a
    human still calls record_small_action/record_official_process to make
    it real. Returns (None, None) when the candidate's actionability_class
    has no known real mapping, rather than defaulting to 'other'.
    """
    action_type = _CLASS_TO_ACTION_TYPE.get(candidate.actionability_class)
    process_type = _CLASS_TO_PROCESS_TYPE.get(candidate.actionability_class)
    return action_type, process_type
