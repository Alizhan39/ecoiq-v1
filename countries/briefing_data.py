"""
EcoIQ Country Intelligence — Investor Briefing Static Content.

Narrative text, transition risks and governance warnings per country slug.
Supplements the DB-backed country profile data rendered in the briefing view.

Each entry schema:
  executive_summary  str        — 2-4 paragraph investment-grade memo opener
  transition_risks   list[dict] — [{title, sector, severity, detail}]
  governance_warnings list[dict]— [{title, severity, detail}]

severity values: 'critical' | 'high' | 'medium' | 'low'

Add entries for new country slugs as needed.
"""

from __future__ import annotations

_CONTENT: dict[str, dict] = {

    'kazakhstan': {

        'executive_summary': (
            "Kazakhstan is Central Asia's largest economy and one of its most significant "
            "fossil fuel producers, generating approximately $220 billion in annual GDP with "
            "hydrocarbons accounting for over 40% of export revenue. The country sits at a "
            "critical transition inflection point: growing international pressure to reduce "
            "methane emissions, decarbonise its ageing coal power fleet and strengthen "
            "governance standards — combined with substantial untapped renewable energy "
            "potential and a world-class critical minerals endowment — creates a complex but "
            "compelling investment landscape.\n\n"

            "EcoIQ intelligence identifies Kazakhstan's key structural strengths as its "
            "natural resource base, geographic centrality in Eurasian logistics corridors and "
            "an improving macroeconomic environment. The primary constraints on investment "
            "readiness are governance quality, transparency deficits and underdeveloped "
            "environmental disclosure infrastructure. Transition finance appetite from EBRD, "
            "AIIB, ADB and IFC is strong for structurally sound projects, but requires "
            "enhanced due diligence frameworks.\n\n"

            "The near-term opportunity set is concentrated in methane abatement, coal-to-clean "
            "district heating modernisation, utility-scale renewable energy build-out and "
            "critical minerals clean processing — all supported by credible DFI financing "
            "pathways. Governance improvement remains the primary prerequisite for unlocking "
            "full MDB eligibility and premium foreign direct investment access."
        ),

        'transition_risks': [
            {
                'title':    'Methane Leakage in Upstream Oil & Gas',
                'sector':   'Oil & Gas',
                'severity': 'critical',
                'detail': (
                    "Uncontrolled methane leakage from ageing upstream infrastructure represents "
                    "Kazakhstan's most material near-term climate liability. Limited monitoring "
                    "infrastructure and minimal LDAR (Leak Detection and Repair) programmes "
                    "create growing exposure to EU CBAM enforcement and OGMP 2.0 compliance "
                    "obligations for export-oriented operators. Methane's 80× CO₂ potency over "
                    "20 years makes this a disproportionate driver of Kazakhstan's climate score."
                ),
            },
            {
                'title':    'Coal Power Stranded Asset Risk',
                'sector':   'Coal / Power',
                'severity': 'critical',
                'detail': (
                    "Kazakhstan's coal power fleet averages over 35 years of age and provides "
                    "over 70% of national electricity. Without a credible managed phase-out "
                    "roadmap, these assets face accelerating economic obsolescence as renewable "
                    "costs decline and carbon pricing mechanisms expand into export markets. "
                    "A JETP-style framework is needed to structure the transition and "
                    "de-risk public investment."
                ),
            },
            {
                'title':    'EU Carbon Border Adjustment Mechanism (CBAM)',
                'sector':   'Trade / Industrial',
                'severity': 'high',
                'detail': (
                    "CBAM will impose direct carbon cost exposure on Kazakh exports to EU "
                    "markets from 2026, particularly affecting energy-intensive sectors including "
                    "steel, cement, aluminium, fertilisers and hydrocarbons. Operators without "
                    "credible decarbonisation pathways will face escalating costs. Early adoption "
                    "of carbon accounting and emissions reduction programmes reduces long-term "
                    "competitiveness risk."
                ),
            },
            {
                'title':    'Water Stress in Industrial and Mining Regions',
                'sector':   'Mining / Industrial',
                'severity': 'high',
                'detail': (
                    "Industrial water use in eastern Kazakhstan — including Karaganda, East "
                    "Kazakhstan and Pavlodar — faces significant availability risk under climate "
                    "change scenarios. Tailings dam integrity, groundwater depletion and "
                    "downstream community impact are undermonitored, creating both operational "
                    "disruption risk and reputational exposure for investors."
                ),
            },
            {
                'title':    'Governance and Contract Enforcement Risk',
                'sector':   'Governance',
                'severity': 'critical',
                'detail': (
                    "Kazakhstan ranks 93rd on the Transparency International Corruption "
                    "Perceptions Index. Judicial independence concerns and weak contract "
                    "enforcement mechanisms create material project execution risk for foreign "
                    "investors in large infrastructure projects. Most DFI programmes require "
                    "enhanced contractual protections and independent oversight as a condition "
                    "of disbursement."
                ),
            },
            {
                'title':    'Just Transition Social Risk',
                'sector':   'Workforce / Social',
                'severity': 'medium',
                'detail': (
                    "An estimated 200,000+ workers in Kazakhstan's coal, oil and gas sectors "
                    "face structural employment risk from accelerated decarbonisation. Without "
                    "credible workforce transition programmes and regional economic diversification, "
                    "the energy transition risks generating significant social instability in "
                    "industrial regions — a material risk for transition finance credibility "
                    "and JETP access."
                ),
            },
        ],

        'governance_warnings': [
            {
                'title':    'Corruption Perceptions Index — Rank 93 / 180',
                'severity': 'high',
                'detail': (
                    "Kazakhstan's TI CPI rank of 93 reflects systemic procurement opacity, "
                    "limited beneficial ownership disclosure and weak anti-corruption enforcement. "
                    "Investors should expect enhanced due diligence requirements, independent "
                    "project monitoring and contractual protections as baseline requirements "
                    "for institutional participation."
                ),
            },
            {
                'title':    'Procurement Transparency Gaps',
                'severity': 'high',
                'detail': (
                    "State procurement processes do not consistently meet Open Contracting Data "
                    "Standard (OCDS) requirements. Beneficial ownership of contracting entities "
                    "is often undisclosed. Most MDB programmes require OCDS-aligned procurement "
                    "as a condition of project financing — a reform prerequisite for large-scale "
                    "DFI engagement."
                ),
            },
            {
                'title':    'Judicial Independence and Dispute Resolution',
                'severity': 'medium',
                'detail': (
                    "Foreign investors should structure projects with robust international "
                    "arbitration clauses (ICSID, ICC, UNCITRAL) and where possible, route "
                    "investments through treaties with strong investor-state dispute resolution. "
                    "The Astana International Financial Centre (AIFC) Court offers a "
                    "common-law alternative for AIFC-registered entities."
                ),
            },
            {
                'title':    'EITI Compliance — Partial',
                'severity': 'medium',
                'detail': (
                    "Kazakhstan is an EITI (Extractive Industries Transparency Initiative) "
                    "member but beneficial ownership reporting remains incomplete across the "
                    "extractive sector. Full EITI compliance — particularly beneficial ownership "
                    "disclosure — is a prerequisite for accessing several multilateral "
                    "climate and transition finance instruments."
                ),
            },
        ],
    },

    # ── Add further countries below ──────────────────────────────────────────────
    # 'uzbekistan': { 'executive_summary': '...', 'transition_risks': [...], ... },
}


def get_briefing_content(country_slug: str) -> dict:
    """Return briefing narrative content for a country slug, or {}."""
    return _CONTENT.get(country_slug, {})


def has_briefing(country_slug: str) -> bool:
    """Return True if a briefing exists for this country slug."""
    return country_slug in _CONTENT
