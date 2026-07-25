"""
public_action_preparation/services/evidence_pack.py — Phase 6-7: the
canonical evidence pack. A pure READ composition over already-persisted
rows — good_agents.WorldSignal, GoodOpportunity, public_need_discovery's
PilotCandidateAssessment/CandidateOrganisationRole, and
good_agents.services.pilot_launchpad.principle_relevance() (reused, not
reimplemented — the same real per-principle activation records PR6
already produces). Never invents a fact, a count, or a date.
"""
from good_agents.models import WorldSignal
from good_agents.services.pilot_launchpad import principle_relevance
from public_need_discovery.services.actionability import get_or_create_candidate
from public_need_discovery.services.roles import confirmed_justifying_roles


def build_evidence_pack(opportunity):
    candidate = get_or_create_candidate(opportunity)
    lead_signal = WorldSignal.objects.filter(title__in=opportunity.detected_signals).first()
    all_signals = list(WorldSignal.objects.filter(title__in=opportunity.detected_signals))
    roles = list(candidate.organisation_roles.select_related('organisation').all())

    return {
        'opportunity': opportunity,
        'candidate': candidate,
        'source_records': [
            {
                'title': s.title, 'publisher': s.publisher, 'source_url': s.source_url,
                'published_at': s.published_at, 'excerpt': s.source_excerpt, 'classification': s.get_content_classification_display(),
            }
            for s in all_signals
        ],
        'lead_signal': lead_signal,
        'jurisdiction': candidate.jurisdiction,
        'jurisdiction_resolved': candidate.jurisdiction_resolved,
        'jurisdiction_notes': candidate.jurisdiction_resolution_notes,
        'organisation_roles': roles,
        'confirmed_justifying_roles': list(confirmed_justifying_roles(candidate)),
        'programme_process_evidence': candidate.official_process_route_reference,
        'relevant_principles': principle_relevance(opportunity),
        'conflicting_evidence': 'None recorded.' if not opportunity.risk else opportunity.risk,
        'missing_evidence': candidate.what_ecoiq_does_not_know or 'Not yet recorded.',
        'evidence_refs': opportunity.evidence_refs,
        'freshest_publication': max((s.published_at for s in all_signals if s.published_at), default=None),
    }
