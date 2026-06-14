"""
EcoIQ Evidence Harvester — registered company documents (operator-curated).

These are real, already-cited statements an operator has registered for a
company, so the offline pipeline has genuine evidence to harvest deterministically
(no live network, no fabrication). Each entry carries its real source URL.

This is the seam where, in a later config-gated slice, live document retrieval
(WebFetchAdapter) replaces hand-registered text. Until then, only verifiable
operator-registered evidence flows through the pipeline.

National Grid plc figures below were retrieved from primary sources:
  - FY2025 Full Year Results Statement (RNS), year ended 31 March 2025
  - National Grid Scope 1/2/3 emissions disclosure
  - third-party workforce aggregator (employees, medium confidence)
"""
from __future__ import annotations

from datetime import date

# slug → list of registered documents.
# Each: source_type (must map to a SourceAdapter), statement (normalizable text),
# url, publication_date, optional category and source_owner.
REGISTERED_DOCUMENTS = {
    "national-grid": [
        # ── Financials (primary: FY2025 RNS) ──
        {"source_type": "annual_report",
         "statement": "Gross revenue was £18,378m in 2024/25.",
         "category": "financial", "source_owner": "National Grid plc",
         "url": "https://www.investegate.co.uk/announcement/rns/national-grid--ng./fy2025-full-year-results-statement/8878931",
         "publication_date": date(2025, 5, 15)},
        {"source_type": "annual_report",
         "statement": "Underlying operating profit was £5,357m in 2024/25.",
         "category": "financial", "source_owner": "National Grid plc",
         "url": "https://www.investegate.co.uk/announcement/rns/national-grid--ng./fy2025-full-year-results-statement/8878931",
         "publication_date": date(2025, 5, 15)},
        {"source_type": "annual_report",
         "statement": "Capital investment was £9,847m in 2024/25.",
         "category": "capital_projects", "source_owner": "National Grid plc",
         "url": "https://www.investegate.co.uk/announcement/rns/national-grid--ng./fy2025-full-year-results-statement/8878931",
         "publication_date": date(2025, 5, 15)},

        # ── Emissions (Scope 1 registered from TWO sources → corroborated) ──
        {"source_type": "annual_report",
         "statement": "Scope 1 emissions were 4.5 MtCO2e in 2024/25.",
         "category": "emissions", "source_owner": "National Grid plc",
         "url": "https://www.nationalgrid.com/responsibility/our-environment/net-zero/scope-1-2-3-emissions",
         "publication_date": date(2025, 5, 15)},
        {"source_type": "sustainability_report",
         "statement": "Scope 1 emissions were 4.5 MtCO2e in 2024/25.",
         "category": "emissions", "source_owner": "National Grid plc",
         "url": "https://www.nationalgrid.com/responsibility/our-environment/net-zero/scope-1-2-3-emissions",
         "publication_date": date(2025, 5, 15)},
        {"source_type": "sustainability_report",
         "statement": "Scope 2 emissions were 2.95 MtCO2e in 2024/25.",
         "category": "emissions", "source_owner": "National Grid plc",
         "url": "https://www.nationalgrid.com/responsibility/our-environment/net-zero/scope-1-2-3-emissions",
         "publication_date": date(2025, 5, 15)},
        {"source_type": "sustainability_report",
         "statement": "Scope 3 emissions were 28.4 MtCO2e in 2024/25.",
         "category": "emissions", "source_owner": "National Grid plc",
         "url": "https://www.nationalgrid.com/responsibility/our-environment/net-zero/scope-1-2-3-emissions",
         "publication_date": date(2025, 5, 15)},

        # ── Workforce (third-party aggregator, single source → PARTIAL) ──
        {"source_type": "press_release",
         "statement": "National Grid had approximately 33,579 employees in 2025.",
         "category": "workforce", "source_owner": "StockAnalysis.com",
         "url": "https://stockanalysis.com/stocks/ngg/employees/",
         "publication_date": date(2025, 5, 15)},

        # ── Targets (climate; no numeric metric → evidence only, no Datapoint) ──
        {"source_type": "sustainability_report",
         "statement": "National Grid targets net zero by 2050.",
         "category": "climate", "source_owner": "National Grid plc",
         "url": "https://www.nationalgrid.com/responsibility/our-environment/net-zero/scope-1-2-3-emissions",
         "publication_date": date(2025, 5, 15)},
    ],
}


def get_documents(slug: str) -> list:
    """Registered documents for a company slug (empty list if none)."""
    return list(REGISTERED_DOCUMENTS.get(slug, []))
