"""
EcoIQ Country Intelligence — Recommended Modernisation Actions.

Static structured data layer — no DB model required.
Import get_actions(slug) in views.py and pass result to template context.

Schema per action:
  title            str  — action headline
  description      str  — 1-sentence compact summary
  sector           str  — sector tag label
  impact_level     str  — 'critical' | 'high' | 'medium'
  finance_relevance str — compact finance route label (tag view)
  status           str  — badge label, normally 'Recommended'
  problem          str  — specific problem being addressed
  opportunity      str  — modernisation / investment opportunity
  stakeholders     str  — key institutions and actors
  finance_route    str  — likely instruments and structures (detailed)
  ecoiq_rationale  str  — why this matters for EcoIQ scores and DFI access

Add entries for new country slugs as needed.
Move to a DB model / admin when volume justifies it.
"""

from __future__ import annotations

_ACTIONS: dict[str, list[dict]] = {

    # ── Kazakhstan ─────────────────────────────────────────────────────────────
    'kazakhstan': [
        {
            'title':             'Reduce methane leakage in oil & gas',
            'description':       (
                'Detect and reduce methane emissions across upstream oil and gas operations '
                'through monitoring, leak detection, repair programmes and better reporting.'
            ),
            'sector':            'Oil & Gas',
            'impact_level':      'critical',
            'finance_relevance': 'Development bank + private capital',
            'status':            'Recommended',
            'problem': (
                "Kazakhstan's oil and gas sector has significant uncontrolled methane leakage "
                "with minimal independent monitoring infrastructure. Methane is over 80× more "
                "potent than CO₂ over a 20-year horizon, making unreported flaring and venting "
                "an outsized climate liability and a growing barrier to DFI access."
            ),
            'opportunity': (
                "Deploy satellite-based and ground-level leak detection across upstream operations. "
                "Mandate LDAR (Leak Detection and Repair) programmes for all major operators. "
                "Align with the World Bank Zero Routine Flaring initiative and OGMP 2.0 "
                "reporting standard to meet international disclosure thresholds."
            ),
            'stakeholders': (
                "KazMunayGas, EBRD, World Bank, IFC, Chevron, Shell (JV operators), "
                "Ministry of Energy, national environmental regulator"
            ),
            'finance_route': (
                "IFC and EBRD concessional transition loans + private operator capex obligations "
                "+ voluntary carbon credit revenue streams"
            ),
            'ecoiq_rationale': (
                "High pollution score and low methane reporting discipline suppress Kazakhstan's "
                "environmental responsibility and transparency dimensions below investment-ready "
                "thresholds. Measurable methane reduction is a direct DFI eligibility lever "
                "and improves EcoIQ climate and evidence scores."
            ),
        },
        {
            'title':             'Modernise coal power plants and district heating',
            'description':       (
                'Upgrade ageing coal power and heating infrastructure, reduce pollution '
                'intensity, improve efficiency and prepare high-emission regions for '
                'cleaner energy transition.'
            ),
            'sector':            'Coal Power / Heating',
            'impact_level':      'critical',
            'finance_relevance': 'Development bank + government',
            'status':            'Recommended',
            'problem': (
                "Over 70% of Kazakhstan's electricity comes from coal. The ageing coal fleet "
                "(average 35+ years) is highly inefficient and drives severe air pollution "
                "in industrial cities including Ekibastuz, Karaganda and Temirtau."
            ),
            'opportunity': (
                "Phased coal plant upgrades — emission controls, efficiency improvements and "
                "a managed phase-out roadmap. A JETP-style (Just Energy Transition Partnership) "
                "framework would unlock concessional finance and allow a structured "
                "coal-to-clean transition backed by international climate finance."
            ),
            'stakeholders': (
                "Samruk-Energy, AIIB, ADB, EBRD, Ministry of Energy, "
                "regional akimats, international climate finance partners"
            ),
            'finance_route': (
                "Development bank concessional loans (AIIB, ADB, EBRD) + government budget "
                "+ JETP transition finance framework + carbon-linked instruments"
            ),
            'ecoiq_rationale': (
                "Coal dependency is the single largest suppressor of Kazakhstan's transition "
                "readiness and climate scores. Decarbonising even part of the power fleet "
                "unlocks higher-tier DFI eligibility and moves the national EcoIQ index materially."
            ),
        },
        {
            'title':             'Expand solar and wind with battery storage',
            'description':       (
                'Scale utility solar, wind and battery storage to reduce fossil dependency '
                'and improve grid flexibility.'
            ),
            'sector':            'Renewable Energy',
            'impact_level':      'high',
            'finance_relevance': 'Private capital + development bank',
            'status':            'Recommended',
            'problem': (
                "Despite ranking among the top 10 globally for solar irradiance and wind "
                "resource, renewable penetration in Kazakhstan remains under 4%. Grid "
                "infrastructure is fossil-locked and auction frameworks are underdeveloped, "
                "deterring private IPP investment."
            ),
            'opportunity': (
                "Utility-scale solar in southern Kazakhstan, wind in the northern and central "
                "steppe, paired with grid-scale battery storage. Competitive auction models — "
                "proven in MENA and Central Asia — can attract private IPPs at scale and "
                "rapidly reduce fossil dependency in the power mix."
            ),
            'stakeholders': (
                "Ministry of Energy, Samruk-Energy, IFC, EBRD, ACWA Power, "
                "private IPP developers, grid operator KEGOC"
            ),
            'finance_route': (
                "IPP equity + EBRD/IFC project finance + green bond issuance "
                "+ power purchase agreements (PPAs) with sovereign credit backstop"
            ),
            'ecoiq_rationale': (
                "Low renewable share and high fossil dependency are the primary drags on "
                "Kazakhstan's energy transition score. Scaling renewables is the highest-ROI "
                "lever for EcoIQ improvement and unlocks Green Climate Fund and "
                "climate bond market eligibility."
            ),
        },
        {
            'title':             'Improve environmental monitoring around mining sites',
            'description':       (
                'Deploy stronger monitoring of air, water, soil and tailings risks around '
                'mining and industrial hotspots.'
            ),
            'sector':            'Mining',
            'impact_level':      'high',
            'finance_relevance': 'Government + development bank',
            'status':            'Recommended',
            'problem': (
                "Kazakhstan's major mining regions — Karaganda, Pavlodar, East Kazakhstan — "
                "show significant gaps in independent air quality, water contamination and "
                "tailings monitoring. Community health impacts are underreported and "
                "data is not publicly accessible in a standardised form."
            ),
            'opportunity': (
                "Establish a national environmental monitoring network with independent data "
                "publication, satellite integration and community access portals. Align with "
                "IFC Performance Standards and Equator Principles disclosure requirements "
                "to meet the baseline needed for DFI co-financing on mining projects."
            ),
            'stakeholders': (
                "Ministry of Ecology, KazMinerals, Eurasian Resources Group (ERG), "
                "regional environmental NGOs, World Bank, affected communities"
            ),
            'finance_route': (
                "Government budget + World Bank / GCF development grants "
                "+ mining company compliance capex (regulatory requirement)"
            ),
            'ecoiq_rationale': (
                "Low evidence completeness and transparency scores directly reflect inadequate "
                "environmental public disclosure. Monitoring infrastructure is a prerequisite "
                "for DFI-backed mining projects and is required for IFC and EBRD co-financing eligibility."
            ),
        },
        {
            'title':             'Develop critical minerals processing with clean energy',
            'description':       (
                'Move beyond raw extraction by developing cleaner processing capacity for '
                'lithium, cobalt, copper and rare earths using low-carbon power.'
            ),
            'sector':            'Critical Minerals',
            'impact_level':      'high',
            'finance_relevance': 'Private capital + blended finance',
            'status':            'Recommended',
            'problem': (
                "Kazakhstan exports significant volumes of raw ore — lithium, cobalt, copper, "
                "rare earths — with minimal domestic processing. The country misses substantial "
                "value-chain opportunity and the high-quality DFI investment that follows "
                "processed and refined critical mineral supply chains."
            ),
            'opportunity': (
                "Develop processing facilities in SEZs powered by renewable energy, targeting "
                "EU Critical Raw Materials Act demand and US IRA-aligned supply chains. "
                "Position Kazakhstan as a strategic clean-energy minerals supplier to "
                "Europe and East Asia, commanding premium FDI."
            ),
            'stakeholders': (
                "Ministry of Industry, KazMinerals, ERG, EU Commission, "
                "US DFC, private strategic investors, AIIB"
            ),
            'finance_route': (
                "Strategic FDI + AIIB project finance + blended finance structures "
                "+ EU/US bilateral partnership programmes + export credit agencies"
            ),
            'ecoiq_rationale': (
                "Moving from raw extraction to high-value processing significantly improves "
                "industrial modernisation and national value scores — unlocking premium "
                "institutional capital and advancing Kazakhstan into the investment-ready tier."
            ),
        },
        {
            'title':             'Strengthen anti-corruption and procurement transparency',
            'description':       (
                'Improve procurement transparency, contract disclosure, beneficial ownership '
                'checks and independent project oversight to reduce governance risk.'
            ),
            'sector':            'Governance',
            'impact_level':      'critical',
            'finance_relevance': 'Development bank + government',
            'status':            'Recommended',
            'problem': (
                "Kazakhstan ranks 93rd on Transparency International's Corruption Perceptions "
                "Index. State procurement lacks beneficial ownership disclosure. Foreign "
                "investors consistently cite governance risk as a top investment barrier, "
                "raising the cost of capital and reducing DFI appetite."
            ),
            'opportunity': (
                "Adopt the Open Contracting Data Standard (OCDS) for public procurement. "
                "Implement a beneficial ownership registry. Strengthen independent judicial "
                "oversight of infrastructure contracts. Align with the EITI "
                "(Extractive Industries Transparency Initiative) reporting framework."
            ),
            'stakeholders': (
                "Agency for Anti-Corruption, EBRD, World Bank governance programmes, "
                "Transparency International, civil society organisations, EITI secretariat"
            ),
            'finance_route': (
                "World Bank and EBRD governance reform loans + domestic budget allocation "
                "+ technical assistance grants from bilateral donors"
            ),
            'ecoiq_rationale': (
                "Transparency and governance scores are the primary constraints on "
                "Kazakhstan's investment readiness tier. Even incremental improvement unlocks "
                "MDB eligibility thresholds and meaningfully shifts the national EcoIQ index."
            ),
        },
        {
            'title':             'Create green industrial zones',
            'description':       (
                'Develop industrial zones powered by cleaner energy, efficient infrastructure '
                'and circular economy principles to attract manufacturing and '
                'export-oriented investment.'
            ),
            'sector':            'Industrial Policy',
            'impact_level':      'high',
            'finance_relevance': 'Government + private capital',
            'status':            'Recommended',
            'problem': (
                "Kazakhstan's existing special economic zones (SEZs) are largely fossil-powered "
                "and lack environmental performance standards. They attract conventional "
                "manufacturing rather than clean technology investment and ESG-aligned "
                "supply chains that command premium FDI."
            ),
            'opportunity': (
                "Designate 2–3 existing SEZs as certified green industrial zones. Mandate "
                "clean energy supply, circular economy standards and ESG disclosure frameworks "
                "aligned with EU taxonomy — creating a premium proposition for "
                "manufacturing FDI targeting European and Asian export markets."
            ),
            'stakeholders': (
                "Ministry of Industry, Astana International Financial Centre (AIFC), "
                "AIIB, IFC, EU trade partnership programmes, strategic FDI investors"
            ),
            'finance_route': (
                "Government infrastructure investment + AIIB/IFC co-financing "
                "+ strategic FDI attraction + green bond financing for zone infrastructure"
            ),
            'ecoiq_rationale': (
                "Green zone designation directly improves industrial modernisation and "
                "policy environment scores, creating compounding EcoIQ improvement and "
                "signalling to capital markets that Kazakhstan is transition-serious."
            ),
        },
        {
            'title':             'Support worker reskilling in fossil-fuel regions',
            'description':       (
                'Build reskilling programmes for workers in coal, oil, gas and heavy industry '
                'regions to support a just transition.'
            ),
            'sector':            'Workforce / Just Transition',
            'impact_level':      'medium',
            'finance_relevance': 'Development bank + government',
            'status':            'Recommended',
            'problem': (
                "An estimated 200,000+ workers in Kazakhstan's coal, oil and gas sectors "
                "face structural employment risk from the energy transition. Without dedicated "
                "workforce transition programmes, decarbonisation risks creating significant "
                "social instability in Karaganda, Ekibastuz and Pavlodar regions."
            ),
            'opportunity': (
                "Establish regional just transition centres offering reskilling for renewable "
                "energy operations, industrial maintenance, digital manufacturing and green "
                "construction. Align with ILO Just Transition Guidelines and access "
                "JETP workforce finance components."
            ),
            'stakeholders': (
                "Ministry of Labour, ILO, ADB, regional akimats, "
                "coal and energy companies, vocational training institutions"
            ),
            'finance_route': (
                "ADB and World Bank workforce development loans + government social budget "
                "+ energy company transition fund contributions"
            ),
            'ecoiq_rationale': (
                "Workforce transition planning is a key indicator in the social dimension of "
                "EcoIQ scoring and a specific eligibility criterion for JETP and just "
                "transition finance instruments. Its absence suppresses governance and "
                "social scores and limits access to blended finance."
            ),
        },
    ],

    # ── Add further countries below ────────────────────────────────────────────
    # 'uzbekistan': [ ... ],
    # 'mongolia':   [ ... ],
}


def get_actions(country_slug: str) -> list[dict]:
    """Return the modernisation action list for a country slug, or []."""
    return _ACTIONS.get(country_slug, [])
