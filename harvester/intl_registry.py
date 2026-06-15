"""
EcoIQ Harvester — international target registry (Kazakhstan / Saudi Arabia /
Türkiye), Track B initial seed. Registries first; documents and harvesting follow.

No-fabrication policy: only confidently-assertable identifying metadata is
populated — company_name, slug, sector, subsector, country (ISO-2). ticker,
website, report URLs and any registry numbers are intentionally left blank,
to be added with verified sources in the documents/harvesting phase — never
invented here.
"""
from __future__ import annotations

# (slug, company_name, sector, subsector, country_iso)
COMPANIES = [
    # ── Kazakhstan (KZ) ──
    ("kazmunaygas", "KazMunayGas", "energy", "Oil & gas (national)", "KZ"),
    ("qazaqgaz", "QazaqGaz", "infrastructure", "Gas transmission (national)", "KZ"),
    ("samruk-energy", "Samruk-Energy", "energy", "Power generation", "KZ"),
    ("kegoc", "KEGOC", "infrastructure", "Electricity grid operator", "KZ"),
    ("kazatomprom", "Kazatomprom", "energy", "Uranium / nuclear fuel", "KZ"),
    # ── Saudi Arabia (SA) ──
    ("saudi-aramco", "Saudi Aramco", "energy", "Oil & gas (integrated)", "SA"),
    ("saudi-electricity-company", "Saudi Electricity Company (SEC)", "utilities", "Electricity", "SA"),
    ("acwa-power", "ACWA Power", "energy", "Power & water generation", "SA"),
    ("sabic", "SABIC", "industrials", "Petrochemicals", "SA"),
    ("maaden", "Ma'aden (Saudi Arabian Mining Company)", "industrials", "Mining", "SA"),
    # ── Türkiye (TR) ──
    ("botas", "BOTAŞ", "infrastructure", "Gas pipelines & transmission", "TR"),
    ("teias", "TEİAŞ", "infrastructure", "Electricity transmission", "TR"),
    ("tpao", "TPAO", "energy", "Oil & gas (national)", "TR"),
    ("tupras", "Tüpraş", "energy", "Oil refining", "TR"),
    ("enerjisa", "Enerjisa", "energy", "Electricity distribution & retail", "TR"),
]


def registry_rows(start_priority: int = 100):
    """Yield normalized dicts for seeding. Identifying metadata only; ticker,
    website, report URLs and registry numbers left blank pending verification."""
    for i, (slug, name, sector, subsector, iso) in enumerate(COMPANIES):
        yield {
            "slug": slug,
            "company_name": name,
            "ticker": "",
            "sector": sector,
            "subsector": subsector,
            "country": iso,
            "website": "",
            "investor_relations_url": "",
            "annual_report_url": "",
            "sustainability_report_url": "",
            "companies_house_number": "",
            "priority": start_priority + i,
        }
