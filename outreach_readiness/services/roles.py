"""outreach_readiness/services/roles.py — Phase 16: honest human review role tracking."""
from outreach_readiness.models import OutreachReviewRole


def record_role(assessment, user, role, *, actor):
    """Records that `user` held `role` on this assessment. `actor` must be a real user (never system/AI)."""
    if actor is None or user is None:
        raise ValueError('Recording a review role requires a real user and a real actor.')
    role_record, _ = OutreachReviewRole.objects.get_or_create(assessment=assessment, user=user, role=role)
    return role_record


def role_summary(assessment):
    """Returns {role: [users]} plus whether any single person holds more than one role (Phase 16's disclosure requirement)."""
    roles = assessment.review_roles.select_related('user').all()
    by_role = {}
    for record in roles:
        by_role.setdefault(record.role, []).append(record.user)

    users_seen = {}
    for record in roles:
        users_seen.setdefault(record.user_id, set()).add(record.role)
    single_reviewer_limitation = any(len(held_roles) > 1 for held_roles in users_seen.values())

    return {'by_role': by_role, 'single_reviewer_limitation': single_reviewer_limitation}
