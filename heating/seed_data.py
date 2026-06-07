"""
Khalifa Heat — canonical household package seed data.

Used by both the data migration and the `seed_heating_packages` management
command so packages exist in every environment (idempotent by slug).
"""

PACKAGE_SEED = [
    {
        'slug': 'diy-basic', 'name': 'Khalifa Heat DIY Basic', 'tier': 1, 'sort_order': 1,
        'target_customer': 'Handy owner or has own local master; budget-conscious villages',
        'included': 'Electric boiler 6–12 kW, thermostat, circuit breakers + RCD/УЗО, '
                    'pump/valve/safety group, connection kit to existing radiators, installation manual.',
        'not_included': 'Installation, electrician, radiator upgrades, insulation upgrades, warranty for self-install error.',
        'price_min_kzt': 900_000, 'price_max_kzt': 1_500_000, 'install_responsibility': 'customer',
    },
    {
        'slug': 'assisted', 'name': 'Khalifa Heat Assisted', 'tier': 2, 'sort_order': 2,
        'target_customer': 'Owner who wants help but is cost-conscious',
        'included': 'Basic kit plus supervised installation — our engineer guides the local master, '
                    'one site visit and commissioning.',
        'not_included': 'Materials beyond the kit, major rewiring, radiator upgrades, insulation upgrades.',
        'price_min_kzt': 1_700_000, 'price_max_kzt': 2_700_000, 'install_responsibility': 'shared',
    },
    {
        'slug': 'full-install', 'name': 'Khalifa Heat Full Install', 'tier': 3, 'sort_order': 3,
        'target_customer': 'Mainstream household wanting a turnkey job',
        'included': 'Basic kit plus full professional installation, commissioning and 1-year warranty.',
        'not_included': 'Insulation upgrade, major grid/meter upgrade.',
        'price_min_kzt': 2_500_000, 'price_max_kzt': 3_800_000, 'install_responsibility': 'ecoiq',
    },
    {
        'slug': 'smart-electric', 'name': 'Khalifa Heat Smart Electric', 'tier': 4, 'sort_order': 4,
        'target_customer': 'Tech-comfortable / better-off home, good grid',
        'included': 'Full install plus smart thermostat, app control, scheduling and buffer tank.',
        'not_included': 'Insulation upgrade, grid upgrade.',
        'price_min_kzt': 3_500_000, 'price_max_kzt': 5_000_000, 'install_responsibility': 'ecoiq',
    },
    {
        'slug': 'ready-plus', 'name': 'Khalifa Heat Ready+', 'tier': 5, 'sort_order': 5,
        'target_customer': 'Future-focused / larger or renovating home',
        'included': 'Smart Electric plus buffer tank sized for a heat pump, reinforced wiring, '
                    'and valving/space pre-plumbed for a future heat-pump upgrade.',
        'not_included': 'The heat pump unit itself, insulation, grid upgrade.',
        'price_min_kzt': 4_000_000, 'price_max_kzt': 6_000_000, 'install_responsibility': 'ecoiq',
    },
]
