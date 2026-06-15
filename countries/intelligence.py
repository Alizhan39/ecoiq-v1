"""
Country Intelligence bridge (read-only, Track A / Phase 1).

Aggregates harvester data (RegistryCompany / Evidence / Datapoint) for a country
and surfaces it alongside the existing CountryProfile fields. Pure reads — no
writes, no scoring, no fabrication. Companies are matched by ISO country code
(CountryProfile.iso_code == RegistryCompany.country).

Every value returned is either real (from CountryProfile or the harvester) or
None — the template labels None as "unavailable". No statistic is invented.
"""
from __future__ import annotations


def _val(x):
    """Pass through real values; None stays None (template → 'unavailable')."""
    return x


def country_intelligence(country) -> dict:
    """Read-only intelligence rollup for a CountryProfile instance."""
    from harvester.models import RegistryCompany, Evidence, Datapoint
    from harvester.rollups import _latest_metric_value
    from django.db.models import Max

    iso = (country.iso_code or "").upper()
    companies = list(RegistryCompany.objects.filter(country=iso, is_active=True)
                     .order_by("priority", "company_name"))
    slugs = [c.slug for c in companies]

    evidence_count = Evidence.objects.filter(company_slug__in=slugs).count() if slugs else 0
    datapoint_count = Datapoint.objects.filter(company_slug__in=slugs).count() if slugs else 0
    last_updated = (Evidence.objects.filter(company_slug__in=slugs)
                    .aggregate(m=Max("retrieved_at"))["m"] if slugs else None)

    # per-company rollup, ranked by operating profit (None last)
    rows = []
    for c in companies:
        op, _ = _latest_metric_value(c.slug, "operating_profit")
        rev, _ = _latest_metric_value(c.slug, "revenue")
        rows.append({
            "slug": c.slug, "company_name": c.company_name,
            "sector": c.sector, "subsector": c.subsector,
            "operating_profit": op, "revenue": rev,
            "evidence_count": Evidence.objects.filter(company_slug=c.slug).count(),
            "datapoint_count": Datapoint.objects.filter(company_slug=c.slug).count(),
        })
    rows.sort(key=lambda r: (r["operating_profit"] is not None,
                             r["operating_profit"] or 0), reverse=True)

    companies_count = len(companies)
    # transparent state: registry seeded but not yet harvested vs no registry yet
    no_registry = companies_count == 0
    data_expansion = companies_count > 0 and evidence_count == 0

    return {
        "iso": iso,
        # Overview (CountryProfile national dataset; None → unavailable)
        "overview": {
            "gdp_usd": _val(country.gdp_usd),
            "gdp_growth_pct": _val(country.gdp_growth_pct),
            "inflation_pct": _val(country.inflation_pct),
            "population_millions": _val(country.population_millions),
            "industrial_gdp_share": _val(country.industrial_gdp_share),
        },
        # Energy profile
        "energy": {
            "renewable_energy_share": _val(country.renewable_energy_share),
            "fossil_fuel_dependency": _val(country.fossil_fuel_dependency),
            "co2_megatonnes": _val(country.co2_megatonnes),
        },
        # Governance profile
        "governance": {
            "policy_environment_score": _val(country.policy_environment_score),
            "transparency_score": _val(country.transparency_score),
            "investment_climate_score": _val(country.investment_climate_score),
            "transition_readiness_score": _val(country.transition_readiness_score),
        },
        "data_sources": getattr(country, "data_sources", "") or "",
        # Harvester-backed intelligence
        "companies_count": companies_count,
        "evidence_count": evidence_count,
        "datapoint_count": datapoint_count,
        "last_updated": last_updated,
        "companies": rows,
        "no_registry": no_registry,
        "data_expansion": data_expansion,
    }
