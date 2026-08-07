"""
Deterministic classification of contact submissions, shared by the live path
and the batch commands so both agree by construction.

Why this module exists
----------------------
The first production rule treated "one contact name recurring" as a single weak
signal that needed corroboration before it could reject. The forensic review of
979 records disagreed: one name attached to 900+ *distinct, unrelated* email
addresses is not a weak hint, it is the whole case. Production put 948 records
into REVIEW; the forensic pass judged 965 of them bots. The gap was almost
entirely that one rule.

Two changes close it:

  1. Count DISTINCT EMAIL ADDRESSES per name, not records per name. Ten records
     from one person is ordinary; ten addresses behind one name is not.
  2. Give signals a strength. A single STRONG signal rejects on its own; MEDIUM
     signals need corroboration; WEAK signals never reject alone.

What this module will not do
----------------------------
No signal uses nationality, religion, ethnicity, language, geography or the
apparent origin of a name. None of the following is a signal on its own, and
none of them contributes to REJECT:

  - the mailbox provider (gmail, yahoo, outlook, hotmail, aol, web.de, …)
  - an unusual, non-English or single-word name
  - a short message
  - a country-code or non-.com domain

Those were all present in the genuine enquiries in this dataset as well as the
abusive ones, so they carry no information.
"""
from collections.abc import Iterable
from enum import Enum

from .fingerprint import normalise_email, normalise_text
from .heuristics import count_urls, email_is_valid, is_disposable, low_content_quality

# Bump when thresholds or signals change; recorded on every classified row so a
# later reviewer can tell which rules produced a decision.
CLASSIFIER_VERSION = '2026.08.06-2'


class Strength(str, Enum):
    STRONG = 'strong'     # decisive on its own
    MEDIUM = 'medium'     # two of these reject; one reviews
    WEAK = 'weak'         # never rejects alone; two review


# ── thresholds, all evidence-backed from the 979-record review ──────────────
# 965/979 records carried one name across 93 domains; the next most frequent
# name appeared twice. 25 distinct addresses is far above any plausible genuine
# pattern (a real person reusing a shared inbox tops out in the low single
# figures) and far below the observed abuse.
NAME_DISTINCT_EMAILS_STRONG = 25
NAME_DISTINCT_EMAILS_WEAK = 5

# A single message template sent from many addresses.
TEMPLATE_DISTINCT_EMAILS_STRONG = 10

# One actor spraying unrelated enquiry categories.
MULTI_TOPIC_THRESHOLD = 4

MAX_URLS = 2


SIGNALS = {
    # code: (strength, human explanation)
    'name_on_many_distinct_emails':   (Strength.STRONG, 'one contact name across many unrelated addresses'),
    'template_reused_across_emails':  (Strength.STRONG, 'one message template sent from many addresses'),
    'honeypot_filled':                (Strength.STRONG, 'hidden field completed'),
    'turnstile_failed':               (Strength.STRONG, 'captcha missing or invalid'),
    'form_too_fast':                  (Strength.STRONG, 'submitted faster than a human can complete'),
    'rate_limited':                   (Strength.STRONG, 'exceeded a submission rate limit'),

    'duplicate_submission':           (Strength.MEDIUM, 'identical submission already seen'),
    'multi_topic_single_actor':       (Strength.MEDIUM, 'same actor across many unrelated topics'),
    'excessive_urls':                 (Strength.MEDIUM, 'more links than an enquiry needs'),
    'invalid_email_format':           (Strength.MEDIUM, 'address is not a valid email'),

    'name_on_several_distinct_emails':(Strength.WEAK, 'name seen with a few different addresses'),
    'disposable_email_domain':        (Strength.WEAK, 'throwaway-inbox provider'),
    'low_content_quality':            (Strength.WEAK, 'almost no distinct wording'),
}


def message_skeleton(message: str | None) -> str:
    """
    Normalised shape of a message with variable parts removed, so a template
    with small substitutions collapses to one value. Digits, URLs and emails
    become placeholders; only the wording structure survives.
    """
    text = normalise_text(message)
    if not text:
        return ''
    tokens = []
    for token in text.split():
        if token.isdigit():
            tokens.append('#')
        elif len(token) > 20:
            tokens.append('~')
        else:
            tokens.append(token)
    return ' '.join(tokens[:40])


class Corpus:
    """
    Aggregate view of a set of submissions, so cross-record signals can be
    computed once instead of per record.

    `add()` accepts already-extracted fields, which keeps this usable both for
    a queryset of stored notifications and for a single live submission scored
    against history.
    """

    def __init__(self) -> None:
        self.emails_by_name: dict[str, set[str]] = {}
        self.emails_by_skeleton: dict[str, set[str]] = {}
        self.subjects_by_name: dict[str, set[str]] = {}
        self.fingerprint_counts: dict[str, int] = {}

    def add(self, *, name: str = '', email: str = '', subject: str = '',
            message: str = '', fingerprint: str = '') -> None:
        n = normalise_text(name)
        e = normalise_email(email)
        if n and e:
            self.emails_by_name.setdefault(n, set()).add(e)
        if n and subject:
            self.subjects_by_name.setdefault(n, set()).add(normalise_text(subject))
        sk = message_skeleton(message)
        if sk and e:
            self.emails_by_skeleton.setdefault(sk, set()).add(e)
        if fingerprint:
            self.fingerprint_counts[fingerprint] = self.fingerprint_counts.get(fingerprint, 0) + 1

    def distinct_emails_for_name(self, name: str) -> int:
        return len(self.emails_by_name.get(normalise_text(name), ()))

    def distinct_emails_for_skeleton(self, message: str) -> int:
        return len(self.emails_by_skeleton.get(message_skeleton(message), ()))

    def distinct_subjects_for_name(self, name: str) -> int:
        return len(self.subjects_by_name.get(normalise_text(name), ()))


def signals_for(*, name: str = '', email: str = '', subject: str = '',
                message: str = '', fingerprint: str = '',
                corpus: 'Corpus | None' = None,
                live_reasons: Iterable[str] = ()) -> list[str]:
    """
    Return the list of signal codes present. `live_reasons` carries codes the
    request-time screening already established (honeypot, turnstile, timing,
    rate limit), which batch analysis of stored records cannot recompute.
    """
    found = []

    for code in live_reasons:
        mapped = {
            'honeypot_filled': 'honeypot_filled',
            'form_too_fast': 'form_too_fast',
            'turnstile_missing': 'turnstile_failed',
            'turnstile_invalid': 'turnstile_failed',
            'turnstile_unavailable': 'turnstile_failed',
            'turnstile_not_configured': 'turnstile_failed',
            'rate_limit_ip': 'rate_limited',
            'rate_limit_email': 'rate_limited',
            'rate_limit_message': 'rate_limited',
            'rate_limit_global': 'rate_limited',
            'duplicate_submission': 'duplicate_submission',
        }.get(code)
        if mapped and mapped not in found:
            found.append(mapped)

    if email and not email_is_valid(email):
        found.append('invalid_email_format')
    if is_disposable(email):
        found.append('disposable_email_domain')
    if count_urls(message) > MAX_URLS:
        found.append('excessive_urls')
    if low_content_quality(message):
        found.append('low_content_quality')

    if corpus is not None:
        distinct = corpus.distinct_emails_for_name(name)
        if distinct >= NAME_DISTINCT_EMAILS_STRONG:
            found.append('name_on_many_distinct_emails')
        elif distinct >= NAME_DISTINCT_EMAILS_WEAK:
            found.append('name_on_several_distinct_emails')

        if corpus.distinct_emails_for_skeleton(message) >= TEMPLATE_DISTINCT_EMAILS_STRONG:
            found.append('template_reused_across_emails')

        if corpus.distinct_subjects_for_name(name) >= MULTI_TOPIC_THRESHOLD and distinct >= NAME_DISTINCT_EMAILS_WEAK:
            found.append('multi_topic_single_actor')

        if fingerprint and corpus.fingerprint_counts.get(fingerprint, 0) > 1:
            if 'duplicate_submission' not in found:
                found.append('duplicate_submission')

    # Stable order, no duplicates.
    return [c for c in SIGNALS if c in found]


def decide(found: list[str]) -> str:
    """
    Fold signals into ACCEPT / REVIEW / REJECT.

      REJECT  one STRONG signal, or two MEDIUM
      REVIEW  one MEDIUM, or two WEAK
      ACCEPT  otherwise

    Deliberately asymmetric: rejecting a real customer costs more than leaving
    a bot in REVIEW, so a single MEDIUM or WEAK signal never rejects.
    """
    strong = [c for c in found if SIGNALS[c][0] is Strength.STRONG]
    medium = [c for c in found if SIGNALS[c][0] is Strength.MEDIUM]
    weak = [c for c in found if SIGNALS[c][0] is Strength.WEAK]

    if strong or len(medium) >= 2:
        return 'REJECT'
    if medium or len(weak) >= 2:
        return 'REVIEW'
    return 'ACCEPT'


def classify(*, name: str = '', email: str = '', subject: str = '',
             message: str = '', fingerprint: str = '',
             corpus: 'Corpus | None' = None,
             live_reasons: Iterable[str] = ()) -> tuple[str, list[str]]:
    """Returns (decision, reason_codes). Reason codes never contain message text."""
    found = signals_for(name=name, email=email, subject=subject, message=message,
                        fingerprint=fingerprint, corpus=corpus, live_reasons=live_reasons)
    return decide(found), found
