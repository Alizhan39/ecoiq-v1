"""
seed_clean_heating_pilot — creates the ONE project anchor for the first
EcoIQ end-to-end vertical slice: "Almaty Clean Heating Pilot — 200 Homes".

GoldProject is used as the TEMPORARY generic project anchor per the approved
canonical-architecture decision (docs/adr-0001): commodity='other', every
gold-specific field left null (never populated with plausible fake numbers),
is_demo=True. The pilot represents a defined portfolio of approximately 200
coal-heated homes in Almaty or the surrounding region — it does NOT claim
any specific real municipality, district, or household list has been
selected.

Unlike seed_gold_intelligence_demo (which needs the Kazakhstan country row
for its map assets and bails without it), this command degrades safely: if
no Kazakhstan CountryProfile exists yet, the pilot is still created with
country=None and a warning, and a re-run after seed_countries attaches it.

Idempotent: update_or_create on a stable slug, safe to re-run.
"""
from django.core.management.base import BaseCommand

PILOT_SLUG = 'almaty-clean-heating-pilot-200-homes'
PILOT_NAME = 'Almaty Clean Heating Pilot — 200 Homes'


class Command(BaseCommand):
    help = 'Seeds the Almaty Clean Heating Pilot project anchor (first EcoIQ vertical slice).'

    def handle(self, *args, **options):
        from countries.models import CountryProfile
        from gold_intelligence.models import GoldProject

        country = CountryProfile.objects.filter(iso_code='KZ').first()
        if country is None:
            self.stdout.write(self.style.WARNING(
                'No Kazakhstan CountryProfile found (run seed_countries to attach one) — '
                'creating the pilot without a country link.'
            ))

        existed_before = GoldProject.objects.filter(slug=PILOT_SLUG).exists()

        project, created = GoldProject.objects.update_or_create(
            slug=PILOT_SLUG,
            defaults=dict(
                name=PILOT_NAME,
                commodity='other',
                country=country,
                region='Almaty region',
                status='exploration',
                description=(
                    'First EcoIQ end-to-end clean-heating vertical-slice pilot: a defined pilot '
                    'portfolio of approximately 200 coal-heated homes in Almaty or the surrounding '
                    'region, evaluated for transition to cleaner heating (heat pumps, district '
                    'heating, insulation, or other evidence-supported interventions). No specific '
                    'municipality, district, or household list has been selected or claimed — the '
                    'scope figure of 200 homes is a pilot design target, not a verified enrolment '
                    'count. All project evidence carries its own real/estimated/illustrative '
                    'labelling; nothing on this record is a verified real-world outcome.'
                ),
                data_sources=(
                    'Pilot design scope only — no technical report, household survey, or '
                    'measured baseline has been attached yet.'
                ),
                is_demo=True,
                # Every gold-specific/technical/financial field is deliberately
                # left null — this is a clean-heating pilot, and no real figure
                # exists yet. update_or_create defaults must say so explicitly,
                # otherwise a re-run after someone hand-edits the row would not
                # reset a fabricated value back to honest-null.
                ore_grade_g_per_tonne=None, resource_tonnes=None, recovery_rate_pct=None,
                mine_life_years=None, expected_annual_production_oz=None,
                total_capex_usd=None, annual_opex_usd=None,
                cash_cost_usd_per_oz=None, aisc_usd_per_oz=None,
                gold_price_assumption_usd_per_oz=None, discount_rate_pct=None,
                total_committed_capital_usd=None, insurance_coverage_usd=None,
                insurance_expiry_date=None, data_last_updated=None,
            ),
        )

        if created:
            state = 'created'
        elif existed_before:
            state = 'updated (already existed)'
        else:
            state = 'updated'
        country_note = country.name if country else 'no country link'
        self.stdout.write(self.style.SUCCESS(
            f'Clean Heating Pilot {state}: "{project.name}" (slug={project.slug}, '
            f'commodity={project.commodity}, country={country_note}, is_demo={project.is_demo}).'
        ))
