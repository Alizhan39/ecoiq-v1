# Structured logging

EcoIQ emits machine-readable JSON logs in production and human-readable console
output everywhere else, with one correlation id per request and central
redaction of sensitive fields.

## Architecture: structlog directly, not django-structlog

`django-structlog` 10.1.0 was evaluated first. It is actively maintained and
does support Django 5.2 on Python 3.11, so compatibility was not the deciding
factor. Two of its behaviours were:

1. **It depends on `django-ipware`** (`Requires-Dist: django-ipware>=6.0.2`) —
   a second, independently-configured client-IP resolver. EcoIQ already has one.
   `core/client_origin.py`'s trusted-proxy model was *measured* against
   production after the previous model silently broke rate limiting: Cloudflare
   sits in front of Render and appends exactly two `X-Forwarded-For` entries. A
   second resolver with its own settings is free to disagree, and the repo-wide
   invariant that only `core/client_origin.py` parses forwarding headers would
   no longer hold.
2. **Its request middleware binds the raw client IP** —
   `middlewares/request.py:218`, `bind_contextvars(ip=ip)` — into the context of
   every log line, plus `user_agent` at line 205.

Eliminating raw-IP logging is the entire point of this work. Adopting a library
whose first action is to bind the raw IP, then configuring that back off, is
more moving parts for a weaker guarantee. The middleware we need instead is
~150 lines, in `core/logging_middleware.py`.

| Package | Version | Purpose |
|---|---|---|
| structlog | 26.1.0 | in `requirements.txt` — production emits through it |

No Sentry, no OpenTelemetry, no logging SaaS SDK.

## Event model

Event names are stable snake_case identifiers in `core/events.py`, not prose.
`event = "contact_submission_rejected"` stays searchable when someone rewords
the sentence around it.

| Event | Level | Emitted by |
|---|---|---|
| `request_started` | INFO | `RequestContextMiddleware` |
| `request_completed` | INFO | `RequestContextMiddleware` |
| `request_failed` | ERROR | `RequestContextMiddleware` |
| `contact_submission_accepted` | INFO | `core.views._log_submission` |
| `contact_submission_reviewed` | INFO | `core.views._log_submission` |
| `contact_submission_rejected` | INFO | `core.views._log_submission` |
| `rate_limit_applied` | INFO | `companies.throttle` |
| `rate_limit_backend_unavailable` | WARNING | reserved |
| `origin_resolution_failed` | WARNING | reserved |

**Rate limiting logs at INFO, not WARNING.** A limiter turning traffic away is
the system working. At WARNING, an attack floods the log with warnings at
precisely the moment the log needs to stay readable. WARNING is reserved for the
limiter itself being unhealthy.

Only events with a real call site are listed. Adding a name without one would
describe a subsystem that does not exist.

## Request ID lifecycle

- Generated server-side as `uuid.uuid4().hex` — random, not derived from any
  internal identifier.
- An inbound `X-Request-ID` is reused **only** if it matches
  `[A-Za-z0-9._-]{8,64}`. An unbounded client string lands in every log line for
  that request: that is log injection (newlines) and log bloat. Anything failing
  validation is replaced silently.
- Bound with `structlog.contextvars`, so every log call during the request
  carries it without being passed around.
- Echoed back as `X-Request-ID` on the response.
- **Cleared at the end of every request, including on exception.** Worker
  threads are reused; without this, one request's id would attach to the next.

`bind_operation()` / `clear_operation()` provide the same correlation for code
with no request — a management command, or a future Celery task binding its own
task id. It sets `operation_id`, deliberately not `request_id`: conflating them
would make a search for one return the other. A future distributed tracer would
add `trace_id`; this is not that and does not pretend to be.

## Origin privacy

Origin fields come from `core.client_origin.safe_origin_context()` and nowhere
else. This module never reads a forwarding header itself.

Logged: `origin_available`, `origin_fingerprint`, `origin_resolution_status`,
`origin_private`, `origin_family`, `forwarded_hop_count`, `trusted_proxy_count`,
`trusted_header_configured`.

`origin_fingerprint` is a keyed HMAC-SHA256 (`REQUEST_ORIGIN_HMAC_KEY`, version
prefixed), not a bare hash — the IPv4 space is small enough to reverse an
unkeyed digest in seconds. Rotating the key expires all correlation, which is
the intended way to expire it.

## Redaction

`redact_sensitive` is the **last** processor in the chain and runs on every
event from every logger, including third-party libraries routed through the
stdlib bridge. It is not advisory; a developer cannot forget it.

- Keys matching `password`, `secret`, `token`, `api_key`, `authorization`,
  `cookie`, `session`, `csrf`, `database_url`, `dsn`, `private_key`,
  `credential`, `turnstile`, `signature` → `[REDACTED]`
- Keys matching `email`, `phone`, `full_name`, `contact_name`, `address`,
  `message`, `body`, `prompt`, `completion`, `ip_address`, `remote_addr`,
  `client_ip`, `forwarded_for` → `[REDACTED]`
- **Values** are scanned for IPv4/IPv6 patterns too, catching an address
  hand-assembled into a message string under an innocent key.
- Matching is by substring, deliberately. An exact key list is the version that
  fails: the field eventually arrives as `stripe_api_key` or `user_password`.
- Only the event dict is touched. Business objects are never mutated.
- The redaction value is constant. Length and prefix are not logged.

`event` is deliberately **not** exempt from value scanning: a stdlib call like
`logger.warning('failed for %s', ip)` renders the address into the message, and
the message becomes `event`. 66 modules still use stdlib logging; exempting
`event` would leave all of them as a hole. `timestamp` *is* exempt, because an
ISO timestamp contains `21:25:13`, which the IPv6 pattern matches.

## Allowed and prohibited fields

**Allowed:** request id, route name, HTTP method, status code, duration,
internal IDs, classifier version, outcome, stable reason codes, origin HMAC
fingerprint, booleans and counts.

**Prohibited:** email, full name, phone, address, raw IP, raw contact message,
form body, uploaded content, AI prompt or response, session cookie, auth token,
password, reset token, query string.

## Field types

Stable by contract: `status_code` int, `duration_ms` float,
`origin_available` bool, `reason_codes` list[str], `forwarded_hop_count` int.
Never `"200"` in one record and `200` in another.

## What is not logged, by construction

No query string (it can carry a token). The **route pattern** is recorded, not
the concrete URL. No request body, no cookies, no Authorization header, no user
agent.

## Rendering

`STRUCTLOG_JSON_LOGS` — defaults to on in production, off elsewhere. Chosen from
configuration, never sniffed from a hostname, so tests are deterministic. JSON
output carries no ANSI escapes.

## Exceptions

`request_failed` is logged with the exception type and traceback, then the
exception is **re-raised**. Django's own handling is unchanged: the client still
receives the generic 500, and a future error tracker still sees it. No request
body, cookies or headers are attached.

## Health checks

`/healthz` and `/health` do not log `request_started` / `request_completed` on
success. **A failing health check still logs** — the filter is on 2xx/3xx only.

## Database query logging

Not enabled, in any environment. `django.db.backends` remains pinned at INFO.

## Static assets

WhiteNoise serves static files before application middleware in production, so
they never reach this logger. No filtering needed.

## Gunicorn

Gunicorn's access log is left as-is. Application `request_completed` events
already carry route, status and duration with correlation; restructuring
Gunicorn's own logger would risk startup for a duplicate of what we now have.
Deferred deliberately.

## Adding an event

1. Add the name to `core/events.py`.
2. Emit with `structlog.get_logger(...)` and keyword fields — never an f-string.
3. Pass only allowed fields. Redaction is a backstop, not permission.
4. Add the event to the table above.

## Future Celery propagation

`bind_operation(operation, operation_id)` is the hook. A task binds its own id
on entry and calls `clear_operation()` in a `finally`. No Celery dependency is
introduced here.

## Future Sentry

`add_service_metadata` already emits `service`, `environment` and `release`
(from `RENDER_GIT_COMMIT`), which is what a Sentry SDK reads for release
attribution. `request_id` is in context on every event, and redaction runs
before rendering. Integration is a configuration step, not a redesign.

## Retention

Fingerprints appear in platform logs (Render retention) and in rate-limit cache
keys (expiring with their window, at most 24h). No raw address is written to a
log or, by this module, to any database column.

**Known debt, not addressed here:** `leads/models.py` (5 models) and `heating`
store raw client IPs in `GenericIPAddressField` columns indefinitely, and
`leads/admin.py` exposes them. `leads.views._is_rate_limited()` queries that
column, so it cannot simply be dropped. Tracked separately — it needs a
retention decision and a staged migration, not a logging change.
