"""
EcoIQ Portfolio calculations — deterministic, no LLM involved anywhere in
this module. investor_portfolio/briefing.py explains these numbers; it never
recomputes or overrides them.

compute_portfolio_snapshot(portfolio) is the single entry point: it reads
Holdings + each company's live market data (league.Company) + each
company's latest PUBLISHED InvestmentRelevanceReport, and returns a plain
dict shaped exactly like PortfolioSnapshot's fields (the view layer does
PortfolioSnapshot.objects.create(portfolio=portfolio, **result)).

Currency handling: this app has no FX-conversion service (none exists
anywhere in the repository — see the module docstring in views.py), so
values are NEVER converted between currencies. When every analytics-included
holding's value shares one currency, `total_market_value` is a real,
honest sum. When they don't, `total_market_value` is left None and
`fx_incomplete=True` — `currency_subtotals` holds the honest per-currency
sums instead. Under fx_incomplete, portfolio *weights* (and therefore the
exposure score) fall back from value-weighting to equal-weighting across
analytics-included holdings, which is disclosed via fx_incomplete rather
than silently pretending $1 == £1.
"""
import datetime

from django.utils import timezone

from investor_portfolio.methodology import (
    CLASSIFICATION_ORDER, CLASSIFICATION_RISK_SCORE, HHI_CONCENTRATION_FLAG,
    HIGH_EXPOSURE_CONCENTRATION_FLAG_PCT, METHODOLOGY_VERSION, STALE_THRESHOLD_DAYS,
    evidence_confidence_for_content, freshness_multiplier,
)


def _holding_value(holding):
    """
    Returns (value: Decimal|None, currency: str|None, missing_market_data: bool,
    stale: bool, price_updated_at: datetime|None) for one Holding.
    Live market price wins when available; manual_current_value (assumed to
    be in the portfolio's base_currency — see Holding.manual_current_value
    help_text) is the documented fallback; otherwise the holding has no
    usable value and is flagged missing_market_data=True (never 0/None
    silently presented as a real value).
    """
    company = holding.company
    if company.has_market_data:
        price, currency = company.normalized_price_and_currency()
        value = round(holding.shares * price, 2)
        return value, currency, False, company.stock_data_is_stale, company.stock_price_updated_at
    if holding.manual_current_value is not None:
        return holding.manual_current_value, holding.portfolio.base_currency, False, False, None
    return None, None, True, False, None


def _latest_published_report(company):
    """Returns the latest published InvestmentRelevanceReport for a company, or None."""
    profile = getattr(company, 'profile', None)
    if profile is None:
        return None
    return profile.investment_reports.filter(status='published').order_by('-version').first()


def _gain_loss(holding, value, currency):
    if value is None or holding.avg_acquisition_price is None:
        return None, None
    if holding.acquisition_currency and currency and holding.acquisition_currency != currency:
        return None, None  # cross-currency gain/loss would require fabricated FX — refuse instead
    cost_basis = holding.shares * holding.avg_acquisition_price
    if cost_basis == 0:
        return None, None
    gain_amount = round(value - cost_basis, 2)
    gain_pct = float(gain_amount / cost_basis * 100)
    return gain_amount, gain_pct


def _build_holding_row(holding, now):
    company = holding.company
    value, currency, missing_market_data, stale_price, price_updated_at = _holding_value(holding)
    gain_amount, gain_pct = _gain_loss(holding, value, currency)

    report = _latest_published_report(company) if holding.include_in_analytics else None
    classification = report.classification if report else None
    has_report = report is not None
    # "known" = has a published report AND that report isn't itself an
    # insufficient_evidence verdict — both cases are "no usable risk signal"
    # and must NOT be folded into the low-exposure bucket.
    is_known = has_report and classification != 'insufficient_evidence'

    evidence_confidence = evidence_confidence_for_content(report.content) if report else None
    report_date = None
    stale_report = False
    age_days = None
    if report:
        report_date = report.published_at or report.generated_at
        age_days = (now - report_date).days
        stale_report = age_days > STALE_THRESHOLD_DAYS

    return {
        'holding_id': holding.pk,
        'company_slug': company.slug,
        'company_name': company.name,
        'ticker': company.ticker,
        'sector': company.sector,
        'sector_display': company.get_sector_display(),
        'country': company.country,
        'exchange': company.exchange,
        'shares': str(holding.shares),
        'currency': currency,
        'market_value': str(value) if value is not None else None,
        'price_per_share': str(round(value / holding.shares, 4)) if value is not None and holding.shares else None,
        'missing_market_data': missing_market_data,
        'stale_price': stale_price,
        'price_updated_at': price_updated_at.isoformat() if price_updated_at else None,
        'gain_amount': str(gain_amount) if gain_amount is not None else None,
        'gain_pct': gain_pct,
        'include_in_analytics': holding.include_in_analytics,
        'has_report': has_report,
        'classification': classification,
        'is_known_exposure': is_known,
        'evidence_confidence': evidence_confidence,
        'report_version': report.version if report else None,
        'report_date': report_date.isoformat() if report_date else None,
        'report_age_days': age_days,
        'stale_report': stale_report,
        # filled in a second pass once total weight is known:
        'weight_pct': None,
        'exposure_contribution': None,
    }


def compute_portfolio_snapshot(portfolio) -> dict:
    now = timezone.now()
    holdings = list(portfolio.holdings.select_related('company').all())
    rows = [_build_holding_row(h, now) for h in holdings]

    # ── Currency / total value ──
    priced_rows = [r for r in rows if r['market_value'] is not None]
    currencies = {r['currency'] for r in priced_rows if r['currency']}
    currency_subtotals = {}
    for r in priced_rows:
        currency_subtotals[r['currency']] = currency_subtotals.get(r['currency'], 0) + float(r['market_value'])
    if portfolio.cash_balance:
        currency_subtotals[portfolio.base_currency] = (
            currency_subtotals.get(portfolio.base_currency, 0) + float(portfolio.cash_balance)
        )
        currencies.add(portfolio.base_currency)

    fx_incomplete = len(currencies) > 1
    total_market_value = None
    total_value_currency = ''
    if not fx_incomplete and currencies:
        total_market_value = round(sum(currency_subtotals.values()), 2)
        total_value_currency = next(iter(currencies))

    # ── Weights (value-weighted normally; equal-weighted if fx_incomplete) ──
    analytics_rows = [r for r in rows if r['include_in_analytics']]
    if fx_incomplete:
        n = len(analytics_rows)
        for r in analytics_rows:
            r['weight_pct'] = round(100.0 / n, 4) if n else 0.0
    else:
        analytics_value_total = sum(float(r['market_value']) for r in analytics_rows if r['market_value'] is not None)
        for r in analytics_rows:
            if r['market_value'] is not None and analytics_value_total > 0:
                r['weight_pct'] = round(float(r['market_value']) / analytics_value_total * 100, 4)
            else:
                r['weight_pct'] = 0.0
    for r in rows:
        if r['weight_pct'] is None:
            r['weight_pct'] = 0.0

    # ── Exposure score (weighted average over KNOWN holdings only) ──
    known_rows = [r for r in analytics_rows if r['is_known_exposure']]
    weighted_terms = []
    for r in known_rows:
        base_score = CLASSIFICATION_RISK_SCORE[r['classification']]
        fresh_mult = freshness_multiplier(r['report_age_days'])
        conf = r['evidence_confidence'] if r['evidence_confidence'] is not None else 0.5
        effective_weight = r['weight_pct'] * conf * fresh_mult
        weighted_terms.append((base_score, effective_weight))
        r['exposure_contribution'] = round(base_score * effective_weight / 100, 2)  # for "largest contributors"

    total_effective_weight = sum(w for _, w in weighted_terms)
    exposure_score = (
        round(sum(score * w for score, w in weighted_terms) / total_effective_weight, 1)
        if total_effective_weight > 0 else None
    )

    known_weight = sum(r['weight_pct'] for r in known_rows)
    analytics_weight = sum(r['weight_pct'] for r in analytics_rows) or 1e-9
    known_exposure_pct = round(known_weight, 2)
    unknown_exposure_pct = round(max(0.0, 100.0 - known_weight), 2) if analytics_rows else None

    evidence_coverage_pct = round(
        sum(r['weight_pct'] * (r['evidence_confidence'] or 0) for r in known_rows), 2
    ) if analytics_rows else None

    stale_weight = sum(r['weight_pct'] for r in known_rows if r['stale_report'])
    stale_analysis_pct = round(stale_weight, 2) if analytics_rows else None

    # ── Distribution (5 buckets — "no report" folds into insufficient_evidence) ──
    distribution = {key: 0.0 for key in CLASSIFICATION_ORDER}
    for r in analytics_rows:
        bucket = r['classification'] if r['is_known_exposure'] else 'insufficient_evidence'
        distribution[bucket] = round(distribution.get(bucket, 0.0) + r['weight_pct'], 2)

    # ── Concentration ──
    top_holdings = sorted(analytics_rows, key=lambda r: r['weight_pct'], reverse=True)[:5]
    hhi = round(sum((r['weight_pct']) ** 2 for r in analytics_rows), 1)  # weight_pct already 0-100 → HHI 0-10000 scale
    by_sector, by_country, by_exchange = {}, {}, {}
    for r in analytics_rows:
        by_sector[r['sector_display']] = round(by_sector.get(r['sector_display'], 0) + r['weight_pct'], 2)
        if r['country']:
            by_country[r['country']] = round(by_country.get(r['country'], 0) + r['weight_pct'], 2)
        if r['exchange']:
            by_exchange[r['exchange']] = round(by_exchange.get(r['exchange'], 0) + r['weight_pct'], 2)
    high_exposure_pct = round(distribution['elevated_exposure'] + distribution['high_exposure'], 2)

    concentration = {
        'top_holdings': [
            {'company_name': r['company_name'], 'ticker': r['ticker'], 'weight_pct': r['weight_pct']}
            for r in top_holdings
        ],
        'hhi': hhi,
        'hhi_flag': hhi >= HHI_CONCENTRATION_FLAG,
        'by_sector': by_sector,
        'by_country': by_country,
        'by_exchange': by_exchange,
        'high_exposure_concentration_pct': high_exposure_pct,
        'high_exposure_concentration_flag': high_exposure_pct >= HIGH_EXPOSURE_CONCENTRATION_FLAG_PCT,
    }

    return {
        'methodology_version': METHODOLOGY_VERSION,
        'total_market_value': total_market_value,
        'total_value_currency': total_value_currency,
        'fx_incomplete': fx_incomplete,
        'currency_subtotals': {k: round(v, 2) for k, v in currency_subtotals.items()},
        'exposure_score': exposure_score,
        'known_exposure_pct': known_exposure_pct if analytics_rows else None,
        'unknown_exposure_pct': unknown_exposure_pct,
        'evidence_coverage_pct': evidence_coverage_pct,
        'stale_analysis_pct': stale_analysis_pct,
        'distribution': distribution,
        'concentration': concentration,
        'holding_snapshots': rows,
    }
