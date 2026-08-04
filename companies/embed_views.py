"""
companies/embed_views.py — PART 5 B2B2C embeddable / white-label components.

Public, read-only, unauthenticated surface for embedding EcoIQ badges and a
risk summary card on THIRD-PARTY sites (a company's own investor-relations
page, a fintech app, a partner directory, etc.). Deliberately separate from
/api/v1/ — that surface requires a secret API key, and secret keys must
never appear in client-side embed code. These views are keyed only by a
company's already-public slug and serve only already-public data (the same
`status in ('public', 'verified')` gate used across the platform).

Every response here:
  - reads ONLY CompanyProfile rows with status in ('public', 'verified') —
    never draft/unpublished intelligence, regardless of who's asking
  - carries a visible "Powered by EcoIQ" attribution + link back to the
    full profile (required attribution, not optional per embed terms)
  - sends X-Frame-Options: ALLOWALL / no clickjacking header on the
    risk-card view ONLY, since that view exists specifically to be framed
    by partner sites — every other EcoIQ page keeps default frame
    protection (see settings.py X_FRAME_OPTIONS)
  - is cacheable (no session/user-specific data, no auth) — short
    Cache-Control so partner embeds stay reasonably fresh without hammering
    the DB on every pageview
"""
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_GET

from companies.models import CompanyProfile
from companies.screening import compute_ethical_screening
from league.models import Company

EMBED_CACHE_SECONDS = 900  # 15 min — public data, no need to hit the DB every load

THEME_CHOICES = ('light', 'dark')

_ETHICAL_LABELS = {
    'passed': ('Passed', '#00c68a'),
    'review_required': ('Review Required', '#f4a261'),
    'failed': ('Failed', '#ef4444'),
    'insufficient_evidence': ('Insufficient Evidence', '#94a3b8'),
}

_ISLAMIC_LABELS = {
    'compliant': ('Indicative Pass', '#00c68a'),
    'non_compliant': ('Indicative Concern', '#ef4444'),
    'review_required': ('Review Required', '#f4a261'),
    'insufficient_evidence': ('Insufficient Evidence', '#94a3b8'),
}


def _public_profile_or_404(slug):
    company = get_object_or_404(Company, slug=slug)
    profile = get_object_or_404(CompanyProfile, company=company, status__in=('public', 'verified'))
    return company, profile


def _theme(request):
    theme = request.GET.get('theme', 'light')
    return theme if theme in THEME_CHOICES else 'light'


def _islamic_status(assessment):
    """Normalize a qdf DecisionAssessment (or None) to one of _ISLAMIC_LABELS' keys."""
    if assessment is None:
        return 'insufficient_evidence'
    if assessment.red_line_breached or assessment.verdict == 'do_not_proceed':
        return 'non_compliant'
    if assessment.verdict == 'proceed':
        return 'compliant'
    return 'review_required'


def _svg_response(svg: str) -> HttpResponse:
    resp = HttpResponse(svg, content_type='image/svg+xml')
    resp['Cache-Control'] = f'public, max-age={EMBED_CACHE_SECONDS}'
    return resp


def _badge_svg(label_left: str, label_right: str, color: str, theme: str) -> str:
    """
    Minimal hand-built badge SVG (shields.io-style two-tone pill). No
    external font/JS dependency, so the badge renders identically wherever
    it's dropped in via <img src="...">
    """
    bg_left = '#30363d' if theme == 'dark' else '#374151'
    text_color = '#f0f6fc' if theme == 'dark' else '#ffffff'
    left_w = max(60, 11 * len(label_left) + 20)
    right_w = max(60, 11 * len(label_right) + 20)
    total_w = left_w + right_w
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="20" role="img" aria-label="{label_left}: {label_right}">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#fff" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{total_w}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{left_w}" height="20" fill="{bg_left}"/>
    <rect x="{left_w}" width="{right_w}" height="20" fill="{color}"/>
    <rect width="{total_w}" height="20" fill="url(#s)"/>
  </g>
  <g fill="{text_color}" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{left_w / 2}" y="14">{label_left}</text>
    <text x="{left_w + right_w / 2}" y="14">{label_right}</text>
  </g>
</svg>'''


@require_GET
def ecoiq_score_badge(request, slug):
    """GET /embed/<slug>/badge.svg — overall EcoIQ Score badge."""
    company, _profile = _public_profile_or_404(slug)
    score = float(company.ecoiq_score)
    color = {
        'restorative': '#00c68a', 'transition': '#3fb950', 'improving': '#f4a261',
        'high-impact': '#f0883e', 'polluter': '#ef4444',
    }.get(company.status_css, '#94a3b8')
    svg = _badge_svg('EcoIQ Score', f'{score:.0f}/100', color, _theme(request))
    return _svg_response(svg)


@require_GET
def ethical_screening_badge(request, slug):
    """GET /embed/<slug>/ethical-badge.svg"""
    _company, profile = _public_profile_or_404(slug)
    result = compute_ethical_screening(profile)
    label, color = _ETHICAL_LABELS.get(result['status'], ('Unknown', '#94a3b8'))
    svg = _badge_svg('EcoIQ Ethical Screening', label, color, _theme(request))
    return _svg_response(svg)


@require_GET
def islamic_screening_badge(request, slug):
    """
    GET /embed/<slug>/islamic-badge.svg

    Indicative only — the badge label itself says "Indicative", and the
    linked risk-card / API response carries the full "not a fatwa"
    disclaimer. A badge has no room for a disclaimer, so it must never
    claim more than "indicative" in the label text.
    """
    _company, profile = _public_profile_or_404(slug)
    from qdf.scoring import get_or_compute
    assessment = get_or_compute(profile)
    label, color = _ISLAMIC_LABELS[_islamic_status(assessment)]
    svg = _badge_svg('EcoIQ Islamic Screening (Indicative)', label, color, _theme(request))
    return _svg_response(svg)


@require_GET
@xframe_options_exempt
def risk_card(request, slug):
    """
    GET /embed/<slug>/risk-card/ — richer HTML card meant to be embedded via
    <iframe>. Deliberately exempted from X-Frame-Options (this is the one
    view on the whole site meant to be framed by third-party pages).
    """
    company, profile = _public_profile_or_404(slug)
    ethical = compute_ethical_screening(profile)

    from qdf.scoring import get_or_compute
    assessment = get_or_compute(profile)

    report = profile.investment_reports.filter(status='published').order_by('-version').first()
    key_risks = (report.content or {}).get('key_risks', [])[:3] if report else []

    context = {
        'company': company,
        'profile': profile,
        'ethical': ethical,
        'islamic_available': assessment is not None,
        'islamic_status': _islamic_status(assessment),
        'islamic_label': _ISLAMIC_LABELS[_islamic_status(assessment)][0],
        'islamic_disclaimer_short': 'Indicative only — not a fatwa or Shariah ruling.',
        'key_risks': key_risks,
        'theme': _theme(request),
        'generated_at': timezone.now(),
        'profile_url': request.build_absolute_uri(
            reverse('companies:detail', kwargs={'slug': company.slug})
        ),
    }
    resp = TemplateResponse(request, 'companies/embed/risk_card.html', context)
    resp['Cache-Control'] = f'public, max-age={EMBED_CACHE_SECONDS}'
    resp['X-Robots-Tag'] = 'noindex'
    return resp


@require_GET
def embed_snippets(request, slug):
    """
    GET /embed/<slug>/ — human-facing page (not an embed itself) showing
    ready-to-copy <img>/<iframe> snippets for this company's badges. Public:
    the slug is already public knowledge and no private data is shown here.
    """
    company, _profile = _public_profile_or_404(slug)
    base = request.build_absolute_uri('/embed/' + slug)
    context = {
        'company': company,
        'badge_svg_url': base + '/badge.svg',
        'ethical_badge_url': base + '/ethical-badge.svg',
        'islamic_badge_url': base + '/islamic-badge.svg',
        'risk_card_url': base + '/risk-card/',
        'loader_js_url': request.build_absolute_uri('/static/js/ecoiq-embed.js'),
    }
    return render(request, 'companies/embed/snippets.html', context)
