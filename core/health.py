"""
Liveness probe for the Render health check.

`/healthz/` answers exactly one question: is this Python process alive and able
to route a request? It deliberately answers nothing else.

No database, no cache, no broker, no template, no AI provider, no outbound
call. A liveness probe that touches a dependency stops being a liveness probe:
a brief database blip would fail the check, Render would replace a web process
that was in fact healthy, and the monitoring would have caused the outage
rather than found it. Readiness — "can this process serve dependent
functionality?" — is a different question and belongs at a separate endpoint
(`/readyz/`), which does not exist yet and is deliberately not added here.

The full middleware stack still runs, and that is intended: the probe should
travel the same path a real request does, or it is not measuring the thing it
claims to measure. It still issues no query, because Django's session and auth
middleware are lazy and this view touches neither `request.session` nor
`request.user`. `core.tests_health` pins that with `assertNumQueries(0)` rather
than leaving it as an assumption.

`core.logging_middleware.QUIET_PATHS` already lists this path, so a successful
probe every few seconds does not fill the log stream. A probe that fails still
logs, because that is the line worth keeping.
"""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.views.decorators.cache import never_cache


@never_cache
def healthz(request: HttpRequest) -> HttpResponse:
    """
    HTTP 200 with the body `ok` for as long as the process can route a request.

    `never_cache` because a cached liveness response is worse than none: an
    intermediary replaying a stale `ok` would report a dead process as healthy.
    """
    return HttpResponse('ok', content_type='text/plain; charset=utf-8')
