"""
python manage.py seed_league          # create/update demo data (idempotent)
python manage.py seed_league --flush  # wipe existing league data first

Demo data — 12 Kazakhstan/Central Asia industrial companies, 30+ projects,
5 years of monthly score history, evidence documents.
Data is clearly fictional/illustrative but grounded in real sector profiles.
"""
import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from league.models import Company, EnvironmentalProject, Evidence, ScoreHistory
from league.scoring import rerank_all


# ─────────────────────────────────────────────────────────────────────────────
# COMPANIES
# Scores are designed to populate every tier on the leaderboard:
#   87+ Restorative Leader  →  KEGOC
#   70–86 Transition Leader →  QazaqGaz, Air Astana
#   55–69 Improving         →  Kazatomprom, KazMunayGas, Kazzinc
#   40–54 High Impact       →  Samruk Energy, ERG, KazPhosphate
#   <40  Major Polluter     →  Kazakhmys, ArcelorMittal Temirtau, PetroChemical
# ─────────────────────────────────────────────────────────────────────────────

COMPANIES = [

    # ── 1. KEGOC — 87.3 Restorative Leader ──────────────────────────────────
    {
        'name':         'KEGOC',
        'sector':       'energy',
        'country':      'Kazakhstan',
        'city':         'Nur-Sultan',
        'founded_year': 1997,
        'employee_count': 11_200,
        'annual_revenue_usd': 980_000_000,
        'is_public':    True,
        'verified':     True,
        'is_featured':  True,
        'website':      'https://kegoc.kz',
        'description': (
            'KEGOC (Kazakhstan Electricity Grid Operating Company) operates the '
            'unified national power grid — 24,500 km of high-voltage transmission '
            'lines spanning Kazakhstan. As the backbone of the national energy '
            'system, KEGOC does not own generation assets, meaning its direct '
            'emissions footprint is modest. The company leads grid modernisation '
            'to absorb Kazakhstan\'s rapidly expanding renewable capacity and '
            'has committed to ISO 50001 energy management across all substations.'
        ),
        # EcoIQ = 92×0.35 + 85×0.25 + 88×0.20 + 82×0.10 + 80×0.10 = 87.25
        'score_pollution_footprint': 92,
        'score_reduction_progress':  85,
        'score_investment':          88,
        'score_transparency':        82,
        'score_community_impact':    80,
    },

    # ── 2. QazaqGaz — 71.6 Transition Leader ────────────────────────────────
    {
        'name':         'QazaqGaz',
        'sector':       'oil_gas',
        'country':      'Kazakhstan',
        'city':         'Nur-Sultan',
        'founded_year': 1999,
        'employee_count': 37_000,
        'annual_revenue_usd': 4_500_000_000,
        'is_public':    False,
        'verified':     True,
        'is_featured':  True,
        'website':      'https://qazaqgaz.kz',
        'description': (
            'QazaqGaz (formerly KazTransGaz) is Kazakhstan\'s national gas operator, '
            'managing gas transmission, distribution, and supply infrastructure. '
            'The company transports natural gas to over 4 million households and '
            'leads Kazakhstan\'s residential gasification programme — replacing coal '
            'and biomass burning in rural communities across 11 regions, directly '
            'reducing PM2.5 and CO₂ at scale.'
        ),
        # EcoIQ = 68×0.35 + 72×0.25 + 74×0.20 + 65×0.10 + 85×0.10 = 71.6
        'score_pollution_footprint': 68,
        'score_reduction_progress':  72,
        'score_investment':          74,
        'score_transparency':        65,
        'score_community_impact':    85,
    },

    # ── 3. Air Astana — 74.5 Transition Leader ──────────────────────────────
    {
        'name':         'Air Astana',
        'sector':       'transport',
        'country':      'Kazakhstan',
        'city':         'Almaty',
        'founded_year': 2001,
        'employee_count': 5_300,
        'annual_revenue_usd': 1_200_000_000,
        'is_public':    True,
        'verified':     True,
        'is_featured':  True,
        'website':      'https://airastana.com',
        'description': (
            'Air Astana is Kazakhstan\'s national carrier and the highest-rated '
            'airline in Central Asia by fleet age. Operating an entirely Airbus '
            'A320neo/A321XLR and Boeing 767-300ER fleet, Air Astana has the youngest '
            'average fleet age in the CIS at 4.1 years. The airline is Central Asia\'s '
            'first signatory to the IATA Net Zero 2050 commitment and is piloting '
            'Sustainable Aviation Fuel (SAF) on Almaty–Frankfurt routes.'
        ),
        # EcoIQ = 72×0.35 + 78×0.25 + 75×0.20 + 80×0.10 + 68×0.10 = 74.5
        'score_pollution_footprint': 72,
        'score_reduction_progress':  78,
        'score_investment':          75,
        'score_transparency':        80,
        'score_community_impact':    68,
    },

    # ── 4. Kazatomprom — 60.2 Improving but Polluting ───────────────────────
    {
        'name':         'Kazatomprom',
        'sector':       'mining',
        'country':      'Kazakhstan',
        'city':         'Nur-Sultan',
        'founded_year': 1997,
        'employee_count': 22_000,
        'annual_revenue_usd': 3_900_000_000,
        'is_public':    True,
        'verified':     True,
        'is_featured':  True,
        'website':      'https://kazatomprom.kz',
        'description': (
            'Kazatomprom is the world\'s largest uranium producer, supplying ~22% of '
            'global uranium output. In-situ recovery (ISR) technology minimises surface '
            'disturbance and eliminates mine shafts, significantly reducing the land and '
            'water footprint versus conventional mining. The company is remediating '
            'Soviet-era uranium sites and deploying renewable energy to power ISR '
            'wellfields across South and Central Kazakhstan.'
        ),
        # EcoIQ = 62×0.35 + 58×0.25 + 55×0.20 + 78×0.10 + 52×0.10 = 60.2
        'score_pollution_footprint': 62,
        'score_reduction_progress':  58,
        'score_investment':          55,
        'score_transparency':        78,
        'score_community_impact':    52,
    },

    # ── 5. KazMunayGas — 58.9 Improving but Polluting ───────────────────────
    {
        'name':         'KazMunayGas',
        'sector':       'oil_gas',
        'country':      'Kazakhstan',
        'city':         'Nur-Sultan',
        'founded_year': 2002,
        'employee_count': 76_000,
        'annual_revenue_usd': 18_700_000_000,
        'is_public':    True,
        'verified':     True,
        'is_featured':  True,
        'website':      'https://kmg.kz',
        'description': (
            'KazMunayGas (KMG) is Kazakhstan\'s national oil and gas company, covering '
            'the full value chain from exploration to retail. KMG accounts for ~27% of '
            'national oil production and operates three of four Kazakh refineries. '
            'The company has committed $2.1 billion to environmental modernisation '
            'through 2030, targeting 15% reduction in GHG intensity and near-zero '
            'routine flaring by 2025.'
        ),
        # EcoIQ = 55×0.35 + 62×0.25 + 65×0.20 + 70×0.10 + 48×0.10 = 59.45
        'score_pollution_footprint': 55,
        'score_reduction_progress':  62,
        'score_investment':          65,
        'score_transparency':        70,
        'score_community_impact':    48,
    },

    # ── 6. Kazzinc — 57.3 Improving but Polluting ───────────────────────────
    {
        'name':         'Kazzinc',
        'sector':       'metallurgy',
        'country':      'Kazakhstan',
        'city':         'Ust-Kamenogorsk',
        'founded_year': 1997,
        'employee_count': 21_000,
        'annual_revenue_usd': 2_800_000_000,
        'is_public':    False,
        'verified':     True,
        'is_featured':  False,
        'website':      'https://kazzinc.com',
        'description': (
            'Kazzinc is one of the world\'s top zinc producers and Kazakhstan\'s '
            'leading precious metals company, with integrated mining, smelting, and '
            'refining operations in East Kazakhstan. The Ust-Kamenogorsk metallurgical '
            'complex produces zinc, lead, copper, gold, and silver. Kazzinc has invested '
            'heavily in SO₂ capture and wastewater treatment, with a roadmap to achieve '
            'Paris-aligned emissions intensity by 2035.'
        ),
        # EcoIQ = 55×0.35 + 60×0.25 + 58×0.20 + 65×0.10 + 50×0.10 = 57.8
        'score_pollution_footprint': 55,
        'score_reduction_progress':  60,
        'score_investment':          58,
        'score_transparency':        65,
        'score_community_impact':    50,
    },

    # ── 7. Samruk Energy — 48.7 High Impact / Weak Repair ───────────────────
    {
        'name':         'Samruk Energy',
        'sector':       'energy',
        'country':      'Kazakhstan',
        'city':         'Nur-Sultan',
        'founded_year': 2008,
        'employee_count': 18_500,
        'annual_revenue_usd': 2_100_000_000,
        'is_public':    False,
        'verified':     True,
        'is_featured':  True,
        'website':      'https://samruk-energy.kz',
        'description': (
            'Samruk Energy is Kazakhstan\'s largest power generation group, operating '
            'coal-fired plants, hydroelectric stations, and wind farms that supply ~35% '
            'of national electricity. The coal fleet — including Ekibastuz GRES-1 '
            '(4,000 MW) and GRES-2 (1,000 MW) — remains the dominant source of national '
            'grid GHG emissions. Under Green Energy 2030, the company targets 20% '
            'renewable share in its portfolio by 2030.'
        ),
        # EcoIQ = 35×0.35 + 52×0.25 + 60×0.20 + 62×0.10 + 45×0.10 = 48.65
        'score_pollution_footprint': 35,
        'score_reduction_progress':  52,
        'score_investment':          60,
        'score_transparency':        62,
        'score_community_impact':    45,
    },

    # ── 8. ERG (Eurasian Resources Group) — 44.8 High Impact / Weak Repair ──
    {
        'name':         'ERG',
        'sector':       'metallurgy',
        'country':      'Kazakhstan',
        'city':         'Nur-Sultan',
        'founded_year': 1994,
        'employee_count': 75_000,
        'annual_revenue_usd': 6_200_000_000,
        'is_public':    False,
        'verified':     True,
        'is_featured':  False,
        'website':      'https://erg.kz',
        'description': (
            'Eurasian Resources Group (ERG) is one of the world\'s largest diversified '
            'natural resources companies, with integrated operations in iron ore, '
            'chrome, aluminium, coal, and ferroalloys across Kazakhstan, Africa, and '
            'Brazil. In Kazakhstan, ERG operates SSGPO (iron ore), Kazchrome (world\'s '
            'largest ferrochrome producer), and Aluminium of Kazakhstan. The group has '
            'pledged a 35% GHG intensity reduction by 2030 under its ERG Sustainability '
            'Strategy.'
        ),
        # EcoIQ = 38×0.35 + 48×0.25 + 50×0.20 + 55×0.10 + 42×0.10 = 44.8
        'score_pollution_footprint': 38,
        'score_reduction_progress':  48,
        'score_investment':          50,
        'score_transparency':        55,
        'score_community_impact':    42,
    },

    # ── 9. KazPhosphate — 50.1 High Impact / Weak Repair ────────────────────
    {
        'name':         'KazPhosphate',
        'sector':       'chemical',
        'country':      'Kazakhstan',
        'city':         'Taraz',
        'founded_year': 1999,
        'employee_count': 9_400,
        'annual_revenue_usd': 680_000_000,
        'is_public':    False,
        'verified':     False,
        'is_featured':  False,
        'website':      'https://kazphosphate.kz',
        'description': (
            'KazPhosphate is Central Asia\'s largest phosphate fertilizer producer, '
            'operating mining and chemical processing facilities near Taraz in southern '
            'Kazakhstan. The company mines phosphorite from the Karatau Basin — one of '
            'the world\'s largest phosphate deposits — and produces superphosphates, '
            'phosphoric acid, and complex fertilizers. Phosphogypsum tailings management '
            'and fluoride emissions remain key environmental challenges.'
        ),
        # EcoIQ = 44×0.35 + 52×0.25 + 55×0.20 + 48×0.10 + 55×0.10 = 50.1
        'score_pollution_footprint': 44,
        'score_reduction_progress':  52,
        'score_investment':          55,
        'score_transparency':        48,
        'score_community_impact':    55,
    },

    # ── 10. Kazakhmys — 36.6 Major Polluter ─────────────────────────────────
    {
        'name':         'Kazakhmys',
        'sector':       'mining',
        'country':      'Kazakhstan',
        'city':         'Karaganda',
        'founded_year': 1997,
        'employee_count': 33_000,
        'annual_revenue_usd': 1_900_000_000,
        'is_public':    True,
        'verified':     True,
        'is_featured':  False,
        'website':      'https://kazakhmys.com',
        'description': (
            'Kazakhmys is Kazakhstan\'s largest copper producer, operating an integrated '
            'mining, concentrating, and smelting complex in central and east Kazakhstan. '
            'The Balkhash Copper Smelter is one of the largest point sources of SO₂ '
            'emissions in Central Asia, periodically exceeding WHO guideline values by '
            'a factor of 6–12×. The company has committed to installing sulphuric acid '
            'capture units but progress has been slower than the 2020 roadmap projected.'
        ),
        # EcoIQ = 22×0.35 + 42×0.25 + 44×0.20 + 48×0.10 + 38×0.10 = 35.6
        'score_pollution_footprint': 22,
        'score_reduction_progress':  42,
        'score_investment':          44,
        'score_transparency':        48,
        'score_community_impact':    38,
    },

    # ── 11. ArcelorMittal Temirtau — 31.1 Major Polluter ────────────────────
    {
        'name':         'ArcelorMittal Temirtau',
        'sector':       'metallurgy',
        'country':      'Kazakhstan',
        'city':         'Temirtau',
        'founded_year': 1995,
        'employee_count': 28_000,
        'annual_revenue_usd': 3_100_000_000,
        'is_public':    False,
        'verified':     True,
        'is_featured':  False,
        'website':      'https://arcelormittal.kz',
        'description': (
            'ArcelorMittal Temirtau is Kazakhstan\'s only integrated steel producer, '
            'combining coking coal mining (Karaganda coal basin) with blast furnace '
            'steelmaking and rolling mills. The Temirtau steelworks — built in the '
            'Soviet era — is one of the most polluting industrial sites in Central Asia, '
            'with coal dust, coke oven gas, and blast furnace emissions making Temirtau '
            'regularly feature on Kazakhstan\'s most polluted cities list. Multiple '
            'government-imposed environmental compliance deadlines have been missed.'
        ),
        # EcoIQ = 18×0.35 + 38×0.25 + 42×0.20 + 42×0.10 + 28×0.10 = 31.1
        'score_pollution_footprint': 18,
        'score_reduction_progress':  38,
        'score_investment':          42,
        'score_transparency':        42,
        'score_community_impact':    28,
    },

    # ── 12. Pavlodar Petrochemical — 26.4 Major Polluter ────────────────────
    {
        'name':         'Pavlodar Petrochemical',
        'sector':       'chemical',
        'country':      'Kazakhstan',
        'city':         'Pavlodar',
        'founded_year': 1978,
        'employee_count': 4_800,
        'annual_revenue_usd': 420_000_000,
        'is_public':    False,
        'verified':     False,
        'is_featured':  False,
        'website':      'https://ppk.kz',
        'description': (
            'Pavlodar Petrochemical Plant processes crude oil into aviation fuels, '
            'diesel, and lubricants. Built in the Soviet era and never fully modernised, '
            'the plant operates well below European fuel quality and environmental '
            'standards. Benzene and VOC emissions from open-top storage tanks have '
            'been cited repeatedly by Kazakhstan\'s Environmental Code enforcement '
            'authority. A planned KZT 180 billion modernisation project has been '
            'deferred twice due to financing constraints.'
        ),
        # EcoIQ = 15×0.35 + 32×0.25 + 35×0.20 + 28×0.10 + 22×0.10 = 26.45
        'score_pollution_footprint': 15,
        'score_reduction_progress':  32,
        'score_investment':          35,
        'score_transparency':        28,
        'score_community_impact':    22,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# PROJECTS  (30+ entries, keyed by company name)
# ─────────────────────────────────────────────────────────────────────────────

PROJECTS = {

    # ── KEGOC ────────────────────────────────────────────────────────────────
    'KEGOC': [
        {
            'name': 'Smart Grid Modernisation — National Backbone',
            'project_type': 'power_modern',
            'status': 'active',
            'start_date': datetime.date(2021, 1, 1),
            'completion_date': datetime.date(2026, 12, 31),
            'investment_usd': 850_000_000,
            'co2_reduction_tonnes': 380_000,
            'pm25_reduction_kg': None,
            'households_helped': 2_200_000,
            'location': 'National power grid, Kazakhstan',
            'description': (
                'Replacement of 1,800 ageing substations with digital IEC 61850 '
                'equipment and SCADA upgrade across the full 24,500 km transmission '
                'network. Smart grid technology reduces transmission losses from 12.4% '
                'to a target of 6.8%, equivalent to avoiding construction of two '
                '500 MW coal plants. Phase 1 (780 substations) complete and live.'
            ),
            'verified': True,
        },
        {
            'name': 'Renewables Integration — North-South Interconnect Upgrade',
            'project_type': 'power_modern',
            'status': 'completed',
            'start_date': datetime.date(2019, 3, 1),
            'completion_date': datetime.date(2023, 6, 30),
            'investment_usd': 420_000_000,
            'co2_reduction_tonnes': 620_000,
            'pm25_reduction_kg': None,
            'households_helped': 1_800_000,
            'location': 'Central Kazakhstan corridor',
            'description': (
                'Doubling of North–South 500 kV interconnect capacity to 1,400 MW, '
                'enabling transmission of renewables from wind-rich northern steppe '
                'to industrial and population centres in the south. Project directly '
                'enabled the grid connection of 1,650 MW of new wind and solar capacity '
                'from independent power producers.'
            ),
            'verified': True,
        },
        {
            'name': 'Grid Loss Reduction — Energy Efficiency Programme',
            'project_type': 'other',
            'status': 'active',
            'start_date': datetime.date(2022, 1, 1),
            'completion_date': None,
            'investment_usd': 95_000_000,
            'co2_reduction_tonnes': 210_000,
            'pm25_reduction_kg': None,
            'households_helped': None,
            'location': 'National power grid, Kazakhstan',
            'description': (
                'Systematic cable replacement, reactive power compensation (12,400 MVAR '
                'of new capacitor banks), and transformer upgrades to cut technical '
                'losses. ISO 50001 energy management certified at all 172 high-voltage '
                'substations. Annual loss reduction of 2.3 TWh achieved in 2023.'
            ),
            'verified': True,
        },
    ],

    # ── QazaqGaz ─────────────────────────────────────────────────────────────
    'QazaqGaz': [
        {
            'name': 'Rural Gasification — South Kazakhstan Phase 1',
            'project_type': 'gasification',
            'status': 'completed',
            'start_date': datetime.date(2019, 3, 1),
            'completion_date': datetime.date(2022, 12, 31),
            'investment_usd': 380_000_000,
            'co2_reduction_tonnes': 1_240_000,
            'pm25_reduction_kg': 86_000_000,
            'households_helped': 280_000,
            'location': 'Turkestan Region, Kazakhstan',
            'description': (
                'Extension of gas pipeline networks to 847 villages in South Kazakhstan, '
                'replacing coal and wood burning stoves with clean gas appliances. '
                'Project eliminated seasonal PM2.5 spikes that previously exceeded WHO '
                'limits by 8× during winter heating season. Coal consumption in the '
                'project area fell by 1.4 million tonnes annually.'
            ),
            'verified': True,
        },
        {
            'name': 'Coal Stove Replacement — Zhambyl Region',
            'project_type': 'coal_stove',
            'status': 'completed',
            'start_date': datetime.date(2020, 6, 1),
            'completion_date': datetime.date(2022, 10, 31),
            'investment_usd': 42_000_000,
            'co2_reduction_tonnes': 186_000,
            'pm25_reduction_kg': 12_400_000,
            'households_helped': 44_000,
            'location': 'Zhambyl Region, Kazakhstan',
            'description': (
                'Direct coal stove replacement programme in 44,000 rural households in '
                'Zhambyl Region. Each household received a gas conversion kit, new '
                'condensing gas range, and connection subsidy. Average household annual '
                'heating cost fell 62%. Child respiratory hospital admissions in the '
                'project area decreased 38% in the following winter.'
            ),
            'verified': True,
        },
        {
            'name': 'Methane Leak Detection & Repair (LDAR)',
            'project_type': 'methane',
            'status': 'active',
            'start_date': datetime.date(2023, 1, 1),
            'completion_date': None,
            'investment_usd': 95_000_000,
            'co2_reduction_tonnes': 320_000,
            'pm25_reduction_kg': None,
            'households_helped': None,
            'location': 'National pipeline network — 17,400 km',
            'description': (
                'Deployment of drone-based and satellite methane detection (GHGSat) '
                'across 17,400 km of gas pipeline. LDAR programme identifies and '
                'repairs leaks quarterly. Year-1 results: 34% reduction in fugitive '
                'emissions vs. 2022 baseline. Programme aligns with Global Methane '
                'Pledge (COP26) and OGMP Level 4 reporting.'
            ),
            'verified': True,
        },
        {
            'name': 'North Kazakhstan Gasification Phase 2',
            'project_type': 'gasification',
            'status': 'active',
            'start_date': datetime.date(2023, 4, 1),
            'completion_date': datetime.date(2026, 6, 30),
            'investment_usd': 510_000_000,
            'co2_reduction_tonnes': 1_650_000,
            'pm25_reduction_kg': 110_000_000,
            'households_helped': 370_000,
            'location': 'North Kazakhstan, Kostanay, Pavlodar regions',
            'description': (
                'Gas main and distribution network construction in three northern '
                'oblasts where coal dominates residential heating. Targets 370,000 '
                'households and 1,200 boiler houses currently using coal. Coal stove '
                'replacement grants of KZT 120,000 available to low-income households. '
                'Phase 2 includes conversion of 84 public buildings (schools, hospitals).'
            ),
            'verified': False,
        },
    ],

    # ── Air Astana ───────────────────────────────────────────────────────────
    'Air Astana': [
        {
            'name': 'Fleet Renewal — Airbus A320neo Family',
            'project_type': 'other',
            'status': 'active',
            'start_date': datetime.date(2018, 1, 1),
            'completion_date': datetime.date(2027, 12, 31),
            'investment_usd': 3_200_000_000,
            'co2_reduction_tonnes': 480_000,
            'pm25_reduction_kg': 2_100_000,
            'households_helped': None,
            'location': 'Route network — 64 destinations',
            'description': (
                'Full replacement of A320ceo and Boeing 737 Classic fleet with A320neo, '
                'A321XLR, and A321neo aircraft. LEAP-1A engines reduce fuel burn by '
                '20% per seat vs. outgoing fleet. 28 aircraft delivered as of Q1 2024; '
                '12 more on order. Absolute CO₂ emissions down 14% since 2019 despite '
                '18% growth in seat capacity.'
            ),
            'verified': True,
        },
        {
            'name': 'Sustainable Aviation Fuel (SAF) Pilot — LHR/FRA Routes',
            'project_type': 'other',
            'status': 'active',
            'start_date': datetime.date(2023, 6, 1),
            'completion_date': datetime.date(2025, 12, 31),
            'investment_usd': 18_000_000,
            'co2_reduction_tonnes': 12_400,
            'pm25_reduction_kg': 180_000,
            'households_helped': None,
            'location': 'London Heathrow & Frankfurt routes',
            'description': (
                'Blend of up to 10% HEFA (Hydroprocessed Esters and Fatty Acids) SAF '
                'on long-haul European routes. Partnered with Neste (Finland) for SAF '
                'supply and Carbon Engineering for lifecycle accounting. Pilot covers '
                '4 weekly roundtrip flights; data informing 2025–2030 blending mandate '
                'compliance strategy.'
            ),
            'verified': True,
        },
        {
            'name': 'Airport Ground Operations Electrification',
            'project_type': 'other',
            'status': 'completed',
            'start_date': datetime.date(2021, 3, 1),
            'completion_date': datetime.date(2023, 9, 30),
            'investment_usd': 24_000_000,
            'co2_reduction_tonnes': 8_200,
            'pm25_reduction_kg': 420_000,
            'households_helped': None,
            'location': 'Nursultan Nazarbayev International Airport',
            'description': (
                'Replacement of 68 diesel ground support vehicles (tugs, belt loaders, '
                'catering trucks, buses) with electric equivalents charged via solar '
                'canopy at the new terminal. Ramp diesel fuel consumption down 91%. '
                'PM2.5 around aircraft parking bays reduced 78% by continuous '
                'monitoring sensor comparison.'
            ),
            'verified': True,
        },
    ],

    # ── Kazatomprom ──────────────────────────────────────────────────────────
    'Kazatomprom': [
        {
            'name': 'Legacy Uranium Site Remediation — North Kazakhstan',
            'project_type': 'water_cleanup',
            'status': 'active',
            'start_date': datetime.date(2018, 9, 1),
            'completion_date': datetime.date(2026, 12, 31),
            'investment_usd': 156_000_000,
            'co2_reduction_tonnes': None,
            'pm25_reduction_kg': None,
            'households_helped': 120_000,
            'location': 'North Kazakhstan Oblast — 3 legacy sites',
            'description': (
                'Remediation of three Soviet-era uranium mining sites covering 4,800 ha. '
                'Programme includes groundwater monitoring (247 wells), waste rock '
                'stabilisation, radioactive waste encapsulation, and revegetation. '
                '47,000 m³ of contaminated soil removed and isolated to date. Local '
                'well water now meets WHO radiological limits within project perimeter. '
                'IAEA peer review completed 2022 with satisfactory rating.'
            ),
            'verified': True,
        },
        {
            'name': 'Wind Power — Inkai Mine Complex',
            'project_type': 'renewable',
            'status': 'completed',
            'start_date': datetime.date(2021, 3, 1),
            'completion_date': datetime.date(2023, 7, 31),
            'investment_usd': 78_000_000,
            'co2_reduction_tonnes': 62_000,
            'pm25_reduction_kg': None,
            'households_helped': None,
            'location': 'Sozak District, Turkestan Region',
            'description': (
                '28 MW wind farm (14 × Enercon E-115 turbines) powering uranium mine '
                'operations at Inkai JV (Kazatomprom 60%, Cameco 40%). Wind energy '
                'covers 68% of mine electricity demand. Reduces diesel generator use '
                'by 93%. Project economics improved by a 15-year fixed-price PPA with '
                'the Inkai site.'
            ),
            'verified': True,
        },
        {
            'name': 'Steppe Restoration & Native Tree Planting',
            'project_type': 'tree_planting',
            'status': 'active',
            'start_date': datetime.date(2022, 4, 1),
            'completion_date': None,
            'investment_usd': 8_500_000,
            'co2_reduction_tonnes': 18_000,
            'pm25_reduction_kg': None,
            'households_helped': None,
            'location': 'Kyzylorda Region — post-mine areas',
            'description': (
                'Planting of 2.4 million drought-resistant native trees and shrubs '
                '(saxaul, tamarisk, poplar) on disturbed land around former ISR '
                'wellfields. Employs 340 local residents in Kyzylorda Region. '
                'Species selection guided by Kazakh Academy of Sciences to maximise '
                'steppe biodiversity. 1.1 million trees planted and surviving as of '
                'end-2023 (46% survival rate above target).'
            ),
            'verified': True,
        },
    ],

    # ── KazMunayGas ──────────────────────────────────────────────────────────
    'KazMunayGas': [
        {
            'name': 'Associated Gas Utilisation — Kashagan Field',
            'project_type': 'methane',
            'status': 'completed',
            'start_date': datetime.date(2019, 4, 1),
            'completion_date': datetime.date(2022, 12, 31),
            'investment_usd': 680_000_000,
            'co2_reduction_tonnes': 2_800_000,
            'pm25_reduction_kg': 3_200_000,
            'households_helped': None,
            'location': 'Kashagan offshore field, Atyrau Region',
            'description': (
                'Construction of gas processing facilities to capture associated gas '
                'previously flared at Kashagan. Annual flaring down 87%, recovering '
                '3.2 bcm/year for domestic grid. Phase 1 completed 2021; Phase 2 '
                '(additional processing capacity) completed Dec 2022. Represents the '
                'largest single GHG abatement project in Kazakhstan\'s oil sector.'
            ),
            'verified': True,
        },
        {
            'name': 'Pavlodar Refinery — Euro-5 Modernisation',
            'project_type': 'power_modern',
            'status': 'active',
            'start_date': datetime.date(2022, 1, 1),
            'completion_date': datetime.date(2025, 6, 30),
            'investment_usd': 1_200_000_000,
            'co2_reduction_tonnes': 890_000,
            'pm25_reduction_kg': 22_000_000,
            'households_helped': None,
            'location': 'Pavlodar Refinery, Pavlodar Region',
            'description': (
                'Deep modernisation of Pavlodar Refinery to Euro-5 fuel standards: '
                'new HDS (hydrodesulphurisation) unit, catalytic reformer upgrade, '
                'isomerisation unit, and biological wastewater treatment. SO₂ '
                'emissions to fall 94%; NOₓ by 67%; benzene 89% vs. 2020 baseline. '
                'Pavlodar city air quality improvement is the primary co-benefit.'
            ),
            'verified': True,
        },
        {
            'name': 'Solar Power — Tengiz Oilfield',
            'project_type': 'renewable',
            'status': 'planned',
            'start_date': datetime.date(2025, 6, 1),
            'completion_date': datetime.date(2027, 12, 31),
            'investment_usd': 210_000_000,
            'co2_reduction_tonnes': 145_000,
            'pm25_reduction_kg': None,
            'households_helped': None,
            'location': 'Tengiz Field, Atyrau Region',
            'description': (
                '100 MW solar PV plant to supply Tengiz field operations, replacing '
                'diesel generation units. Combined with 40 MW battery storage for '
                'overnight supply. Part of KMG\'s Scope 2 net-zero target for '
                'operated assets by 2035. EPC tender awarded to Masdar (UAE) Nov 2024.'
            ),
            'verified': False,
        },
    ],

    # ── Kazzinc ──────────────────────────────────────────────────────────────
    'Kazzinc': [
        {
            'name': 'Ust-Kamenogorsk Zinc Plant — SO₂ Acid Plant Expansion',
            'project_type': 'filters',
            'status': 'completed',
            'start_date': datetime.date(2019, 1, 1),
            'completion_date': datetime.date(2022, 8, 31),
            'investment_usd': 320_000_000,
            'co2_reduction_tonnes': 195_000,
            'pm25_reduction_kg': 18_000_000,
            'households_helped': 340_000,
            'location': 'Ust-Kamenogorsk Metallurgical Complex',
            'description': (
                'Installation of double contact–double absorption (DCDA) sulphuric '
                'acid plant to capture SO₂ off-gases from zinc roasting and smelting. '
                'SO₂ capture rate increased from 62% to 98.6%. Acid production of '
                '820,000 t/year sold to fertilizer manufacturers. Ust-Kamenogorsk '
                'city annual mean SO₂ concentration fell from 84 μg/m³ to 11 μg/m³.'
            ),
            'verified': True,
        },
        {
            'name': 'Coal Stove Replacement — Ridder City',
            'project_type': 'coal_stove',
            'status': 'completed',
            'start_date': datetime.date(2021, 8, 1),
            'completion_date': datetime.date(2023, 3, 31),
            'investment_usd': 28_000_000,
            'co2_reduction_tonnes': 84_000,
            'pm25_reduction_kg': 5_600_000,
            'households_helped': 18_500,
            'location': 'Ridder (Leninogorsk), East Kazakhstan',
            'description': (
                'Company-funded programme replacing coal stoves in 18,500 worker '
                'households in the mining town of Ridder. Gas boilers provided free '
                'to households earning below median income; subsidised for others. '
                'Programme reduced Ridder\'s winter AQI from hazardous (250+) to '
                'moderate (<100) — a first in the city\'s 200-year history.'
            ),
            'verified': True,
        },
        {
            'name': 'Lead & Precious Metals Waste Reduction',
            'project_type': 'waste',
            'status': 'active',
            'start_date': datetime.date(2022, 6, 1),
            'completion_date': datetime.date(2025, 12, 31),
            'investment_usd': 45_000_000,
            'co2_reduction_tonnes': 32_000,
            'pm25_reduction_kg': 8_200_000,
            'households_helped': None,
            'location': 'Ust-Kamenogorsk lead smelter',
            'description': (
                'Hydrometallurgical reprocessing of historic slag dumps (12M tonnes) '
                'to recover lead, silver, gold, and bismuth, simultaneously eliminating '
                'a legacy pollution source. New bag filter house on the lead blast '
                'furnace captures 99.4% of dust. Lead in ambient air near the plant '
                'reduced from 4.2 μg/m³ to 0.38 μg/m³ (WHO limit: 0.5 μg/m³).'
            ),
            'verified': True,
        },
    ],

    # ── Samruk Energy ────────────────────────────────────────────────────────
    'Samruk Energy': [
        {
            'name': 'Ekibastuz GRES-2 Filter & Desulphurisation Retrofit',
            'project_type': 'filters',
            'status': 'completed',
            'start_date': datetime.date(2019, 6, 1),
            'completion_date': datetime.date(2022, 3, 31),
            'investment_usd': 290_000_000,
            'co2_reduction_tonnes': 740_000,
            'pm25_reduction_kg': 48_000_000,
            'households_helped': 800_000,
            'location': 'Ekibastuz GRES-2, Pavlodar Region',
            'description': (
                'Replacement of all 4 electrostatic precipitators and installation of '
                'wet flue gas desulphurisation (FGD) units at 1,000 MW coal plant. '
                'Fly ash capture: 88% → 99.7%. SO₂ emissions: −82%. NOₓ reduced 45% '
                'via low-NOₓ burner retrofit. Ekibastuz city PM10 annual mean fell '
                'from 112 μg/m³ to 38 μg/m³ — first time within national standard.'
            ),
            'verified': True,
        },
        {
            'name': 'Balkhash Wind Farm — 100 MW Phase 1',
            'project_type': 'renewable',
            'status': 'completed',
            'start_date': datetime.date(2020, 1, 1),
            'completion_date': datetime.date(2023, 9, 30),
            'investment_usd': 185_000_000,
            'co2_reduction_tonnes': 210_000,
            'pm25_reduction_kg': None,
            'households_helped': 95_000,
            'location': 'Lake Balkhash, Karaganda Region',
            'description': (
                '100 MW onshore wind farm: 50 × Vestas V150 turbines commissioned '
                '2021–2023. Capacity factor 38% (above project base case of 34%). '
                'Supplies clean electricity to ~95,000 homes, offsetting coal dispatch '
                'from Balkhash thermal plant. Grid integration supported by KEGOC '
                'interconnect upgrade (concurrent project). Phase 2 (150 MW) FID '
                'expected Q3 2025.'
            ),
            'verified': True,
        },
        {
            'name': 'Shardara Hydroelectric Rehabilitation',
            'project_type': 'power_modern',
            'status': 'active',
            'start_date': datetime.date(2023, 3, 1),
            'completion_date': datetime.date(2025, 12, 31),
            'investment_usd': 120_000_000,
            'co2_reduction_tonnes': 95_000,
            'pm25_reduction_kg': None,
            'households_helped': 60_000,
            'location': 'Shardara Dam, Turkestan Region',
            'description': (
                'Full rehabilitation of 3 × 80 MW Francis turbine units, restoring '
                'design capacity and improving efficiency 18%. New fish passage '
                'structures and sediment management dredging will restore Syr Darya '
                'downstream ecosystem. Works on Unit 1 completed and reconnected to '
                'grid Q4 2023; Units 2 and 3 in progress.'
            ),
            'verified': True,
        },
    ],

    # ── ERG ──────────────────────────────────────────────────────────────────
    'ERG': [
        {
            'name': 'Kazchrome Aktobe Plant — Baghouse Filter Upgrade',
            'project_type': 'filters',
            'status': 'active',
            'start_date': datetime.date(2022, 4, 1),
            'completion_date': datetime.date(2025, 6, 30),
            'investment_usd': 180_000_000,
            'co2_reduction_tonnes': 85_000,
            'pm25_reduction_kg': 24_000_000,
            'households_helped': 260_000,
            'location': 'Aktobe Ferroalloys Plant, Aktobe Region',
            'description': (
                'Replacement of wet scrubbers with state-of-the-art pulse-jet baghouse '
                'filters on all 24 submerged arc furnaces at the world\'s largest '
                'ferrochrome plant. Chromium VI in ambient air near the plant falls '
                'below EU Industrial Emissions Directive limits for first time. '
                'Dust suppression on ore storage yards also included.'
            ),
            'verified': True,
        },
        {
            'name': 'SSGPO Iron Ore — Closed-Loop Water Recycling',
            'project_type': 'water_cleanup',
            'status': 'completed',
            'start_date': datetime.date(2020, 6, 1),
            'completion_date': datetime.date(2023, 3, 31),
            'investment_usd': 95_000_000,
            'co2_reduction_tonnes': 48_000,
            'pm25_reduction_kg': None,
            'households_helped': None,
            'location': 'SSGPO, Rudny, Kostanay Region',
            'description': (
                'Full closed-loop water recycling system for Sokolov-Sarbay iron ore '
                'concentrator: new thickeners, filtration building, and return pipeline '
                'network. Fresh water withdrawal from Tobol River reduced by 85% '
                '(from 62M m³/year to 9.3M m³/year). Tailings slurry solids recovery '
                'increased, reducing tailings pond area expansion requirements.'
            ),
            'verified': True,
        },
        {
            'name': 'Methane Capture — Karaganda Coal Mine Ventilation',
            'project_type': 'methane',
            'status': 'active',
            'start_date': datetime.date(2023, 1, 1),
            'completion_date': datetime.date(2026, 12, 31),
            'investment_usd': 55_000_000,
            'co2_reduction_tonnes': 140_000,
            'pm25_reduction_kg': None,
            'households_helped': 28_000,
            'location': 'Karaganda Coal Basin, Karaganda Region',
            'description': (
                'Capture and utilisation of ventilation air methane (VAM) and '
                'drainage methane from 4 deep coal mines. Captured methane combusted '
                'in dedicated power plant (12 MW), supplying electricity to mining '
                'operations and 28,000 nearby households. Methane abatement equal '
                'to 140,000 t CO₂e/year (methane GWP100 factor of 28 applied).'
            ),
            'verified': False,
        },
    ],

    # ── KazPhosphate ─────────────────────────────────────────────────────────
    'KazPhosphate': [
        {
            'name': 'Phosphogypsum Stack Management & Capping',
            'project_type': 'waste',
            'status': 'active',
            'start_date': datetime.date(2021, 3, 1),
            'completion_date': datetime.date(2027, 12, 31),
            'investment_usd': 62_000_000,
            'co2_reduction_tonnes': None,
            'pm25_reduction_kg': 6_800_000,
            'households_helped': 85_000,
            'location': 'Taraz Industrial Zone, Zhambyl Region',
            'description': (
                'Progressive capping of 160 ha phosphogypsum stack with HDPE liner '
                'and topsoil/vegetation layer, plus leachate collection system. '
                'Eliminates wind-blown fluoride dust that was the primary air quality '
                'concern for Taraz city residents. Fluoride in ambient air near the '
                'stack reduced from 18 μg/m³ to 2.1 μg/m³ (WHO guideline: 1 μg/m³).'
            ),
            'verified': True,
        },
        {
            'name': 'Electrolysis Line Energy Efficiency Modernisation',
            'project_type': 'power_modern',
            'status': 'completed',
            'start_date': datetime.date(2020, 9, 1),
            'completion_date': datetime.date(2022, 12, 31),
            'investment_usd': 38_000_000,
            'co2_reduction_tonnes': 62_000,
            'pm25_reduction_kg': None,
            'households_helped': None,
            'location': 'Zhambyl Phosphorus Plant, Taraz',
            'description': (
                'Replacement of 1960s-era electrolysis cells with modern bipolar '
                'membrane technology. Specific energy consumption for yellow phosphorus '
                'production fell from 14,800 kWh/t to 11,200 kWh/t (−24%). Annual '
                'electricity saving of 186 GWh reduces Scope 2 emissions by 62,000 t '
                'CO₂ and saves KZT 4.2 billion/year in energy costs.'
            ),
            'verified': True,
        },
    ],

    # ── Kazakhmys ────────────────────────────────────────────────────────────
    'Kazakhmys': [
        {
            'name': 'Balkhash Copper Smelter — SO₂ Capture Plant',
            'project_type': 'filters',
            'status': 'active',
            'start_date': datetime.date(2022, 10, 1),
            'completion_date': datetime.date(2026, 6, 30),
            'investment_usd': 480_000_000,
            'co2_reduction_tonnes': 220_000,
            'pm25_reduction_kg': 38_000_000,
            'households_helped': 420_000,
            'location': 'Balkhash Copper Smelter, Karaganda Region',
            'description': (
                'Installation of double-contact sulphuric acid plant to capture SO₂ '
                'from copper smelting converters and flash smelting furnace. Design '
                'capture rate 98.5%. Project delayed 18 months due to supply chain '
                'disruptions; anode furnace module commissioned Q2 2024. Full capture '
                'plant commissioning expected Q4 2025. Balkhash city SO₂ emergency '
                'events expected to reduce from 47/year to <3/year.'
            ),
            'verified': True,
        },
        {
            'name': 'East Kazakhstan Tailings Rehabilitation',
            'project_type': 'water_cleanup',
            'status': 'active',
            'start_date': datetime.date(2021, 5, 1),
            'completion_date': datetime.date(2025, 9, 30),
            'investment_usd': 95_000_000,
            'co2_reduction_tonnes': None,
            'pm25_reduction_kg': 12_000_000,
            'households_helped': 68_000,
            'location': 'Zhezkazgan tailings complex, Karaganda Region',
            'description': (
                'Stabilisation and revegetation of 1,400 ha of historic copper '
                'tailings to prevent wind erosion. Copper, arsenic, and cadmium in '
                'Zhezkazgan city dust reduced by 71% in wind tunnel sampling. '
                'Drainage collection system prevents acid mine drainage entering '
                'Kengir River. 340 ha revegetated with halophyte species to date.'
            ),
            'verified': False,
        },
    ],

    # ── ArcelorMittal Temirtau ────────────────────────────────────────────────
    'ArcelorMittal Temirtau': [
        {
            'name': 'Blast Furnace Gas Recovery & Utilisation',
            'project_type': 'filters',
            'status': 'active',
            'start_date': datetime.date(2023, 1, 1),
            'completion_date': datetime.date(2026, 3, 31),
            'investment_usd': 145_000_000,
            'co2_reduction_tonnes': 380_000,
            'pm25_reduction_kg': 28_000_000,
            'households_helped': 210_000,
            'location': 'Temirtau Steelworks, Karaganda Region',
            'description': (
                'Capture of blast furnace gas (BFG) currently flared or vented — '
                'calorific value 3.2 MJ/Nm³ — to fuel reheating furnaces and '
                'on-site power plant (120 MW). BFG cleaning train includes '
                'venturi scrubber and bag filter. Expected to eliminate 12 emergency '
                'flaring events per year that cause acute pollution episodes. '
                'Project subject to EU lender requirements (EBRD co-finance).'
            ),
            'verified': False,
        },
        {
            'name': 'Coking Plant Dust & Gas Collection',
            'project_type': 'filters',
            'status': 'planned',
            'start_date': datetime.date(2025, 3, 1),
            'completion_date': datetime.date(2028, 12, 31),
            'investment_usd': 210_000_000,
            'co2_reduction_tonnes': 180_000,
            'pm25_reduction_kg': 52_000_000,
            'households_helped': 340_000,
            'location': 'Temirtau Coke Oven Battery, Karaganda Region',
            'description': (
                'Enclosed coal charging system, coke oven door seals, and combined '
                'gas collection on all 5 coke batteries (280 ovens total). PAH, '
                'benzene, and H₂S emissions from coking operations are the leading '
                'carcinogenic air quality concern for Temirtau\'s 183,000 residents. '
                'Project financing pending; MOU signed with EBRD for €160M loan.'
            ),
            'verified': False,
        },
    ],

    # ── Pavlodar Petrochemical ────────────────────────────────────────────────
    'Pavlodar Petrochemical': [
        {
            'name': 'Tank Farm VOC Vapour Recovery',
            'project_type': 'filters',
            'status': 'active',
            'start_date': datetime.date(2023, 6, 1),
            'completion_date': datetime.date(2025, 6, 30),
            'investment_usd': 22_000_000,
            'co2_reduction_tonnes': 18_000,
            'pm25_reduction_kg': 2_400_000,
            'households_helped': None,
            'location': 'Pavlodar Refinery Tank Farm',
            'description': (
                'Installation of floating roof seals and vapour recovery units (VRU) '
                'on 38 atmospheric storage tanks containing crude, naphtha, and '
                'aviation fuel. Reduces fugitive VOC (benzene) emissions by an '
                'estimated 2,400 t/year. Required under Kazakhstan\'s 2023 '
                'Environmental Code enforcement notice EP-2023-4821.'
            ),
            'verified': False,
        },
        {
            'name': 'Wastewater Treatment Plant Upgrade',
            'project_type': 'water_cleanup',
            'status': 'planned',
            'start_date': datetime.date(2025, 1, 1),
            'completion_date': datetime.date(2027, 12, 31),
            'investment_usd': 58_000_000,
            'co2_reduction_tonnes': None,
            'pm25_reduction_kg': None,
            'households_helped': 95_000,
            'location': 'Pavlodar Refinery, Pavlodar Region',
            'description': (
                'Replacement of 1970s gravity separator and API skimmer wastewater '
                'system with dissolved air flotation, biological treatment (MBR), and '
                'advanced oxidation (UV/H₂O₂). Irtysh River discharge to meet '
                'Kazakhstan Class 3 water quality standard for oils, phenols, and '
                'heavy metals. Financing under negotiation with Development Bank of '
                'Kazakhstan.'
            ),
            'verified': False,
        },
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# EVIDENCE  (2–3 documents per company)
# ─────────────────────────────────────────────────────────────────────────────

EVIDENCE = {
    'KEGOC': [
        {
            'doc_type': 'audit_report',
            'title': 'ISO 50001 Energy Management Certification — Bureau Veritas 2023',
            'url': 'https://kegoc.kz/en/sustainable-development/',
            'date_issued': datetime.date(2023, 11, 28),
            'issuer': 'Bureau Veritas Kazakhstan',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'government_report',
            'title': 'National Power Grid Losses Reduction Progress — MIIR Kazakhstan 2023',
            'url': 'https://miir.gov.kz/',
            'date_issued': datetime.date(2023, 12, 15),
            'issuer': 'Ministry of Industry and Infrastructure, Kazakhstan',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'engineering_audit',
            'title': 'Smart Grid Phase 1 Commissioning Verification — Siemens AG',
            'url': 'https://kegoc.kz/',
            'date_issued': datetime.date(2024, 1, 10),
            'issuer': 'Siemens Energy AG',
            'verification_status': 'verified',
        },
    ],
    'QazaqGaz': [
        {
            'doc_type': 'audit_report',
            'title': 'Environmental Performance Audit 2023 — EY Kazakhstan',
            'url': 'https://qazaqgaz.kz/en/sustainability',
            'date_issued': datetime.date(2023, 12, 15),
            'issuer': 'Ernst & Young Kazakhstan',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'government_report',
            'title': 'Ministry of Ecology — Gasification Progress Report Q4 2023',
            'url': 'https://ecologia.gov.kz/',
            'date_issued': datetime.date(2024, 1, 20),
            'issuer': 'Ministry of Ecology and Natural Resources, Kazakhstan',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'satellite',
            'title': 'Pipeline Methane Emissions — GHGSat Satellite Survey 2023',
            'url': 'https://www.ghgsat.com/',
            'date_issued': datetime.date(2023, 10, 5),
            'issuer': 'GHGSat Inc.',
            'verification_status': 'verified',
        },
    ],
    'Air Astana': [
        {
            'doc_type': 'audit_report',
            'title': 'IATA Environmental Assessment — 4-Star Rating 2023',
            'url': 'https://www.iata.org/en/programs/environment/',
            'date_issued': datetime.date(2023, 9, 14),
            'issuer': 'International Air Transport Association (IATA)',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'engineering_audit',
            'title': 'Fleet Fuel Efficiency Verification — Airbus Flight Hour Services',
            'url': 'https://airastana.com/global/en-gb/About-Us/Sustainability',
            'date_issued': datetime.date(2024, 2, 28),
            'issuer': 'Airbus Flight Operations',
            'verification_status': 'verified',
        },
    ],
    'Kazatomprom': [
        {
            'doc_type': 'audit_report',
            'title': 'Annual ESG Report 2023 — PwC Kazakhstan Limited Assurance',
            'url': 'https://kazatomprom.kz/en/pages/sustainability',
            'date_issued': datetime.date(2024, 3, 28),
            'issuer': 'PricewaterhouseCoopers Kazakhstan',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'government_report',
            'title': 'IAEA Safety Review — ISR Operations (OSART Mission 2022)',
            'url': 'https://www.iaea.org/',
            'date_issued': datetime.date(2022, 11, 10),
            'issuer': 'International Atomic Energy Agency',
            'verification_status': 'verified',
        },
    ],
    'KazMunayGas': [
        {
            'doc_type': 'audit_report',
            'title': 'Sustainability Report 2023 — KPMG Limited Assurance',
            'url': 'https://kmg.kz/en/sustainability/',
            'date_issued': datetime.date(2024, 4, 1),
            'issuer': 'KPMG Forensic Kazakhstan',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'satellite',
            'title': 'Kashagan Flaring Reduction — Sentinel-3 & Viirs Satellite Data',
            'url': 'https://globalflaring.com/',
            'date_issued': datetime.date(2023, 6, 1),
            'issuer': 'European Space Agency (Copernicus Programme)',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'government_report',
            'title': 'Associated Gas Utilisation Certificate — Ministry of Energy Kazakhstan',
            'url': 'https://energo.gov.kz/',
            'date_issued': datetime.date(2023, 2, 22),
            'issuer': 'Ministry of Energy, Republic of Kazakhstan',
            'verification_status': 'verified',
        },
    ],
    'Kazzinc': [
        {
            'doc_type': 'engineering_audit',
            'title': 'Acid Plant Commissioning & SO₂ Capture Verification — SGS Kazakhstan',
            'url': 'https://kazzinc.com/en/sustainability/',
            'date_issued': datetime.date(2022, 10, 18),
            'issuer': 'SGS Kazakhstan Ltd.',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'audit_report',
            'title': 'ESG Disclosure Report 2023 — Deloitte Assurance',
            'url': 'https://kazzinc.com/en/sustainability/',
            'date_issued': datetime.date(2024, 3, 15),
            'issuer': 'Deloitte & Touche LLP',
            'verification_status': 'verified',
        },
    ],
    'Samruk Energy': [
        {
            'doc_type': 'engineering_audit',
            'title': 'GRES-2 Post-Retrofit Emissions Verification — Bureau Veritas',
            'url': 'https://samruk-energy.kz/',
            'date_issued': datetime.date(2022, 6, 15),
            'issuer': 'Bureau Veritas Kazakhstan',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'audit_report',
            'title': 'Integrated Sustainability Report 2023 — Deloitte',
            'url': 'https://samruk-energy.kz/en/sustainability/',
            'date_issued': datetime.date(2024, 2, 20),
            'issuer': 'Deloitte & Touche LLP, Kazakhstan',
            'verification_status': 'verified',
        },
    ],
    'ERG': [
        {
            'doc_type': 'audit_report',
            'title': 'ERG Sustainability Performance Report 2023 — EY Limited Assurance',
            'url': 'https://erg.kz/en/sustainability/',
            'date_issued': datetime.date(2024, 4, 5),
            'issuer': 'Ernst & Young LLP',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'government_report',
            'title': 'Chromium VI Emissions Compliance Certificate — Ministry of Ecology 2023',
            'url': 'https://ecologia.gov.kz/',
            'date_issued': datetime.date(2023, 12, 8),
            'issuer': 'Ministry of Ecology and Natural Resources, Kazakhstan',
            'verification_status': 'pending',
        },
    ],
    'KazPhosphate': [
        {
            'doc_type': 'government_report',
            'title': 'Phosphogypsum Stack Environmental Monitoring — Zhambyl Oblast 2023',
            'url': 'https://ecologia.gov.kz/',
            'date_issued': datetime.date(2023, 11, 30),
            'issuer': 'Department of Ecology, Zhambyl Region',
            'verification_status': 'pending',
        },
    ],
    'Kazakhmys': [
        {
            'doc_type': 'engineering_audit',
            'title': 'Balkhash Smelter Stack Emission Measurements — Intertek 2023',
            'url': 'https://kazakhmys.com/',
            'date_issued': datetime.date(2023, 9, 22),
            'issuer': 'Intertek Caleb Brett',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'government_report',
            'title': 'Environmental Compliance Order EP-2023-7142 — Ministry of Ecology',
            'url': 'https://ecologia.gov.kz/',
            'date_issued': datetime.date(2023, 5, 14),
            'issuer': 'Ministry of Ecology and Natural Resources, Kazakhstan',
            'verification_status': 'pending',
        },
    ],
    'ArcelorMittal Temirtau': [
        {
            'doc_type': 'government_report',
            'title': 'Environmental Compliance Inspection Report 2023 — Ministry of Ecology',
            'url': 'https://ecologia.gov.kz/',
            'date_issued': datetime.date(2023, 8, 10),
            'issuer': 'Ministry of Ecology and Natural Resources, Kazakhstan',
            'verification_status': 'pending',
        },
        {
            'doc_type': 'audit_report',
            'title': 'ArcelorMittal Group Climate Action Report 2023',
            'url': 'https://corporate.arcelormittal.com/climate-action',
            'date_issued': datetime.date(2024, 3, 1),
            'issuer': 'ArcelorMittal Global Sustainability',
            'verification_status': 'verified',
        },
    ],
    'Pavlodar Petrochemical': [
        {
            'doc_type': 'government_report',
            'title': 'Environmental Enforcement Notice EP-2023-4821 — VOC Emissions',
            'url': 'https://ecologia.gov.kz/',
            'date_issued': datetime.date(2023, 7, 3),
            'issuer': 'Ministry of Ecology and Natural Resources, Kazakhstan',
            'verification_status': 'pending',
        },
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# SCORE HISTORY — 5 years (60 monthly snapshots) per company
# Each company's trajectory reflects its narrative:
#   KEGOC      — steady high performer, slight annual improvement
#   QazaqGaz   — strong upward trend (gasification programme)
#   Air Astana — rapid improvement from 2021 fleet renewal
#   KMG        — choppy: improved after Kashagan flaring fix, then plateau
#   ArcelorMittal Temirtau — declining then bottoming out
# ─────────────────────────────────────────────────────────────────────────────

def _build_monthly_history(pillar_history_60: list[dict]) -> list[dict]:
    """
    Given a list of 60 dicts (one per month, oldest first) with keys:
      date, pollution, reduction, investment, transparency, community
    return a list of snapshot dicts ready for ScoreHistory.objects.create().
    """
    from league.scoring import compute_ecoiq_score
    snapshots = []
    for m in pillar_history_60:
        score = compute_ecoiq_score(
            m['pollution'], m['reduction'], m['investment'],
            m['transparency'], m['community']
        )
        snapshots.append({
            'date':       m['date'],
            'ecoiq_score': score,
            'score_pollution_footprint': m['pollution'],
            'score_reduction_progress':  m['reduction'],
            'score_investment':          m['investment'],
            'score_transparency':        m['transparency'],
            'score_community_impact':    m['community'],
        })
    return snapshots


def _months_ago(n: int) -> datetime.date:
    """First day of the month n months ago."""
    today = datetime.date.today()
    month = today.month - n
    year  = today.year + month // 12
    month = month % 12
    if month == 0:
        month = 12
        year -= 1
    return datetime.date(year, month, 1)


def _lerp_int(start: int, end: int, step: int, total: int) -> int:
    """Linear interpolation from start to end over total steps."""
    return round(start + (end - start) * step / (total - 1))


def _build_pillar_history(
    start: dict, end: dict, n: int = 60,
    jitter: dict | None = None
) -> list[dict]:
    """
    Linearly interpolate pillar scores from `start` to `end` over `n` months.
    Optional `jitter` adds per-pillar noise (± half-value) to each point.
    """
    import random
    random.seed(42)
    keys = ('pollution', 'reduction', 'investment', 'transparency', 'community')
    history = []
    for i in range(n):
        d = _months_ago(n - 1 - i)
        row = {'date': d}
        for k in keys:
            v = _lerp_int(start[k], end[k], i, n)
            if jitter and k in jitter:
                v += random.randint(-jitter[k], jitter[k])
            row[k] = max(0, min(100, v))
        history.append(row)
    return history


# Per-company 5-year pillar trajectories
HISTORIES = {

    'KEGOC': _build_pillar_history(
        start={'pollution': 85, 'reduction': 72, 'investment': 76, 'transparency': 70, 'community': 68},
        end=  {'pollution': 92, 'reduction': 85, 'investment': 88, 'transparency': 82, 'community': 80},
        jitter={'pollution': 1, 'reduction': 2, 'investment': 2},
    ),

    'QazaqGaz': _build_pillar_history(
        start={'pollution': 52, 'reduction': 48, 'investment': 55, 'transparency': 50, 'community': 60},
        end=  {'pollution': 68, 'reduction': 72, 'investment': 74, 'transparency': 65, 'community': 85},
        jitter={'reduction': 2, 'community': 3},
    ),

    'Air Astana': _build_pillar_history(
        start={'pollution': 55, 'reduction': 48, 'investment': 55, 'transparency': 62, 'community': 50},
        end=  {'pollution': 72, 'reduction': 78, 'investment': 75, 'transparency': 80, 'community': 68},
        jitter={'pollution': 2, 'reduction': 3},
    ),

    'Kazatomprom': _build_pillar_history(
        start={'pollution': 55, 'reduction': 44, 'investment': 40, 'transparency': 62, 'community': 40},
        end=  {'pollution': 62, 'reduction': 58, 'investment': 55, 'transparency': 78, 'community': 52},
        jitter={'reduction': 2},
    ),

    'KazMunayGas': _build_pillar_history(
        # Improved sharply 2021–22 (Kashagan), then plateaued
        start={'pollution': 40, 'reduction': 35, 'investment': 50, 'transparency': 55, 'community': 38},
        end=  {'pollution': 55, 'reduction': 62, 'investment': 65, 'transparency': 70, 'community': 48},
        jitter={'pollution': 2, 'reduction': 3, 'investment': 2},
    ),

    'Kazzinc': _build_pillar_history(
        start={'pollution': 38, 'reduction': 40, 'investment': 42, 'transparency': 48, 'community': 36},
        end=  {'pollution': 55, 'reduction': 60, 'investment': 58, 'transparency': 65, 'community': 50},
        jitter={'pollution': 2, 'reduction': 2},
    ),

    'Samruk Energy': _build_pillar_history(
        start={'pollution': 22, 'reduction': 30, 'investment': 42, 'transparency': 48, 'community': 35},
        end=  {'pollution': 35, 'reduction': 52, 'investment': 60, 'transparency': 62, 'community': 45},
        jitter={'reduction': 3, 'investment': 2},
    ),

    'ERG': _build_pillar_history(
        start={'pollution': 28, 'reduction': 32, 'investment': 38, 'transparency': 40, 'community': 32},
        end=  {'pollution': 38, 'reduction': 48, 'investment': 50, 'transparency': 55, 'community': 42},
        jitter={'pollution': 2, 'reduction': 2},
    ),

    'KazPhosphate': _build_pillar_history(
        start={'pollution': 35, 'reduction': 38, 'investment': 42, 'transparency': 38, 'community': 44},
        end=  {'pollution': 44, 'reduction': 52, 'investment': 55, 'transparency': 48, 'community': 55},
        jitter={'reduction': 2},
    ),

    'Kazakhmys': _build_pillar_history(
        # Slight improvements but still low — slow change
        start={'pollution': 18, 'reduction': 28, 'investment': 32, 'transparency': 38, 'community': 28},
        end=  {'pollution': 22, 'reduction': 42, 'investment': 44, 'transparency': 48, 'community': 38},
        jitter={'pollution': 1, 'reduction': 2},
    ),

    'ArcelorMittal Temirtau': _build_pillar_history(
        # Declining early, very slight uptick in latest year from BFG project start
        start={'pollution': 20, 'reduction': 45, 'investment': 48, 'transparency': 45, 'community': 30},
        end=  {'pollution': 18, 'reduction': 38, 'investment': 42, 'transparency': 42, 'community': 28},
        jitter={'reduction': 3, 'pollution': 1},
    ),

    'Pavlodar Petrochemical': _build_pillar_history(
        start={'pollution': 18, 'reduction': 28, 'investment': 30, 'transparency': 25, 'community': 18},
        end=  {'pollution': 15, 'reduction': 32, 'investment': 35, 'transparency': 28, 'community': 22},
        jitter={'reduction': 2},
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# MANAGEMENT COMMAND
# ─────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = (
        'Seed EcoIQ Good Deeds League with 12 Kazakhstan demo companies, '
        '30+ projects, 5-year score history, and evidence documents.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush', action='store_true',
            help='Delete all existing league data before seeding',
        )

    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write('Flushing existing league data…')
            ScoreHistory.objects.all().delete()
            Evidence.objects.all().delete()
            EnvironmentalProject.objects.all().delete()
            Company.objects.all().delete()
            self.stdout.write(self.style.WARNING('  ✓ Deleted.'))

        company_count   = 0
        project_count   = 0
        evidence_count  = 0
        history_count   = 0

        for data in COMPANIES:
            name = data['name']

            company, created = Company.objects.update_or_create(
                slug=slugify(name),
                defaults={
                    'name':         name,
                    'sector':       data['sector'],
                    'country':      data['country'],
                    'city':         data['city'],
                    'founded_year': data['founded_year'],
                    'employee_count':     data['employee_count'],
                    'annual_revenue_usd': data['annual_revenue_usd'],
                    'is_public':    data['is_public'],
                    'verified':     data['verified'],
                    'is_featured':  data['is_featured'],
                    'website':      data['website'],
                    'description':  data['description'],
                    'score_pollution_footprint': data['score_pollution_footprint'],
                    'score_reduction_progress':  data['score_reduction_progress'],
                    'score_investment':           data['score_investment'],
                    'score_transparency':         data['score_transparency'],
                    'score_community_impact':     data['score_community_impact'],
                }
            )
            action = '✓ Created' if created else '○ Updated'
            self.stdout.write(
                f'  {action}: {company.name:35s}  '
                f'EcoIQ {company.ecoiq_score:5.1f}  ({company.status_label})'
            )
            company_count += 1

            # ── Projects ─────────────────────────────────────────────────────
            for pdata in PROJECTS.get(name, []):
                EnvironmentalProject.objects.update_or_create(
                    company=company,
                    name=pdata['name'],
                    defaults={k: v for k, v in pdata.items() if k != 'name'},
                )
                project_count += 1

            # ── Evidence ──────────────────────────────────────────────────────
            for edata in EVIDENCE.get(name, []):
                Evidence.objects.update_or_create(
                    company=company,
                    title=edata['title'],
                    defaults={k: v for k, v in edata.items() if k != 'title'},
                )
                evidence_count += 1

            # ── 5-year score history ───────────────────────────────────────
            pillar_months = HISTORIES.get(name, [])
            if pillar_months:
                ScoreHistory.objects.filter(company=company).delete()
                snapshots = _build_monthly_history(pillar_months)
                objs = [
                    ScoreHistory(
                        company=company,
                        date=snap['date'],
                        ecoiq_score=Decimal(str(snap['ecoiq_score'])),
                        score_pollution_footprint=snap['score_pollution_footprint'],
                        score_reduction_progress=snap['score_reduction_progress'],
                        score_investment=snap['score_investment'],
                        score_transparency=snap['score_transparency'],
                        score_community_impact=snap['score_community_impact'],
                    )
                    for snap in snapshots
                ]
                ScoreHistory.objects.bulk_create(objs, ignore_conflicts=True)
                history_count += len(objs)

        # Assign ranks
        rerank_all()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'✓ Seeded {company_count} companies  |  '
            f'{project_count} projects  |  '
            f'{evidence_count} evidence docs  |  '
            f'{history_count} monthly history snapshots'
        ))
        self.stdout.write(self.style.SUCCESS(
            '  Leaderboard: http://127.0.0.1:8000/league/'
        ))
