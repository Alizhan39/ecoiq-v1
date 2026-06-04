"""
EcoIQ PDF Report Generator
----------------------------
Generates premium consulting-style A4 PDFs using WeasyPrint (synchronous,
no Celery, no Redis — just render HTML → bytes).

Usage:
    from league.pdf_report import generate_pdf_report
    pdf_bytes = generate_pdf_report(company_instance)
"""
import math
from datetime import date

from django.template.loader import render_to_string


# ─────────────────────────────────────────────────────────────────────────────
# SVG helpers  (all generate strings/lists suitable for Django templates)
# ─────────────────────────────────────────────────────────────────────────────

_CX = 140       # radar chart centre-x  (viewBox 0 0 280 280)
_CY = 140       # radar chart centre-y
_MAX_R = 88     # outer ring radius
_LABEL_R = _MAX_R + 20  # label offset


def _angle(i: int, n: int = 5) -> float:
    """Angle in radians for axis i, starting at 12-o'clock."""
    return math.radians(270 + i * 360 / n)


def _radar_polygon(scores: list[int]) -> str:
    """SVG polygon `points` attribute for the data shape."""
    pts = []
    for i, s in enumerate(scores):
        a = _angle(i)
        r = s / 100 * _MAX_R
        pts.append(f"{_CX + r * math.cos(a):.2f},{_CY + r * math.sin(a):.2f}")
    return " ".join(pts)


def _grid_ring(pct: float) -> str:
    """SVG polygon `points` for a grid ring at given fraction (0–1)."""
    pts = []
    for i in range(5):
        a = _angle(i)
        r = pct * _MAX_R
        pts.append(f"{_CX + r * math.cos(a):.2f},{_CY + r * math.sin(a):.2f}")
    return " ".join(pts)


def _axis_lines() -> list[dict]:
    return [
        {
            'x2': round(_CX + _MAX_R * math.cos(_angle(i)), 2),
            'y2': round(_CY + _MAX_R * math.sin(_angle(i)), 2),
        }
        for i in range(5)
    ]


def _axis_labels(names: list[str]) -> list[dict]:
    """Label positions for radar axes (5 short names)."""
    result = []
    for i, name in enumerate(names):
        a = _angle(i)
        x = _CX + _LABEL_R * math.cos(a)
        y = _CY + _LABEL_R * math.sin(a)
        # Horizontal alignment: left/middle/right depending on x position
        if x < _CX - 4:
            anchor = 'end'
        elif x > _CX + 4:
            anchor = 'start'
        else:
            anchor = 'middle'
        result.append({'label': name, 'x': round(x, 1), 'y': round(y, 1), 'anchor': anchor})
    return result


# Sparkline SVG (trend line, A4-friendly width)
_SPK_W   = 500
_SPK_H   = 110
_SPK_PAD = 12


def _sparkline_polyline(scores: list[float]) -> str:
    """SVG polyline `points` for a score trend line."""
    if not scores:
        return ""
    n = len(scores)
    pts = []
    for i, s in enumerate(scores):
        x = _SPK_PAD + i / max(n - 1, 1) * (_SPK_W - 2 * _SPK_PAD)
        y = _SPK_PAD + (1 - s / 100) * (_SPK_H - 2 * _SPK_PAD)
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def _sparkline_fill(scores: list[float]) -> str:
    """Closed SVG path for a filled area under the sparkline."""
    if not scores:
        return ""
    n = len(scores)
    bottom_y = _SPK_PAD + (_SPK_H - 2 * _SPK_PAD)  # y at score=0
    pts = []
    for i, s in enumerate(scores):
        x = _SPK_PAD + i / max(n - 1, 1) * (_SPK_W - 2 * _SPK_PAD)
        y = _SPK_PAD + (1 - s / 100) * (_SPK_H - 2 * _SPK_PAD)
        pts.append(f"{x:.1f},{y:.1f}")
    # Close the path along the bottom
    last_x = _SPK_PAD + (_SPK_W - 2 * _SPK_PAD)
    first_x = float(_SPK_PAD)
    return " ".join(pts) + f" {last_x:.1f},{bottom_y:.1f} {first_x:.1f},{bottom_y:.1f}"


def _tier_bands() -> list[dict]:
    """Horizontal bands for tier coloring on the sparkline chart."""
    # Each band: (score_lo, score_hi, fill_color, label)
    bands = [
        (85, 100, '#b7e4c7', 'Restorative'),
        (70,  85, '#d8f3dc', 'Transition'),
        (55,  70, '#edf7f0', 'Improving'),
        (40,  55, '#fce9d4', 'High Impact'),
        ( 0,  40, '#ffe0e3', 'Polluter'),
    ]
    result = []
    for lo, hi, color, label in bands:
        y_top = _SPK_PAD + (1 - hi / 100) * (_SPK_H - 2 * _SPK_PAD)
        h     = (hi - lo) / 100 * (_SPK_H - 2 * _SPK_PAD)
        # x position for label on the right
        lx = _SPK_W - _SPK_PAD - 2
        ly = y_top + h / 2
        result.append({
            'y':     round(y_top, 1),
            'h':     round(h, 1),
            'color': color,
            'label': label,
            'lx':    round(lx, 1),
            'ly':    round(ly, 1),
        })
    return result


def _score_to_tier(score: float) -> tuple[str, str]:
    """(tier label, tier hex colour)"""
    if score >= 85: return 'Restorative Leader',      '#2d6a4f'
    if score >= 70: return 'Transition Leader',        '#40916c'
    if score >= 55: return 'Improving but Polluting',  '#52b788'
    if score >= 40: return 'High Impact / Weak Repair','#f4a261'
    return 'Major Polluter', '#e63946'


# ─────────────────────────────────────────────────────────────────────────────
# Context builder
# ─────────────────────────────────────────────────────────────────────────────

def build_pdf_context(company) -> dict:
    """
    Assemble the full template context for `league/report_pdf.html`.
    Imports view-layer helpers to avoid duplicating SDG / project-type data.
    """
    from .views import _SDG_MAP, _SDG_ALL, PROJECT_TYPE_META, _stub_recommendations

    score = float(company.ecoiq_score)
    tier_label, tier_color = _score_to_tier(score)

    # Projects
    all_projects       = list(company.projects.order_by('start_date', 'name'))
    projects_completed = [p for p in all_projects if p.status == 'completed']
    projects_active    = [p for p in all_projects if p.status == 'active']
    projects_planned   = [p for p in all_projects if p.status == 'planned']

    for p in all_projects:
        p.type_meta = PROJECT_TYPE_META.get(p.project_type, PROJECT_TYPE_META['other'])

    # Pillars
    pillars = [
        {'key': 'pollution',    'name': 'Pollution',     'full': 'Pollution Footprint', 'weight': 35, 'score': company.score_pollution_footprint},
        {'key': 'reduction',    'name': 'Reduction',     'full': 'Reduction Progress',  'weight': 25, 'score': company.score_reduction_progress},
        {'key': 'investment',   'name': 'Investment',    'full': 'Investment',          'weight': 20, 'score': company.score_investment},
        {'key': 'transparency', 'name': 'Transparency',  'full': 'Transparency',        'weight': 10, 'score': company.score_transparency},
        {'key': 'community',    'name': 'Community',     'full': 'Community Impact',    'weight': 10, 'score': company.score_community_impact},
    ]
    pillar_scores = [p['score'] for p in pillars]
    pillar_names  = [p['name'] for p in pillars]

    # Score history
    history_qs     = list(company.history.order_by('date'))
    history_scores = [float(h.ecoiq_score) for h in history_qs]
    history_labels = [str(h.date)[:7] for h in history_qs]   # "YYYY-MM"

    # First / last / delta for trend summary
    if len(history_scores) >= 2:
        trend_start = history_scores[0]
        trend_end   = history_scores[-1]
        trend_delta = round(trend_end - trend_start, 1)
        trend_label = history_labels[0] + ' → ' + history_labels[-1]
    else:
        trend_start = trend_end = score
        trend_delta = 0.0
        trend_label = ''

    # CO₂
    co2_completed = sum(p.co2_reduction_tonnes or 0 for p in projects_completed)
    co2_active    = sum(p.co2_reduction_tonnes or 0 for p in projects_active)
    co2_planned   = sum(p.co2_reduction_tonnes or 0 for p in projects_planned)
    co2_total     = co2_completed + co2_active
    co2_cars      = round(co2_total / 4.6) if co2_total else 0
    co2_trees     = round(co2_total * 45)  if co2_total else 0

    # Investment
    total_inv_usd = company.total_investment_usd or 0
    total_inv_m   = round(total_inv_usd / 1_000_000, 1) if total_inv_usd else 0

    # Evidence
    evidence    = list(company.evidence.select_related('project').order_by('-date_issued'))
    ev_verified = sum(1 for e in evidence if e.verification_status == 'verified')
    ev_pending  = sum(1 for e in evidence if e.verification_status == 'pending')
    ev_rejected = sum(1 for e in evidence if e.verification_status == 'rejected')

    # SDG
    active_sdg_nums: set[int] = set()
    for p in all_projects:
        active_sdg_nums.update(_SDG_MAP.get(p.project_type, []))
    sdg_active = sorted(active_sdg_nums)
    sdg_grid = [
        {'num': num, 'label': label, 'color': color, 'active': num in active_sdg_nums}
        for num, label, color in _SDG_ALL
    ]

    # AI Recommendations
    recommendations = _stub_recommendations(company, all_projects)

    # Roadmap
    roadmap_projects = sorted(
        [p for p in all_projects if p.start_date],
        key=lambda p: p.start_date,
    )

    # Group evidence by year
    ev_by_year: dict = {}
    for ev in evidence:
        yr = ev.date_issued.year if ev.date_issued else 0
        ev_by_year.setdefault(yr, []).append(ev)
    transparency_history = sorted(ev_by_year.items(), reverse=True)

    # Investment per-project bars for PDF table
    inv_projects = sorted(
        [p for p in all_projects if (p.investment_usd or 0) > 0],
        key=lambda p: -(p.investment_usd or 0),
    )[:8]  # top-8 for table

    # ── SVG data ─────────────────────────────────────────────────────────────
    radar_data    = _radar_polygon(pillar_scores)
    radar_rings   = [_grid_ring(f) for f in (0.2, 0.4, 0.6, 0.8, 1.0)]
    radar_axes    = _axis_lines()
    radar_labels  = _axis_labels(pillar_names)
    sparkline_pts = _sparkline_polyline(history_scores)
    sparkline_fill= _sparkline_fill(history_scores)
    tier_bands    = _tier_bands()

    # SVG score ring (r=52, circumference ≈ 327)
    score_arc = round(score / 100 * 327, 1)

    return {
        'company':        company,
        'score':          score,
        'tier_label':     tier_label,
        'tier_color':     tier_color,
        'pillars':        pillars,
        'score_arc':      score_arc,

        'all_projects':       all_projects,
        'projects_completed': projects_completed,
        'projects_active':    projects_active,
        'projects_planned':   projects_planned,
        'roadmap_projects':   roadmap_projects,
        'inv_projects':       inv_projects,

        # CO₂
        'co2_total':      co2_total,
        'co2_completed':  co2_completed,
        'co2_active':     co2_active,
        'co2_planned':    co2_planned,
        'co2_cars':       co2_cars,
        'co2_trees':      co2_trees,

        # Investment
        'total_inv_m':    total_inv_m,
        'total_inv_usd':  total_inv_usd,

        # Trend
        'trend_start':    trend_start,
        'trend_end':      trend_end,
        'trend_delta':    trend_delta,
        'trend_label':    trend_label,

        # Evidence
        'evidence':            evidence,
        'ev_verified':         ev_verified,
        'ev_pending':          ev_pending,
        'ev_rejected':         ev_rejected,
        'transparency_history': transparency_history,

        # Qualitative
        'sdg_grid':        sdg_grid,
        'sdg_active':      sdg_active,
        'recommendations': recommendations,

        # SVG chart data
        'radar_data':     radar_data,
        'radar_rings':    radar_rings,
        'radar_axes':     radar_axes,
        'radar_labels':   radar_labels,
        'sparkline_pts':  sparkline_pts,
        'sparkline_fill': sparkline_fill,
        'tier_bands':     tier_bands,
        'spk_w':          _SPK_W,
        'spk_h':          _SPK_H,
        'spk_pad':        _SPK_PAD,

        'report_date': date.today(),
        'radar_cx': _CX,
        'radar_cy': _CY,
        'history_labels': history_labels,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_pdf_report(company) -> bytes:
    """
    Render the PDF report for a Company instance.
    Returns raw PDF bytes ready for HttpResponse.

    del + gc.collect() after write_pdf() frees WeasyPrint's internal layout tree
    and cairocffi objects promptly — prevents memory accumulation on 2 GB Render.
    base_url uses SITE_URL so static asset references resolve correctly on Render.
    """
    import gc
    import weasyprint
    from django.conf import settings as _s

    context   = build_pdf_context(company)
    html_str  = render_to_string('league/report_pdf.html', context)
    base_url  = getattr(_s, 'SITE_URL', 'https://ecoiq.uk') + '/'
    _html_doc = weasyprint.HTML(string=html_str, base_url=base_url)
    try:
        pdf_bytes = _html_doc.write_pdf()
    finally:
        del _html_doc
        gc.collect()
    return pdf_bytes
