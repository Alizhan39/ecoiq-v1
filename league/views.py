"""
EcoIQ Good Deeds League — public views.

/league/                  → leaderboard (public)
/league/<slug>/           → company ESG intelligence profile (public)
"""
from companies.eligibility import publishable_company_ids
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

#: The pillar scores the recommendation engine reads, with the label a reader
#: sees when one of them has not been assessed.
_RECOMMENDATION_PILLARS = (
    ('score_pollution_footprint', 'Pollution footprint'),
    ('score_reduction_progress', 'Reduction progress'),
    ('score_investment', 'Investment'),
    ('score_transparency', 'Transparency'),
    ('score_community_impact', 'Community impact'),
)


def _below(value, threshold) -> bool:
    """
    Is this score measurably below the threshold?

    UNKNOWN IS NOT A GAP
    --------------------
    `company.score_pollution_footprint < 60` raised

        TypeError: '<' not supported between instances of 'NoneType' and 'int'

    for any organisation whose pillar scores have not been computed — which is
    most of them — so /league/<slug>/report.pdf returned a 500 to anonymous
    callers rather than a report.

    Coercing the unknown to 0 would have been worse than the crash: every
    recommendation would fire, and the PDF would tell a reader that an
    organisation nobody has assessed has a critical pollution-monitoring gap.
    A recommendation is a claim about a measured deficiency. No measurement,
    no claim.
    """
    return value is not None and value < threshold


def unassessed_pillars(company):
    """
    The pillars carrying no score, so the report can say which.

    Without this the empty recommendation list rendered "No critical
    recommendations — company scores above threshold on all pillars", which for
    an unassessed organisation reports silence as a pass. That is the exact
    substitution — UNKNOWN read as a clean bill of health — that the rest of
    this codebase is written to prevent.
    """
    return [label for field, label in _RECOMMENDATION_PILLARS
            if getattr(company, field, None) is None]


# Stub AI recommendations — generated from pillar score gaps
def _stub_recommendations(company, projects):
    sdg_lkp = _SDG_LOOKUP
    recs = []

    if _below(company.score_pollution_footprint, 60):
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

    if _below(company.score_reduction_progress, 60):
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

    if _below(company.score_investment, 60):
        recs.append({
            'priority': 'high', 'priority_label': 'High',
            'icon': '💚',
            'title': 'Increase Environmental Capex to ≥1% of Annual Revenue',
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

    if _below(company.score_transparency, 65):
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

    if _below(company.score_community_impact, 60):
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

    # A company with no score has no tier. get_tier() bands a number; handing
    # it None crashes, and handing it 0 would band an unscored company as the
    # worst one.
    for co in companies:
        co.tier = None if co.ecoiq_score is None else get_tier(float(co.ecoiq_score))
        co.ecoiq_profile = _profile_map.get(co.pk)

    # ── Public evidence gate (D1.5) ───────────────────────────────────────────
    # No evidence, no rank.
    #
    # A league table makes a comparative claim about every organisation in it,
    # including the ones near the bottom. Substituting 0, 50 or "unranked" for a
    # missing score would not make that claim safer — it would just make it
    # quieter. So an organisation whose score has no evidence provenance is
    # removed from the ordering rather than placed within it.
    #
    # Removed from the *ranking*, not from the database and not from its own
    # page: companies/views.py serves those separately. Staff still see the full
    # table, so the seeded data stays inspectable.
    ineligible_count = 0
    if not request.user.is_staff:
        # Bulk, not per-company. The loop this replaces ran the eligibility
        # decision once per row -- roughly two queries each -- which is the
        # reason the CHARTS below were left ungated: the correct check looked
        # too expensive to run twice on one page. Making it cheap removes the
        # incentive to skip it.
        eligible_ids = publishable_company_ids(companies)
        eligible = [co for co in companies if co.pk in eligible_ids]
        ineligible_count = len(companies) - len(eligible)
        companies = eligible

    all_cos   = Company.objects.prefetch_related('projects')
    total_co2 = sum(c.total_co2_reduced for c in all_cos)
    total_inv = sum(c.total_investment_usd for c in all_cos)
    total_hh  = sum(c.total_households_helped for c in all_cos)

    # ── Analytics chart data ──────────────────────────────────────────────────
    SECTOR_LABEL = dict(SECTOR_CHOICES)
    from collections import defaultdict
    _sector_scores = defaultdict(list)

    # CHART DATA IS PUBLISHED DATA.
    #
    # These figures are serialised into inline JavaScript on a public page, so
    # they are as published as the table above them -- and for a while they
    # were not gated like it. The table filtered on evidence; the charts
    # filtered only on `is not None`, which let a company with a real but
    # UNEVIDENCED score into the chart JSON with its score and all five pillar
    # values, while the visible row said "evidence assessment pending".
    #
    # Hiding a number in the table and shipping it in a <script> tag is not
    # containment. Both now use the same gate.
    _publishable = publishable_company_ids(all_cos)

    for co in all_cos:
        if co.pk in _publishable and co.ecoiq_score is not None:
            _sector_scores[co.sector].append(float(co.ecoiq_score))

    chart_sectors = json.dumps(sorted([
        {
            'label': SECTOR_LABEL.get(s, s.replace('_', ' ').title()),
            'avg':   round(sum(v) / len(v), 1),
            'count': len(v),
        }
        for s, v in _sector_scores.items()
    ], key=lambda x: x['avg'], reverse=True))

    # Bug fix: this used to read from `all_cos` (unfiltered), so the "Top
    # Companies" chart always showed platform-wide top companies even when
    # `?sector=` was applied — leaking other sectors' company names onto an
    # otherwise correctly-filtered leaderboard page. It must reuse the same
    # sector-filtered `qs` the main table uses. `chart_sectors`/`total_*`
    # below are intentionally left platform-wide — they're cross-sector
    # comparison/overview figures, not part of the "current sector" table.
    # Companies without a score are excluded from the chart rather than
    # plotted at zero: a zero-length bar is a visual claim that the company
    # scored worst, and an absent bar claims nothing.
    _ranked_candidates = list(qs.order_by('rank', '-ecoiq_score')[:40])
    _ranked_publishable = publishable_company_ids(_ranked_candidates)
    _all_ranked = [co for co in _ranked_candidates
                   if co.pk in _ranked_publishable
                   and co.ecoiq_score is not None][:15]
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
        # How many organisations were withheld from the ranking for lack of
        # evidence. Shown so the table's emptiness is explained rather than
        # looking like a failure.
        'ineligible_count':  ineligible_count,
    })


# ── Company ESG profile ────────────────────────────────────────────────────────

# company_profile is gone with templates/league/company.html.
#
# /league/<slug>/ redirects to /companies/<slug>/ (see company_redirect below).
# Both routes rendered league.Company by the same slug, so a second profile was
# two surfaces for one organisation and two chances for them to disagree about
# what is publishable.


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

def company_redirect(request, slug):
    """
    /league/<slug>/ → /companies/<slug>/

    Both routes rendered league.Company by the same slug. Keeping two surfaces
    for one organisation would be two chances for them to disagree about what
    is publishable, so the league defers to the company page.

    404s on an unknown slug rather than redirecting to one: a 302 followed by a
    404 tells a crawler the URL moved before telling it the destination does
    not exist, and existing inbound links to real companies still resolve in
    one hop.
    """
    from django.shortcuts import redirect

    get_object_or_404(Company, slug=slug)
    return redirect(f'/companies/{slug}/', permanent=False)
