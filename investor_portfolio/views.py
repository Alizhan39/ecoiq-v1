"""
EcoIQ Portfolio & Watchlist Intelligence — views.

Privacy (spec §11): every Portfolio/Holding/PortfolioSnapshot/PortfolioBriefing
view goes through _portfolios_visible_to(user) (owner, or staff — mirrors
core/views.py:_assessments_visible_to), and non-owners get a 404, not a 403,
so a guessed URL doesn't even confirm the portfolio exists. There is NO view
anywhere in this app that renders another user's acquisition prices, share
counts, total value, notes, or briefings — public/is_public only ever
applies to Watchlist (which carries no financial data at all).
"""
import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from league.models import Company

from .calculations import compute_portfolio_snapshot
from .changes import diff_snapshots
from .csv_import import export_holdings_csv, parse_holdings_csv, summarize_rows
from .methodology import CLASSIFICATION_ORDER, STALE_THRESHOLD_DAYS
from .models import Holding, Portfolio, PortfolioBriefing, PortfolioSnapshot, Watchlist, WatchlistItem

DISCLAIMER_FINANCIAL = (
    "EcoIQ provides environmental stewardship and sustainability-risk intelligence. "
    "It does not provide investment advice, financial recommendations, portfolio-management "
    "services or predictions of investment performance."
)

CLASSIFICATION_DISPLAY = {
    'lower_exposure': 'Lower Identified Exposure',
    'moderate_exposure': 'Moderate Identified Exposure',
    'elevated_exposure': 'Elevated Identified Exposure',
    'high_exposure': 'High Identified Exposure',
    'insufficient_evidence': 'Insufficient Evidence',
    None: 'No Report',
}


# ── Permission helpers ───────────────────────────────────────────────────────

def _portfolios_visible_to(user):
    if user.is_staff:
        return Portfolio.objects.all()
    return Portfolio.objects.filter(owner=user)


def _watchlists_editable_by(user):
    if user.is_staff:
        return Watchlist.objects.all()
    return Watchlist.objects.filter(owner=user)


def _watchlist_or_404(user, pk):
    """
    Public watchlists are viewable by anyone, including anonymous visitors
    (that's the point of the is_public flag — no financial data is ever on
    a Watchlist). A private watchlist 404s for everyone except its owner or
    staff — including anonymous users — so a guessed URL never even confirms
    a private watchlist exists.
    """
    wl = get_object_or_404(Watchlist, pk=pk)
    if wl.is_public:
        return wl
    if user.is_authenticated and (wl.owner_id == user.id or user.is_staff):
        return wl
    raise Http404


# ── Watchlists ───────────────────────────────────────────────────────────────

@login_required
def watchlist_list(request):
    watchlists = Watchlist.objects.filter(owner=request.user).prefetch_related('items')
    return render(request, 'investor_portfolio/watchlist_list.html', {
        'watchlists': watchlists,
    })


@login_required
def watchlist_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Watchlist name is required.')
            return redirect('portfolio:watchlist_list')
        wl, created = Watchlist.objects.get_or_create(
            owner=request.user, name=name,
            defaults={
                'description': request.POST.get('description', '').strip(),
                'is_public': request.POST.get('is_public') == 'on',
            },
        )
        if not created:
            messages.warning(request, f'You already have a watchlist named "{name}".')
        else:
            messages.success(request, f'Watchlist "{name}" created.')
        return redirect('portfolio:watchlist_detail', pk=wl.pk)
    return render(request, 'investor_portfolio/watchlist_form.html', {})


def watchlist_detail(request, pk):
    wl = _watchlist_or_404(request.user, pk)
    is_owner = request.user.is_authenticated and wl.owner_id == request.user.id

    items = list(wl.items.select_related('company').order_by('order', 'added_at'))
    rows = []
    now = timezone.now()
    for item in items:
        co = item.company
        profile = getattr(co, 'profile', None)
        report = (profile.investment_reports.filter(status='published').order_by('-version').first()
                  if profile else None)
        prior_report = None
        if report:
            prior_report = (profile.investment_reports
                             .filter(status='published', version__lt=report.version)
                             .order_by('-version').first())
        rows.append({
            'item': item,
            'company': co,
            'classification': report.classification if report else None,
            'classification_display': CLASSIFICATION_DISPLAY.get(report.classification if report else None),
            'report': report,
            'report_age_days': (now - (report.published_at or report.generated_at)).days if report else None,
            'stale': (now - (report.published_at or report.generated_at)).days > STALE_THRESHOLD_DAYS if report else False,
            'classification_changed': bool(prior_report and prior_report.classification != report.classification),
            'is_new_report': report is not None and report.version == 1,
        })

    sort = request.GET.get('sort', 'name')
    if sort == 'exposure':
        order = {c: i for i, c in enumerate(CLASSIFICATION_ORDER)}
        rows.sort(key=lambda r: order.get(r['classification'], -1), reverse=True)
    elif sort == 'report_date':
        rows.sort(key=lambda r: r['report_age_days'] if r['report_age_days'] is not None else 10**9)
    elif sort == 'sector':
        rows.sort(key=lambda r: r['company'].get_sector_display())
    elif sort == 'changed':
        rows.sort(key=lambda r: not r['classification_changed'])
    else:
        rows.sort(key=lambda r: r['company'].name.lower())

    distribution = {key: 0 for key in CLASSIFICATION_ORDER}
    for r in rows:
        bucket = r['classification'] if r['classification'] else 'insufficient_evidence'
        distribution[bucket] = distribution.get(bucket, 0) + 1

    return render(request, 'investor_portfolio/watchlist_detail.html', {
        'watchlist': wl,
        'is_owner': is_owner,
        'rows': rows,
        'distribution': distribution,
        'sort': sort,
        'stale_threshold_days': STALE_THRESHOLD_DAYS,
    })


@require_POST
@login_required
def watchlist_delete(request, pk):
    wl = get_object_or_404(_watchlists_editable_by(request.user), pk=pk)
    wl.delete()
    messages.success(request, 'Watchlist deleted.')
    return redirect('portfolio:watchlist_list')


@require_POST
@login_required
def watchlist_remove_company(request, pk, company_slug):
    wl = get_object_or_404(_watchlists_editable_by(request.user), pk=pk)
    WatchlistItem.objects.filter(watchlist=wl, company__slug=company_slug).delete()
    messages.success(request, 'Removed from watchlist.')
    next_url = request.POST.get('next') or reverse('portfolio:watchlist_detail', kwargs={'pk': wl.pk})
    return redirect(next_url)


@require_POST
@login_required
def watchlist_add_company(request):
    """
    Called from the 'Add to watchlist' control on a public company page.
    Accepts either watchlist_id (existing) or new_watchlist_name (create +
    add in one action, per spec §1).
    """
    company = get_object_or_404(Company, slug=request.POST.get('company_slug', ''))
    watchlist_id = request.POST.get('watchlist_id', '').strip()
    new_name = request.POST.get('new_watchlist_name', '').strip()
    next_url = request.POST.get('next') or company.stock_profile_url or '/'

    if watchlist_id:
        wl = get_object_or_404(Watchlist, pk=watchlist_id, owner=request.user)
    elif new_name:
        wl, _created = Watchlist.objects.get_or_create(owner=request.user, name=new_name)
    else:
        messages.error(request, 'Choose an existing watchlist or name a new one.')
        return redirect(next_url)

    _item, created = WatchlistItem.objects.get_or_create(watchlist=wl, company=company)
    if created:
        messages.success(request, f'Added {company.name} to "{wl.name}".')
    else:
        messages.info(request, f'{company.name} is already in "{wl.name}".')
    return redirect(next_url)


# ── Portfolios ───────────────────────────────────────────────────────────────

@login_required
def portfolio_list(request):
    portfolios = Portfolio.objects.filter(owner=request.user).prefetch_related('holdings')
    return render(request, 'investor_portfolio/portfolio_list.html', {
        'portfolios': portfolios,
        'disclaimer_financial': DISCLAIMER_FINANCIAL,
    })


@login_required
def portfolio_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Portfolio name is required.')
            return redirect('portfolio:portfolio_list')
        cash = request.POST.get('cash_balance', '').strip()
        portfolio, created = Portfolio.objects.get_or_create(
            owner=request.user, name=name,
            defaults={
                'base_currency': (request.POST.get('base_currency') or 'USD').upper()[:8],
                'description': request.POST.get('description', '').strip(),
                'cash_balance': Decimal(cash) if cash else None,
            },
        )
        if not created:
            messages.warning(request, f'You already have a portfolio named "{name}".')
        else:
            messages.success(request, f'Portfolio "{name}" created.')
        return redirect('portfolio:portfolio_dashboard', pk=portfolio.pk)
    return render(request, 'investor_portfolio/portfolio_form.html', {})


@login_required
def portfolio_dashboard(request, pk):
    portfolio = get_object_or_404(_portfolios_visible_to(request.user), pk=pk)
    snapshot = portfolio.latest_snapshot
    prior_snapshot = portfolio.snapshots.exclude(pk=snapshot.pk).order_by('-calculated_at').first() if snapshot else None
    diff = diff_snapshots(prior_snapshot, snapshot) if snapshot else None

    rows = list(snapshot.holding_snapshots) if snapshot else []

    # ── Filters ──
    sector_f = request.GET.get('sector', '')
    country_f = request.GET.get('country', '')
    exposure_f = request.GET.get('exposure', '')
    stale_f = request.GET.get('stale', '')
    missing_f = request.GET.get('missing_data', '')
    if sector_f:
        rows = [r for r in rows if r['sector'] == sector_f]
    if country_f:
        rows = [r for r in rows if r['country'] == country_f]
    if exposure_f:
        def _bucket(r):
            return r['classification'] if r['is_known_exposure'] else 'insufficient_evidence'
        rows = [r for r in rows if _bucket(r) == exposure_f]
    if stale_f == '1':
        rows = [r for r in rows if r['stale_report'] or r['stale_price']]
    if missing_f == '1':
        rows = [r for r in rows if r['missing_market_data']]

    sort = request.GET.get('sort', 'weight')
    reverse_sort = request.GET.get('dir', 'desc') == 'desc'
    sort_keys = {
        'weight': lambda r: r['weight_pct'] or 0,
        'value': lambda r: float(r['market_value']) if r['market_value'] else -1,
        'name': lambda r: r['company_name'].lower(),
        'classification': lambda r: CLASSIFICATION_ORDER.index(r['classification']) if r['classification'] in CLASSIFICATION_ORDER else -1,
        'confidence': lambda r: r['evidence_confidence'] or 0,
        'shares': lambda r: float(r['shares']) if r['shares'] else 0,
    }
    rows.sort(key=sort_keys.get(sort, sort_keys['weight']), reverse=reverse_sort)

    all_rows = list(snapshot.holding_snapshots) if snapshot else []
    sectors = sorted({r['sector_display'] for r in all_rows})
    countries = sorted({r['country'] for r in all_rows if r['country']})

    return render(request, 'investor_portfolio/portfolio_dashboard.html', {
        'portfolio': portfolio,
        'snapshot': snapshot,
        'diff': diff,
        'rows': rows,
        'all_holdings_count': len(all_rows),
        'sectors': sectors,
        'countries': countries,
        'sort': sort, 'dir': request.GET.get('dir', 'desc'),
        'filters': {'sector': sector_f, 'country': country_f, 'exposure': exposure_f,
                    'stale': stale_f, 'missing_data': missing_f},
        'classification_order': CLASSIFICATION_ORDER,
        'classification_display': CLASSIFICATION_DISPLAY,
        'latest_briefing': portfolio.latest_briefing,
        'disclaimer_financial': DISCLAIMER_FINANCIAL,
        'is_staff_viewing_other': request.user.is_staff and portfolio.owner_id != request.user.id,
    })


@require_POST
@login_required
def portfolio_recalculate(request, pk):
    portfolio = get_object_or_404(_portfolios_visible_to(request.user), pk=pk)
    result = compute_portfolio_snapshot(portfolio)
    PortfolioSnapshot.objects.create(portfolio=portfolio, **result)
    messages.success(request, 'Portfolio analytics recalculated.')
    return redirect('portfolio:portfolio_dashboard', pk=portfolio.pk)


@require_POST
@login_required
def portfolio_delete(request, pk):
    portfolio = get_object_or_404(_portfolios_visible_to(request.user), pk=pk)
    portfolio.delete()
    messages.success(request, 'Portfolio deleted.')
    return redirect('portfolio:portfolio_list')


# ── Holdings ─────────────────────────────────────────────────────────────────

def _parse_holding_form(request):
    errors = []
    company = None
    company_slug = request.POST.get('company_slug', '').strip()
    if not company_slug:
        errors.append('Company is required.')
    else:
        company = Company.objects.filter(slug=company_slug).first()
        if not company:
            errors.append('Company not found.')

    shares = None
    try:
        shares = Decimal(request.POST.get('shares', '').strip())
        if shares <= 0:
            errors.append('Shares must be greater than zero.')
    except (InvalidOperation, ValueError):
        errors.append('Shares must be a valid number.')

    avg_price_raw = request.POST.get('avg_acquisition_price', '').strip()
    avg_price = None
    if avg_price_raw:
        try:
            avg_price = Decimal(avg_price_raw)
        except InvalidOperation:
            errors.append('Average acquisition price must be a valid number.')

    manual_value_raw = request.POST.get('manual_current_value', '').strip()
    manual_value = None
    if manual_value_raw:
        try:
            manual_value = Decimal(manual_value_raw)
        except InvalidOperation:
            errors.append('Manual current value must be a valid number.')

    acq_date_raw = request.POST.get('acquisition_date', '').strip()
    acq_date = None
    if acq_date_raw:
        try:
            acq_date = datetime.date.fromisoformat(acq_date_raw)
        except ValueError:
            errors.append('Acquisition date must be YYYY-MM-DD.')

    return {
        'company': company,
        'shares': shares,
        'avg_acquisition_price': avg_price,
        'acquisition_currency': (request.POST.get('acquisition_currency') or 'USD').upper()[:8],
        'acquisition_date': acq_date,
        'manual_current_value': manual_value,
        'notes': request.POST.get('notes', '').strip(),
        'include_in_analytics': request.POST.get('include_in_analytics', 'on') == 'on',
    }, errors


@login_required
def holding_create(request, pk):
    portfolio = get_object_or_404(_portfolios_visible_to(request.user), pk=pk)
    if request.method == 'POST':
        data, errors = _parse_holding_form(request)
        if not errors and Holding.objects.filter(portfolio=portfolio, company=data['company']).exists():
            errors.append(f'{data["company"].name} is already a holding in this portfolio — edit it instead of adding it again.')
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            company = data.pop('company')
            Holding.objects.create(portfolio=portfolio, company=company, **data)
            messages.success(request, f'Added {company.name} to {portfolio.name}.')
            return redirect('portfolio:portfolio_dashboard', pk=portfolio.pk)
    return render(request, 'investor_portfolio/holding_form.html', {
        'portfolio': portfolio, 'holding': None,
        'companies': Company.objects.order_by('name').only('slug', 'name', 'ticker'),
    })


@login_required
def holding_edit(request, pk, holding_id):
    portfolio = get_object_or_404(_portfolios_visible_to(request.user), pk=pk)
    holding = get_object_or_404(Holding, pk=holding_id, portfolio=portfolio)
    if request.method == 'POST':
        data, errors = _parse_holding_form(request)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            data.pop('company')  # company is immutable on edit — delete + recreate to change it
            for field, value in data.items():
                setattr(holding, field, value)
            holding.save()
            messages.success(request, f'Updated {holding.company.name}.')
            return redirect('portfolio:portfolio_dashboard', pk=portfolio.pk)
    return render(request, 'investor_portfolio/holding_form.html', {
        'portfolio': portfolio, 'holding': holding,
        'companies': Company.objects.order_by('name').only('slug', 'name', 'ticker'),
    })


@require_POST
@login_required
def holding_delete(request, pk, holding_id):
    portfolio = get_object_or_404(_portfolios_visible_to(request.user), pk=pk)
    Holding.objects.filter(pk=holding_id, portfolio=portfolio).delete()
    messages.success(request, 'Holding removed.')
    return redirect('portfolio:portfolio_dashboard', pk=portfolio.pk)


# ── CSV import / export ──────────────────────────────────────────────────────

@login_required
def portfolio_import_csv(request, pk):
    portfolio = get_object_or_404(_portfolios_visible_to(request.user), pk=pk)

    if request.method == 'POST' and request.FILES.get('csv_file'):
        existing_ids = list(portfolio.holdings.values_list('company_id', flat=True))
        rows = parse_holdings_csv(request.FILES['csv_file'], existing_company_ids=existing_ids)
        request.session[f'portfolio_import_{portfolio.pk}'] = rows
        return render(request, 'investor_portfolio/portfolio_import_preview.html', {
            'portfolio': portfolio, 'rows': rows, 'summary': summarize_rows(rows),
        })

    return render(request, 'investor_portfolio/portfolio_import_upload.html', {'portfolio': portfolio})


@require_POST
@login_required
def portfolio_import_confirm(request, pk):
    portfolio = get_object_or_404(_portfolios_visible_to(request.user), pk=pk)
    rows = request.session.pop(f'portfolio_import_{portfolio.pk}', None)
    if not rows:
        messages.error(request, 'Nothing to import — please upload a CSV again.')
        return redirect('portfolio:portfolio_import_csv', pk=portfolio.pk)

    created = 0
    for row in rows:
        if row['status'] != 'matched':
            continue
        company = Company.objects.filter(pk=row['company_id']).first()
        if not company:
            continue
        Holding.objects.create(
            portfolio=portfolio, company=company,
            shares=Decimal(row['quantity']),
            avg_acquisition_price=Decimal(row['avg_price']) if row['avg_price'] else None,
            acquisition_currency=row['currency'],
            acquisition_date=datetime.date.fromisoformat(row['acquisition_date']) if row['acquisition_date'] else None,
        )
        created += 1
    messages.success(request, f'Imported {created} holding(s).')
    return redirect('portfolio:portfolio_dashboard', pk=portfolio.pk)


@login_required
def portfolio_export_csv(request, pk):
    portfolio = get_object_or_404(_portfolios_visible_to(request.user), pk=pk)
    result = compute_portfolio_snapshot(portfolio)  # always current — export doesn't require a saved snapshot
    csv_text = export_holdings_csv(result['holding_snapshots'])
    response = HttpResponse(csv_text, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{portfolio.name}-holdings.csv"'
    return response


# ── AI Portfolio Briefing ───────────────────────────────────────────────────

@require_POST
@login_required
def portfolio_generate_briefing(request, pk):
    portfolio = get_object_or_404(_portfolios_visible_to(request.user), pk=pk)
    snapshot = portfolio.latest_snapshot
    if snapshot is None:
        messages.error(request, 'Recalculate portfolio analytics before generating a briefing.')
        return redirect('portfolio:portfolio_dashboard', pk=portfolio.pk)

    prior = portfolio.snapshots.exclude(pk=snapshot.pk).order_by('-calculated_at').first()
    diff = diff_snapshots(prior, snapshot)

    from .briefing import generate_portfolio_briefing
    try:
        briefing = generate_portfolio_briefing(portfolio, snapshot, diff, user=request.user)
        if briefing.prohibited_language_flags:
            messages.warning(request, f'Briefing v{briefing.version} generated but flagged '
                                       f'{len(briefing.prohibited_language_flags)} language finding(s).')
        else:
            messages.success(request, f'Portfolio briefing v{briefing.version} generated.')
    except RuntimeError as exc:
        messages.error(request, f'Could not generate briefing: {exc}')
    return redirect('portfolio:portfolio_dashboard', pk=portfolio.pk)


@require_POST
@login_required
def portfolio_briefing_status(request, pk, briefing_id):
    """Unlike company reports, the OWNER (not just staff) may move their own private briefing through
    draft -> reviewed -> published, since it is never shown to anyone but them (+ staff)."""
    portfolio = get_object_or_404(_portfolios_visible_to(request.user), pk=pk)
    briefing = get_object_or_404(PortfolioBriefing, pk=briefing_id, portfolio=portfolio)
    action = request.POST.get('action')

    if action == 'mark_reviewed':
        briefing.status = 'reviewed'
        briefing.reviewed_by = request.user
        briefing.reviewed_at = timezone.now()
        briefing.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
    elif action == 'publish':
        if not briefing.is_publishable:
            messages.error(request, 'Cannot finalize — this briefing has prohibited-language flags.')
            return redirect('portfolio:portfolio_dashboard', pk=portfolio.pk)
        briefing.status = 'published'
        briefing.published_at = timezone.now()
        briefing.save(update_fields=['status', 'published_at'])
    messages.success(request, f'Briefing v{briefing.version} updated.')
    return redirect('portfolio:portfolio_dashboard', pk=portfolio.pk)
