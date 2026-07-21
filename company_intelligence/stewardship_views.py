"""
company_intelligence/stewardship_views.py — feat/stewardship-universe
(PR 13): the Stewardship Universe operational surface. Deliberately
staff-only throughout, same convention as review_views.py — this is an
internal governance/ops tool ("what does EcoIQ track and how healthy is
its evidence base?"), NOT the public research surface (that remains
Discover Companies). Views orchestrate only; all computation lives in
services/stewardship_state.py, source_discovery.py, source_registry.py,
and refresh_orchestrator.py.
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from companies.models import CompanyProfile
from league.models import Company

from company_intelligence.services import change_timeline, refresh_orchestrator, source_registry, stewardship_state


def _profile_or_404(slug):
    company = get_object_or_404(Company, slug=slug)
    return get_object_or_404(CompanyProfile, company=company)


@staff_member_required(login_url='/login/')
def universe_view(request):
    """/companies/universe/ — every tracked (or trackable) company, its
    derived operational state, and its real health indicators. Companies
    with tracking_status='not_tracked' are included too (so staff can see
    what's available to start tracking), clearly labelled as such."""
    profiles = CompanyProfile.objects.select_related('company').order_by('company__name')

    rows = []
    for profile in profiles:
        health = stewardship_state.compute_company_health(profile)
        state = stewardship_state.compute_tracking_state(profile, health=health)
        open_alerts_count = profile.stewardship_alerts.exclude(state__in=('resolved', 'dismissed')).count()
        open_conflicts_count = profile.change_events.filter(event_type='potential_conflict').exclude(
            kpi_evidence_link__review_state__in=('confirmed', 'rejected'),
        ).count()
        latest_change = profile.change_events.order_by('-detected_at').first()
        rows.append({
            'profile': profile, 'health': health, 'state': state,
            'open_alerts_count': open_alerts_count, 'open_conflicts_count': open_conflicts_count,
            'latest_change': latest_change,
        })

    state_filter = request.GET.get('state', '')
    if state_filter:
        rows = [r for r in rows if r['state']['state'] == state_filter]

    return render(request, 'company_intelligence/universe.html', {
        'rows': rows,
        'state_choices': list(stewardship_state.DERIVED_STATE_LABELS.items()),
        'state_filter': state_filter,
    })


@staff_member_required(login_url='/login/')
def company_status_view(request, slug):
    """/companies/<slug>/status/ — "where did this company's intelligence
    come from?" One operational page: sources, documents, evidence, KPI
    candidates, review state, refresh history, Observatory sessions."""
    profile = _profile_or_404(slug)
    health = stewardship_state.compute_company_health(profile)
    state = stewardship_state.compute_tracking_state(profile, health=health)
    registry_rows = source_registry.source_registry_rows(profile)
    refresh_runs = profile.refresh_runs.select_related('observatory_session', 'actor')[:20]
    observatory_sessions = profile.observatory_sessions.order_by('-started_at')[:20]
    open_alerts = profile.stewardship_alerts.exclude(state__in=('resolved', 'dismissed')).select_related('change_event')[:20]
    timeline = change_timeline.company_change_timeline(profile, limit=40)

    return render(request, 'company_intelligence/company_status.html', {
        'profile': profile, 'company': profile.company,
        'health': health, 'state': state,
        'registry_rows': registry_rows,
        'refresh_runs': refresh_runs,
        'observatory_sessions': observatory_sessions,
        'open_alerts': open_alerts,
        'timeline': timeline,
    })


@staff_member_required(login_url='/login/')
def trigger_refresh_view(request, slug):
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)
    dry_run = request.POST.get('dry_run') == '1'

    result = refresh_orchestrator.refresh_company_intelligence(
        profile, actor=request.user, triggered_by='manual', dry_run=dry_run,
    )

    if dry_run:
        messages.info(
            request,
            f"Dry run: {result['sources_due']} of {result['sources_total']} registered source(s) are due — "
            f"nothing was fetched or changed.",
        )
    elif isinstance(result, dict) and result.get('error') in ('paused', 'already_refreshing'):
        messages.warning(request, result['note'])
    else:
        summary = (
            f"Refresh {result.get_status_display()} — {result.sources_checked} source(s) checked, "
            f"{result.sources_failed} failed, {result.documents_new} new document(s), "
            f"{result.documents_unchanged} unchanged, {result.kpi_candidates_proposed} KPI candidate(s) proposed."
        )
        if result.status == 'failed':
            messages.error(request, summary)
        elif result.status == 'partial':
            messages.warning(request, summary)
        else:
            messages.success(request, summary)
        for w in result.warnings:
            messages.info(request, w)
        for e in result.errors:
            messages.error(request, e)

    return redirect('companies:company_status', slug=slug)


@staff_member_required(login_url='/login/')
def approve_source_view(request, slug, source_id):
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)
    from company_intelligence.models import DiscoveredSource

    discovered = get_object_or_404(DiscoveredSource, pk=source_id, company=profile)
    notes = request.POST.get('notes', '').strip()
    try:
        source_registry.approve_discovered_source(discovered, actor=request.user, notes=notes)
        messages.success(request, f'Source approved and registered: {discovered.url}')
    except ValueError as exc:
        messages.error(request, f'Could not register this source: {exc}')
    return redirect('companies:company_status', slug=slug)


@staff_member_required(login_url='/login/')
def reject_source_view(request, slug, source_id):
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)
    from company_intelligence.models import DiscoveredSource

    discovered = get_object_or_404(DiscoveredSource, pk=source_id, company=profile)
    reason = request.POST.get('reason', '').strip()
    source_registry.reject_discovered_source(discovered, actor=request.user, reason=reason)
    messages.success(request, f'Source rejected: {discovered.url}')
    return redirect('companies:company_status', slug=slug)


@staff_member_required(login_url='/login/')
def pause_tracking_view(request, slug):
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)
    profile.tracking_status = 'paused'
    profile.save(update_fields=['tracking_status'])
    messages.success(request, f'{profile.company.name} tracking paused.')
    return redirect('companies:company_status', slug=slug)


@staff_member_required(login_url='/login/')
def resume_tracking_view(request, slug):
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)
    profile.tracking_status = 'active'
    profile.save(update_fields=['tracking_status'])
    messages.success(request, f'{profile.company.name} tracking resumed.')
    return redirect('companies:company_status', slug=slug)
