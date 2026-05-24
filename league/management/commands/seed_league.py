"""
python manage.py seed_league          # create demo data
python manage.py seed_league --flush  # delete existing league data first
"""
import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from league.models import Company, EnvironmentalProject, Evidence, ScoreHistory
from league.scoring import rerank_all


# ── Demo companies ─────────────────────────────────────────────────────────────

COMPANIES = [
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
            'managing the country\'s gas transmission, distribution, and supply infrastructure. '
            'The company transports natural gas to over 4 million households and is leading '
            'Kazakhstan\'s residential gasification programme, replacing coal and wood stoves '
            'in rural communities across 11 regions.'
        ),
        'score_pollution_footprint': 68,
        'score_reduction_progress':  72,
        'score_investment':          74,
        'score_transparency':        65,
        'score_community_impact':    85,
    },
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
            'KazMunayGas (KMG) is Kazakhstan\'s national oil and gas company, responsible '
            'for the exploration, production, refining, and transport of hydrocarbons. '
            'Operating across the full value chain, KMG accounts for ~27% of national oil '
            'production. The company has committed $2.1 billion to environmental modernisation '
            'through 2030, targeting a 15% reduction in greenhouse gas intensity.'
        ),
        'score_pollution_footprint': 38,
        'score_reduction_progress':  55,
        'score_investment':          62,
        'score_transparency':        70,
        'score_community_impact':    48,
    },
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
            'Kazatomprom is the world\'s largest uranium producer, supplying ~22% of global '
            'uranium output. Unlike conventional mining, in-situ recovery (ISR) technology '
            'minimises surface disturbance and water usage. The company is investing in '
            'environmental remediation of legacy Soviet-era uranium sites and renewable '
            'energy for mine operations.'
        ),
        'score_pollution_footprint': 62,
        'score_reduction_progress':  58,
        'score_investment':          55,
        'score_transparency':        78,
        'score_community_impact':    52,
    },
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
            'Samruk Energy is Kazakhstan\'s leading power generation company, operating '
            'coal-fired power plants, hydroelectric stations, and wind farms. The company '
            'supplies ~35% of Kazakhstan\'s electricity. Under its Green Energy 2030 '
            'strategy, Samruk Energy is investing KZT 500 billion in renewable capacity '
            'and modernising ageing coal plants with high-efficiency filters and turbines.'
        ),
        'score_pollution_footprint': 32,
        'score_reduction_progress':  50,
        'score_investment':          60,
        'score_transparency':        62,
        'score_community_impact':    45,
    },
]


# ── Projects per company ───────────────────────────────────────────────────────

PROJECTS = {
    'QazaqGaz': [
        {
            'name': 'Rural Gasification — South Kazakhstan',
            'project_type': 'gasification',
            'status': 'completed',
            'start_date': datetime.date(2020, 3, 1),
            'completion_date': datetime.date(2023, 11, 30),
            'investment_usd': 380_000_000,
            'co2_reduction_tonnes': 1_240_000,
            'pm25_reduction_kg': 86_000_000,
            'households_helped': 280_000,
            'location': 'Turkestan Region, Kazakhstan',
            'description': (
                'Extension of gas pipeline networks to 847 villages in South Kazakhstan, '
                'replacing coal and wood burning stoves with clean gas appliances. '
                'Project eliminated seasonal PM2.5 spikes that previously exceeded WHO limits '
                'by 8× during winter heating season.'
            ),
            'verified': True,
        },
        {
            'name': 'Coal Stove Replacement — Zhambyl Region',
            'project_type': 'coal_stove',
            'status': 'completed',
            'start_date': datetime.date(2021, 6, 1),
            'completion_date': datetime.date(2022, 10, 31),
            'investment_usd': 42_000_000,
            'co2_reduction_tonnes': 186_000,
            'pm25_reduction_kg': 12_400_000,
            'households_helped': 44_000,
            'location': 'Zhambyl Region, Kazakhstan',
            'description': (
                'Direct coal stove replacement programme in 44,000 rural households. '
                'Each household received a gas conversion kit, new gas range, and connection '
                'subsidy. Average household annual heating cost reduced by 62%.'
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
            'location': 'National pipeline network',
            'description': (
                'Deployment of drone-based and satellite methane detection across '
                '17,400 km of gas pipeline. LDAR programme identifies and repairs leaks '
                'quarterly. First-year results showed 34% reduction in fugitive emissions '
                'versus 2022 baseline.'
            ),
            'verified': True,
        },
    ],

    'KazMunayGas': [
        {
            'name': 'Associated Gas Utilisation — Kashagan Field',
            'project_type': 'filters',
            'status': 'completed',
            'start_date': datetime.date(2019, 4, 1),
            'completion_date': datetime.date(2022, 12, 31),
            'investment_usd': 680_000_000,
            'co2_reduction_tonnes': 2_800_000,
            'pm25_reduction_kg': 3_200_000,
            'households_helped': None,
            'location': 'Kashagan, Atyrau Region',
            'description': (
                'Construction of gas processing facilities to capture and utilise '
                'previously flared associated gas at Kashagan oilfield. Annual gas '
                'flaring reduced by 87%, recovering 3.2 billion cubic metres per year '
                'for sale into the domestic gas grid.'
            ),
            'verified': True,
        },
        {
            'name': 'Refinery Modernisation — Pavlodar',
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
                'Deep modernisation of Pavlodar Refinery to Euro-5 fuel standards, '
                'including desulphurisation units, catalytic cracking upgrades, and '
                'wastewater treatment plant. Project will reduce SO₂ emissions by 94% '
                'and NOₓ by 67% versus 2020 levels.'
            ),
            'verified': True,
        },
        {
            'name': 'Solar Power for Tengiz Operations',
            'project_type': 'renewable',
            'status': 'planned',
            'start_date': datetime.date(2025, 1, 1),
            'completion_date': datetime.date(2027, 12, 31),
            'investment_usd': 210_000_000,
            'co2_reduction_tonnes': 145_000,
            'pm25_reduction_kg': None,
            'households_helped': None,
            'location': 'Tengiz Field, Atyrau Region',
            'description': (
                '100 MW solar photovoltaic plant to power Tengiz oilfield operations, '
                'replacing diesel generation. Project part of KMG\'s commitment to achieve '
                'net-zero Scope 2 emissions by 2035.'
            ),
            'verified': False,
        },
    ],

    'Kazatomprom': [
        {
            'name': 'Legacy Site Remediation — North Kazakhstan',
            'project_type': 'water_cleanup',
            'status': 'active',
            'start_date': datetime.date(2018, 9, 1),
            'completion_date': datetime.date(2026, 12, 31),
            'investment_usd': 156_000_000,
            'co2_reduction_tonnes': None,
            'pm25_reduction_kg': None,
            'households_helped': 120_000,
            'location': 'North Kazakhstan Oblast',
            'description': (
                'Remediation of three Soviet-era uranium mining sites totalling 4,800 ha. '
                'Groundwater monitoring wells, waste rock stabilisation, and radioactive '
                'waste encapsulation. 47,000 m³ of contaminated soil removed and '
                'isolated to date. Local well water now meets WHO radiological standards '
                'within the project perimeter.'
            ),
            'verified': True,
        },
        {
            'name': 'Wind Power for Mine Operations — South Kazakhstan',
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
                'Installation of 28 MW wind farm to supply electricity to uranium '
                'mine operations at the Inkai joint venture. Wind energy now covers '
                '68% of mine\'s electricity demand, eliminating ~62,000 tonnes CO₂ annually.'
            ),
            'verified': True,
        },
        {
            'name': 'Tree Planting & Steppe Restoration',
            'project_type': 'tree_planting',
            'status': 'active',
            'start_date': datetime.date(2022, 4, 1),
            'completion_date': None,
            'investment_usd': 8_500_000,
            'co2_reduction_tonnes': 18_000,
            'pm25_reduction_kg': None,
            'households_helped': None,
            'location': 'Kyzylorda Region',
            'description': (
                'Planting of 2.4 million drought-resistant native trees and shrubs '
                'in areas around former mine sites. Programme employs 340 local workers '
                'and collaborates with Kazakh Academy of Sciences for species selection '
                'to maximise steppe biodiversity restoration.'
            ),
            'verified': True,
        },
    ],

    'Samruk Energy': [
        {
            'name': 'Ekibastuz GRES-2 Filter Modernisation',
            'project_type': 'filters',
            'status': 'completed',
            'start_date': datetime.date(2019, 6, 1),
            'completion_date': datetime.date(2022, 3, 31),
            'investment_usd': 290_000_000,
            'co2_reduction_tonnes': 740_000,
            'pm25_reduction_kg': 48_000_000,
            'households_helped': 800_000,
            'location': 'Ekibastuz, Pavlodar Region',
            'description': (
                'Replacement of all electrostatic precipitators and installation of '
                'flue gas desulphurisation units at 1000 MW coal plant. Fly ash capture '
                'rate improved from 88% to 99.7%. SO₂ emissions reduced by 82%. '
                'Air quality in Ekibastuz city now consistently within Kazakhstan standards.'
            ),
            'verified': True,
        },
        {
            'name': 'Balkhash Wind Farm Phase 1',
            'project_type': 'renewable',
            'status': 'completed',
            'start_date': datetime.date(2020, 1, 1),
            'completion_date': datetime.date(2023, 9, 30),
            'investment_usd': 185_000_000,
            'co2_reduction_tonnes': 210_000,
            'pm25_reduction_kg': None,
            'households_helped': 95_000,
            'location': 'Balkhash, Karaganda Region',
            'description': (
                '100 MW onshore wind farm on the shores of Lake Balkhash. 50 Vestas V150 '
                'turbines commissioned in three tranches 2021-2023. Now supplying clean '
                'electricity to ~95,000 homes and offsetting coal generation at Balkhash '
                'thermal plant.'
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
            'location': 'Shardara, Turkestan Region',
            'description': (
                'Full rehabilitation of 3 × 80 MW hydro units at Shardara Dam, '
                'restoring design capacity and increasing generation efficiency by 18%. '
                'Upgraded fish passages and sediment management will restore Syr Darya '
                'river ecosystem downstream of the dam.'
            ),
            'verified': True,
        },
    ],
}


# ── Evidence per company ──────────────────────────────────────────────────────

EVIDENCE = {
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
            'title': 'Ministry of Ecology — Gasification Progress Report Q3 2023',
            'url': 'https://ecologia.gov.kz/',
            'date_issued': datetime.date(2023, 9, 30),
            'issuer': 'Ministry of Ecology and Natural Resources, Kazakhstan',
            'verification_status': 'verified',
        },
    ],
    'KazMunayGas': [
        {
            'doc_type': 'audit_report',
            'title': 'Sustainability Report 2023 — KPMG Assurance',
            'url': 'https://kmg.kz/en/sustainability/',
            'date_issued': datetime.date(2024, 4, 1),
            'issuer': 'KPMG Forensic',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'satellite',
            'title': 'Kashagan Flaring Reduction — Sentinel-3 Satellite Data',
            'url': 'https://copernicusglobal.eu/',
            'date_issued': datetime.date(2023, 6, 1),
            'issuer': 'European Space Agency / Copernicus',
            'verification_status': 'verified',
        },
    ],
    'Kazatomprom': [
        {
            'doc_type': 'audit_report',
            'title': 'Annual Sustainability & ESG Report 2023',
            'url': 'https://kazatomprom.kz/en/pages/sustainability',
            'date_issued': datetime.date(2024, 3, 28),
            'issuer': 'PwC Kazakhstan',
            'verification_status': 'verified',
        },
        {
            'doc_type': 'government_report',
            'title': 'IAEA Safety Review — In-Situ Recovery Operations',
            'url': 'https://www.iaea.org/',
            'date_issued': datetime.date(2022, 11, 10),
            'issuer': 'International Atomic Energy Agency',
            'verification_status': 'verified',
        },
    ],
    'Samruk Energy': [
        {
            'doc_type': 'engineering_audit',
            'title': 'Ekibastuz GRES-2 Post-Retrofit Emissions Verification',
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
}


# ── Score history (6 months trending) ─────────────────────────────────────────

def _history(base_score, months=6, drift=2.0):
    """Generate <months> monthly score snapshots trending upward from base_score."""
    from datetime import date, timedelta
    today = date.today()
    result = []
    for i in range(months, 0, -1):
        # Approx first of month, months ago
        d = today.replace(day=1)
        for _ in range(i - 1):
            d = (d - timedelta(days=1)).replace(day=1)
        score = max(0, min(100, base_score - drift * (i - 1) + (i * 0.3)))
        result.append({'date': d, 'score': round(score, 1)})
    return result


# ── Command ───────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Seed EcoIQ Good Deeds League with demo company data'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Delete all existing league data before seeding')

    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write('Flushing existing league data…')
            ScoreHistory.objects.all().delete()
            Evidence.objects.all().delete()
            EnvironmentalProject.objects.all().delete()
            Company.objects.all().delete()
            self.stdout.write(self.style.WARNING('  Deleted.'))

        created_count = 0

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
                    'employee_count':      data['employee_count'],
                    'annual_revenue_usd':  data['annual_revenue_usd'],
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
            action = 'Created' if created else 'Updated'
            self.stdout.write(f'  {action}: {company} (EcoIQ {company.ecoiq_score})')
            created_count += 1

            # Projects
            for pdata in PROJECTS.get(name, []):
                proj, _ = EnvironmentalProject.objects.update_or_create(
                    company=company,
                    name=pdata['name'],
                    defaults={k: v for k, v in pdata.items() if k != 'name'},
                )

            # Evidence
            for edata in EVIDENCE.get(name, []):
                Evidence.objects.update_or_create(
                    company=company,
                    title=edata['title'],
                    defaults={k: v for k, v in edata.items() if k != 'title'},
                )

            # Score history
            base = float(company.ecoiq_score)
            ScoreHistory.objects.filter(company=company).delete()
            for snap in _history(base, months=6, drift=1.5):
                ScoreHistory.objects.create(
                    company=company,
                    date=snap['date'],
                    ecoiq_score=Decimal(str(snap['score'])),
                    score_pollution_footprint=company.score_pollution_footprint,
                    score_reduction_progress=company.score_reduction_progress,
                    score_investment=company.score_investment,
                    score_transparency=company.score_transparency,
                    score_community_impact=company.score_community_impact,
                )

        # Assign ranks
        rerank_all()
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Seeded {created_count} companies with projects, evidence, and score history.'
        ))
        self.stdout.write(self.style.SUCCESS(
            '  View at: http://127.0.0.1:8000/league/'
        ))
