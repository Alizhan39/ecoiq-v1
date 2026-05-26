"""
EcoIQ Environmental Intelligence OS — Views.

/intelligence/              → Bloomberg-style intelligence hub
/intelligence/country/<code>/ → National intelligence dashboard
/intelligence/compare/      → Multi-company comparison engine
/intelligence/alerts/       → Real-time alert feed
/intelligence/tracker/<mod>/→ Strategic intelligence module
/intelligence/api/alerts/   → Alert JSON feed (poll)
/intelligence/briefing/<slug>/ → AI executive briefing
"""
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from league.models import Company, SECTOR_CHOICES
from league.scoring import get_tier
from intelligence.models import (
    CountryIntelligence, IntelligenceAlert,
    MonitorWatch, StrategicSignal, ExecutiveBriefing,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

SECTOR_LABEL = dict(SECTOR_CHOICES)

def _sector_name(code):
    return SECTOR_LABEL.get(code, code.replace('_', ' ').title())

def _tier_color(score):
    return get_tier(float(score)).colour


# ── Hub ───────────────────────────────────────────────────────────────────────

@staff_member_required(login_url='/login/')
def hub(request):
    """
    Main intelligence terminal — aggregate view of the entire platform.
    """
    from intelligence.compute import get_rank_movers

    # ── Global KPIs ───────────────────────────────────────────────────────────
    all_companies = list(
        Company.objects.prefetch_related('projects', 'alerts').order_by('rank', '-ecoiq_score')
    )
    company_count  = len(all_companies)
    verified_count = sum(1 for c in all_companies if c.verified)
    total_co2      = sum(c.total_co2_reduced for c in all_companies)
    total_inv      = sum(c.total_investment_usd for c in all_companies)
    total_hh       = sum(c.total_households_helped for c in all_companies)

    # Alert counts
    alert_qs       = IntelligenceAlert.objects.all()
    unread_alerts  = alert_qs.filter(is_read=False).count()
    critical_alerts= alert_qs.filter(is_read=False, severity='critical').count()
    recent_alerts  = list(alert_qs.order_by('-created_at')[:20])

    # ── Rank movers ───────────────────────────────────────────────────────────
    movers = get_rank_movers(days=30, limit=6)

    # ── Sector heatmap ────────────────────────────────────────────────────────
    sector_data = defaultdict(lambda: {'count': 0, 'scores': [], 'co2': 0, 'inv': 0})
    for co in all_companies:
        sd = sector_data[co.sector]
        sd['count']  += 1
        sd['scores'].append(float(co.ecoiq_score))
        sd['co2']    += co.total_co2_reduced
        sd['inv']    += co.total_investment_usd

    sector_grid = []
    for code, sd in sorted(sector_data.items(), key=lambda x: -sum(x[1]['scores'])/max(len(x[1]['scores']),1)):
        avg_score = round(sum(sd['scores']) / len(sd['scores']), 1)
        sector_grid.append({
            'code':      code,
            'label':     _sector_name(code),
            'count':     sd['count'],
            'avg_score': avg_score,
            'co2':       sd['co2'],
            'inv_m':     round(sd['inv'] / 1_000_000, 1) if sd['inv'] else 0,
            'color':     _tier_color(avg_score),
        })

    # ── Country table ─────────────────────────────────────────────────────────
    countries = list(CountryIntelligence.objects.order_by('-national_ecoiq_score')[:20])

    # Bootstrap countries from Company data if none computed yet
    if not countries:
        from intelligence.compute import compute_country_intelligence
        try:
            compute_country_intelligence()
            countries = list(CountryIntelligence.objects.order_by('-national_ecoiq_score')[:20])
        except Exception:
            pass

    # ── Strategic signals summary ─────────────────────────────────────────────
    signals = list(
        StrategicSignal.objects.select_related('company')
        .order_by('-detected_at')[:15]
    )

    # ── Top performers vs worst ───────────────────────────────────────────────
    top5     = [c for c in all_companies if c.rank][:5]
    bottom5  = sorted([c for c in all_companies if c.rank], key=lambda c: c.rank, reverse=True)[:5]

    # ── Score distribution (histogram buckets) ────────────────────────────────
    buckets = [0] * 10
    for co in all_companies:
        idx = min(9, int(float(co.ecoiq_score) / 10))
        buckets[idx] += 1
    hist_json = json.dumps({
        'labels': [f'{i*10}-{i*10+9}' for i in range(10)],
        'counts': buckets,
    })

    # ── Recent ingestion activity ─────────────────────────────────────────────
    from ingestion.models import IngestionJob
    recent_jobs = list(IngestionJob.objects.select_related('result_company').order_by('-created_at')[:6])

    # ── Score scatter (for bubble chart) ─────────────────────────────────────
    scatter_data = json.dumps([
        {
            'x':       co.score_transparency,
            'y':       float(co.ecoiq_score),
            'r':       max(4, min(20, (co.total_co2_reduced or 0) / 50000)),
            'name':    co.name[:25],
            'sector':  co.sector,
            'color':   _tier_color(co.ecoiq_score),
        }
        for co in all_companies
    ])

    return render(request, 'intelligence/hub.html', {
        # KPIs
        'company_count':   company_count,
        'verified_count':  verified_count,
        'total_co2':       total_co2,
        'total_inv_m':     round(total_inv / 1_000_000) if total_inv else 0,
        'total_hh':        total_hh,
        'unread_alerts':   unread_alerts,
        'critical_alerts': critical_alerts,

        # Tables & cards
        'all_companies':   all_companies[:30],
        'top5':            top5,
        'bottom5':         bottom5,
        'movers_gainers':  movers['gainers'],
        'movers_losers':   movers['losers'],
        'sector_grid':     sector_grid,
        'countries':       countries,
        'recent_alerts':   recent_alerts,
        'signals':         signals,
        'recent_jobs':     recent_jobs,

        # Charts
        'hist_json':       hist_json,
        'scatter_data':    scatter_data,

        # Sector choices for filter
        'sector_choices':  SECTOR_CHOICES,
    })


# ── Country Intelligence ──────────────────────────────────────────────────────

@staff_member_required(login_url='/login/')
def country_detail(request, code: str):
    """National intelligence dashboard."""
    ci = get_object_or_404(CountryIntelligence, country_code=code)

    companies = list(
        Company.objects.filter(country=ci.country_name)
        .prefetch_related('projects')
        .order_by('rank', '-ecoiq_score')
    )

    # Sector breakdown for this country
    sector_dist = defaultdict(lambda: {'count': 0, 'scores': []})
    for co in companies:
        sector_dist[co.sector]['count'] += 1
        sector_dist[co.sector]['scores'].append(float(co.ecoiq_score))

    sectors = [
        {
            'label':     _sector_name(code_),
            'count':     data['count'],
            'avg_score': round(sum(data['scores']) / len(data['scores']), 1),
        }
        for code_, data in sorted(sector_dist.items(),
                                   key=lambda x: -x[1]['count'])
    ]

    # Score history (aggregate from ScoreHistory)
    from league.models import ScoreHistory
    from django.db.models import Avg

    history_qs = (
        ScoreHistory.objects
        .filter(company__country=ci.country_name)
        .values('date')
        .annotate(avg_score=Avg('ecoiq_score'))
        .order_by('date')
    )
    hist_labels = [str(h['date'])[:7] for h in history_qs]
    hist_scores = [round(float(h['avg_score']), 1) for h in history_qs]

    # Transparency ranking within country
    for i, co in enumerate(sorted(companies, key=lambda c: c.score_transparency, reverse=True), 1):
        co.trans_rank = i

    # Alerts for country companies
    country_alerts = list(
        IntelligenceAlert.objects
        .filter(company__country=ci.country_name)
        .order_by('-created_at')[:10]
    )

    # Strategic signals
    country_signals = list(
        StrategicSignal.objects
        .filter(company__country=ci.country_name)
        .select_related('company')
        .order_by('-detected_at')[:10]
    )

    # Latest executive briefings for this country's top companies
    briefings = list(
        ExecutiveBriefing.objects
        .filter(company__country=ci.country_name)
        .select_related('company')
        .order_by('-created_at')[:3]
    )

    # Pillar radar JSON
    radar_json = json.dumps({
        'labels': ['Pollution', 'Reduction', 'Investment', 'Transparency', 'Community'],
        'scores': [
            float(ci.avg_pollution), float(ci.avg_reduction),
            float(ci.avg_investment), float(ci.avg_transparency),
            float(ci.avg_community),
        ],
    })

    # Company chart (top 12 by score)
    company_chart = json.dumps([
        {
            'name':  co.name[:22] + ('…' if len(co.name) > 22 else ''),
            'score': float(co.ecoiq_score),
            'color': _tier_color(co.ecoiq_score),
        }
        for co in companies[:12]
    ])

    return render(request, 'intelligence/country.html', {
        'ci':              ci,
        'companies':       companies,
        'sectors':         sectors,
        'hist_labels':     json.dumps(hist_labels),
        'hist_scores':     json.dumps(hist_scores),
        'country_alerts':  country_alerts,
        'country_signals': country_signals,
        'briefings':       briefings,
        'radar_json':      radar_json,
        'company_chart':   company_chart,
    })


# ── Comparison Engine ─────────────────────────────────────────────────────────

@staff_member_required(login_url='/login/')
def compare(request):
    """Multi-company comparison engine — up to 4 companies side by side."""
    slugs = request.GET.getlist('co')[:4]
    companies = []
    if slugs:
        for s in slugs:
            try:
                co = Company.objects.prefetch_related('projects', 'history').get(slug=s)
                co.tier = get_tier(float(co.ecoiq_score))
                companies.append(co)
            except Company.DoesNotExist:
                pass

    # Comparison data structures
    pillar_keys = [
        ('pollution',    'Pollution Footprint',  'score_pollution_footprint'),
        ('reduction',    'Reduction Progress',   'score_reduction_progress'),
        ('investment',   'Investment',           'score_investment'),
        ('transparency', 'Transparency',         'score_transparency'),
        ('community',    'Community Impact',     'score_community_impact'),
    ]
    pillar_comparison = [
        {
            'key': key,
            'label': label,
            'scores': [getattr(co, attr) for co in companies],
            'max': max((getattr(co, attr) for co in companies), default=0),
        }
        for key, label, attr in pillar_keys
    ]

    # Radar overlay
    radar_datasets = json.dumps([
        {
            'label': co.name[:25],
            'data': [
                co.score_pollution_footprint, co.score_reduction_progress,
                co.score_investment, co.score_transparency, co.score_community_impact,
            ],
            'color': _tier_color(co.ecoiq_score),
        }
        for co in companies
    ])

    # Score history overlay
    history_json = {}
    for co in companies:
        h = list(co.history.order_by('date'))
        history_json[co.slug] = {
            'name':   co.name,
            'color':  _tier_color(co.ecoiq_score),
            'labels': [str(s.date)[:7] for s in h],
            'scores': [float(s.ecoiq_score) for s in h],
        }

    # All companies for the select picker
    all_companies = list(Company.objects.order_by('rank', 'name'))

    return render(request, 'intelligence/compare.html', {
        'companies':         companies,
        'selected_slugs':    slugs,
        'all_companies':     all_companies,
        'pillar_comparison': pillar_comparison,
        'radar_datasets':    radar_datasets,
        'history_json':      json.dumps(history_json),
    })


# ── Alert Feed ────────────────────────────────────────────────────────────────

@staff_member_required(login_url='/login/')
def alerts(request):
    """Intelligence alert command centre."""
    severity  = request.GET.get('severity', '')
    atype     = request.GET.get('type', '')
    unread    = request.GET.get('unread', '')

    qs = IntelligenceAlert.objects.select_related('company').order_by('-created_at')
    if severity:
        qs = qs.filter(severity=severity)
    if atype:
        qs = qs.filter(alert_type=atype)
    if unread == '1':
        qs = qs.filter(is_read=False)

    alert_list = list(qs[:100])

    # Mark all as read if requested
    if request.GET.get('mark_read') == '1':
        IntelligenceAlert.objects.filter(is_read=False).update(is_read=True)

    counts = {
        'total':    IntelligenceAlert.objects.count(),
        'unread':   IntelligenceAlert.objects.filter(is_read=False).count(),
        'critical': IntelligenceAlert.objects.filter(severity='critical').count(),
        'high':     IntelligenceAlert.objects.filter(severity='high').count(),
    }

    return render(request, 'intelligence/alerts.html', {
        'alert_list':  alert_list,
        'counts':      counts,
        'severity':    severity,
        'atype':       atype,
        'unread':      unread,
        'alert_types': IntelligenceAlert.ALERT_TYPE_CHOICES,
        'severities':  IntelligenceAlert.SEVERITY_CHOICES,
    })


# ── Strategic Tracker ─────────────────────────────────────────────────────────

MODULE_META = {
    'methane': {
        'label':    'Methane Leakage Intelligence',
        'icon':     '☁️',
        'accent':   '#f4a261',
        'desc':     'Real-time methane leakage signals from oil & gas, mining, and agriculture sectors.',
        'sectors':  ['oil_gas', 'mining', 'agriculture'],
    },
    'coal_transition': {
        'label':    'Coal-to-Gas Transition Tracker',
        'icon':     '⚡',
        'accent':   '#58a6ff',
        'desc':     'Monitoring industrial coal replacement programmes and transition timelines.',
        'sectors':  ['energy', 'metallurgy', 'chemical'],
    },
    'water_restoration': {
        'label':    'Water Restoration Tracker',
        'icon':     '💧',
        'accent':   '#26bde2',
        'desc':     'Tracking industrial water pollution reduction and ecosystem restoration.',
        'sectors':  ['mining', 'chemical', 'agriculture'],
    },
    'flare_reduction': {
        'label':    'Flare Reduction Monitor',
        'icon':     '🔥',
        'accent':   '#e63946',
        'desc':     'Monitoring gas flaring reduction commitments and verified reductions.',
        'sectors':  ['oil_gas', 'energy'],
    },
    'modernisation': {
        'label':    'Industrial Modernisation Tracker',
        'icon':     '🏭',
        'accent':   '#00e89a',
        'desc':     'Tracking clean technology adoption and industrial facility upgrades.',
        'sectors':  ['metallurgy', 'chemical', 'energy', 'mining'],
    },
    'ethical_investment': {
        'label':    'Ethical Investment Scoring',
        'icon':     '📊',
        'accent':   '#8b5cf6',
        'desc':     'ESG investment credibility analysis and greenwashing detection.',
        'sectors':  ['oil_gas', 'mining', 'energy', 'chemical', 'metallurgy'],
    },
}


@staff_member_required(login_url='/login/')
def tracker(request, module: str):
    """Strategic intelligence module view."""
    if module not in MODULE_META:
        from django.http import Http404
        raise Http404(f'Unknown module: {module}')

    meta = MODULE_META[module]

    # Companies in relevant sectors
    sector_companies = list(
        Company.objects
        .filter(sector__in=meta['sectors'])
        .order_by('rank', '-ecoiq_score')
    )
    for co in sector_companies:
        co.tier = get_tier(float(co.ecoiq_score))

    # Signals for this module
    module_signals = list(
        StrategicSignal.objects
        .filter(module=module)
        .select_related('company')
        .order_by('-detected_at')
    )

    # Alerts for these companies
    module_alerts = list(
        IntelligenceAlert.objects
        .filter(company__sector__in=meta['sectors'])
        .order_by('-created_at')[:20]
    )

    # Score distribution for relevant sector companies
    scores = [float(co.ecoiq_score) for co in sector_companies]
    sector_avg = round(sum(scores) / len(scores), 1) if scores else 0

    # Key stats
    positive_signals = sum(1 for s in module_signals if s.polarity == 'positive')
    risk_signals     = sum(1 for s in module_signals if s.polarity == 'risk')

    return render(request, 'intelligence/tracker.html', {
        'module':           module,
        'meta':             meta,
        'sector_companies': sector_companies,
        'module_signals':   module_signals,
        'module_alerts':    module_alerts,
        'sector_avg':       sector_avg,
        'positive_signals': positive_signals,
        'risk_signals':     risk_signals,
        'all_modules':      MODULE_META,
    })


# ── Briefing ──────────────────────────────────────────────────────────────────

@staff_member_required(login_url='/login/')
def briefing(request, slug: str):
    """View or generate AI executive briefing for a company."""
    company = get_object_or_404(Company, slug=slug)

    # Get latest briefing or generate on demand
    existing = ExecutiveBriefing.objects.filter(
        company=company
    ).order_by('-created_at').first()

    generated_now = False
    if request.method == 'POST' or not existing:
        from intelligence.compute import generate_executive_briefing
        from django.conf import settings
        if settings.ANTHROPIC_API_KEY:
            new_b = generate_executive_briefing(company)
            if new_b:
                existing = new_b
                generated_now = True

    tier = get_tier(float(company.ecoiq_score))

    return render(request, 'intelligence/briefing.html', {
        'company':        company,
        'tier':           tier,
        'briefing':       existing,
        'generated_now':  generated_now,
        'all_briefings':  list(
            ExecutiveBriefing.objects.filter(company=company).order_by('-created_at')[:5]
        ),
    })


# ── API: Alert poll ───────────────────────────────────────────────────────────

@staff_member_required(login_url='/login/')
def api_alerts(request):
    """JSON endpoint for real-time alert polling."""
    alerts_qs = IntelligenceAlert.objects.filter(
        is_read=False
    ).select_related('company').order_by('-created_at')[:10]

    return JsonResponse({
        'count': alerts_qs.count(),
        'alerts': [
            {
                'id':         a.pk,
                'type':       a.alert_type,
                'severity':   a.severity,
                'title':      a.title,
                'company':    a.company.name if a.company else None,
                'icon':       a.alert_icon,
                'color':      a.severity_color,
                'created_at': a.created_at.isoformat(),
            }
            for a in alerts_qs
        ],
    })


# ── API: Mark alert read ──────────────────────────────────────────────────────

@staff_member_required(login_url='/login/')
@require_POST
def api_mark_read(request, alert_id: int):
    IntelligenceAlert.objects.filter(pk=alert_id).update(is_read=True)
    return JsonResponse({'ok': True})
