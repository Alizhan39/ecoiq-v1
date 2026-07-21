"""
company_intelligence/monitor_views.py — feat/stewardship-monitor (PR 14):
the compact staff-facing Stewardship Monitor — operational intelligence
about the health of EcoIQ's own evidence supply chain, never an investor
marketing page. Staff-only throughout, same convention as
stewardship_views.py/review_views.py. Views orchestrate only; all
computation lives in services/stewardship_alerts.py,
services/change_timeline.py, and services/refresh_policy.py.
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from companies.models import CompanyProfile
from league.models import Company

from company_intelligence.models import CompanyRefreshRun, StewardshipAlert, StewardshipChangeEvent
from company_intelligence.services import refresh_policy, stewardship_alerts


def _profile_or_404(slug):
    company = get_object_or_404(Company, slug=slug)
    return get_object_or_404(CompanyProfile, company=company)


@staff_member_required(login_url='/login/')
def monitor_dashboard_view(request):
    """
    /companies/monitor/ — Monitoring Health, Recent Changes, Review
    Required, Potential Conflicts, Source Failures, Overdue Companies,
    Recent Refresh Runs, Scheduler Status. Every count here is a real,
    live query — no invented uptime percentage, no opaque health score.
    """
    tracked = CompanyProfile.objects.filter(tracking_status__in=('active', 'refresh_in_progress', 'error'))
    overdue = [p for p in tracked if refresh_policy.is_company_due_for_refresh(p)]

    last_run = CompanyRefreshRun.objects.order_by('-started_at').first()
    recent_runs = CompanyRefreshRun.objects.select_related('company__company', 'actor')[:15]
    recent_batch_partial_or_failed = CompanyRefreshRun.objects.filter(status__in=('partial', 'failed'))[:10]

    from harvester.models import Source

    # A source is "currently failing" when its most recent attempt was a
    # failure — i.e. no success has happened since the last recorded
    # failure. Computed in Python (not a queryset filter) since comparing
    # two nullable fields on the same row needs no vendor-specific F()
    # trick here — this list is small (active sources with any failure on
    # record) and never scanned per-request at scale.
    failing_sources = [
        s for s in Source.objects.filter(is_active=True, last_failure_at__isnull=False).select_related('company__company')
        if not s.last_success_at or s.last_success_at < s.last_failure_at
    ]

    open_conflicts = StewardshipChangeEvent.objects.filter(
        event_type='potential_conflict',
    ).exclude(
        kpi_evidence_link__review_state__in=('confirmed', 'rejected'),
    ).select_related('company__company')[:20]

    recent_changes = StewardshipChangeEvent.objects.select_related('company__company')[:25]
    open_alerts_qs = StewardshipAlert.objects.exclude(state__in=('resolved', 'dismissed')).select_related('company__company', 'change_event')
    review_required_alerts = open_alerts_qs.filter(change_event__review_required=True)[:25]
    open_alerts = open_alerts_qs[:25]

    health = {
        'tracked_companies': tracked.count(),
        'due_for_refresh': len([p for p in tracked if refresh_policy.is_company_due_for_refresh(p)]),
        'overdue_companies': len(overdue),
        'last_run_at': last_run.started_at if last_run else None,
        'last_run_status': last_run.get_status_display() if last_run else None,
        'partial_or_failed_recent_count': recent_batch_partial_or_failed.count(),
        'sources_currently_failing': len(failing_sources),
        'open_potential_conflicts': open_conflicts.count(),
        'open_alerts': open_alerts.count(),
    }

    return render(request, 'company_intelligence/monitor.html', {
        'health': health,
        'overdue': overdue,
        'recent_runs': recent_runs,
        'failing_sources': failing_sources,
        'open_conflicts': open_conflicts,
        'recent_changes': recent_changes,
        'open_alerts': open_alerts,
        'review_required_alerts': review_required_alerts,
    })


@staff_member_required(login_url='/login/')
def alert_acknowledge_view(request, slug, alert_id):
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)
    alert = get_object_or_404(StewardshipAlert, pk=alert_id, company=profile)
    stewardship_alerts.acknowledge_alert(alert, request.user)
    messages.success(request, 'Alert acknowledged.')
    return redirect('companies:company_status', slug=slug)


@staff_member_required(login_url='/login/')
def alert_resolve_view(request, slug, alert_id):
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)
    alert = get_object_or_404(StewardshipAlert, pk=alert_id, company=profile)
    reason = request.POST.get('reason', '').strip()
    stewardship_alerts.resolve_alert(alert, request.user, reason=reason)
    messages.success(request, 'Alert resolved.')
    return redirect('companies:company_status', slug=slug)


@staff_member_required(login_url='/login/')
def alert_dismiss_view(request, slug, alert_id):
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)
    alert = get_object_or_404(StewardshipAlert, pk=alert_id, company=profile)
    reason = request.POST.get('reason', '').strip()
    stewardship_alerts.dismiss_alert(alert, request.user, reason=reason)
    messages.success(request, 'Alert dismissed.')
    return redirect('companies:company_status', slug=slug)


@staff_member_required(login_url='/login/')
def refresh_diff_view(request, slug, run_id):
    """
    /companies/<slug>/status/refresh/<run_id>/diff/ — Before/After for one
    refresh run: this run's own real counters plus the exact
    StewardshipChangeEvent rows it produced. No invented summary — the
    "diff" IS the literal list of detected changes, nothing synthesized.
    """
    profile = _profile_or_404(slug)
    run = get_object_or_404(CompanyRefreshRun, pk=run_id, company=profile)

    previous_run = CompanyRefreshRun.objects.filter(
        company=profile, started_at__lt=run.started_at,
    ).order_by('-started_at').first()

    change_events = run.change_events.select_related('source', 'document', 'evidence', 'kpi_evidence_link').all()

    return render(request, 'company_intelligence/refresh_diff.html', {
        'profile': profile, 'company': profile.company,
        'run': run, 'previous_run': previous_run,
        'change_events': change_events,
    })
