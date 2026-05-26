"""
Management command: seed_phase2_companies

Seeds 8 Phase 2 global companies:
  NVIDIA, Siemens, Samsung Electronics, CATL, BYD,
  EDF, Schneider Electric, Ørsted

Safe to re-run: uses update_or_create (idempotent).

Usage:
    python manage.py seed_phase2_companies
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from league.models import Company
from companies.models import CompanyProfile, CompanyGuidanceVideo
from companies.scoring import recalculate_and_save

DISCLAIMER = (
    "Indicative EcoIQ analysis based on publicly available information. "
    "All scores are estimated and require independent verification. "
    "This profile has not been verified or endorsed by the company."
)

SEED_DATA = [

    # ── NVIDIA ───────────────────────────────────────────────────────────────────
    {
        'name': 'NVIDIA', 'slug': 'nvidia', 'sector': 'other',
        'country': 'United States', 'city': 'Santa Clara, CA',
        'description': 'NVIDIA designs graphics processing units (GPUs) and system-on-chip units for gaming, professional visualisation, and AI computing. It is the primary infrastructure provider for modern AI model training and inference.',
        'website': 'https://nvidia.com',
        'employee_count': 29600, 'annual_revenue_usd': 60922000000, 'is_public': True,
        'score_pollution_footprint': 78, 'score_reduction_progress': 70,
        'score_investment': 72, 'score_transparency': 76, 'score_community_impact': 68,
        'ownership_type': 'public_listed', 'funding_status': 'not_seeking',
        'pollution_level': 'medium',
        'estimated_emissions': 3200000,
        'renewable_energy_share': 62.0,
        'jobs_created_score': 68.0, 'regional_development_score': 60.0,
        'infrastructure_contribution_score': 72.0, 'national_value_score': 74.0,
        'waste_management_score': 60.0, 'water_impact_score': 56.0, 'biodiversity_impact_score': 55.0,
        'energy_transition_score': 72.0, 'digitalization_score': 96.0,
        'infrastructure_upgrade_score': 88.0, 'future_readiness_score': 92.0,
        'transparency_score_detail': 72.0, 'audit_quality_score': 70.0,
        'procurement_transparency_score': 68.0, 'anti_corruption_score': 74.0,
        'controversy_risk_score': 30.0,
        'profit_extraction_risk_score': 48.0, 'profit_extraction_score': 48.0,
        'modernization_projects': [
            'Blackwell GPU Architecture for AI', 'GeForce NOW Cloud Gaming',
            'NVIDIA DGX Cloud — AI Supercomputing', 'Energy-Efficient AI Chip R&D',
        ],
        'ai_summary': (
            f"NVIDIA Corporation is the world's dominant provider of graphics processing units and "
            f"AI computing infrastructure. Publicly available data indicates annual revenues exceeding "
            f"$60 billion, driven primarily by data centre AI chip demand from hyperscale cloud providers "
            f"and AI companies. NVIDIA's H100 and Blackwell GPU architectures are foundational to "
            f"the global AI training and inference supply chain. {DISCLAIMER}"
        ),
        'ai_modernization_report': (
            "NVIDIA's digitalization and future readiness scores are among the highest in EcoIQ's "
            "global dataset. Its GPU architecture is central to the industrial AI transition — "
            "enabling energy optimisation, predictive maintenance, and autonomous systems across "
            "heavy industry. However, the energy consumption of AI training at scale represents a "
            "significant indirect environmental impact that NVIDIA's supply chain scores do not yet "
            "fully capture. Renewable energy procurement for owned facilities has increased but "
            "Scope 3 downstream energy use (customers running AI on NVIDIA chips) remains untracked."
        ),
        'ai_investment_opportunity': (
            "NVIDIA presents a compelling ethical investment case for investors who view AI "
            "infrastructure as essential to industrial decarbonisation. Its chips power climate "
            "modelling, grid optimisation, and clean energy R&D alongside more energy-intensive "
            "generative AI applications. Green bond potential exists for R&D programmes explicitly "
            "targeting energy-efficient AI architectures (e.g. sub-1W inference chips)."
        ),
        'ai_risk_notes': (
            "Key risks: (1) AI energy consumption narrative — NVIDIA's products enable energy-intensive "
            "applications whose aggregate environmental impact is significant and not yet publicly "
            "reported; (2) Concentration risk — 70%+ GPU market share creates systemic dependence; "
            "(3) Supply chain — TSMC manufacturing in Taiwan carries geopolitical and water risk; "
            "(4) Profit extraction concern — extraordinarily high margins with limited community "
            "benefit investment relative to profitability scale."
        ),
        'ai_recommendations': [
            'Publish GPU energy efficiency roadmap with measurable targets',
            'Report on Scope 3 downstream AI energy use from top 50 customers',
            'Commit $1bn to AI-for-climate research infrastructure',
            'Expand community benefit investment relative to $60bn+ revenue base',
            'Publish independent audit of TSMC supply chain environmental impact',
        ],
        'video_title': 'NVIDIA: The AI Chip Powering the Transition — EcoIQ Analysis',
        'video_executive_summary': (
            "NVIDIA's extraordinary AI infrastructure leadership gives it unique leverage to "
            "accelerate industrial decarbonisation. Its EcoIQ score of 73 reflects genuine "
            "innovation leadership tempered by accountability gaps in downstream energy use."
        ),
        'video_script': (
            "NVIDIA, you have built something the world has never seen before. The GPU that "
            "once powered video games now powers the artificial intelligence that is redesigning "
            "entire industries. Your EcoIQ score of 73 places you firmly in the Responsible "
            "Builder category — strong on innovation, strong on transparency, but with a gap "
            "that only you can close. That gap is energy. Every H100 chip you ship will be run "
            "by customers who collectively consume more electricity than some countries. You "
            "cannot control what they build — but you can lead on how efficiently they build it. "
            "An NVIDIA committed to publishing the energy efficiency trajectory of every chip "
            "architecture, every year, alongside an AI-for-climate research commitment — that "
            "is the NVIDIA that earns a score of 90 or above. The technology to power the "
            "transition already lives in your data centres. The question is whether the "
            "accountability will match the ambition."
        ),
        'video_higgsfield': (
            "Opening shot: extreme close-up of GPU chip under microscope lighting — circuit "
            "pathways glowing electric blue. Slow pull-back reveals the chip on a circuit board, "
            "then within a server rack, then within a vast data centre. Overlay: abstract AI "
            "neural network pulsing with light. Cut to aerial shots of a wind farm and solar "
            "array, with data lines visually connecting to the GPU. Montage: AI-powered grid "
            "optimisation, climate modelling simulations, autonomous industrial robots. "
            "Colour palette: deep black, electric blue, silver-white, with green energy "
            "pulses. Tone: technically precise, forward-looking, intelligent power."
        ),
        'video_actions': [
            'Publish annual GPU energy efficiency roadmap',
            'Report Scope 3 downstream AI energy use',
            'Commit to AI-for-climate research programme',
            'Scale community benefit investment',
            'Independent audit of supply chain environmental impact',
        ],
    },

    # ── Siemens ──────────────────────────────────────────────────────────────────
    {
        'name': 'Siemens', 'slug': 'siemens', 'sector': 'energy',
        'country': 'Germany', 'city': 'Munich',
        'description': 'Siemens is a global technology company focused on industry, infrastructure, mobility, and healthcare. It is a leader in industrial automation, smart grid solutions, digital twin technology, and sustainable infrastructure development.',
        'website': 'https://siemens.com',
        'employee_count': 320000, 'annual_revenue_usd': 77800000000, 'is_public': True,
        'score_pollution_footprint': 72, 'score_reduction_progress': 68,
        'score_investment': 75, 'score_transparency': 78, 'score_community_impact': 72,
        'ownership_type': 'public_listed', 'funding_status': 'open_to_funding',
        'pollution_level': 'low',
        'estimated_emissions': 2100000,
        'renewable_energy_share': 78.0,
        'jobs_created_score': 80.0, 'regional_development_score': 78.0,
        'infrastructure_contribution_score': 82.0, 'national_value_score': 80.0,
        'waste_management_score': 70.0, 'water_impact_score': 66.0, 'biodiversity_impact_score': 62.0,
        'energy_transition_score': 82.0, 'digitalization_score': 88.0,
        'infrastructure_upgrade_score': 85.0, 'future_readiness_score': 84.0,
        'transparency_score_detail': 80.0, 'audit_quality_score': 78.0,
        'procurement_transparency_score': 75.0, 'anti_corruption_score': 78.0,
        'controversy_risk_score': 28.0,
        'profit_extraction_risk_score': 32.0, 'profit_extraction_score': 32.0,
        'modernization_projects': [
            'DEGREE Sustainability Framework', 'Siemens Xcelerator Digital Platform',
            'Smart Infrastructure Grid Solutions', 'Siemens Energy Spin-off Integration',
            'Digital Factory Twin Technology',
        ],
        'ai_summary': (
            f"Siemens AG is one of the world's largest industrial technology companies, with "
            f"revenues exceeding €77 billion and operations in over 200 countries. It has "
            f"systematically transformed from a diversified conglomerate into a focused technology "
            f"company spanning automation, smart infrastructure, and healthcare. Siemens' DEGREE "
            f"sustainability framework commits to carbon neutrality by 2030 for its own operations. "
            f"{DISCLAIMER}"
        ),
        'ai_modernization_report': (
            "Siemens represents the German industrial transition archetype: converting legacy "
            "engineering excellence into digital infrastructure leadership. The Xcelerator platform "
            "and digital twin technology position it as the infrastructure layer for Industry 4.0 "
            "adoption globally. Siemens Energy (separately listed) handles the power generation "
            "transition portfolio. The company's transparency and governance scores are among "
            "the highest in EcoIQ's industrial sector dataset."
        ),
        'ai_investment_opportunity': (
            "Siemens offers a compelling transition infrastructure investment case. Its exposure "
            "to smart grid, industrial automation, building efficiency, and digital manufacturing "
            "places it at the intersection of every major industrial transition theme. "
            "Green bond issuance backed by smart infrastructure projects is a credible pathway. "
            "The DEGREE framework provides investor-grade accountability anchors."
        ),
        'ai_risk_notes': (
            "Key considerations: (1) Siemens Energy — its separately listed energy subsidiary "
            "carries wind turbine (Gamesa) quality and operational risk; (2) Geographical "
            "concentration in Germany creates exposure to Energiewende policy risk; "
            "(3) Competition from Chinese industrial automation players (ABB, Huawei Industrial) "
            "increasing; (4) Defence sector exposure (Siemens has defence-adjacent contracts) "
            "creates ESG screening complexity."
        ),
        'ai_recommendations': [
            'Publish full Scope 3 supply chain emissions by 2026',
            'Deepen community investment in regions of industrial legacy transformation',
            'Lead on AI-powered grid optimisation transparency standards',
            'Expand Xcelerator platform access for SME industrial partners',
            'Publish independent biodiversity impact assessment for facility locations',
        ],
        'video_title': 'Siemens: Engineering the Industrial Transition — EcoIQ Intelligence',
        'video_executive_summary': (
            "Siemens is EcoIQ's top-scoring industrial conglomerate — a Responsible Builder on the "
            "threshold of Regenerative Leader. Its combination of transparency, industrial modernization "
            "expertise, and DEGREE sustainability framework makes it the benchmark for industrial transition."
        ),
        'video_script': (
            "Siemens, you have spent 175 years building the infrastructure of industrial civilization. "
            "Now you are doing something harder — rebuilding it sustainably. Your EcoIQ score of 74 "
            "makes you the benchmark for industrial companies globally. Your digital twin technology "
            "is helping factories consume 30% less energy. Your smart grid solutions are enabling "
            "renewable integration across Europe. Your DEGREE framework is one of the most credible "
            "corporate sustainability architectures EcoIQ has analysed. The gap between 74 and 90 "
            "lies in three areas: deeper community investment in the industrial regions you helped "
            "build and are now helping transform, full Scope 3 supply chain transparency, and "
            "ensuring your energy subsidiary navigates the Gamesa wind turbine challenges without "
            "undermining your sustainability leadership. Siemens, the industrial transition needs "
            "exactly what you have built. Now it needs you to account for all of it."
        ),
        'video_higgsfield': (
            "Opening shot: factory floor with robotic arms moving precisely in choreography, "
            "overlaid with digital twin visualisation. Smooth transition to a smart grid control "
            "room — screens showing real-time energy flow optimisation. Cut to aerial view of "
            "a German city with Siemens infrastructure visible — trains, traffic systems, "
            "building automation. Close-up of engineer reviewing digital sustainability dashboard. "
            "Wide shot of offshore wind farm at sunset. Colour palette: Siemens teal, deep steel "
            "grey, warm amber, with data overlay in cool white. Tone: precise, trustworthy, "
            "confident industrial leadership."
        ),
        'video_actions': [
            'Publish Scope 3 supply chain emissions',
            'Deepen community investment in industrial regions',
            'Lead on AI grid optimisation transparency',
            'Expand Xcelerator for SME partners',
            'Biodiversity impact assessment for facilities',
        ],
    },

    # ── Samsung Electronics ──────────────────────────────────────────────────────
    {
        'name': 'Samsung Electronics', 'slug': 'samsung-electronics', 'sector': 'other',
        'country': 'South Korea', 'city': 'Suwon, Gyeonggi-do',
        'description': 'Samsung Electronics is one of the world\'s largest technology companies, producing semiconductors, consumer electronics, and IT solutions. It is the world\'s largest memory chip and smartphone manufacturer, and a critical node in the global technology supply chain.',
        'website': 'https://samsung.com',
        'employee_count': 270372, 'annual_revenue_usd': 200734000000, 'is_public': True,
        'score_pollution_footprint': 62, 'score_reduction_progress': 60,
        'score_investment': 66, 'score_transparency': 68, 'score_community_impact': 64,
        'ownership_type': 'public_listed', 'funding_status': 'not_seeking',
        'pollution_level': 'medium',
        'estimated_emissions': 12800000,
        'renewable_energy_share': 32.0,
        'jobs_created_score': 74.0, 'regional_development_score': 70.0,
        'infrastructure_contribution_score': 72.0, 'national_value_score': 78.0,
        'waste_management_score': 62.0, 'water_impact_score': 50.0, 'biodiversity_impact_score': 55.0,
        'energy_transition_score': 62.0, 'digitalization_score': 88.0,
        'infrastructure_upgrade_score': 80.0, 'future_readiness_score': 82.0,
        'transparency_score_detail': 68.0, 'audit_quality_score': 65.0,
        'procurement_transparency_score': 62.0, 'anti_corruption_score': 68.0,
        'controversy_risk_score': 42.0,
        'profit_extraction_risk_score': 42.0, 'profit_extraction_score': 42.0,
        'modernization_projects': [
            'RE100 Commitment by 2050', 'Samsung Green Factory Programme',
            '3nm Gate-All-Around Chip Process', 'EV Battery Chips (Exynos Auto)',
            'Water Recycling in Semiconductor Fabs',
        ],
        'ai_summary': (
            f"Samsung Electronics Co. Ltd is South Korea's largest company and one of the world's "
            f"most important technology manufacturers. Publicly available data indicates revenues "
            f"exceeding $200 billion, with major business units in semiconductors (DRAM, NAND flash, "
            f"logic chips), consumer electronics (TVs, appliances), and mobile devices. Samsung's "
            f"manufacturing footprint spans South Korea, Vietnam, India, and the US. {DISCLAIMER}"
        ),
        'ai_modernization_report': (
            "Samsung's semiconductor manufacturing is among the most technologically advanced in "
            "the world but also among the most energy and water-intensive. Chip fabs require "
            "ultra-pure water at massive volumes — a growing scarcity risk in South Korea's "
            "Gyeonggi-do manufacturing belt. Samsung's RE100 commitment (100% renewables by 2050) "
            "reflects ambition, but current renewable share (32%) indicates significant implementation "
            "work remains. The company's 3nm advanced process and EV-focused chip portfolio "
            "position it well in the clean technology supply chain."
        ),
        'ai_investment_opportunity': (
            "Samsung is a critical infrastructure node for the EV and clean energy transition — "
            "its DRAM and NAND chips are in every EV, smart grid controller, and renewable energy "
            "management system. Green bond potential exists for programmes targeting water recycling "
            "in semiconductor manufacturing and renewable energy procurement for Korean fabs. "
            "POSCO and Samsung collaboration on green steel for facility construction is an "
            "emerging transition investment theme."
        ),
        'ai_risk_notes': (
            "Key risks: (1) Water scarcity — semiconductor fabs use billions of litres of ultra-pure "
            "water; climate change threatens supply to Gyeonggi-do region; (2) Governance — "
            "Samsung Group's governance structure (Lee family holding company) remains a "
            "transparency concern for institutional ESG investors; (3) Labour practices — "
            "supply chain audit across Vietnam and India manufacturing remains incomplete; "
            "(4) RE100 gap — South Korea's coal-heavy grid makes renewable procurement structurally "
            "difficult without Power Purchase Agreements or green tariff frameworks."
        ),
        'ai_recommendations': [
            'Publish water consumption and recycling data by facility, annually',
            'Accelerate RE100: 60% renewable by 2030 (vs current 32%)',
            'Independent supply chain labour audit across Vietnam and India facilities',
            'Strengthen chaebol governance transparency for international investors',
            'Partner with POSCO for green steel in facility construction',
        ],
        'video_title': 'Samsung Electronics: The Supply Chain of the Clean Economy — EcoIQ',
        'video_executive_summary': (
            "Samsung sits at the heart of the global clean energy supply chain — its chips are in "
            "every EV battery management system and smart grid controller. Its EcoIQ score of 64 "
            "reflects solid governance and innovation, with water stewardship and renewable energy "
            "procurement as the clearest improvement pathways."
        ),
        'video_script': (
            "Samsung Electronics, you are inside every electric vehicle, every solar inverter, "
            "and every smart grid controller on Earth. The chips you make are the nervous system "
            "of the clean energy transition. Your EcoIQ score of 64 makes you a Public-Benefit "
            "Oriented company — solid governance, strong innovation, but with gaps that matter. "
            "The first is water. Your semiconductor fabs consume more clean water than some cities. "
            "As South Korea faces growing water stress, this is not just a sustainability issue — "
            "it is a business continuity risk. The second is energy. Your RE100 commitment is real, "
            "but 32% renewables today against a 2050 target tells a story of insufficient pace. "
            "The third is governance — your group structure is opaque to many international investors "
            "who want to allocate capital to your transition story. Close these gaps, and Samsung "
            "moves from a supply chain commodity to an ethical investment anchor in the clean economy."
        ),
        'video_higgsfield': (
            "Opening: extreme close-up of semiconductor wafer being processed — etching patterns "
            "in ultraviolet light. Pull back to cleanroom workers in protective suits. "
            "Cut to visualization of a chip inside an EV battery management system. "
            "Aerial shot of Samsung's Hwaseong manufacturing campus. "
            "Animation showing water cycle through semiconductor fab — intake, processing, recycling. "
            "Montage: Samsung chips in solar panels, smart grid monitors, wind turbine controls. "
            "Close-up of water droplet in clean room. Colour palette: crisp white, electric blue, "
            "Samsung navy, with green data overlays. Tone: precision, global infrastructure, responsible scale."
        ),
        'video_actions': [
            'Publish annual water consumption data by facility',
            'Accelerate RE100 to 60% by 2030',
            'Independent supply chain labour audit',
            'Strengthen chaebol governance transparency',
            'Lead on semiconductor water recycling innovation',
        ],
    },

    # ── CATL ─────────────────────────────────────────────────────────────────────
    {
        'name': 'CATL', 'slug': 'catl', 'sector': 'energy',
        'country': 'China', 'city': 'Ningde, Fujian',
        'description': 'Contemporary Amperex Technology Co. Limited (CATL) is the world\'s largest manufacturer of lithium-ion batteries for electric vehicles and energy storage systems. It supplies batteries to Tesla, BMW, Volkswagen, Ford, and virtually every major automaker globally.',
        'website': 'https://catl.com',
        'employee_count': 101000, 'annual_revenue_usd': 48670000000, 'is_public': True,
        'score_pollution_footprint': 68, 'score_reduction_progress': 72,
        'score_investment': 74, 'score_transparency': 66, 'score_community_impact': 70,
        'ownership_type': 'public_listed', 'funding_status': 'seeking_partners',
        'pollution_level': 'medium',
        'estimated_emissions': 8400000,
        'renewable_energy_share': 68.0,
        'jobs_created_score': 80.0, 'regional_development_score': 82.0,
        'infrastructure_contribution_score': 78.0, 'national_value_score': 82.0,
        'waste_management_score': 66.0, 'water_impact_score': 60.0, 'biodiversity_impact_score': 58.0,
        'energy_transition_score': 88.0, 'digitalization_score': 82.0,
        'infrastructure_upgrade_score': 84.0, 'future_readiness_score': 88.0,
        'transparency_score_detail': 64.0, 'audit_quality_score': 62.0,
        'procurement_transparency_score': 58.0, 'anti_corruption_score': 62.0,
        'controversy_risk_score': 35.0,
        'profit_extraction_risk_score': 36.0, 'profit_extraction_score': 36.0,
        'modernization_projects': [
            'Condensed Battery Technology (500Wh/kg)', 'Sodium-Ion Battery Commercialisation',
            'Zero-Carbon Manufacturing Pledge', 'European Gigafactory (Hungary)',
            'Battery Recycling (CATL Brunp)',
        ],
        'ai_summary': (
            f"Contemporary Amperex Technology Co. Limited (CATL) is the world's largest EV battery "
            f"manufacturer, with publicly reported revenues exceeding $48 billion and a global "
            f"market share estimated above 35%. CATL's batteries power vehicles from Tesla, BMW, "
            f"Volkswagen, Mercedes-Benz, Ford, and virtually every major EV manufacturer. "
            f"The company is rapidly internationalising with gigafactories in Germany (Erfurt) "
            f"and Hungary (Debrecen). {DISCLAIMER}"
        ),
        'ai_modernization_report': (
            "CATL is the backbone of the global EV supply chain and arguably the most important "
            "company in the industrial clean energy transition. Its condensed battery technology "
            "(500 Wh/kg) and sodium-ion battery programmes represent the cutting edge of "
            "energy storage innovation. CATL's zero-carbon manufacturing pledge and European "
            "factory expansion demonstrate strategic alignment with ethical investment criteria. "
            "Transparency and governance scores are constrained by China-listed company disclosure "
            "norms, which remain below European and US standards."
        ),
        'ai_investment_opportunity': (
            "CATL is the primary investment vehicle for EV battery supply chain exposure. "
            "Its European factory programme creates direct access for ESG-aligned capital "
            "in regulated investment environments. Battery recycling subsidiary (Brunp) "
            "represents a growing circular economy opportunity. "
            "Green bonds for gigafactory construction with certified renewable energy supply "
            "are a credible near-term issuance path."
        ),
        'ai_risk_notes': (
            "Key risks: (1) Cobalt supply chain — Democratic Republic of Congo sourcing "
            "creates human rights exposure despite CATL's Responsible Cobalt Initiative "
            "participation; (2) China geopolitical risk — trade tariffs and technology "
            "decoupling threatening European market access; (3) Transparency gap — "
            "financial and operational disclosure below international standards; "
            "(4) Battery fire and safety liability as market scale increases."
        ),
        'ai_recommendations': [
            'Publish independently audited cobalt supply chain due diligence report annually',
            'Accelerate European gigafactory renewable energy certification',
            'Improve financial disclosure to international institutional investment standards',
            'Expand CATL Brunp recycling to close-loop 95% material recovery by 2030',
            'Publish full lifecycle carbon analysis for each battery product line',
        ],
        'video_title': 'CATL: Powering the World\'s Clean Transport Revolution — EcoIQ',
        'video_executive_summary': (
            "CATL is the single most important company in the global EV battery transition. "
            "Its EcoIQ score of 73 reflects genuine innovation and regional development leadership, "
            "with cobalt supply chain transparency and governance disclosure as the critical "
            "improvement imperatives."
        ),
        'video_script': (
            "CATL, you have done something no company in history has done — you have built the "
            "battery that is ending the oil age. Every electric vehicle on every road, in every "
            "country, carries your technology or technology you inspired. Your EcoIQ score of 73 "
            "puts you firmly in Responsible Builder territory. Your regional development impact "
            "in Ningde is extraordinary — a city transformed by clean technology investment. "
            "Your European gigafactories are bringing the battery transition to the continent "
            "that needs it most. But your path to 90 runs through the Congo. Every cobalt "
            "atom in your batteries must be traceable, independently audited, and free from "
            "human rights compromise. No amount of battery innovation can offset supply chain "
            "harm — and EcoIQ will track this rigorously. The world needs your technology. "
            "Now it needs your supply chain accountability to match."
        ),
        'video_higgsfield': (
            "Opening shot: interior of a gigafactory at full production — battery cells moving "
            "on conveyor lines in organised sequences, workers in cleanroom suits. "
            "Aerial view of the Ningde coast and city — modern industrial development visible. "
            "Cut to an EV charging at a modern urban station, CATL battery indicator visible. "
            "Animation showing battery cell chemistry — lithium ions moving through electrode. "
            "Wide shot of cobalt mine transitioning to recycling facility — illustrating supply "
            "chain accountability narrative. Sunset over an ocean, EV ferry crossing. "
            "Colour palette: electric teal, deep industrial blue, silver, with warm amber "
            "accents. Tone: industrial scale, clean energy optimism, accountability gravitas."
        ),
        'video_actions': [
            'Annual independently audited cobalt supply chain report',
            'Renewable energy certification for all gigafactories',
            'International-standard financial disclosure',
            '95% material recovery in battery recycling by 2030',
            'Lifecycle carbon analysis per product line',
        ],
    },

    # ── BYD ──────────────────────────────────────────────────────────────────────
    {
        'name': 'BYD', 'slug': 'byd', 'sector': 'energy',
        'country': 'China', 'city': 'Shenzhen, Guangdong',
        'description': 'BYD Co. Ltd. is the world\'s largest manufacturer of electric vehicles and a major producer of rechargeable batteries, solar panels, and energy storage systems. It designs and manufactures its own batteries, electric drivetrains, and chips — a uniquely vertically integrated clean technology company.',
        'website': 'https://byd.com',
        'employee_count': 570000, 'annual_revenue_usd': 84977000000, 'is_public': True,
        'score_pollution_footprint': 74, 'score_reduction_progress': 78,
        'score_investment': 76, 'score_transparency': 64, 'score_community_impact': 78,
        'ownership_type': 'public_listed', 'funding_status': 'not_seeking',
        'pollution_level': 'low',
        'estimated_emissions': 9800000,
        'renewable_energy_share': 72.0,
        'jobs_created_score': 88.0, 'regional_development_score': 86.0,
        'infrastructure_contribution_score': 82.0, 'national_value_score': 84.0,
        'waste_management_score': 68.0, 'water_impact_score': 64.0, 'biodiversity_impact_score': 60.0,
        'energy_transition_score': 92.0, 'digitalization_score': 84.0,
        'infrastructure_upgrade_score': 86.0, 'future_readiness_score': 90.0,
        'transparency_score_detail': 62.0, 'audit_quality_score': 60.0,
        'procurement_transparency_score': 58.0, 'anti_corruption_score': 62.0,
        'controversy_risk_score': 32.0,
        'profit_extraction_risk_score': 30.0, 'profit_extraction_score': 30.0,
        'modernization_projects': [
            'Blade Battery Technology (LFP)', 'BYD Ocean / Dynasty Series EV Expansion',
            'BYD Electric Bus Global Deployment', 'Solar + Storage Integration',
            'BYD Fang Cheng Bao Luxury EV Brand',
        ],
        'ai_summary': (
            f"BYD Co. Ltd is the world's largest manufacturer of electric vehicles by volume, "
            f"having surpassed Tesla in global EV sales in 2023. With publicly reported revenues "
            f"exceeding $84 billion, BYD is a vertically integrated clean technology company "
            f"that designs its own batteries (Blade Battery), electric drivetrains, and "
            f"semiconductors. BYD also manufactures electric buses deployed in London, LA, "
            f"and dozens of other cities globally. {DISCLAIMER}"
        ),
        'ai_modernization_report': (
            "BYD represents the most dramatic industrial transformation in EcoIQ's global dataset. "
            "Founded as a battery manufacturer in 1995, it has become the world's largest EV company "
            "through vertical integration and ruthless cost discipline. The Blade Battery (LFP "
            "chemistry) has eliminated cobalt from its vehicles — a significant supply chain "
            "ethics improvement over competitors. BYD's electric bus programme has deployed "
            "carbon-free public transit in cities across six continents. Energy transition and "
            "future readiness scores (92 and 90) are among the highest in EcoIQ's database."
        ),
        'ai_investment_opportunity': (
            "BYD is the world's most direct investment vehicle for the EV mass-market transition. "
            "Its cobalt-free LFP battery chemistry, vertically integrated model, and global "
            "deployment scale create a defensible competitive moat. International expansion "
            "(Thailand, Brazil, Hungary factories) creates ESG-aligned manufacturing investment "
            "opportunities. Electric bus and commercial vehicle segments offer transition "
            "finance opportunities aligned with urban decarbonisation."
        ),
        'ai_risk_notes': (
            "Key risks: (1) Governance transparency — as a Chinese-listed company, BYD's "
            "disclosure standards remain below European and US norms; "
            "(2) Geopolitical trade risk — EU EV tariffs threatening European market access; "
            "(3) Water consumption in battery and chip manufacturing; "
            "(4) Labour practices across the 570,000-person manufacturing workforce require "
            "independent verification; (5) Rapid international expansion creating governance "
            "consistency challenges."
        ),
        'ai_recommendations': [
            'Publish independently audited labour standards report for all manufacturing facilities',
            'Strengthen financial disclosure to international ESG investment standards',
            'Publish water consumption and recycling data by facility',
            'Lead on EV battery end-of-life recycling programme globally',
            'Establish independent board oversight for international operations governance',
        ],
        'video_title': 'BYD: The Company Rewriting the Rules of Clean Transport — EcoIQ',
        'video_executive_summary': (
            "BYD is EcoIQ's highest-scoring Chinese company — a Responsible Builder with the "
            "largest clean vehicle manufacturing footprint in the world. Its path to Regenerative "
            "Leader runs through transparency and governance improvement."
        ),
        'video_script': (
            "BYD, you have done what many said was impossible. You took a battery company "
            "from a basement in Shenzhen and turned it into the world's largest electric vehicle "
            "manufacturer — without cobalt, without compromise on cost, and without losing sight "
            "of the mission. Your EcoIQ score of 78 places you among the most impactful "
            "companies on Earth. Your Blade Battery has eliminated cobalt from millions of "
            "vehicles. Your electric buses are carrying commuters in London, Los Angeles, and "
            "Bogotá on zero-emission journeys every day. Your employment impact — over 570,000 "
            "people — is one of the most significant job creation stories in the clean economy. "
            "Your path to 90 is not a technology challenge. It is a transparency challenge. "
            "International investors who want to allocate capital to your story need governance "
            "standards they trust. Labour audits they can verify. Financial disclosures that "
            "meet international norms. Build that transparency, and BYD becomes not just the "
            "world's largest EV company — it becomes the world's most fundable clean energy story."
        ),
        'video_higgsfield': (
            "Opening shot: BYD EV assembly line — robotic precision, Blade Battery modules "
            "being installed into vehicle frames. Cut to BYD electric bus navigating a city "
            "street at dusk, passengers visible through glass. Aerial view of Shenzhen skyline "
            "with BYD headquarters and manufacturing campus. Animation of Blade Battery internal "
            "structure — LFP cells arranged for safety and energy density. "
            "Montage: BYD buses in London, LA, Santiago — global deployment story. "
            "Final shot: BYD EV on open road at sunrise, clean and silent. "
            "Colour palette: BYD green, deep navy, silver-white, warm morning light. "
            "Tone: confident scale, clean energy pride, future-ready momentum."
        ),
        'video_actions': [
            'Independently audited labour standards across all facilities',
            'International-standard ESG financial disclosure',
            'Water consumption transparency by facility',
            'Global EV battery end-of-life recycling programme',
            'Independent governance for international operations',
        ],
    },

    # ── EDF ──────────────────────────────────────────────────────────────────────
    {
        'name': 'EDF', 'slug': 'edf', 'sector': 'energy',
        'country': 'France', 'city': 'Paris',
        'description': 'Électricité de France (EDF) is the world\'s largest nuclear power company and France\'s primary electricity utility. It operates 56 nuclear reactors in France and has significant renewable energy and grid operations across Europe.',
        'website': 'https://edf.fr',
        'employee_count': 180000, 'annual_revenue_usd': 143600000000, 'is_public': False,
        'score_pollution_footprint': 65, 'score_reduction_progress': 62,
        'score_investment': 68, 'score_transparency': 72, 'score_community_impact': 70,
        'ownership_type': 'state',
        'state_owned_percentage': 100.0,
        'funding_status': 'seeking_partners',
        'pollution_level': 'low',
        'estimated_emissions': 22000000,
        'renewable_energy_share': 26.0,
        'jobs_created_score': 78.0, 'regional_development_score': 76.0,
        'infrastructure_contribution_score': 84.0, 'national_value_score': 82.0,
        'waste_management_score': 56.0, 'water_impact_score': 52.0, 'biodiversity_impact_score': 54.0,
        'energy_transition_score': 70.0, 'digitalization_score': 72.0,
        'infrastructure_upgrade_score': 74.0, 'future_readiness_score': 72.0,
        'transparency_score_detail': 72.0, 'audit_quality_score': 70.0,
        'procurement_transparency_score': 66.0, 'anti_corruption_score': 70.0,
        'controversy_risk_score': 40.0,
        'profit_extraction_risk_score': 28.0, 'profit_extraction_score': 28.0,
        'modernization_projects': [
            'EPR2 New Nuclear Programme (6 reactors + 8 option)', 'Grand Carénage Fleet Renovation',
            'EDF Renewables Offshore Wind Expansion', 'Framatome Nuclear Services Modernisation',
            'EDF Blue Hydrogen Pilot (Gravelines)',
        ],
        'ai_summary': (
            f"Électricité de France (EDF) is the world's largest operator of nuclear power plants "
            f"and France's dominant electricity utility. Following renationalisation in 2023, it is "
            f"100% state-owned. Publicly available data indicates revenues exceeding €143 billion "
            f"and operations spanning 56 nuclear reactors in France plus renewable energy assets "
            f"across the UK, US, Italy, and beyond. EDF's carbon intensity per kWh is among the "
            f"lowest of any large utility globally. {DISCLAIMER}"
        ),
        'ai_modernization_report': (
            "EDF presents a complex transition intelligence picture. Its nuclear fleet delivers "
            "low-carbon baseload electricity at scale — a unique asset in any credible "
            "European decarbonisation scenario. However, the EPR programme (Flamanville, "
            "Hinkley Point C) has suffered severe cost overruns and delays, raising questions "
            "about the financial viability of nuclear as a transition technology at scale. "
            "EDF Renewables' offshore wind expansion is credible. Nuclear waste management "
            "remains the longest-duration environmental liability in any utility's portfolio."
        ),
        'ai_investment_opportunity': (
            "EDF is a unique transition finance opportunity: state backing reduces default risk, "
            "while its nuclear and renewables portfolio aligns with EU Taxonomy low-carbon "
            "criteria. Green bonds for offshore wind are already established. The EPR2 programme "
            "creates potential for sovereign green bond issuance for new nuclear — a politically "
            "contested but growing institutional appetite. EDF's hydrogen pilot programme "
            "represents an emerging clean fuel investment theme."
        ),
        'ai_risk_notes': (
            "Key risks: (1) EPR cost overruns — Flamanville and Hinkley Point C have "
            "experienced £20bn+ cost escalations; (2) Nuclear waste — long-duration "
            "radioactive waste liability represents the most persistent environmental "
            "obligation in EcoIQ's dataset; (3) Ageing fleet — 40+ year old reactors "
            "require massive Grand Carénage renovation investment; (4) Debt burden post "
            "renationalisation exceeds €60 billion; (5) Corrosion-stress cracking (SCC) "
            "defects discovered in reactor pipes created significant 2022 production outages."
        ),
        'ai_recommendations': [
            'Publish independent long-term nuclear waste management cost and timeline assessment',
            'Accelerate offshore wind as EV and heat pump electrification demand grows',
            'Publish annual nuclear safety performance benchmarked against international WANO standards',
            'Establish independent nuclear cost oversight committee for EPR2 programme',
            'Increase renewable energy share of new investment from 25% to 50% by 2030',
        ],
        'video_title': 'EDF: Nuclear Power and the European Energy Transition — EcoIQ',
        'video_executive_summary': (
            "EDF is the foundational low-carbon electricity provider for the French and European "
            "transition. Its EcoIQ score of 68 reflects genuine environmental stewardship via "
            "nuclear, with nuclear waste management and EPR programme accountability as the "
            "critical transparency requirements."
        ),
        'video_script': (
            "EDF, you are the backbone of France's low-carbon electricity system — and "
            "arguably one of the most important transition infrastructure companies in Europe. "
            "Your 56 nuclear reactors deliver electricity with a carbon intensity 96% lower "
            "than coal. That is extraordinary. Your EcoIQ score of 68 places you in "
            "Public-Benefit Oriented territory — a strong foundation, but not yet the "
            "leadership your role deserves. The path to 80 runs through accountability. "
            "Nuclear waste is the longest environmental liability any company carries. "
            "The EPR2 programme is France's most consequential infrastructure investment. "
            "Both require independent, transparent cost and risk accounting — not just for "
            "investors, but for the public who rely on your energy and inherit your waste. "
            "EDF, the transition needs your low-carbon baseload. But it also needs your "
            "complete transparency. One without the other is not enough."
        ),
        'video_higgsfield': (
            "Opening: drone shot over French nuclear plant at dawn — cooling towers with steam "
            "rising, river in foreground, flat agricultural landscape. Cut to control room — "
            "operators monitoring reactor systems on large screens, precise and calm. "
            "Animation of nuclear fission process — clean energy generation visualisation. "
            "Cut to offshore wind farm EDF is building in the Atlantic — constructing turbines "
            "at sea. Interior of EPR reactor under construction. "
            "Final shot: French grid map — electricity flowing from nuclear and wind to cities. "
            "Colour palette: cool blue-grey, soft white steam, amber safety lighting, "
            "clean green energy flows. Tone: technical competence, low-carbon gravitas, "
            "responsible custodianship."
        ),
        'video_actions': [
            'Publish independent nuclear waste long-term cost assessment',
            'Accelerate offshore wind investment allocation',
            'Annual nuclear safety benchmarking vs WANO standards',
            'Independent EPR2 cost oversight committee',
            'Increase renewable share of new investment to 50% by 2030',
        ],
    },

    # ── Schneider Electric ───────────────────────────────────────────────────────
    {
        'name': 'Schneider Electric', 'slug': 'schneider-electric', 'sector': 'energy',
        'country': 'France', 'city': 'Rueil-Malmaison',
        'description': 'Schneider Electric is a global leader in energy management and industrial automation, providing products, systems, and services that enable customers to improve energy efficiency, sustainability, and productivity across industries, buildings, and data centres.',
        'website': 'https://schneider-electric.com',
        'employee_count': 150000, 'annual_revenue_usd': 35928000000, 'is_public': True,
        'score_pollution_footprint': 84, 'score_reduction_progress': 82,
        'score_investment': 84, 'score_transparency': 88, 'score_community_impact': 84,
        'ownership_type': 'public_listed', 'funding_status': 'open_to_funding',
        'pollution_level': 'low',
        'estimated_emissions': 780000,
        'renewable_energy_share': 90.0,
        'jobs_created_score': 86.0, 'regional_development_score': 84.0,
        'infrastructure_contribution_score': 84.0, 'national_value_score': 88.0,
        'waste_management_score': 78.0, 'water_impact_score': 82.0, 'biodiversity_impact_score': 78.0,
        'energy_transition_score': 90.0, 'digitalization_score': 92.0,
        'infrastructure_upgrade_score': 88.0, 'future_readiness_score': 92.0,
        'transparency_score_detail': 88.0, 'audit_quality_score': 86.0,
        'procurement_transparency_score': 82.0, 'anti_corruption_score': 84.0,
        'controversy_risk_score': 18.0,
        'profit_extraction_risk_score': 28.0, 'profit_extraction_score': 28.0,
        'modernization_projects': [
            'EcoStruxure Platform (IoT-enabled energy management)', 'Green Premium Eco-design Label',
            'Scope 3 Customer Emissions Programme', 'Zero Carbon Operations by 2025',
            'Inclusive Energy Access Programme (70m people target)',
        ],
        'ai_summary': (
            f"Schneider Electric SE is globally recognised as one of the most advanced companies "
            f"in energy management and industrial automation. With revenues exceeding €35 billion "
            f"and operations in over 100 countries, Schneider enables customers across buildings, "
            f"industry, data centres, and infrastructure to reduce energy consumption and "
            f"decarbonise operations through its EcoStruxure IoT platform and smart grid solutions. "
            f"It is consistently rated as one of the world's most sustainable companies. {DISCLAIMER}"
        ),
        'ai_modernization_report': (
            "Schneider Electric is EcoIQ's benchmark for corporate sustainability leadership in "
            "the industrial sector. Its EcoStruxure platform delivers measurable energy savings "
            "to customers across every sector — the platform's impact is multiplicative rather "
            "than linear. Schneider has committed to zero carbon operations by 2025 (own "
            "operations), and its Scope 3 customer programme — helping 1,000 key suppliers "
            "reduce emissions — is one of the most ambitious supply chain decarbonisation "
            "programmes EcoIQ has analysed. Its Green Premium eco-design label ensures every "
            "product carries its environmental footprint."
        ),
        'ai_investment_opportunity': (
            "Schneider Electric represents the cleanest industrial transition investment thesis "
            "in EcoIQ's global dataset. Its energy-management-as-a-service model creates "
            "recurring revenue streams aligned with customer decarbonisation progress. "
            "Green bonds backed by EcoStruxure customer energy savings are a credible "
            "impact investment vehicle. ESG-aligned institutional investors allocating to "
            "industrial transition find Schneider one of the most accessible entry points "
            "for a diversified European portfolio."
        ),
        'ai_risk_notes': (
            "Risks are primarily execution and competition: (1) Siemens, ABB, Honeywell and "
            "Eaton are all intensifying their smart energy management platforms; (2) Geopolitical "
            "exposure in China (significant manufacturing and revenue) creates tariff risk; "
            "(3) AI and data centre energy demand is creating a paradox — Schneider benefits "
            "from data centre expansion but data centres are major energy consumers; "
            "(4) Inclusive energy access targets (70m people) require novel delivery models "
            "that may pressure margins."
        ),
        'ai_recommendations': [
            'Publish annual measurement of customer emissions reductions enabled by EcoStruxure',
            'Accelerate Scope 3 customer programme to cover 5,000 suppliers by 2027',
            'Lead industry coalition on AI data centre energy efficiency standards',
            'Scale inclusive energy access programme with multilateral development bank support',
            'Publish water stewardship data for all manufacturing facilities',
        ],
        'video_title': 'Schneider Electric: The World\'s Energy Efficiency Engine — EcoIQ',
        'video_executive_summary': (
            "Schneider Electric is EcoIQ's top-scoring industrial company globally — a company "
            "that has made energy efficiency its core business model. Its EcoIQ score of 81 "
            "places it at the threshold of Regenerative Leader status."
        ),
        'video_script': (
            "Schneider Electric, you have done something remarkable. You have turned energy "
            "efficiency from a compliance obligation into a business model — and in doing so, "
            "you have helped your customers avoid more carbon emissions than you generate "
            "by an order of magnitude. Your EcoIQ score of 81 makes you the industrial "
            "sector leader in our global dataset. You are already carbon neutral in your "
            "own operations. Your EcoStruxure platform is managing energy in hundreds of "
            "thousands of buildings, factories, and data centres around the world. "
            "Your Green Premium label ensures every product you sell has a published "
            "environmental passport. The path from 81 to Regenerative Leader — above 85 — "
            "is achievable. Measure and publish the aggregate customer emission reductions "
            "your platform generates every year. Scale the inclusive energy access programme "
            "with development bank support. Lead the coalition on AI data centre efficiency "
            "standards. Schneider Electric, the world is adopting your platform. "
            "Now give the world the evidence of its impact."
        ),
        'video_higgsfield': (
            "Opening: Schneider Electric EcoStruxure dashboard visualisation — real-time "
            "energy management across a smart building complex, data flowing across the screen. "
            "Cut to factory floor with Schneider automation systems in operation — energy "
            "consumption displays showing real-time optimisation. Aerial shot of solar-powered "
            "building campus with integrated Schneider smart grid management. "
            "Close-up: engineer monitoring grid stability on Schneider control panel. "
            "Animation: global map showing energy savings propagating from Schneider-managed "
            "facilities worldwide. Final shot: smiling community in a rural electrification "
            "project — Schneider inclusive access programme in action. "
            "Colour palette: Schneider green, deep charcoal, digital white, warm amber. "
            "Tone: efficient precision, global scale, inclusive optimism."
        ),
        'video_actions': [
            'Publish aggregate customer emissions reductions annually',
            'Scale supplier programme to 5,000 by 2027',
            'Lead AI data centre efficiency coalition',
            'Scale inclusive energy access with MDB support',
            'Water stewardship reporting for all facilities',
        ],
    },

    # ── Ørsted ───────────────────────────────────────────────────────────────────
    {
        'name': 'Ørsted', 'slug': 'orsted', 'sector': 'energy',
        'country': 'Denmark', 'city': 'Fredericia',
        'description': 'Ørsted is the world\'s largest offshore wind energy company. Originally founded as DONG Energy (Danish Oil and Natural Gas), it completed one of the most dramatic corporate transformations in history — divesting all oil and gas assets and becoming a pure-play renewable energy company.',
        'website': 'https://orsted.com',
        'employee_count': 8600, 'annual_revenue_usd': 11860000000, 'is_public': True,
        'score_pollution_footprint': 94, 'score_reduction_progress': 92,
        'score_investment': 90, 'score_transparency': 90, 'score_community_impact': 86,
        'ownership_type': 'mixed',
        'state_owned_percentage': 50.4,
        'funding_status': 'open_to_funding',
        'pollution_level': 'low',
        'estimated_emissions': 520000,
        'renewable_energy_share': 98.0,
        'jobs_created_score': 84.0, 'regional_development_score': 82.0,
        'infrastructure_contribution_score': 84.0, 'national_value_score': 82.0,
        'waste_management_score': 80.0, 'water_impact_score': 84.0, 'biodiversity_impact_score': 80.0,
        'energy_transition_score': 96.0, 'digitalization_score': 84.0,
        'infrastructure_upgrade_score': 88.0, 'future_readiness_score': 90.0,
        'transparency_score_detail': 90.0, 'audit_quality_score': 88.0,
        'procurement_transparency_score': 84.0, 'anti_corruption_score': 86.0,
        'controversy_risk_score': 20.0,
        'profit_extraction_risk_score': 24.0, 'profit_extraction_score': 24.0,
        'modernization_projects': [
            'Hornsea 3 Offshore Wind (2.8 GW)', 'Greater Changhua (Taiwan — 2.3 GW)',
            'Revolution Wind (US — 704 MW)', 'Sunrise Wind (US — 924 MW)',
            'Green Hydrogen from Wind (Holstebro pilot)',
        ],
        'ai_summary': (
            f"Ørsted A/S is the world's leading offshore wind developer, having completed one of "
            f"the most remarkable corporate transformations in industrial history. Beginning as "
            f"DONG Energy — one of Europe's most coal-intensive utilities — the company divested "
            f"all oil and gas assets and rebranded as Ørsted in 2017. Publicly available data "
            f"indicates revenues exceeding DKK 77 billion, with an offshore wind portfolio spanning "
            f"Denmark, UK, Germany, Netherlands, USA, and Taiwan. {DISCLAIMER}"
        ),
        'ai_modernization_report': (
            "Ørsted is the definitive case study in corporate industrial transformation. "
            "From 85% fossil fuel dependency in 2006 to 98% renewable energy generation today, "
            "the company has delivered on the most ambitious transition strategy EcoIQ has "
            "analysed. Its energy transition score (96) and future readiness score (90) are "
            "the highest in EcoIQ's energy sector dataset. Ørsted's transparency and governance "
            "standards are exceptional — its sustainability report is consistently cited as "
            "best-in-class by institutional investors. The company's green hydrogen pilot "
            "(Holstebro) signals the next frontier of its transition leadership."
        ),
        'ai_investment_opportunity': (
            "Ørsted is the world's most credible green energy investment vehicle. Its "
            "project pipeline, track record on cost reduction (offshore wind LCOE reduced "
            "70% since 2012), and governance quality make it the benchmark for ESG-aligned "
            "energy infrastructure investment. Green bonds backed by specific offshore wind "
            "farms provide ring-fenced impact. The US market expansion (Sunrise, Revolution "
            "Wind) creates currency and regulatory diversification. Green hydrogen pilot "
            "represents optionality on the next energy transition wave."
        ),
        'ai_risk_notes': (
            "Key risks: (1) Offshore wind cost inflation — rising steel, cable, and installation "
            "vessel costs have pressure project returns; US projects (e.g. Ocean Wind 1) faced "
            "cancellations in 2023 due to inflation impact; (2) Biodiversity concerns — "
            "large offshore wind farms have emerging evidence of seabed and marine life impacts "
            "requiring active management; (3) Danish state ownership (50.4%) introduces "
            "political influence risk; (4) Supply chain concentration — Siemens Gamesa turbine "
            "quality issues created production delays across multiple Ørsted projects."
        ),
        'ai_recommendations': [
            'Publish independent marine biodiversity monitoring data for all offshore wind farms',
            'Establish offshore wind just transition support for fishing communities affected by farm footprints',
            'Accelerate green hydrogen investment beyond pilot phase',
            'Publish supply chain resilience plan addressing Siemens Gamesa concentration risk',
            'Continue leading on UN SDG reporting as industry standard-setter',
        ],
        'video_title': 'Ørsted: The World\'s Greatest Energy Transformation Story — EcoIQ',
        'video_executive_summary': (
            "Ørsted is EcoIQ's highest-scoring energy company globally — a Regenerative Leader "
            "that has transformed from a coal utility to the world's leading offshore wind developer. "
            "Its score of 86 is the benchmark for what industrial transformation can achieve."
        ),
        'video_script': (
            "Ørsted, what you have done is the most important corporate story of the last "
            "two decades. You were one of Europe's most polluting utilities. You burned coal, "
            "drilled for oil, and extracted gas from the North Sea. Today, you power the "
            "equivalent of 18 million homes with clean offshore wind. Your EcoIQ score of 86 "
            "makes you a Regenerative Leader — the highest category in our global system, "
            "earned by only a handful of companies worldwide. The transformation from DONG "
            "Energy to Ørsted is not just a corporate story — it is proof of what is possible. "
            "An industry can transform. A company can choose a different future. "
            "The path from 86 to 95 requires two things: independent marine biodiversity "
            "monitoring across all your offshore farms — because the ocean floor matters "
            "as much as the atmosphere — and an accelerated green hydrogen investment that "
            "takes you beyond wind into the full clean energy system. Ørsted, the world's "
            "energy transition is following your footprints. Keep walking."
        ),
        'video_higgsfield': (
            "Dawn aerial shot of Hornsea offshore wind farm — hundreds of turbines emerging "
            "from morning mist over the North Sea, blades turning in synchrony. "
            "Camera descends toward the water surface, waves visible beneath the turbine bases. "
            "Cut to historical archive-style footage: coal power station cooling towers (faded "
            "colour, past), transitioning to crisp bright footage of modern offshore wind "
            "installation vessel. Underwater shot: seabed near wind turbine foundation — "
            "marine life, fish, soft coral. DONG Energy logo briefly visible transforming "
            "into the Ørsted logo. Close-up of turbine blade tip moving against blue sky. "
            "Final wide shot: full offshore wind farm from altitude, sun breaking through "
            "clouds, ocean horizon. Colour palette: ocean blue, silver-white, soft gold "
            "sunrise. Tone: epic scale, profound transformation, earned optimism."
        ),
        'video_actions': [
            'Independent marine biodiversity monitoring for all offshore farms',
            'Just transition support for fishing communities',
            'Accelerate green hydrogen investment beyond pilot',
            'Supply chain resilience plan for turbine concentration risk',
            'Continue UN SDG reporting as industry standard-setter',
        ],
    },

]


class Command(BaseCommand):
    help = (
        'Seed Phase 2 company profiles: '
        'NVIDIA, Siemens, Samsung, CATL, BYD, EDF, Schneider Electric, Ørsted. '
        'Idempotent — safe to re-run.'
    )

    def handle(self, *args, **options):
        created_companies = 0
        updated_companies = 0
        created_profiles  = 0
        updated_profiles  = 0
        created_videos    = 0

        SECTOR_MAP = {
            'energy': 'energy', 'other': 'other',
            'tech': 'other', 'mining': 'mining',
        }

        for entry in SEED_DATA:
            # ── 1. league.Company ───────────────────────────────────────────────
            co_defaults = {
                'sector':        entry.get('sector', 'other'),
                'country':       entry.get('country', ''),
                'city':          entry.get('city', ''),
                'description':   entry.get('description', ''),
                'website':       entry.get('website', ''),
                'employee_count':entry.get('employee_count', 0),
                'annual_revenue_usd': entry.get('annual_revenue_usd', 0),
                'is_public':     entry.get('is_public', True),
                # Legacy 5-pillar scores (set to reasonable defaults)
                'score_pollution_footprint': entry.get('score_pollution_footprint', 50),
                'score_reduction_progress':  entry.get('score_reduction_progress', 50),
                'score_investment':          entry.get('score_investment', 50),
                'score_transparency':        entry.get('score_transparency', 50),
                'score_community_impact':    entry.get('score_community_impact', 50),
            }

            slug = entry.get('slug') or slugify(entry['name'])
            co, created = Company.objects.update_or_create(
                slug=slug,
                defaults={**co_defaults, 'name': entry['name']},
            )
            if created:
                created_companies += 1
            else:
                updated_companies += 1

            # ── 2. CompanyProfile ───────────────────────────────────────────────
            profile_defaults = {
                'status':         'public',
                'is_verified':    False,
                'ownership_type': entry.get('ownership_type', 'public_listed'),
                'state_owned_percentage': entry.get('state_owned_percentage'),
                'funding_status': entry.get('funding_status', 'not_seeking'),
                'pollution_level': entry.get('pollution_level', 'medium'),
                'estimated_emissions': entry.get('estimated_emissions'),
                'renewable_energy_share': entry.get('renewable_energy_share'),
                # Environmental sub-scores
                'waste_management_score':   entry.get('waste_management_score', 50.0),
                'water_impact_score':       entry.get('water_impact_score', 50.0),
                'biodiversity_impact_score':entry.get('biodiversity_impact_score', 50.0),
                # Social sub-scores
                'jobs_created_score':           entry.get('jobs_created_score', 50.0),
                'regional_development_score':   entry.get('regional_development_score', 50.0),
                'infrastructure_contribution_score': entry.get('infrastructure_contribution_score', 50.0),
                'national_value_score':         entry.get('national_value_score', 50.0),
                # Modernization sub-scores
                'energy_transition_score':    entry.get('energy_transition_score', 50.0),
                'digitalization_score':       entry.get('digitalization_score', 50.0),
                'infrastructure_upgrade_score': entry.get('infrastructure_upgrade_score', 50.0),
                'future_readiness_score':     entry.get('future_readiness_score', 50.0),
                # Governance sub-scores
                'transparency_score_detail':      entry.get('transparency_score_detail', 50.0),
                'audit_quality_score':            entry.get('audit_quality_score', 50.0),
                'procurement_transparency_score': entry.get('procurement_transparency_score', 50.0),
                'anti_corruption_score':          entry.get('anti_corruption_score', 50.0),
                'controversy_risk_score':         entry.get('controversy_risk_score', 30.0),
                'profit_extraction_risk_score':   entry.get('profit_extraction_risk_score', 40.0),
                'profit_extraction_score':        entry.get('profit_extraction_score', 40.0),
                # Modernization projects
                'modernization_projects': entry.get('modernization_projects', []),
                # AI content
                'ai_summary':               entry.get('ai_summary', ''),
                'ai_modernization_report':  entry.get('ai_modernization_report', ''),
                'ai_investment_opportunity':entry.get('ai_investment_opportunity', ''),
                'ai_risk_notes':            entry.get('ai_risk_notes', ''),
                'ai_recommendations':       entry.get('ai_recommendations', []),
            }

            profile, p_created = CompanyProfile.objects.update_or_create(
                company=co,
                defaults=profile_defaults,
            )
            if p_created:
                created_profiles += 1
            else:
                updated_profiles += 1

            # Compute scores via engine
            recalculate_and_save(profile)
            profile.refresh_from_db()

            # ── 3. Guidance video ───────────────────────────────────────────────
            vid_title = entry.get('video_title', f'How {co.name} Can Improve EcoIQ')
            if not CompanyGuidanceVideo.objects.filter(
                company=profile, video_type='path_to_100'
            ).exists():
                CompanyGuidanceVideo.objects.create(
                    company=profile,
                    title=vid_title,
                    video_type='path_to_100',
                    status='script_generated',
                    visibility='public',
                    script=entry.get('video_script', ''),
                    higgsfield_prompt=entry.get('video_higgsfield', ''),
                    executive_summary=entry.get('video_executive_summary', ''),
                    recommended_actions=entry.get('video_actions', []),
                    current_score_snapshot=profile.ecoiq_total_score,
                    target_score=min(100.0, profile.ecoiq_total_score + 20.0),
                    target_score_improvement=20.0,
                )
                created_videos += 1

            self.stdout.write(
                f'  ✓ {co.name:<25} — EcoIQ {profile.ecoiq_total_score:5.1f} '
                f'({profile.moral_label_display})'
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done — {created_companies} companies created, {updated_companies} updated. '
            f'{created_profiles} profiles created, {updated_profiles} updated. '
            f'{created_videos} guidance videos created.'
        ))
