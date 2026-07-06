"""
financial_intelligence_cloud/services/qa_router.py — "Ask EcoIQ about my
portfolio." A fixed dispatch table of supported questions, NOT fuzzy NLP —
this platform has no live LLM call anywhere; every agent output in this
codebase is fixture_output/simulated-mode.

Every resolver receives `institutional_account` (and optionally `portfolio`)
and is required to filter through
`portfolio_entity__portfolio__institutional_account` before touching
anything else — this is the concrete mechanism that proves "never answer
beyond the user's authorised portfolio scope." An unsupported
`question_key` returns an honest "not supported" response rather than a
fuzzy guess.
"""
from datetime import timedelta

from django.utils import timezone

from financial_intelligence_cloud.models import AdvisoryOpportunity, PortfolioSignal


def _scoped_signals(institutional_account, portfolio=None):
    qs = PortfolioSignal.objects.filter(portfolio_entity__portfolio__institutional_account=institutional_account)
    if portfolio is not None:
        qs = qs.filter(portfolio_entity__portfolio=portfolio)
    return qs


def _scoped_opportunities(institutional_account, portfolio=None):
    qs = AdvisoryOpportunity.objects.filter(portfolio_entity__portfolio__institutional_account=institutional_account)
    if portfolio is not None:
        qs = qs.filter(portfolio_entity__portfolio=portfolio)
    return qs


def _which_client_to_call(institutional_account, portfolio):
    opp = _scoped_opportunities(institutional_account, portfolio).order_by('-priority_score').first()
    if not opp:
        return {'answer': 'No advisory opportunities identified yet.', 'citations': []}
    return {
        'answer': f'{opp.portfolio_entity.name} — {opp.headline}',
        'citations': [opp.id],
        'next_action': 'Recommended client call — not a guaranteed advisory-revenue outcome.',
    }


def _largest_capital_at_risk(institutional_account, portfolio):
    signal = _scoped_signals(institutional_account, portfolio).exclude(capital_at_risk__isnull=True).order_by('-capital_at_risk').first()
    if not signal:
        return {'answer': 'No capital-at-risk signals identified yet.', 'citations': []}
    return {
        'answer': f'{signal.portfolio_entity.name}: £{signal.capital_at_risk:,.0f} projected capital at risk (estimated, not a verified loss).',
        'citations': [signal.id],
        'next_action': 'Review evidence before any external communication.',
    }


def _most_finance_ready(institutional_account, portfolio):
    opp = _scoped_opportunities(institutional_account, portfolio).exclude(finance_readiness_score__isnull=True).order_by('-finance_readiness_score').first()
    if not opp:
        return {'answer': 'No finance-ready opportunities identified yet.', 'citations': []}
    return {
        'answer': f'{opp.portfolio_entity.name}: finance readiness {opp.finance_readiness_score}/100. Finance opportunity identified — not a credit approval.',
        'citations': [opp.id],
        'next_action': 'Route to Finance Review; human approval required before outreach.',
    }


def _equipment_finance_need(institutional_account, portfolio):
    opp = _scoped_opportunities(institutional_account, portfolio).filter(opportunity_type='finance_readiness_advisory').order_by('-priority_score').first()
    if not opp:
        return {'answer': 'No equipment-finance opportunities identified yet.', 'citations': []}
    return {
        'answer': f'{opp.portfolio_entity.name}: {opp.headline}',
        'citations': [opp.id],
        'next_action': 'Human review required before any funder outreach.',
    }


def _capital_priority(institutional_account, portfolio):
    opp = _scoped_opportunities(institutional_account, portfolio).filter(opportunity_type='capital_raise_support').order_by('-priority_score').first()
    if not opp:
        return {'answer': 'No capital allocation ranking available for this portfolio.', 'citations': []}
    return {
        'answer': f'{opp.portfolio_entity.name} — {opp.headline}',
        'citations': [opp.id],
        'next_action': 'Recommendation for investment-committee review, never an autonomous decision.',
    }


def _missing_evidence(institutional_account, portfolio):
    signals = _scoped_signals(institutional_account, portfolio).filter(evidence_quality__in=['weak', 'missing'])
    return {
        'answer': f'{signals.count()} signals have weak or missing evidence.',
        'citations': list(signals.values_list('id', flat=True)[:20]),
        'next_action': 'Request additional evidence before acting on these signals.',
    }


def _needs_human_approval(institutional_account, portfolio):
    signals = _scoped_signals(institutional_account, portfolio).filter(human_approval_required=True)
    return {
        'answer': f'{signals.count()} signals require human approval before any external action.',
        'citations': list(signals.values_list('id', flat=True)[:20]),
        'next_action': 'Route to relationship owner / portfolio manager for review.',
    }


def _whats_changed_since_yesterday(institutional_account, portfolio):
    since = timezone.now() - timedelta(days=1)
    signals = _scoped_signals(institutional_account, portfolio).filter(detected_at__gte=since)
    return {
        'answer': f'{signals.count()} new signals detected in the last day.',
        'citations': list(signals.values_list('id', flat=True)),
        'next_action': 'Review the daily brief for full detail.',
    }


def _verified_value_recovered(institutional_account, portfolio):
    signals = _scoped_signals(institutional_account, portfolio).exclude(verified_recovered_value__isnull=True)
    total = sum(s.verified_recovered_value for s in signals)
    return {
        'answer': f'£{total:,.0f} verified value recovered to date across {signals.count()} case(s).',
        'citations': list(signals.values_list('id', flat=True)),
        'next_action': 'None required — this figure is real and MRV-verified, not estimated.',
    }


SUPPORTED_QUESTION_PATTERNS = {
    'which_client_to_call':          _which_client_to_call,
    'why_this_client':                _which_client_to_call,
    'portfolio_company_losing_value': _largest_capital_at_risk,
    'largest_capital_at_risk':        _largest_capital_at_risk,
    'most_finance_ready_opportunity': _most_finance_ready,
    'equipment_finance_need':         _equipment_finance_need,
    'capital_priority':               _capital_priority,
    'missing_evidence':               _missing_evidence,
    'needs_human_approval':           _needs_human_approval,
    'whats_changed_since_yesterday':  _whats_changed_since_yesterday,
    'verified_value_recovered':       _verified_value_recovered,
    'next_advisory_opportunity':      _which_client_to_call,
}


def answer_portfolio_question(institutional_account, question_key, portfolio=None):
    """
    Never answers beyond institutional_account's own signals/opportunities.
    Unsupported question_key returns an honest 'not supported' response
    rather than a fuzzy guess.
    """
    resolver = SUPPORTED_QUESTION_PATTERNS.get(question_key)
    if resolver is None:
        return {
            'question_key': question_key,
            'answer': f"'{question_key}' is not a supported question.",
            'citations': [], 'next_action': '', 'supported': False,
        }
    result = resolver(institutional_account, portfolio)
    result['question_key'] = question_key
    result.setdefault('next_action', '')
    result['supported'] = True
    return result
