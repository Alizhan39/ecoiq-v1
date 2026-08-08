"""
Request correlation and lifecycle logging.

One id per request, bound into contextvars so every log line emitted while
handling it carries the same `request_id` without anyone passing it around.

What this deliberately does not log
-----------------------------------
No query string, no request body, no cookies, no Authorization header, no
user agent, no raw address. The path is recorded as the resolved **route
pattern** (`/companies/<slug>/`) rather than the concrete URL, because a
concrete URL can carry an identifier or a token in it and a route pattern
cannot.

Origin metadata comes from `core.client_origin.safe_origin_context()`, which
returns a fixed, closed set of structural fields and a keyed HMAC fingerprint.
This module never touches a forwarding header itself.
"""
from __future__ import annotations

import re
import time
import uuid
from collections.abc import Callable
from typing import Any

import structlog
from django.http import HttpRequest, HttpResponse
from django.urls import resolve

from core import events
from core.client_origin import safe_origin_context

REQUEST_ID_HEADER = 'X-Request-ID'
REQUEST_ID_META = 'HTTP_X_REQUEST_ID'

# An inbound id is accepted only in this shape. Without a bound, a client
# controls an unbounded string that lands in every log line for that request —
# a cheap way to inject newlines into a log stream or simply to bloat it.
INBOUND_ID_RE = re.compile(r'\A[A-Za-z0-9._-]{8,64}\Z')

# Paths whose successful completion is not worth a line each. A failure on any
# of them still logs — the filter is on `request_completed` at 2xx/3xx only.
QUIET_PATHS: tuple[str, ...] = ('/healthz', '/healthz/', '/health', '/health/')


def _new_request_id() -> str:
    """A fresh opaque id. uuid4 is random, not derived from anything internal."""
    return uuid.uuid4().hex


def incoming_request_id(request: HttpRequest) -> str:
    """
    The upstream id if it is safe to reuse, otherwise a new one.

    Reusing an inbound id is what makes a trace span a proxy or a client retry,
    but only a validated one: length- and charset-bounded, so it cannot forge a
    log line or carry a payload.
    """
    supplied = request.META.get(REQUEST_ID_META, '') or ''
    if INBOUND_ID_RE.match(supplied.strip()):
        return supplied.strip()
    return _new_request_id()


def route_of(request: HttpRequest) -> str:
    """
    The matched route pattern, never the concrete URL.

    `/companies/acme-ltd/` becomes `companies:detail`. A concrete path can carry
    an identifier, a slug tied to a person, or a token someone put in a URL; a
    route name cannot.
    """
    try:
        match = resolve(request.path_info)
    except Exception:
        return 'unresolved'
    return match.view_name or 'unnamed'


class RequestContextMiddleware:
    """
    Binds correlation context, logs the request lifecycle, echoes the id back.

    Place high in MIDDLEWARE so the id covers as much of the request as
    possible, including anything logged by middleware below it.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.logger = structlog.get_logger('ecoiq.request')

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = incoming_request_id(request)
        route = route_of(request)

        # clear_contextvars first: worker threads are reused, and without this a
        # previous request's bindings would still be present on this one.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            route=route,
            **safe_origin_context(request),
        )
        request.request_id = request_id  # type: ignore[attr-defined]

        # Same id on the Sentry event. Deliberately not a second correlation
        # id: one value has to join the HTTP response header, the log line and
        # the Sentry issue, or none of them join at all.
        #
        # A tag, because tags are searchable in Sentry and a context is not.
        # Not in the event title — that would fragment every issue into one
        # issue per request.
        _bind_sentry_scope(request_id, route, request)

        quiet = request.path_info in QUIET_PATHS
        if not quiet:
            self.logger.info(events.REQUEST_STARTED)

        started = time.monotonic()
        try:
            response = self.get_response(request)
        except Exception as exc:
            # Log and re-raise. Django's own handler still runs, still returns
            # the generic 500, and still reports to any future error tracker.
            self.logger.exception(
                events.REQUEST_FAILED,
                duration_ms=round((time.monotonic() - started) * 1000, 2),
                exception_type=type(exc).__name__,
            )
            structlog.contextvars.clear_contextvars()
            raise

        duration_ms = round((time.monotonic() - started) * 1000, 2)
        status = int(response.status_code)

        # A health check that fails is exactly the line we want to keep.
        if not quiet or status >= 400:
            self.logger.info(
                events.REQUEST_COMPLETED,
                status_code=status,
                duration_ms=duration_ms,
            )

        response[REQUEST_ID_HEADER] = request_id
        # Always clear: a leaked binding would attach this request's id to the
        # next one handled by this thread.
        structlog.contextvars.clear_contextvars()
        return response


def _bind_sentry_scope(request_id: str, route: str, request: HttpRequest) -> None:
    """
    Mirror the correlation fields onto Sentry's scope, if Sentry is active.

    Silently does nothing when the SDK is absent or uninitialised, which is the
    normal state in development, CI and any deployment without a DSN.

    Only fields already approved for logging are attached. safe_origin_context()
    returns a closed set that cannot contain an address, so Sentry receives the
    same keyed fingerprint the logs carry and nothing more.
    """
    try:
        import sentry_sdk
    except ImportError:                                    # pragma: no cover
        return
    if sentry_sdk.get_client().dsn is None:
        return
    scope = sentry_sdk.get_current_scope()
    scope.set_tag('request_id', request_id)
    scope.set_tag('route', route)
    scope.set_context('ecoiq', {
        'request_id': request_id,
        'route': route,
        **safe_origin_context(request),
    })


def bind_operation(operation: str, operation_id: str | None = None) -> str:
    """
    Correlation for work with no HTTP request — a management command, or a
    future Celery task binding its own task id.

    Returns the id so a caller can report it. Deliberately not called
    `request_id`: conflating the two would make a log search for one return the
    other. A future distributed tracer would add `trace_id` alongside; this is
    not that, and does not pretend to be.
    """
    resolved = operation_id or _new_request_id()
    structlog.contextvars.bind_contextvars(
        operation=operation, operation_id=resolved)
    return resolved


def clear_operation() -> None:
    """Drop operation context. Call in a finally block."""
    structlog.contextvars.clear_contextvars()


def current_context() -> dict[str, Any]:
    """The currently bound context. For tests and diagnostics."""
    return dict(structlog.contextvars.get_contextvars())
