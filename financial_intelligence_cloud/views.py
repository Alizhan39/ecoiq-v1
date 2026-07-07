from django.db.models import Sum
from django.shortcuts import get_object_or_404, render

from financial_intelligence_cloud.models import (
    AdvisoryOpportunity, InstitutionalAccount, PortfolioDailyBrief, PortfolioEntity, PortfolioSignal,
)
from financial_intelligence_cloud.services.daily_brief import generate_daily_portfolio_brief, generate_opportunity_feed
from financial_intelligence_cloud.services.demo_portfolios import ATLAS_SLUG, CIVIC_SLUG, NORTHSTAR_SLUG
from financial_intelligence_cloud.services.qa_router import SUPPORTED_QUESTION_PATTERNS, answer_portfolio_question
from financial_intelligence_cloud.services.subscription import SUBSCRIPTION_TIER_FEATURES

CORE_PURPOSE = (
    "Continuous risk, opportunity and capital intelligence for accounting firms, financial institutions "
    "and investment portfolios — the commercial layer that turns EcoIQ's governed AI-agent, Waste-to-Value "
    "and Capital Allocation architecture into a product professional firms use every day."
)

QUESTIONS_ANSWERED = [
    'Which client should I call today?', 'Why should I call them?',
    'Which portfolio company is losing value?', 'Which company has the largest capital at risk?',
    'Which opportunity is most finance-ready?', 'Which client may need equipment finance?',
    'Which project deserves capital first?', 'Which evidence is missing?',
    'Which case requires human approval?', 'What changed since yesterday?',
    'What verified value has already been recovered?', 'Which advisory opportunity should our firm pursue next?',
]

CTA_BUTTONS = [
    {'label': 'Connect a Demo Portfolio', 'url_name': 'financial_intelligence_cloud:overview'},
    {'label': 'Open Client Opportunity Radar', 'url_name': 'financial_intelligence_cloud:demo_accounting'},
    {'label': 'Who Should I Call Today?', 'url_name': 'financial_intelligence_cloud:clients_to_call'},
    {'label': 'View Portfolio Intelligence', 'url_name': 'financial_intelligence_cloud:portfolio'},
    {'label': 'Ask EcoIQ About My Portfolio', 'url_name': 'financial_intelligence_cloud:ask'},
    {'label': 'Where Should the Next £1 Go?', 'url_name': 'financial_intelligence_cloud:demo_investment'},
    {'label': 'Open Finance Opportunity Radar', 'url_name': 'financial_intelligence_cloud:demo_bank'},
    {'label': 'View Approval Queue', 'url_name': 'financial_intelligence_cloud:opportunity_feed'},
    {'label': 'Generate Daily Brief', 'url_name': 'financial_intelligence_cloud:daily_brief'},
    {'label': 'Request Institutional Pilot', 'url_name': 'financial_intelligence_cloud:subscription'},
]

SAFETY_PRINCIPLES = [
    'Capital at risk is never the same as verified loss.',
    'Potential recoverable value is never the same as verified recovered value.',
    'A finance opportunity identified is never a credit approval.',
    'An investment ranking is never investment advice.',
    'A recommended client call is never a guaranteed advisory-revenue outcome.',
    'An estimated payback is never a verified return.',
    'A funding route identified is never funding secured.',
]


def _demo_stats():
    return {
        'entities_analysed': PortfolioEntity.objects.count(),
        'assets_under_analysis': InstitutionalAccount.objects.filter(is_demo=True).aggregate(
            total=Sum('portfolios__assets_under_analysis'))['total'] or 0,
        'total_capital_at_risk': PortfolioSignal.objects.aggregate(total=Sum('capital_at_risk'))['total'] or 0,
        'total_potential_recoverable_value': PortfolioSignal.objects.aggregate(
            total=Sum('potential_recoverable_value'))['total'] or 0,
        'opportunities_detected': AdvisoryOpportunity.objects.count(),
        'finance_ready_cases': AdvisoryOpportunity.objects.filter(finance_readiness_score__gte=70).count(),
        'approvals_required': PortfolioSignal.objects.filter(human_approval_required=True).count(),
        'verified_value_recovered': PortfolioSignal.objects.aggregate(
            total=Sum('verified_recovered_value'))['total'] or 0,
    }


def overview(request):
    accounts = InstitutionalAccount.objects.filter(is_demo=True).prefetch_related('portfolios')
    return render(request, 'financial_intelligence_cloud/overview.html', {
        'core_purpose': CORE_PURPOSE,
        'questions_answered': QUESTIONS_ANSWERED,
        'accounts': accounts,
        'stats': _demo_stats(),
        'cta_buttons': CTA_BUTTONS,
        'safety_principles': SAFETY_PRINCIPLES,
    })


def clients_to_call(request):
    account = get_object_or_404(InstitutionalAccount, slug=NORTHSTAR_SLUG)
    portfolio = account.portfolios.first()
    opportunities = AdvisoryOpportunity.objects.filter(
        portfolio_entity__portfolio=portfolio,
    ).select_related('portfolio_entity').order_by('-priority_score')[:15]
    return render(request, 'financial_intelligence_cloud/clients_to_call.html', {
        'account': account, 'portfolio': portfolio, 'opportunities': opportunities,
    })


def opportunity_feed(request):
    account = get_object_or_404(InstitutionalAccount, slug=NORTHSTAR_SLUG)
    portfolio = account.portfolios.first()
    items = generate_opportunity_feed(account, portfolio)
    return render(request, 'financial_intelligence_cloud/opportunity_feed.html', {
        'account': account, 'portfolio': portfolio, 'items': items,
    })


def portfolio_view(request):
    accounts = InstitutionalAccount.objects.filter(is_demo=True).prefetch_related('portfolios')

    from ai_agent_council.models import CouncilRun
    freshbridge_council_run = CouncilRun.objects.filter(
        slug='freshbridge-foods-advisory-demo',
    ).prefetch_related('tasks').first()

    return render(request, 'financial_intelligence_cloud/portfolio.html', {
        'accounts': accounts, 'stats': _demo_stats(),
        'freshbridge_council_run': freshbridge_council_run,
    })


def ask(request):
    account_slug = request.GET.get('account', NORTHSTAR_SLUG)
    account = InstitutionalAccount.objects.filter(slug=account_slug).first()
    question_key = request.GET.get('question')
    result = None
    if account and question_key:
        result = answer_portfolio_question(account, question_key)
    return render(request, 'financial_intelligence_cloud/ask.html', {
        'account': account, 'question_key': question_key, 'result': result,
        'supported_questions': list(SUPPORTED_QUESTION_PATTERNS.keys()),
        'accounts': InstitutionalAccount.objects.filter(is_demo=True),
    })


def daily_brief(request):
    account_slug = request.GET.get('account', NORTHSTAR_SLUG)
    account = get_object_or_404(InstitutionalAccount, slug=account_slug)
    portfolio = account.portfolios.first()
    brief = generate_daily_portfolio_brief(account, portfolio)
    return render(request, 'financial_intelligence_cloud/daily_brief.html', {
        'account': account, 'portfolio': portfolio, 'brief': brief,
        'accounts': InstitutionalAccount.objects.filter(is_demo=True),
    })


def subscription(request):
    return render(request, 'financial_intelligence_cloud/subscription.html', {
        'tier_features': SUBSCRIPTION_TIER_FEATURES,
    })


def demo_accounting(request):
    account = get_object_or_404(InstitutionalAccount, slug=NORTHSTAR_SLUG)
    portfolio = account.portfolios.first()
    top_opportunity = AdvisoryOpportunity.objects.filter(
        portfolio_entity__portfolio=portfolio,
    ).order_by('-priority_score').first()
    return render(request, 'financial_intelligence_cloud/demo_accounting.html', {
        'account': account, 'portfolio': portfolio, 'top_opportunity': top_opportunity,
    })


def demo_investment(request):
    account = get_object_or_404(InstitutionalAccount, slug=ATLAS_SLUG)
    portfolio = account.portfolios.first()
    ranked_opportunities = AdvisoryOpportunity.objects.filter(
        portfolio_entity__portfolio=portfolio, opportunity_type='capital_raise_support',
    ).select_related('portfolio_entity').order_by('-priority_score')
    return render(request, 'financial_intelligence_cloud/demo_investment.html', {
        'account': account, 'portfolio': portfolio, 'ranked_opportunities': ranked_opportunities,
    })


def demo_bank(request):
    account = get_object_or_404(InstitutionalAccount, slug=CIVIC_SLUG)
    portfolio = account.portfolios.first()
    finance_opportunities = AdvisoryOpportunity.objects.filter(
        portfolio_entity__portfolio=portfolio, finance_readiness_score__isnull=False,
    ).select_related('portfolio_entity').order_by('-finance_readiness_score')[:15]
    return render(request, 'financial_intelligence_cloud/demo_bank.html', {
        'account': account, 'portfolio': portfolio, 'finance_opportunities': finance_opportunities,
    })
