"""
partner_participation/services/staleness.py — Phase 25: nothing here
stays "current" forever. A capability with no `reconfirmation_due_at` set
is NOT treated as permanently valid — `staleness_of()` reports it
honestly as "no reconfirmation schedule set" rather than silently
assuming freshness.
"""
import datetime

from django.utils import timezone

DEFAULT_RECONFIRMATION_WINDOW_DAYS = 180


def staleness_of(edge):
    if edge.verification_state == 'expired':
        return 'expired'
    if edge.reconfirmation_due_at is None:
        return 'no_schedule_set'
    now = timezone.now()
    if edge.reconfirmation_due_at < now:
        return 'stale'
    return 'current'


def reconfirm(edge, *, actor, window_days=DEFAULT_RECONFIRMATION_WINDOW_DAYS):
    """
    A real human (organisation member or EcoIQ staff) reconfirms a
    capability is still accurate — bumps last_confirmed_at and schedules
    the next reconfirmation. Never silently extends staleness without a
    real actor.
    """
    if actor is None:
        raise ValueError('Reconfirmation requires a real actor.')
    now = timezone.now()
    edge.last_confirmed_at = now
    edge.reconfirmation_due_at = now + datetime.timedelta(days=window_days)
    edge.save(update_fields=['last_confirmed_at', 'reconfirmation_due_at', 'updated_at'])
    return edge


def sweep_expire_stale(*, grace_days=30):
    """
    Marks capabilities 'expired' once they've been stale for longer than
    `grace_days` past their reconfirmation due date — time-based, unlike
    every other function here, meant to be called periodically (mirrors
    good_agents.services.notify.sweep_funding_deadlines' own precedent).
    """
    from capability_graph.models import OrganisationCapability
    cutoff = timezone.now() - datetime.timedelta(days=grace_days)
    candidates = OrganisationCapability.objects.filter(
        reconfirmation_due_at__lt=cutoff,
    ).exclude(verification_state='expired')
    count = candidates.update(verification_state='expired')
    return count
