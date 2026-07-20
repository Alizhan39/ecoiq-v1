"""
company_intelligence/services/freshness.py — feat/company-evidence-
ingestion (PR 10): "a company must not display an old screening as if
permanently valid."

Deliberately NOT a stored field: staleness is a function of the current
date minus a fixed timestamp, so storing it would itself go stale the
moment it was written. Computed at read time, every time.

STALE_AFTER_DAYS is an explicit, documented policy constant — never a
hidden rule. 180 days (~2 fiscal quarters) matches this repo's existing
harvester.verification.freshness() horizon philosophy (a documented decay
window, not an arbitrary cliff) while being short enough that a screening
genuinely needs a real refresh before being relied upon for anything
company-specific.
"""
import datetime

from django.utils import timezone

STALE_AFTER_DAYS = 180


def screening_freshness(screen):
    """
    screen: a company_intelligence.models.CompanyShariahScreen or None.
    Returns {'is_stale': bool, 'reason': str, 'screened_days_ago': int|None,
    'financial_data_days_ago': int|None, 'label': str}.

    Staleness is driven by the OLDER of two real dates: when the screen was
    run, and how old its financial_facts.as_of_date is (a screen run
    yesterday against a 3-year-old balance sheet is still stale) — never
    just the screening timestamp alone.
    """
    if screen is None:
        return {
            'is_stale': None, 'reason': 'No screening exists yet.',
            'screened_days_ago': None, 'financial_data_days_ago': None,
            'label': 'Not Screened',
        }

    now = timezone.now()
    screened_days_ago = (now - screen.screened_at).days

    financial_data_days_ago = None
    if screen.financial_facts is not None and screen.financial_facts.as_of_date is not None:
        financial_data_days_ago = (now.date() - screen.financial_facts.as_of_date).days

    reasons = []
    if screened_days_ago > STALE_AFTER_DAYS:
        reasons.append(f'Screening was run {screened_days_ago} days ago (>{STALE_AFTER_DAYS}-day policy window).')
    if financial_data_days_ago is not None and financial_data_days_ago > STALE_AFTER_DAYS:
        reasons.append(
            f'Underlying financial data is {financial_data_days_ago} days old (>{STALE_AFTER_DAYS}-day policy window).'
        )

    is_stale = bool(reasons)
    return {
        'is_stale': is_stale,
        'reason': ' '.join(reasons) if reasons else 'Within the freshness policy window.',
        'screened_days_ago': screened_days_ago,
        'financial_data_days_ago': financial_data_days_ago,
        'label': 'Screening Requires Refresh' if is_stale else 'Current',
    }
