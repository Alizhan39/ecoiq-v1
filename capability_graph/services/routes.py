"""
capability_graph/services/routes.py — verified public routes into a
capability. A route is never guessed: `route_value` must be passed in by
the caller from real evidence (typically the parent capability's own
`evidence_url`, or an independently sourced public contact).
"""
from capability_graph.models import PublicRoute, PublicRouteRevision


def add_public_route(organisation_capability, route_type, route_value, *, is_currently_open=True, notes=''):
    if not route_value:
        raise ValueError('route_value is required — a route can never be recorded with no real destination.')
    route, _ = PublicRoute.objects.update_or_create(
        organisation_capability=organisation_capability, route_type=route_type, route_value=route_value,
        defaults=dict(is_currently_open=is_currently_open, notes=notes),
    )
    return route


def propose_route_update(route, *, actor, route_value=None, is_currently_open=None, reason=''):
    """
    PR8 Phase 10 — a partner-side member proposes an update to an existing
    route. Every change is logged to PublicRouteRevision BEFORE the live
    row is mutated, so no prior value is ever lost. This never sets
    `verified_at` — a partner-edited route is not automatically
    "independently verified" (that requires a separate EcoIQ action, same
    human-gate discipline as everywhere else in this codebase).
    """
    if actor is None:
        raise ValueError('propose_route_update() requires a real actor.')
    PublicRouteRevision.objects.create(
        route=route,
        previous_route_value=route.route_value, new_route_value=route_value or route.route_value,
        previous_is_currently_open=route.is_currently_open,
        new_is_currently_open=route.is_currently_open if is_currently_open is None else is_currently_open,
        changed_by=actor, reason=reason,
    )
    if route_value is not None:
        route.route_value = route_value
    if is_currently_open is not None:
        route.is_currently_open = is_currently_open
    route.proposed_by = actor
    route.save(update_fields=['route_value', 'is_currently_open', 'proposed_by', 'updated_at'])
    return route
