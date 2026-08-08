# Sentry error monitoring

Disabled unless `SENTRY_DSN` is set. **No DSN is configured, and no event has
ever been sent.** Activation is a separate, deliberate step.

## Why a Sentry-specific privacy layer exists

The structured logging pipeline scrubs what goes into a *log line*. Sentry does
not read log lines — it captures exceptions and request state directly from the
running process. Measured against **sentry-sdk 2.66.1**, the defaults it would
otherwise use are:

| Option | SDK default | Why that matters here | Our value |
|---|---|---|---|
| `include_local_variables` | **`True`** | frame locals hold contact messages, AI prompts, API keys, DB credentials | `False` |
| `max_request_body_size` | **`'medium'`** | sends request bodies, form data, JSON | `'never'` |
| `send_default_pii` | `None` | changed across major versions; too important to inherit | `False` |
| `traces_sample_rate` | `None` | — | `0.0` unless configured |
| `profiles_sample_rate` | `None` | — | `0.0` explicitly |

DjangoIntegration additionally attaches "HTTP method, URL, headers, form data,
JSON payloads" to every event. None of that passes through structlog, so none of
it would have been redacted by the logging work.

## Defence layers

1. **SDK options** — stop data being collected at all. The only layer that
   cannot be defeated by a payload shape nobody anticipated, so it does as much
   as possible.
2. **`EventScrubber(recursive=True)`** — the SDK's own key-based scrubber,
   widened with EcoIQ's `SENSITIVE_KEY_PARTS` and `PERSONAL_KEY_PARTS`.
3. **`before_send`** — our recursive pass over the finished event.
4. **`before_breadcrumb`** — the same pass per breadcrumb.

Layers 2–4 share the key lists with `core/logging_setup.py`, so Sentry and the
logs cannot drift apart on what counts as sensitive.

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `SENTRY_DSN` | *(unset)* | Absent → disabled cleanly. **Never committed.** |
| `SENTRY_ENABLED` | *(unset)* | `false`/`0`/`no` disables even with a DSN present |
| `SENTRY_ENVIRONMENT` | `production` in prod, `development` otherwise | Never defaults to `production` locally |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0` | Rejected unless `0.0 ≤ x ≤ 1.0` |

A malformed rate raises `SentryConfigurationError`. It is never read as `1.0` —
that would bill for every transaction, which is exactly the accident worth
failing loudly over.

A missing DSN does **not** fail startup. A deployment without error monitoring
is a normal state (local, CI, a fresh environment) and refusing to boot over it
would be worse than the gap.

## What is sent

`request.method` · route-pattern URL without query string · non-credential
headers · exception **type** · stack frames with file/function/line · breadcrumbs
from INFO upward · `tags.request_id` · `tags.route` · `contexts.ecoiq`
(request_id, route, safe origin fields) · `environment` · `release` ·
`user.id` only.

## Integrations

**Only `DjangoIntegration` and `LoggingIntegration`.** `auto_enabling_integrations`
is off.

Left on, the SDK enables whatever it finds installed — a captured event listed
`celery`, `fastapi`, `flask`, `httpx`, `langchain`, `langgraph`, `redis`,
`sqlalchemy` and `starlette`. `langchain` is the one that matters: its
instrumentation exists to record prompts and completions, which is exactly the
data this application must never send. `redis` and `httpx` add breadcrumbs that
can carry URLs and keys. Disabling the lot is smaller and more honest than
auditing nine integrations nobody asked for.

## Command-line arguments

`extra['sys.argv']` is attached to every event. This repository has management
commands that take secrets as arguments (`create_demo_user --password …`), and
neither the key rules (the key is `sys.argv`) nor the value rules (a password
has no shape) catch them — verified leaking before `scrub_argv` existed.

`argv[0]` and `argv[1]` are kept so the failing command is identifiable;
everything after is redacted as a unit.

## The `message` exemption

`message` is in `PERSONAL_KEY_PARTS` so `contact_message` is caught. Applied to
Sentry's own top-level `message` field it turned **every breadcrumb into
`[REDACTED]`** — a trail that says nothing.

The exact key `message` is therefore exempt from *key* redaction but still
*value*-scrubbed, so `rate_limit_applied` survives while an address or email
inside a message does not. Any other key containing "message" is still redacted.

Residual risk, stated plainly: a breadcrumb message can still contain arbitrary
text a developer chose to log. That is the same exposure the log line already
has, and the mitigation is the logging policy — not double-redaction that
destroys the trail.

## Source context

Sentry captures `pre_context` / `context_line` / `post_context` — the **source
lines** around each frame. That is code, not runtime data, and it is the same
tradeoff the logging pipeline already accepts for tracebacks. A secret only
appears there if it is hardcoded in the source, which the Gitleaks gate blocks
separately.

## What is never sent

`send_default_pii=False` · raw IP (any form) · email · username · phone ·
cookies · `Authorization` · `X-CSRFToken` · `X-Forwarded-For` ·
`CF-Connecting-IP` · request body / form data / JSON payload · query string ·
arbitrary exception message text · **stack-frame locals** · AI prompts or
completions · database URLs.

## Exception message policy

`exception.values[].value` is replaced with `[REDACTED]`; the type and the full
stack are kept. Same decision, same reason, as the logging pipeline: that string
is arbitrary text nobody vetted. `ValueError` plus `File …, line 412, in submit`
identifies the defect; the message could be a provider response or a token
someone interpolated.

## Request correlation

One id, three places: the `X-Request-ID` response header, the `request_id` log
field, and Sentry's `tags.request_id` (also mirrored in `contexts.ecoiq`). Bound
by the existing `RequestContextMiddleware` — no second correlation id is
generated. It is a **tag** because tags are searchable and contexts are not, and
it is **not** in the event title, which would fragment one issue per request.

## Breadcrumbs and duplicate events

`LoggingIntegration(level=INFO, event_level=ERROR)`. Breadcrumbs from INFO up;
only ERROR becomes an event. `request_started` and `request_completed` are
dropped in `before_breadcrumb` — they are the highest-volume events the app
logs and would evict everything useful from the trail.

One unhandled exception produces **exactly one** event. Asserted by test:
DjangoIntegration and LoggingIntegration both observe the same fault, and this
level split is what stops both filing it.

## Ignored errors

`Http404`, `PermissionDenied`, `SuspiciousOperation`. Deliberately short — a
long ignore list is how a real regression gets filtered out. Rate limits are not
ignored because they never reach ERROR: `rate_limit_applied` logs at INFO.

## Tracing and profiling

Tracing defaults to **0.0**. Recommended first production value once error
monitoring is proven: **0.01–0.05**, after a traffic and cost review. Never
hardcode `1.0`.

Profiling is **off** (`profiles_sample_rate=0.0`) and stays off. It samples
stacks continuously, which is a different exposure from error frames, and a
separate cost decision.

## Transactions and spans

`transaction_style='url'` gives the route pattern (`/companies/<slug>/`), not the
concrete URL — low cardinality, no identifiers in the title. `middleware_spans`,
`signals_spans` and `cache_spans` are off: noise before there is any tracing to
read. DB spans carry no bound parameter values, and SQL logging remains off.

## Tests

`core/tests_sentry_privacy.py` installs a **fake transport** capturing payloads
at the wire boundary — the last point before bytes would leave the process. The
DSN is a `.invalid` host that cannot resolve. Testing `before_send` alone would
prove only that `before_send` works; it says nothing about a field an
integration adds afterwards.

Nine synthetic markers are spread across headers, cookies, query string, body,
exception message, breadcrumbs, nested extras, user context and an AI-shaped
context, then asserted absent from `json.dumps(event)`.

## Production activation — not yet performed

1. Create the Sentry project.
2. Copy the DSN.
3. Add `SENTRY_DSN` as a Render **secret** (never a committed value).
4. Set `SENTRY_ENVIRONMENT=production`.
5. Leave `SENTRY_TRACES_SAMPLE_RATE` unset (0.0).
6. Deploy; confirm `settings.SENTRY_ACTIVE` is `True`.
7. Send one controlled test event from a Render one-off job.
8. Inspect that event in the UI and confirm redaction against this document.
9. Only then consider tracing at 0.01–0.05.
10. Configure alerts.

**Rollback:** remove `SENTRY_DSN`, or set `SENTRY_ENABLED=false`. The SDK goes
inert; nothing else changes.

## Suggested initial alerts

New issue · regression on a resolved issue · error-rate spike above baseline ·
the same 500 recurring within a short window. Not per-event alerts — that is
alert fatigue, and the first thing people mute.

## Cost controls

Errors sampled at 1.0 (Sentry's own quotas handle volume; sampling errors loses
the one occurrence someone needs). Tracing 0.0. Profiling 0.0. Lifecycle
breadcrumbs dropped. Expected 404/403 not filed.
