"""public_action_preparation/services/roles.py — Phase 16: honest human review role tracking, same discipline as outreach_readiness.services.roles."""
from public_action_preparation.models import ActionReviewRole


def record_role(opportunity, user, role, *, actor):
    if actor is None or user is None:
        raise ValueError('Recording a review role requires a real user and a real actor.')
    role_record, _ = ActionReviewRole.objects.get_or_create(opportunity=opportunity, user=user, role=role)
    return role_record


def role_summary(opportunity):
    roles = opportunity.action_review_roles.select_related('user').all()
    by_role = {}
    for record in roles:
        by_role.setdefault(record.role, []).append(record.user)

    users_seen = {}
    for record in roles:
        users_seen.setdefault(record.user_id, set()).add(record.role)
    single_reviewer_limitation = any(len(held_roles) > 1 for held_roles in users_seen.values())

    return {'by_role': by_role, 'single_reviewer_limitation': single_reviewer_limitation}
