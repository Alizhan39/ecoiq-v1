"""
global_research/services/permissions.py — mission-level visibility.

Per docs/adr/ADR-global-research-engine.md decision 12: this platform has
no multi-tenant concept anywhere (confirmed in the existing-system audit),
so "tenant isolation" here means per-user mission visibility, modeled on
`legacy_safe.services.permissions.can_access()`'s three-input deterministic
shape — re-checked per item, never trusted once from a list view's own filtering.
"""


def can_view_mission(mission, user):
    """A pure, deterministic check — never delegated to an LLM. Staff can
    view every mission (matching this platform's existing @staff_member_required
    convention); a non-staff user can only view a mission they created or
    approved. Anonymous users can never view a mission."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if user.is_staff:
        return True
    return mission.created_by_id == user.pk or mission.approved_by_id == user.pk


def can_manage_mission(mission, user):
    """Stricter than can_view_mission — required for approval-type actions
    (approve requirements, shortlist, approve a document draft, promote).
    Only staff, in this single-tenant platform, matching every other
    approval gate in the repo (all staff-gated, none role-scoped further)."""
    return bool(user and getattr(user, 'is_authenticated', False) and user.is_staff)
