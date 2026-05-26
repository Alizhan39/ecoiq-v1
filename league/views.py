"""
EcoIQ Good Deeds League — public views.

/league/                  → leaderboard (public)
/league/<slug>/           → company ESG intelligence profile (public)
"""
import json
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

from .models import Company, EnvironmentalProject, SECTOR_CHOICES
from .scoring import get_tier


# ── SDG mapping ────────────────────────────────────────────────────────────────

_SDG_MAP = {
    'coal_stove':    [3, 7, 11, 13],
    'gasification':  [7, 11, 13],
    'methane':       [13, 15],
    'renewable':     [7, 9, 13],
    'water_cleanup': [6, 14, 15],
    'filters':       [3, 9, 11],
    'tree_planting': [13, 15],
    'power_modern':  [7, 9, 11],
    'waste':         [12, 13],
    'other':         [9, 13],
}

# Full UN SDG catalogue: (number, short label, official hex colour)
_SDG_ALL = [
    (1,  'No Poverty',              '#e5243b'),
    (2,  'Zero Hunger',             '#dda63a'),
    (3,  'Good Health',             '#4c9f38'),
    (4,  'Quality Education',       '#c5192d'),
    (5,  'Gender Equality',         '#ff3a21'),
    (6,  'Clean Water',             '#26bde2'),
    (7,  'Clean Energy',            '#fcc30b'),
    (8,  'Decent Work',             '#a21942'),
    (9,  'Industry & Innovation',   '#fd6925'),
    (10, 'Reduced Inequalities',    '#dd1367'),
    (11, 'Sustainable Cities',      '#fd9d24'),
    (12, 'Responsible Consumption', '#bf8b2e'),
    (13, 'Climate Action',          '#3f7e44'),
    (14, 'Life Below Water',        '#0a97d9'),
    (15, 'Life on Land',            '#56c02b'),
    (16, 'Peace & Justice',         '#00689d'),
    (17, 'Partnerships',            '#19486a'),
]
_SDG_LOOKUP = {num: (label, color) for num, label, color in _SDG_ALL}


# ── Project type metadata ──────────────────────────────────────────────────────

PROJECT_TYPE_META = {
    'coal_stove':    {'label': 'Coal Stove Replacement', 'icon': '🏠', 'accent': '#8B4513'},
    'gasification':  {'label': 'Gasification',           'icon': '🔥', 'accent': '#e67e22'},
    'methane':       {'label': 'Methane Reduction',       'icon': '⚗️',  'accent': '#f39c12'},
    'renewable':     {'label': 'Renewable Energy',        'icon': '♻️',  'accent': '#27ae60'},
    'water_cleanup': {'label': 'Water Clean-up',          'icon': '💧', 'accent': '#2980b9'},
    'filters':       {'label': 'Industrial Filters',      'icon': '🔬', 'accent': '#8e44ad'},
    'tree_planting': {'label': 'Tree Planting',           'icon': '🌳', 'accent': '#2d6a4f'},
    'power_modern':  {'label': 'Power Modernisation',     'icon': '⚡', 'accent': '#2c3e50'},
    'waste':         {'label': 'Waste Reduction',         'icon': '♻️',  'accent': '#7f8c8d'},
    'other':         {'label': 'Other Initiative',        'icon': '🌱', 'accent': '#16a085'},
}

# Stub AI recommendations — generated from pillar score gaps
def _stub_recommendations(company, projects):
    sdg_lkp = _SDG_LOOKUP
    recs = []

    if company.score_pollution_footprint < 60:
        recs.append({
            'priority': 'critical', 'priority_label': 'Critical',
            'icon': '📡',
            'title': 'Deploy Continuous Emissions Monitoring (CEMS)',
            'impact': 'Pollution Footprint +8–15 pts',
            'rationale': (
                'No real-time stack monitoring found in the evidence base. '
                'CEMS provides tamper-evident, near-real-time telemetry that '
                'satisfies both Kazakhstan Environmental Code (2022) Tier-1 '
                'requirements and MSCI ESG data quality thresholds.'
            ),
            'sdgs': [
                {'num': n, 'label': sdg_lkp[n][0], 'color': sdg_lkp[n][1]}
                for n in [9, 11, 13] if n in sdg_lkp
            ],
        })

    if company.score_reduction_progress < 60:
        recs.append({
            'priority': 'high', 'priority_label': 'High',
            'icon': '🎯',
            'title': 'Set a Science-Based Emissions Reduction Target (SBTi)',
            'impact': 'Reduction Progress +10–18 pts',
            'rationale': (
                'No independently verified GHG pathway detected. '
                'An SBTi 1.5 °C-aligned commitment unlocks green bond eligibility, '
                'improves Bloomberg ESG score inputs, and signals credibility '
                'to institutional investors applying Paris-aligned screening.'
            ),
            'sdgs': [
                {'num': n, 'label': sdg_lkp[n][0], 'color': sdg_lkp[n][1]}
                for n in [13, 17] if n in sdg_lkp
            ],
        })

    if company.score_investment < 60:
        recs.append({
            'priority': 'high', 'priority_label': 'High',
            'icon': '💚',
            'title': f'Increase Environmental Capex to ≥1% of Annual Revenue',
            'impact': 'Investment pillar +12–20 pts',
            'rationale': (
                'Current clean investment appears below the sector median for '
                f'{company.get_sector_display()}. The 1% annual revenue threshold '
                'is the MSCI ESG benchmark used to distinguish "credible commitment" '
                'from "token compliance" in heavy-industry ratings.'
            ),
            'sdgs': [
                {'num': n, 'label': sdg_lkp[n][0], 'color': sdg_lkp[n][1]}
                for n in [9, 13] if n in sdg_lkp
            ],
        })

    if company.score_transparency < 65:
        recs.append({
            'priority': 'medium', 'priority_label': 'Medium',
            'icon': '📊',
            'title': 'Publish Annual GRI/TCFD-Aligned Sustainability Report',
            'impact': 'Transparency +15–25 pts',
            'rationale': (
                'No GRI Standards, TCFD framework, or CDP disclosure found. '
                'Annual third-party assured reporting is now expected of all '
                'Tier-1 permitted emitters under Kazakhstan\'s Environmental '
                'Code revision (2022), and required for S&P 500 supply-chain ESG audits.'
            ),
            'sdgs': [
                {'num': n, 'label': sdg_lkp[n][0], 'color': sdg_lkp[n][1]}
                for n in [16, 17] if n in sdg_lkp
            ],
        })

    if company.score_community_impact < 60:
        recs.append({
            'priority': 'medium', 'priority_label': 'Medium',
            'icon': '🌡️',
            'title': 'Launch Open Community Air Quality Monitoring Network',
            'impact': 'Community Impact +8–14 pts',
            'rationale': (
                'No community-accessible environmental monitoring found near '
                'primary facilities. Low-cost sensor networks with open data APIs '
                '(PurpleAir / IQAir AirVisual) cost <$50K to deploy city-wide '
                'and directly feed EcoIQ Community Impact scoring.'
            ),
            'sdgs': [
                {'num': n, 'label': sdg_lkp[n][0], 'color': sdg_lkp[n][1]}
                for n in [3, 11] if n in sdg_lkp
            ],
        })

    return recs[:4]


# ── Leaderboard ────────────────────────────────────────────────────────────────

def leaderboard(request):
    """Public league table ranked by EcoIQ score with optional sector filter."""
    sector = request.GET.get('sector', '').strip()
    qs = Company.objects.prefetch_related('projects')

    if sector and sector != 'all':
        qs = qs.filter(sector=sector)

    companies = list(qs.order_by('rank', '-ecoiq_score', 'name'))

    # Annotate with tier + EcoIQ Intelligence profile if available
    _profile_map = {}
    try:
        from companies.models import CompanyProfile
        for p in CompanyProfile.objects.filter(
            company__in=[c.pk for c in companies],
            status__in=('public', 'verified'),
        ).select_related('company'):
            _profile_map[p.company_id] = p
    except Exception:
        pass

    for co in companies:
        co.tier = get_tier(float(co.ecoiq_score))
        co.ecoiq_profile = _profile_map.get(co.pk)

    all_cos   = Company.objects.prefetch_related('projects')
    total_co2 = sum(c.total_co2_reduced for c in all_cos)
    total_inv = sum(c.total_investment_usd for c in all_cos)
    total_hh  = sum(c.total_households_helped for c in all_cos)

    # ── Analytics chart data ──────────────────────────────────────────────────
    SECTOR_LABEL = dict(SECTOR_CHOICES)
    from collections import defaultdict
    _sector_scores = defaultdict(list)
    for co in all_cos:
        _sector_scores[co.sector].append(float(co.ecoiq_score))

    chart_sectors = json.dumps(sorted([
        {
            'label': SECTOR_LABEL.get(s, s.replace('_', ' ').title()),
            'avg':   round(sum(v) / len(v), 1),
            'count': len(v),
        }
        for s, v in _sector_scores.items()
    ], key=lambda x: x['avg'], reverse=True))

    _all_ranked = list(all_cos.order_by('rank', '-ecoiq_score')[:15])
    chart_companies = json.dumps([
        {
            'name':         co.name[:22] + ('…' if len(co.name) > 22 else ''),
            'score':        float(co.ecoiq_score),
            'pollution':    co.score_pollution_footprint,
            'reduction':    co.score_reduction_progress,
            'investment':   co.score_investment,
            'transparency': co.score_transparency,
            'community':    co.score_community_impact,
            'tier':         get_tier(float(co.ecoiq_score)).css,
        }
        for co in _all_ranked
    ])

    return render(request, 'league/leaderboard.html', {
        'companies':         companies,
        'sector':            sector,
        'sector_choices':    [('all', 'All Sectors')] + list(SECTOR_CHOICES),
        'total_co2':         total_co2,
        'total_inv_m':       round(total_inv / 1_000_000) if total_inv else 0,
        'total_hh':          total_hh,
        'company_count':     Company.objects.count(),
        'chart_sectors':     chart_sectors,
        'chart_companies':   chart_companies,
    })


# ── Company ESG profile ────────────────────────────────────────────────────────

def company_profile(request, slug):
    from datetime import date, timedelta
    import math as _math

    company = get_object_or_404(
        Company.objects.prefetch_related('projects', 'evidence', 'history'),
        slug=slug,
    )
    tier = get_tier(float(company.ecoiq_score))

    # ── Projects ──────────────────────────────────────────────────────────────
    all_projects       = list(company.projects.order_by('start_date', 'name'))
    projects_completed = [p for p in all_projects if p.status == 'completed']
    projects_active    = [p for p in all_projects if p.status == 'active']
    projects_planned   = [p for p in all_projects if p.status == 'planned']

    for p in all_projects:
        p.type_meta = PROJECT_TYPE_META.get(p.project_type, PROJECT_TYPE_META['other'])

    # ── Pillars ───────────────────────────────────────────────────────────────
    pillars = [
        {'key': 'pollution',    'name': 'Pollution Footprint', 'name_ru': 'Pollution',    'weight': 35, 'score': company.score_pollution_footprint,  'color': '#ef4444'},
        {'key': 'reduction',    'name': 'Reduction Progress',  'name_ru': 'Reduction',    'weight': 25, 'score': company.score_reduction_progress,   'color': '#22c55e'},
        {'key': 'investment',   'name': 'Investment',          'name_ru': 'Investment',   'weight': 20, 'score': company.score_investment,           'color': '#3b82f6'},
        {'key': 'transparency', 'name': 'Transparency',        'name_ru': 'Transparency', 'weight': 10, 'score': company.score_transparency,         'color': '#f59e0b'},
        {'key': 'community',    'name': 'Community Impact',    'name_ru': 'Community',    'weight': 10, 'score': company.score_community_impact,     'color': '#8b5cf6'},
    ]

    # ── Score history ─────────────────────────────────────────────────────────
    history_qs           = list(company.history.order_by('date'))
    history_labels       = [str(h.date)[:7] for h in history_qs]
    history_scores       = [float(h.ecoiq_score) for h in history_qs]
    history_pollution    = [h.score_pollution_footprint for h in history_qs]
    history_reduction    = [h.score_reduction_progress  for h in history_qs]
    history_invest       = [h.score_investment           for h in history_qs]
    history_transparency = [h.score_transparency         for h in history_qs]
    history_community    = [h.score_community_impact     for h in history_qs]

    # ── Year-on-year delta ────────────────────────────────────────────────────
    twelve_ago  = date.today() - timedelta(days=365)
    old_snap    = company.history.filter(date__lte=twelve_ago).order_by('-date').first()
    yoy_delta   = round(float(company.ecoiq_score) - float(old_snap.ecoiq_score), 1) if old_snap else None

    # ── Score history change table (last 6 snapshots) ─────────────────────────
    recent_snaps  = list(company.history.order_by('-date')[:7])
    score_changes = []
    for i in range(len(recent_snaps) - 1):
        cur  = recent_snaps[i]
        prev = recent_snaps[i + 1]
        score_changes.append({
            'date':  str(cur.date)[:7],
            'score': float(cur.ecoiq_score),
            'delta': round(float(cur.ecoiq_score) - float(prev.ecoiq_score), 1),
            'rank':  cur.rank,
        })

    # ── Sector intelligence ───────────────────────────────────────────────────
    sector_qs = Company.objects.filter(sector=company.sector)
    sector_total = sector_qs.count()
    sector_below = sector_qs.filter(ecoiq_score__lt=company.ecoiq_score).count()
    sector_percentile = round(sector_below / max(sector_total, 1) * 100)

    # Top 6 peers in same sector (include self for chart)
    sector_peers = list(
        Company.objects.filter(sector=company.sector)
        .order_by('-ecoiq_score')[:6]
    )
    peer_chart = json.dumps([
        {
            'name':  p.name[:22] + ('…' if len(p.name) > 22 else ''),
            'score': float(p.ecoiq_score),
            'tier':  get_tier(float(p.ecoiq_score)).css,
            'self':  (p.pk == company.pk),
        }
        for p in sector_peers
    ])

    # ── CO₂ analytics ─────────────────────────────────────────────────────────
    co2_completed  = sum(p.co2_reduction_tonnes or 0 for p in projects_completed)
    co2_active     = sum(p.co2_reduction_tonnes or 0 for p in projects_active)
    co2_planned    = sum(p.co2_reduction_tonnes or 0 for p in projects_planned)
    co2_total      = co2_completed + co2_active
    co2_cars_equiv = round(co2_total / 4.6) if co2_total else 0
    co2_trees_equiv= round(co2_total * 45)  if co2_total else 0

    # CO₂ time-series (24 months, derived from pollution history)
    _poll_24  = history_pollution[-24:] if history_pollution else []
    _labs_24  = history_labels[-24:]   if history_labels   else []
    # Simulate emission intensity: inverse of pollution score
    emissions_chart = json.dumps({
        'labels':    _labs_24,
        'intensity': [round(120 - s * 0.8 + (i % 5 - 2) * 3, 1) for i, s in enumerate(_poll_24)] if _poll_24 else [],
        'co2_seq':   [round(co2_total * (0.85 + 0.02 * i), 0) for i in range(len(_labs_24))]   if _poll_24 else [],
    })

    # Methane simulation (sector-dependent baseline)
    _methane_base = 90 if company.sector in ('oil_gas', 'mining') else 55
    methane_chart = json.dumps({
        'labels':   _labs_24,
        'methane':  [
            round(max(5, _methane_base - history_scores[-24:][i] * 0.35
                      + (_math.sin(i * 0.45) * 4)), 1)
            for i in range(len(_labs_24))
        ] if _labs_24 and history_scores else [],
        'limit':    100,
    })

    # ── Investment chart ──────────────────────────────────────────────────────
    inv_projects = sorted(
        [p for p in all_projects if p.investment_usd and p.start_date],
        key=lambda p: p.start_date,
    )
    inv_labels     = json.dumps([p.name[:30] + ('…' if len(p.name) > 30 else '') for p in inv_projects])
    inv_amounts    = json.dumps([round(p.investment_usd / 1_000_000, 1) for p in inv_projects])
    cum = 0
    inv_cum = []
    for p in inv_projects:
        cum += round(p.investment_usd / 1_000_000, 1)
        inv_cum.append(round(cum, 1))
    inv_cumulative = json.dumps(inv_cum)
    inv_colors = json.dumps([
        '#00e89a' if p.status == 'completed'
        else '#3b82f6' if p.status == 'active'
        else '#6b7280'
        for p in inv_projects
    ])

    # ── SDG alignment ─────────────────────────────────────────────────────────
    active_sdg_nums = set()
    for p in all_projects:
        active_sdg_nums.update(_SDG_MAP.get(p.project_type, []))
    sdg_grid = [
        {'num': num, 'label': label, 'color': color, 'active': num in active_sdg_nums}
        for num, label, color in _SDG_ALL
    ]
    sdg_active_count = sum(1 for s in sdg_grid if s['active'])

    # ── AI findings from linked jobs ──────────────────────────────────────────
    from audit.models import AIAnalysisJob, AIFinding, AIScoreEstimate  # noqa: F401
    latest_job = company.ai_jobs.filter(status='completed').order_by('-created_at').first()
    ai_findings = []
    ai_score_estimate = None
    greenwashing_data = None
    ai_job_meta = None
    if latest_job:
        ai_findings = list(
            latest_job.findings.filter(status='approved')
            .order_by('-confidence_score')[:10]
        )
        ai_job_meta = {
            'filename':  latest_job.original_filename,
            'year':      latest_job.detected_year,
            'summary':   latest_job.executive_summary[:300] if latest_job.executive_summary else '',
            'doc_type':  latest_job.detected_doc_type,
            'total':     latest_job.finding_count,
            'approved':  latest_job.approved_count,
            'date':      str(latest_job.completed_at)[:10] if latest_job.completed_at else '',
        }
        try:
            se = latest_job.score_estimate
            ai_score_estimate = se
            if se.greenwashing_score is not None:
                gw_score   = se.greenwashing_score
                gw_color   = (
                    '#ef4444' if gw_score >= 70 else
                    '#f59e0b' if gw_score >= 40 else
                    '#22c55e'
                )
                greenwashing_data = {
                    'score':   gw_score,
                    'level':   se.greenwashing_level,
                    'signals': se.greenwashing_signals or [],
                    'verdict': se.greenwashing_verdict,
                    'color':   gw_color,
                }
        except Exception:
            pass

    # Greenwashing gauge JSON for Chart.js
    gw_gauge_json = 'null'
    if greenwashing_data:
        gw_score_val = greenwashing_data['score']
        gw_color_val = greenwashing_data['color']
        gw_gauge_json = json.dumps({
            'score': gw_score_val,
            'color': gw_color_val,
        })

    # ── Evidence & disclosure completeness ────────────────────────────────────
    evidence     = list(company.evidence.select_related('project').order_by('-date_issued'))
    ev_verified  = sum(1 for e in evidence if e.verification_status == 'verified')
    ev_pending   = sum(1 for e in evidence if e.verification_status == 'pending')
    ev_rejected  = sum(1 for e in evidence if e.verification_status == 'rejected')

    _all_ev_types = ['audit_report', 'government_report', 'satellite',
                     'engineering_audit', 'photo', 'invoice', 'permit']
    _present_types = {e.doc_type for e in evidence}
    disclosure_completeness = round(len(_present_types & set(_all_ev_types)) / len(_all_ev_types) * 100)
    disclosure_missing = sorted(set(_all_ev_types) - _present_types)
    all_ev_types_list = [
        {'key': k, 'label': k.replace('_', ' ').title(), 'present': k in _present_types}
        for k in _all_ev_types
    ]

    ev_by_year = {}
    for ev in evidence:
        yr = ev.date_issued.year if ev.date_issued else 0
        ev_by_year.setdefault(yr, []).append(ev)
    transparency_history = sorted(ev_by_year.items(), reverse=True)

    # ── Roadmap ───────────────────────────────────────────────────────────────
    roadmap_projects = sorted(
        [p for p in all_projects if p.start_date],
        key=lambda p: p.start_date,
    )

    # ── SVG score arc ─────────────────────────────────────────────────────────
    score_arc = round(float(company.ecoiq_score) / 100 * 327, 1)

    # ── AI Recommendations (stub) ─────────────────────────────────────────────
    recommendations = _stub_recommendations(company, all_projects)

    ctx = {
        'company':   company,
        'tier':      tier,
        'pillars':   pillars,
        'score_arc': score_arc,

        # Ranking & sector
        'yoy_delta':          yoy_delta,
        'sector_percentile':  sector_percentile,
        'sector_total':       sector_total,
        'sector_peers':       sector_peers,
        'peer_chart':         peer_chart,
        'score_changes':      score_changes,

        # Projects
        'all_projects':       all_projects,
        'projects_completed': projects_completed,
        'projects_active':    projects_active,
        'projects_planned':   projects_planned,
        'roadmap_projects':   roadmap_projects,

        # Chart JSON
        'radar_labels':       json.dumps([p['name'] for p in pillars]),
        'radar_scores':       json.dumps([p['score'] for p in pillars]),
        'hist_labels':        json.dumps(history_labels),
        'hist_scores':        json.dumps(history_scores),
        'hist_pollution':     json.dumps(history_pollution),
        'hist_reduction':     json.dumps(history_reduction),
        'hist_invest':        json.dumps(history_invest),
        'hist_transparency':  json.dumps(history_transparency),
        'hist_community':     json.dumps(history_community),
        'inv_labels':         inv_labels,
        'inv_amounts':        inv_amounts,
        'inv_cumulative':     inv_cumulative,
        'inv_colors':         inv_colors,
        'emissions_chart':    emissions_chart,
        'methane_chart':      methane_chart,
        'gw_gauge_json':      gw_gauge_json,

        # CO₂
        'co2_completed':   co2_completed,
        'co2_active':      co2_active,
        'co2_planned':     co2_planned,
        'co2_total':       co2_total,
        'co2_cars_equiv':  co2_cars_equiv,
        'co2_trees_equiv': co2_trees_equiv,

        # AI Intelligence
        'ai_findings':        ai_findings,
        'ai_job_meta':        ai_job_meta,
        'ai_score_estimate':  ai_score_estimate,
        'greenwashing_data':  greenwashing_data,

        # Qualitative
        'sdg_grid':              sdg_grid,
        'sdg_active_count':      sdg_active_count,
        'recommendations':       recommendations,
        'evidence':              evidence,
        'ev_verified':           ev_verified,
        'ev_pending':            ev_pending,
        'ev_rejected':           ev_rejected,
        'transparency_history':  transparency_history,
        'disclosure_completeness': disclosure_completeness,
        'disclosure_missing':    disclosure_missing,
        'all_ev_types_list':     all_ev_types_list,

        'project_type_meta': PROJECT_TYPE_META,
    }
    # ── Explainability engine ──────────────────────────────────────────────────
    try:
        from league.explainability import explain_company as _explain_co
        ctx['explanations'] = _explain_co(company, ctx)
    except Exception:
        ctx['explanations'] = []

    return render(request, 'league/company.html', ctx)


# ── PDF Report ─────────────────────────────────────────────────────────────────

def report_pdf(request, slug):
    """
    Stream a premium A4 PDF report for the given company.
    Generated synchronously via WeasyPrint — suitable for Render free tier.
    """
    from .pdf_report import generate_pdf_report

    company = get_object_or_404(
        Company.objects.prefetch_related('projects', 'evidence', 'history'),
        slug=slug,
    )

    pdf_bytes = generate_pdf_report(company)
    filename  = f"ecoiq-report-{company.slug}-{company.ecoiq_score}.pdf"

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
