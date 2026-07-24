"""
collaboration_rooms/services/summary.py — deterministic collaboration
summary (Phase 28). Pure aggregation over real rows — "No unsupported
LLM narrative required" per the brief's own instruction. This is what
every room detail view/API renders by default; services/ai_assist.py is
a genuinely optional richer layer on top, never a replacement.
"""
def collaboration_summary(room):
    open_questions = room.information_requests.exclude(status__in=['answered', 'closed'])
    missing_evidence = room.information_requests.filter(status='needs_evidence')
    latest_event = room.activity_events.order_by('-created_at').first()
    proposed = room.next_step_proposals.filter(status__in=['proposed', 'accepted']).order_by('-created_at').first()

    consent_state = None
    if proposed is not None:
        consent_state = [
            {
                'party': c.organisation.name if c.organisation_id else 'EcoIQ',
                'status': c.get_status_display(),
            }
            for c in proposed.consents.all()
        ]

    return {
        'opportunity_title': room.opportunity.title,
        'organisation': room.anchor_organisation.name,
        'status': room.get_status_display(),
        'participants': [
            {'user': str(p.user), 'organisation': p.organisation.name if p.organisation_id else 'EcoIQ', 'role': p.get_role_display()}
            for p in room.participants.filter(revoked_at__isnull=True)
        ],
        'evidence_shared_count': room.evidence_items.count(),
        'open_questions': [q.question_text for q in open_questions],
        'missing_evidence': [q.question_text for q in missing_evidence],
        'proposed_next_step': proposed.get_proposal_type_display() if proposed else None,
        'consent_state': consent_state,
        'latest_activity': f'{latest_event.get_event_type_display()} ({latest_event.created_at:%Y-%m-%d %H:%M})' if latest_event else 'No activity yet.',
    }
