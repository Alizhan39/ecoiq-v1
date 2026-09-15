from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Q, Sum, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from financial_intelligence_cloud.forms import (
    ClientPaymentForm, ClientReminderForm, ClientServiceForm, RecordPaymentForm,
)
from financial_intelligence_cloud.models import (
    AccountingActivity, AdvisoryOpportunity, ClientPayment, ClientReminder, ClientService,
    InstitutionalAccount, PaymentReceipt, PortfolioDailyBrief, PortfolioEntity, PortfolioSignal,
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


def _accounting_accounts():
    return InstitutionalAccount.objects.filter(account_type__in=('accounting_firm', 'advisory_firm'))


def _selected_account(request):
    accounts = _accounting_accounts()
    account_id = request.GET.get('account') or request.POST.get('account')
    if account_id:
        return get_object_or_404(accounts, pk=account_id)
    return accounts.order_by('is_demo', 'firm_name').first()


def _dashboard_redirect(account):
    url = '/financial-intelligence-cloud/accounting-operations/'
    return redirect(f'{url}?account={account.pk}' if account else url)


def _balances_by_currency(payments):
    totals = {}
    for payment in payments:
        totals[payment.currency] = totals.get(payment.currency, 0) + payment.balance
    return [{'currency': currency, 'amount': amount} for currency, amount in sorted(totals.items())]


@staff_member_required
def accounting_operations(request):
    """One low-cost operational view; deadlines are calculated live, not by Celery."""
    accounts = _accounting_accounts().order_by('is_demo', 'firm_name')
    account = _selected_account(request)
    if not account:
        return render(request, 'financial_intelligence_cloud/accounting_operations.html', {
            'accounts': accounts, 'account': None,
        })

    today = timezone.localdate()
    now = timezone.now()
    next_week = now + timedelta(days=7)
    query = request.GET.get('q', '').strip()
    owner_filter = request.GET.get('owner', '')
    service_status = request.GET.get('status', '')

    engagements = ClientService.objects.filter(
        client__portfolio__institutional_account=account, is_active=True,
    ).select_related('client', 'service', 'assigned_to')
    if query:
        engagements = engagements.filter(
            Q(client__name__icontains=query) | Q(service__name__icontains=query)
            | Q(assigned_to__username__icontains=query),
        )
    if owner_filter == 'mine':
        engagements = engagements.filter(assigned_to=request.user)
    elif owner_filter.isdigit():
        engagements = engagements.filter(assigned_to_id=owner_filter)
    if service_status:
        engagements = engagements.filter(status=service_status)

    open_payments = ClientPayment.objects.filter(
        client_service__client__portfolio__institutional_account=account,
    ).exclude(status__in=('paid', 'waived')).select_related(
        'client_service__client', 'client_service__service',
    )
    overdue_payments = list(open_payments.filter(due_date__lt=today).order_by('due_date')[:50])
    upcoming_payments = list(open_payments.filter(due_date__gte=today).order_by('due_date')[:50])
    outstanding_by_currency = _balances_by_currency(open_payments)
    overdue_by_currency = _balances_by_currency(overdue_payments)

    active_reminders = ClientReminder.objects.filter(
        Q(client__portfolio__institutional_account=account)
        | Q(client_service__client__portfolio__institutional_account=account),
        status__in=('open', 'snoozed'),
    ).select_related('client', 'client_service__service', 'owner')
    if owner_filter == 'mine':
        active_reminders = active_reminders.filter(owner=request.user)
    elif owner_filter.isdigit():
        active_reminders = active_reminders.filter(owner_id=owner_filter)
    priority_order = Case(
        When(priority='urgent', then=Value(0)), When(priority='high', then=Value(1)),
        When(priority='normal', then=Value(2)), default=Value(3), output_field=IntegerField(),
    )
    due_reminders = list(active_reminders.filter(
        Q(status='open', due_at__lte=now)
        | Q(status='snoozed', snoozed_until__lte=now),
    ).annotate(priority_order=priority_order).order_by('priority_order', 'due_at')[:50])
    upcoming_reminders = list(active_reminders.filter(
        Q(status='open', due_at__gt=now, due_at__lte=next_week)
        | Q(status='snoozed', snoozed_until__gt=now, snoozed_until__lte=next_week),
    ).order_by('due_at')[:50])

    clients = PortfolioEntity.objects.filter(
        portfolio__institutional_account=account,
    ).annotate(
        service_count=Count('accounting_engagements', filter=Q(accounting_engagements__is_active=True), distinct=True),
        open_payment_count=Count(
            'accounting_engagements__payments',
            filter=~Q(accounting_engagements__payments__status__in=('paid', 'waived')),
            distinct=True,
        ),
        open_reminder_count=Count(
            'accounting_reminders',
            filter=Q(accounting_reminders__status__in=('open', 'snoozed')),
            distinct=True,
        ),
    ).order_by('name')[:100]

    staff_ids = set(engagements.exclude(assigned_to=None).values_list('assigned_to_id', flat=True))
    staff_ids.update(active_reminders.exclude(owner=None).values_list('owner_id', flat=True))
    from django.contrib.auth import get_user_model
    employees = get_user_model().objects.filter(pk__in=staff_ids).order_by('first_name', 'username')

    return render(request, 'financial_intelligence_cloud/accounting_operations.html', {
        'accounts': accounts,
        'account': account,
        'clients': clients,
        'engagements': engagements.order_by('next_due_date', 'client__name')[:100],
        'employees': employees,
        'overdue_payments': overdue_payments,
        'upcoming_payments': upcoming_payments,
        'due_reminders': due_reminders,
        'upcoming_reminders': upcoming_reminders,
        'outstanding_by_currency': outstanding_by_currency,
        'overdue_by_currency': overdue_by_currency,
        'query': query,
        'owner_filter': owner_filter,
        'service_status': service_status,
        'reminder_form': ClientReminderForm(institutional_account=account, initial={'owner': request.user}),
        'service_form': ClientServiceForm(institutional_account=account),
        'payment_form': ClientPaymentForm(institutional_account=account),
        'recent_activity': account.accounting_activity.select_related('actor', 'client')[:20],
    })


@staff_member_required
def add_accounting_reminder(request):
    account = _selected_account(request)
    if request.method != 'POST' or not account:
        return _dashboard_redirect(account)
    form = ClientReminderForm(request.POST, institutional_account=account)
    if form.is_valid():
        reminder = form.save()
        client = reminder.client or reminder.client_service.client
        AccountingActivity.objects.create(
            institutional_account=account, client=client, client_service=reminder.client_service,
            actor=request.user, event_type='reminder_created', summary=f'Reminder added: {reminder.title}',
            metadata={'due_at': reminder.due_at.isoformat(), 'priority': reminder.priority},
        )
        messages.success(request, 'Reminder added.')
    else:
        messages.error(request, 'Reminder was not added. Check the selected client, owner and due time.')
    return _dashboard_redirect(account)


@staff_member_required
def add_client_service(request):
    account = _selected_account(request)
    if request.method != 'POST' or not account:
        return _dashboard_redirect(account)
    form = ClientServiceForm(request.POST, institutional_account=account)
    if form.is_valid():
        engagement = form.save()
        AccountingActivity.objects.create(
            institutional_account=account, client=engagement.client, client_service=engagement,
            actor=request.user, event_type='service_assigned',
            summary=f'{engagement.service.name} assigned to {engagement.client.name}',
            metadata={'assigned_to_id': engagement.assigned_to_id, 'next_due_date': str(engagement.next_due_date or '')},
        )
        messages.success(request, 'Client service added.')
    else:
        messages.error(request, 'Client service was not added. Check the form values.')
    return _dashboard_redirect(account)


@staff_member_required
def add_client_payment(request):
    account = _selected_account(request)
    if request.method != 'POST' or not account:
        return _dashboard_redirect(account)
    form = ClientPaymentForm(request.POST, institutional_account=account)
    if form.is_valid():
        payment = form.save(commit=False)
        if payment.due_date < timezone.localdate():
            payment.status = 'overdue'
        payment.save()
        engagement = payment.client_service
        AccountingActivity.objects.create(
            institutional_account=account, client=engagement.client, client_service=engagement,
            actor=request.user, event_type='payment_due_created',
            summary=f'Payment due recorded for {engagement.client.name}',
            metadata={'payment_id': payment.pk, 'amount_due': str(payment.amount_due), 'due_date': str(payment.due_date)},
        )
        messages.success(request, 'Payment due added.')
    else:
        messages.error(request, 'Payment due was not added. Check the form values.')
    return _dashboard_redirect(account)


@staff_member_required
@transaction.atomic
def record_client_payment(request, payment_id):
    payment = get_object_or_404(
        ClientPayment.objects.select_for_update().select_related(
            'client_service__client__portfolio__institutional_account',
        ),
        pk=payment_id,
    )
    account = payment.client_service.client.portfolio.institutional_account
    if request.method != 'POST':
        return _dashboard_redirect(account)
    form = RecordPaymentForm(request.POST, payment=payment)
    if form.is_valid():
        amount = form.cleaned_data['amount_received']
        PaymentReceipt.objects.create(
            payment=payment, amount=amount, payment_method=form.cleaned_data['payment_method'],
            reference=form.cleaned_data['reference'], recorded_by=request.user,
        )
        payment.amount_paid += amount
        payment.payment_method = form.cleaned_data['payment_method'] or payment.payment_method
        payment.reference = form.cleaned_data['reference'] or payment.reference
        if payment.amount_paid >= payment.amount_due:
            payment.status = 'paid'
            payment.paid_at = timezone.now()
        else:
            payment.status = 'part_paid'
        payment.save()
        AccountingActivity.objects.create(
            institutional_account=account, client=payment.client_service.client,
            client_service=payment.client_service, actor=request.user,
            event_type='payment_received',
            summary=f'Payment received from {payment.client_service.client.name}',
            metadata={
                'payment_id': payment.pk, 'amount_received': str(amount),
                'amount_paid_total': str(payment.amount_paid), 'status': payment.status,
            },
        )
        messages.success(request, 'Payment updated.')
    else:
        messages.error(request, 'Payment was not updated. Check the amount against the outstanding balance.')
    return _dashboard_redirect(account)


@staff_member_required
def update_accounting_reminder(request, reminder_id):
    reminder = get_object_or_404(
        ClientReminder.objects.select_related('client__portfolio__institutional_account', 'client_service__client__portfolio__institutional_account'),
        pk=reminder_id,
    )
    client = reminder.client or reminder.client_service.client
    account = client.portfolio.institutional_account
    if request.method != 'POST':
        return _dashboard_redirect(account)
    action = request.POST.get('action')
    if action == 'done':
        reminder.status = 'done'
        reminder.completed_at = timezone.now()
        summary = f'Reminder completed: {reminder.title}'
    elif action in {'snooze_1d', 'snooze_7d'}:
        days = 1 if action == 'snooze_1d' else 7
        reminder.status = 'snoozed'
        reminder.snoozed_until = timezone.now() + timedelta(days=days)
        summary = f'Reminder snoozed {days} day(s): {reminder.title}'
    else:
        messages.error(request, 'Unknown reminder action.')
        return _dashboard_redirect(account)
    reminder.save(update_fields=['status', 'completed_at', 'snoozed_until', 'updated_at'])
    AccountingActivity.objects.create(
        institutional_account=account, client=client, client_service=reminder.client_service,
        actor=request.user, event_type='reminder_updated', summary=summary,
        metadata={'reminder_id': reminder.pk, 'status': reminder.status},
    )
    messages.success(request, 'Reminder updated.')
    return _dashboard_redirect(account)
