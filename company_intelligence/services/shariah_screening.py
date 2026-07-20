"""
company_intelligence/services/shariah_screening.py — feat/company-halal-
intelligence (PR 9): deterministic, methodology-versioned Shariah
eligibility screening. Two independent screens (business activity,
financial ratio), never collapsed into one number, combined only into an
honest overall_result that is FAIL if either screen fails and never PASS
unless both screens actually pass.

This is a screening PROXY under a named, documented methodology — never a
religious ruling, never a fatwa, never "Islamically approved". Every
result is labelled "Screened according to [methodology name] v[version]".

Distinct from qdf.DecisionAssessment's existing "halal" question (a coarse
ethics-proxy derived from controversy/ethics signals on CompanyProfile,
answering a different, broader question — see that app's own docstring).
This module performs the sector/keyword + balance-sheet-ratio screen a
real Shariah eligibility index would use; it does not read or write
anything in the qdf app.

No financial value is ever silently treated as zero: a missing
CompanyFinancialFacts field is recorded as a missing input and excluded
from ratio calculation, never defaulted.
"""
from company_intelligence.models import CompanyShariahScreen

RESULT_ORDER = ['fail', 'not_screened', 'insufficient_data', 'conditional', 'pass']


def _text_haystack(company_profile):
    league_company = company_profile.company
    return f'{league_company.name} {league_company.description or ""}'.lower()


def run_business_activity_screen(company_profile, methodology):
    """
    Matches the company's own free-text name/description against the
    methodology's own configured keyword rules — never a hardcoded
    denylist inside this function. `league.Company.sector`'s fixed choices
    are all industrial categories (oil_gas, mining, energy, ...); none of
    them are Shariah-prohibited categories, so this screen is
    keyword-based against real company text, the only structured signal
    actually available for this in the current data model (documented
    limitation — see PR9 report's "known limitations").

    Returns {'result', 'reason', 'evidence_refs', 'matched_categories'}.
    """
    haystack = _text_haystack(company_profile)
    rules = methodology.business_activity_rules or []

    blocked_matches = []
    restricted_matches = []
    for rule in rules:
        keywords = rule.get('keywords', [])
        if any(kw.lower() in haystack for kw in keywords):
            if rule.get('status') == 'blocked':
                blocked_matches.append(rule)
            elif rule.get('status') == 'restricted':
                restricted_matches.append(rule)

    if blocked_matches:
        labels = ', '.join(r['label'] for r in blocked_matches)
        return {
            'result': 'fail',
            'reason': f'Business activity screen matched blocked categories: {labels}.',
            'evidence_refs': [],
            'matched_categories': [r['category'] for r in blocked_matches],
        }

    if restricted_matches:
        labels = ', '.join(r['label'] for r in restricted_matches)
        return {
            'result': 'conditional',
            'reason': (
                f'Business activity screen matched restricted categories requiring revenue-share review: '
                f'{labels}. This methodology cannot compute segment revenue share from currently available '
                f'data, so this is reported as conditional pending human review, not passed by default.'
            ),
            'evidence_refs': [],
            'matched_categories': [r['category'] for r in restricted_matches],
        }

    league_company = company_profile.company
    has_real_description = bool((league_company.description or '').strip())
    if not has_real_description:
        return {
            'result': 'insufficient_data',
            'reason': 'No business activity description is recorded for this company — the screen cannot '
                       'confirm the absence of prohibited activity from silence alone.',
            'evidence_refs': [],
            'matched_categories': [],
        }

    return {
        'result': 'pass',
        'reason': 'No blocked or restricted business-activity categories matched under this methodology.',
        'evidence_refs': [],
        'matched_categories': [],
    }


def _ratio(numerator, denominator):
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(numerator / denominator, 4)


def run_financial_ratio_screen(financial_facts, methodology):
    """
    Computes each configured ratio ONLY when both its numerator and
    denominator are real (non-None) values — a missing field is recorded
    in `missing_inputs`, never treated as zero. Returns
    {'result', 'detail': {'ratios', 'thresholds', 'missing_inputs', 'evaluated'}}.
    """
    thresholds = methodology.financial_ratio_rules or {}
    detail = {'ratios': {}, 'thresholds': thresholds, 'missing_inputs': [], 'evaluated': []}

    if financial_facts is None:
        detail['missing_inputs'] = ['financial_facts']
        return {'result': 'insufficient_data', 'detail': detail}

    checks = [
        ('debt_to_market_cap', financial_facts.total_debt_usd, financial_facts.market_cap_usd,
         'total_debt_usd', 'market_cap_usd', 'debt_to_market_cap_max'),
        ('interest_bearing_securities_to_market_cap', financial_facts.interest_bearing_securities_usd,
         financial_facts.market_cap_usd, 'interest_bearing_securities_usd', 'market_cap_usd',
         'interest_bearing_securities_to_market_cap_max'),
        ('non_permissible_income_to_revenue', financial_facts.non_permissible_income_usd,
         financial_facts.revenue_usd, 'non_permissible_income_usd', 'revenue_usd',
         'non_permissible_income_to_revenue_max'),
    ]

    for ratio_key, numerator, denominator, num_field, den_field, threshold_key in checks:
        if numerator is None:
            detail['missing_inputs'].append(num_field)
            continue
        if denominator is None:
            detail['missing_inputs'].append(den_field)
            continue
        ratio = _ratio(numerator, denominator)
        detail['ratios'][ratio_key] = ratio
        threshold = thresholds.get(threshold_key)
        if threshold is None:
            continue
        passed = ratio <= threshold
        detail['evaluated'].append({'ratio': ratio_key, 'value': ratio, 'threshold': threshold, 'passed': passed})

    if not detail['evaluated']:
        return {'result': 'insufficient_data', 'detail': detail}
    if any(not e['passed'] for e in detail['evaluated']):
        result = 'fail'
    elif detail['missing_inputs']:
        result = 'conditional'
    else:
        result = 'pass'
    return {'result': result, 'detail': detail}


def _combine(business_result, financial_result):
    if business_result == 'fail' or financial_result == 'fail':
        return 'fail'
    if business_result == 'not_screened' or financial_result == 'not_screened':
        return 'not_screened'
    if business_result == 'insufficient_data' or financial_result == 'insufficient_data':
        return 'insufficient_data'
    if business_result == 'conditional' or financial_result == 'conditional':
        return 'conditional'
    return 'pass'


def _completeness_pct(business_outcome, financial_outcome):
    """Honest completeness: how much of the possible screening inputs were
    actually available, not whether the result was favourable."""
    business_pts = 0 if business_outcome['result'] == 'insufficient_data' else 1
    financial_detail = financial_outcome['detail']
    possible_ratios = 3
    missing = len(financial_detail.get('missing_inputs', []))
    evaluated = len(financial_detail.get('evaluated', []))
    financial_pts = evaluated / possible_ratios if possible_ratios else 0
    return round(((business_pts + financial_pts) / 2) * 100, 1)


def run_shariah_screen(company_profile, methodology, financial_facts=None, actor=None, is_demo=False):
    """
    Orchestrates both screens and persists exactly one new
    CompanyShariahScreen row — never mutates a prior screen (each run is
    its own dated record, so history is preserved). review_status starts
    at 'automated_preliminary'; only an explicit separate human action
    (not this function) ever upgrades it.
    """
    business_outcome = run_business_activity_screen(company_profile, methodology)
    financial_outcome = run_financial_ratio_screen(financial_facts, methodology)
    overall = _combine(business_outcome['result'], financial_outcome['result'])

    return CompanyShariahScreen.objects.create(
        company=company_profile,
        methodology=methodology,
        financial_facts=financial_facts,
        business_activity_result=business_outcome['result'],
        business_activity_reason=business_outcome['reason'],
        business_activity_evidence_refs=business_outcome['evidence_refs'],
        financial_ratio_result=financial_outcome['result'],
        financial_ratio_detail=financial_outcome['detail'],
        overall_result=overall,
        data_completeness_pct=_completeness_pct(business_outcome, financial_outcome),
        review_status='automated_preliminary',
        screened_by=actor,
        is_demo=is_demo,
    )


def latest_screen_for(company_profile):
    """The most recent screen across any methodology — never fabricates
    one when none exists."""
    return company_profile.shariah_screens.select_related('methodology', 'financial_facts').first()
