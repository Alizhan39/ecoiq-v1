"""outreach_readiness/services/route.py — Phase 5: contact route verification and provenance."""
from django.utils import timezone

from outreach_readiness.models import OutreachRoute


class RouteNotAllowedError(Exception):
    pass


def record_route(assessment, *, actor, contact_page_or_institutional_email, route_type, source_reference,
                  official_website='', route_purpose='', jurisdiction='', date_checked=None,
                  accepts_this_request_type=None, published_restrictions='', linked_capability_graph_route=None):
    """
    Records a real, published route — never a guessed email, never a
    personal contact unless clearly published for the relevant
    institutional purpose (enforced by review discipline, same as
    good_agents.ActionContact). Supersedes any prior active route for this
    assessment (Phase 5 — "if no defensible route exists, the pilot
    remains BLOCKED_NO_VERIFIED_ROUTE" implies exactly one active route at
    a time, with history preserved via `superseded_at`).
    """
    if actor is None:
        raise RouteNotAllowedError('Recording a contact route requires a real actor.')
    if not contact_page_or_institutional_email or not source_reference:
        raise RouteNotAllowedError('A route requires both a real contact channel and its published source reference.')

    assessment.routes.filter(superseded_at__isnull=True).update(superseded_at=timezone.now())
    return OutreachRoute.objects.create(
        assessment=assessment, official_website=official_website,
        contact_page_or_institutional_email=contact_page_or_institutional_email, route_type=route_type,
        route_purpose=route_purpose, source_reference=source_reference, date_checked=date_checked or timezone.now().date(),
        jurisdiction=jurisdiction, accepts_this_request_type=accepts_this_request_type,
        published_restrictions=published_restrictions, linked_capability_graph_route=linked_capability_graph_route,
        created_by=actor,
    )


def active_route(assessment):
    return assessment.routes.filter(superseded_at__isnull=True).order_by('-created_at').first()
