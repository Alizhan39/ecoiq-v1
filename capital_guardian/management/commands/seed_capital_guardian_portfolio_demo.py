"""
seed_capital_guardian_portfolio_demo — Phase 2: creates two ADDITIONAL
clearly-flagged synthetic demonstration projects ("KZ Copper Project 02",
"UK Infrastructure Project 01") alongside "KZ Gold Project 01" (seeded by
seed_capital_guardian_demo) so the Investor Portfolio page has more than one
real project to aggregate, filter, sort and compare.

Every figure here is an explicitly labelled synthetic/illustrative estimate
(is_demo=True everywhere) — this is NOT a claim about any real, named
project's actual capital, ownership, or operational status. Completion %
and Capital Protection Score are genuinely computed from the seeded data
below, not reverse-engineered to hit an exact illustrative target — they
land close to, but not always exactly on, any example figures quoted
elsewhere, by design (never fabricate a number to match a target).

Idempotent: update_or_create everywhere, safe to re-run.
"""
import datetime

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seeds "KZ Copper Project 02" and "UK Infrastructure Project 01" for the Capital Guardian Investor Portfolio.'

    def handle(self, *args, **options):
        from countries.models import CountryProfile
        from gold_intelligence.models import CapitalBudgetLine, EquipmentSpec, GoldProject, MineTimelineMilestone

        from capital_guardian.models import CapitalTraceEntry, OperationalSnapshot, ProjectGovernance
        from capital_guardian.services.red_flag_engine import detect_red_flags
        from evidence_memory.models import EvidenceMemory

        today = datetime.date.today()

        # ============================= KZ Copper Project 02 =============================
        kz = CountryProfile.objects.filter(iso_code='KZ').first()
        if kz is None:
            self.stdout.write(self.style.WARNING('No Kazakhstan CountryProfile found — run seed_countries first.'))
        else:
            copper, _ = GoldProject.objects.update_or_create(
                slug='kz-copper-project-02',
                defaults=dict(
                    name='KZ Copper Project 02', commodity='copper', country=kz, region='East Kazakhstan',
                    status='construction',
                    description=(
                        'SYNTHETIC DEMONSTRATION PROJECT used to exercise the Capital Guardian Investor Portfolio '
                        'with a second, non-gold commodity. Not a claim about any real, named project.'
                    ),
                    total_committed_capital_usd=180_000_000, total_capex_usd=150_000_000,
                    insurance_coverage_usd=70_000_000, insurance_expiry_date=today + datetime.timedelta(days=200),
                    data_sources='Synthetic demonstration figures only — not real project data.',
                    data_last_updated=today, is_demo=True,
                ),
            )
            ProjectGovernance.objects.update_or_create(
                project=copper,
                defaults=dict(
                    founder_holdco_pct=55.0, investor_spv_pct=45.0,
                    founder_board_seats=2, investor_board_seats=2, independent_chair_seats=1,
                    reserved_matters_active=True, escrow_account_active=True, investor_first_waterfall_active=True,
                    quarterly_audit_active=True, independent_technical_adviser_active=True,
                    insurance_monitoring_active=True, milestone_based_capital_release_active=False,
                    is_demo=True,
                ),
            )
            CapitalBudgetLine.objects.update_or_create(
                project=copper, label='Concentrator & Mine Development',
                defaults=dict(category='processing_plant', planned_usd=150_000_000, committed_usd=156_000_000, spent_usd=88_000_000),
            )
            copper_milestones_spec = [
                ('exploration', 'complete', datetime.date(2021, 6, 1), datetime.date(2022, 9, 1), None, False, 'not_required'),
                ('licensing', 'complete', datetime.date(2022, 9, 1), datetime.date(2023, 9, 1), None, False, 'not_required'),
                ('construction', 'in_progress', today - datetime.timedelta(days=300), today + datetime.timedelta(days=120), 88.0, True, 'verified'),
                ('processing_plant', 'not_started', today + datetime.timedelta(days=120), today + datetime.timedelta(days=300), None, False, 'not_required'),
                ('production', 'not_started', today + datetime.timedelta(days=300), today + datetime.timedelta(days=650), None, False, 'not_required'),
                ('expansion', 'not_started', today + datetime.timedelta(days=1200), today + datetime.timedelta(days=1600), None, False, 'not_required'),
            ]
            copper_milestones = {}
            for phase, status, planned_start, planned_end, completion_override, verification_required, verification_status in copper_milestones_spec:
                m, _ = MineTimelineMilestone.objects.update_or_create(
                    project=copper, phase=phase,
                    defaults=dict(
                        status=status, planned_start=planned_start, planned_end=planned_end,
                        completion_pct_override=completion_override,
                        capital_required_usd=14_000_000 if phase == 'processing_plant' else None,
                        verification_required=verification_required, verification_status=verification_status,
                        delay_risk='low' if status != 'not_started' else '',
                        responsible_party='EPC Contractor' if phase in ('construction', 'processing_plant') else 'Project Team',
                    ),
                )
                copper_milestones[phase] = m
            copper_equipment_spec = [
                ('crusher', 'Primary Crusher', 'Metso', 'Metso Outotec Kazakhstan (illustrative)', 11_000_000, 'complete', 'passed', 'complete', 'complete'),
                ('flotation', 'Flotation Circuit', 'FLSmidth', 'FLSmidth Central Asia (illustrative)', 16_000_000, 'in_progress', 'not_started', 'not_started', 'not_started'),
                ('thickener', 'Tailings Thickener', 'Weir', 'Weir Minerals (illustrative)', 6_000_000, 'not_started', 'not_applicable', 'not_started', 'not_started'),
                ('haul_truck', 'CAT Haul Trucks (fleet of 8)', 'Caterpillar', 'Caterpillar Kazakhstan (illustrative)', 10_400_000, 'complete', 'passed', 'complete', 'complete'),
                ('excavator', 'Hydraulic Excavators (fleet of 4)', 'Komatsu', 'Komatsu Central Asia (illustrative)', 6_000_000, 'complete', 'passed', 'complete', 'complete'),
            ]
            copper_equipment = {}
            for equipment_type, label, manufacturer, supplier, capex, manufacturing_status, fat_status, delivery_status, installation_status in copper_equipment_spec:
                e, _ = EquipmentSpec.objects.update_or_create(
                    project=copper, label=label,
                    defaults=dict(
                        equipment_type=equipment_type, manufacturer=manufacturer, supplier=supplier, capex_usd=capex,
                        manufacturing_status=manufacturing_status, fat_status=fat_status,
                        delivery_status=delivery_status, installation_status=installation_status,
                        insurance_status='in_progress',
                    ),
                )
                copper_equipment[label] = e
            copper_entries_spec = [
                ('Concentrator Deposit', 18_000_000, copper_equipment['Primary Crusher'], copper_milestones['construction'], 'verified', 'not_required', True),
                ('Flotation Circuit Payment', 22_000_000, copper_equipment['Flotation Circuit'], copper_milestones['construction'], 'verified', 'not_required', True),
                ('Open Pit Development', 25_000_000, None, copper_milestones['construction'], 'verified', 'not_required', True),
                ('Tailings Facility Construction', 14_000_000, copper_equipment['Tailings Thickener'], copper_milestones['construction'], 'unverified', 'not_required', False),
                ('Insurance Premium', 2_000_000, None, None, 'verified', 'not_required', True),
                ('Independent Technical Adviser', 1_500_000, None, None, 'verified', 'pending', True),
                ('Site Infrastructure Works', 8_500_000, None, None, 'unverified', 'not_required', False),
            ]
            copper_trace_entries = {}
            for purpose, amount, related_equipment, related_milestone, verification_status, investor_approval_status, add_evidence in copper_entries_spec:
                entry, _ = CapitalTraceEntry.objects.update_or_create(
                    project=copper, purpose=purpose,
                    defaults=dict(
                        date=today - datetime.timedelta(days=45), amount_usd=amount, currency='USD',
                        supplier='Illustrative Contractor', approval_status='approved',
                        investor_approval_status=investor_approval_status, verification_status=verification_status,
                        insurance_status='insured', payment_status='paid',
                        related_equipment=related_equipment, related_milestone=related_milestone, is_demo=True,
                    ),
                )
                copper_trace_entries[purpose] = entry
                if add_evidence:
                    EvidenceMemory.objects.update_or_create(
                        source_reference=f'capital_guardian.CapitalTraceEntry:{entry.pk}',
                        defaults=dict(
                            text_chunk=f'Synthetic demonstration evidence document supporting the "{purpose}" capital movement ({entry.trace_id}).',
                            source_type='manual', confidence=78.0, is_demo=True,
                            verification_status='verified', review_tier='human_reviewed', document_category='payment_confirmation',
                        ),
                    )
            OperationalSnapshot.objects.update_or_create(
                project=copper, date=today,
                defaults=dict(
                    ore_mined_tonnes=9_800, plant_throughput_tph=420, recovery_rate_pct=86.4,
                    equipment_availability_pct=89.0, energy_use_mwh=31.2, water_recycled_pct=68.0,
                    environmental_status='amber', is_demo=True,
                ),
            )
            copper_flags = detect_red_flags(copper)
            self.stdout.write(self.style.SUCCESS(
                f'"{copper.name}" ready ({copper.capital_trace_entries.count()} capital movements, {len(copper_flags)} red flags detected).',
            ))

        # ============================= UK Infrastructure Project 01 =============================
        gb = CountryProfile.objects.filter(iso_code='GB').first()
        if gb is None:
            self.stdout.write(self.style.WARNING('No United Kingdom CountryProfile found — run seed_countries first.'))
        else:
            infra, _ = GoldProject.objects.update_or_create(
                slug='uk-infrastructure-project-01',
                defaults=dict(
                    name='UK Infrastructure Project 01', commodity='infrastructure', country=gb, region='North West England',
                    status='construction',
                    description=(
                        'SYNTHETIC DEMONSTRATION PROJECT used to exercise the Capital Guardian Investor Portfolio '
                        'with a non-mining sector. Not a claim about any real, named project.'
                    ),
                    total_committed_capital_usd=240_000_000, total_capex_usd=200_000_000,
                    insurance_coverage_usd=180_000_000, insurance_expiry_date=today + datetime.timedelta(days=300),
                    data_sources='Synthetic demonstration figures only — not real project data.',
                    data_last_updated=today, is_demo=True,
                ),
            )
            ProjectGovernance.objects.update_or_create(
                project=infra,
                defaults=dict(
                    founder_holdco_pct=40.0, investor_spv_pct=60.0,
                    founder_board_seats=2, investor_board_seats=3, independent_chair_seats=1,
                    reserved_matters_active=True, escrow_account_active=True, investor_first_waterfall_active=True,
                    quarterly_audit_active=True, independent_technical_adviser_active=True,
                    insurance_monitoring_active=True, milestone_based_capital_release_active=True,
                    is_demo=True,
                ),
            )
            CapitalBudgetLine.objects.update_or_create(
                project=infra, label='Civil, Structural & M&E Works',
                defaults=dict(category='infrastructure', planned_usd=200_000_000, committed_usd=201_000_000, spent_usd=150_000_000),
            )
            infra_milestones_spec = [
                ('exploration', 'complete', datetime.date(2021, 1, 1), datetime.date(2021, 9, 1), None, False, 'not_required'),
                ('licensing', 'complete', datetime.date(2021, 9, 1), datetime.date(2022, 6, 1), None, False, 'not_required'),
                ('construction', 'complete', datetime.date(2022, 6, 1), today - datetime.timedelta(days=60), None, True, 'verified'),
                ('processing_plant', 'complete', today - datetime.timedelta(days=60), today - datetime.timedelta(days=10), None, True, 'verified'),
                ('production', 'in_progress', today - datetime.timedelta(days=10), today + datetime.timedelta(days=200), 12.0, True, 'pending'),
                ('expansion', 'not_started', today + datetime.timedelta(days=900), today + datetime.timedelta(days=1300), None, False, 'not_required'),
            ]
            infra_milestones = {}
            for phase, status, planned_start, planned_end, completion_override, verification_required, verification_status in infra_milestones_spec:
                m, _ = MineTimelineMilestone.objects.update_or_create(
                    project=infra, phase=phase,
                    defaults=dict(
                        status=status, planned_start=planned_start, planned_end=planned_end,
                        completion_pct_override=completion_override,
                        capital_required_usd=6_000_000 if phase == 'production' else None,
                        verification_required=verification_required, verification_status=verification_status,
                        delay_risk='low', responsible_party='EPC Contractor',
                    ),
                )
                infra_milestones[phase] = m
            infra_equipment_spec = [
                ('power_plant', 'Energy Centre', 'Siemens', 'Siemens Energy (illustrative)', 40_000_000, 'complete', 'passed', 'complete', 'complete'),
                ('conveyor', 'Materials Handling System', 'ABB', 'ABB UK (illustrative)', 12_000_000, 'complete', 'passed', 'complete', 'complete'),
                ('crusher', 'Aggregate Processing Unit', 'Metso', 'Metso Outotec UK (illustrative)', 8_000_000, 'complete', 'passed', 'complete', 'complete'),
            ]
            infra_equipment = {}
            for equipment_type, label, manufacturer, supplier, capex, manufacturing_status, fat_status, delivery_status, installation_status in infra_equipment_spec:
                e, _ = EquipmentSpec.objects.update_or_create(
                    project=infra, label=label,
                    defaults=dict(
                        equipment_type=equipment_type, manufacturer=manufacturer, supplier=supplier, capex_usd=capex,
                        manufacturing_status=manufacturing_status, fat_status=fat_status,
                        delivery_status=delivery_status, installation_status=installation_status,
                        commissioning_status='complete', warranty_status='in_progress',
                        performance_guarantee_status='in_progress', insurance_status='insured',
                        maintenance_status='in_progress', inspection_status='passed',
                    ),
                )
                infra_equipment[label] = e
            infra_entries_spec = [
                ('Civil Works Advance Payment', 45_000_000, None, infra_milestones['construction']),
                ('Steel Structure Fabrication', 38_000_000, None, infra_milestones['construction']),
                ('Mechanical & Electrical Systems', 32_000_000, infra_equipment['Energy Centre'], infra_milestones['processing_plant']),
                ('Independent Engineer Payment', 3_000_000, None, None),
                ('Insurance Premium', 2_000_000, None, None),
                ('Site Enabling Works', 21_000_000, None, infra_milestones['construction']),
                ('Project Management Services', 15_000_000, None, None),
            ]
            for purpose, amount, related_equipment, related_milestone in infra_entries_spec:
                entry, _ = CapitalTraceEntry.objects.update_or_create(
                    project=infra, purpose=purpose,
                    defaults=dict(
                        date=today - datetime.timedelta(days=60), amount_usd=amount, currency='USD',
                        supplier='Illustrative Contractor', approval_status='approved',
                        investor_approval_status='not_required', verification_status='verified',
                        insurance_status='insured', payment_status='paid',
                        related_equipment=related_equipment, related_milestone=related_milestone, is_demo=True,
                    ),
                )
                EvidenceMemory.objects.update_or_create(
                    source_reference=f'capital_guardian.CapitalTraceEntry:{entry.pk}',
                    defaults=dict(
                        text_chunk=f'Synthetic demonstration evidence document supporting the "{purpose}" capital movement ({entry.trace_id}).',
                        source_type='manual', confidence=85.0, is_demo=True,
                        verification_status='verified', review_tier='independently_verified', document_category='inspection_report',
                    ),
                )
            # No OperationalSnapshot for this project — mining-specific Digital
            # Twin metrics (ore mined, gold grade, doré produced) genuinely
            # don't apply to an infrastructure asset, so it honestly shows an
            # empty Digital Twin state rather than fabricated readings.
            infra_flags = detect_red_flags(infra)
            self.stdout.write(self.style.SUCCESS(
                f'"{infra.name}" ready ({infra.capital_trace_entries.count()} capital movements, {len(infra_flags)} red flags detected).',
            ))
