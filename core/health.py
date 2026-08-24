"""
Liveness probe for the Render health check.

`/healthz/` answers exactly one question: is this Python process alive and able
to route a request? It deliberately answers nothing else.

No database, no cache, no broker, no template, no AI provider, no outbound
call. A liveness probe that touches a dependency stops being a liveness probe:
a brief database blip would fail the check, Render would replace a web process
that was in fact healthy, and the monitoring would have caused the outage
rather than found it. Readiness — "can this process serve dependent
functionality?" — is a different question and lives at `/readyz/`, below.
The two are deliberately separate: only liveness is wired to
`healthCheckPath` in render.yaml, so a dependency outage can never cause
Render to restart a web process that is itself fine.

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

import logging

from django.conf import settings
from django.db import connections
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache


@never_cache
def healthz(request: HttpRequest) -> HttpResponse:
    """
    HTTP 200 with the body `ok` for as long as the process can route a request.

    `never_cache` because a cached liveness response is worse than none: an
    intermediary replaying a stale `ok` would report a dead process as healthy.
    """
    return HttpResponse('ok', content_type='text/plain; charset=utf-8')


# ── Readiness ─────────────────────────────────────────────────────────────────
#
# `/readyz/` answers a different question from `/healthz/`: not "is this process
# alive?" but "can it currently serve the functionality that depends on its
# backing services?" It is NOT wired to render.yaml's healthCheckPath, and must
# not be — readiness failing is a reason to stop sending traffic, never a reason
# to kill a healthy process. Keeping the two apart is the whole design.
#
# WHAT IT REPORTS, AND WHAT IT REFUSES TO
#
# The body names each check and whether it passed. It carries no hostname, no
# port, no database name, no user, no connection string, no driver message and
# no traceback — a readiness probe is typically the most anonymously-reachable
# endpoint a service has, and an error string from a database driver routinely
# contains the host and user it failed to authenticate as. Failures are logged
# server-side with their real detail; the response gets a stable category.

READY_STATUS = 200
NOT_READY_STATUS = 503

_logger = logging.getLogger('ecoiq.health')

#: Bounded so a hung broker cannot hold a probe open. A readiness check that
#: never returns is indistinguishable from one that failed, but ties up a worker
#: thread while being useless.
REDIS_TIMEOUT_SECONDS = 2


def _check_database() -> tuple[bool, str]:
    """
    One trivial round trip on the default connection.

    `SELECT 1` rather than an ORM call: it proves the connection is usable
    without depending on any table existing, so a mid-migration schema state
    reports the connection honestly instead of failing for an unrelated reason.
    """
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        # exc_info so the real driver message reaches the logs and Sentry, and
        # nothing of it reaches the response body.
        _logger.warning('readiness.database_unavailable', exc_info=True)
        return False, 'unavailable'
    return True, 'ok'


def _check_redis() -> tuple[bool, str]:
    """
    PING against the configured broker, only when Redis is genuinely expected.

    Skipped entirely unless settings.REDIS_CONFIGURED — see the note there for
    why REDIS_URL's own truthiness is the wrong signal.
    """
    try:
        import redis
    except ImportError:
        _logger.warning('readiness.redis_client_missing')
        return False, 'client_missing'
    try:
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
            socket_timeout=REDIS_TIMEOUT_SECONDS,
        )
        try:
            client.ping()
        finally:
            client.close()
    except Exception:
        _logger.warning('readiness.redis_unavailable', exc_info=True)
        return False, 'unavailable'
    return True, 'ok'


@never_cache
def readyz(request: HttpRequest) -> JsonResponse:
    """
    200 when every expected dependency answers, 503 when any does not.

    503 (not 500) because "not ready" is an expected, recoverable operational
    state, not an application error: it tells a load balancer to route
    elsewhere and try again, which is exactly what a starting or briefly
    disconnected process wants said about it.
    """
    checks: dict[str, str] = {}

    database_ok, checks['database'] = _check_database()
    ready = database_ok

    if getattr(settings, 'REDIS_CONFIGURED', False):
        redis_ok, checks['redis'] = _check_redis()
        ready = ready and redis_ok
    else:
        # Reported rather than omitted. A missing key reads as "not checked yet"
        # to a human scanning two deployments side by side; "skipped" says the
        # dependency is deliberately not expected here.
        checks['redis'] = 'skipped'

    return JsonResponse(
        {'status': 'ready' if ready else 'not_ready', 'checks': checks},
        status=READY_STATUS if ready else NOT_READY_STATUS,
    )
