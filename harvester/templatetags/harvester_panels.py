"""
Harvester presentation template tags.

`company_evidence_panel` renders the read-only Evidence Layer panel on the
canonical company page via an inclusion tag — so the company page only needs a
`{% load %}` + one tag line, with no changes to companies/views.py.
"""
from django import template

from harvester.rollups import company_rollup, platform_stats

register = template.Library()


@register.inclusion_tag("harvester/_intelligence_block.html")
def intelligence_block():
    """Compact read-only platform intelligence block for the homepage."""
    return platform_stats()


@register.inclusion_tag("harvester/_company_evidence_panel.html")
def company_evidence_panel(slug, limit=5):
    """Read-only evidence rollup for a company slug. Safe on unknown slugs
    (returns empty counts)."""
    if not slug:
        return {"slug": "", "has_data": False, "evidence_count": 0,
                "datapoint_count": 0, "last_updated": None,
                "latest_evidence": [], "latest_datapoints": [],
                "dashboard_url": ""}
    return company_rollup(slug, n=limit)
