"""
Structured logging for EcoIQ.

Why structlog directly, and not django-structlog
------------------------------------------------
django-structlog 10.1.0 is well maintained and does support Django 5.2 on
Python 3.11, so compatibility was not the deciding factor. Two of its defaults
were:

  1. It depends on `django-ipware`, a second, independently-configured client-IP
     resolver. EcoIQ already has one — `core.client_origin` — whose trusted-proxy
     model was measured against production (Cloudflare in front of Render appends
     exactly two X-Forwarded-For entries) after the previous model silently broke
     rate limiting. A second resolver with its own settings would be free to
     disagree, and the repo-wide invariant that only `core/client_origin.py`
     parses forwarding headers would no longer hold.
  2. Its request middleware calls `bind_contextvars(ip=ip)` — the raw client
     address, in the context of every log line — plus `user_agent`.

Eliminating raw-IP logging is the point of this module, so adopting a library
whose first act is to bind the raw IP, then configuring that back off, is more
moving parts for a worse guarantee. The middleware we need instead is small, and
it is in `core.logging_middleware`.

What is guaranteed here
-----------------------
`redact_sensitive` runs on **every** event from **every** logger, including
third-party libraries routed through the stdlib bridge. It is not advisory: a
developer cannot forget it, because it is not something they invoke.

Nothing in this module reads a request body, a cookie, an Authorization header,
a session, or a raw address.
"""
from __future__ import annotations

import logging
import re
from collections.abc import MutableMapping
from typing import Any

import structlog

# ── redaction ────────────────────────────────────────────────────────────────

REDACTED = '[REDACTED]'

# Substring match, deliberately. An exact key list is the version of this that
# fails: the field will eventually arrive as `stripe_api_key`, `user_password`
# or `auth_token_refresh`, and an exact list catches none of them.
SENSITIVE_KEY_PARTS: tuple[str, ...] = (
    'password', 'passwd', 'secret', 'token', 'api_key', 'apikey',
    'authorization', 'auth_header', 'cookie', 'session', 'csrf',
    'database_url', 'dsn', 'private_key', 'credential', 'passphrase',
    'turnstile', 'signature',
)

# Personal or user-generated content. Distinct from the list above because these
# are not credentials — they are someone's data, and they do not belong in an
# operational log even when it would be convenient.
PERSONAL_KEY_PARTS: tuple[str, ...] = (
    'email', 'phone', 'full_name', 'contact_name', 'first_name', 'last_name',
    'address', 'postcode', 'message', 'body', 'prompt', 'completion',
    'ip_address', 'remote_addr', 'client_ip', 'forwarded_for',
)

# Values that look like an address even when the key is innocent — a defence
# against a raw IP arriving inside an f-string someone assembled by hand.
IPV4_RE = re.compile(r'\b\d{1,3}(?:\.\d{1,3}){3}\b')
IPV6_RE = re.compile(r'\b(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}\b')
# Same reasoning for addresses of the other kind. An exception message is
# user-influenced text — `ValueError("no account for alice@example.com")` is an
# ordinary thing to write — and a key-name rule cannot catch it because the key
# is `exception`, which we very much want to keep.
EMAIL_RE = re.compile(r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b')

# Keys whose values must survive the value scan.
#
# `timestamp` is here for a concrete reason: an ISO timestamp contains
# `21:25:13`, which the IPv6 pattern matches, so scanning it would corrupt every
# log line. The others are opaque digests that would be mangled for no gain.
#
# `event` is deliberately NOT exempt. A stdlib call like
# `logger.warning('failed for %s', ip)` renders the address into the message,
# and the message becomes `event` — so exempting it would leave 66 modules'
# worth of legacy logging as an unredacted hole. Structlog event names are
# snake_case identifiers, so scanning them costs nothing.
VALUE_SCAN_EXEMPT: frozenset[str] = frozenset({
    'origin_fingerprint', 'request_id', 'timestamp', 'level',
    'classifier_version', 'snapshot_hash', 'fingerprint',
})


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS + PERSONAL_KEY_PARTS)


def _scrub_value(value: Any) -> Any:
    """Replace anything address-shaped inside a string value."""
    if not isinstance(value, str):
        return value
    scrubbed = IPV4_RE.sub(REDACTED, value)
    if ':' in scrubbed:
        scrubbed = IPV6_RE.sub(REDACTED, scrubbed)
    if '@' in scrubbed:
        scrubbed = EMAIL_RE.sub(REDACTED, scrubbed)
    return scrubbed


def _redact(obj: Any, depth: int = 0) -> Any:
    """Recursive redaction of a mapping, bounded so a cycle cannot hang a log call."""
    if depth > 6:
        return REDACTED
    if isinstance(obj, MutableMapping):
        out: dict[Any, Any] = {}
        for key, value in obj.items():
            if isinstance(key, str) and _is_sensitive(key):
                out[key] = REDACTED
            elif isinstance(key, str) and key in VALUE_SCAN_EXEMPT:
                out[key] = value
            else:
                out[key] = _redact(value, depth + 1)
        return out
    if isinstance(obj, (list, tuple)):
        return type(obj)(_redact(v, depth + 1) for v in obj)
    return _scrub_value(obj)


def redact_sensitive(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """
    structlog processor. Redacts the event dict only — never a business object.

    Runs last in the chain, so anything a caller or another processor added is
    covered. Only the dict passed to the logger is touched; the objects it was
    built from are untouched.
    """
    result = _redact(event_dict)
    return result if isinstance(result, MutableMapping) else event_dict


def add_service_metadata(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """
    Environment and release fields, for filtering once logs are aggregated.

    Also the hook a future Sentry integration reads for environment/release,
    which is why it lives here rather than being formatted into a message.
    """
    from django.conf import settings

    event_dict.setdefault('service', 'ecoiq')
    event_dict.setdefault(
        'environment',
        'production' if getattr(settings, 'IS_PRODUCTION', False) else 'development')
    release = getattr(settings, 'RELEASE_VERSION', '')
    if release:
        event_dict.setdefault('release', release)
    return event_dict


# ── configuration ────────────────────────────────────────────────────────────

SHARED_PROCESSORS: list[Any] = [
    structlog.contextvars.merge_contextvars,     # request_id and friends
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt='iso', utc=True),
    structlog.processors.StackInfoRenderer(),
    # Turns exc_info into an `exception` STRING before redaction runs.
    #
    # Order is the whole point. Left as a (type, value, traceback) tuple, the
    # exception is an object the scrubber cannot read, and the renderer
    # stringifies it afterwards — so `ValueError('failed for 203.0.113.9')`
    # reached the log intact. An exception message is user-influenced text and
    # gets redacted like any other.
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
    add_service_metadata,
    # Last, so nothing added above escapes it.
    redact_sensitive,
]


def configure_structlog(*, json_logs: bool) -> None:
    """
    Wire structlog and the stdlib together.

    `json_logs` is passed explicitly rather than sniffed from the hostname: the
    renderer is a deployment decision, and tests need to choose it.

    The stdlib bridge matters more than it looks. 66 modules already call
    `logging.getLogger(...)`, and rewriting them is not the job of this PR — but
    their output must still be redacted and still carry the request id. Routing
    them through the same processor chain achieves both without touching them.
    """
    renderer: Any = (
        structlog.processors.JSONRenderer() if json_logs
        # colors=False: ANSI escapes in a log aggregator are noise, and the dev
        # console is readable without them.
        else structlog.dev.ConsoleRenderer(colors=False)
    )

    structlog.configure(
        processors=[
            *SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # Applied to records from plain `logging` calls, so a third-party
        # WARNING is redacted and correlated exactly like ours.
        foreign_pre_chain=SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Every handler on every configured logger, not just root.
    #
    # settings.LOGGING gives `django.request` and `django.db.backends` their own
    # handlers with `propagate: False`. Formatting only root's handlers would
    # leave those two outside the pipeline — and `django.request` is where
    # unhandled 500s and their tracebacks go. Those lines would have stayed
    # plain text in a JSON log stream, and unredacted.
    seen: set[int] = set()
    loggers: list[logging.Logger] = [logging.getLogger()]
    for name in list(logging.root.manager.loggerDict):
        item = logging.getLogger(name)
        if isinstance(item, logging.Logger):
            loggers.append(item)
    for entry in loggers:
        for handler in entry.handlers:
            if id(handler) not in seen:
                seen.add(id(handler))
                handler.setFormatter(formatter)


def get_logger(name: str | None = None) -> Any:
    """The logger every EcoIQ module should use for structured events."""
    return structlog.get_logger(name)
