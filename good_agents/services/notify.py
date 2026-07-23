"""
good_agents/services/notify.py — reuses the existing
`notifications.AdminNotification` infrastructure (PR4 Phase 13). No second
notification system: every call here goes through
`notifications.models.create_notification`, which already never raises.

Only meaningful events create a notification — never one per raw signal.
Each notification is deduplicated on (source_object_id, reason) so a
re-run of the same discovery run, or the same opportunity being
re-evaluated later, never spams a second identical notification.
"""
from notifications.models import AdminNotification, create_notification

STRONG_MATCH_CONFIDENCE_THRESHOLD = 70.0
ZERO_CAPITAL_QUALITY_CONFIDENCE_THRESHOLD = 55.0


def _already_notified(opportunity, reason):
    return AdminNotification.objects.filter(
        source_type='good_agents_opportunity',
        source_model='good_agents.goodopportunity',
        source_object_id=str(opportunity.pk),
        metadata__reason=reason,
    ).exists()


def _notify_once(opportunity, reason, *, title, message, priority='normal'):
    if _already_notified(opportunity, reason):
        return None
    return create_notification(
        title, source_type='good_agents_opportunity', message=message, instance=opportunity,
        priority=priority, metadata={'reason': reason, 'opportunity_id': opportunity.pk},
    )


def notify_for_opportunity(opportunity, prioritisation_result):
    """Call once per opportunity per discovery run — checks all trigger conditions, dedups each independently."""
    created = []

    if 'URGENT' in prioritisation_result.labels:
        n = _notify_once(
            opportunity, 'urgent_public_need',
            title=f'Urgent: {opportunity.title}',
            message=f'Urgency {opportunity.urgency:.0f}/100. {opportunity.problem_statement[:200]}',
            priority='urgent',
        )
        if n:
            created.append(n)

    if opportunity.status == 'qualified' and prioritisation_result.dimensions.get('adjusted_confidence', 0) >= STRONG_MATCH_CONFIDENCE_THRESHOLD:
        n = _notify_once(
            opportunity, 'high_priority_qualified',
            title=f'Qualified opportunity: {opportunity.title}',
            message=f'Qualified with {prioritisation_result.dimensions["adjusted_confidence"]:.0f}% confidence.',
            priority='high',
        )
        if n:
            created.append(n)

    if opportunity.zero_capital_possible and opportunity.confidence >= ZERO_CAPITAL_QUALITY_CONFIDENCE_THRESHOLD:
        n = _notify_once(
            opportunity, 'zero_capital_action_available',
            title=f'Zero-capital action available: {opportunity.title}',
            message='A zero-capital next step (connect/introduce/identify existing resource) is ready for review.',
            priority='normal',
        )
        if n:
            created.append(n)

    red_team_review = getattr(opportunity, 'red_team_review', None)
    if red_team_review is not None and not red_team_review.cleared and red_team_review.contradicting_evidence:
        n = _notify_once(
            opportunity, 'material_contradiction',
            title=f'Contradiction flagged: {opportunity.title}',
            message=red_team_review.contradicting_evidence[:300],
            priority='high',
        )
        if n:
            created.append(n)

    return created


def notify_for_strong_resource_match(resource_match):
    if resource_match.confidence < STRONG_MATCH_CONFIDENCE_THRESHOLD:
        return None
    need = resource_match.need
    if AdminNotification.objects.filter(
        source_type='good_agents_opportunity', source_model='good_agents.resourcematch',
        source_object_id=str(resource_match.pk),
    ).exists():
        return None
    return create_notification(
        f'Strong resource match: {need.title} <-> {resource_match.resource.title}',
        source_type='good_agents_opportunity', message=resource_match.match_reason[:300],
        instance=resource_match, priority='normal',
        metadata={'reason': 'strong_resource_match', 'confidence': resource_match.confidence},
    )
