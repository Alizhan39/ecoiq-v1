"""
EcoIQ Evidence Harvester — shared vocabularies (machine-readable, additive).

These are the controlled vocabularies the acquisition layer is built on:
source types, update frequencies, the 25 evidence categories, and the
verification statuses. Kept in one place so models, the seed catalog, the
verification engine, and (later) the normalization engine agree on the values.

No scoring, no interpretation here — just the enumerations.
"""
from __future__ import annotations

# ── Source types ────────────────────────────────────────────────────────────
# value, human label. Order roughly follows source priority (primary filings →
# regulators → media → international datasets → licensed/future).
SOURCE_TYPES = [
    ("annual_report", "Annual Report"),
    ("sustainability_report", "Sustainability Report"),
    ("esg_report", "ESG Report"),
    ("tcfd_report", "TCFD Report"),
    ("transition_plan", "Transition Plan"),
    ("company_website", "Company Website"),
    ("investor_relations", "Investor Relations Page"),
    ("companies_house", "Companies House"),
    ("fca_filing", "FCA Filing"),
    ("regulatory_filing", "Regulatory Filing"),
    ("ofgem", "Ofgem"),
    ("environment_agency", "Environment Agency"),
    ("financial_times", "Financial Times"),
    ("reuters", "Reuters"),
    ("bloomberg", "Bloomberg (reference)"),
    ("press_release", "Press Release"),
    ("tender_portal", "Tender Portal"),
    ("procurement_db", "Procurement Database"),
    ("world_bank", "World Bank"),
    ("iea", "IEA"),
    ("ebrd", "EBRD"),
    ("oecd", "OECD"),
    ("undp", "UNDP"),
    ("cdp", "CDP"),
    ("gri", "GRI"),
    ("sasb", "SASB"),
    ("issb", "ISSB"),
    ("sbti", "SBTi"),
    ("msci", "MSCI (future)"),
    ("sustainalytics", "Sustainalytics (future)"),
    ("refinitiv", "Refinitiv (future)"),
]

# Licensed / not-yet-integrated sources — seeded as is_active=False so they are
# catalogued but never harvested or fabricated.
FUTURE_SOURCE_TYPES = {"msci", "sustainalytics", "refinitiv", "bloomberg"}

# ── Update frequency ────────────────────────────────────────────────────────
UPDATE_FREQUENCIES = [
    ("realtime", "Real-time"),
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
    ("quarterly", "Quarterly"),
    ("annual", "Annual"),
    ("adhoc", "Ad hoc"),
]

# ── Evidence categories (the 25 required) ───────────────────────────────────
EVIDENCE_CATEGORIES = [
    ("financial", "Financial"),
    ("governance", "Governance"),
    ("board", "Board"),
    ("ownership", "Ownership"),
    ("executive_compensation", "Executive Compensation"),
    ("strategy", "Strategy"),
    ("risk", "Risk"),
    ("climate", "Climate"),
    ("emissions", "Emissions"),
    ("energy", "Energy"),
    ("water", "Water"),
    ("waste", "Waste"),
    ("air_pollution", "Air Pollution"),
    ("biodiversity", "Biodiversity"),
    ("land_use", "Land Use"),
    ("supply_chain", "Supply Chain"),
    ("human_rights", "Human Rights"),
    ("workforce", "Workforce"),
    ("health_safety", "Health & Safety"),
    ("cybersecurity", "Cybersecurity"),
    ("innovation", "Innovation"),
    ("capital_projects", "Capital Projects"),
    ("regulatory_compliance", "Regulatory Compliance"),
    ("future_commitments", "Future Commitments"),
    ("contradictions", "Contradictions"),
]
CATEGORY_VALUES = [c[0] for c in EVIDENCE_CATEGORIES]

# ── Verification status ─────────────────────────────────────────────────────
# Including the explicit "absence" markers so missing data is recorded, never
# fabricated or silently skipped.
VERIFICATION_STATUSES = [
    ("VERIFIED", "Verified — corroborated by an independent source"),
    ("PARTIAL", "Partial — single credible source, not yet corroborated"),
    ("UNVERIFIED", "Unverified — recorded but not assessed"),
    ("CONTRADICTED", "Contradicted — sources disagree"),
    ("NOT_FOUND", "Not found — no source located"),
    ("INSUFFICIENT_EVIDENCE", "Insufficient evidence — source too weak to assert"),
]

# ── Normalization status ────────────────────────────────────────────────────
# A Datapoint is NORMALIZED only when a clean value was deterministically
# extracted. When the metric is discussed but no value can be parsed, the row is
# recorded as NOT_NORMALIZED with value=None — never a fabricated number.
NORMALIZATION_STATUSES = [
    ("NORMALIZED", "Normalized — clean value extracted"),
    ("NOT_NORMALIZED", "Not normalized — metric present, no parseable value"),
]

# ── Registry sectors (Slice 6 target universe) ──────────────────────────────
REGISTRY_SECTORS = [
    ("energy", "Energy"),
    ("utilities", "Utilities"),
    ("water", "Water"),
    ("infrastructure", "Infrastructure"),
    ("industrials", "Industrials"),
]
