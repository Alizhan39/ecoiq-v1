"""
company_intelligence/discovery_views.py — feat/company-discovery-ranking
(PR 11): "Discover Companies" — evidence-driven company discovery across
two independent lenses (preliminary Shariah screening, 114-KPI evidence
coverage). Views here ORCHESTRATE only — all scoring/filtering logic lives
in services/discovery_engine.py and services/match_trace.py; nothing is
duplicated in a template.

Every view is either a public, GET-only read (matching companies.
company_detail's existing convention) or a staff-gated POST for a genuinely
stateful action (registering a new official document source — the same
@staff_member_required discipline PR10 already established for
refresh_company_view/evidence_review_action_view).
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from companies.models import CompanyProfile
from league.models import Company, SECTOR_CHOICES

from company_intelligence.models import CompanyShariahScreen
from company_intelligence.services import discovery_engine
from company_intelligence.services.match_trace import explain_company_match
from core.esg_principles_data import PRINCIPLE_CATEGORIES, PRINCIPLES

PRINCIPLES_BY_ID = {p['id']: p for p in PRINCIPLES}
SHARIAH_STATUS_CHOICES = [c for c, _ in CompanyShariahScreen._meta.get_field('overall_result').choices]


def _profile_or_404(slug):
    company = get_object_or_404(Company, slug=slug)
    return get_object_or_404(CompanyProfile, company=company, status__in=('public', 'verified', 'draft'))


def _criteria_from_request(request):
    """
    One shared query-param convention for both discover_companies_view and
    explain_match_view, so a link from a discovery result row to Explain
    Match carries the exact same criteria the discovery view used — never
    a re-derived, possibly-drifted second interpretation of the same
    filters.
    """
    kpi_ids = [int(v) for v in request.GET.getlist('kpi') if v.isdigit() and int(v) in PRINCIPLES_BY_ID]
    shariah_status = [v for v in request.GET.getlist('shariah') if v in SHARIAH_STATUS_CHOICES or v == 'not_screened']
    tier_raw = request.GET.get('tier', '')
    min_source_tier = int(tier_raw) if tier_raw.isdigit() else None

    min_confirmed_raw = request.GET.get('min_confirmed_kpi', '')
    min_confirmed_kpi_coverage = int(min_confirmed_raw) if min_confirmed_raw.isdigit() else None

    min_reviewed_raw = request.GET.get('min_human_reviewed_pct', '')
    try:
        min_human_reviewed_pct = float(min_reviewed_raw) if min_reviewed_raw else None
    except ValueError:
        min_human_reviewed_pct = None

    def _tri_state(param_name):
        raw = request.GET.get(param_name, '')
        if raw == '1':
            return True
        if raw == '0':
            return False
        return None

    from company_intelligence.services.stewardship_state import DERIVED_STATE_LABELS

    monitoring_health_raw = request.GET.get('monitoring_health', '')
    monitoring_health = monitoring_health_raw if monitoring_health_raw in DERIVED_STATE_LABELS else ''

    return {
        'kpi_ids': kpi_ids,
        'shariah_status': shariah_status,
        'sector': request.GET.get('sector', ''),
        'country': request.GET.get('country', ''),
        'min_source_tier': min_source_tier,
        'require_current_screening': request.GET.get('fresh') == '1',
        'controversy_state': request.GET.get('controversy', 'any'),
        'include_demo': request.GET.get('include_demo') == '1',
        'min_confirmed_kpi_coverage': min_confirmed_kpi_coverage,
        'min_human_reviewed_pct': min_human_reviewed_pct,
        'has_disputes': _tri_state('has_disputes'),
        'has_potential_conflicts': _tri_state('has_potential_conflicts'),
        'monitoring_health': monitoring_health,
    }


def discover_companies_view(request):
    """
    /companies/discover/ — the primary discovery surface. Demo companies
    are excluded by default (criteria['include_demo'] defaults False); no
    BUY/SELL/HOLD/target-price language anywhere on this page or the
    services behind it.
    """
    from ai_observatory.services import recorder

    criteria = _criteria_from_request(request)

    session = recorder.start_session(kind='company_discovery', user=request.user)
    with recorder.record_stage(session, 'filtering', 'Company Filtering', category='deterministic') as info:
        companies = discovery_engine.discover_companies(criteria)
        info['items_processed'] = len(companies)
        info['metadata'] = {'criteria': criteria}
    with recorder.record_stage(session, 'ranking', 'Evidence-Backed Ranking', category='deterministic') as info:
        results = discovery_engine.rank_company_matches(companies, criteria=criteria)
        info['items_processed'] = len(results)
    recorder.finish_session(session, evidence_retrieved=len(results), final_recommendation_status='recorded')

    principles_by_category = {}
    for p in PRINCIPLES:
        principles_by_category.setdefault(p['category'], []).append(p)
    # Django templates cannot look up a dict value by a loop variable key
    # (no `{{ dict|attr:key }}` filter) — resolved here in Python, same
    # discipline as PR10's CompanyFinancialFactSource.value property.
    kpi_picker_groups = [
        {'key': cat_key, 'label': cat_label, 'principles': principles_by_category.get(cat_key, [])}
        for cat_key, cat_label in PRINCIPLE_CATEGORIES
    ]

    from company_intelligence.services.stewardship_state import DERIVED_STATE_LABELS

    return render(request, 'company_intelligence/discover.html', {
        'criteria': criteria,
        'results': results,
        'result_count': len(results),
        'kpi_picker_groups': kpi_picker_groups,
        'sector_choices': SECTOR_CHOICES,
        'shariah_status_choices': CompanyShariahScreen._meta.get_field('overall_result').choices,
        'weights': discovery_engine.DEFAULT_RANKING_WEIGHTS,
        'monitoring_health_choices': list(DERIVED_STATE_LABELS.items()),
    })


def strongest_alignment_view(request):
    """
    /companies/strongest-alignment/ — feat/global-stewardship-universe
    (PR 15) Section 12: a dedicated view answering "which real companies
    currently have the strongest verified evidence of alignment with
    EcoIQ's 114 stewardship KPIs?" Reuses discover_companies()/
    rank_company_matches() verbatim (never a second ranking engine) — the
    only difference from Discover Companies is presentation: sorted
    strictly by the Evidence-Backed Stewardship Alignment Indicator
    (already how rank_company_matches sorts), and companies with zero
    CONFIRMED KPI-supporting evidence are excluded here rather than merely
    sorted with the rest. This is deliberate: kpi_alignment's own "absence
    of evidence is neutral, not negative" component (discovery_engine's own
    module docstring) means composite is almost never literally None, so
    filtering on composite alone would let an entirely unevidenced company
    appear in a "strongest alignment" list — misleading for this specific,
    more claim-heavy view (Discover Companies still shows every candidate,
    evidence or not).

    Mandatory disclaimer text (Section 12's own words, rendered verbatim
    in the template): "Research ranking based on currently available and
    reviewed stewardship evidence. This is not investment advice or a
    prediction of financial performance."
    """
    from ai_observatory.services import recorder

    criteria = _criteria_from_request(request)

    session = recorder.start_session(kind='company_discovery', user=request.user)
    with recorder.record_stage(session, 'filtering', 'Company Filtering', category='deterministic') as info:
        companies = discovery_engine.discover_companies(criteria)
        info['items_processed'] = len(companies)
        info['metadata'] = {'criteria': criteria}
    with recorder.record_stage(session, 'ranking', 'Evidence-Backed Ranking', category='deterministic') as info:
        results = [
            r for r in discovery_engine.rank_company_matches(companies, criteria=criteria)
            if r['kpi_detail']['supported_kpi_ids']
        ]
        info['items_processed'] = len(results)
    recorder.finish_session(session, evidence_retrieved=len(results), final_recommendation_status='recorded')

    return render(request, 'company_intelligence/strongest_alignment.html', {
        'criteria': criteria,
        'results': results,
        'result_count': len(results),
        'weights': discovery_engine.DEFAULT_RANKING_WEIGHTS,
    })


def explain_match_view(request, slug):
    """
    /companies/<slug>/explain-match/ — "Why does this company appear (and
    rank where it does) under my selected criteria?" Same query-param
    criteria convention as discover_companies_view.
    """
    profile = _profile_or_404(slug)
    criteria = _criteria_from_request(request)
    trace = explain_company_match(profile, criteria=criteria)
    return render(request, 'company_intelligence/explain_match.html', {
        'profile': profile, 'company': profile.company, 'trace': trace, 'criteria': criteria,
    })


def _comparison_extras_for_company(company_profile):
    """
    feat/global-stewardship-universe (PR 15) Section 14 — the extra
    comparison rows the brief asks for (methodology version, human-reviewed
    evidence, category coverage, disputes, potential conflicts, staleness,
    monitoring health, last refresh). Every value here is a straight read
    from an existing PR9-14 service — never a second comparison-only
    computation of something already computed elsewhere.
    """
    from company_intelligence.models import CompanyKPIEvidenceLink, StewardshipAlert
    from company_intelligence.services import (
        alignment_metrics, coverage_matrix, evidence_provenance, shariah_screening, stewardship_state,
    )

    metrics = alignment_metrics.stewardship_alignment_metrics(company_profile)
    coverage = coverage_matrix.coverage_matrix_for_company(company_profile)
    tracking = stewardship_state.compute_tracking_state(company_profile)
    screen = shariah_screening.latest_screen_for(company_profile)

    disputed_count = CompanyKPIEvidenceLink.objects.filter(
        assessment__company=company_profile, review_state='disputed',
    ).values('assessment__kpi_id').distinct().count()
    open_conflicts_count = StewardshipAlert.objects.filter(
        company=company_profile, alert_type='potential_conflict',
    ).exclude(state__in=('resolved', 'dismissed')).count()

    return {
        'methodology_version': f'{screen.methodology.name} v{screen.methodology.version}' if screen else 'Not screened',
        'metrics': metrics,
        'coverage': coverage,
        'self_report_concentration': evidence_provenance.self_report_concentration(company_profile),
        'evidence_concentration_warnings': evidence_provenance.evidence_concentration_warning(company_profile),
        'disputed_count': disputed_count,
        'open_conflicts_count': open_conflicts_count,
        'monitoring_health': tracking,
        'last_refresh_at': company_profile.last_refresh_at,
    }


def company_comparison_view(request):
    """
    /companies/compare/?companies=slug1,slug2,slug3 — 2-5 companies, side
    by side, on real evidence-backed criteria only. Never expected returns,
    price targets, or trading signals (see discovery_engine's own scope
    discipline).
    """
    from ai_observatory.services import recorder

    slugs = [s.strip() for s in request.GET.get('companies', '').split(',') if s.strip()][:5]
    profiles = []
    for slug in slugs:
        try:
            profiles.append(_profile_or_404(slug))
        except Http404:
            continue

    criteria = _criteria_from_request(request)
    session = recorder.start_session(kind='company_discovery', user=request.user)
    with recorder.record_stage(session, 'comparison', 'Company Comparison', category='deterministic') as info:
        comparison = discovery_engine.compare_companies(profiles, criteria=criteria) if len(profiles) >= 2 else []
        for row in comparison:
            row['extras'] = _comparison_extras_for_company(row['company'])
        info['items_processed'] = len(comparison)
        info['metadata'] = {'slugs': slugs}
    recorder.finish_session(session, evidence_retrieved=len(comparison), final_recommendation_status='recorded')

    return render(request, 'company_intelligence/compare.html', {
        'comparison': comparison, 'slugs': slugs, 'criteria': criteria,
        'too_few': len(profiles) < 2,
    })


@staff_member_required(login_url='/login/')
def register_document_source_view(request, slug):
    """
    POST-only, staff-only. Registers (or reuses) a real, staff-provided
    official document URL as a harvester.Source for this company, then
    immediately ingests it — mirroring PR10's refresh_company_view
    discipline ("a staff-triggered fetch is acceptable"). Never fabricates
    a document URL: this view only ever fetches what staff explicitly typed
    in.
    """
    if request.method != 'POST':
        raise Http404()
    profile = _profile_or_404(slug)

    source_url = request.POST.get('source_url', '').strip()
    document_type = request.POST.get('document_type', '')
    publisher = request.POST.get('publisher', '').strip()

    from harvester.constants import SOURCE_TYPES
    valid_types = {t for t, _ in SOURCE_TYPES}
    if not source_url or document_type not in valid_types:
        messages.error(request, 'A valid document URL and document type are required.')
        return redirect('companies:detail', slug=slug)

    from company_intelligence.services.url_safety import is_safe_external_url

    is_safe, reason = is_safe_external_url(source_url)
    if not is_safe:
        messages.error(request, f'This URL cannot be registered: {reason}')
        return redirect('companies:detail', slug=slug)

    from company_intelligence.services.evidence_ingestion import ingest_sustainability_document

    try:
        result = ingest_sustainability_document(profile, source_url, document_type, publisher=publisher, actor=request.user)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Sustainability document ingestion failed for company %s', profile.pk)
        messages.error(request, 'Document ingestion failed unexpectedly — nothing was changed.')
        return redirect('companies:detail', slug=slug)

    run = result['ingestion_run']
    if run and run.status == 'failed':
        messages.warning(request, f'Document fetch failed: {run.error_message}')
    elif run and run.status == 'skipped':
        messages.warning(request, 'Document fetch was skipped — check the URL is reachable and not disallowed by robots.txt.')
    else:
        messages.success(
            request,
            f'Document registered and ingested — {len(result["kpi_candidates_proposed"])} new KPI candidate(s) proposed '
            f'for human review.',
        )
    for w in result['warnings']:
        messages.info(request, w)
    return redirect('companies:detail', slug=slug)
