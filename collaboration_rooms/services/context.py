"""
collaboration_rooms/services/context.py — the read-only opportunity
context package every room begins with (Phase 5). Pure aggregation over
already-persisted rows; nothing here infers or invents a fact.
"""
from good_agents.models import ActionPathway, WorldSignal


def build_context_package(room):
    candidate = room.routing_candidate
    opportunity = candidate.opportunity
    lead_signals = list(WorldSignal.objects.filter(title__in=opportunity.detected_signals))
    pathways = list(ActionPathway.objects.filter(opportunity=opportunity))

    known_unknowns = []
    if opportunity.insufficient_evidence:
        known_unknowns.append('This opportunity is flagged as having insufficient evidence.')
    if not opportunity.evidence_refs:
        known_unknowns.append('No evidence references are recorded for this opportunity.')
    if not lead_signals:
        known_unknowns.append('No originating signal could be resolved for this opportunity.')

    action_gate = getattr(opportunity, 'action_gate', None)

    return {
        'opportunity': opportunity,
        'problem_statement': opportunity.problem_statement,
        'signals': lead_signals,
        'evidence_refs': list(opportunity.evidence_refs) or [],
        'relevant_principles': [a.agent.name for a in opportunity.agent_activations.select_related('agent').all()],
        'human_review_decision': action_gate.get_current_state_display() if action_gate else 'Not yet reviewed',
        'action_pathways': pathways,
        'why_matched': list(candidate.match_reasons),
        'known_unknowns': known_unknowns,
        'current_routing_status': candidate.get_status_display(),
        'organisation': candidate.organisation,
    }
