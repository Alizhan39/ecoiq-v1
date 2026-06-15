"""Country presentation template tags (read-only)."""
from django import template

from countries.intelligence import country_intelligence

register = template.Library()


@register.inclusion_tag("countries/_country_intelligence.html")
def country_intelligence_panel(country):
    """Read-only harvester-backed intelligence panel for a CountryProfile."""
    if country is None:
        return {"no_registry": True, "companies_count": 0, "evidence_count": 0,
                "datapoint_count": 0, "companies": [], "overview": {},
                "energy": {}, "governance": {}}
    return country_intelligence(country)
