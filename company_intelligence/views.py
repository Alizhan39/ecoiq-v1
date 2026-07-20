"""
company_intelligence/views.py — feat/company-halal-intelligence (PR 9).

Every view here is either a public, GET-only read (matching companies.
company_detail's existing fully-public, no-login convention — see PR9
audit) or a login-gated POST for the one genuinely personal, stateful
action this app introduces: the Research Watchlist. Shariah screening and
KPI-assessment computation are NOT triggered from a public button — like
every other company-scoring pipeline in this repo (companies/
management/commands/recalculate_scores.py, pandas_scoring_engine's
recalculate_ecoiq_scores.py, league's seed_league.py), they run via a
management command (see management/commands/seed_company_intelligence_demo.py
for this PR's own instrumented example), never as an anonymous-triggerable
web action — consistent with "no state-changing GET actions" and this
being research intelligence, not a live scoring API.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from companies.models import CompanyProfile
from league.models import Company

from company_intelligence.models import ResearchWatchlistEntry
from company_intelligence.services.company_trace import build_company_trace


def _profile_or_404(slug):
    company = get_object_or_404(Company, slug=slug)
    return get_object_or_404(CompanyProfile, company=company, status__in=('public', 'verified', 'draft'))


def explain_view(request, slug):
    """
    /companies/<slug>/explain/ — "Why does EcoIQ classify this company
    this way?" GET-only, public (same access level as the company detail
    page itself), no telemetry written by viewing it.
    """
    profile = _profile_or_404(slug)
    try:
        trace = build_company_trace(profile, user=request.user)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Unexpected failure building company trace for %s', profile.pk)
        messages.error(request, 'Something went wrong building this company\'s research trace.')
        return redirect('companies:detail', slug=slug)

    return render(request, 'company_intelligence/explain.html', {
        'profile': profile, 'company': profile.company, 'trace': trace,
    })


@login_required
def watchlist_add_view(request, slug):
    """POST-only. Adds (or updates the status of) the current user's own
    Research Watchlist entry for this company. Never accepts or stores a
    BUY/SELL/HOLD value — status is restricted to
    ResearchWatchlistEntry.STATUS_CHOICES."""
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)
    status = request.POST.get('status', 'researching')
    valid_statuses = {choice for choice, _ in ResearchWatchlistEntry.STATUS_CHOICES}
    if status not in valid_statuses:
        status = 'researching'

    entry, created = ResearchWatchlistEntry.objects.update_or_create(
        user=request.user, company=profile, defaults={'status': status},
    )
    messages.success(
        request,
        f'Added {profile.company.name} to your research watchlist.' if created
        else f'Updated your watchlist status for {profile.company.name}.',
    )
    return redirect('companies:detail', slug=slug)


@login_required
def watchlist_remove_view(request, slug):
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)
    ResearchWatchlistEntry.objects.filter(user=request.user, company=profile).delete()
    messages.success(request, f'Removed {profile.company.name} from your research watchlist.')
    return redirect('companies:watchlist')


@login_required
def watchlist_view(request):
    """GET-only. Shows ONLY the current user's own watchlist entries —
    never another user's, matching this app's per-user isolation rule
    (there is no organisation concept for personal research lists)."""
    entries = (
        ResearchWatchlistEntry.objects
        .filter(user=request.user)
        .select_related('company', 'company__company')
    )
    return render(request, 'company_intelligence/watchlist.html', {'entries': entries})
