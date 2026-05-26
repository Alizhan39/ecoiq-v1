"""
EcoIQ Transition Engine — Financing Seed Data.

Pre-seeds the FinancingOpportunity registry with real DFIs, climate funds,
green bond programmes, and export credit agencies that are active in
industrial decarbonisation, particularly in Central Asia, Eastern Europe,
and emerging markets.

Usage:
    python manage.py seed_financing
    python manage.py seed_financing --clear    # delete existing before seeding
"""
from django.core.management.base import BaseCommand
from transition.models import FinancingOpportunity


FINANCING_DATA = [
    # ── Multilateral Development Finance Institutions ──────────────────────────
    {
        'institution_name': 'Asian Infrastructure Investment Bank',
        'programme_name': 'Climate Finance Facility',
        'acronym': 'AIIB',
        'source_type': 'dfi',
        'instrument': 'loan',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Central Asia', 'South Asia', 'Southeast Asia', 'Eastern Europe'],
        'focus_areas': ['renewable', 'energy_efficiency', 'coal_transition', 'clean_energy'],
        'min_ticket_usd': 10_000_000,
        'max_ticket_usd': 500_000_000,
        'typical_tenor_years': 20.0,
        'typical_interest_rate': 1.5,
        'grace_period_years': 5.0,
        'co_financing_required': True,
        'co_financing_pct': 20.0,
        'description': (
            'AIIB provides financing for sustainable infrastructure across Asia and beyond. '
            'The Climate Finance Facility targets coal-to-clean transitions, grid modernisation, '
            'and industrial decarbonisation projects in member countries.'
        ),
        'eligibility_criteria': 'AIIB member country, sovereign or corporate borrower, project IRR > 8%',
        'typical_timeline_days': 270,
        'url': 'https://www.aiib.org',
        'hq_country': 'China',
        'brand_colour': '#00a0e9',
    },
    {
        'institution_name': 'European Bank for Reconstruction and Development',
        'programme_name': 'Green Economy Transition',
        'acronym': 'EBRD',
        'source_type': 'dfi',
        'instrument': 'loan',
        'eligible_sectors': [],
        'eligible_countries': ['Kazakhstan', 'Uzbekistan', 'Ukraine', 'Poland', 'Romania',
                               'Bulgaria', 'Serbia', 'Georgia', 'Armenia', 'Azerbaijan',
                               'Kyrgyzstan', 'Tajikistan', 'Turkmenistan', 'Mongolia'],
        'eligible_regions': ['Central Asia', 'Eastern Europe', 'Caucasus'],
        'focus_areas': ['coal_transition', 'methane', 'energy_efficiency', 'renewable',
                        'industrial', 'water'],
        'min_ticket_usd': 5_000_000,
        'max_ticket_usd': 300_000_000,
        'typical_tenor_years': 15.0,
        'typical_interest_rate': 3.0,
        'grace_period_years': 3.0,
        'co_financing_required': False,
        'co_financing_pct': 30.0,
        'description': (
            'EBRD is the leading development bank in Central Asia and Eastern Europe, '
            'financing industrial decarbonisation, coal transition, and green economy projects. '
            'GET approach targets 50% green financing by 2025.'
        ),
        'eligibility_criteria': 'EBRD member country, bankable project, ESG standards compliance',
        'typical_timeline_days': 180,
        'url': 'https://www.ebrd.com',
        'hq_country': 'United Kingdom',
        'brand_colour': '#e30613',
    },
    {
        'institution_name': 'Asian Development Bank',
        'programme_name': 'Energy Transition Mechanism',
        'acronym': 'ADB',
        'source_type': 'dfi',
        'instrument': 'blended',
        'eligible_sectors': ['energy', 'utilities', 'industrial'],
        'eligible_countries': [],
        'eligible_regions': ['Central Asia', 'South Asia', 'Southeast Asia', 'Pacific'],
        'focus_areas': ['coal_transition', 'renewable', 'clean_energy', 'energy_efficiency'],
        'min_ticket_usd': 20_000_000,
        'max_ticket_usd': 1_000_000_000,
        'typical_tenor_years': 25.0,
        'typical_interest_rate': 1.0,
        'grace_period_years': 8.0,
        'co_financing_required': True,
        'co_financing_pct': 25.0,
        'description': (
            'ADB\'s Energy Transition Mechanism accelerates coal retirement and clean energy '
            'transition across Asia. Blends concessional loans, grants, and technical '
            'assistance to make transitions financially viable.'
        ),
        'eligibility_criteria': 'ADB member developing country, power sector or industrial applicant',
        'typical_timeline_days': 365,
        'url': 'https://www.adb.org/what-we-do/energy-transition-mechanism',
        'hq_country': 'Philippines',
        'brand_colour': '#e8001d',
    },
    {
        'institution_name': 'International Finance Corporation',
        'programme_name': 'Climate Finance Program',
        'acronym': 'IFC',
        'source_type': 'dfi',
        'instrument': 'equity',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Global'],
        'focus_areas': ['renewable', 'energy_efficiency', 'industrial', 'clean_energy',
                        'carbon_market'],
        'min_ticket_usd': 5_000_000,
        'max_ticket_usd': 200_000_000,
        'typical_tenor_years': 10.0,
        'typical_interest_rate': 5.0,
        'grace_period_years': 2.0,
        'co_financing_required': False,
        'co_financing_pct': 25.0,
        'description': (
            'IFC is the largest global development institution focused on the private sector. '
            'Provides equity, loans, and advisory services for climate-smart industrial projects '
            'in emerging markets.'
        ),
        'eligibility_criteria': 'Private sector entity in IDA/IBRD eligible country',
        'typical_timeline_days': 180,
        'url': 'https://www.ifc.org',
        'hq_country': 'USA',
        'brand_colour': '#0066b2',
    },
    {
        'institution_name': 'World Bank Group',
        'programme_name': 'Scaling Solar / ESMAP',
        'acronym': 'WBG',
        'source_type': 'dfi',
        'instrument': 'loan',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Global'],
        'focus_areas': ['renewable', 'energy_efficiency', 'coal_transition', 'methane',
                        'flare', 'water'],
        'min_ticket_usd': 10_000_000,
        'max_ticket_usd': 500_000_000,
        'typical_tenor_years': 20.0,
        'typical_interest_rate': 2.5,
        'grace_period_years': 5.0,
        'co_financing_required': True,
        'co_financing_pct': 20.0,
        'description': (
            'The World Bank provides financing and technical assistance for climate-aligned '
            'infrastructure. ESMAP supports energy sector transitions; Scaling Solar enables '
            'private solar development in emerging markets.'
        ),
        'eligibility_criteria': 'World Bank member country; sovereign guarantee or IDA eligibility',
        'typical_timeline_days': 365,
        'url': 'https://www.worldbank.org',
        'hq_country': 'USA',
        'brand_colour': '#009edb',
    },
    {
        'institution_name': 'Islamic Development Bank',
        'programme_name': 'Climate Action Programme',
        'acronym': 'IsDB',
        'source_type': 'dfi',
        'instrument': 'loan',
        'eligible_sectors': [],
        'eligible_countries': ['Kazakhstan', 'Uzbekistan', 'Kyrgyzstan', 'Tajikistan',
                               'Turkmenistan', 'Azerbaijan', 'Pakistan', 'Bangladesh',
                               'Egypt', 'Morocco', 'Jordan', 'Algeria', 'Indonesia'],
        'eligible_regions': ['Central Asia', 'MENA', 'South Asia', 'Southeast Asia',
                             'Sub-Saharan Africa'],
        'focus_areas': ['renewable', 'energy_efficiency', 'water', 'industrial'],
        'min_ticket_usd': 5_000_000,
        'max_ticket_usd': 200_000_000,
        'typical_tenor_years': 20.0,
        'typical_interest_rate': 2.5,
        'grace_period_years': 5.0,
        'co_financing_required': False,
        'co_financing_pct': 30.0,
        'description': (
            'IsDB provides Sharia-compliant financing for sustainable infrastructure in '
            'member countries. Climate Action Programme targets renewable energy, '
            'energy efficiency, and water management projects.'
        ),
        'eligibility_criteria': 'IsDB member country; Sharia-compliant project structure',
        'typical_timeline_days': 270,
        'url': 'https://www.isdb.org',
        'hq_country': 'Saudi Arabia',
        'brand_colour': '#006636',
    },

    # ── Climate Funds ──────────────────────────────────────────────────────────
    {
        'institution_name': 'Green Climate Fund',
        'programme_name': 'Private Sector Facility',
        'acronym': 'GCF',
        'source_type': 'climate_fund',
        'instrument': 'grant',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Global'],
        'focus_areas': ['coal_transition', 'methane', 'renewable', 'energy_efficiency',
                        'water', 'industrial'],
        'min_ticket_usd': 500_000,
        'max_ticket_usd': 250_000_000,
        'typical_tenor_years': 20.0,
        'typical_interest_rate': 0.0,
        'grace_period_years': 10.0,
        'co_financing_required': True,
        'co_financing_pct': 50.0,
        'description': (
            'GCF is the world\'s largest dedicated climate fund. Provides grants, concessional '
            'loans, and equity for transformational climate action in developing countries. '
            'Co-financing typically required from national development banks or private sector.'
        ),
        'eligibility_criteria': 'Developing country, national designated authority endorsement, '
                                 'accredited implementing entity required',
        'typical_timeline_days': 540,
        'url': 'https://www.greenclimate.fund',
        'hq_country': 'South Korea',
        'brand_colour': '#00a651',
    },
    {
        'institution_name': 'Climate Investment Funds',
        'programme_name': 'Clean Technology Fund / Accelerating Coal Transition',
        'acronym': 'CIF',
        'source_type': 'climate_fund',
        'instrument': 'blended',
        'eligible_sectors': ['energy', 'industrial', 'utilities'],
        'eligible_countries': [],
        'eligible_regions': ['Central Asia', 'Eastern Europe', 'South Asia',
                             'Southeast Asia', 'Sub-Saharan Africa', 'MENA'],
        'focus_areas': ['coal_transition', 'renewable', 'energy_efficiency', 'clean_energy'],
        'min_ticket_usd': 1_000_000,
        'max_ticket_usd': 500_000_000,
        'typical_tenor_years': 20.0,
        'typical_interest_rate': 0.25,
        'grace_period_years': 10.0,
        'co_financing_required': True,
        'co_financing_pct': 40.0,
        'description': (
            'CIF\'s Accelerating Coal Transition programme provides concessional financing '
            'to retire coal assets and finance clean replacement capacity. Works through '
            'multilateral development bank partners.'
        ),
        'eligibility_criteria': 'CIF eligible country, MDB co-financing required',
        'typical_timeline_days': 365,
        'url': 'https://www.cif.org',
        'hq_country': 'USA',
        'brand_colour': '#2f9e44',
    },
    {
        'institution_name': 'Global Environment Facility',
        'programme_name': 'Industrial & Urban Mitigation',
        'acronym': 'GEF',
        'source_type': 'climate_fund',
        'instrument': 'grant',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Global'],
        'focus_areas': ['methane', 'industrial', 'energy_efficiency', 'circular'],
        'min_ticket_usd': 500_000,
        'max_ticket_usd': 50_000_000,
        'typical_tenor_years': 5.0,
        'typical_interest_rate': 0.0,
        'grace_period_years': 0.0,
        'co_financing_required': True,
        'co_financing_pct': 60.0,
        'description': (
            'GEF provides grants for global environmental benefit, including industrial '
            'methane reduction, energy efficiency, and circular economy initiatives. '
            'Requires significant co-financing (typically 4:1 ratio).'
        ),
        'eligibility_criteria': 'GEF eligible developing country; government or accredited '
                                 'entity implementing partner',
        'typical_timeline_days': 365,
        'url': 'https://www.thegef.org',
        'hq_country': 'USA',
        'brand_colour': '#279af1',
    },
    {
        'institution_name': 'Just Energy Transition Partnership',
        'programme_name': 'Country Platform',
        'acronym': 'JETP',
        'source_type': 'blended',
        'instrument': 'blended',
        'eligible_sectors': ['energy', 'industrial', 'utilities', 'mining'],
        'eligible_countries': ['South Africa', 'Indonesia', 'India', 'Vietnam',
                               'Senegal', 'Nigeria'],
        'eligible_regions': ['Sub-Saharan Africa', 'Southeast Asia', 'South Asia'],
        'focus_areas': ['coal_transition', 'renewable', 'just_transition', 'clean_energy'],
        'min_ticket_usd': 100_000_000,
        'max_ticket_usd': 10_000_000_000,
        'typical_tenor_years': 15.0,
        'typical_interest_rate': 2.0,
        'grace_period_years': 5.0,
        'co_financing_required': True,
        'co_financing_pct': 30.0,
        'description': (
            'JETPs are country-level partnerships to accelerate coal transition while '
            'supporting workers and communities. Backed by G7 donors through blended '
            'public/private financing packages.'
        ),
        'eligibility_criteria': 'JETP partner country; national energy transition plan',
        'typical_timeline_days': 540,
        'url': 'https://www.iea.org/news/five-countries-set-out-plans-to-power-just-energy-transitions',
        'hq_country': 'International',
        'brand_colour': '#e8a838',
    },

    # ── Export Credit Agencies ─────────────────────────────────────────────────
    {
        'institution_name': 'US Export-Import Bank',
        'programme_name': 'Climate Finance Program',
        'acronym': 'US EXIM',
        'source_type': 'export_credit',
        'instrument': 'loan',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Global'],
        'focus_areas': ['renewable', 'energy_efficiency', 'coal_transition', 'clean_energy'],
        'min_ticket_usd': 1_000_000,
        'max_ticket_usd': 500_000_000,
        'typical_tenor_years': 18.0,
        'typical_interest_rate': 4.5,
        'grace_period_years': 2.0,
        'co_financing_required': False,
        'co_financing_pct': 15.0,
        'description': (
            'US EXIM provides financing for export of US-made clean energy equipment. '
            'Climate Finance Program has a dedicated envelope for renewable energy, '
            'grid modernisation, and industrial decarbonisation.'
        ),
        'eligibility_criteria': 'Purchase of US goods/services ≥51% US content; creditworthy buyer',
        'typical_timeline_days': 120,
        'url': 'https://www.exim.gov',
        'hq_country': 'USA',
        'brand_colour': '#003087',
    },
    {
        'institution_name': 'UK Export Finance',
        'programme_name': 'Clean Growth Financing Initiative',
        'acronym': 'UKEF',
        'source_type': 'export_credit',
        'instrument': 'guarantee',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Global'],
        'focus_areas': ['renewable', 'energy_efficiency', 'clean_energy', 'industrial'],
        'min_ticket_usd': 5_000_000,
        'max_ticket_usd': 2_000_000_000,
        'typical_tenor_years': 15.0,
        'typical_interest_rate': 3.5,
        'grace_period_years': 2.0,
        'co_financing_required': False,
        'co_financing_pct': 20.0,
        'description': (
            'UKEF offers guarantees and direct loans to support UK export of clean energy '
            'and environmental technologies. Can cover up to 85% of contract value.'
        ),
        'eligibility_criteria': 'UK content requirement; environmental standards compliance',
        'typical_timeline_days': 90,
        'url': 'https://www.gov.uk/guidance/climate-change-and-clean-growth',
        'hq_country': 'United Kingdom',
        'brand_colour': '#012169',
    },

    # ── Green Bond Programmes ──────────────────────────────────────────────────
    {
        'institution_name': 'International Capital Market Association',
        'programme_name': 'Green Bond Principles / Transition Finance',
        'acronym': 'ICMA',
        'source_type': 'green_bond',
        'instrument': 'bond',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Global'],
        'focus_areas': ['renewable', 'energy_efficiency', 'coal_transition', 'industrial',
                        'circular', 'water'],
        'min_ticket_usd': 100_000_000,
        'max_ticket_usd': None,
        'typical_tenor_years': 10.0,
        'typical_interest_rate': None,
        'grace_period_years': None,
        'co_financing_required': False,
        'co_financing_pct': None,
        'description': (
            'ICMA\'s Green Bond Principles and Climate Transition Finance Handbook provide '
            'the global standard for labelled green and transition bonds. Companies can '
            'issue bonds in capital markets under these frameworks.'
        ),
        'eligibility_criteria': 'Listed or rated company; second-party opinion required; '
                                 'use of proceeds must align with GBP taxonomy',
        'typical_timeline_days': 60,
        'url': 'https://www.icmagroup.org/sustainable-finance/',
        'hq_country': 'Switzerland',
        'brand_colour': '#1a4f8a',
    },
    {
        'institution_name': 'Luxembourg Green Exchange',
        'programme_name': 'LGX Transition Bond Programme',
        'acronym': 'LGX',
        'source_type': 'green_bond',
        'instrument': 'bond',
        'eligible_sectors': ['energy', 'industrial', 'utilities', 'mining'],
        'eligible_countries': [],
        'eligible_regions': ['Global'],
        'focus_areas': ['coal_transition', 'methane', 'energy_efficiency', 'industrial'],
        'min_ticket_usd': 50_000_000,
        'max_ticket_usd': None,
        'typical_tenor_years': 7.0,
        'typical_interest_rate': None,
        'grace_period_years': None,
        'co_financing_required': False,
        'co_financing_pct': None,
        'description': (
            'LGX is the world\'s leading platform for green, social, and sustainability bonds. '
            'Transition bond framework enables high-emitting companies to access capital '
            'markets for credible decarbonisation plans.'
        ),
        'eligibility_criteria': 'Publicly-rated issuer; verified transition plan; '
                                 'EU taxonomy or ICMA alignment',
        'typical_timeline_days': 90,
        'url': 'https://www.luxse.com/lgx',
        'hq_country': 'Luxembourg',
        'brand_colour': '#e30613',
    },

    # ── Carbon Markets ─────────────────────────────────────────────────────────
    {
        'institution_name': 'Gold Standard Foundation',
        'programme_name': 'Gold Standard VER Certification',
        'acronym': 'GS',
        'source_type': 'carbon_market',
        'instrument': 'carbon_credit',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Global'],
        'focus_areas': ['methane', 'renewable', 'flare', 'coal_transition', 'energy_efficiency'],
        'min_ticket_usd': None,
        'max_ticket_usd': None,
        'typical_tenor_years': None,
        'typical_interest_rate': None,
        'grace_period_years': None,
        'co_financing_required': False,
        'co_financing_pct': None,
        'description': (
            'Gold Standard certifies high-quality carbon credits for voluntary carbon markets. '
            'Projects that reduce methane, flares, or industrial emissions can generate '
            'verified emission reductions (VERs) worth $10-50/tCO₂ on voluntary markets.'
        ),
        'eligibility_criteria': 'Additionality, permanence, SD co-benefits; methodology approval',
        'typical_timeline_days': 365,
        'url': 'https://www.goldstandard.org',
        'hq_country': 'Switzerland',
        'brand_colour': '#f7941d',
    },
    {
        'institution_name': 'Verified Carbon Standard / Verra',
        'programme_name': 'VCS Programme',
        'acronym': 'VCS',
        'source_type': 'carbon_market',
        'instrument': 'carbon_credit',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Global'],
        'focus_areas': ['methane', 'flare', 'renewable', 'industrial', 'coal_transition'],
        'min_ticket_usd': None,
        'max_ticket_usd': None,
        'typical_tenor_years': None,
        'typical_interest_rate': None,
        'grace_period_years': None,
        'co_financing_required': False,
        'co_financing_pct': None,
        'description': (
            'Verra\'s VCS is the world\'s most widely used voluntary carbon standard. '
            'Industrial methane reduction, flare elimination, and coal transition projects '
            'can generate ACCUs/VCUs tradeable on voluntary carbon markets.'
        ),
        'eligibility_criteria': 'Approved VCS methodology; third-party verification',
        'typical_timeline_days': 270,
        'url': 'https://verra.org/programs/verified-carbon-standard/',
        'hq_country': 'USA',
        'brand_colour': '#00843d',
    },

    # ── Blended Finance & Specialised Funds ───────────────────────────────────
    {
        'institution_name': 'European Fund for Strategic Investments',
        'programme_name': 'InvestEU Guarantee',
        'acronym': 'InvestEU',
        'source_type': 'blended',
        'instrument': 'guarantee',
        'eligible_sectors': [],
        'eligible_countries': ['Poland', 'Romania', 'Bulgaria', 'Hungary', 'Serbia',
                               'Albania', 'North Macedonia', 'Ukraine', 'Moldova'],
        'eligible_regions': ['Eastern Europe'],
        'focus_areas': ['renewable', 'energy_efficiency', 'industrial', 'coal_transition'],
        'min_ticket_usd': 10_000_000,
        'max_ticket_usd': 500_000_000,
        'typical_tenor_years': 15.0,
        'typical_interest_rate': 2.5,
        'grace_period_years': 3.0,
        'co_financing_required': False,
        'co_financing_pct': 50.0,
        'description': (
            'InvestEU provides EU budget guarantees to EIB and national promotional banks '
            'for green and sustainable infrastructure. Targets market failures in climate '
            'and environment investment.'
        ),
        'eligibility_criteria': 'EU member state or candidate country; EU taxonomy alignment',
        'typical_timeline_days': 180,
        'url': 'https://www.eib.org/en/products/mandates-partnerships/investeu/index.htm',
        'hq_country': 'Luxembourg',
        'brand_colour': '#003399',
    },
    {
        'institution_name': 'FMO Dutch Entrepreneurial Development Bank',
        'programme_name': 'Energy & Industry Finance',
        'acronym': 'FMO',
        'source_type': 'dfi',
        'instrument': 'loan',
        'eligible_sectors': ['energy', 'industrial', 'agriculture'],
        'eligible_countries': [],
        'eligible_regions': ['Global', 'Central Asia', 'Sub-Saharan Africa',
                             'Southeast Asia', 'MENA'],
        'focus_areas': ['renewable', 'energy_efficiency', 'industrial', 'water'],
        'min_ticket_usd': 5_000_000,
        'max_ticket_usd': 100_000_000,
        'typical_tenor_years': 12.0,
        'typical_interest_rate': 4.0,
        'grace_period_years': 2.0,
        'co_financing_required': False,
        'co_financing_pct': 25.0,
        'description': (
            'FMO is the Dutch development bank focused on private sector development '
            'in emerging markets. Provides loans, equity, and guarantees for clean energy '
            'and industrial sustainability projects.'
        ),
        'eligibility_criteria': 'Private sector in emerging market; ESG framework compliance',
        'typical_timeline_days': 150,
        'url': 'https://www.fmo.nl',
        'hq_country': 'Netherlands',
        'brand_colour': '#00a0df',
    },
    {
        'institution_name': 'DEG German Investment Corporation',
        'programme_name': 'Industrial Energy Efficiency',
        'acronym': 'DEG',
        'source_type': 'dfi',
        'instrument': 'loan',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Central Asia', 'Eastern Europe', 'Sub-Saharan Africa',
                             'South Asia', 'Southeast Asia', 'MENA'],
        'focus_areas': ['energy_efficiency', 'renewable', 'industrial', 'water'],
        'min_ticket_usd': 5_000_000,
        'max_ticket_usd': 100_000_000,
        'typical_tenor_years': 10.0,
        'typical_interest_rate': 5.0,
        'grace_period_years': 2.0,
        'co_financing_required': False,
        'co_financing_pct': 30.0,
        'description': (
            'DEG finances and structures private-sector projects in developing and '
            'emerging markets, with a strong focus on industrial energy efficiency '
            'and renewable energy deployment.'
        ),
        'eligibility_criteria': 'Private company in eligible country; ESG due diligence',
        'typical_timeline_days': 180,
        'url': 'https://www.deginvest.de',
        'hq_country': 'Germany',
        'brand_colour': '#003063',
    },
    {
        'institution_name': 'Proparco',
        'programme_name': 'CREATE / Climate Finance',
        'acronym': 'Proparco',
        'source_type': 'dfi',
        'instrument': 'loan',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Sub-Saharan Africa', 'MENA', 'Central Asia', 'Southeast Asia'],
        'focus_areas': ['renewable', 'energy_efficiency', 'industrial', 'water'],
        'min_ticket_usd': 3_000_000,
        'max_ticket_usd': 75_000_000,
        'typical_tenor_years': 12.0,
        'typical_interest_rate': 4.5,
        'grace_period_years': 2.0,
        'co_financing_required': False,
        'co_financing_pct': 25.0,
        'description': (
            'Proparco (subsidiary of AFD Group) finances private sector projects in '
            'developing countries. CREATE programme targets renewable energy and climate '
            'adaptation in French partner countries and beyond.'
        ),
        'eligibility_criteria': 'Private company in developing country; AFD eligible country',
        'typical_timeline_days': 150,
        'url': 'https://www.proparco.fr',
        'hq_country': 'France',
        'brand_colour': '#003063',
    },
    {
        'institution_name': 'OPIC / US International Development Finance Corporation',
        'programme_name': '2X Climate Finance Initiative',
        'acronym': 'DFC',
        'source_type': 'dfi',
        'instrument': 'loan',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Central Asia', 'Sub-Saharan Africa', 'Southeast Asia',
                             'South Asia', 'MENA', 'Eastern Europe'],
        'focus_areas': ['renewable', 'clean_energy', 'energy_efficiency', 'industrial'],
        'min_ticket_usd': 1_000_000,
        'max_ticket_usd': 500_000_000,
        'typical_tenor_years': 15.0,
        'typical_interest_rate': 4.0,
        'grace_period_years': 3.0,
        'co_financing_required': False,
        'co_financing_pct': 25.0,
        'description': (
            'DFC (formerly OPIC) is the US Government\'s development finance institution. '
            'Provides loans, equity, and political risk insurance for private sector '
            'investment in developing and frontier markets, with growing climate focus.'
        ),
        'eligibility_criteria': 'US national security criteria; private company; '
                                 'eligible developing country',
        'typical_timeline_days': 150,
        'url': 'https://www.dfc.gov',
        'hq_country': 'USA',
        'brand_colour': '#003087',
    },

    # ── Infrastructure Grants ──────────────────────────────────────────────────
    {
        'institution_name': 'EU Global Gateway',
        'programme_name': 'Green & Digital Connectivity',
        'acronym': 'GG',
        'source_type': 'infra_grant',
        'instrument': 'grant',
        'eligible_sectors': [],
        'eligible_countries': ['Kazakhstan', 'Uzbekistan', 'Kyrgyzstan', 'Tajikistan',
                               'Turkmenistan', 'Georgia', 'Armenia', 'Azerbaijan',
                               'Ukraine', 'Moldova'],
        'eligible_regions': ['Central Asia', 'Eastern Europe', 'Caucasus',
                             'Sub-Saharan Africa', 'MENA'],
        'focus_areas': ['renewable', 'energy_efficiency', 'coal_transition', 'industrial',
                        'water'],
        'min_ticket_usd': 5_000_000,
        'max_ticket_usd': 300_000_000,
        'typical_tenor_years': None,
        'typical_interest_rate': 0.0,
        'grace_period_years': None,
        'co_financing_required': True,
        'co_financing_pct': 40.0,
        'description': (
            'EU Global Gateway Team Europe packages combine grants, guarantees, and '
            'concessional loans for sustainable infrastructure. Central Asia and Eastern '
            'Neighbourhood are priority regions for green connectivity.'
        ),
        'eligibility_criteria': 'EU partnership agreement country; alignment with EU Green Deal',
        'typical_timeline_days': 365,
        'url': 'https://commission.europa.eu/strategy-and-policy/priorities-2019-2024/stronger-europe-world/global-gateway_en',
        'hq_country': 'Belgium',
        'brand_colour': '#003399',
    },
    {
        'institution_name': 'USAID',
        'programme_name': 'Clean Energy Finance Initiative',
        'acronym': 'USAID',
        'source_type': 'infra_grant',
        'instrument': 'grant',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Central Asia', 'Sub-Saharan Africa', 'Southeast Asia',
                             'South Asia', 'MENA'],
        'focus_areas': ['renewable', 'energy_efficiency', 'coal_transition', 'clean_energy'],
        'min_ticket_usd': 500_000,
        'max_ticket_usd': 50_000_000,
        'typical_tenor_years': None,
        'typical_interest_rate': 0.0,
        'grace_period_years': None,
        'co_financing_required': True,
        'co_financing_pct': 50.0,
        'description': (
            'USAID Clean Energy Finance Initiative provides grants and technical assistance '
            'to catalyse private investment in clean energy across developing countries. '
            'Focuses on policy reform, market development, and project preparation.'
        ),
        'eligibility_criteria': 'Eligible USAID country; aligned with US clean energy priorities',
        'typical_timeline_days': 180,
        'url': 'https://www.usaid.gov/energy',
        'hq_country': 'USA',
        'brand_colour': '#002868',
    },

    # ── Sovereign / Specialised ────────────────────────────────────────────────
    {
        'institution_name': 'Kazakhstan Development Bank',
        'programme_name': 'Green Economy Financing Facility',
        'acronym': 'DBK',
        'source_type': 'dfi',
        'instrument': 'loan',
        'eligible_sectors': [],
        'eligible_countries': ['Kazakhstan'],
        'eligible_regions': ['Central Asia'],
        'focus_areas': ['renewable', 'energy_efficiency', 'industrial', 'coal_transition',
                        'methane', 'water'],
        'min_ticket_usd': 1_000_000,
        'max_ticket_usd': 50_000_000,
        'typical_tenor_years': 10.0,
        'typical_interest_rate': 7.0,
        'grace_period_years': 2.0,
        'co_financing_required': False,
        'co_financing_pct': 20.0,
        'description': (
            'DBK is Kazakhstan\'s state development bank. Provides medium- and long-term '
            'financing for priority industrial and infrastructure projects including '
            'renewable energy, industrial modernisation, and environmental compliance.'
        ),
        'eligibility_criteria': 'Kazakhstan-registered company; feasibility study required',
        'typical_timeline_days': 90,
        'url': 'https://www.kdb.kz',
        'hq_country': 'Kazakhstan',
        'brand_colour': '#00ace6',
    },
    {
        'institution_name': 'European Investment Bank',
        'programme_name': 'Climate Bank Roadmap',
        'acronym': 'EIB',
        'source_type': 'dfi',
        'instrument': 'loan',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Eastern Europe', 'Central Asia', 'Global'],
        'focus_areas': ['renewable', 'energy_efficiency', 'coal_transition', 'industrial',
                        'water', 'circular'],
        'min_ticket_usd': 25_000_000,
        'max_ticket_usd': 1_000_000_000,
        'typical_tenor_years': 20.0,
        'typical_interest_rate': 2.0,
        'grace_period_years': 5.0,
        'co_financing_required': False,
        'co_financing_pct': 50.0,
        'description': (
            'EIB is the EU\'s climate bank, committed to aligning all financing with '
            'the Paris Agreement. Provides long-tenor loans for clean energy, industrial '
            'decarbonisation, and circular economy outside as well as inside the EU.'
        ),
        'eligibility_criteria': 'EU taxonomy alignment; bankable project; EU or partner country',
        'typical_timeline_days': 270,
        'url': 'https://www.eib.org',
        'hq_country': 'Luxembourg',
        'brand_colour': '#f7a800',
    },
    {
        'institution_name': 'International Renewable Energy Agency',
        'programme_name': 'Renewable Energy Finance Coalition',
        'acronym': 'IRENA',
        'source_type': 'infra_grant',
        'instrument': 'grant',
        'eligible_sectors': ['energy', 'utilities'],
        'eligible_countries': [],
        'eligible_regions': ['Global'],
        'focus_areas': ['renewable', 'coal_transition', 'clean_energy', 'energy_efficiency'],
        'min_ticket_usd': 100_000,
        'max_ticket_usd': 5_000_000,
        'typical_tenor_years': None,
        'typical_interest_rate': 0.0,
        'grace_period_years': None,
        'co_financing_required': False,
        'co_financing_pct': None,
        'description': (
            'IRENA provides technical assistance, market intelligence, and coalition '
            'facilitation grants for renewable energy deployment. Not a direct financier '
            'but connects projects with appropriate funding sources and provides project '
            'preparation support.'
        ),
        'eligibility_criteria': 'IRENA member country; renewable energy project',
        'typical_timeline_days': 90,
        'url': 'https://www.irena.org/Finance',
        'hq_country': 'UAE',
        'brand_colour': '#f59c1a',
    },
]


class Command(BaseCommand):
    help = 'Seed the FinancingOpportunity registry with real DFIs, climate funds, and programmes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing FinancingOpportunity records before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            count, _ = FinancingOpportunity.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {count} existing records'))

        created = 0
        updated = 0
        for data in FINANCING_DATA:
            obj, is_new = FinancingOpportunity.objects.update_or_create(
                institution_name=data['institution_name'],
                programme_name=data.get('programme_name', ''),
                defaults=data,
            )
            if is_new:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seed complete: {created} created, {updated} updated '
            f'({created + updated} total financing opportunities)'
        ))
