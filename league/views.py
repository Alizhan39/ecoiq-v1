"""
EcoIQ Good Deeds League — public views.

/league/                  → leaderboard (public)
/league/<slug>/           → company profile (public)
"""
from django.shortcuts import render, get_object_or_404

from .models import Company, EnvironmentalProject, SECTOR_CHOICES
from .scoring import get_tier


# ── Leaderboard ────────────────────────────────────────────────────────────────

def leaderboard(request):
    """
    Public league table ranked by EcoIQ score.
    Optional ?sector= filter.
    """
    sector = request.GET.get('sector', '').strip()
    qs = Company.objects.prefetch_related('projects')

    if sector and sector != 'all':
        qs = qs.filter(sector=sector)

    companies = list(qs.order_by('rank', '-ecoiq_score', 'name'))

    # Annotate with tier info for the template (no leading underscore — DTL blocks those)
    for co in companies:
        co.tier = get_tier(float(co.ecoiq_score))

    # Aggregate totals for the stats bar
    all_cos = Company.objects.prefetch_related('projects')
    total_co2   = sum(c.total_co2_reduced for c in all_cos)
    total_inv   = sum(c.total_investment_usd for c in all_cos)
    total_hh    = sum(c.total_households_helped for c in all_cos)

    ctx = {
        'companies':    companies,
        'sector':       sector,
        'sector_choices': [('all', 'Все отрасли')] + list(SECTOR_CHOICES),
        'total_co2':    total_co2,
        'total_inv_m':  round(total_inv / 1_000_000) if total_inv else 0,
        'total_hh':     total_hh,
        'company_count': Company.objects.count(),
    }
    return render(request, 'league/leaderboard.html', ctx)


# ── Company profile ────────────────────────────────────────────────────────────

def company_profile(request, slug):
    company = get_object_or_404(Company, slug=slug)
    tier    = get_tier(float(company.ecoiq_score))

    projects_active    = company.projects.filter(status__in=['active', 'planned']).order_by('-start_date')
    projects_completed = company.projects.filter(status='completed').order_by('-completion_date')

    # Build pillar breakdown for the score bar chart
    pillars = [
        {'name': 'Pollution Footprint', 'name_ru': 'Загрязнение',  'weight': 35,
         'score': company.score_pollution_footprint},
        {'name': 'Reduction Progress',  'name_ru': 'Снижение',     'weight': 25,
         'score': company.score_reduction_progress},
        {'name': 'Investment',          'name_ru': 'Инвестиции',   'weight': 20,
         'score': company.score_investment},
        {'name': 'Transparency',        'name_ru': 'Прозрачность', 'weight': 10,
         'score': company.score_transparency},
        {'name': 'Community Impact',    'name_ru': 'Сообщество',   'weight': 10,
         'score': company.score_community_impact},
    ]

    # Spark-line data for trend chart (last 6 months of history)
    history_qs = company.history.order_by('date')[:12]
    history_labels = [str(h.date) for h in history_qs]
    history_scores = [float(h.ecoiq_score) for h in history_qs]

    evidence = company.evidence.select_related('project').order_by('-date_issued')

    ctx = {
        'company':            company,
        'tier':               tier,
        'pillars':            pillars,
        'projects_active':    projects_active,
        'projects_completed': projects_completed,
        'evidence':           evidence,
        'history_labels':     history_labels,
        'history_scores':     history_scores,
    }
    return render(request, 'league/company.html', ctx)
