"""
The single screening entry point.

Cheap local checks run first; Cloudflare is contacted last and only if the
submission is still viable, so an obvious bot costs no network call.
"""
import logging

from django.core.cache import cache
from django.http import HttpRequest

from . import classify, heuristics, ratelimit, timing, turnstile
from .fingerprint import submission_fingerprint
from .verdict import Decision, Reason, Verdict

logger = logging.getLogger(__name__)

DUPLICATE_TTL = 60 * 60 * 24
DUPLICATE_PREFIX = 'antispam:fp:'


def _client_ip(request: HttpRequest | None) -> str:
    """Trusted client address. See core.client_origin for why not XFF[0]."""
    from core.client_origin import client_ip
    return client_ip(request)


def evaluate(*, request: HttpRequest | None = None, form: str = 'contact',
             name: str = '', email: str = '', subject: str = '',
             message: str = '', honeypot: str = '', form_token: str = '',
             turnstile_token: str = '', check_duplicates: bool = True) -> Verdict:
    """
    Screen one public submission and return a Verdict.

    Side effects are limited to this module's own rate-limit and duplicate
    counters. Nothing is written to the notification table, no email is sent,
    no task is dispatched — the caller decides, based on the verdict.
    """
    verdict = Verdict(decision=Decision.ACCEPT)
    ip = _client_ip(request)

    fingerprint = submission_fingerprint(
        email=email, name=name, subject=subject, message=message, form=form)
    verdict.fingerprint = fingerprint

    # ── 1. honeypot and timing ───────────────────────────────────────────
    if (honeypot or '').strip():
        verdict.add(Reason.HONEYPOT_FILLED)

    ok, code = timing.check(form_token)
    if not ok:
        verdict.add({
            'too_fast': Reason.FORM_TOO_FAST,
            'expired': Reason.FORM_EXPIRED,
            'tampered': Reason.FORM_TIMING_TAMPERED,
        }.get(code, Reason.FORM_TIMING_TAMPERED))

    # ── 2. field shape ───────────────────────────────────────────────────
    if not heuristics.email_is_valid(email):
        verdict.add(Reason.INVALID_EMAIL_FORMAT)
    if not heuristics.field_lengths_ok(name=name, subject=subject, message=message):
        verdict.add(Reason.INVALID_FIELD_LENGTH)

    # ── 3. duplicate suppression ─────────────────────────────────────────
    # cache.add is atomic, so two simultaneous identical posts cannot both win.
    if check_duplicates:
        try:
            first = cache.add(DUPLICATE_PREFIX + fingerprint, 1, DUPLICATE_TTL)
            if not first:
                verdict.add(Reason.DUPLICATE_SUBMISSION)
        except Exception as exc:
            logger.warning('antispam_duplicate_check_unavailable',
                           extra={'error': type(exc).__name__})

    # ── 4. rate limits ───────────────────────────────────────────────────
    for scope in ratelimit.check(ip=ip, email=email, message=message, form=form):
        verdict.add({
            'ip': Reason.RATE_LIMIT_IP,
            'email': Reason.RATE_LIMIT_EMAIL,
            'message': Reason.RATE_LIMIT_MESSAGE,
            'global': Reason.RATE_LIMIT_GLOBAL,
        }[scope])

    # ── 5. content heuristics ────────────────────────────────────────────
    if heuristics.count_urls(message) > heuristics.MAX_URLS:
        verdict.add(Reason.EXCESSIVE_URLS)
    if heuristics.is_disposable(email):
        verdict.add(Reason.DISPOSABLE_EMAIL_DOMAIN)
    if heuristics.low_content_quality(message):
        verdict.add(Reason.LOW_CONTENT_QUALITY)
    # One name across a handful of addresses is a soft hint; one name across
    # dozens is decisive on its own. Splitting the two is what closes the gap
    # between this path and the forensic review of the live incident — see
    # notifications/antispam/classify.py.
    try:
        distinct = heuristics.distinct_emails_for_name(name)
        if distinct >= classify.NAME_DISTINCT_EMAILS_STRONG:
            verdict.add(Reason.NAME_ON_MANY_DISTINCT_EMAILS)
        elif distinct >= classify.NAME_DISTINCT_EMAILS_WEAK:
            verdict.add(Reason.NAME_REUSED_ACROSS_EMAILS)
    except Exception as exc:
        logger.warning('antispam_name_reuse_check_failed',
                       extra={'error': type(exc).__name__})

    # ── 6. Turnstile — network, and only if still viable ─────────────────
    if not verdict.reasons or all(r not in _HARD for r in verdict.reasons):
        result = turnstile.verify(
            turnstile_token,
            remote_ip=ip or None,
            expected_action=form,
            expected_hostname=(request.get_host().split(':')[0] if request else None),
        )
        if not result.ok:
            verdict.add({
                'missing': Reason.TURNSTILE_MISSING,
                'invalid': Reason.TURNSTILE_INVALID,
                'replayed': Reason.TURNSTILE_INVALID,
                'action_mismatch': Reason.TURNSTILE_INVALID,
                'hostname_mismatch': Reason.TURNSTILE_INVALID,
                'unavailable': Reason.TURNSTILE_UNAVAILABLE,
                'not_configured': Reason.TURNSTILE_NOT_CONFIGURED,
            }.get(result.code, Reason.TURNSTILE_INVALID))

    return verdict.resolve()


from .verdict import HARD_REJECT as _HARD  # noqa: E402  (used above)
