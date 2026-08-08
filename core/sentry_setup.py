"""
Sentry error monitoring, disabled unless explicitly configured.

Why this module exists rather than a call in settings
-----------------------------------------------------
`sentry_sdk.init()` is called in exactly one place, from `ecoiq/settings.py`,
and everything it needs is here. Scattering `init()` or `capture_exception()`
through views and tasks is how a project ends up with two clients, duplicated
events, and no single place to check what leaves the building.

Why structlog redaction is not enough
-------------------------------------
This is the part worth being clear about. The logging pipeline scrubs what goes
into a *log line*. Sentry does not read log lines — it captures exceptions and
request state directly from the running process, before any of that. Measured
against sentry-sdk 2.66.1, the defaults it would use are:

    include_local_variables  True      -> every stack frame's local variables
    max_request_body_size    'medium'  -> request bodies, form data, JSON

and DjangoIntegration attaches "HTTP method, URL, headers, form data, JSON
payloads" to every event. A local variable in a contact view holds the message
text; one in an AI client holds the prompt and the API key. None of that passes
through structlog, so none of it would have been redacted.

The defences here are therefore independent of logging, and layered:

    1. SDK options that stop data being *collected* at all
    2. EventScrubber, the SDK's own recursive key-based scrubber
    3. before_send, our own recursive pass over the finished event
    4. before_breadcrumb, the same pass over each breadcrumb

The order matters: (1) is the only one that cannot be defeated by a payload
shape nobody anticipated, so as much as possible is done there.
"""
from __future__ import annotations

import os
from collections.abc import MutableMapping
from typing import Any

REDACTED = '[REDACTED]'

# Reused so Sentry and the log pipeline cannot drift apart on what is sensitive.
from core.logging_setup import (  # noqa: E402
    PERSONAL_KEY_PARTS, SENSITIVE_KEY_PARTS, _scrub_value,
)

# Event sections we deliberately never send. `data` is the request body,
# `cookies` speaks for itself, and `env` carries the whole WSGI environ — the
# socket peer address and every inbound header, forwarding headers included.
#
# (Those two environ keys are named in core/client_origin.py and nowhere else.
# Writing them here as literals would trip the repo-wide guard asserting that
# only the resolver reads them, and that guard is worth more than the clarity
# of naming them in a comment.)
REQUEST_KEYS_DROPPED = ('data', 'cookies', 'env')

# Headers dropped by exact name, case-insensitively. DjangoIntegration collects
# all of them; these are the ones that are credentials or addresses.
HEADERS_DROPPED = frozenset({
    'authorization', 'cookie', 'set-cookie', 'x-csrftoken', 'x-forwarded-for',
    'cf-connecting-ip', 'true-client-ip', 'x-real-ip', 'proxy-authorization',
    'x-api-key', 'cf-turnstile-response',
})

# Exceptions that are ordinary control flow, not defects. Kept deliberately
# short: a long ignore list is how a real regression gets filtered out.
IGNORED_EXCEPTIONS = (
    'django.http.Http404',
    'django.core.exceptions.PermissionDenied',
    'django.core.exceptions.SuspiciousOperation',
)


# Sentry's own top-level field for a breadcrumb or event title. It holds a
# controlled event name — `rate_limit_applied` — not user content, and
# `message` is in PERSONAL_KEY_PARTS to catch `contact_message` and friends.
# Blanket-redacting it turned every breadcrumb into "[REDACTED]", which is a
# trail that tells you nothing. Exact key only: `contact_message` still goes.
MESSAGE_KEYS = frozenset({'message'})

# Typed fields whose values Sentry parses rather than displays. Scrubbing one
# does not redact a secret; it corrupts a field the ingest pipeline validates,
# and the event is discarded — "Discarded invalid value / Name: timestamp" is
# what an over-eager value scan actually bought us.
#
# The value scan is now accurate enough not to need this (IPv6 is validated by
# `ipaddress`, so a clock time is never mistaken for an address). It stays as
# defence in depth: a typed field should not be at the mercy of a text pattern
# at all, whatever that pattern currently does.
TYPED_VALUE_KEYS = frozenset({
    'timestamp', 'start_timestamp', 'received', 'datetime', 'event_id',
    'span_id', 'trace_id', 'parent_span_id', 'release', 'environment',
    'platform', 'level', 'logger', 'transaction', 'type', 'lineno',
})


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in MESSAGE_KEYS:
        return False
    return any(part in lowered for part in SENSITIVE_KEY_PARTS + PERSONAL_KEY_PARTS)


def scrub(obj: Any, depth: int = 0) -> Any:
    """
    Recursive redaction of an outbound Sentry payload.

    Bounded depth so a self-referencing structure cannot hang the SDK's
    background worker — an event is not worth a stuck thread.
    """
    if depth > 12:
        return REDACTED
    if isinstance(obj, MutableMapping):
        out: dict[Any, Any] = {}
        for key, value in obj.items():
            if isinstance(key, str) and _is_sensitive_key(key):
                out[key] = REDACTED
            elif isinstance(key, str) and key.lower() in TYPED_VALUE_KEYS:
                # Passed through untouched — see TYPED_VALUE_KEYS.
                out[key] = value
            else:
                out[key] = scrub(value, depth + 1)
        return out
    if isinstance(obj, (list, tuple)):
        return type(obj)(scrub(v, depth + 1) for v in obj)
    return _scrub_value(obj)


def scrub_request(request: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Strip the request section down to method and path."""
    for key in REQUEST_KEYS_DROPPED:
        request.pop(key, None)

    headers = request.get('headers')
    if isinstance(headers, MutableMapping):
        request['headers'] = {
            name: (REDACTED if name.lower() in HEADERS_DROPPED else _scrub_value(value))
            for name, value in headers.items()
        }

    # A query string is user-controlled and routinely carries tokens and search
    # terms. The path alone is what makes an event findable.
    if request.get('query_string'):
        request['query_string'] = REDACTED
    url = request.get('url')
    if isinstance(url, str) and '?' in url:
        request['url'] = url.split('?', 1)[0]
    return request


def scrub_exception_values(event: MutableMapping[str, Any]) -> None:
    """
    Replace each exception's message, keep its type and stack.

    The same decision the log pipeline makes, for the same reason:
    `exception.values[].value` is arbitrary text nobody vetted. It could be a
    provider response, a contact message, or a token someone interpolated. The
    type plus the frame is what identifies the defect.
    """
    exception = event.get('exception')
    if not isinstance(exception, MutableMapping):
        return
    for entry in exception.get('values') or []:
        if not isinstance(entry, MutableMapping):
            continue
        if entry.get('value'):
            entry['value'] = REDACTED
        stacktrace = entry.get('stacktrace')
        if isinstance(stacktrace, MutableMapping):
            for frame in stacktrace.get('frames') or []:
                # Belt and braces: include_local_variables is off, so this
                # should already be absent. If a future SDK reintroduces it,
                # or an integration sets it directly, it dies here.
                if isinstance(frame, MutableMapping):
                    frame.pop('vars', None)


def scrub_argv(event: MutableMapping[str, Any]) -> None:
    """
    Keep which command ran; drop what it was given.

    The SDK attaches `extra['sys.argv']` to every event. For a web worker that
    is harmless, but this application has management commands that take secrets
    on the command line — `create_demo_user --password …` among them — and a
    command that raises would have shipped that argument to Sentry verbatim.

    No key rule catches it: the key is `sys.argv`, not `password`. No value rule
    catches it either, because a password has no shape. Verified: a synthetic
    `--password ARGV_SECRET_55123` reached the transport intact before this.

    argv[0] and argv[1] identify the script and the subcommand, which is the
    diagnostic value; everything after is redacted as a unit rather than
    guessing which arguments are sensitive.
    """
    extra = event.get('extra')
    if not isinstance(extra, MutableMapping):
        return
    argv = extra.get('sys.argv')
    if isinstance(argv, (list, tuple)) and argv:
        kept = [str(part) for part in argv[:2]]
        if len(argv) > 2:
            kept.append(REDACTED)
        extra['sys.argv'] = kept


def before_send(event: MutableMapping[str, Any], hint: Any) -> MutableMapping[str, Any] | None:
    """
    Last gate before an event leaves the process.

    Wrapped, because a raising before_send is swallowed by the SDK and the event
    is dropped with no trace. A NameError introduced here once disabled error
    reporting entirely and the only symptom was events quietly not arriving —
    monitoring failing silently is worse than monitoring being switched off,
    because nobody goes looking.

    On failure the event is DROPPED, not sent unscrubbed: a scrubber that cannot
    run has not established that the payload is safe. The drop is logged through
    the structured pipeline, which is redacted and does not depend on this code.
    """
    try:
        return _before_send(event, hint)
    except Exception:
        import structlog
        structlog.get_logger('ecoiq.sentry').exception(
            'sentry_before_send_failed',
            note='event dropped rather than sent unscrubbed')
        return None


def _before_send(event: MutableMapping[str, Any], hint: Any) -> MutableMapping[str, Any] | None:
    request = event.get('request')
    if isinstance(request, MutableMapping):
        event['request'] = scrub_request(request)

    scrub_exception_values(event)
    scrub_argv(event)

    # Never send user identity beyond an internal id. DjangoIntegration will
    # populate username/email if send_default_pii is ever switched on; this
    # keeps that from mattering.
    user = event.get('user')
    if isinstance(user, MutableMapping):
        event['user'] = {'id': str(user['id'])} if user.get('id') else {}

    return scrub(event)  # type: ignore[return-value]


def before_breadcrumb(crumb: MutableMapping[str, Any], hint: Any) -> MutableMapping[str, Any] | None:
    """
    Same scrubbing for breadcrumbs, plus dropping the noisy ones.

    Also wrapped: a breadcrumb that cannot be scrubbed is dropped, not kept.

    Request lifecycle events are the highest-volume thing this application logs.
    As breadcrumbs they would push the genuinely interesting lines out of the
    trail long before the error that needs them.
    """
    try:
        message = str(crumb.get('message') or '')
        if message in ('request_started', 'request_completed'):
            return None
        return scrub(crumb)  # type: ignore[return-value]
    except Exception:
        return None


# ── configuration ────────────────────────────────────────────────────────────

class SentryConfigurationError(RuntimeError):
    """Raised when Sentry is explicitly enabled but cannot be configured safely."""


def _sample_rate(name: str, default: float = 0.0) -> float:
    """
    Parse a rate, refusing anything outside 0.0–1.0.

    A malformed value must never be read as 1.0. At full sampling this would
    bill for every transaction in production, which is precisely the accident
    worth failing loudly over.
    """
    raw = (os.environ.get(name) or '').strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise SentryConfigurationError(
            f'{name} must be a number between 0.0 and 1.0, got {raw!r}.') from None
    if not 0.0 <= value <= 1.0:
        raise SentryConfigurationError(
            f'{name} must be between 0.0 and 1.0, got {value}.')
    return value


def sentry_options(*, dsn: str, environment: str, release: str) -> dict[str, Any]:
    """The complete option set, as a dict so tests can assert on it directly."""
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber

    denylist = list(DEFAULT_DENYLIST) + [
        *SENSITIVE_KEY_PARTS, *PERSONAL_KEY_PARTS,
        'client_secret', 'refresh_token', 'access_token', 'database_url',
    ]

    return {
        'dsn': dsn,
        'environment': environment,
        'release': release or None,
        'debug': False,

        # Never. Off by default in the SDK too, but stated explicitly because
        # its default has changed across major versions and this one matters.
        'send_default_pii': False,

        # Default is True. Locals hold contact messages, AI prompts, API keys
        # and database credentials — the single most dangerous default here.
        'include_local_variables': False,

        # Default is 'medium', which sends request bodies and form data.
        'max_request_body_size': 'never',

        # The SDK's own recursive scrubber, widened with our key lists. Runs in
        # addition to before_send, not instead of it.
        'event_scrubber': EventScrubber(denylist=denylist, recursive=True),

        'before_send': before_send,
        'before_breadcrumb': before_breadcrumb,

        # Errors: all of them. Sentry's own rate limits handle volume, and
        # sampling errors means losing the one occurrence someone needs.
        'sample_rate': 1.0,

        # Tracing off unless deliberately configured. Never hardcode 1.0.
        'traces_sample_rate': _sample_rate('SENTRY_TRACES_SAMPLE_RATE', 0.0),

        # Profiling stays off. It is a separate cost and privacy decision, and
        # it samples stacks — which is a different exposure from error frames.
        'profiles_sample_rate': 0.0,

        'ignore_errors': list(IGNORED_EXCEPTIONS),

        # 2s. Long enough to flush a pending event on a Render restart, short
        # enough not to hold a shutdown open.
        'shutdown_timeout': 2,

        # Only the two integrations we actually reviewed. Without this the SDK
        # auto-enables whatever it finds installed — a captured event listed
        # celery, fastapi, flask, httpx, langchain, langgraph, redis, sqlalchemy
        # and starlette, none of which was assessed here.
        #
        # langchain is the one that matters: its instrumentation exists to
        # record prompts and completions, which is precisely the data this
        # application must never send. redis and httpx add breadcrumbs that can
        # carry URLs and keys. Turning the lot off is smaller and more honest
        # than auditing nine integrations nobody asked for.
        'auto_enabling_integrations': False,
        'integrations': [
            DjangoIntegration(
                # Route pattern, not the concrete URL. A URL carries slugs and
                # ids, which makes transaction names high-cardinality and can
                # put an identifier in the title.
                transaction_style='url',
                middleware_spans=False,
                signals_spans=False,
                cache_spans=False,
            ),
            LoggingIntegration(
                # Breadcrumbs from INFO upward…
                level=20,        # logging.INFO
                # …but only ERROR becomes an event. Without this split, every
                # logger.error would produce a Sentry event AND DjangoIntegration
                # would produce one for the same exception — two events, one
                # fault. ERROR here plus DjangoIntegration is the standard pair;
                # the duplicate case is covered by a test.
                event_level=40,  # logging.ERROR
            ),
        ],
        'attach_stacktrace': False,
        '_sdk_version': sentry_sdk.VERSION,
    }


def is_enabled() -> bool:
    """
    True only when a DSN is present and Sentry has not been switched off.

    Absent DSN means disabled, silently and cleanly. A deployment without error
    monitoring configured is a normal state — local development, CI, a fresh
    environment — and refusing to boot over it would be worse than the gap.
    """
    if (os.environ.get('SENTRY_ENABLED') or '').strip().lower() in ('0', 'false', 'no'):
        return False
    return bool((os.environ.get('SENTRY_DSN') or '').strip())


def initialise(*, environment: str, release: str) -> bool:
    """
    Initialise the SDK. Returns whether it was enabled.

    Called once, from settings. No network happens here: the SDK opens no
    connection at init, and the first request is only made when an event is
    actually queued.
    """
    if not is_enabled():
        return False

    import sentry_sdk

    options = sentry_options(
        dsn=(os.environ.get('SENTRY_DSN') or '').strip(),
        environment=environment,
        release=release,
    )
    options.pop('_sdk_version', None)
    sentry_sdk.init(**options)
    return True
