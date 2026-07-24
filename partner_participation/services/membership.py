"""
partner_participation/services/membership.py — organisation claims.

A user requesting association with a real capability_graph.Organisation
NEVER gains any role automatically — not from matching the organisation's
website email domain, not from any other inference. `request_membership()`
always starts at 'claim_requested'; only `review_membership()`, called
with a real EcoIQ staff actor, can move it to 'verified_member' or
'rejected'. This is the exact same human-gate discipline as PR5's
`action_gate.transition()`/`responsible_party.confirm()`.
"""
from django.utils import timezone

from partner_participation.models import CRITICAL_MANAGEMENT_ROLES, EDITING_ROLES, OrganisationMembership


class AlreadyMemberError(Exception):
    pass


class ReviewNotAllowedError(Exception):
    pass


class NotAuthorisedError(Exception):
    pass


def request_membership(organisation, user, *, role='viewer', justification=''):
    """
    Creates a claim at 'claim_requested' — never higher. A user with an
    existing membership row for this organisation cannot request a second
    one; they must wait for the existing row's review (or contact EcoIQ if
    rejected/suspended) rather than spawning a duplicate claim.
    """
    if OrganisationMembership.objects.filter(organisation=organisation, user=user).exists():
        raise AlreadyMemberError(f'{user} already has a membership record for {organisation}.')
    return OrganisationMembership.objects.create(
        organisation=organisation, user=user, role=role, justification=justification, status='claim_requested',
    )


def review_membership(membership, *, decision, actor, notes=''):
    """
    The ONLY way a membership can reach 'verified_member' or 'rejected'.
    Requires a real staff actor — mirrors every other human-gate in this
    codebase. `decision` must be 'verified_member' or 'rejected'; anything
    else raises rather than silently no-op'ing.
    """
    if actor is None or not getattr(actor, 'is_staff', False):
        raise ReviewNotAllowedError('Membership review requires a real EcoIQ staff actor.')
    if decision not in ('verified_member', 'rejected'):
        raise ValueError(f'review_membership() decision must be verified_member or rejected, got {decision!r}.')
    membership.status = decision
    membership.reviewed_by = actor
    membership.reviewed_at = timezone.now()
    if notes:
        membership.review_notes = notes
    membership.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes', 'updated_at'])
    return membership


def suspend_membership(membership, *, actor, reason=''):
    if actor is None or not getattr(actor, 'is_staff', False):
        raise ReviewNotAllowedError('Suspension requires a real EcoIQ staff actor.')
    membership.status = 'suspended'
    membership.reviewed_by = actor
    membership.reviewed_at = timezone.now()
    if reason:
        membership.review_notes = f'{membership.review_notes}\n\nSuspended: {reason}'.strip()
    membership.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes', 'updated_at'])
    return membership


def user_role_for_organisation(organisation, user):
    """Returns the user's real, verified role for this organisation, or None if not a verified member."""
    if user is None or not user.is_authenticated:
        return None
    membership = OrganisationMembership.objects.filter(
        organisation=organisation, user=user, status='verified_member',
    ).first()
    return membership.role if membership else None


def can_edit(organisation, user):
    return user_role_for_organisation(organisation, user) in EDITING_ROLES


def can_manage_critical(organisation, user):
    return user_role_for_organisation(organisation, user) in CRITICAL_MANAGEMENT_ROLES


def can_respond_to_routing(organisation, user):
    role = user_role_for_organisation(organisation, user)
    return role in EDITING_ROLES or role == 'routing_manager'
