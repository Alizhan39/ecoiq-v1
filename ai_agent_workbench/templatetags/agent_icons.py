"""
ai_agent_workbench/templatetags/agent_icons.py — sophisticated, abstract
per-agent avatar glyphs (no emoji, no cartoon robots). Each is a small
stroke-based SVG in the same visual language as the EcoIQ header mark
(hexagon/circle outline + accent geometry) so the agent roster reads as
part of the existing identity, not a bolted-on icon set.
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# icon_key -> (stroke color token, inner glyph path markup)
_GLYPHS = {
    # Research Agent — network / evidence-search pulse
    'network': (
        '#58a6ff',
        '<circle cx="20" cy="11" r="2.6"/><circle cx="11" cy="27" r="2.6"/><circle cx="29" cy="27" r="2.6"/>'
        '<path d="M20 13.5 L13 24.5 M20 13.5 L27 24.5 M13.6 27 L26.4 27" stroke-width="1.4"/>',
    ),
    # Document Reader Agent — extracted lines from a page
    'document': (
        '#06b6d4',
        '<rect x="12" y="8" width="16" height="24" rx="2" stroke-width="1.6"/>'
        '<path d="M15.5 14.5H24.5M15.5 19.5H24.5M15.5 24.5H21" stroke-width="1.4"/>',
    ),
    # Photo / Visual Evidence Agent — lens / aperture
    'aperture': (
        '#a855f7',
        '<circle cx="20" cy="20" r="9" stroke-width="1.6"/>'
        '<path d="M20 13v4.5M27 20h-4.5M20 27v-4.5M13 20h4.5" stroke-width="1.4"/>',
    ),
    # Asset Passport Agent — structured record card
    'passport': (
        '#00e89a',
        '<rect x="10" y="11" width="20" height="18" rx="2.5" stroke-width="1.6"/>'
        '<circle cx="15.5" cy="17" r="2.1" stroke-width="1.3"/>'
        '<path d="M19.5 16h6M19.5 19h6M13 24.5h14" stroke-width="1.3"/>',
    ),
    # Industrial Playbook Matching Agent — branching pathway
    'pathway': (
        '#f4a261',
        '<circle cx="12" cy="20" r="2.2"/><circle cx="28" cy="11" r="2.2"/><circle cx="28" cy="29" r="2.2"/>'
        '<path d="M14 20 L26 11.5 M14 20 L26 28.5" stroke-width="1.4"/>',
    ),
    # Finance Modelling Agent — ascending model bars
    'bars': (
        '#58a6ff',
        '<path d="M13 27V21M20 27V15M27 27V10" stroke-width="2.4" stroke-linecap="round"/>',
    ),
    # MRV Agent — verification rings
    'verify_ring': (
        '#00e89a',
        '<circle cx="20" cy="20" r="9" stroke-width="1.6"/>'
        '<path d="M16 20.3 L18.7 23 L24.3 16.8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    ),
    # Governance Agent — shield
    'shield': (
        '#a855f7',
        '<path d="M20 9 L29 12.5 V20.5 C29 26 25 29.5 20 31.5 C15 29.5 11 26 11 20.5 V12.5 Z" stroke-width="1.6"/>',
    ),
    # Report Generator Agent — folded-corner report
    'report': (
        '#06b6d4',
        '<path d="M13 8 H23 L27 12 V32 H13 Z" stroke-width="1.6"/><path d="M23 8 V12 H27" stroke-width="1.4"/>'
        '<path d="M16.5 18h7M16.5 22.5h7M16.5 27h4.5" stroke-width="1.3"/>',
    ),
    # Amanah Autopilot Supervisor — overnight watch (crescent + orbit)
    'overnight': (
        '#f4a261',
        '<path d="M24.5 11.5a8.5 8.5 0 1 0 4 15.7A10.2 10.2 0 0 1 24.5 11.5Z" stroke-width="1.6"/>'
        '<circle cx="28" cy="13" r="1.4" fill="currentColor" stroke="none"/>',
    ),
    # Waste & Leakage Agent — value leaking into a monitored basin
    'leak': (
        '#e63946',
        '<path d="M20 9c3.2 4.4 6 8.4 6 11.7A6 6 0 0 1 14 20.7C14 17.4 16.8 13.4 20 9Z" stroke-width="1.6"/>'
        '<path d="M12 29.5h16" stroke-width="1.4"/>',
    ),
    # Capital Allocation Agent — governed allocation compass
    'allocate': (
        '#00e89a',
        '<circle cx="20" cy="20" r="9.5" stroke-width="1.6"/>'
        '<path d="M20 20 L24.5 13.5 M20 20 L15.5 22.5" stroke-width="1.6" stroke-linecap="round"/>'
        '<circle cx="20" cy="20" r="1.6" fill="currentColor" stroke="none"/>',
    ),
}

# Agent name -> icon_key, kept here (not in agent_data.py) so the visual
# layer's icon choices stay separate from the honest data layer.
AGENT_ICON_KEYS = {
    'Research Agent': 'network',
    'Document Reader Agent': 'document',
    'Photo / Visual Evidence Agent': 'aperture',
    'Asset Passport Agent': 'passport',
    'Industrial Playbook Matching Agent': 'pathway',
    'Finance Modelling Agent': 'bars',
    'MRV Agent': 'verify_ring',
    'Governance Agent': 'shield',
    'Report Generator Agent': 'report',
    'Amanah Autopilot Supervisor': 'overnight',
    'Waste & Leakage Agent': 'leak',
    'Capital Allocation Agent': 'allocate',
}


@register.simple_tag
def agent_icon(icon_key, size=40):
    color, glyph = _GLYPHS.get(icon_key, _GLYPHS['network'])
    svg = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 40 40" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true" style="color:{color};">'
        f'<circle cx="20" cy="20" r="19" fill="rgba(255,255,255,.03)" stroke="{color}" stroke-opacity=".35"/>'
        f'<g stroke="{color}" stroke-linecap="round" stroke-linejoin="round">{glyph}</g>'
        f'</svg>'
    )
    return mark_safe(svg)


@register.simple_tag
def agent_icon_for_name(agent_name, size=40):
    return agent_icon(AGENT_ICON_KEYS.get(agent_name, 'network'), size=size)
