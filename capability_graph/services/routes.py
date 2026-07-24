"""
capability_graph/services/routes.py — verified public routes into a
capability. A route is never guessed: `route_value` must be passed in by
the caller from real evidence (typically the parent capability's own
`evidence_url`, or an independently sourced public contact).
"""
from capability_graph.models import PublicRoute


def add_public_route(organisation_capability, route_type, route_value, *, is_currently_open=True, notes=''):
    if not route_value:
        raise ValueError('route_value is required — a route can never be recorded with no real destination.')
    route, _ = PublicRoute.objects.update_or_create(
        organisation_capability=organisation_capability, route_type=route_type, route_value=route_value,
        defaults=dict(is_currently_open=is_currently_open, notes=notes),
    )
    return route
