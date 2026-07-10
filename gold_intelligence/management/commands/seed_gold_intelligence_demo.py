"""
seed_gold_intelligence_demo — creates ONE clearly-flagged demonstration gold
project so the real, working Gold Intelligence engines (project economics,
risk intelligence, capital tracker, equipment intelligence, mine map) can be
exercised end-to-end.

Every financial/technical figure here is an explicitly labelled
illustrative estimate (is_demo=True everywhere, and GoldProject.data_sources
says so directly) — this is NOT a claim about any real, named mine's actual
economics. Follows the exact same idiom already used by geo_intelligence's
own seed_geo_intelligence_demo command (is_demo=True on every row, no
un-flagged demo data anywhere in this platform).

Idempotent: get_or_create + explicit field sync, safe to re-run.
"""
import datetime

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seeds one clearly-flagged demonstration Gold Intelligence project (Kazakhstan).'

    def handle(self, *args, **options):
        from countries.models import CountryProfile
        from geo_intelligence.models import GeoAsset, InvestmentGeoOpportunity
        from gold_intelligence.models import (
            CapitalBudgetLine, EquipmentSpec, GoldProject, MineTimelineMilestone, ScenarioAssumption,
        )

        country = CountryProfile.objects.filter(iso_code='KZ').first()
        if country is None:
            self.stdout.write(self.style.WARNING('No Kazakhstan CountryProfile found — run seed_countries first.'))
            return

        project, _ = GoldProject.objects.update_or_create(
            slug='kazakhstan-gold-project-demo',
            defaults=dict(
                name='Kazakhstan Gold Project (Demonstration)',
                country=country, region='East Kazakhstan', status='construction',
                description=(
                    'Illustrative demonstration project used to exercise EcoIQ Gold Intelligence\'s real '
                    'CAPEX/IRR/NPV/sensitivity engine end-to-end. Not a claim about any specific real, '
                    'named mine\'s actual economics — replace with a real NI 43-101/JORC technical report '
                    'before use in an actual investment decision.'
                ),
                ore_grade_g_per_tonne=2.1, resource_tonnes=50_000_000, recovery_rate_pct=88.0,
                mine_life_years=12, expected_annual_production_oz=150_000,
                total_capex_usd=350_000_000, annual_opex_usd=120_000_000,
                cash_cost_usd_per_oz=750.0, aisc_usd_per_oz=950.0,
                gold_price_assumption_usd_per_oz=2000.0, discount_rate_pct=8.0,
                data_sources='Illustrative demonstration figures only — not a real, licensed technical report.',
                data_last_updated=datetime.date.today(), is_demo=True,
            ),
        )

        # --- Map: real GeoAsset rows tagged for this project (source_reference) ---
        ref = f'gold_intelligence.GoldProject:{project.slug}'
        base_lat, base_lng = 49.95, 82.6   # East Kazakhstan (Ust-Kamenogorsk area), illustrative siting only
        asset_specs = [
            ('gold_deposit', 'Demonstration Gold Deposit', 0.0, 0.0),
            ('active_mine', 'Demonstration Open Pit', 0.05, 0.03),
            ('processing_plant', 'Demonstration Processing Plant', 0.08, -0.02),
            ('exploration_licence', 'Demonstration Exploration Licence Block', -0.15, 0.20),
            ('power_plant', 'Regional Power Substation', -0.10, -0.10),
            ('water_source', 'Irtysh River Water Intake', 0.02, -0.30),
            ('rail', 'Regional Rail Spur', 0.20, 0.05),
            ('road', 'Regional Access Road', 0.03, 0.10),
            ('airport', 'Ust-Kamenogorsk Airport', 0.35, -0.15),
        ]
        for asset_type, name, dlat, dlng in asset_specs:
            GeoAsset.objects.update_or_create(
                name=name, asset_type=asset_type, country=country,
                defaults=dict(
                    latitude=round(base_lat + dlat, 4), longitude=round(base_lng + dlng, 4),
                    region='East Kazakhstan', source_reference=ref,
                    workbench_case_slug='kazakhstan-gold-project-demo', is_demo=True,
                ),
            )

        InvestmentGeoOpportunity.objects.update_or_create(
            title='Kazakhstan Gold Project — Processing Plant Modernisation', country=country,
            defaults=dict(
                latitude=round(base_lat + 0.08, 4), longitude=round(base_lng - 0.02, 4),
                region='East Kazakhstan', opportunity_type='modernisation',
                estimated_impact='Illustrative demonstration opportunity linked to the demo gold project.',
                risk_level='medium', investment_score=None, confidence=None,
                source_reference=ref, workbench_case_slug='kazakhstan-gold-project-demo',
                workbench_agent_slug='capital-allocation-agent', is_demo=True,
            ),
        )

        # --- Capital Tracker ---
        capital_lines = [
            ('mining_equipment', 'Mining fleet & crusher', 45_000_000, 42_000_000, 18_000_000),
            ('processing_plant', 'CIL processing plant', 180_000_000, 170_000_000, 60_000_000),
            ('infrastructure', 'Power, water & access road', 60_000_000, 55_000_000, 25_000_000),
            ('permits_licensing', 'Permits & licensing', 8_000_000, 8_000_000, 8_000_000),
            ('contingency', 'Contingency reserve', 57_000_000, 20_000_000, 0),
        ]
        for category, label, planned, committed, spent in capital_lines:
            CapitalBudgetLine.objects.update_or_create(
                project=project, label=label,
                defaults=dict(category=category, planned_usd=planned, committed_usd=committed, spent_usd=spent),
            )

        # --- Mine Timeline ---
        milestones = [
            ('exploration', 'complete', datetime.date(2019, 1, 1), datetime.date(2021, 6, 1), datetime.date(2019, 1, 1), datetime.date(2021, 4, 15)),
            ('licensing', 'complete', datetime.date(2021, 6, 1), datetime.date(2023, 1, 1), datetime.date(2021, 6, 1), datetime.date(2022, 11, 1)),
            ('construction', 'in_progress', datetime.date(2023, 1, 1), datetime.date(2026, 12, 1), datetime.date(2023, 2, 1), None),
            ('processing_plant', 'in_progress', datetime.date(2024, 6, 1), datetime.date(2026, 12, 1), datetime.date(2024, 7, 1), None),
            ('production', 'not_started', datetime.date(2027, 1, 1), datetime.date(2039, 1, 1), None, None),
            ('expansion', 'not_started', datetime.date(2033, 1, 1), datetime.date(2035, 1, 1), None, None),
        ]
        for phase, status, planned_start, planned_end, actual_start, actual_end in milestones:
            MineTimelineMilestone.objects.update_or_create(
                project=project, phase=phase,
                defaults=dict(
                    status=status, planned_start=planned_start, planned_end=planned_end,
                    actual_start=actual_start, actual_end=actual_end,
                ),
            )

        # --- Equipment Intelligence ---
        equipment_specs = [
            ('crusher', 'Primary Jaw Crusher', 12_000_000, 10, 1_200, 0, None),
            ('mill', 'SAG Mill', 35_000_000, 14, 8_500, 120, None),
            ('cil', 'CIL Circuit (8 tanks)', 40_000_000, 16, 2_000, 300, 92.0),
            ('thickener', 'Tailings Thickener', 6_000_000, 8, 400, 50, None),
            ('filter_press', 'Filter Press', 5_000_000, 6, 350, 20, None),
            ('tailings', 'Tailings Storage Facility', 30_000_000, 18, 100, 10, None),
            ('power_plant', 'On-site Diesel/Grid Substation', 15_000_000, 12, 0, 0, None),
        ]
        for equipment_type, label, capex, lead_time, power, water, recovery in equipment_specs:
            EquipmentSpec.objects.update_or_create(
                project=project, equipment_type=equipment_type,
                defaults=dict(
                    label=label, capex_usd=capex, lead_time_months=lead_time,
                    power_usage_kw=power, water_usage_m3_per_hour=water, recovery_pct=recovery,
                ),
            )

        # --- Scenario Analysis ---
        scenarios = [
            ('Gold price -20%', 1600.0, None, None),
            ('Gold price +20%', 2400.0, None, None),
            ('CAPEX overrun +15%', None, 1.15, None),
            ('OPEX increase +10%', None, None, 1.10),
        ]
        for name, gold_price, capex_mult, opex_mult in scenarios:
            ScenarioAssumption.objects.update_or_create(
                project=project, name=name,
                defaults=dict(gold_price_usd_per_oz=gold_price, capex_multiplier=capex_mult, opex_multiplier=opex_mult),
            )

        self.stdout.write(self.style.SUCCESS(
            f'Gold Intelligence demo ready: project "{project.name}" '
            f'({project.geo_assets.count()} map assets, {project.capital_budget_lines.count()} budget lines, '
            f'{project.timeline_milestones.count()} milestones, {project.equipment_specs.count()} equipment specs, '
            f'{project.scenarios.count()} scenarios).',
        ))
