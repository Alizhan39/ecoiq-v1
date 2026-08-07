"""
Stable log event names.

An event name is an identifier, not prose. `logger.info(events.REQUEST_FAILED)`
stays searchable when someone rewords the sentence around it, and a dashboard
built on `event = "contact_submission_rejected"` does not break because a
message gained a comma.

Only events actually emitted today are listed. Adding a name here without a
call site would describe a subsystem that does not exist.
"""

# ── HTTP request lifecycle ───────────────────────────────────────────────────
REQUEST_STARTED = 'request_started'
REQUEST_COMPLETED = 'request_completed'
REQUEST_FAILED = 'request_failed'

# ── abuse screening on public forms ──────────────────────────────────────────
CONTACT_SUBMISSION_ACCEPTED = 'contact_submission_accepted'
CONTACT_SUBMISSION_REVIEWED = 'contact_submission_reviewed'
CONTACT_SUBMISSION_REJECTED = 'contact_submission_rejected'

# ── rate limiting ────────────────────────────────────────────────────────────
# INFO, not WARNING: a limiter turning traffic away is the system working. A
# WARNING per blocked request would mean an attack floods the log with warnings
# at exactly the moment the log needs to stay readable. Reserve WARNING for the
# limiter itself being unhealthy.
RATE_LIMIT_APPLIED = 'rate_limit_applied'
RATE_LIMIT_BACKEND_UNAVAILABLE = 'rate_limit_backend_unavailable'

# ── origin resolution ────────────────────────────────────────────────────────
ORIGIN_RESOLUTION_FAILED = 'origin_resolution_failed'
