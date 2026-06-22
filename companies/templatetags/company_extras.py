"""
Template helpers for the company directory cards.

Pure presentation helpers — no DB access, no model changes. Used by
templates/companies/_company_card.html.
"""
from urllib.parse import urlparse

from django import template

register = template.Library()


# ── Logo domain ──────────────────────────────────────────────────────────────
@register.filter
def domain_of(url):
    """Return the bare domain (no scheme, no www, no path) from a URL, or ''."""
    if not url:
        return ''
    try:
        netloc = urlparse(url if '//' in url else 'https://' + url).netloc
        netloc = netloc.split('@')[-1].split(':')[0]  # strip auth / port
        return netloc[4:] if netloc.startswith('www.') else netloc
    except Exception:
        return ''


# ── Sector visuals (fixed set; not per-company photos) ───────────────────────
_SECTOR_EMOJI = {
    'oil_gas': '🛢️', 'mining': '⛏️', 'energy': '⚡', 'chemical': '⚗️',
    'metallurgy': '🏭', 'transport': '🚚', 'agriculture': '🌾', 'other': '🏢',
}

# Dark, low-luminance accents so white header text always stays readable.
_SECTOR_ACCENT = {
    'oil_gas':     '38,28,18',
    'mining':      '46,38,28',
    'energy':      '14,52,40',
    'chemical':    '28,38,54',
    'metallurgy':  '44,40,50',
    'transport':   '18,40,52',
    'agriculture': '22,46,28',
    'other':       '16,34,28',
}


@register.filter
def sector_emoji(code):
    return _SECTOR_EMOJI.get(code, '🏢')


@register.filter
def sector_gradient(code):
    """A dark emerald→sector-tinted gradient for the identity banner."""
    rgb = _SECTOR_ACCENT.get(code, '16,34,28')
    return f"linear-gradient(135deg, rgba(6,18,14,.96) 0%, rgba({rgb},.6) 100%)"


# ── Controversy / risk band (controversy_risk_score: higher = more risk) ─────
def _risk(score):
    try:
        return float(score)
    except (TypeError, ValueError):
        return None


@register.filter
def risk_label(score):
    s = _risk(score)
    if s is None:
        return 'Unrated'
    if s < 25:
        return 'Low Risk'
    if s < 50:
        return 'Moderate Risk'
    if s < 75:
        return 'High Risk'
    return 'Critical Risk'


@register.filter
def risk_color(score):
    s = _risk(score)
    if s is None:
        return '#94a3b8'
    if s < 25:
        return '#00e89a'
    if s < 50:
        return '#f4a261'
    if s < 75:
        return '#e63946'
    return '#b91c1c'
