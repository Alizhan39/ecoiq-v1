"""
EcoIQ Country Intelligence — National Transition Roadmap Static Data.

Staged pathway showing how a country could improve its EcoIQ score toward 100.
Framed as indicative AI-assisted strategic guidance — not government policy,
not investment advice, not a verified implementation plan.

Each phase schema:
  phase       int          — sequential number (1-based)
  title       str          — short phase name
  timeline    str          — human-readable duration
  uplift_low  int          — estimated minimum score uplift
  uplift_high int          — estimated maximum score uplift
  actions     list[str]    — 3-5 concrete actions
  sectors     list[str]    — relevant sectors
  finance_route str        — indicative finance mechanism
  evidence    str          — evidence / due diligence note

summary_card dict:
  text        str          — summary note on total potential uplift
  disclaimer  str          — mandatory disclaimer text
"""

from __future__ import annotations

_ROADMAPS: dict[str, dict] = {

    'kazakhstan': {

        'phases': [
            {
                'phase': 1,
                'title': 'Stabilise Transparency and Baseline Data',
                'timeline': '0–6 months',
                'uplift_low': 8,
                'uplift_high': 12,
                'actions': [
                    'Publish clearer industrial emissions baselines',
                    'Improve procurement transparency and open contracting',
                    'Disclose major industrial environmental risks',
                    'Verify and standardise company-level climate data reporting',
                ],
                'sectors': ['Governance', 'Data Infrastructure', 'Heavy Industry'],
                'finance_route': 'Government budget + development bank technical assistance',
                'evidence': (
                    'Requires independent audit of disclosure frameworks, EITI reporting '
                    'completeness, and OCDS procurement alignment before score uplift can '
                    'be verified.'
                ),
            },
            {
                'phase': 2,
                'title': 'Reduce Methane and Industrial Leakage',
                'timeline': '6–18 months',
                'uplift_low': 10,
                'uplift_high': 15,
                'actions': [
                    'Deploy methane leak detection and repair (LDAR) programmes',
                    'Install continuous monitoring in active oil and gas fields',
                    'Adopt stronger environmental reporting standards for operators',
                    'Engage independent third-party verification of emission reductions',
                ],
                'sectors': ['Oil & Gas'],
                'finance_route': 'Private capital + development bank climate finance (EBRD, IFC)',
                'evidence': (
                    'Requires satellite or ground-based methane monitoring data, operator '
                    'disclosures under OGMP 2.0, and independent verification before '
                    'emissions-linked score improvements are recognised.'
                ),
            },
            {
                'phase': 3,
                'title': 'Modernise Coal Power and District Heating',
                'timeline': '1–4 years',
                'uplift_low': 12,
                'uplift_high': 18,
                'actions': [
                    'Upgrade or decommission ageing coal power units (35+ year fleet)',
                    'Improve district heating efficiency and switch to cleaner fuels',
                    'Reduce PM2.5, SO₂ and NOx emissions from power and heat sectors',
                    'Develop a managed coal region transition plan with community support',
                ],
                'sectors': ['Coal Power', 'District Heating', 'Air Quality'],
                'finance_route': 'Development bank + government + blended finance (JETP-type)',
                'evidence': (
                    'Requires verified retirement timelines, air quality monitoring data, '
                    'independent energy audit of heating systems, and credible just '
                    'transition plans for affected workforces.'
                ),
            },
            {
                'phase': 4,
                'title': 'Scale Renewables, Storage and Grid Flexibility',
                'timeline': '2–6 years',
                'uplift_low': 10,
                'uplift_high': 16,
                'actions': [
                    'Expand utility-scale solar and wind capacity significantly',
                    'Invest in battery storage and grid balancing infrastructure',
                    'Modernise transmission and distribution infrastructure',
                    'Improve renewable energy integration and curtailment management',
                ],
                'sectors': ['Renewable Energy', 'Grid Infrastructure', 'Energy Storage'],
                'finance_route': 'Private capital + development bank (ADB, AIIB, EBRD)',
                'evidence': (
                    'Requires verified capacity additions, grid stability data, independent '
                    'power purchase agreement audits, and renewable generation tracking '
                    'before score uplift is recognised.'
                ),
            },
            {
                'phase': 5,
                'title': 'Build Clean Industrial Growth Engines',
                'timeline': '3–8 years',
                'uplift_low': 10,
                'uplift_high': 14,
                'actions': [
                    'Develop clean critical minerals processing and refining capacity',
                    'Establish green industrial economic zones',
                    'Build circular economy and waste reduction infrastructure',
                    'Attract cleaner, export-oriented manufacturing investment',
                ],
                'sectors': ['Critical Minerals', 'Industrial Policy', 'Manufacturing'],
                'finance_route': 'Private capital + blended finance + sovereign co-investment',
                'evidence': (
                    'Requires feasibility studies for industrial zones, lifecycle emissions '
                    'assessments for minerals processing, and independent verification of '
                    'clean production standards before score recognition.'
                ),
            },
            {
                'phase': 6,
                'title': 'Institutionalise Long-Term Stewardship',
                'timeline': '5–10 years',
                'uplift_low': 12,
                'uplift_high': 20,
                'actions': [
                    'Establish independent impact verification and reporting bodies',
                    'Embed anti-corruption safeguards across public investment channels',
                    'Launch worker reskilling and just transition programmes at scale',
                    'Require public benefit reporting from major industrial operators',
                    'Build long-term transition governance into national policy frameworks',
                ],
                'sectors': ['Governance', 'Workforce Development', 'Public Benefit'],
                'finance_route': 'Government + DFIs + sovereign wealth and pension funds',
                'evidence': (
                    'Requires independent governance assessments, workforce transition '
                    'outcome data, beneficial ownership registry completion, and multi-year '
                    'public reporting before long-term score improvements are consolidated.'
                ),
            },
        ],

        'summary_card': {
            'text': (
                'Estimated potential EcoIQ improvement: from 29.8 toward 80–90+ over a staged '
                'transition pathway, subject to verified implementation, governance reform and '
                'measurable impact.'
            ),
            'disclaimer': (
                'This roadmap is AI-assisted and indicative only. It does not represent official '
                'policy, financial advice or verified project feasibility. Implementation requires '
                'technical studies, stakeholder consultation, financing due diligence and '
                'independent verification.'
            ),
        },
    },

    # ── Add further countries below ──────────────────────────────────────────────
    # 'germany': { 'phases': [...], 'summary_card': {...} },
}


def get_roadmap(country_slug: str) -> dict:
    """Return roadmap data for a country slug, or {}."""
    return _ROADMAPS.get(country_slug, {})


def has_roadmap(country_slug: str) -> bool:
    """Return True if a roadmap exists for this country slug."""
    return country_slug in _ROADMAPS
