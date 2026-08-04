"""
EcoIQ Portfolio Exposure Methodology — versioned, deterministic, no LLM.

Every numeric mapping and weight used by investor_portfolio/calculations.py
lives here so a methodology change is a one-file diff and every persisted
PortfolioSnapshot records exactly which METHODOLOGY_VERSION produced it.

This module contains ONLY pure functions and constant tables — no DB access,
no model imports beyond what's needed for type clarity. calculations.py is
the only caller.
"""

METHODOLOGY_VERSION = 'v1'

# ── Classification → risk score (0-100, higher = more identified exposure) ──
# 'insufficient_evidence' deliberately has NO entry: it is excluded from the
# weighted-average numerator entirely (see calculations.py) rather than
# being silently treated as 0 (low risk) or omitted from the denominator.
CLASSIFICATION_RISK_SCORE = {
    'lower_exposure': 15,
    'moderate_exposure': 40,
    'elevated_exposure': 65,
    'high_exposure': 90,
}

# Order used for distribution dicts / dashboard bars — always show all 5,
# even at 0%, so an empty bucket reads as "zero", not "not tracked".
CLASSIFICATION_ORDER = [
    'lower_exposure', 'moderate_exposure', 'elevated_exposure',
    'high_exposure', 'insufficient_evidence',
]

# ── Evidence-type → confidence weight (0-1) ─────────────────────────────────
# Sampled from the evidence_type values already stored on each
# InvestmentRelevanceReport's key_risks/positive_signals entries
# (companies.investment_report.EVIDENCE_TYPE_CHOICES) — no new evidence
# taxonomy invented for this app.
EVIDENCE_TYPE_CONFIDENCE_WEIGHT = {
    'verified_evidence': 1.0,
    'company_reported': 0.75,
    'external_allegation': 0.5,
    'ai_interpretation': 0.4,
    'insufficient_evidence': 0.1,
}
DEFAULT_EVIDENCE_CONFIDENCE = 0.5  # a published report with no risk/signal entries to sample

# ── Report freshness → weight multiplier ────────────────────────────────────
# (max_age_days_inclusive, multiplier) — first match wins, None = catch-all.
FRESHNESS_BANDS = [
    (30, 1.0),
    (90, 0.85),
    (180, 0.65),
    (None, 0.45),
]
STALE_THRESHOLD_DAYS = 90  # a report older than this is flagged stale everywhere in this app

# ── Concentration ────────────────────────────────────────────────────────────
# High-exposure concentration flag threshold — % of analytics-included value
# in elevated_exposure + high_exposure combined, above which the dashboard
# calls out concentration risk in plain text (not just a number).
HIGH_EXPOSURE_CONCENTRATION_FLAG_PCT = 25.0
# HHI (Herfindahl-Hirschman Index, 0-10000) above which holding concentration
# itself (regardless of classification) is flagged. 2500 is the standard
# US DOJ/FTC "highly concentrated" threshold, reused here for a portfolio's
# holding weights rather than a market's firms.
HHI_CONCENTRATION_FLAG = 2500


def freshness_multiplier(age_days):
    """age_days may be None (unknown report date) — treated as the stalest band."""
    if age_days is None:
        return FRESHNESS_BANDS[-1][1]
    for max_age, multiplier in FRESHNESS_BANDS:
        if max_age is None or age_days <= max_age:
            return multiplier
    return FRESHNESS_BANDS[-1][1]


def evidence_confidence_for_content(report_content: dict) -> float:
    """Average evidence-type confidence weight across a report's risk/signal entries."""
    entries = list(report_content.get('key_risks') or []) + list(report_content.get('positive_signals') or [])
    if not entries:
        return DEFAULT_EVIDENCE_CONFIDENCE
    weights = [
        EVIDENCE_TYPE_CONFIDENCE_WEIGHT.get(e.get('evidence_type'), DEFAULT_EVIDENCE_CONFIDENCE)
        for e in entries if isinstance(e, dict)
    ]
    return sum(weights) / len(weights) if weights else DEFAULT_EVIDENCE_CONFIDENCE
