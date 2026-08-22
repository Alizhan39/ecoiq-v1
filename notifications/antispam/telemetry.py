"""
notifications/antispam/telemetry.py — the structured record of one screening.

WHY THIS MOVED HERE
-------------------
It used to be `core.views._log_submission`, a private helper beside the
server-rendered contact form. When that form became React and the endpoint
became `/api/v2/contact/`, the new endpoint screened submissions correctly and
recorded NOTHING — so `monitoring.record()` stopped counting, and with it the
rejection-spike and fingerprint-flood alerts stopped firing. Silently: no error,
no failing test, just an alert that would never arrive again.

Telemetry that lives next to one caller is telemetry that gets left behind when
that caller is replaced. It lives with the screening now, so any endpoint that
screens can record, and there is one implementation to keep honest.

WHAT IS NEVER RECORDED
----------------------
The message, the address, the name, the subject, or a Turnstile token. Every
field emitted is an outcome, a deterministic reason code, or a structural fact.
`safe_origin_context` supplies the single canonical keyed fingerprint for the
client address — a second, independently-keyed hash computed here could not be
correlated with it and neither could be rotated without missing the other.

The logger name is part of the observable contract: notifications/tests_antispam
asserts on it, and renaming it buys nothing but a broken privacy test.
"""
from __future__ import annotations

import structlog

_LOGGER = 'notifications.antispam'


def log_submission(event: str, verdict, request, *, form: str = 'contact') -> None:
    """Record one screening outcome, and feed the alert counters."""
    from core.client_origin import safe_origin_context

    structlog.get_logger(_LOGGER).info(
        event,
        form=form,
        decision=verdict.decision.value,
        reason_codes=verdict.reason_codes,
        submission_fingerprint=verdict.fingerprint[:12],
        **safe_origin_context(request),
    )

    from notifications.antispam import monitoring
    monitoring.record(event, fingerprint=verdict.fingerprint, form=form)
