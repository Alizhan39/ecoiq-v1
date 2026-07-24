"""
partner_participation/services/share_package.py — PR9 Phase 11: the
structured content a human reviews before approving a share. Every field
is read from already-persisted rows — nothing here infers or invents a
claim. "Known unknowns" is a real, honest field: it explicitly lists what
ISN'T known, rather than silently omitting it.
"""
from good_agents.models import WorldSignal


def build_share_package(candidate):
    opportunity = candidate.opportunity
    lead_signal = WorldSignal.objects.filter(title__in=opportunity.detected_signals).first()

    known_unknowns = []
    if opportunity.insufficient_evidence:
        known_unknowns.append('This opportunity is flagged as having insufficient evidence.')
    if not opportunity.evidence_refs:
        known_unknowns.append('No evidence references are recorded for this opportunity.')
    if not lead_signal:
        known_unknowns.append('No originating signal could be resolved for this opportunity.')

    return {
        'opportunity_title': opportunity.title,
        'problem_statement': opportunity.problem_statement,
        'source_evidence': list(opportunity.evidence_refs) or [],
        'originating_signal': lead_signal.title if lead_signal else None,
        'originating_publisher': lead_signal.publisher if lead_signal else '',
        'location': opportunity.region or (opportunity.geography.name if opportunity.geography_id else ''),
        'relevant_principles': [a.agent.name for a in opportunity.agent_activations.select_related('agent').all()],
        'why_matched': list(candidate.match_reasons),
        'requested_next_step': (
            'Please review and let us know if this is of interest, and whether you need more information '
            'before deciding.'
        ),
        'known_unknowns': known_unknowns,
        # Never claims confidentiality it hasn't actually established — this
        # repo has no confidentiality-classification mechanism yet, so this
        # is reported honestly rather than invented.
        'confidentiality_status': 'Not classified — treat as containing only information already public in the originating signal.',
    }


def render_share_message(candidate):
    package = build_share_package(candidate)
    subject = f'EcoIQ — potential opportunity match: {package["opportunity_title"]}'
    lines = [
        f'Organisation: {candidate.organisation.name}',
        f'Opportunity: {package["opportunity_title"]}',
        '',
        package['problem_statement'],
        '',
        f'Location: {package["location"] or "Not recorded"}',
        f'Relevant principles: {", ".join(package["relevant_principles"]) or "None recorded"}',
        '',
        'Why this may match your organisation:',
        *[f'- {reason}' for reason in package['why_matched']],
        '',
        package['requested_next_step'],
    ]
    if package['known_unknowns']:
        lines += ['', 'What we do not yet know:', *[f'- {u}' for u in package['known_unknowns']]]
    lines += ['', f'Confidentiality: {package["confidentiality_status"]}']
    return subject, '\n'.join(lines)
