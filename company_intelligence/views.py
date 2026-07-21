"""
company_intelligence/views.py — feat/company-halal-intelligence (PR 9).

Every view here is either a public, GET-only read (matching companies.
company_detail's existing fully-public, no-login convention — see PR9
audit) or a gated POST for a genuinely stateful action. Shariah screening
and KPI-assessment computation are NOT triggered from a PUBLIC button —
like every other company-scoring pipeline in this repo (companies/
management/commands/recalculate_scores.py, pandas_scoring_engine's
recalculate_ecoiq_scores.py, league's seed_league.py), the primary path is
a management command (see management/commands/seed_company_intelligence_demo.py
and .../ingest_real_company_evidence.py) — consistent with "no
state-changing GET actions" and this being research intelligence, not a
live scoring API.

feat/company-evidence-ingestion (PR 10) adds exactly two STAFF-gated POST
actions the brief explicitly allows ("A staff-triggered refresh is
acceptable for this PR" / "Provide a minimal staff review workflow"):
refresh_company_view (re-runs real ingestion for one company) and
evidence_review_action_view (records one EvidenceReviewAction and, for
verify/reject, moves the target CompanyKPIEvidenceLink's review_state).
Both are @staff_member_required, matching every other state-changing
action already gated that way elsewhere in this codebase (capital_guardian,
etc.) — never public, unlike the Research Watchlist's ordinary-user gate.
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from companies.models import CompanyProfile
from league.models import Company

from company_intelligence.models import CompanyKPIEvidenceLink, EvidenceReviewAction, ResearchWatchlistEntry
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
    ResearchWatchlistEntry.STATUS_CHOICES.

    feat/company-discovery-ranking (PR 11): an optional `research_context`
    POST field (e.g. "Added from Discover Companies — KPI: Bees &
    Sustainable Production Systems") lets a user record WHY they added a
    company, without inventing any trading/portfolio semantics — it's
    stored in the existing free-text `notes` field, never overwritten with
    blank when the field is absent (so re-adding/updating status from the
    plain company page never clobbers a note a user wrote earlier).
    """
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)
    status = request.POST.get('status', 'researching')
    valid_statuses = {choice for choice, _ in ResearchWatchlistEntry.STATUS_CHOICES}
    if status not in valid_statuses:
        status = 'researching'

    defaults = {'status': status}
    research_context = request.POST.get('research_context', '').strip()
    if research_context:
        defaults['notes'] = research_context

    entry, created = ResearchWatchlistEntry.objects.update_or_create(
        user=request.user, company=profile, defaults=defaults,
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


@staff_member_required(login_url='/login/')
def refresh_company_view(request, slug):
    """
    POST-only, staff-only. Re-runs real evidence ingestion for this company
    (idempotent — see evidence_ingestion.ingest_company_evidence) and, if a
    Shariah methodology is available, re-screens with whatever fresh
    financial facts were found. Never fabricates a source when none is
    mapped — an honest warning is shown instead of a fake refresh.
    """
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)

    from company_intelligence.models import ShariahMethodology
    from company_intelligence.services.evidence_ingestion import ingest_company_evidence

    methodology = ShariahMethodology.objects.filter(is_active=True).order_by('-effective_date').first()
    try:
        result = ingest_company_evidence(profile, actor=request.user, methodology=methodology)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Refresh failed for company %s', profile.pk)
        messages.error(request, 'Refresh failed unexpectedly — nothing was changed.')
        return redirect('companies:detail', slug=slug)

    if not result['identity']['sec_available']:
        messages.warning(request, result['warnings'][0] if result['warnings'] else 'No real source available for this company.')
    else:
        run = result['ingestion_run']
        messages.success(
            request,
            f'Refresh complete — ingestion {run.get_status_display() if run else "n/a"}, '
            f'{len(result["kpi_candidates_proposed"])} new KPI candidate(s) proposed.'
            + (f' {len(result["warnings"])} warning(s) — see below.' if result['warnings'] else ''),
        )
        for w in result['warnings']:
            messages.info(request, w)
    return redirect('companies:detail', slug=slug)


@staff_member_required(login_url='/login/')
def evidence_review_action_view(request, slug):
    """
    POST-only, staff-only. The company-page "quick review" action —
    delegates all state mutation to
    company_intelligence.services.evidence_review.apply_review_decision(),
    the SAME function the dedicated Evidence Review Workbench
    (review_views.py, feat/evidence-review-workbench PR 12) uses, so there
    is exactly one place a KPI link's review_state/relationship is ever
    mutated, never two diverging copies of this logic.
    """
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)

    link_id = request.POST.get('kpi_evidence_link_id')
    action = request.POST.get('action')
    reason = request.POST.get('reason', '')

    from company_intelligence.services import evidence_review

    if action not in evidence_review.ACTION_TRANSITIONS:
        messages.error(request, 'Invalid review action.')
        return redirect('companies:detail', slug=slug)

    link = get_object_or_404(
        CompanyKPIEvidenceLink, pk=link_id, assessment__company=profile,
    )
    evidence_review.apply_review_decision(link, action, request.user, reason=reason)

    messages.success(request, f'Recorded "{dict(EvidenceReviewAction.ACTION_CHOICES)[action]}" for this evidence link.')
    return redirect('companies:detail', slug=slug)
