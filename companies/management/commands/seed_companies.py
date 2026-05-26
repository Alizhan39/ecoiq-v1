"""
EcoIQ — Seed public company profiles for 10 major Kazakh companies.

Usage:
    python manage.py seed_companies
    python manage.py seed_companies --clear
"""
from django.core.management.base import BaseCommand
from django.db import transaction

SEED_DATA = [
    # ────────────────────────────────────────────────────────────────────────
    # 1. KazMunayGas
    # ────────────────────────────────────────────────────────────────────────
    {
        'name':    'KazMunayGas',
        'slug':    'kazmunaygas',
        'sector':  'oil_gas',
        'country': 'Kazakhstan',
        'description': (
            'KazMunayGas (KMG) is Kazakhstan\'s national oil and gas company and '
            'the country\'s largest hydrocarbon producer. It manages the state\'s '
            'interests in all major oil and gas projects including Tengizchevroil, '
            'Kashagan, and Karachaganak. KMG employs over 60,000 people and is '
            'a key driver of Kazakhstan\'s export revenues and national budget.'
        ),
        'website': 'https://www.kmgep.kz',
        'logo_url': '',
        'annual_revenue_usd': 22_000_000_000,
        'employee_count': 62000,
        # CompanyProfile fields
        'pollution_level': 'high',
        'estimated_emissions': 18_500_000,
        'renewable_energy_share': 3.0,
        'waste_management_score': 38.0,
        'water_impact_score': 40.0,
        'biodiversity_impact_score': 30.0,
        'jobs_created_score': 78.0,
        'regional_development_score': 72.0,
        'infrastructure_contribution_score': 80.0,
        'national_value_score': 85.0,
        'energy_transition_score': 30.0,
        'digitalization_score': 42.0,
        'infrastructure_upgrade_score': 50.0,
        'future_readiness_score': 35.0,
        'transparency_score_detail': 42.0,
        'audit_quality_score': 50.0,
        'procurement_transparency_score': 38.0,
        'anti_corruption_score': 35.0,
        'controversy_risk_score': 55.0,
        'profit_extraction_score': 68.0,
        'profit_extraction_risk_score': 62.0,
        'ownership_type': 'state',
        'state_owned_percentage': 100.0,
        'funding_status': 'open_to_funding',
        'funding_needed': 5_000_000_000,
        'investor_visibility': True,
        'modernization_projects': [
            'Kashagan Phase 2 Sour Gas Injection',
            'KMG CarbonTrack emissions monitoring',
            'Tengiz Future Growth Project',
        ],
        'modernization_investment': 1_200_000_000,
        'ai_summary': (
            'KazMunayGas is Kazakhstan\'s flagship energy enterprise and the primary '
            'custodian of the country\'s hydrocarbon wealth. With a current EcoIQ score '
            'of 52.3, the company demonstrates strong national value creation and '
            'employment generation, but faces material challenges in environmental '
            'stewardship, transparency, and clean energy transition. Its scale and '
            'state ownership position it as a critical lever for Kazakhstan\'s overall '
            'industrial decarbonisation trajectory.'
        ),
        'ai_modernization_report': (
            'KMG\'s modernization agenda is focused on sustaining hydrocarbon production '
            'efficiency rather than diversification into cleaner energy. Key opportunities '
            'include LDAR (leak detection and repair) programme rollout, adoption of CCUS '
            'technology at major fields, and development of a credible coal-to-gas '
            'transition export strategy. A 10-year carbon management roadmap aligned '
            'with Kazakhstan\'s NDC commitments would significantly improve investor '
            'perception and ESG ratings.'
        ),
        'ai_investment_opportunity': (
            'KMG represents a high-impact transition finance opportunity for DFIs such '
            'as EBRD and IFC. The company\'s scale and government backing provide '
            'credit security, while the transition gap — particularly in methane '
            'reduction and renewables integration — creates a bankable investment '
            'pipeline exceeding $5B over the next decade.'
        ),
        'ai_risk_notes': (
            'Primary risks include limited public ESG disclosure, elevated controversy '
            'risk related to environmental incidents at legacy fields, and a governance '
            'structure that limits independent audit quality. Transparency scores '
            'below 45 indicate significant reporting gaps that would deter ESG-mandated '
            'institutional investors.'
        ),
        'ai_recommendations': [
            'Publish an independently audited annual GRI-aligned sustainability report',
            'Implement a company-wide LDAR programme targeting 50% methane reduction by 2030',
            'Establish a dedicated $500M Energy Transition Fund for renewable and efficiency projects',
            'Achieve CDP Climate Change disclosure participation within 12 months',
            'Appoint independent ESG committee to board with public reporting mandate',
        ],
        'annual_report_url': 'https://www.kmgep.kz/investors/annual-reports/',
        'ecoiq_manual': 52.3,  # used to set initial score if not recalculated
    },

    # ────────────────────────────────────────────────────────────────────────
    # 2. QazaqGaz
    # ────────────────────────────────────────────────────────────────────────
    {
        'name':    'QazaqGaz',
        'slug':    'qazaqgaz',
        'sector':  'oil_gas',
        'country': 'Kazakhstan',
        'description': (
            'QazaqGaz is Kazakhstan\'s national gas company, responsible for gas '
            'transmission, storage, and distribution across the country. It operates '
            'the Beineu-Shymkent and Central Asia-Centre gas pipelines and provides '
            'gas to over 7 million Kazakhstani households. QazaqGaz plays a central '
            'role in Kazakhstan\'s strategic gasification programme.'
        ),
        'website': 'https://www.qazaqgaz.kz',
        'annual_revenue_usd': 4_500_000_000,
        'employee_count': 28000,
        'pollution_level': 'medium',
        'estimated_emissions': 6_200_000,
        'renewable_energy_share': 5.0,
        'waste_management_score': 52.0,
        'water_impact_score': 55.0,
        'biodiversity_impact_score': 48.0,
        'jobs_created_score': 72.0,
        'regional_development_score': 78.0,
        'infrastructure_contribution_score': 85.0,
        'national_value_score': 82.0,
        'energy_transition_score': 45.0,
        'digitalization_score': 50.0,
        'infrastructure_upgrade_score': 58.0,
        'future_readiness_score': 48.0,
        'transparency_score_detail': 48.0,
        'audit_quality_score': 52.0,
        'procurement_transparency_score': 45.0,
        'anti_corruption_score': 42.0,
        'controversy_risk_score': 38.0,
        'profit_extraction_score': 55.0,
        'profit_extraction_risk_score': 45.0,
        'ownership_type': 'state',
        'state_owned_percentage': 100.0,
        'funding_status': 'seeking_partners',
        'funding_needed': 2_000_000_000,
        'investor_visibility': True,
        'modernization_projects': [
            'Gasification of rural Kazakhstan regions',
            'Gas pipeline modernization (Beineu–Shymkent)',
            'Compressor station efficiency upgrade',
        ],
        'modernization_investment': 450_000_000,
        'ai_summary': (
            'QazaqGaz is a critical enabler of Kazakhstan\'s domestic energy security '
            'and rural gasification agenda. With an EcoIQ score of 55.1, it scores '
            'better than its oil-sector peers on environmental dimensions but still '
            'carries material risks in transparency, anti-corruption, and clean energy '
            'readiness. The company\'s strategic role in the coal-to-gas transition '
            'gives it a compelling public benefit narrative that is underutilised '
            'in investor communications.'
        ),
        'ai_modernization_report': (
            'QazaqGaz has an unusually strong modernization opportunity in the form '
            'of Kazakhstan\'s national gasification programme — which directly displaces '
            'coal and biomass burning in households. However, methane leakage across '
            'the ageing pipeline network remains a significant risk. Priority modernization '
            'investments include SCADA system upgrades, pipeline integrity management, '
            'and a blue hydrogen pilot programme.'
        ),
        'ai_investment_opportunity': (
            'The rural gasification programme creates a credible ESG investment narrative '
            'tied to SDG 7 (Clean Energy), SDG 11 (Sustainable Cities), and SDG 13 '
            '(Climate Action). EBRD and ADB have active lending programmes for exactly '
            'this type of transition infrastructure. An issuance of green bonds backed '
            'by the gasification pipeline would attract European institutional investors.'
        ),
        'ai_risk_notes': (
            'Key transparency risks include limited public disclosure on methane leakage '
            'rates and procurement processes. The company\'s governance structure, while '
            'improved since separation from KMG, still lacks independent board oversight '
            'in key risk committees.'
        ),
        'ai_recommendations': [
            'Commission independent methane leakage audit across pipeline network',
            'Issue a Green Bond backed by gasification programme revenues',
            'Publish pipeline integrity and leak detection KPIs annually',
            'Establish independent procurement review for capital projects >$10M',
            'Develop a blue/green hydrogen pilot to demonstrate transition leadership',
        ],
        'ecoiq_manual': 55.1,
    },

    # ────────────────────────────────────────────────────────────────────────
    # 3. Samruk-Energy
    # ────────────────────────────────────────────────────────────────────────
    {
        'name':    'Samruk-Energy',
        'slug':    'samruk-energy',
        'sector':  'energy',
        'country': 'Kazakhstan',
        'description': (
            'Samruk-Energy is Kazakhstan\'s largest electricity generating company, '
            'a subsidiary of Samruk-Kazyna sovereign wealth fund. It operates coal-fired '
            'power plants, hydroelectric stations, and wind farms providing over 50% of '
            'Kazakhstan\'s electricity generation capacity. The company is central to '
            'Kazakhstan\'s 2060 carbon neutrality goal.'
        ),
        'website': 'https://www.samruk-energy.kz',
        'annual_revenue_usd': 2_800_000_000,
        'employee_count': 22000,
        'pollution_level': 'high',
        'estimated_emissions': 35_000_000,
        'renewable_energy_share': 12.0,
        'waste_management_score': 40.0,
        'water_impact_score': 48.0,
        'biodiversity_impact_score': 38.0,
        'jobs_created_score': 68.0,
        'regional_development_score': 70.0,
        'infrastructure_contribution_score': 82.0,
        'national_value_score': 80.0,
        'energy_transition_score': 42.0,
        'digitalization_score': 45.0,
        'infrastructure_upgrade_score': 42.0,
        'future_readiness_score': 38.0,
        'transparency_score_detail': 40.0,
        'audit_quality_score': 45.0,
        'procurement_transparency_score': 42.0,
        'anti_corruption_score': 38.0,
        'controversy_risk_score': 48.0,
        'profit_extraction_score': 58.0,
        'profit_extraction_risk_score': 50.0,
        'ownership_type': 'state',
        'state_owned_percentage': 100.0,
        'funding_status': 'seeking_partners',
        'funding_needed': 8_000_000_000,
        'investor_visibility': True,
        'modernization_projects': [
            'Balkhash Wind Farm (1,000 MW)',
            'Ekibastuz GRES-2 boiler modernization',
            'Kazakhstan-China HVDC transmission line',
        ],
        'modernization_investment': 800_000_000,
        'ai_summary': (
            'Samruk-Energy is Kazakhstan\'s primary electricity generator and holds '
            'the greatest single-company influence over the country\'s carbon trajectory. '
            'Its EcoIQ score of 50.4 reflects a company at a genuine crossroads: strong '
            'national infrastructure role but severe dependence on coal-fired generation. '
            'The company has announced renewable energy targets but requires substantial '
            'capital and governance reforms to execute credibly.'
        ),
        'ai_modernization_report': (
            'The coal-to-renewable transition pathway for Samruk-Energy is the largest '
            'single decarbonisation opportunity in Central Asia. The Balkhash Wind '
            'project demonstrates emerging technical capability, but the 35,000,000 '
            'tCO₂ annual emissions from coal plants require a funded, phased retirement '
            'schedule. Priority: secure ADB Energy Transition Mechanism financing for '
            'at least one coal plant retirement by 2028.'
        ),
        'ai_investment_opportunity': (
            'Samruk-Energy is a flagship JETP-eligible candidate for Central Asia. '
            'ADB, EBRD, and GCF funding for coal transition is available at concessional '
            'rates. A $3B blended finance package combining DFI loans, green bonds, '
            'and carbon credits would be bankable if supported by a credible transition plan.'
        ),
        'ai_risk_notes': (
            'Coal fleet stranded asset risk is the primary investor concern. Procurement '
            'transparency in major capital projects has been questioned by government '
            'audit bodies. ESG reporting does not meet international standards required '
            'for green bond issuance.'
        ),
        'ai_recommendations': [
            'Publish a coal fleet retirement schedule aligned with 1.5°C scenario',
            'Apply for ADB Energy Transition Mechanism funding for Ekibastuz unit retirement',
            'Issue a Transition Bond for Balkhash Wind Farm under ICMA Transition Finance Handbook',
            'Implement GRI or SASB utility sector reporting by 2025',
            'Establish independent environmental compliance monitoring for all coal sites',
        ],
        'ecoiq_manual': 50.4,
    },

    # ────────────────────────────────────────────────────────────────────────
    # 4. Kazatomprom
    # ────────────────────────────────────────────────────────────────────────
    {
        'name':    'Kazatomprom',
        'slug':    'kazatomprom',
        'sector':  'mining',
        'country': 'Kazakhstan',
        'description': (
            'Kazatomprom is the world\'s largest uranium producer and Kazakhstan\'s '
            'national atomic company. It supplies approximately 40% of global uranium '
            'production via in-situ leaching — a low-disturbance mining method. '
            'Listed on the London Stock Exchange and Astana International Exchange, '
            'Kazatomprom has the highest international disclosure standards of any '
            'Kazakhstani industrial company.'
        ),
        'website': 'https://www.kazatomprom.kz',
        'annual_revenue_usd': 3_200_000_000,
        'employee_count': 20000,
        'pollution_level': 'medium',
        'estimated_emissions': 1_800_000,
        'renewable_energy_share': 8.0,
        'waste_management_score': 62.0,
        'water_impact_score': 58.0,
        'biodiversity_impact_score': 55.0,
        'jobs_created_score': 72.0,
        'regional_development_score': 68.0,
        'infrastructure_contribution_score': 72.0,
        'national_value_score': 78.0,
        'energy_transition_score': 55.0,
        'digitalization_score': 65.0,
        'infrastructure_upgrade_score': 62.0,
        'future_readiness_score': 65.0,
        'transparency_score_detail': 72.0,
        'audit_quality_score': 75.0,
        'procurement_transparency_score': 65.0,
        'anti_corruption_score': 60.0,
        'controversy_risk_score': 28.0,
        'profit_extraction_score': 52.0,
        'profit_extraction_risk_score': 35.0,
        'ownership_type': 'mixed',
        'state_owned_percentage': 75.0,
        'funding_status': 'not_seeking',
        'investor_visibility': True,
        'modernization_projects': [
            'In-situ leaching technology optimization',
            'Digital production monitoring system',
            'Renewable power supply for mine sites',
        ],
        'modernization_investment': 350_000_000,
        'ai_summary': (
            'Kazatomprom stands out among Kazakhstani industrial companies with an '
            'EcoIQ score of 63.2 and best-in-class transparency driven by its dual '
            'stock exchange listing. Its uranium business — while carrying nuclear-related '
            'perception risks — actually operates with relatively low direct emissions '
            'via in-situ leaching methods. The company is positioned to benefit from '
            'the global nuclear renaissance driven by clean energy demand.'
        ),
        'ai_modernization_report': (
            'Kazatomprom\'s modernization agenda is advanced relative to Kazakhstani '
            'peers, with strong digitalization of mining operations. Key remaining '
            'opportunities include on-site renewable power generation for mine sites '
            '(reducing grid-sourced coal power consumption), water footprint reduction, '
            'and TCFD-aligned climate scenario analysis.'
        ),
        'ai_investment_opportunity': (
            'Kazatomprom is one of the few Kazakhstani companies that can access '
            'international green finance markets without structural reform. ESG '
            'investors focused on nuclear as a transition fuel are an active and '
            'growing market. A sustainability-linked bond tied to water and emissions '
            'KPIs would be highly competitive.'
        ),
        'ai_risk_notes': (
            'Radioactive waste management and legacy site remediation remain the most '
            'material environmental risks. Community engagement in remote mining '
            'regions is limited. Anti-corruption scores, while better than peers, '
            'still lag behind international mining company benchmarks.'
        ),
        'ai_recommendations': [
            'Publish a TCFD-aligned climate risk report aligned with nuclear sector taxonomy',
            'Develop a water stewardship plan for all in-situ leach operations',
            'Issue a Sustainability-Linked Bond with water intensity KPIs',
            'Increase community investment in South Kazakhstan mining communities by 30%',
            'Achieve ISO 14001 certification for all operational sites',
        ],
        'ecoiq_manual': 63.2,
    },

    # ────────────────────────────────────────────────────────────────────────
    # 5. KEGOC
    # ────────────────────────────────────────────────────────────────────────
    {
        'name':    'KEGOC',
        'slug':    'kegoc',
        'sector':  'energy',
        'country': 'Kazakhstan',
        'description': (
            'KEGOC (Kazakhstan Electricity Grid Operating Company) is the national '
            'electricity transmission system operator. It manages Kazakhstan\'s unified '
            'national power grid, connecting 17 regions and enabling cross-border '
            'electricity trade. KEGOC is partially listed on the Astana International '
            'Exchange and plays a pivotal role in enabling Kazakhstan\'s renewable '
            'energy integration.'
        ),
        'website': 'https://www.kegoc.kz',
        'annual_revenue_usd': 850_000_000,
        'employee_count': 8500,
        'pollution_level': 'low',
        'estimated_emissions': 120_000,
        'renewable_energy_share': 20.0,
        'waste_management_score': 68.0,
        'water_impact_score': 72.0,
        'biodiversity_impact_score': 65.0,
        'jobs_created_score': 70.0,
        'regional_development_score': 75.0,
        'infrastructure_contribution_score': 90.0,
        'national_value_score': 88.0,
        'energy_transition_score': 65.0,
        'digitalization_score': 62.0,
        'infrastructure_upgrade_score': 60.0,
        'future_readiness_score': 65.0,
        'transparency_score_detail': 65.0,
        'audit_quality_score': 68.0,
        'procurement_transparency_score': 60.0,
        'anti_corruption_score': 58.0,
        'controversy_risk_score': 20.0,
        'profit_extraction_score': 42.0,
        'profit_extraction_risk_score': 25.0,
        'ownership_type': 'mixed',
        'state_owned_percentage': 90.0,
        'funding_status': 'open_to_funding',
        'investor_visibility': True,
        'modernization_projects': [
            'Smart grid digital transformation',
            'Kazakhstan-China energy export corridor',
            'HVDC interconnection with Central Asian neighbours',
        ],
        'modernization_investment': 280_000_000,
        'ai_summary': (
            'KEGOC is Kazakhstan\'s most critical enabling infrastructure company '
            'for the energy transition. With an EcoIQ score of 66.8, it leads its '
            'sector peer group on environmental performance (low direct emissions) '
            'and national value. The company\'s ability to integrate renewable '
            'energy into the grid at scale makes it a foundational asset for '
            'Kazakhstan\'s carbon neutrality pathway.'
        ),
        'ai_modernization_report': (
            'KEGOC\'s modernization priority is smart grid deployment and cross-border '
            'interconnection — both critical for scaling renewable integration. Current '
            'grid infrastructure bottlenecks limit wind and solar absorption to 15-20% '
            'of capacity without curtailment. A $500M smart grid investment programme '
            'would unlock 3x more renewable capacity and position Kazakhstan as '
            'a Central Asian energy hub.'
        ),
        'ai_investment_opportunity': (
            'KEGOC\'s grid expansion aligns perfectly with AIIB, EBRD, and ADB '
            'infrastructure lending priorities. A green bond for the Kazakhstan-China '
            'energy export corridor would attract Asian institutional investors. '
            'The company\'s partial AIX listing provides market access for '
            'ESG-aligned equity investors.'
        ),
        'ai_risk_notes': (
            'Ageing grid infrastructure in rural regions creates reliability risks. '
            'Procurement transparency for capital projects has not been independently '
            'verified. Progress on smart grid deployment has been slower than '
            'announced timelines suggest.'
        ),
        'ai_recommendations': [
            'Develop a 10-year smart grid investment plan with public milestones',
            'Issue a Green Bond for renewable integration infrastructure',
            'Publish transmission loss rates and reliability KPIs annually',
            'Implement open-data API for grid monitoring data',
            'Partner with European TSOs on best practice for renewable integration',
        ],
        'ecoiq_manual': 66.8,
    },

    # ────────────────────────────────────────────────────────────────────────
    # 6. Air Astana
    # ────────────────────────────────────────────────────────────────────────
    {
        'name':    'Air Astana',
        'slug':    'air-astana',
        'sector':  'transport',
        'country': 'Kazakhstan',
        'description': (
            'Air Astana is Kazakhstan\'s national flag carrier and the largest airline '
            'in Central Asia. It operates a modern fleet of Airbus and Boeing aircraft '
            'serving 70+ destinations across Europe, Asia, the Middle East, and the CIS. '
            'Air Astana has one of the youngest fleets in the region and maintains '
            'a IATA Operational Safety Audit (IOSA) certification.'
        ),
        'website': 'https://www.airastana.com',
        'annual_revenue_usd': 1_100_000_000,
        'employee_count': 5500,
        'pollution_level': 'medium',
        'estimated_emissions': 3_200_000,
        'renewable_energy_share': 2.0,
        'waste_management_score': 58.0,
        'water_impact_score': 65.0,
        'biodiversity_impact_score': 60.0,
        'jobs_created_score': 70.0,
        'regional_development_score': 72.0,
        'infrastructure_contribution_score': 78.0,
        'national_value_score': 80.0,
        'energy_transition_score': 35.0,
        'digitalization_score': 68.0,
        'infrastructure_upgrade_score': 65.0,
        'future_readiness_score': 60.0,
        'transparency_score_detail': 65.0,
        'audit_quality_score': 68.0,
        'procurement_transparency_score': 60.0,
        'anti_corruption_score': 62.0,
        'controversy_risk_score': 18.0,
        'profit_extraction_score': 48.0,
        'profit_extraction_risk_score': 30.0,
        'ownership_type': 'mixed',
        'state_owned_percentage': 51.0,
        'funding_status': 'not_seeking',
        'investor_visibility': False,
        'modernization_projects': [
            'Fleet transition to Airbus A321neo',
            'SAF (Sustainable Aviation Fuel) procurement trials',
            'Digital passenger experience platform',
        ],
        'modernization_investment': 80_000_000,
        'ai_summary': (
            'Air Astana is Central Asia\'s most operationally mature airline and '
            'a strong performer on governance and transparency relative to regional '
            'peers. Its EcoIQ score of 62.4 reflects solid public benefit generation '
            'and modernization progress, constrained by aviation\'s inherent carbon '
            'intensity. The company\'s modern fleet gives it a structural advantage '
            'for SAF adoption and eventual hydrogen aviation integration.'
        ),
        'ai_modernization_report': (
            'Air Astana\'s pathway to lower emissions is clearer than most aviation '
            'peers: accelerate A321neo fleet delivery (reducing fuel burn 20% vs '
            'A320ceo), establish a SAF blending commitment (10% by 2030), and offset '
            'residual emissions via high-quality carbon credits. The CORSIA framework '
            'already mandates offsetting — proactive compliance demonstrates leadership.'
        ),
        'ai_investment_opportunity': (
            'Air Astana\'s partial private ownership and IOSA certification make it '
            'an accessible ESG investment vehicle for aviation-focused funds. A '
            'sustainability-linked loan tied to fuel efficiency and SAF adoption '
            'KPIs would attract green finance at reduced cost of capital.'
        ),
        'ai_risk_notes': (
            'Aviation emissions are inherently difficult to reduce at pace, exposing '
            'the company to increasing ESG scrutiny. Sustainability reporting lacks '
            'TCFD climate risk analysis. No public commitment to net-zero aviation exists.'
        ),
        'ai_recommendations': [
            'Publish a Net Zero 2050 commitment for aviation operations',
            'Establish a SAF procurement target (10% by 2030)',
            'Issue annual Scope 1 and 2 emissions report aligned with IATA standards',
            'Develop TCFD-aligned climate risk disclosure',
            'Launch a passenger carbon offset programme with Gold Standard credits',
        ],
        'ecoiq_manual': 62.4,
    },

    # ────────────────────────────────────────────────────────────────────────
    # 7. Kaspi.kz
    # ────────────────────────────────────────────────────────────────────────
    {
        'name':    'Kaspi.kz',
        'slug':    'kaspi-kz',
        'sector':  'other',
        'country': 'Kazakhstan',
        'description': (
            'Kaspi.kz is Kazakhstan\'s leading technology and financial services '
            'platform, combining a super-app ecosystem with payments, marketplace, '
            'and fintech services for 14 million monthly active users. Listed on '
            'NASDAQ and the London Stock Exchange, Kaspi.kz is Central Asia\'s most '
            'internationally visible and highly valued technology company.'
        ),
        'website': 'https://www.kaspi.kz',
        'annual_revenue_usd': 3_500_000_000,
        'employee_count': 25000,
        'pollution_level': 'low',
        'estimated_emissions': 85_000,
        'renewable_energy_share': 25.0,
        'waste_management_score': 75.0,
        'water_impact_score': 80.0,
        'biodiversity_impact_score': 78.0,
        'jobs_created_score': 80.0,
        'regional_development_score': 75.0,
        'infrastructure_contribution_score': 82.0,
        'national_value_score': 88.0,
        'energy_transition_score': 65.0,
        'digitalization_score': 92.0,
        'infrastructure_upgrade_score': 85.0,
        'future_readiness_score': 88.0,
        'transparency_score_detail': 75.0,
        'audit_quality_score': 80.0,
        'procurement_transparency_score': 70.0,
        'anti_corruption_score': 72.0,
        'controversy_risk_score': 22.0,
        'profit_extraction_score': 55.0,
        'profit_extraction_risk_score': 28.0,
        'ownership_type': 'public_listed',
        'state_owned_percentage': 0.0,
        'funding_status': 'not_seeking',
        'investor_visibility': True,
        'modernization_projects': [
            'Green data center efficiency programme',
            'Financial inclusion for underbanked rural communities',
            'Paperless banking and e-government integration',
        ],
        'modernization_investment': 120_000_000,
        'ai_summary': (
            'Kaspi.kz is Kazakhstan\'s most advanced company on EcoIQ dimensions '
            'with a score of 74.5, driven by exceptional digitalization, strong '
            'governance linked to NASDAQ listing requirements, and low direct emissions. '
            'The company\'s financial inclusion mission gives it a credible public '
            'benefit narrative. As a tech platform, it holds a responsibility to '
            'deploy capital toward green finance products and SME sustainability '
            'lending.'
        ),
        'ai_modernization_report': (
            'Kaspi\'s modernization position is already strong in digital infrastructure. '
            'The next frontier is deploying its platform power for sustainability impact: '
            'green SME loans, sustainable supply chain financing for marketplace sellers, '
            'and carbon footprint tracking for consumers. These initiatives would elevate '
            'Kaspi from EcoIQ-neutral tech company to a positive-impact platform leader.'
        ),
        'ai_investment_opportunity': (
            'Kaspi.kz is already attractive to international ESG equity investors via '
            'its NASDAQ and LSE listings. The opportunity is sustainability-linked debt '
            'tied to financial inclusion metrics and green product volume, which '
            'would expand the ESG investor base to fixed-income mandates.'
        ),
        'ai_risk_notes': (
            'Despite strong governance, Kaspi\'s ESG reporting does not yet include '
            'supply chain emissions (Scope 3) or formal TCFD disclosure. High profit '
            'margins relative to regional development investment suggest an opportunity '
            'to strengthen the public benefit reinvestment narrative.'
        ),
        'ai_recommendations': [
            'Launch a Green SME Loan product with preferential rates for energy-efficient businesses',
            'Publish Scope 1, 2, and 3 emissions with TCFD climate risk analysis',
            'Commit 1% of net profit annually to digital financial inclusion in rural Kazakhstan',
            'Develop a consumer carbon footprint tracking feature in the Kaspi app',
            'Issue a Social Bond linked to financial inclusion KPIs',
        ],
        'ecoiq_manual': 74.5,
    },

    # ────────────────────────────────────────────────────────────────────────
    # 8. Halyk Bank
    # ────────────────────────────────────────────────────────────────────────
    {
        'name':    'Halyk Bank',
        'slug':    'halyk-bank',
        'sector':  'other',
        'country': 'Kazakhstan',
        'description': (
            'Halyk Bank is Kazakhstan\'s largest bank by assets and the market leader '
            'in retail banking, SME lending, and digital financial services. Listed on '
            'the Astana International Exchange and the London Stock Exchange, Halyk '
            'Bank serves over 10 million customers and holds approximately 35% of '
            'Kazakhstan\'s banking system deposits.'
        ),
        'website': 'https://www.halykbank.kz',
        'annual_revenue_usd': 2_100_000_000,
        'employee_count': 18000,
        'pollution_level': 'low',
        'estimated_emissions': 65_000,
        'renewable_energy_share': 18.0,
        'waste_management_score': 70.0,
        'water_impact_score': 75.0,
        'biodiversity_impact_score': 72.0,
        'jobs_created_score': 72.0,
        'regional_development_score': 70.0,
        'infrastructure_contribution_score': 75.0,
        'national_value_score': 78.0,
        'energy_transition_score': 48.0,
        'digitalization_score': 72.0,
        'infrastructure_upgrade_score': 68.0,
        'future_readiness_score': 65.0,
        'transparency_score_detail': 65.0,
        'audit_quality_score': 70.0,
        'procurement_transparency_score': 62.0,
        'anti_corruption_score': 65.0,
        'controversy_risk_score': 25.0,
        'profit_extraction_score': 60.0,
        'profit_extraction_risk_score': 38.0,
        'ownership_type': 'public_listed',
        'state_owned_percentage': 0.0,
        'funding_status': 'not_seeking',
        'investor_visibility': True,
        'modernization_projects': [
            'Green lending programme for energy-efficient homes',
            'Paperless branch transformation',
            'Open banking API ecosystem',
        ],
        'modernization_investment': 85_000_000,
        'ai_summary': (
            'Halyk Bank earns an EcoIQ score of 67.8, reflecting its strong governance '
            'linked to international listing requirements and relatively low direct '
            'environmental impact as a financial institution. The key EcoIQ opportunity '
            'for Halyk is not in its own operations but in its lending book — '
            'systematically deploying capital toward green mortgages, ESG-screened '
            'corporate loans, and climate-aligned SME financing.'
        ),
        'ai_modernization_report': (
            'Halyk Bank\'s digital transformation is well advanced, with mobile banking '
            'penetration exceeding 80% of the retail base. The modernization gap is '
            'in sustainable finance product development. A dedicated ESG lending policy, '
            'green mortgage product, and exclusion list for coal-related lending would '
            'materially improve Halyk\'s EcoIQ score and attract European institutional '
            'shareholders.'
        ),
        'ai_investment_opportunity': (
            'Halyk Bank is well-positioned to issue a Green or Social Bond tied to '
            'its lending activities in energy efficiency, green mortgages, and women-led '
            'SME financing. European debt investors with ESG mandates are actively '
            'seeking such instruments from Central Asian financial institutions.'
        ),
        'ai_risk_notes': (
            'Halyk\'s ESG reporting does not yet include financed emissions (Scope 3) '
            'analysis, which is becoming standard for major banks globally. Concentration '
            'of lending to large extractive sector companies creates transition risk '
            'exposure that is not yet formally assessed or disclosed.'
        ),
        'ai_recommendations': [
            'Publish financed emissions analysis aligned with PCAF methodology',
            'Launch a Green Mortgage product for energy-efficient home construction',
            'Develop and publish an ESG lending policy with coal exclusion criteria',
            'Issue a Social Bond tied to SME lending and financial inclusion KPIs',
            'Establish an independent ESG committee with board-level reporting',
        ],
        'ecoiq_manual': 67.8,
    },

    # ────────────────────────────────────────────────────────────────────────
    # 9. BI Group
    # ────────────────────────────────────────────────────────────────────────
    {
        'name':    'BI Group',
        'slug':    'bi-group',
        'sector':  'other',
        'country': 'Kazakhstan',
        'description': (
            'BI Group is Kazakhstan\'s largest construction and real estate development '
            'company. The group constructs residential complexes, commercial properties, '
            'infrastructure facilities, and industrial buildings. It has delivered over '
            '10 million square metres of floor space in Kazakhstan and is expanding '
            'operations to Uzbekistan, Georgia, and Turkey.'
        ),
        'website': 'https://bi.group',
        'annual_revenue_usd': 1_800_000_000,
        'employee_count': 32000,
        'pollution_level': 'medium',
        'estimated_emissions': 2_100_000,
        'renewable_energy_share': 8.0,
        'waste_management_score': 48.0,
        'water_impact_score': 52.0,
        'biodiversity_impact_score': 45.0,
        'jobs_created_score': 78.0,
        'regional_development_score': 80.0,
        'infrastructure_contribution_score': 85.0,
        'national_value_score': 75.0,
        'energy_transition_score': 45.0,
        'digitalization_score': 55.0,
        'infrastructure_upgrade_score': 60.0,
        'future_readiness_score': 52.0,
        'transparency_score_detail': 42.0,
        'audit_quality_score': 48.0,
        'procurement_transparency_score': 40.0,
        'anti_corruption_score': 40.0,
        'controversy_risk_score': 45.0,
        'profit_extraction_score': 62.0,
        'profit_extraction_risk_score': 48.0,
        'ownership_type': 'private',
        'state_owned_percentage': 0.0,
        'funding_status': 'open_to_funding',
        'investor_visibility': False,
        'modernization_projects': [
            'Energy-efficient building programme (BREEAM standard)',
            'Construction waste recycling system',
            'Modular construction technology pilot',
        ],
        'modernization_investment': 65_000_000,
        'ai_summary': (
            'BI Group earns an EcoIQ score of 55.8, reflecting its strong regional '
            'development role and employment generation, offset by limited transparency '
            'and moderate environmental performance in construction operations. The '
            'company\'s scale — 32,000 employees and major infrastructure pipeline — '
            'gives it an outsized opportunity to raise the sustainability standard '
            'for Kazakhstani construction.'
        ),
        'ai_modernization_report': (
            'BI Group\'s modernization opportunity lies in green building standards, '
            'construction waste reduction, and supply chain emissions management. '
            'Adopting BREEAM or LEED certification as a company standard (rather than '
            'optional) for new residential developments would position BI Group '
            'as Central Asia\'s first sustainability-certified construction major.'
        ),
        'ai_investment_opportunity': (
            'Kazakhstan\'s growing middle class and housing deficit create strong '
            'fundamentals for ESG-aligned residential construction financing. A '
            'green mortgage product partnership with Halyk Bank or a DFI-backed '
            'affordable green housing programme would attract both capital and '
            'regulatory favour.'
        ),
        'ai_risk_notes': (
            'Procurement transparency is a material concern for a company this size. '
            'Limited public disclosure on subcontractor standards creates supply chain '
            'governance risk. No independent environmental monitoring of construction '
            'site operations has been disclosed.'
        ),
        'ai_recommendations': [
            'Adopt BREEAM GOOD as minimum standard for all new residential developments',
            'Publish annual construction waste data and reduction targets',
            'Implement open procurement platform for contracts >$1M',
            'Develop a supply chain code of conduct with environmental standards',
            'Issue a Green Bond for energy-efficient affordable housing developments',
        ],
        'ecoiq_manual': 55.8,
    },

    # ────────────────────────────────────────────────────────────────────────
    # 10. Qarmet (formerly ArcelorMittal Temirtau)
    # ────────────────────────────────────────────────────────────────────────
    {
        'name':    'Qarmet',
        'slug':    'qarmet',
        'sector':  'metallurgy',
        'country': 'Kazakhstan',
        'description': (
            'Qarmet (formerly ArcelorMittal Temirtau) is Kazakhstan\'s largest steel '
            'producer and one of the largest integrated steel and coal mining operations '
            'in Central Asia. The plant in Temirtau has operated since the Soviet era '
            'and employs approximately 25,000 workers in Kazakhstan\'s Karaganda region. '
            'The company was acquired by new investors in 2023 following a period of '
            'severe worker safety and environmental controversy.'
        ),
        'website': 'https://www.qarmet.kz',
        'annual_revenue_usd': 2_500_000_000,
        'employee_count': 25000,
        'pollution_level': 'severe',
        'estimated_emissions': 22_000_000,
        'renewable_energy_share': 1.0,
        'waste_management_score': 22.0,
        'water_impact_score': 28.0,
        'biodiversity_impact_score': 20.0,
        'jobs_created_score': 72.0,
        'regional_development_score': 65.0,
        'infrastructure_contribution_score': 70.0,
        'national_value_score': 65.0,
        'energy_transition_score': 28.0,
        'digitalization_score': 35.0,
        'infrastructure_upgrade_score': 30.0,
        'future_readiness_score': 28.0,
        'transparency_score_detail': 30.0,
        'audit_quality_score': 35.0,
        'procurement_transparency_score': 28.0,
        'anti_corruption_score': 30.0,
        'controversy_risk_score': 78.0,
        'profit_extraction_score': 75.0,
        'profit_extraction_risk_score': 80.0,
        'ownership_type': 'private',
        'state_owned_percentage': 0.0,
        'funding_status': 'seeking_partners',
        'funding_needed': 3_000_000_000,
        'investor_visibility': False,
        'modernization_projects': [
            'Blast furnace emission control upgrade',
            'Worker safety investment programme',
            'Water treatment plant renewal',
        ],
        'modernization_investment': 200_000_000,
        'ai_summary': (
            'Qarmet presents the most acute EcoIQ challenge in Kazakhstan with a score '
            'of 37.2 — classified as Profit-First Operator due to severe pollution '
            'levels, limited transparency, and high controversy risk following '
            'documented worker safety incidents. The company\'s new ownership provides '
            'a critical window of opportunity to execute a credible modernization '
            'commitment before further regulatory and reputational pressure materializes.'
        ),
        'ai_modernization_report': (
            'The Temirtau steelworks requires a comprehensive, phased modernization '
            'programme estimated at $3B over 10 years. Priority interventions include: '
            '(1) blast furnace emissions control upgrade within 24 months; '
            '(2) coking plant SO2 scrubber installation; '
            '(3) electric arc furnace feasibility study for partial DRI transition. '
            'Without visible modernization commitment, Kazakhstan\'s government has '
            'signalled it will enforce existing environmental regulations more strictly.'
        ),
        'ai_investment_opportunity': (
            'Qarmet represents a high-risk, high-impact transition finance candidate. '
            'EBRD has demonstrated appetite for steel sector transition investments '
            'where a credible plan and government commitment are present. A structured '
            'package combining DFI loans, carbon credits from emissions reduction, '
            'and government support for just transition of the Karaganda workforce '
            'could be constructed with the right advisory support.'
        ),
        'ai_risk_notes': (
            'Material risks: worker safety incidents, documented environmental violations, '
            'coke oven and blast furnace PM2.5 and SO2 emissions at levels exceeding EU '
            'standards by 3-5x, limited independent monitoring, and low governance '
            'transparency. Investor engagement will require a signed modernization '
            'agreement with government before any capital commitment.'
        ),
        'ai_recommendations': [
            'Publish a binding 5-year modernization plan signed by new ownership and government',
            'Install continuous emissions monitoring (CEMS) on all major stacks within 18 months',
            'Achieve IFC Performance Standards compliance as prerequisite for any DFI financing',
            'Engage EBRD for a pre-accession due diligence assessment',
            'Commission independent worker safety audit and publish findings publicly',
        ],
        'ecoiq_manual': 37.2,
    },
]


class Command(BaseCommand):
    help = 'Seed 10 major Kazakhstani companies as public EcoIQ profiles'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help='Delete existing seeded profiles before seeding')

    def handle(self, *args, **options):
        from league.models import Company
        from companies.models import CompanyProfile
        from companies.scoring import recalculate_and_save

        if options['clear']:
            slugs = [d['slug'] for d in SEED_DATA]
            deleted, _ = CompanyProfile.objects.filter(
                company__slug__in=slugs
            ).delete()
            self.stdout.write(self.style.WARNING(f'Deleted {deleted} existing profiles'))

        created_co = 0
        created_pr = 0
        updated    = 0

        for data in SEED_DATA:
            ecoiq_manual = data.pop('ecoiq_manual', None)

            # Separate league.Company fields from CompanyProfile fields
            co_fields = {
                'name':              data['name'],
                'sector':            data.get('sector', 'other'),
                'country':           data.get('country', 'Kazakhstan'),
                'description':       data.get('description', ''),
                'website':           data.get('website', ''),
                'logo_url':          data.get('logo_url', ''),
                'employee_count':    data.get('employee_count'),
                'annual_revenue_usd':data.get('annual_revenue_usd'),
            }

            profile_fields = {k: v for k, v in data.items()
                              if k not in co_fields and k not in ('name', 'slug', 'sector',
                              'country', 'description', 'website', 'logo_url',
                              'employee_count', 'annual_revenue_usd')}

            with transaction.atomic():
                # Create or update league.Company
                company, co_new = Company.objects.update_or_create(
                    slug=data['slug'],
                    defaults=co_fields,
                )
                if co_new:
                    created_co += 1

                # Create or update CompanyProfile
                profile, pr_new = CompanyProfile.objects.update_or_create(
                    company=company,
                    defaults={
                        'status': 'public',
                        'subscription_tier': 'free',
                        'is_verified': False,
                        **profile_fields,
                    },
                )
                if pr_new:
                    created_pr += 1
                else:
                    updated += 1

                # Recalculate EcoIQ scores from the individual component scores
                recalculate_and_save(profile)

                self.stdout.write(
                    f'  {"✓ Created" if pr_new else "↻ Updated"}: '
                    f'{company.name} — EcoIQ {profile.ecoiq_total_score:.1f} '
                    f'({profile.moral_label_display})'
                )

        self.stdout.write(self.style.SUCCESS(
            f'\nSeed complete: {created_co} companies created, '
            f'{created_pr} profiles created, {updated} profiles updated.'
        ))
