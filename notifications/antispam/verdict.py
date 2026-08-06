"""Verdict types and reason codes for public-submission screening."""
from dataclasses import dataclass, field
from enum import Enum


class Decision(str, Enum):
    """
    ACCEPT  — behave exactly as before: notification, email, downstream work.
    REVIEW  — quarantine. A record is kept for a human, but the commercial team
              is not alerted and no downstream work runs.
    REJECT  — nothing is created and nothing downstream runs.
    """
    ACCEPT = 'accept'
    REVIEW = 'review'
    REJECT = 'reject'


class Reason(str, Enum):
    """Explicit, stable reason codes. Never free text, so they can be counted."""
    HONEYPOT_FILLED = 'honeypot_filled'
    FORM_TOO_FAST = 'form_too_fast'
    FORM_EXPIRED = 'form_expired'
    FORM_TIMING_TAMPERED = 'form_timing_tampered'
    TURNSTILE_MISSING = 'turnstile_missing'
    TURNSTILE_INVALID = 'turnstile_invalid'
    TURNSTILE_UNAVAILABLE = 'turnstile_unavailable'
    TURNSTILE_NOT_CONFIGURED = 'turnstile_not_configured'
    RATE_LIMIT_IP = 'rate_limit_ip'
    RATE_LIMIT_EMAIL = 'rate_limit_email'
    RATE_LIMIT_MESSAGE = 'rate_limit_message'
    RATE_LIMIT_GLOBAL = 'rate_limit_global'
    DUPLICATE_SUBMISSION = 'duplicate_submission'
    EXCESSIVE_URLS = 'excessive_urls'
    NAME_REUSED_ACROSS_EMAILS = 'name_reused_across_emails'
    LOW_CONTENT_QUALITY = 'low_content_quality'
    DISPOSABLE_EMAIL_DOMAIN = 'disposable_email_domain'
    INVALID_EMAIL_FORMAT = 'invalid_email_format'
    INVALID_FIELD_LENGTH = 'invalid_field_length'


# Reasons that mean "this is not a person filling in a form".
HARD_REJECT = frozenset({
    Reason.HONEYPOT_FILLED,
    Reason.TURNSTILE_MISSING,
    Reason.TURNSTILE_INVALID,
    Reason.TURNSTILE_UNAVAILABLE,
    Reason.TURNSTILE_NOT_CONFIGURED,
    Reason.RATE_LIMIT_IP,
    Reason.RATE_LIMIT_EMAIL,
    Reason.RATE_LIMIT_MESSAGE,
    Reason.RATE_LIMIT_GLOBAL,
    Reason.DUPLICATE_SUBMISSION,
    Reason.INVALID_EMAIL_FORMAT,
    Reason.INVALID_FIELD_LENGTH,
    Reason.FORM_TIMING_TAMPERED,
})

# Reasons that are suspicious but survivable — a real person can trip these.
SOFT_REVIEW = frozenset({
    Reason.FORM_TOO_FAST,
    Reason.FORM_EXPIRED,
    Reason.EXCESSIVE_URLS,
    Reason.NAME_REUSED_ACROSS_EMAILS,
    Reason.LOW_CONTENT_QUALITY,
    Reason.DISPOSABLE_EMAIL_DOMAIN,
})

# HTTP status a caller should use for each decision.
HTTP_STATUS = {
    Reason.RATE_LIMIT_IP: 429,
    Reason.RATE_LIMIT_EMAIL: 429,
    Reason.RATE_LIMIT_MESSAGE: 429,
    Reason.RATE_LIMIT_GLOBAL: 429,
}


@dataclass
class Verdict:
    decision: Decision
    reasons: list = field(default_factory=list)
    fingerprint: str = ''
    score: int = 0

    @property
    def accepted(self):
        return self.decision is Decision.ACCEPT

    @property
    def rejected(self):
        return self.decision is Decision.REJECT

    @property
    def quarantined(self):
        return self.decision is Decision.REVIEW

    @property
    def reason_codes(self):
        return [r.value for r in self.reasons]

    @property
    def http_status(self):
        """429 for rate limits, otherwise 200 — a bot learns nothing from it."""
        for r in self.reasons:
            if r in HTTP_STATUS:
                return HTTP_STATUS[r]
        return 200

    def add(self, reason):
        if reason not in self.reasons:
            self.reasons.append(reason)
        return self

    def resolve(self):
        """Fold the collected reasons into a final decision."""
        if any(r in HARD_REJECT for r in self.reasons):
            self.decision = Decision.REJECT
        elif len(self.reasons) >= 2:
            # Two independent soft signals together is enough to quarantine.
            self.decision = Decision.REVIEW
        elif self.reasons:
            self.decision = Decision.REVIEW
        else:
            self.decision = Decision.ACCEPT
        self.score = len(self.reasons)
        return self
