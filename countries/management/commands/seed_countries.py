"""
management command: seed_countries

Seeds 10 country intelligence profiles — UK, USA, Germany, France,
South Korea, China, Saudi Arabia, Kazakhstan, UAE, Denmark.

Safe to re-run: uses update_or_create (idempotent).

Usage:
    python manage.py seed_countries
"""
from django.core.management.base import BaseCommand
from countries.models import CountryProfile

AI_DISCLAIMER = (
    "EcoIQ AI-generated analysis based on publicly available data. "
    "Not independently verified. For indicative intelligence purposes only."
)


COUNTRIES = [

    # ── United Kingdom ──────────────────────────────────────────────────────────
    {
        'name': 'United Kingdom',
        'iso_code': 'GB',
        'flag_emoji': '🇬🇧',
        'region': 'western_europe',
        'is_published': True,
        'featured': True,
        'national_ecoiq_index': 62.4,
        'transition_readiness_score': 70.0,
        'policy_environment_score': 72.0,
        'investment_climate_score': 74.0,
        'transparency_score': 78.0,
        'industrial_modernization_score': 65.0,
        'transition_readiness_label': 'advancing',
        'gdp_usd': 3_100_000_000_000,
        'industrial_gdp_share': 18.5,
        'co2_megatonnes': 340.0,
        'renewable_energy_share': 43.0,
        'fossil_fuel_dependency': 79.0,
        'companies_tracked': 4,
        'estimated_transition_gap_usd': 28_000_000_000,
        'green_finance_available_usd': 15_000_000_000,
        'ai_overview': (
            f"{AI_DISCLAIMER}\n\n"
            "The United Kingdom is one of the world's leading advanced economies, "
            "with a strong financial services sector centred in London and a legacy "
            "industrial base undergoing structured transition. The country has committed "
            "to net zero by 2050 and has significantly expanded offshore wind capacity, "
            "making it a benchmark market for renewable energy investment.\n\n"
            "EcoIQ tracks four major UK-domiciled companies in its global dataset: "
            "BP, Shell, Unilever, and Maersk (European operations). BP and Shell remain "
            "challenged on environmental stewardship but both have articulated accelerating "
            "transition strategies. Unilever leads on public benefit and transparency. "
            "The UK's strong regulatory environment and Transition Finance Market Review "
            "position it as a significant destination for ethical investment capital.\n\n"
            "Key risks include the pace of North Sea phase-down, energy security pressures "
            "from the Ukraine conflict, and political continuity on climate commitments."
        ),
        'ai_transition_narrative': (
            f"{AI_DISCLAIMER}\n\n"
            "The UK's industrial transition story is defined by three major forces: "
            "the rapid expansion of offshore wind (now the world's largest installed capacity), "
            "the managed decline of North Sea oil and gas, and the emergence of green finance "
            "as a London specialisation. The Inflation Reduction Act competitor dynamic with "
            "the US has prompted increased domestic clean tech incentives. "
            "Carbon capture and hydrogen infrastructure remain underfunded relative to ambition. "
            "The UK's transition readiness score of 70 reflects genuine progress tempered by "
            "fossil fuel dependency that still exceeds 79% of total energy consumption."
        ),
        'ai_risk_summary': (
            f"{AI_DISCLAIMER}\n\n"
            "Primary risks: (1) Energy security pressures incentivising continued North Sea "
            "production beyond climate targets; (2) Post-Brexit trade frictions reducing "
            "access to EU green finance frameworks; (3) Planning system bottlenecks delaying "
            "onshore wind and solar deployment; (4) Stranded asset exposure in financial "
            "sector from fossil fuel lending portfolios."
        ),
        'ai_investment_thesis': (
            f"{AI_DISCLAIMER}\n\n"
            "The UK presents a strong investment thesis for offshore wind, green hydrogen, "
            "industrial decarbonisation finance, and sustainable infrastructure. London's "
            "financial ecosystem — including the London Stock Exchange's sustainability "
            "segment and the UK Green Finance Institute — provides institutional depth. "
            "Key opportunities: North Sea transition finance, EV charging infrastructure, "
            "energy efficiency in commercial real estate."
        ),
        'industrial_sectors': [
            {'name': 'Oil & Gas', 'ecoiq_score': 34.0, 'pollution_level': 'high', 'transition_status': 'transitioning'},
            {'name': 'Financial Services', 'ecoiq_score': 55.0, 'pollution_level': 'low', 'transition_status': 'advancing'},
            {'name': 'Consumer Goods', 'ecoiq_score': 68.0, 'pollution_level': 'medium', 'transition_status': 'advancing'},
            {'name': 'Offshore Wind', 'ecoiq_score': 82.0, 'pollution_level': 'low', 'transition_status': 'leading'},
            {'name': 'Manufacturing', 'ecoiq_score': 48.0, 'pollution_level': 'medium', 'transition_status': 'developing'},
        ],
        'pollution_hotspots': [
            {'name': 'North Sea Oil Platforms', 'description': 'Ongoing upstream extraction with methane flaring', 'severity': 'high'},
            {'name': 'South Yorkshire Steel Belt', 'description': 'Legacy steel manufacturing with high particulate emissions', 'severity': 'medium'},
        ],
        'financing_gaps': [
            {'sector': 'Offshore Wind Transmission', 'gap_usd': 8_000_000_000, 'opportunity': 'Grid connection infrastructure for new wind farms'},
            {'sector': 'Industrial Decarbonisation', 'gap_usd': 12_000_000_000, 'opportunity': 'CCS and hydrogen for heavy industry'},
            {'sector': 'EV Infrastructure', 'gap_usd': 4_000_000_000, 'opportunity': 'Nationwide charging network expansion'},
        ],
        'policy_highlights': [
            {'title': 'Net Zero 2050 Commitment', 'description': 'Legally binding target to reach net zero greenhouse gas emissions', 'year': 2019, 'status': 'active'},
            {'title': 'Contracts for Difference', 'description': 'Auction mechanism supporting offshore wind at scale', 'year': 2014, 'status': 'active'},
            {'title': 'North Sea Transition Deal', 'description': 'Managed transition framework for North Sea operators', 'year': 2021, 'status': 'active'},
        ],
    },

    # ── United States ───────────────────────────────────────────────────────────
    {
        'name': 'United States',
        'iso_code': 'US',
        'flag_emoji': '🇺🇸',
        'region': 'north_america',
        'is_published': True,
        'featured': True,
        'national_ecoiq_index': 58.3,
        'transition_readiness_score': 66.0,
        'policy_environment_score': 61.0,
        'investment_climate_score': 80.0,
        'transparency_score': 72.0,
        'industrial_modernization_score': 70.0,
        'transition_readiness_label': 'advancing',
        'gdp_usd': 27_360_000_000_000,
        'industrial_gdp_share': 17.4,
        'co2_megatonnes': 4_897.0,
        'renewable_energy_share': 22.0,
        'fossil_fuel_dependency': 81.0,
        'companies_tracked': 10,
        'estimated_transition_gap_usd': 320_000_000_000,
        'green_finance_available_usd': 180_000_000_000,
        'ai_overview': (
            f"{AI_DISCLAIMER}\n\n"
            "The United States is the world's largest economy and home to the greatest "
            "concentration of EcoIQ-tracked companies, including Apple, Microsoft, Alphabet, "
            "Amazon, Tesla, ExxonMobil, Walmart, JPMorgan Chase, BlackRock, and NVIDIA. "
            "The US presents a bifurcated ethical performance landscape: technology companies "
            "in the 70-80 EcoIQ band sit alongside oil majors with scores in the 30-40 range.\n\n"
            "The Inflation Reduction Act (2022) represents the largest clean energy investment "
            "in US history, unlocking an estimated $369bn in tax credits and driving rapid "
            "expansion of solar, wind, battery storage, and EV manufacturing. "
            "However, the US remains the second-largest absolute emitter globally, "
            "with fossil fuel dependency above 80% and significant regulatory uncertainty "
            "across political cycles.\n\n"
            "Investment climate score (80) reflects unparalleled capital market depth, "
            "but policy instability constrains the effective transition readiness score."
        ),
        'ai_transition_narrative': (
            f"{AI_DISCLAIMER}\n\n"
            "The US transition story is defined by private sector leadership — Tesla, "
            "Microsoft, and Apple have made credible transition commitments that go beyond "
            "regulatory requirements. The IRA has unlocked a manufacturing renaissance in "
            "clean energy components. However, ExxonMobil and other oil majors continue to "
            "expand upstream capacity, creating a structural contradiction in the national "
            "transition narrative. The SEC's climate disclosure rule (pending implementation) "
            "will significantly increase transparency for listed companies."
        ),
        'ai_risk_summary': (
            f"{AI_DISCLAIMER}\n\n"
            "Primary risks: (1) Political cycle risk — IRA incentives face legislative "
            "vulnerability; (2) Methane regulation rollback potential; (3) Grid infrastructure "
            "inadequacy for accelerated renewable deployment; (4) Financial sector exposure to "
            "fossil fuel lending (JPMorgan Chase is world's largest fossil fuel financier); "
            "(5) Wealth extraction dynamics in tech sector reducing public benefit scores."
        ),
        'ai_investment_thesis': (
            f"{AI_DISCLAIMER}\n\n"
            "Priority investment themes: AI infrastructure (NVIDIA, data centres), "
            "clean manufacturing (IRA-incentivised battery gigafactories), "
            "distributed energy resources, carbon capture at industrial scale. "
            "The US offers unparalleled deal flow and exit optionality but requires "
            "careful political risk management for long-duration transition assets."
        ),
        'industrial_sectors': [
            {'name': 'Technology', 'ecoiq_score': 77.0, 'pollution_level': 'medium', 'transition_status': 'leading'},
            {'name': 'Oil & Gas', 'ecoiq_score': 32.0, 'pollution_level': 'high', 'transition_status': 'lagging'},
            {'name': 'Finance', 'ecoiq_score': 52.0, 'pollution_level': 'low', 'transition_status': 'developing'},
            {'name': 'Retail', 'ecoiq_score': 45.0, 'pollution_level': 'medium', 'transition_status': 'developing'},
            {'name': 'Semiconductors', 'ecoiq_score': 71.0, 'pollution_level': 'medium', 'transition_status': 'advancing'},
            {'name': 'EV / Clean Energy', 'ecoiq_score': 79.0, 'pollution_level': 'low', 'transition_status': 'leading'},
        ],
        'pollution_hotspots': [
            {'name': 'Permian Basin (Texas / New Mexico)', 'description': 'World\'s largest oil field; significant methane flaring and fugitive emissions', 'severity': 'severe'},
            {'name': 'Gulf Coast Petrochemical Corridor', 'description': 'High-density refinery and chemical plant cluster with toxic air emissions', 'severity': 'severe'},
            {'name': 'Appalachian Coal Country', 'description': 'Legacy coal mining with groundwater contamination and land subsidence', 'severity': 'high'},
        ],
        'financing_gaps': [
            {'sector': 'Grid Modernization', 'gap_usd': 100_000_000_000, 'opportunity': 'Transmission infrastructure for renewable integration'},
            {'sector': 'Industrial Decarbonisation', 'gap_usd': 80_000_000_000, 'opportunity': 'Steel, cement, chemicals transition'},
            {'sector': 'Affordable Housing / Clean Energy', 'gap_usd': 60_000_000_000, 'opportunity': 'Low-income community clean energy access'},
        ],
        'policy_highlights': [
            {'title': 'Inflation Reduction Act', 'description': '$369bn in clean energy tax credits and incentives', 'year': 2022, 'status': 'active'},
            {'title': 'SEC Climate Disclosure Rule', 'description': 'Mandatory climate-related disclosures for listed companies', 'year': 2024, 'status': 'pending'},
            {'title': 'Infrastructure Investment & Jobs Act', 'description': '$1.2tn infrastructure investment including $65bn for clean energy grid', 'year': 2021, 'status': 'active'},
        ],
    },

    # ── Germany ─────────────────────────────────────────────────────────────────
    {
        'name': 'Germany',
        'iso_code': 'DE',
        'flag_emoji': '🇩🇪',
        'region': 'western_europe',
        'is_published': True,
        'featured': True,
        'national_ecoiq_index': 67.8,
        'transition_readiness_score': 74.0,
        'policy_environment_score': 76.0,
        'investment_climate_score': 73.0,
        'transparency_score': 80.0,
        'industrial_modernization_score': 72.0,
        'transition_readiness_label': 'advancing',
        'gdp_usd': 4_460_000_000_000,
        'industrial_gdp_share': 26.4,
        'co2_megatonnes': 649.0,
        'renewable_energy_share': 52.0,
        'fossil_fuel_dependency': 74.0,
        'companies_tracked': 2,
        'estimated_transition_gap_usd': 38_000_000_000,
        'green_finance_available_usd': 22_000_000_000,
        'ai_overview': (
            f"{AI_DISCLAIMER}\n\n"
            "Germany is Europe's largest economy and one of the world's most significant "
            "industrial transition stories. The Energiewende (energy transition) remains the "
            "most ambitious industrial transformation in any major economy, targeting 80% "
            "renewable electricity by 2030 and carbon neutrality by 2045. Germany hosts "
            "EcoIQ's highest-scoring industrial company — Siemens (EcoIQ 74.2) — and is a "
            "key manufacturing hub for Schneider Electric's European operations.\n\n"
            "Germany's industrial base is deeply integrated with the global supply chain, "
            "making its transition particularly consequential for automotive, machinery, "
            "and chemical sectors worldwide. The shutdown of nuclear energy (completed 2023) "
            "has increased short-term fossil dependence but accelerated renewable deployment urgency."
        ),
        'ai_transition_narrative': (
            f"{AI_DISCLAIMER}\n\n"
            "Siemens represents the German industrial transition archetype: a legacy engineering "
            "conglomerate converting to digital infrastructure, energy management, and clean "
            "manufacturing. The German automotive sector — Volkswagen, BMW, Mercedes — is "
            "undergoing the most significant transformation in its history, pivoting to EV "
            "platforms under intense competitive pressure from BYD and CATL. "
            "Germany's hydrogen strategy (National Hydrogen Strategy 2020) aims to make the "
            "country a leading green hydrogen producer and importer, with North Africa and "
            "Australia identified as supply corridor partners."
        ),
        'ai_risk_summary': (
            f"{AI_DISCLAIMER}\n\n"
            "Primary risks: (1) Energy cost competitiveness — high electricity prices threaten "
            "industrial relocation (Deindustrialisierung debate); (2) Gas dependency from "
            "Russia disruption requiring rapid LNG substitution; (3) Automotive sector "
            "transition risk as EV pivot creates significant employment disruption; "
            "(4) Slow permitting processes delaying wind and solar buildout."
        ),
        'ai_investment_thesis': (
            f"{AI_DISCLAIMER}\n\n"
            "Germany offers deep industrial expertise, strong institutional frameworks, "
            "and significant green bond market depth. Priority opportunities: "
            "industrial electrification, hydrogen infrastructure, building efficiency retrofits, "
            "and advanced manufacturing automation. KfW's green finance capacity provides "
            "significant public co-investment potential."
        ),
        'industrial_sectors': [
            {'name': 'Engineering / Automation', 'ecoiq_score': 74.0, 'pollution_level': 'low', 'transition_status': 'leading'},
            {'name': 'Automotive', 'ecoiq_score': 55.0, 'pollution_level': 'medium', 'transition_status': 'advancing'},
            {'name': 'Chemicals', 'ecoiq_score': 46.0, 'pollution_level': 'high', 'transition_status': 'developing'},
            {'name': 'Energy / Utilities', 'ecoiq_score': 62.0, 'pollution_level': 'medium', 'transition_status': 'advancing'},
        ],
        'pollution_hotspots': [
            {'name': 'Rhineland Lignite Mining', 'description': 'Largest lignite coal mining district in Europe — significant CO₂ and land impact', 'severity': 'severe'},
            {'name': 'Ruhr Industrial Valley', 'description': 'Legacy steel and chemical manufacturing; ongoing modernisation', 'severity': 'medium'},
        ],
        'financing_gaps': [
            {'sector': 'Green Hydrogen Infrastructure', 'gap_usd': 15_000_000_000, 'opportunity': 'Electrolyser capacity and pipeline buildout'},
            {'sector': 'Building Retrofits', 'gap_usd': 18_000_000_000, 'opportunity': '35m buildings requiring energy efficiency upgrades'},
            {'sector': 'Industrial Electrification', 'gap_usd': 12_000_000_000, 'opportunity': 'Industrial heat and process electrification'},
        ],
        'policy_highlights': [
            {'title': 'Energiewende 2.0', 'description': '80% renewable electricity by 2030, carbon neutral by 2045', 'year': 2023, 'status': 'active'},
            {'title': 'National Hydrogen Strategy', 'description': '10 GW domestic electrolysis capacity by 2030', 'year': 2020, 'status': 'active'},
            {'title': 'Climate Action Programme', 'description': '€100bn Climate Action Fund for low-carbon investment', 'year': 2023, 'status': 'active'},
        ],
    },

    # ── France ──────────────────────────────────────────────────────────────────
    {
        'name': 'France',
        'iso_code': 'FR',
        'flag_emoji': '🇫🇷',
        'region': 'western_europe',
        'is_published': True,
        'featured': False,
        'national_ecoiq_index': 65.2,
        'transition_readiness_score': 72.0,
        'policy_environment_score': 74.0,
        'investment_climate_score': 71.0,
        'transparency_score': 76.0,
        'industrial_modernization_score': 68.0,
        'transition_readiness_label': 'advancing',
        'gdp_usd': 3_030_000_000_000,
        'industrial_gdp_share': 16.8,
        'co2_megatonnes': 288.0,
        'renewable_energy_share': 26.0,
        'fossil_fuel_dependency': 52.0,
        'companies_tracked': 2,
        'estimated_transition_gap_usd': 22_000_000_000,
        'green_finance_available_usd': 14_000_000_000,
        'ai_overview': (
            f"{AI_DISCLAIMER}\n\n"
            "France hosts two of EcoIQ's most strategically important tracked companies: "
            "EDF (Électricité de France), the world's largest nuclear power operator, "
            "and Schneider Electric, globally recognised as a leader in energy management "
            "and industrial automation. Together they represent the dual French energy "
            "transition model: low-carbon baseload from nuclear combined with smart "
            "energy management at the industrial and building level.\n\n"
            "France's fossil fuel dependency (52%) is notably lower than most large "
            "economies due to nuclear's 70% share of electricity generation. "
            "The country's transition strategy balances nuclear renaissance (EPR2 programme) "
            "with accelerating renewable deployment under the Loi Energie-Climat."
        ),
        'ai_transition_narrative': (
            f"{AI_DISCLAIMER}\n\n"
            "EDF represents the nuclear-as-transition-technology thesis: very low operational "
            "emissions, energy security, and baseload reliability, but high capital cost and "
            "waste management complexity. Schneider Electric represents the efficiency and "
            "electrification pathway: helping industrial customers reduce energy consumption "
            "through digital monitoring, automation, and smart grid integration. "
            "France's EV adoption rate is among Europe's highest, and the country is "
            "targeting gigafactory capacity for battery production (Douai, Dunkirk)."
        ),
        'ai_risk_summary': (
            f"{AI_DISCLAIMER}\n\n"
            "Primary risks: (1) Nuclear ageing fleet — extended lifetime operation of "
            "40-year-old reactors introduces safety and cost uncertainty; (2) EDF's debt "
            "burden following renationalisation; (3) Industrial competitiveness under "
            "high energy cost environment; (4) Social cohesion risks from rapid transition "
            "(gilets jaunes precedent)."
        ),
        'ai_investment_thesis': (
            f"{AI_DISCLAIMER}\n\n"
            "France offers a distinctive investment thesis anchored in nuclear baseload "
            "security and industrial electrification leadership. Priority opportunities: "
            "EV manufacturing supply chain, building retrofit finance, smart grid "
            "technology, and energy efficiency-as-a-service models following Schneider's "
            "EcoStruxure platform success."
        ),
        'industrial_sectors': [
            {'name': 'Nuclear / Energy', 'ecoiq_score': 68.0, 'pollution_level': 'low', 'transition_status': 'advancing'},
            {'name': 'Energy Management', 'ecoiq_score': 80.0, 'pollution_level': 'low', 'transition_status': 'leading'},
            {'name': 'Aerospace / Defence', 'ecoiq_score': 52.0, 'pollution_level': 'medium', 'transition_status': 'developing'},
            {'name': 'Automotive', 'ecoiq_score': 58.0, 'pollution_level': 'medium', 'transition_status': 'advancing'},
        ],
        'pollution_hotspots': [
            {'name': 'Nuclear Waste Storage Sites', 'description': 'Long-term radioactive waste management — Cigéo deep geological repository under development', 'severity': 'medium'},
            {'name': 'Fos-sur-Mer Industrial Zone', 'description': 'Steel, chemicals, and refinery cluster near Marseille', 'severity': 'medium'},
        ],
        'financing_gaps': [
            {'sector': 'Nuclear EPR2 Programme', 'gap_usd': 65_000_000_000, 'opportunity': 'New nuclear fleet financing over 2025-2045'},
            {'sector': 'Building Renovation', 'gap_usd': 16_000_000_000, 'opportunity': 'MaPrimeRénov programme scale-up'},
        ],
        'policy_highlights': [
            {'title': 'Loi Energie-Climat', 'description': 'Carbon neutrality by 2050, 40% renewable electricity by 2030', 'year': 2019, 'status': 'active'},
            {'title': 'Relance Industrielle Verte', 'description': '€1bn green industrial acceleration fund', 'year': 2023, 'status': 'active'},
        ],
    },

    # ── South Korea ─────────────────────────────────────────────────────────────
    {
        'name': 'South Korea',
        'iso_code': 'KR',
        'flag_emoji': '🇰🇷',
        'region': 'east_asia',
        'is_published': True,
        'featured': False,
        'national_ecoiq_index': 56.8,
        'transition_readiness_score': 62.0,
        'policy_environment_score': 64.0,
        'investment_climate_score': 68.0,
        'transparency_score': 70.0,
        'industrial_modernization_score': 74.0,
        'transition_readiness_label': 'developing',
        'gdp_usd': 1_710_000_000_000,
        'industrial_gdp_share': 32.6,
        'co2_megatonnes': 592.0,
        'renewable_energy_share': 9.0,
        'fossil_fuel_dependency': 83.0,
        'companies_tracked': 1,
        'estimated_transition_gap_usd': 45_000_000_000,
        'green_finance_available_usd': 12_000_000_000,
        'ai_overview': (
            f"{AI_DISCLAIMER}\n\n"
            "South Korea is one of the world's most industrially intensive economies, "
            "with EcoIQ tracking Samsung Electronics as its primary representative. "
            "The country is among the top 10 absolute CO₂ emitters globally and maintains "
            "one of the highest fossil fuel dependencies (83%) of any advanced economy, "
            "driven by heavy industry, steel, chemicals, and electronics manufacturing.\n\n"
            "Samsung's EcoIQ score (64.0) reflects genuine progress on transparency, "
            "supply chain responsibility, and semiconductor energy efficiency, "
            "partially offset by the pollution intensity of chip fabrication processes. "
            "South Korea's K-ETS carbon market (est. 2015) is Asia's oldest ETS, "
            "though coverage and ambition remain below EU standards."
        ),
        'ai_transition_narrative': (
            f"{AI_DISCLAIMER}\n\n"
            "South Korea's transition narrative is centred on technology-led decarbonisation. "
            "The country is the world's leading manufacturer of EV batteries (through Samsung "
            "SDI, LG Energy Solution, SK On) and is the technology backbone of the global "
            "clean energy supply chain. The tension lies between being the manufacturer of "
            "transition technologies globally while remaining dependent on coal and LNG "
            "domestically. The 2023 National Carbon Neutrality Plan targets 40% emissions "
            "reduction by 2030 — ambitious but requiring dramatic policy implementation."
        ),
        'ai_risk_summary': (
            f"{AI_DISCLAIMER}\n\n"
            "Primary risks: (1) Coal phase-out delayed — government still approving new coal "
            "plants while committing to neutrality; (2) Chaebol governance concerns — "
            "Samsung, Hyundai concentration creates systemic risk; (3) Water scarcity "
            "threatening semiconductor manufacturing (chip fabs require ultra-pure water); "
            "(4) Supply chain geopolitical exposure to China (rare earths, precursor materials)."
        ),
        'ai_investment_thesis': (
            f"{AI_DISCLAIMER}\n\n"
            "South Korea is the world's most critical jurisdiction for EV battery supply chain "
            "investment. Priority opportunities: battery gigafactories, semiconductor "
            "decarbonisation (chip fabs moving to renewable energy), offshore wind (expanding "
            "programme off southwest coast), and hydrogen import infrastructure."
        ),
        'industrial_sectors': [
            {'name': 'Semiconductors / Electronics', 'ecoiq_score': 64.0, 'pollution_level': 'medium', 'transition_status': 'advancing'},
            {'name': 'Steel / Heavy Industry', 'ecoiq_score': 38.0, 'pollution_level': 'high', 'transition_status': 'developing'},
            {'name': 'Automotive', 'ecoiq_score': 55.0, 'pollution_level': 'medium', 'transition_status': 'advancing'},
            {'name': 'Battery Manufacturing', 'ecoiq_score': 71.0, 'pollution_level': 'medium', 'transition_status': 'leading'},
        ],
        'pollution_hotspots': [
            {'name': 'POSCO Pohang Steel Complex', 'description': 'World\'s largest steel mill — significant air and water pollution', 'severity': 'severe'},
            {'name': 'Gyeonggi-do Industrial Belt', 'description': 'High-density semiconductor and electronics manufacturing zone', 'severity': 'medium'},
        ],
        'financing_gaps': [
            {'sector': 'Renewable Energy Infrastructure', 'gap_usd': 20_000_000_000, 'opportunity': 'Offshore wind and solar to replace coal baseload'},
            {'sector': 'Green Hydrogen', 'gap_usd': 15_000_000_000, 'opportunity': 'Import infrastructure and domestic electrolysis'},
            {'sector': 'Steel Decarbonisation', 'gap_usd': 12_000_000_000, 'opportunity': 'Hydrogen-based direct reduction for POSCO'},
        ],
        'policy_highlights': [
            {'title': 'Carbon Neutrality Plan 2050', 'description': '40% emissions reduction by 2030 vs. 2018', 'year': 2021, 'status': 'active'},
            {'title': 'Korea ETS (K-ETS)', 'description': 'Asia\'s first national emissions trading scheme', 'year': 2015, 'status': 'active'},
        ],
    },

    # ── China ───────────────────────────────────────────────────────────────────
    {
        'name': 'China',
        'iso_code': 'CN',
        'flag_emoji': '🇨🇳',
        'region': 'east_asia',
        'is_published': True,
        'featured': True,
        'national_ecoiq_index': 48.6,
        'transition_readiness_score': 64.0,
        'policy_environment_score': 58.0,
        'investment_climate_score': 56.0,
        'transparency_score': 44.0,
        'industrial_modernization_score': 68.0,
        'transition_readiness_label': 'developing',
        'gdp_usd': 17_700_000_000_000,
        'industrial_gdp_share': 38.3,
        'co2_megatonnes': 11_900.0,
        'renewable_energy_share': 31.0,
        'fossil_fuel_dependency': 86.0,
        'companies_tracked': 3,
        'estimated_transition_gap_usd': 650_000_000_000,
        'green_finance_available_usd': 220_000_000_000,
        'ai_overview': (
            f"{AI_DISCLAIMER}\n\n"
            "China is simultaneously the world's largest carbon emitter and the world's "
            "largest investor in renewable energy — a profound paradox that defines the "
            "global transition trajectory. EcoIQ tracks three Chinese companies: "
            "CATL (world's largest battery manufacturer), BYD (world's largest EV maker), "
            "and Saudi Aramco's Chinese equity partner in refining (tracked separately). "
            "CATL and BYD represent the most compelling clean transition stories in the "
            "global dataset, with scores of 73.1 and 77.8 respectively.\n\n"
            "China's national EcoIQ index (48.6) is depressed by its industrial base's "
            "coal dependency, transparency deficits, and state-owned enterprise governance "
            "concerns, even as its clean tech sectors outperform global benchmarks."
        ),
        'ai_transition_narrative': (
            f"{AI_DISCLAIMER}\n\n"
            "The China transition story is the world's largest manufacturing pivot. "
            "China now produces 75% of the world's solar panels, 70% of its EV batteries, "
            "and is installing renewable capacity faster than any nation in history. "
            "BYD's rise from chemical company to world's leading EV manufacturer represents "
            "the most dramatic industrial transformation EcoIQ has tracked. CATL's battery "
            "technology leadership is the backbone of the global EV supply chain. "
            "The tension: China continues to build and export coal plants through Belt & "
            "Road while simultaneously leading on clean technology domestically."
        ),
        'ai_risk_summary': (
            f"{AI_DISCLAIMER}\n\n"
            "Primary risks: (1) Coal lock-in — China approved 106 GW of new coal capacity "
            "in 2023; (2) Transparency deficit — state-owned enterprises lack independent "
            "auditing; (3) Geopolitical supply chain risk — Western decoupling creating "
            "parallel supply chains; (4) Belt & Road fossil fuel exports undercutting "
            "transition leadership narrative; (5) Real estate crisis constraining "
            "green infrastructure investment."
        ),
        'ai_investment_thesis': (
            f"{AI_DISCLAIMER}\n\n"
            "Despite governance risks, China offers the world's highest-return clean tech "
            "investment opportunities. Priority areas: battery supply chain (CATL ecosystem), "
            "EV charging infrastructure (BYD network), offshore wind manufacturing, "
            "solar panel upstream supply chain. Requires careful geopolitical risk hedging "
            "and supply chain transparency diligence."
        ),
        'industrial_sectors': [
            {'name': 'Battery Technology', 'ecoiq_score': 73.0, 'pollution_level': 'medium', 'transition_status': 'leading'},
            {'name': 'EV / New Energy Vehicles', 'ecoiq_score': 78.0, 'pollution_level': 'low', 'transition_status': 'leading'},
            {'name': 'Steel / Heavy Industry', 'ecoiq_score': 32.0, 'pollution_level': 'severe', 'transition_status': 'lagging'},
            {'name': 'Coal Power', 'ecoiq_score': 18.0, 'pollution_level': 'severe', 'transition_status': 'critical'},
            {'name': 'Renewables Manufacturing', 'ecoiq_score': 72.0, 'pollution_level': 'low', 'transition_status': 'leading'},
            {'name': 'State-Owned Finance', 'ecoiq_score': 38.0, 'pollution_level': 'low', 'transition_status': 'developing'},
        ],
        'pollution_hotspots': [
            {'name': 'Hebei Province Steel Belt', 'description': 'World\'s most polluted steel-making region; PM2.5 levels far exceed WHO limits', 'severity': 'severe'},
            {'name': 'Inner Mongolia Coal Fields', 'description': 'Massive coal extraction and power generation complex', 'severity': 'severe'},
            {'name': 'Pearl River Delta Manufacturing', 'description': 'High-density electronics and chemical manufacturing; significant heavy metal contamination', 'severity': 'high'},
        ],
        'financing_gaps': [
            {'sector': 'Coal Transition Finance', 'gap_usd': 200_000_000_000, 'opportunity': 'Just transition for coal regions and workers'},
            {'sector': 'Grid Modernization', 'gap_usd': 180_000_000_000, 'opportunity': 'Ultra-high voltage grid for renewable integration'},
            {'sector': 'Energy Storage', 'gap_usd': 100_000_000_000, 'opportunity': 'Grid-scale battery storage for intermittent renewables'},
        ],
        'policy_highlights': [
            {'title': 'Carbon Neutrality 2060', 'description': 'Peak emissions before 2030, carbon neutrality by 2060', 'year': 2020, 'status': 'active'},
            {'title': 'China ETS', 'description': 'World\'s largest carbon market by emissions coverage', 'year': 2021, 'status': 'active'},
            {'title': '14th Five-Year Plan', 'description': '20% non-fossil energy in primary energy by 2025', 'year': 2021, 'status': 'active'},
        ],
    },

    # ── Saudi Arabia ────────────────────────────────────────────────────────────
    {
        'name': 'Saudi Arabia',
        'iso_code': 'SA',
        'flag_emoji': '🇸🇦',
        'region': 'middle_east',
        'is_published': True,
        'featured': True,
        'national_ecoiq_index': 34.2,
        'transition_readiness_score': 42.0,
        'policy_environment_score': 45.0,
        'investment_climate_score': 54.0,
        'transparency_score': 38.0,
        'industrial_modernization_score': 52.0,
        'transition_readiness_label': 'developing',
        'gdp_usd': 1_100_000_000_000,
        'industrial_gdp_share': 44.2,
        'co2_megatonnes': 723.0,
        'renewable_energy_share': 3.0,
        'fossil_fuel_dependency': 99.0,
        'companies_tracked': 1,
        'estimated_transition_gap_usd': 120_000_000_000,
        'green_finance_available_usd': 18_000_000_000,
        'ai_overview': (
            f"{AI_DISCLAIMER}\n\n"
            "Saudi Arabia presents one of the most complex transition challenges in EcoIQ's "
            "global dataset. As the world's largest oil exporter and home to Saudi Aramco — "
            "the company with the highest absolute carbon emissions among any EcoIQ-tracked "
            "entity — the Kingdom's transition trajectory has outsized global consequences.\n\n"
            "Saudi Aramco's EcoIQ score (29.5) places it in the Extractive/Harmful category, "
            "reflecting its severe pollution intensity, profit extraction concentration, and "
            "governance transparency gaps. Vision 2030 articulates a genuine diversification "
            "ambition, but the pace of industrial transition lags the stated goals significantly. "
            "The country's renewable energy share (3%) is among the lowest in the EcoIQ dataset."
        ),
        'ai_transition_narrative': (
            f"{AI_DISCLAIMER}\n\n"
            "Vision 2030's transition narrative centres on three pillars: diversifying GDP "
            "beyond oil (target: 50% non-oil by 2030), expanding renewable energy (target: "
            "50% renewable electricity by 2030), and developing an industrial base in "
            "mining, tourism, logistics, and technology. NEOM — the flagship megaproject — "
            "represents both the ambition and the risk: a $500bn planned city powered by "
            "100% renewables, but facing serious questions about environmental impact, "
            "human rights, and financial viability. Aramco's downstream diversification "
            "into chemicals is the credible near-term transition bet."
        ),
        'ai_risk_summary': (
            f"{AI_DISCLAIMER}\n\n"
            "Primary risks: (1) Economic structural dependency — oil revenues fund 60%+ of "
            "government spending; (2) Governance transparency — limited independent audit "
            "of Aramco's reserve claims and emissions data; (3) Human rights concerns — "
            "labour rights, freedom of expression, and social constraints affect "
            "international investment climate; (4) Water scarcity — desalination energy "
            "demand compounds fossil fuel dependency; (5) NEOM viability risk."
        ),
        'ai_investment_thesis': (
            f"{AI_DISCLAIMER}\n\n"
            "High-risk, high-potential transition play. Priority opportunities: "
            "desert solar (Saudi Arabia has the world's highest solar irradiance), "
            "green hydrogen export (NEOM H2 project — one of world's largest), "
            "industrial city infrastructure (SABIC chemicals modernisation), "
            "mining sector modernisation (phosphates, copper, gold). "
            "ESG-aware investors require enhanced transparency and governance commitments "
            "before large-scale allocation."
        ),
        'industrial_sectors': [
            {'name': 'Oil & Gas', 'ecoiq_score': 29.0, 'pollution_level': 'severe', 'transition_status': 'critical'},
            {'name': 'Petrochemicals', 'ecoiq_score': 36.0, 'pollution_level': 'high', 'transition_status': 'lagging'},
            {'name': 'Renewables (Emerging)', 'ecoiq_score': 58.0, 'pollution_level': 'low', 'transition_status': 'developing'},
            {'name': 'Mining', 'ecoiq_score': 40.0, 'pollution_level': 'medium', 'transition_status': 'developing'},
        ],
        'pollution_hotspots': [
            {'name': 'Ghawar Oil Field Complex', 'description': 'World\'s largest conventional oil field; gas flaring and produced water contamination', 'severity': 'severe'},
            {'name': 'Jubail Industrial City', 'description': 'World\'s largest industrial city; petrochemicals, fertilisers, steel — significant air and water pollution', 'severity': 'severe'},
        ],
        'financing_gaps': [
            {'sector': 'Solar / Renewable Energy', 'gap_usd': 50_000_000_000, 'opportunity': 'Utility-scale solar to meet 50% renewable target'},
            {'sector': 'Green Hydrogen Export', 'gap_usd': 30_000_000_000, 'opportunity': 'NEOM H2 project and export terminal infrastructure'},
            {'sector': 'Mining Modernisation', 'gap_usd': 25_000_000_000, 'opportunity': 'Ma\'aden mineral diversification and clean processing'},
        ],
        'policy_highlights': [
            {'title': 'Vision 2030', 'description': 'Economic diversification: 50% non-oil GDP, 1m new jobs by 2030', 'year': 2016, 'status': 'active'},
            {'title': 'Saudi Green Initiative', 'description': 'Net zero by 2060; 50% renewable electricity by 2030', 'year': 2021, 'status': 'active'},
            {'title': 'National Industrial Strategy', 'description': 'Manufacturing output target: 400bn SAR by 2030', 'year': 2022, 'status': 'active'},
        ],
    },

    # ── Kazakhstan ──────────────────────────────────────────────────────────────
    {
        'name': 'Kazakhstan',
        'iso_code': 'KZ',
        'flag_emoji': '🇰🇿',
        'region': 'central_asia',
        'is_published': True,
        'featured': True,
        'national_ecoiq_index': 29.8,
        'transition_readiness_score': 34.0,
        'policy_environment_score': 36.0,
        'investment_climate_score': 42.0,
        'transparency_score': 32.0,
        'industrial_modernization_score': 38.0,
        'transition_readiness_label': 'lagging',
        'gdp_usd': 259_000_000_000,
        'industrial_gdp_share': 36.4,
        'co2_megatonnes': 248.0,
        'renewable_energy_share': 6.0,
        'fossil_fuel_dependency': 94.0,
        'companies_tracked': 0,
        'estimated_transition_gap_usd': 35_000_000_000,
        'green_finance_available_usd': 2_800_000_000,
        'ai_overview': (
            f"{AI_DISCLAIMER}\n\n"
            "Kazakhstan is Central Asia's largest economy and one of the world's most "
            "resource-intensive industrial nations. With oil and gas constituting 60%+ of "
            "export revenues and coal powering 70% of electricity, the country's transition "
            "gap is among the largest per capita in EcoIQ's dataset. The Tengiz and "
            "Kashagan oil fields (operated by Chevron and international consortia) are "
            "among the most complex and emissions-intensive in the world.\n\n"
            "Kazakhstan has no EcoIQ-tracked domestic companies in its initial dataset, "
            "reflecting limited corporate disclosure standards. The Government's Green "
            "Economy Concept (2013) and Climate Strategy 2060 commit to carbon neutrality, "
            "but implementation pace is significantly below stated ambition."
        ),
        'ai_transition_narrative': (
            f"{AI_DISCLAIMER}\n\n"
            "Kazakhstan's transition opportunity is enormous: abundant solar and wind "
            "resources (3,000 hours/year sunshine, strong steppe winds), large uranium "
            "reserves (world's largest producer), and emerging lithium and rare earth "
            "deposits. The country is positioned to become a significant clean energy "
            "and critical minerals supplier to both European and Asian markets. "
            "Tengizchevroil's Future Growth Project demonstrates international capital's "
            "continued appetite for upstream extraction, creating a structural "
            "tension with transition ambitions. Astana Finance Hub is developing "
            "green bond frameworks to attract transition finance."
        ),
        'ai_risk_summary': (
            f"{AI_DISCLAIMER}\n\n"
            "Primary risks: (1) Governance and corruption — Transparency International "
            "ranks Kazakhstan 93rd globally, depressing investor confidence; (2) "
            "Infrastructure deficit — power grid and transport modernisation require "
            "massive capital that domestic capacity cannot provide; (3) Geopolitical "
            "positioning between Russia and China creates alignment complexity; "
            "(4) Environmental enforcement gap — mining and extraction pollution "
            "significantly underreported; (5) Skilled labour shortage for "
            "knowledge-economy transition."
        ),
        'ai_investment_thesis': (
            f"{AI_DISCLAIMER}\n\n"
            "Kazakhstan's transition investment case rests on three pillars: "
            "(1) Critical minerals — lithium, cobalt, rare earths for EV supply chain; "
            "(2) Renewable energy — utility-scale solar and wind at competitive LCOE for "
            "regional export; (3) Nuclear expansion — Kazatomprom uranium supply combined "
            "with potential small modular reactor deployment. "
            "Requires governance improvement and transparency commitments for "
            "institutional investment at scale. AIIB and EBRD active in market."
        ),
        'industrial_sectors': [
            {'name': 'Oil & Gas', 'ecoiq_score': 24.0, 'pollution_level': 'severe', 'transition_status': 'critical'},
            {'name': 'Coal Power', 'ecoiq_score': 18.0, 'pollution_level': 'severe', 'transition_status': 'critical'},
            {'name': 'Mining (Metals & Minerals)', 'ecoiq_score': 30.0, 'pollution_level': 'high', 'transition_status': 'lagging'},
            {'name': 'Uranium Mining', 'ecoiq_score': 42.0, 'pollution_level': 'medium', 'transition_status': 'developing'},
            {'name': 'Agriculture', 'ecoiq_score': 45.0, 'pollution_level': 'medium', 'transition_status': 'developing'},
        ],
        'pollution_hotspots': [
            {'name': 'Tengiz / Kashagan Oil Fields', 'description': 'Massive oil extraction complex with sour gas (H₂S) flaring and significant toxic waste', 'severity': 'severe'},
            {'name': 'Ekibastuz Coal Complex', 'description': 'World\'s largest open-pit coal mine — severe air and land pollution', 'severity': 'severe'},
            {'name': 'Balkhash Copper Smelter', 'description': 'Major SO₂ and heavy metal pollution affecting Lake Balkhash basin', 'severity': 'severe'},
            {'name': 'Aral Sea Region', 'description': 'Environmental catastrophe — dried sea bed releasing salt and pesticide dust', 'severity': 'severe'},
        ],
        'financing_gaps': [
            {'sector': 'Renewable Energy Infrastructure', 'gap_usd': 12_000_000_000, 'opportunity': 'Utility-scale solar and wind to replace coal'},
            {'sector': 'Grid Modernisation', 'gap_usd': 8_000_000_000, 'opportunity': 'Aging Soviet-era grid requires full replacement'},
            {'sector': 'Critical Minerals Processing', 'gap_usd': 6_000_000_000, 'opportunity': 'In-country processing of lithium and rare earths'},
            {'sector': 'Clean Coal Transition', 'gap_usd': 5_000_000_000, 'opportunity': 'Just transition for mining communities'},
        ],
        'policy_highlights': [
            {'title': 'Climate Strategy 2060', 'description': 'Carbon neutrality by 2060, 15% renewables by 2030', 'year': 2021, 'status': 'active'},
            {'title': 'Green Economy Concept', 'description': 'Water efficiency, renewable energy, sustainable agriculture targets', 'year': 2013, 'status': 'active'},
            {'title': 'Astana Finance Hub Green Bond Framework', 'description': 'Green and climate bond listing framework for Central Asian issuers', 'year': 2022, 'status': 'active'},
        ],
    },

    # ── UAE ─────────────────────────────────────────────────────────────────────
    {
        'name': 'United Arab Emirates',
        'iso_code': 'AE',
        'flag_emoji': '🇦🇪',
        'region': 'middle_east',
        'is_published': True,
        'featured': False,
        'national_ecoiq_index': 41.5,
        'transition_readiness_score': 54.0,
        'policy_environment_score': 58.0,
        'investment_climate_score': 66.0,
        'transparency_score': 52.0,
        'industrial_modernization_score': 62.0,
        'transition_readiness_label': 'developing',
        'gdp_usd': 507_000_000_000,
        'industrial_gdp_share': 38.0,
        'co2_megatonnes': 238.0,
        'renewable_energy_share': 14.0,
        'fossil_fuel_dependency': 95.0,
        'companies_tracked': 0,
        'estimated_transition_gap_usd': 40_000_000_000,
        'green_finance_available_usd': 12_000_000_000,
        'ai_overview': (
            f"{AI_DISCLAIMER}\n\n"
            "The UAE is the most advanced Gulf economy in its transition positioning, "
            "having hosted COP28 in Dubai (2023) and committed to net zero by 2050. "
            "ADNOC (Abu Dhabi National Oil Company) remains the dominant industrial entity, "
            "but Abu Dhabi and Dubai are both investing significantly in clean energy, "
            "AI infrastructure, and financial services diversification.\n\n"
            "The Masdar Clean Energy platform is among the most credible sovereign-backed "
            "renewable energy investors globally. ENEC's Barakah nuclear plant (commissioned "
            "2021) gives the UAE a low-carbon baseload anchor. COP28's outcome — the first "
            "global agreement to 'transition away' from fossil fuels — positions the "
            "UAE as an unlikely but significant transition catalyst."
        ),
        'ai_transition_narrative': (
            f"{AI_DISCLAIMER}\n\n"
            "The UAE's transition narrative has two tracks: Abu Dhabi's oil-funded sovereign "
            "wealth diversification (Mubadala, ADIA) investing globally in clean tech, "
            "and Dubai's pivot to become a global hub for AI, fintech, and digital economy. "
            "Masdar's 100 GW renewable energy target by 2030 is one of the world's largest "
            "stated ambitions from a Gulf nation. The challenge: ADNOC's concurrent "
            "expansion programme and COP28 'business of transition' framing that "
            "emphasised abatement over reduction."
        ),
        'ai_risk_summary': (
            f"{AI_DISCLAIMER}\n\n"
            "Primary risks: (1) ADNOC expansion despite transition rhetoric; "
            "(2) Labour rights — migrant worker conditions remain a significant governance "
            "concern affecting investment ESG screening; (3) Water security — "
            "desalination dependency makes industrial expansion energy/cost intensive; "
            "(4) Financial centre competition — Singapore and London challenge "
            "Dubai's green finance hub ambitions."
        ),
        'ai_investment_thesis': (
            f"{AI_DISCLAIMER}\n\n"
            "UAE presents a unique hub-and-spoke transition investment platform: "
            "access to MENA deal flow, sovereign wealth co-investment potential, "
            "and AI infrastructure at competitive energy cost. Priority opportunities: "
            "solar-powered data centres, green hydrogen export, MENA renewable energy "
            "development through Masdar, and Islamic green finance instruments."
        ),
        'industrial_sectors': [
            {'name': 'Oil & Gas', 'ecoiq_score': 34.0, 'pollution_level': 'high', 'transition_status': 'lagging'},
            {'name': 'Renewable Energy', 'ecoiq_score': 68.0, 'pollution_level': 'low', 'transition_status': 'advancing'},
            {'name': 'Financial Services', 'ecoiq_score': 58.0, 'pollution_level': 'low', 'transition_status': 'advancing'},
            {'name': 'Real Estate / Infrastructure', 'ecoiq_score': 46.0, 'pollution_level': 'medium', 'transition_status': 'developing'},
        ],
        'pollution_hotspots': [
            {'name': 'ADNOC Offshore Fields', 'description': 'Abu Dhabi offshore oil and gas with methane flaring', 'severity': 'high'},
            {'name': 'Ruwais Industrial Complex', 'description': 'Large petrochemical and refining complex — significant emissions', 'severity': 'high'},
        ],
        'financing_gaps': [
            {'sector': 'Utility-Scale Solar', 'gap_usd': 18_000_000_000, 'opportunity': 'Al Dhafra Solar expansion and new projects'},
            {'sector': 'Green Hydrogen Export', 'gap_usd': 12_000_000_000, 'opportunity': 'Export infrastructure for European market supply'},
        ],
        'policy_highlights': [
            {'title': 'UAE Net Zero 2050', 'description': 'Net zero by 2050 — first Gulf state to commit', 'year': 2021, 'status': 'active'},
            {'title': 'UAE Energy Strategy 2050', 'description': '44% clean energy by 2050; 44% nuclear, 38% gas, 6% coal, 12% renewables', 'year': 2017, 'status': 'active'},
        ],
    },

    # ── Turkey ──────────────────────────────────────────────────────────────────
    {
        'name': 'Turkey',
        'iso_code': 'TR',
        'flag_emoji': '🇹🇷',
        'region': 'middle_east',
        'is_published': True,
        'featured': False,
        'national_ecoiq_index': 38.5,
        'transition_readiness_score': 42.0,
        'policy_environment_score': 44.0,
        'investment_climate_score': 52.0,
        'transparency_score': 40.0,
        'industrial_modernization_score': 50.0,
        'transition_readiness_label': 'developing',
        'gdp_usd': 1_108_000_000_000,
        'industrial_gdp_share': 28.3,
        'co2_megatonnes': 523.0,
        'renewable_energy_share': 42.0,
        'fossil_fuel_dependency': 68.0,
        'companies_tracked': 0,
        'estimated_transition_gap_usd': 55_000_000_000,
        'green_finance_available_usd': 8_000_000_000,
        'ai_overview': (
            f"{AI_DISCLAIMER}\n\n"
            "Turkey is a uniquely positioned economy bridging European and Middle Eastern "
            "industrial systems. With a population of 85 million and a rapidly growing "
            "industrial base, the country is the second-largest steel producer in Europe, "
            "a major automotive manufacturer, and an increasingly important hub for "
            "defence, technology, and construction exports.\n\n"
            "Turkey's energy profile is paradoxical: 42% renewable electricity generation "
            "(primarily hydro, with fast-growing solar and wind) coexists with heavy "
            "dependence on imported fossil fuels for industry and heating. The country "
            "ratified the Paris Agreement only in 2021, making it a late entrant to "
            "international climate frameworks, but has since accelerated renewable deployment "
            "significantly. EcoIQ currently tracks no Turkish-domiciled companies in its "
            "initial dataset, reflecting limited English-language corporate disclosure standards. "
            "Key sectors — steel, cement, textiles, automotive — represent significant "
            "transition finance opportunities."
        ),
        'ai_transition_narrative': (
            f"{AI_DISCLAIMER}\n\n"
            "Turkey's transition story is anchored in its exceptional renewable energy "
            "resource base. The country has outstanding solar irradiance across Anatolia, "
            "strong Aegean and Black Sea wind corridors, and the largest hydropower capacity "
            "in its region. Installed solar capacity tripled between 2019–2023, and onshore "
            "wind deployment accelerated under the YEKA (Renewable Energy Resource Area) "
            "auction mechanism.\n\n"
            "The key tension is industrial: Turkey's steel and cement sectors are among "
            "the most carbon-intensive per unit of output globally, yet also among the most "
            "competitive manufacturers for European and Gulf markets. The EU's Carbon Border "
            "Adjustment Mechanism (CBAM, effective 2026) creates a powerful incentive for "
            "Turkish industrial decarbonisation — steel and cement face direct tariff "
            "exposure. This represents the most significant near-term driver of industrial "
            "transition investment in Turkey."
        ),
        'ai_risk_summary': (
            f"{AI_DISCLAIMER}\n\n"
            "Primary risks: (1) Currency and macroeconomic volatility — Turkish lira "
            "depreciation creates long-duration investment risk for foreign capital; "
            "(2) Governance and rule-of-law concerns — Transparency International ranks "
            "Turkey 115th globally, creating contract and regulatory risk; (3) Coal "
            "dependency — Turkey approved new coal plants while committing to net zero "
            "by 2053, creating stranded asset risk; (4) CBAM exposure — EU export "
            "competitiveness in steel and cement at risk without decarbonisation investment; "
            "(5) Political risk — limited institutional independence affects investment "
            "structuring for long-duration assets."
        ),
        'ai_investment_thesis': (
            f"{AI_DISCLAIMER}\n\n"
            "Turkey's investment thesis rests on the CBAM-driven industrial modernisation "
            "opportunity and its exceptional renewable resource base. Priority investment "
            "areas: (1) Green steel — hydrogen-based direct reduction to preserve EU market "
            "access; (2) Utility-scale solar (best-in-class irradiance, low land cost); "
            "(3) Offshore wind — Black Sea and Aegean expansion under YEKA; (4) Industrial "
            "energy efficiency — cement, ceramics, glass decarbonisation with EBRD support; "
            "(5) EV supply chain — growing automotive manufacturing base and proximity to "
            "European OEMs. EBRD and IFC both active in country. Requires currency risk "
            "hedging and governance diligence for institutional allocation."
        ),
        'industrial_sectors': [
            {'name': 'Steel / Iron', 'ecoiq_score': 32.0, 'pollution_level': 'high', 'transition_status': 'developing'},
            {'name': 'Cement / Construction Materials', 'ecoiq_score': 28.0, 'pollution_level': 'high', 'transition_status': 'lagging'},
            {'name': 'Automotive Manufacturing', 'ecoiq_score': 52.0, 'pollution_level': 'medium', 'transition_status': 'advancing'},
            {'name': 'Textiles / Apparel', 'ecoiq_score': 46.0, 'pollution_level': 'medium', 'transition_status': 'developing'},
            {'name': 'Renewable Energy', 'ecoiq_score': 68.0, 'pollution_level': 'low', 'transition_status': 'advancing'},
            {'name': 'Defence / Aerospace', 'ecoiq_score': 44.0, 'pollution_level': 'medium', 'transition_status': 'developing'},
        ],
        'pollution_hotspots': [
            {'name': 'Karabük Steel Complex', 'description': 'Major integrated steel plant with significant air and water pollution — CBAM exposure', 'severity': 'high'},
            {'name': 'Aliağa Industrial Zone (Izmir)', 'description': 'Iron/steel, petrochemicals, and ship-breaking — persistent air and marine pollution', 'severity': 'high'},
            {'name': 'Zonguldak Coal Mining Region', 'description': 'Black Sea coal mining and legacy thermal power — high particulate and SO₂ emissions', 'severity': 'high'},
            {'name': 'Marmara Sea Mucilage Zone', 'description': 'Industrial and agricultural run-off has caused recurring mucilage blooms threatening marine ecosystem', 'severity': 'severe'},
        ],
        'financing_gaps': [
            {'sector': 'Green Steel (CBAM Compliance)', 'gap_usd': 18_000_000_000, 'opportunity': 'DRI-EAF conversion and hydrogen infrastructure to maintain EU market access'},
            {'sector': 'Offshore Wind (Black Sea / Aegean)', 'gap_usd': 15_000_000_000, 'opportunity': 'YEKA offshore auction program — 5 GW pipeline'},
            {'sector': 'Industrial Energy Efficiency', 'gap_usd': 12_000_000_000, 'opportunity': 'Cement, ceramics, glass decarbonisation with EBRD/IFC co-financing'},
            {'sector': 'EV Manufacturing Supply Chain', 'gap_usd': 8_000_000_000, 'opportunity': 'Battery and EV component manufacturing for OEM supply chains'},
        ],
        'policy_highlights': [
            {'title': 'Paris Agreement Ratification', 'description': 'Turkey ratified the Paris Agreement and committed to net zero by 2053', 'year': 2021, 'status': 'active'},
            {'title': 'YEKA Renewable Auctions', 'description': 'Renewable Energy Resource Area program — large-scale wind and solar tendering', 'year': 2017, 'status': 'active'},
            {'title': 'National Climate Strategy 2053', 'description': 'Net zero by 2053, 100% renewable electricity by 2035 target', 'year': 2022, 'status': 'active'},
            {'title': 'CBAM Adaptation', 'description': 'EU Carbon Border Adjustment Mechanism creates mandatory decarbonisation pressure on steel, cement', 'year': 2023, 'status': 'critical deadline 2026'},
        ],
    },

    # ── Denmark ─────────────────────────────────────────────────────────────────
    {
        'name': 'Denmark',
        'iso_code': 'DK',
        'flag_emoji': '🇩🇰',
        'region': 'western_europe',
        'is_published': True,
        'featured': True,
        'national_ecoiq_index': 78.4,
        'transition_readiness_score': 88.0,
        'policy_environment_score': 86.0,
        'investment_climate_score': 82.0,
        'transparency_score': 90.0,
        'industrial_modernization_score': 80.0,
        'transition_readiness_label': 'leading',
        'gdp_usd': 406_000_000_000,
        'industrial_gdp_share': 19.4,
        'co2_megatonnes': 32.0,
        'renewable_energy_share': 83.0,
        'fossil_fuel_dependency': 54.0,
        'companies_tracked': 1,
        'estimated_transition_gap_usd': 4_000_000_000,
        'green_finance_available_usd': 6_000_000_000,
        'ai_overview': (
            f"{AI_DISCLAIMER}\n\n"
            "Denmark is the global benchmark for industrial transition. It hosts Ørsted — "
            "EcoIQ's highest-scoring energy company (86.4) and the world's leading offshore "
            "wind developer — and has achieved 83% renewable electricity, the highest "
            "sustained level among major economies. Denmark's national EcoIQ index (78.4) "
            "is the highest in EcoIQ's initial country dataset.\n\n"
            "The Danish transition story is remarkable not just for outcomes but for process: "
            "Ørsted began as DONG Energy (Danish Oil and Natural Gas), one of Europe's most "
            "coal-intensive utilities, and transformed into the world's leading offshore wind "
            "developer in under a decade. This story — from fossil fuel dependency to "
            "renewable leadership through deliberate industrial strategy — is the most "
            "cited transition case study in EcoIQ's analysis."
        ),
        'ai_transition_narrative': (
            f"{AI_DISCLAIMER}\n\n"
            "Ørsted's transformation defines the Denmark transition narrative. "
            "The company divested its oil and gas business, shuttered coal plants, and "
            "reinvested entirely in offshore wind — achieving a 70-point EcoIQ score "
            "improvement in under 10 years. Denmark's electricity system demonstrates that "
            "80%+ renewable penetration is operationally viable at grid scale. "
            "The country is now a net electricity exporter and is developing Power-to-X "
            "(green hydrogen) as the next phase of its energy transition. "
            "Maersk — also Danish — is leading maritime decarbonisation through methanol "
            "and ammonia fuel investment."
        ),
        'ai_risk_summary': (
            f"{AI_DISCLAIMER}\n\n"
            "Denmark's risk profile is low by global standards. Primary considerations: "
            "(1) Remaining fossil fuel dependency (54%) concentrated in heating and transport; "
            "(2) North Sea gas phase-out timeline — Denmark still produces gas as a "
            "European security supplier post-Ukraine crisis; (3) Wind energy supply chain "
            "concentration risk (Vestas/Siemens Gamesa duopoly); (4) Housing cost and "
            "inequality as rapid transition creates urban-rural economic divergence."
        ),
        'ai_investment_thesis': (
            f"{AI_DISCLAIMER}\n\n"
            "Denmark is the world's most de-risked transition investment environment. "
            "Priority opportunities: offshore wind supply chain (foundations, cables, "
            "installation vessels), Power-to-X infrastructure for green hydrogen export, "
            "maritime decarbonisation technology (following Maersk's green fuel bet), "
            "and Nordic circular economy businesses. Low returns reflect low risk — "
            "Denmark is appropriate for impact-first institutional capital."
        ),
        'industrial_sectors': [
            {'name': 'Offshore Wind', 'ecoiq_score': 86.0, 'pollution_level': 'low', 'transition_status': 'leading'},
            {'name': 'Shipping / Maritime', 'ecoiq_score': 70.0, 'pollution_level': 'medium', 'transition_status': 'advancing'},
            {'name': 'Pharmaceuticals', 'ecoiq_score': 74.0, 'pollution_level': 'low', 'transition_status': 'leading'},
            {'name': 'Agriculture / Food', 'ecoiq_score': 62.0, 'pollution_level': 'medium', 'transition_status': 'advancing'},
        ],
        'pollution_hotspots': [
            {'name': 'North Sea Gas Fields', 'description': 'Remaining offshore gas extraction; being phased out by 2050', 'severity': 'medium'},
        ],
        'financing_gaps': [
            {'sector': 'Power-to-X / Green Hydrogen', 'gap_usd': 2_500_000_000, 'opportunity': 'Electrolysis and export infrastructure for green hydrogen'},
            {'sector': 'District Heating Electrification', 'gap_usd': 1_200_000_000, 'opportunity': 'Heat pump conversion of legacy district heating systems'},
        ],
        'policy_highlights': [
            {'title': 'Climate Act 2020', 'description': '70% emissions reduction by 2030 vs. 1990; climate neutrality by 2050', 'year': 2020, 'status': 'active'},
            {'title': 'Energy Island Bornholm', 'description': 'World\'s first energy island — 2 GW offshore wind hub in Baltic Sea', 'year': 2022, 'status': 'active'},
            {'title': 'North Sea Agreement', 'description': 'No new oil and gas exploration licenses — managed phase-out', 'year': 2020, 'status': 'active'},
        ],
    },

]


class Command(BaseCommand):
    help = 'Seed 10 country intelligence profiles (idempotent — safe to re-run).'

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for data in COUNTRIES:
            obj, created = CountryProfile.objects.update_or_create(
                name=data['name'],
                defaults=data,
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  CREATED  {obj.flag_emoji} {obj.name}'))
            else:
                updated_count += 1
                self.stdout.write(f'  updated  {obj.flag_emoji} {obj.name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Done — {created_count} created, {updated_count} updated.'
            )
        )
