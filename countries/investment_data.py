"""
EcoIQ Country Intelligence — Priority Investment Opportunities.

Static structured data layer — no DB model required.
Import get_opportunities(slug) in views.py and pass result to template context.

This is NOT an investment marketplace. Data is AI-assisted and indicative only.
Positioning: climate transition intelligence / development finance intelligence.

Schema per opportunity:
  title               str  — opportunity headline
  sector              str  — sector tag label
  impact_level        str  — 'critical' | 'high' | 'medium'
  risk_level          str  — 'high' | 'medium' | 'low'
  ecoiq_priority      str  — 'critical' | 'strategic' | 'important'
  thesis              str  — investment thesis (expanded)
  stakeholders        str  — key institutions and actors (expanded)
  finance_route       str  — likely instruments and structures (expanded)
  rationale           str  — EcoIQ score rationale (expanded)
  strategic_relevance str  — broader geopolitical/market context (expanded)

Future readiness hooks (add when needed):
  - financing_engine_tags: list[str]   → links to FinancingOpportunity slugs
  - dfi_readiness_score: int           → 0-100 DFI eligibility proxy
  - anti_corruption_flag: bool         → governance risk overlay
  - pipeline_status: str               → 'pre-pipeline' | 'active' | 'closed'

Keyed by country slug. Add entries for new countries as needed.
"""

from __future__ import annotations

_OPPORTUNITIES: dict[str, list[dict]] = {

    # ── Kazakhstan ─────────────────────────────────────────────────────────────
    'kazakhstan': [
        {
            'title':    'Methane Reduction in Oil & Gas',
            'sector':   'Oil & Gas',
            'impact_level':   'critical',
            'risk_level':     'medium',
            'ecoiq_priority': 'critical',
            'thesis': (
                "Upstream methane abatement across Kazakhstan's major oil and gas fields "
                "offers measurable, verifiable emissions reduction at relatively low "
                "cost-per-tonne — attractive for carbon credit structuring, DFI concessional "
                "loans and operator compliance capex. OGMP 2.0 alignment creates a credible "
                "reporting baseline for institutional investors."
            ),
            'stakeholders': (
                "KazMunayGas, international JV operators (Chevron, Shell, TotalEnergies), "
                "EBRD, IFC, World Bank, UNFCCC carbon credit verifiers, "
                "Ministry of Energy, national environmental regulator"
            ),
            'finance_route': (
                "EBRD / IFC concessional transition loans + private operator compliance capex "
                "+ voluntary carbon market revenue (VERRA, Gold Standard) "
                "+ blended finance for monitoring infrastructure build-out"
            ),
            'rationale': (
                "Kazakhstan's methane reporting gap is a primary drag on its transparency "
                "and environmental scores. Measurable, third-party-verified methane reduction "
                "is the highest-ROI EcoIQ intervention in the hydrocarbons sector — directly "
                "improving environmental responsibility, evidence completeness and transparency dimensions."
            ),
            'strategic_relevance': (
                "EU CBAM (Carbon Border Adjustment Mechanism) and OGMP 2.0 adoption will make "
                "methane disclosure a commercial prerequisite for Kazakh oil exporters to European "
                "markets by 2026–2027. Early movers gain a competitive export advantage and reduce "
                "regulatory risk in the most important energy trade corridor."
            ),
        },
        {
            'title':    'Coal-to-Clean Heat Modernisation',
            'sector':   'Coal Power / District Heating',
            'impact_level':   'critical',
            'risk_level':     'medium',
            'ecoiq_priority': 'critical',
            'thesis': (
                "Replacing ageing coal boilers in district heating systems across Karaganda, "
                "Ekibastuz and Pavlodar with modern heat pumps, biomass or efficient gas "
                "systems is near-term, shovel-ready infrastructure investment with clear DFI "
                "financing paths, proven technology and measurable pollution reduction outcomes."
            ),
            'stakeholders': (
                "Samruk-Energy, municipal akimats, AIIB, EBRD, ADB, "
                "national government (Ministry of Energy), EU technical assistance programmes, "
                "local engineering and construction firms"
            ),
            'finance_route': (
                "AIIB / EBRD sovereign concessional loans + government infrastructure budget "
                "+ EU technical grant assistance (Central Asia Energy Programme) "
                "+ carbon offset revenue + JETP co-financing framework"
            ),
            'rationale': (
                "Coal district heating drives Kazakhstan's worst air quality scores in industrial "
                "cities and is a major suppressor of the transition readiness EcoIQ dimension. "
                "Decarbonising even a portion of the heating fleet unlocks JETP access and "
                "advances Kazakhstan toward the investment-ready tier."
            ),
            'strategic_relevance': (
                "Kazakhstan's formal JETP (Just Energy Transition Partnership) engagement makes "
                "coal heat modernisation a primary diplomatic and financial opportunity with G7 "
                "partners. EU technical assistance programmes targeting Central Asia specifically "
                "identify district heating as a priority co-investment theme for 2025–2030."
            ),
        },
        {
            'title':    'Renewable Energy + Battery Storage',
            'sector':   'Renewable Energy',
            'impact_level':   'high',
            'risk_level':     'medium',
            'ecoiq_priority': 'strategic',
            'thesis': (
                "Utility-scale solar and wind projects in Kazakhstan are commercially viable "
                "under competitive auction frameworks. Kazakhstan offers strong resource "
                "quality — top 10 globally for solar irradiance and significant wind potential "
                "— improving PPA structures, and growing DFI appetite for Central Asian "
                "renewables as a diversification away from Southeast Asia."
            ),
            'stakeholders': (
                "Ministry of Energy, Samruk-Energy, ACWA Power, IFC, EBRD, "
                "private IPP developers, grid operator KEGOC, "
                "battery storage technology vendors (CATL, BYD, Samsung SDI)"
            ),
            'finance_route': (
                "IPP equity + IFC / EBRD project finance + green bond issuance "
                "+ sovereign PPA with government credit backstop "
                "+ GCF (Green Climate Fund) co-financing for storage components"
            ),
            'rationale': (
                "Renewable scale-up is the single most impactful EcoIQ lever for Kazakhstan — "
                "simultaneously improving energy transition, climate responsibility and industrial "
                "modernisation scores. Every gigawatt of renewable capacity added measurably shifts "
                "the national EcoIQ index and expands the DFI universe available to the country."
            ),
            'strategic_relevance': (
                "Kazakhstan's geography makes it a natural hub for a Central Asian renewable "
                "energy corridor. Belt & Road adjacency, proximity to Chinese demand and potential "
                "power export to Russia and future regional grids position Kazakhstan renewable "
                "projects as strategic, not just commercial, infrastructure investments."
            ),
        },
        {
            'title':    'Critical Minerals Clean Processing',
            'sector':   'Critical Minerals',
            'impact_level':   'high',
            'risk_level':     'medium',
            'ecoiq_priority': 'strategic',
            'thesis': (
                "Kazakhstan holds significant deposits of lithium, cobalt, copper and rare "
                "earths. Investing in domestic refining and processing capacity powered by "
                "clean energy positions Kazakhstan as a premium ESG-aligned supplier for "
                "EV battery supply chains and EU Critical Raw Materials Act buyers — commanding "
                "premium valuations over raw ore exporters."
            ),
            'stakeholders': (
                "Ministry of Industry, KazMinerals, Eurasian Resources Group (ERG), "
                "EU Commission (CRMA), US Development Finance Corporation (DFC), "
                "AIIB, strategic industrial investors, clean energy partners"
            ),
            'finance_route': (
                "Strategic FDI + AIIB project finance + blended finance structures "
                "+ EU and US bilateral partnership programmes "
                "+ export credit agencies (UK UKEF, German ECA) "
                "+ green bond financing for clean energy supply to processing facilities"
            ),
            'rationale': (
                "Moving from raw extraction to high-value processing significantly improves "
                "Kazakhstan's industrial modernisation and national value EcoIQ scores — the "
                "two dimensions most closely correlated with premium FDI quality and long-term "
                "sovereign creditworthiness. Clean processing unlocks investment-ready tier access."
            ),
            'strategic_relevance': (
                "EU Critical Raw Materials Act (2024) and US Inflation Reduction Act supply "
                "chain requirements create structured policy demand for Kazakhstan's mineral "
                "resources — but only when processed under credible ESG and governance standards. "
                "Kazakhstan is one of very few non-allied countries with both resource base and "
                "political willingness to engage Western supply chain partnerships."
            ),
        },
        {
            'title':    'Industrial Pollution Monitoring Infrastructure',
            'sector':   'Environmental Infrastructure',
            'impact_level':   'high',
            'risk_level':     'low',
            'ecoiq_priority': 'strategic',
            'thesis': (
                "Building Kazakhstan's national environmental monitoring network is a "
                "precondition for DFI access across multiple sectors — creating a foundational "
                "infrastructure investment with compounding multiplier effects across mining, "
                "energy, industrial and transition finance projects. Low risk, high enabling value."
            ),
            'stakeholders': (
                "Ministry of Ecology, World Bank, Green Climate Fund (GCF), "
                "regional governments, KazMinerals, mining companies, "
                "environmental technology vendors, international NGOs"
            ),
            'finance_route': (
                "World Bank / GCF grants + government infrastructure budget "
                "+ mining company compliance contributions (regulatory mandate) "
                "+ technology vendor partnerships + bilateral donor technical assistance"
            ),
            'rationale': (
                "Evidence completeness and transparency are Kazakhstan's two lowest EcoIQ "
                "sub-scores. Environmental monitoring infrastructure directly improves both "
                "dimensions — unlocking access to a significantly broader DFI universe and "
                "improving the quality and reliability of all EcoIQ intelligence for the country."
            ),
            'strategic_relevance': (
                "Kazakhstan's ambition to attract ESG-aligned FDI and meet international "
                "climate finance standards requires auditable, independently published "
                "environmental data. Monitoring infrastructure is the foundational layer for "
                "any credible industrial transition narrative — without it, every other "
                "investment case rests on weak evidence."
            ),
        },
        {
            'title':    'Green Industrial Zones',
            'sector':   'Industrial Policy',
            'impact_level':   'high',
            'risk_level':     'medium',
            'ecoiq_priority': 'important',
            'thesis': (
                "Designating 2–3 existing Kazakh SEZs as certified green industrial zones "
                "creates premium FDI destinations for clean manufacturing, processing and "
                "export-oriented supply chains — directly competitive with Southeast Asian "
                "and Eastern European greenfield investment destinations for ESG-aligned "
                "manufacturing capital seeking non-China supply chain diversification."
            ),
            'stakeholders': (
                "Ministry of Industry, Astana International Financial Centre (AIFC), "
                "AIIB, IFC, EU trade and investment programmes, "
                "strategic manufacturing FDI investors, clean energy developers"
            ),
            'finance_route': (
                "Government SEZ infrastructure investment + AIIB / IFC co-financing "
                "+ green bond financing for zone-level clean energy infrastructure "
                "+ FDI incentive packages + EU taxonomy-aligned financing frameworks"
            ),
            'rationale': (
                "Green zone designation simultaneously improves industrial modernisation, "
                "policy environment and investment climate EcoIQ scores — the combined effect "
                "moves Kazakhstan materially toward the investment-ready tier and signals "
                "credible transition intent to international capital markets."
            ),
            'strategic_relevance': (
                "Kazakhstan's strategic ambition to diversify its economy away from raw commodity "
                "dependence makes green industrial zones a policy imperative. EU taxonomy alignment "
                "would unlock preferential financing access and open supply chain partnership "
                "opportunities with European manufacturers seeking post-China sourcing alternatives "
                "across automotive, electronics and clean energy sectors."
            ),
        },
    ],

    # ── Add further countries below ────────────────────────────────────────────
    # 'uzbekistan': [ ... ],
    # 'mongolia':   [ ... ],
}


def get_opportunities(country_slug: str) -> list[dict]:
    """Return the investment opportunity list for a country slug, or []."""
    return _OPPORTUNITIES.get(country_slug, [])
