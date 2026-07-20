"""
EcoIQ Evidence Harvester — SourceAdapter layer (Slice 2, additive).

A SourceAdapter turns a source into a list of EvidenceCandidate records. The
layer is deterministic and offline-safe: adapters that need the network are
declared with requires_network=True and, when no network/input is available,
return [] — which the pipeline records as NOT_FOUND. Nothing is ever fabricated.

Adapter families
  DocumentAdapter        — operator-registered documents (annual/sustainability/
                           ESG reports, regulatory filings, press releases).
  ProfileDerivedAdapter  — reads data EcoIQ already stores on CompanyProfile
                           (company website, investor relations). Fully offline.
  NetworkAdapter         — Companies House, news. Wired but inert offline.

Each adapter advertises a source_type from harvester.constants.SOURCE_TYPES.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

# ── Candidate record (pre-dedup, pre-storage) ───────────────────────────────
@dataclass
class EvidenceCandidate:
    company_slug: str
    category: str
    statement: str                       # the core fact text (used for dedup)
    source_type: str
    title: str = ""
    url: str = ""
    publication_date: Optional[date] = None
    excerpt: str = ""
    full_text: str = ""
    document_type: str = ""
    source_owner: str = ""
    # feat/company-discovery-ranking (PR 11) — where in a multi-chunk
    # source document this candidate came from (e.g. "Page 14", "Section:
    # Climate & Energy") so evidence stays traceable to an exact location,
    # never just "somewhere in this document". Blank for single-fact
    # sources with no meaningful location unit.
    source_location: str = ""

    def __post_init__(self):
        if not self.excerpt:
            self.excerpt = (self.statement or "")[:600]


# ── Deterministic free-text → category classifier ───────────────────────────
# Conservative keyword map; returns the first category whose keywords match, or
# None (caller decides a fallback). Order matters — most specific first.
CATEGORY_KEYWORDS = [
    ("emissions", ("scope 1", "scope 2", "scope 3", "co2", "ghg", "greenhouse", "tco2e", "carbon emission")),
    ("climate", ("net zero", "net-zero", "decarbon", "climate", "paris agreement", "1.5°c", "sbti", "transition plan")),
    ("energy", ("renewable", "generation capacity", "installed capacity", "grid", "electricity", "gas network", "megawatt", "gwh", "twh")),
    ("water", ("water withdrawal", "water consumption", "water discharge", "water stress")),
    ("waste", ("waste", "recycl", "landfill", "circular economy")),
    ("air_pollution", ("nox", "sox", "pm2.5", "particulate", "air quality")),
    ("biodiversity", ("biodiversity", "habitat", "species", "ecosystem")),
    ("land_use", ("land use", "land-use", "deforest", "land degradation")),
    ("emissions", ("emission",)),
    ("executive_compensation", ("remuneration", "executive pay", "ceo pay", "bonus", "lti")),
    ("board", ("board of directors", "non-executive", "chair of the board", "board independence")),
    ("ownership", ("shareholder", "ownership", "major holding", "tr-1", "beneficial owner")),
    ("governance", ("governance", "audit committee", "internal control", "ethics", "anti-corruption")),
    ("financial", ("revenue", "ebitda", "operating profit", "net debt", "capex", "dividend", "profit after tax", "turnover")),
    ("capital_projects", ("capital investment", "capital project", "infrastructure project", "construction of")),
    ("workforce", ("employees", "headcount", "workforce", "diversity", "gender pay")),
    ("health_safety", ("health and safety", "fatalities", "lost time injury", "ltifr", "occupational")),
    ("human_rights", ("human rights", "modern slavery", "forced labour", "child labour")),
    ("supply_chain", ("supply chain", "supplier", "procurement", "critical mineral")),
    ("cybersecurity", ("cyber", "scada", "ot security", "data breach", "ransomware")),
    ("innovation", ("research and development", "r&d", "patent", "innovation", "digital transformation")),
    ("regulatory_compliance", ("fine", "penalty", "enforcement", "breach of", "regulatory action", "sanction")),
    ("future_commitments", ("by 2030", "by 2035", "by 2040", "by 2050", "target to", "commit to", "pledge")),
    ("risk", ("principal risk", "risk factor", "uncertaint", "exposure to")),
    ("strategy", ("strategy", "strategic priorit", "business model", "outlook")),
]


def classify_text(text: str, default: str = "strategy") -> str:
    """Best-effort deterministic category for free text. Never raises."""
    t = (text or "").lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(k in t for k in keywords):
            return category
    return default


# ── Adapter interface ───────────────────────────────────────────────────────
class BaseSourceAdapter:
    """Abstract adapter. Subclasses set `source_type` and implement collect()."""

    source_type: str = ""
    requires_network: bool = False

    def collect(self, company_slug: str, *, documents=None, profile=None) -> list:
        """Return a list[EvidenceCandidate]. Must never fabricate: when no input
        is available, return []."""
        raise NotImplementedError


class DocumentAdapter(BaseSourceAdapter):
    """Turns operator-registered documents into candidates.

    `documents` is a list of dicts: {statement, title?, url?, publication_date?,
    category?, full_text?, source_owner?}. category is auto-classified when
    absent. With no documents → [] (the honest NOT_FOUND path).
    """

    document_type = "document"

    def collect(self, company_slug, *, documents=None, profile=None):
        out = []
        for d in (documents or []):
            stmt = (d.get("statement") or d.get("excerpt") or "").strip()
            if not stmt:
                continue
            out.append(EvidenceCandidate(
                company_slug=company_slug,
                category=d.get("category") or classify_text(stmt),
                statement=stmt,
                source_type=self.source_type,
                title=d.get("title", ""),
                url=d.get("url", ""),
                publication_date=d.get("publication_date"),
                excerpt=d.get("excerpt", "") or stmt[:600],
                full_text=d.get("full_text", ""),
                document_type=self.document_type,
                source_owner=d.get("source_owner", ""),
            ))
        return out


class AnnualReportAdapter(DocumentAdapter):
    source_type = "annual_report"
    document_type = "annual_report"


class SustainabilityReportAdapter(DocumentAdapter):
    source_type = "sustainability_report"
    document_type = "sustainability_report"


class ESGReportAdapter(DocumentAdapter):
    source_type = "esg_report"
    document_type = "esg_report"


class RegulatoryFilingAdapter(DocumentAdapter):
    source_type = "regulatory_filing"
    document_type = "regulatory_filing"


class PressReleaseAdapter(DocumentAdapter):
    source_type = "press_release"
    document_type = "press_release"


class ProfileDerivedAdapter(BaseSourceAdapter):
    """Base for adapters that read data EcoIQ already stores on CompanyProfile.

    `fields` maps a CompanyProfile attribute → (category, statement template).
    Fully offline; emits a candidate only when the field has a real value.
    """

    fields: list = []  # list of (attr, category, template)

    def collect(self, company_slug, *, documents=None, profile=None):
        if profile is None:
            return []
        out = []
        for attr, category, template in self.fields:
            val = getattr(profile, attr, None)
            if val in (None, "", [], {}):
                continue
            stmt = template.format(value=val)
            url = ""
            if isinstance(val, str) and val.startswith("http"):
                url = val
            out.append(EvidenceCandidate(
                company_slug=company_slug,
                category=category,
                statement=stmt,
                source_type=self.source_type,
                title=stmt[:120],
                url=url,
                document_type=self.source_type,
                source_owner="Company",
            ))
        return out


class CompanyWebsiteAdapter(ProfileDerivedAdapter):
    source_type = "company_website"
    fields = [
        ("ai_summary", "strategy", "{value}"),
        ("ai_modernization_report", "strategy", "{value}"),
    ]


class InvestorRelationsAdapter(ProfileDerivedAdapter):
    source_type = "investor_relations"
    fields = [
        ("annual_report_url", "financial", "Annual report published at {value}"),
        ("sustainability_report_url", "climate", "Sustainability report published at {value}"),
    ]


class NetworkAdapter(BaseSourceAdapter):
    """Adapter that requires live network/API access. Inert offline: returns []
    so the pipeline records NOT_FOUND rather than inventing data. The concrete
    online implementation arrives in a later, config-gated slice."""

    requires_network = True

    def collect(self, company_slug, *, documents=None, profile=None):
        # No network/credentials wired in this slice → honest empty result.
        return []


class CompaniesHouseAdapter(NetworkAdapter):
    source_type = "companies_house"


class NewsAdapter(NetworkAdapter):
    source_type = "reuters"  # representative news source_type


# ── Registry ────────────────────────────────────────────────────────────────
_ADAPTERS = {
    cls.source_type: cls
    for cls in (
        AnnualReportAdapter, SustainabilityReportAdapter, ESGReportAdapter,
        RegulatoryFilingAdapter, PressReleaseAdapter,
        CompanyWebsiteAdapter, InvestorRelationsAdapter,
        CompaniesHouseAdapter, NewsAdapter,
    )
}

# The 9 source families this slice must support (for coverage assertions).
SUPPORTED_SOURCE_TYPES = sorted(_ADAPTERS.keys())


def get_adapter(source_type: str):
    """Return an adapter instance for a source_type, or None if unsupported."""
    cls = _ADAPTERS.get(source_type)
    return cls() if cls else None
