"""
partner_participation/permissions.py — the first non-EcoIQ-staff-facing
permission gate in this lineage (every prior good_agents/capability_graph
view was `@staff_member_required`). A real, authenticated user only sees
an organisation's Partner Portal if they hold a `verified_member`
OrganisationMembership row for it — never inferred from session state,
email domain, or organisation name alone.
"""
import functools

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404

from capability_graph.models import Organisation
from partner_participation.models import EDITING_ROLES, OrganisationMembership


def membership_required(allowed_roles=None):
    """
    Decorator for views with an `org_pk` URL kwarg. Requires login AND a
    real `verified_member` OrganisationMembership; if `allowed_roles` is
    given, the member's role must be one of them. Attaches
    `request.organisation` and `request.membership` for the view.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        @login_required(login_url='/login/')
        def wrapped(request, org_pk, *args, **kwargs):
            organisation = get_object_or_404(Organisation, pk=org_pk)
            membership = OrganisationMembership.objects.filter(
                organisation=organisation, user=request.user, status='verified_member',
            ).first()
            if membership is None:
                return HttpResponseForbidden('You are not a verified member of this organisation.')
            if allowed_roles is not None and membership.role not in allowed_roles:
                return HttpResponseForbidden('Your role does not permit this action.')
            request.organisation = organisation
            request.membership = membership
            return view_func(request, org_pk, *args, **kwargs)
        return wrapped
    return decorator


def editor_required(view_func):
    return membership_required(allowed_roles=EDITING_ROLES)(view_func)


def any_member_required(view_func):
    return membership_required(allowed_roles=None)(view_func)
