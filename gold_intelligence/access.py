"""Project permissions shared by retrieval, execution and result visibility."""
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.db.models import Q

from gold_intelligence.models import GoldProject, ProjectMembership

READ = 'read'
ANALYSE = 'analyse'
SHARE = 'share'
APPROVE = 'approve'
ROLE_PERMISSIONS = {
    ProjectMembership.Role.VIEWER: frozenset({READ}),
    ProjectMembership.Role.ANALYST: frozenset({READ, ANALYSE}),
    ProjectMembership.Role.REVIEWER: frozenset({READ, APPROVE}),
    ProjectMembership.Role.MANAGER: frozenset({READ, ANALYSE, SHARE, APPROVE}),
}


def is_active_user(user):
    return bool(user and user.is_authenticated and user.is_active)


def projects_for(user, permission=READ):
    if permission not in {READ, ANALYSE, SHARE, APPROVE} or not is_active_user(user):
        return GoldProject.objects.none()
    if user.is_staff:
        return GoldProject.objects.all()
    roles = [role for role, permissions in ROLE_PERMISSIONS.items() if permission in permissions]
    return GoldProject.objects.filter(memberships__user=user, memberships__is_active=True, memberships__role__in=roles)


def can(user, project, permission=READ):
    return bool(project is not None and project.pk is not None
                and projects_for(user, permission).filter(pk=project.pk).exists())


def require(user, project, permission):
    if not can(user, project, permission):
        raise PermissionDenied('This action requires an active project role.')


def resolve_context(requesting_user_id=None, project_id=None, *, permission=ANALYSE):
    """Reload grants at execution time. IDs must come from trusted server code.

    A fully absent context preserves legacy, memory-free execution. Partial,
    deleted, malformed or revoked context must never fall back to that path.
    """
    if requesting_user_id is None and project_id is None:
        return None, None
    from django.contrib.auth import get_user_model
    try:
        user = get_user_model().objects.filter(pk=requesting_user_id, is_active=True).first()
        project = GoldProject.objects.filter(pk=project_id).first()
    except (ValueError, TypeError, OverflowError):
        raise PermissionDenied('Invalid project context.') from None
    require(user, project, permission)
    return user, project


def visible_results(queryset, user):
    """Project results require a current grant; preserve unscoped legacy reads.

    Project FKs use PROTECT so deleting a project cannot turn private results
    into unscoped records. Decision Studio applies its ownership rule as well.
    """
    return queryset.filter(Q(project__isnull=True) | Q(project__in=projects_for(user)))


def project_permission_required(permission):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            from django.contrib.auth.views import redirect_to_login
            from django.shortcuts import get_object_or_404
            if not is_active_user(request.user):
                return redirect_to_login(request.get_full_path(), '/login/')
            project = get_object_or_404(GoldProject, slug=kwargs.get('slug'))
            require(request.user, project, permission)
            return view(request, *args, **kwargs)
        return wrapped
    return decorate
