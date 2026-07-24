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


# --- PR5 Phase 26 — Impact Action Network events -----------------------
# Same dedup discipline as above (source_model + source_object_id + reason),
# generalised to whichever action-network model the event is about instead
# of always the opportunity. Every function here fires on a real mutation
# already made by a governed service call — never a synthetic/periodic
# "just in case" ping, except the funding-deadline sweep below, which is
# inherently time-based rather than event-based.

def _already_notified_for(instance, reason):
    return AdminNotification.objects.filter(
        source_model=f'{instance._meta.app_label}.{instance._meta.model_name}',
        source_object_id=str(instance.pk),
        metadata__reason=reason,
    ).exists()


def _notify_instance_once(instance, reason, *, title, message, priority='normal', extra_metadata=None):
    if _already_notified_for(instance, reason):
        return None
    metadata = {'reason': reason}
    if extra_metadata:
        metadata.update(extra_metadata)
    return create_notification(
        title, source_type='good_agents_opportunity', message=message, instance=instance,
        priority=priority, metadata=metadata,
    )


def notify_zero_capital_pathway_ready(pathway):
    return _notify_instance_once(
        pathway, 'zero_capital_pathway_ready',
        title=f'Zero-capital action ready: {pathway.opportunity.title}',
        message=f'{pathway.get_pathway_type_display()} pathway needs no capital — ready to move forward.',
    )


def notify_connection_candidate_ready(candidate):
    need = candidate.resource_match.need
    return _notify_instance_once(
        candidate, 'connection_ready_for_introduction',
        title=f'Resource match ready: {need.title}',
        message=f'{need.title} <-> {candidate.resource_match.resource.title} is ready for a human-approved introduction.',
    )


def notify_outreach_awaiting_approval(draft):
    return _notify_instance_once(
        draft, 'outreach_awaiting_approval',
        title=f'Outreach draft awaiting approval: {draft.subject}',
        message=f'A {draft.get_draft_type_display()} draft is ready for human review before it can be sent.',
    )


def notify_outreach_reply_received(draft):
    return _notify_instance_once(
        draft, 'outreach_reply_received',
        title=f'Reply received: {draft.subject}',
        message='A reply was recorded against this outreach draft.',
        priority='high',
    )


def notify_project_candidate_ready(candidate):
    return _notify_instance_once(
        candidate, 'project_candidate_ready',
        title=f'Project candidate ready for review: {candidate.opportunity.title}',
        message=(candidate.rationale or 'A project candidate has been proposed and needs human approval.')[:300],
    )


def notify_funding_deadline_approaching(funding_action, *, days_threshold=14):
    from django.utils import timezone
    if not funding_action.deadline:
        return None
    days_left = (funding_action.deadline - timezone.now().date()).days
    if days_left < 0 or days_left > days_threshold:
        return None
    return _notify_instance_once(
        funding_action, 'funding_deadline_approaching',
        title=f'Funding deadline approaching: {funding_action.funding_match.opportunity.title}',
        message=f'{days_left} day(s) left until the funding deadline.',
        priority='high',
        extra_metadata={'days_left': days_left},
    )


def sweep_funding_deadlines(*, days_threshold=14):
    """
    Time-based check, unlike every other function in this module —
    "approaching" depends on the passage of time, not a discrete mutation,
    so this is meant to be called periodically (e.g. from
    run_good_while_you_sleep) rather than from a service call site.
    """
    from good_agents.models import FundingAction
    candidates = (
        FundingAction.objects.exclude(status__in=['rejected', 'expired', 'awarded'])
        .exclude(deadline=None).select_related('funding_match__opportunity')
    )
    return [n for n in (notify_funding_deadline_approaching(a, days_threshold=days_threshold) for a in candidates) if n]


def notify_outcome_measured(opportunity):
    return _notify_instance_once(
        opportunity, 'outcome_measured',
        title=f'Outcome measured, verification required: {opportunity.title}',
        message='Real after-data has been recorded against this opportunity — not yet independently verified.',
    )


def notify_verified_impact(opportunity):
    return _notify_instance_once(
        opportunity, 'verified_impact_achieved',
        title=f'Verified impact achieved: {opportunity.title}',
        message='This opportunity now has an independently verified real-world outcome.',
        priority='high',
    )
