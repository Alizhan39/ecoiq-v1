"""
EcoIQ Source Registry — the global source catalog (machine-readable).

Each entry is a global (company-agnostic) source definition. Company-specific
sources (e.g. one company's annual report PDF) are registered per-company by
the harvester at discovery time; this catalog seeds the shared, reusable
sources and their base trust + cadence.

confidence_base (0..1) encodes source-class trust, NOT any company assessment:
  primary regulated filings / standards bodies → high
  company self-disclosure                      → medium-high
  reputable media                              → medium
  licensed/aggregated (not yet integrated)     → catalogued, is_active=False

Adding a row here and re-running `seed_sources` is idempotent (keyed by
source_type + name).
"""
from __future__ import annotations

from .constants import FUTURE_SOURCE_TYPES

# (source_type, name, source_owner, source_url, confidence_base, update_frequency)
CATALOG = [
    # ── Company self-disclosure (per-company URLs filled at discovery) ──
    ("annual_report", "Annual Report", "Company", "", 0.85, "annual"),
    ("sustainability_report", "Sustainability Report", "Company", "", 0.75, "annual"),
    ("esg_report", "ESG Report", "Company", "", 0.75, "annual"),
    ("tcfd_report", "TCFD Report", "Company", "", 0.80, "annual"),
    ("transition_plan", "Climate Transition Plan", "Company", "", 0.78, "annual"),
    ("company_website", "Company Website", "Company", "", 0.55, "monthly"),
    ("investor_relations", "Investor Relations", "Company", "", 0.70, "quarterly"),
    ("press_release", "Press Release", "Company", "", 0.60, "adhoc"),

    # ── UK regulated filings & regulators ──
    ("companies_house", "Companies House", "Companies House (UK)",
     "https://find-and-update.company-information.service.gov.uk/", 0.92, "adhoc"),
    ("fca_filing", "FCA National Storage Mechanism", "Financial Conduct Authority",
     "https://data.fca.org.uk/artefacts/", 0.92, "adhoc"),
    ("regulatory_filing", "Regulatory Filing", "Regulator", "", 0.85, "adhoc"),
    ("ofgem", "Ofgem", "Office of Gas and Electricity Markets",
     "https://www.ofgem.gov.uk/", 0.88, "adhoc"),
    ("environment_agency", "Environment Agency", "Environment Agency (UK)",
     "https://www.gov.uk/government/organisations/environment-agency", 0.88, "adhoc"),

    # ── Reputable media (reference) ──
    ("financial_times", "Financial Times", "Financial Times",
     "https://www.ft.com/", 0.65, "daily"),
    ("reuters", "Reuters", "Reuters", "https://www.reuters.com/", 0.65, "daily"),
    ("bloomberg", "Bloomberg", "Bloomberg", "https://www.bloomberg.com/", 0.65, "daily"),

    # ── Procurement / tenders ──
    ("tender_portal", "Contracts Finder", "UK Government",
     "https://www.contractsfinder.service.gov.uk/", 0.75, "adhoc"),
    ("procurement_db", "Find a Tender", "UK Government",
     "https://www.find-tender.service.gov.uk/", 0.75, "adhoc"),

    # ── International datasets ──
    ("world_bank", "World Bank Open Data", "World Bank",
     "https://data.worldbank.org/", 0.80, "annual"),
    ("iea", "IEA", "International Energy Agency", "https://www.iea.org/", 0.82, "annual"),
    ("ebrd", "EBRD", "European Bank for Reconstruction and Development",
     "https://www.ebrd.com/", 0.80, "adhoc"),
    ("oecd", "OECD", "OECD", "https://www.oecd.org/", 0.80, "annual"),
    ("undp", "UNDP", "United Nations Development Programme",
     "https://www.undp.org/", 0.78, "annual"),

    # ── Disclosure frameworks / standards bodies ──
    ("cdp", "CDP", "CDP (Carbon Disclosure Project)",
     "https://www.cdp.net/", 0.82, "annual"),
    ("gri", "GRI", "Global Reporting Initiative",
     "https://www.globalreporting.org/", 0.80, "adhoc"),
    ("sasb", "SASB", "SASB / IFRS Foundation",
     "https://sasb.ifrs.org/", 0.80, "adhoc"),
    ("issb", "ISSB", "IFRS Foundation",
     "https://www.ifrs.org/groups/international-sustainability-standards-board/", 0.82, "adhoc"),
    ("sbti", "Science Based Targets initiative", "SBTi",
     "https://sciencebasedtargets.org/", 0.85, "adhoc"),

    # ── Licensed / future (catalogued, is_active=False) ──
    ("msci", "MSCI ESG", "MSCI", "https://www.msci.com/", 0.80, "annual"),
    ("sustainalytics", "Sustainalytics", "Morningstar Sustainalytics",
     "https://www.sustainalytics.com/", 0.80, "annual"),
    ("refinitiv", "Refinitiv (LSEG)", "LSEG", "https://www.lseg.com/", 0.80, "annual"),
]


def catalog_rows():
    """Yield normalized dicts for seeding (is_active derived from FUTURE set)."""
    for source_type, name, owner, url, conf, freq in CATALOG:
        yield {
            "source_type": source_type,
            "name": name,
            "source_owner": owner,
            "source_url": url,
            "confidence_base": conf,
            "update_frequency": freq,
            "is_active": source_type not in FUTURE_SOURCE_TYPES,
        }
