"""
EcoIQ Harvester — UK Energy / Utilities / Water / Infrastructure / Industrials
target registry (Slice 6, phase-1: first 25 companies). Registry only.

No-fabrication policy: only fields that can be asserted with confidence are
populated — company_name, slug, sector, subsector, country, ticker (LSE-listed
plcs only), and the primary corporate website domain. Volatile deep links
(investor_relations_url, annual_report_url, sustainability_report_url) and
companies_house_number are intentionally left blank, to be filled by discovery
or operator verification later — never invented here.
"""
from __future__ import annotations

# (slug, company_name, ticker, sector, subsector, website)
# country defaults to "GB". Blank ticker = not a directly LSE-listed plc
# (private, mutual, or a subsidiary of a foreign-listed parent).
COMPANIES = [
    ("national-grid", "National Grid plc", "NG.", "utilities",
     "Electricity & gas networks", "https://www.nationalgrid.com"),
    ("sse", "SSE plc", "SSE.", "energy",
     "Generation & networks", "https://www.sse.com"),
    ("centrica", "Centrica plc", "CNA.", "energy",
     "Supply & services", "https://www.centrica.com"),
    ("scottishpower", "ScottishPower", "", "energy",
     "Supply & networks (Iberdrola)", "https://www.scottishpower.com"),
    ("severn-trent", "Severn Trent plc", "SVT.", "water",
     "Water & wastewater", "https://www.severntrent.com"),
    ("united-utilities", "United Utilities Group plc", "UU.", "water",
     "Water & wastewater", "https://www.unitedutilities.com"),
    ("pennon", "Pennon Group plc", "PNN.", "water",
     "Water (South West Water)", "https://www.pennon-group.co.uk"),
    ("drax", "Drax Group plc", "DRX.", "energy",
     "Power generation (biomass)", "https://www.drax.com"),
    ("national-gas", "National Gas", "", "infrastructure",
     "Gas transmission", "https://www.nationalgas.com"),
    ("octopus-energy", "Octopus Energy", "", "energy",
     "Retail supply", "https://octopus.energy"),
    ("edf-energy-uk", "EDF Energy UK", "", "energy",
     "Generation & supply (nuclear)", "https://www.edfenergy.com"),
    ("eon-uk", "E.ON UK", "", "energy",
     "Retail supply", "https://www.eonenergy.com"),
    ("ovo-energy", "OVO Energy", "", "energy",
     "Retail supply", "https://www.ovoenergy.com"),
    ("thames-water", "Thames Water", "", "water",
     "Water & wastewater", "https://www.thameswater.co.uk"),
    ("anglian-water", "Anglian Water", "", "water",
     "Water & wastewater", "https://www.anglianwater.co.uk"),
    ("northumbrian-water", "Northumbrian Water", "", "water",
     "Water & wastewater", "https://www.nwl.co.uk"),
    ("yorkshire-water", "Yorkshire Water", "", "water",
     "Water & wastewater", "https://www.yorkshirewater.com"),
    ("cadent-gas", "Cadent Gas", "", "infrastructure",
     "Gas distribution", "https://cadentgas.com"),
    ("sgn", "SGN", "", "infrastructure",
     "Gas distribution", "https://www.sgn.co.uk"),
    ("northern-powergrid", "Northern Powergrid", "", "infrastructure",
     "Electricity distribution", "https://www.northernpowergrid.com"),
    ("uk-power-networks", "UK Power Networks", "", "infrastructure",
     "Electricity distribution", "https://www.ukpowernetworks.co.uk"),
    ("sp-energy-networks", "SP Energy Networks", "", "infrastructure",
     "Electricity distribution", "https://www.spenergynetworks.co.uk"),
    ("western-power-distribution", "Western Power Distribution", "", "infrastructure",
     "Electricity distribution", "https://www.westernpower.co.uk"),
    ("shell-uk", "Shell UK", "", "energy",
     "Oil & gas", "https://www.shell.co.uk"),
    ("bp", "BP p.l.c.", "BP.", "energy",
     "Oil & gas", "https://www.bp.com"),
]


def registry_rows():
    """Yield normalized dicts for seeding. Report URLs + CH number left blank."""
    for i, (slug, name, ticker, sector, subsector, website) in enumerate(COMPANIES):
        yield {
            "slug": slug,
            "company_name": name,
            "ticker": ticker,
            "sector": sector,
            "subsector": subsector,
            "country": "GB",
            "website": website,
            "investor_relations_url": "",
            "annual_report_url": "",
            "sustainability_report_url": "",
            "companies_house_number": "",
            "priority": i + 1,
        }
