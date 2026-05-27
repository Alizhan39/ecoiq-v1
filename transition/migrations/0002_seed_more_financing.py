"""
Data migration — seed additional FinancingOpportunity records.
Uses update_or_create so running twice is safe.
"""
from django.db import migrations

EXTRA_INSTRUMENTS = [
    # ── Innovation & Technology Funds ──────────────────────────────────────────
    {
        'institution_name': 'Innovate UK',
        'programme_name':   'Industrial Decarbonisation Challenge',
        'acronym':          'IUK',
        'source_type':      'infra_grant',
        'instrument':       'grant',
        'eligible_sectors': [],
        'eligible_countries': ['United Kingdom'],
        'eligible_regions': ['Western Europe'],
        'focus_areas':      ['industrial', 'energy_efficiency', 'coal_transition', 'renewable'],
        'min_ticket_usd':   500_000,
        'max_ticket_usd':   20_000_000,
        'typical_tenor_years': None,
        'typical_interest_rate': 0.0,
        'description': (
            'UK Research & Innovation grant programmes supporting industrial decarbonisation, '
            'clean technology scale-up, and net-zero manufacturing transitions.'
        ),
        'eligibility_criteria': 'UK-registered entity; project must demonstrate clear pathway to commercialisation',
        'url': 'https://www.ukri.org/councils/innovate-uk/',
        'hq_country': 'United Kingdom',
        'brand_colour': '#e40034',
    },
    {
        'institution_name': 'Breakthrough Energy Ventures',
        'programme_name':   'Industrial Innovation Fund',
        'acronym':          'BEV',
        'source_type':      'private_equity',
        'instrument':       'equity',
        'eligible_sectors': ['energy', 'chemical', 'metallurgy', 'other'],
        'eligible_countries': [],
        'eligible_regions': ['Global'],
        'focus_areas':      ['clean_energy', 'renewable', 'industrial', 'coal_transition'],
        'min_ticket_usd':   5_000_000,
        'max_ticket_usd':   100_000_000,
        'description': (
            'Breakthrough Energy Ventures backs technologies that reduce greenhouse gas emissions '
            'at scale — including industrial decarbonisation, green hydrogen, and long-duration storage.'
        ),
        'eligibility_criteria': 'Deep-tech companies with potential for gigaton-scale emissions reduction',
        'url': 'https://www.breakthroughenergy.org',
        'hq_country': 'United States',
        'brand_colour': '#1a73e8',
    },
    {
        'institution_name': 'EU Innovation Fund',
        'programme_name':   'Large-Scale Competitive Call',
        'acronym':          'EU IF',
        'source_type':      'infra_grant',
        'instrument':       'grant',
        'eligible_sectors': ['energy', 'chemical', 'metallurgy'],
        'eligible_countries': [],
        'eligible_regions': ['Western Europe', 'Eastern Europe'],
        'focus_areas':      ['industrial', 'coal_transition', 'energy_efficiency', 'clean_energy', 'renewable'],
        'min_ticket_usd':   8_000_000,
        'max_ticket_usd':   500_000_000,
        'typical_tenor_years': None,
        'typical_interest_rate': 0.0,
        'description': (
            'EU Innovation Fund — world\'s largest decarbonisation grant programme. '
            'Funds innovative industrial low-carbon technologies in EU+EEA countries, '
            'covering up to 60% of relevant costs.'
        ),
        'eligibility_criteria': 'EU/EEA-registered entity; project must avoid 1M+ tonnes CO₂/year',
        'url': 'https://climate.ec.europa.eu/eu-action/eu-emissions-trading-system-eu-ets/innovation-fund_en',
        'hq_country': 'Belgium',
        'brand_colour': '#003399',
    },
    {
        'institution_name': 'KfW Development Bank',
        'programme_name':   'Green Transition Finance',
        'acronym':          'KfW',
        'source_type':      'dfi',
        'instrument':       'loan',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Global', 'Eastern Europe', 'Central Asia', 'Sub-Saharan Africa'],
        'focus_areas':      ['renewable', 'energy_efficiency', 'industrial', 'coal_transition', 'water'],
        'min_ticket_usd':   5_000_000,
        'max_ticket_usd':   400_000_000,
        'typical_tenor_years': 20.0,
        'typical_interest_rate': 2.0,
        'grace_period_years': 5.0,
        'description': (
            'KfW finances sustainable development projects globally, focusing on climate change '
            'mitigation, energy transition, and green infrastructure in emerging and developing markets.'
        ),
        'eligibility_criteria': 'Partner country government or private sector; bankable project with ESG standards',
        'url': 'https://www.kfw-entwicklungsbank.de',
        'hq_country': 'Germany',
        'brand_colour': '#00945e',
    },
    {
        'institution_name': 'Bpifrance',
        'programme_name':   'Industrial Transition Guarantee',
        'acronym':          'BPI',
        'source_type':      'blended',
        'instrument':       'guarantee',
        'eligible_sectors': [],
        'eligible_countries': ['France'],
        'eligible_regions': ['Western Europe'],
        'focus_areas':      ['industrial', 'energy_efficiency', 'renewable', 'coal_transition'],
        'min_ticket_usd':   1_000_000,
        'max_ticket_usd':   100_000_000,
        'description': (
            'France\'s public investment bank provides financing, guarantees, and equity '
            'for industrial modernisation, clean technology, and transition finance in France and Europe.'
        ),
        'eligibility_criteria': 'French-registered SME or mid-cap; transition project with measurable impact',
        'url': 'https://www.bpifrance.fr',
        'hq_country': 'France',
        'brand_colour': '#00a0e3',
    },
    # ── Multilateral & Sovereign ────────────────────────────────────────────────
    {
        'institution_name': 'Global Energy Alliance for People and Planet',
        'programme_name':   'Just Energy Transition Fund',
        'acronym':          'GEAPP',
        'source_type':      'blended',
        'instrument':       'blended',
        'eligible_sectors': ['energy', 'oil_gas'],
        'eligible_countries': [],
        'eligible_regions': ['Sub-Saharan Africa', 'South Asia', 'Southeast Asia'],
        'focus_areas':      ['coal_transition', 'renewable', 'clean_energy', 'energy_efficiency'],
        'min_ticket_usd':   10_000_000,
        'max_ticket_usd':   200_000_000,
        'description': (
            'GEAPP mobilises blended finance for clean energy access and fossil fuel transition '
            'in emerging economies, combining grant, concessional debt, and technical assistance.'
        ),
        'eligibility_criteria': 'Eligible developing country; energy transition project with community benefit',
        'url': 'https://www.energyalliance.org',
        'hq_country': 'United States',
        'brand_colour': '#ff6b35',
    },
    {
        'institution_name': 'African Development Bank',
        'programme_name':   'Climate Action Window',
        'acronym':          'AfDB',
        'source_type':      'dfi',
        'instrument':       'loan',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Sub-Saharan Africa'],
        'focus_areas':      ['renewable', 'coal_transition', 'energy_efficiency', 'water', 'industrial'],
        'min_ticket_usd':   5_000_000,
        'max_ticket_usd':   300_000_000,
        'typical_tenor_years': 20.0,
        'typical_interest_rate': 2.5,
        'grace_period_years': 5.0,
        'description': (
            'African Development Bank provides financing for infrastructure modernisation, '
            'industrial transition, and clean energy across Africa, with a 40% climate finance target.'
        ),
        'eligibility_criteria': 'AfDB member country, sovereign or private sector, ESG compliance required',
        'url': 'https://www.afdb.org',
        'hq_country': 'Ivory Coast',
        'brand_colour': '#009900',
    },
    {
        'institution_name': 'Inter-American Development Bank',
        'programme_name':   'Green Finance Initiative',
        'acronym':          'IDB',
        'source_type':      'dfi',
        'instrument':       'loan',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Latin America'],
        'focus_areas':      ['renewable', 'industrial', 'energy_efficiency', 'coal_transition', 'water'],
        'min_ticket_usd':   5_000_000,
        'max_ticket_usd':   250_000_000,
        'typical_tenor_years': 18.0,
        'typical_interest_rate': 3.0,
        'description': (
            'IDB finances sustainable development across Latin America, targeting climate finance, '
            'industrial decarbonisation, and energy transition in member countries.'
        ),
        'eligibility_criteria': 'IDB member country, sovereign guarantee or private sector, compliance framework',
        'url': 'https://www.iadb.org',
        'hq_country': 'United States',
        'brand_colour': '#00a0dc',
    },
    # ── Green Bond & Transition Finance ────────────────────────────────────────
    {
        'institution_name': 'Climate Bonds Initiative',
        'programme_name':   'Transition Bonds Programme',
        'acronym':          'CBI',
        'source_type':      'green_bond',
        'instrument':       'bond',
        'eligible_sectors': ['energy', 'oil_gas', 'mining', 'chemical', 'metallurgy'],
        'eligible_countries': [],
        'eligible_regions': ['Global'],
        'focus_areas':      ['coal_transition', 'industrial', 'methane', 'energy_efficiency'],
        'min_ticket_usd':   50_000_000,
        'max_ticket_usd':   None,
        'description': (
            'CBI\'s Transition Finance programme certifies bonds issued by high-emitting companies '
            'with credible, science-based decarbonisation strategies — enabling access to '
            'green capital markets for industrial transition.'
        ),
        'eligibility_criteria': 'Science-based targets; credible 2050 net-zero pathway; third-party verification',
        'url': 'https://www.climatebonds.net',
        'hq_country': 'United Kingdom',
        'brand_colour': '#0d9960',
    },
    {
        'institution_name': 'International Finance Facility for Education',
        'programme_name':   'Workforce Transition Finance',
        'acronym':          'IFFEd',
        'source_type':      'blended',
        'instrument':       'blended',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Sub-Saharan Africa', 'South Asia', 'Southeast Asia', 'Central Asia'],
        'focus_areas':      ['industrial', 'coal_transition', 'energy_efficiency'],
        'min_ticket_usd':   2_000_000,
        'max_ticket_usd':   50_000_000,
        'description': (
            'Blended finance for workforce reskilling and community support in just transition '
            'contexts — particularly relevant for coal communities transitioning to new industries.'
        ),
        'eligibility_criteria': 'Lower-middle or upper-middle income countries; community transition programme',
        'url': 'https://www.iffed.org',
        'hq_country': 'United Kingdom',
        'brand_colour': '#f7931e',
    },
    # ── Sovereign & Industrial Modernization ────────────────────────────────────
    {
        'institution_name': 'US Department of Energy',
        'programme_name':   'Loan Programs Office — Industrial Decarbonization',
        'acronym':          'DOE LPO',
        'source_type':      'dfi',
        'instrument':       'loan',
        'eligible_sectors': ['energy', 'chemical', 'metallurgy', 'other'],
        'eligible_countries': ['United States'],
        'eligible_regions': ['North America'],
        'focus_areas':      ['industrial', 'energy_efficiency', 'renewable', 'clean_energy', 'coal_transition'],
        'min_ticket_usd':   10_000_000,
        'max_ticket_usd':   10_000_000_000,
        'typical_tenor_years': 25.0,
        'typical_interest_rate': 4.0,
        'description': (
            'DOE Loan Programs Office provides direct loans and loan guarantees for innovative '
            'clean energy and industrial decarbonisation projects in the United States.'
        ),
        'eligibility_criteria': 'US-based project; innovative clean energy technology; commercial readiness',
        'url': 'https://www.energy.gov/lpo',
        'hq_country': 'United States',
        'brand_colour': '#003087',
    },
    {
        'institution_name': 'Sustainable Development Investment Partnership',
        'programme_name':   'Industrial Infrastructure Platform',
        'acronym':          'SDIP',
        'source_type':      'blended',
        'instrument':       'blended',
        'eligible_sectors': [],
        'eligible_countries': [],
        'eligible_regions': ['Sub-Saharan Africa', 'South Asia', 'Southeast Asia', 'Central Asia', 'MENA'],
        'focus_areas':      ['industrial', 'energy_efficiency', 'renewable', 'water', 'coal_transition'],
        'min_ticket_usd':   20_000_000,
        'max_ticket_usd':   500_000_000,
        'description': (
            'SDIP mobilises public and private capital for infrastructure modernisation in '
            'developing countries, providing risk-sharing and co-financing to crowd in private investment.'
        ),
        'eligibility_criteria': 'Developing country; bankable infrastructure project; demonstrable development impact',
        'url': 'https://www.sdipglobal.org',
        'hq_country': 'Switzerland',
        'brand_colour': '#3355ff',
    },
]


def seed_extra(apps, schema_editor):
    FinancingOpportunity = apps.get_model('transition', 'FinancingOpportunity')
    for data in EXTRA_INSTRUMENTS:
        FinancingOpportunity.objects.update_or_create(
            institution_name=data['institution_name'],
            programme_name=data.get('programme_name', ''),
            defaults={k: v for k, v in data.items()
                      if k not in ('institution_name', 'programme_name')},
        )


def unseed_extra(apps, schema_editor):
    FinancingOpportunity = apps.get_model('transition', 'FinancingOpportunity')
    names = {d['institution_name'] for d in EXTRA_INSTRUMENTS}
    FinancingOpportunity.objects.filter(institution_name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('transition', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_extra, reverse_code=unseed_extra),
    ]
