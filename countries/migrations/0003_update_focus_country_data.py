"""
Data migration: update macro/climate data for the 4 EcoIQ focus markets.

Sources (all verified June 2026):
  GDP / Growth / Population / Inflation -- IMF World Economic Outlook, April 2026
  CO2 (fossil)  -- EDGAR 2024 report (2023 data, most recent available)
  Renewables     -- per-country sources noted in data_sources field

Fields flagged 'needs_update':  fossil_fuel_dependency, industrial_gdp_share,
  estimated_transition_gap_usd -- kept from existing DB; no verified update found.
"""
import datetime
from django.db import migrations


# Verified data -- do NOT change without adding a source citation.
FOCUS_COUNTRIES = {
    # ---- United Kingdom -------------------------------------------------------
    "United Kingdom": {
        "gdp_usd":                4_260_000_000_000,   # $4.26 T   IMF WEO Apr 2026
        "gdp_growth_pct":         0.8,                 # %         IMF WEO Apr 2026
        "inflation_pct":          3.2,                 # %         IMF WEO Apr 2026
        "population_millions":    69.9,                # M         IMF WEO Apr 2026
        "co2_megatonnes":         292.0,               # Mt CO2    EDGAR 2024 (2023 data)
        "renewable_energy_share": 40.0,                # % elec    DESNZ/Carbon Brief 2025
        # fossil_fuel_dependency:  keep existing (79%) -- no verified update
        # industrial_gdp_share:    keep existing (18.5%) -- no verified update
        # estimated_transition_gap_usd: keep existing -- no verified update
        "data_sources": (
            "GDP/growth/inflation/population: IMF WEO April 2026; "
            "CO2 (fossil): EDGAR 2024 report (2023 data); "
            "Renewables (electricity): DESNZ/Carbon Brief 2025. "
            "Fossil dependency & industrial GDP share: flagged for update -- last set prior to 2024."
        ),
        "data_last_updated": datetime.date(2026, 6, 4),
    },

    # ---- Kazakhstan -----------------------------------------------------------
    "Kazakhstan": {
        "gdp_usd":                360_460_000_000,     # $360.46 B IMF WEO Apr 2026
        "gdp_growth_pct":         4.6,                 # %         IMF WEO Apr 2026
        "population_millions":    21.1,                # M         IMF WEO Apr 2026
        "co2_megatonnes":         341.0,               # Mt CO2-eq KZ national inventory 2021
        "renewable_energy_share": 6.0,                 # % elec    KZ national energy data 2023
        # fossil_fuel_dependency:  keep existing (94%) -- consistent with national data
        # industrial_gdp_share:    keep existing (36.4%) -- no verified update
        "data_sources": (
            "GDP/growth/population: IMF WEO April 2026; "
            "CO2: Kazakhstan national GHG inventory 2021 (most recent officially submitted); "
            "Renewables (electricity): Kazakhstan national energy data 2023. "
            "Fossil dependency flagged for update."
        ),
        "data_last_updated": datetime.date(2026, 6, 4),
    },

    # ---- Saudi Arabia ---------------------------------------------------------
    "Saudi Arabia": {
        "gdp_usd":                1_389_000_000_000,   # $1.389 T  IMF WEO Apr 2026
        "gdp_growth_pct":         3.1,                 # %         IMF WEO Apr 2026
        "population_millions":    35.2,                # M         IMF WEO Apr 2026
        "co2_megatonnes":         623.0,               # Mt CO2    EDGAR / Our World in Data 2023
        "renewable_energy_share": 2.2,                 # % elec    Ember 2024
        # fossil_fuel_dependency:  keep existing (99%) -- consistent with energy mix
        # industrial_gdp_share:    keep existing (44.2%) -- no verified update
        "data_sources": (
            "GDP/growth/population: IMF WEO April 2026; "
            "CO2 (fossil): EDGAR 2024 / Our World in Data (2023 data); "
            "Renewables (electricity): Ember 2024. "
            "Industrial GDP share flagged for update."
        ),
        "data_last_updated": datetime.date(2026, 6, 4),
    },

    # ---- Turkiye (stored as 'Turkey' in DB) -----------------------------------
    "Turkey": {
        "name":                   "Türkiye",       # official spelling (u-umlaut ü)
        "gdp_usd":                1_640_000_000_000,   # $1.640 T  IMF WEO Apr 2026
        "gdp_growth_pct":         3.4,                 # %         IMF WEO Apr 2026
        "population_millions":    87.9,                # M         IMF WEO Apr 2026
        "co2_megatonnes":         446.0,               # Mt CO2    EDGAR / Worldometer 2023
        "renewable_energy_share": 45.5,                # % elec    Ember Turkiye Elec. Review 2025
        # fossil_fuel_dependency, industrial_gdp_share: not in existing DB -- not added
        "data_sources": (
            "GDP/growth/population: IMF WEO April 2026; "
            "CO2 (fossil): EDGAR 2024 / Worldometer (2023 data, ~446 Mt); "
            "Renewables (electricity): Ember Turkiye Electricity Review 2025 (2024 data). "
            "Name updated to official spelling 'Türkiye' (slug 'turkey' unchanged for URL stability)."
        ),
        "data_last_updated": datetime.date(2026, 6, 4),
    },
}


def update_country_data(apps, schema_editor):
    CountryProfile = apps.get_model('countries', 'CountryProfile')

    for lookup_name, fields in FOCUS_COUNTRIES.items():
        try:
            country = CountryProfile.objects.get(name=lookup_name)
        except CountryProfile.DoesNotExist:
            # Maybe it was already renamed in a previous run
            new_name = fields.get('name', lookup_name)
            try:
                country = CountryProfile.objects.get(name=new_name)
            except CountryProfile.DoesNotExist:
                print(f'  [SKIP] CountryProfile not found: {lookup_name!r} or {new_name!r}')
                continue

        for field, value in fields.items():
            if field == 'name' and country.name != value:
                country.name = value
            elif field != 'name':
                setattr(country, field, value)

        country.save()
        print(f'  [OK] Updated: {country.name}')


def reverse_update(apps, schema_editor):
    # Intentionally not reversing data -- forward migration is idempotent.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('countries', '0002_add_macro_provenance_fields'),
    ]

    operations = [
        migrations.RunPython(
            update_country_data,
            reverse_code=reverse_update,
        ),
    ]
