"""
api/v2_platform.py — platform counters and module statuses for the frontend.

The ONE endpoint any surface calls to learn a number about EcoIQ. Everything
here is derived: from the database, or from the code-owned module registry.
Nothing is hard-coded, and every figure carries the derivation that produced it
so a reader can check it.

Narrow on purpose. The brief warns against one giant "everything" endpoint, and
this is the platform resource — counters and module statuses — not a dumping
ground for whatever the homepage happens to need next.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from platform_registry.agents import MODULES
from platform_registry.stats import platform_stats


@api_view(['GET'])
@permission_classes([AllowAny])
def platform(request):
    """
    GET /api/v2/platform/

    `counters[].value` may be null, which means "no meaningful figure" and must
    render as an em dash. It is never 0 — a zero is a measurement and null is
    the absence of one.

    `modules[].evaluation` may be "NOT YET MEASURED", which is an honest value
    and must never be rendered as 0%.
    """
    counters = [
        {
            'key': counter.key,
            'label': counter.label,
            'value': counter.value,
            'derivation': counter.derivation,
            'is_proof': counter.is_proof,
        }
        for counter in platform_stats().values()
    ]

    modules = [
        {
            'key': module.key,
            'name': module.name,
            'kind': module.kind,
            'status': module.status,
            'evaluation': module.evaluation,
            'basis': module.basis,
        }
        for module in MODULES
    ]

    return Response({'counters': counters, 'modules': modules})
