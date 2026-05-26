"""
EcoIQ Industrial Transition Engine — Views.

/transition/                        → directory of company dashboards
/transition/<slug>/                 → company transition dashboard
/transition/<slug>/roadmap/<pk>/    → full roadmap detail
/transition/<slug>/generate/        → POST → generate new roadmap
/transition/financing/              → financing opportunity directory
/transition/financing/<pk>/         → financing detail
"""
import logging
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from league.models import Company
from transition.models import (
    TransitionRoadmap, TransitionPhase, FinancingOpportunity,
    FinancingMatch, TechnologyRecommendation, FacilityRecord,
    ROADMAP_TYPES,
)

logger = logging.getLogger(__name__)

# ── Index: list companies with transition readiness ────────────────────────────

@staff_member_required(login_url='/login/')
def index(request):
    companies = Company.objects.prefetch_related('roadmaps').order_by('-ecoiq_score')[:50]
    total_roadmaps = TransitionRoadmap.objects.count()
    total_financing = FinancingOpportunity.objects.filter(is_active=True).count()
    recent_roadmaps = TransitionRoadmap.objects.select_related('company').order_by('-created_at')[:8]

    return render(request, 'transition/index.html', {
        'companies': companies,
        'total_roadmaps': total_roadmaps,
        'total_financing': total_financing,
        'recent_roadmaps': recent_roadmaps,
        'roadmap_types': ROADMAP_TYPES,
    })


# ── Company transition dashboard ───────────────────────────────────────────────

@staff_member_required(login_url='/login/')
def dashboard(request, slug):
    company  = get_object_or_404(Company, slug=slug)
    roadmaps = company.roadmaps.prefetch_related(
        'phases', 'financing_matches__opportunity', 'tech_recs'
    ).order_by('-created_at')
    facilities = company.facilities.order_by('facility_type', 'name')
    tech_recs  = TechnologyRecommendation.objects.filter(
        company=company, roadmap__isnull=True
    ).order_by('priority')[:6]

    # Aggregate stats
    active_roadmap = roadmaps.filter(status='active').first() or roadmaps.first()
    total_capex = sum((r.total_capex_usd or 0) for r in roadmaps)
    co2_potential = sum((r.co2_reduction_tonnes or 0) for r in roadmaps)

    return render(request, 'transition/dashboard.html', {
        'company': company,
        'roadmaps': roadmaps,
        'active_roadmap': active_roadmap,
        'facilities': facilities,
        'tech_recs': tech_recs,
        'total_capex': total_capex,
        'co2_potential': co2_potential,
        'roadmap_types': ROADMAP_TYPES,
    })


# ── Generate roadmap (POST) ────────────────────────────────────────────────────

@staff_member_required(login_url='/login/')
@require_POST
def generate_roadmap(request, slug):
    company      = get_object_or_404(Company, slug=slug)
    roadmap_type = request.POST.get('roadmap_type', 'full')

    # Validate roadmap_type
    valid_types = {k for k, _ in ROADMAP_TYPES}
    if roadmap_type not in valid_types:
        roadmap_type = 'full'

    try:
        from transition.engine import generate_roadmap as _gen, match_financing, recommend_technologies
        roadmap = _gen(company, roadmap_type)
        match_financing(roadmap)
        recommend_technologies(company, roadmap)
        return redirect('transition:roadmap', slug=company.slug, pk=roadmap.pk)
    except Exception as exc:
        logger.exception('Roadmap generation failed for %s', company.name)
        return render(request, 'transition/dashboard.html', {
            'company': company,
            'roadmaps': company.roadmaps.all(),
            'roadmap_types': ROADMAP_TYPES,
            'error': str(exc),
        })


# ── Roadmap detail ─────────────────────────────────────────────────────────────

@staff_member_required(login_url='/login/')
def roadmap_detail(request, slug, pk):
    company = get_object_or_404(Company, slug=slug)
    roadmap = get_object_or_404(TransitionRoadmap, pk=pk, company=company)
    phases  = roadmap.phases.order_by('number')
    matches = roadmap.financing_matches.select_related('opportunity').order_by('-match_score')
    tech_recs = roadmap.tech_recs.order_by('priority')

    # Build Gantt data for the timeline chart
    gantt_data = []
    cursor = 0
    for phase in phases:
        gantt_data.append({
            'name': phase.name,
            'start': cursor,
            'duration': phase.duration_months,
            'capex': phase.capex_usd or 0,
        })
        cursor += phase.duration_months

    return render(request, 'transition/roadmap.html', {
        'company': company,
        'roadmap': roadmap,
        'phases': phases,
        'matches': matches,
        'tech_recs': tech_recs,
        'gantt_data': gantt_data,
        'current_state': roadmap.current_state_json or {},
        'target_state': roadmap.target_state_json or {},
    })


# ── Financing directory ────────────────────────────────────────────────────────

@staff_member_required(login_url='/login/')
def financing_directory(request):
    source_type = request.GET.get('type', '')
    region      = request.GET.get('region', '')

    opps = FinancingOpportunity.objects.filter(is_active=True)
    if source_type:
        opps = opps.filter(source_type=source_type)
    # Group by source type
    from itertools import groupby
    opps_list = list(opps.order_by('source_type', 'institution_name'))

    source_groups = {}
    for opp in opps_list:
        key = opp.get_source_type_display()
        source_groups.setdefault(key, []).append(opp)

    from transition.models import FINANCING_SOURCE_TYPES
    return render(request, 'transition/financing.html', {
        'source_groups': source_groups,
        'all_opps': opps_list,
        'source_types': FINANCING_SOURCE_TYPES,
        'selected_type': source_type,
        'total_count': len(opps_list),
    })


# ── Financing detail ───────────────────────────────────────────────────────────

@staff_member_required(login_url='/login/')
def financing_detail(request, pk):
    opp = get_object_or_404(FinancingOpportunity, pk=pk)
    recent_matches = opp.matches.select_related('roadmap__company').order_by('-created_at')[:10]
    return render(request, 'transition/financing_detail.html', {
        'opp': opp,
        'recent_matches': recent_matches,
    })


# ── API: roadmap status (for async polling) ────────────────────────────────────

@staff_member_required(login_url='/login/')
def api_roadmap_status(request, pk):
    roadmap = get_object_or_404(TransitionRoadmap, pk=pk)
    return JsonResponse({
        'status': roadmap.status,
        'title': roadmap.title,
        'phase_count': roadmap.phase_count,
        'match_count': roadmap.financing_matches.count(),
    })
