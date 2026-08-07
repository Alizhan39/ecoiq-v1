"""
Deterministic content signals.

Every check here is mechanical and explainable. None of them looks at
nationality, religion, ethnicity, or the apparent origin of a person's name,
and none treats a mainstream free-mail provider as suspicious on its own — the
live abuse and the genuine enquiries both used gmail, yahoo and hotmail.
"""
import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .fingerprint import email_domain, normalise_text

_URL = re.compile(r'(https?://|www\.)', re.I)
_BBCODE = re.compile(r'\[(url|link)[=\]]', re.I)

# Throwaway-inbox providers. Deliberately short and specific: these exist to be
# anonymous and disposable. Mainstream consumer providers are NOT listed.
DISPOSABLE_DOMAINS = frozenset({
    'mailinator.com', 'guerrillamail.com', 'guerrillamail.info', '10minutemail.com',
    'temp-mail.org', 'tempmail.com', 'throwawaymail.com', 'yopmail.com',
    'sharklasers.com', 'trashmail.com', 'getnada.com', 'dispostable.com',
    'maildrop.cc', 'fakeinbox.com', 'mailnesia.com', 'spam4.me',
})

MAX_URLS = 2
MAX_NAME_LENGTH = 200
MAX_SUBJECT_LENGTH = 200
MIN_MESSAGE_LENGTH = 20
MAX_MESSAGE_LENGTH = 4000


def count_urls(message: str | None) -> int:
    return len(_URL.findall(message or '')) + len(_BBCODE.findall(message or ''))


def email_is_valid(email: str | None) -> bool:
    try:
        validate_email((email or '').strip())
        return True
    except ValidationError:
        return False


def is_disposable(email: str | None) -> bool:
    return email_domain(email) in DISPOSABLE_DOMAINS


def field_lengths_ok(*, name: str = '', subject: str = '', message: str = '') -> bool:
    if len(name or '') > MAX_NAME_LENGTH:
        return False
    if len(subject or '') > MAX_SUBJECT_LENGTH:
        return False
    length = len(message or '')
    return MIN_MESSAGE_LENGTH <= length <= MAX_MESSAGE_LENGTH


def low_content_quality(message: str | None) -> bool:
    """
    True when the body carries almost no information: very few distinct words,
    or one token repeated. Length alone is never the signal — a short, genuine
    enquiry is fine.
    """
    text = normalise_text(message)
    if not text:
        return True
    words = text.split()
    if len(words) < 4:
        return True
    unique = len(set(words))
    if unique <= 2:
        return True
    # A wall of one repeated token.
    return unique / len(words) < 0.2


def distinct_emails_for_name(name: str, *, lookback_days: int = 30) -> int:
    """
    How many different addresses have used this contact name recently.

    The strongest signal from the live incident. Keyed on the name only — it
    says nothing about what the name is, only that it recurs with different
    senders. Returns a count so the caller can distinguish "a handful", which a
    real person or a shared team inbox can produce, from "hundreds", which they
    cannot.
    """
    from datetime import timedelta

    from django.utils import timezone

    from notifications.models import AdminNotification

    if not normalise_text(name):
        return 0
    cutoff = timezone.now() - timedelta(days=lookback_days)
    return (
        AdminNotification.objects
        .filter(created_at__gte=cutoff)
        .exclude(contact_email='')
        .filter(contact_name__iexact=(name or '').strip())
        .values('contact_email').distinct().count()
    )


def name_reused_across_emails(name: str, email: str | None = None, *,
                              lookback_days: int = 30, threshold: int = 5) -> bool:
    """Boolean form of `distinct_emails_for_name`, kept for existing callers."""
    return distinct_emails_for_name(name, lookback_days=lookback_days) >= threshold
