"""
seed_capital_guardian_demo — creates ONE clearly-flagged synthetic
demonstration project ("KZ Gold Project 01") so Capital Guardian's real,
working engines (capital trace, capital protection score, red flag engine,
digital twin, milestone control) can be exercised end-to-end.

Every figure here is an explicitly labelled synthetic/illustrative estimate
(is_demo=True everywhere) — this is NOT a claim about any real, named
project's actual capital, ownership, or operational status. Manufacturer
names on equipment are illustrative examples only (Metso, FLSmidth,
Caterpillar, Komatsu, Siemens, ABB, Weir) — never a claim that company is
actually involved.

Idempotent: update_or_create everywhere, safe to re-run.
"""
import datetime

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seeds "KZ Gold Project 01", Capital Guardian\'s synthetic demonstration project.'

    def handle(self, *args, **options):
        from countries.models import CountryProfile
        from gold_intelligence.models import CapitalBudgetLine, EquipmentSpec, GoldProject, MineTimelineMilestone

        from capital_guardian.models import CapitalTraceEntry, OperationalSnapshot, ProjectGovernance
        from capital_guardian.services.red_flag_engine import detect_red_flags

        country = CountryProfile.objects.filter(iso_code='KZ').first()
        if country is None:
            self.stdout.write(self.style.WARNING('No Kazakhstan CountryProfile found — run seed_countries first.'))
            return

        today = datetime.date.today()

        project, _ = GoldProject.objects.update_or_create(
            slug='kz-gold-project-01',
            defaults=dict(
                name='KZ Gold Project 01',
                country=country, region='Central Kazakhstan', status='construction',
                description=(
                    'SYNTHETIC DEMONSTRATION PROJECT used to exercise EcoIQ Capital Guardian\'s real capital '
                    'traceability, governance, equipment, digital twin, milestone control and red flag engines '
                    'end-to-end. Not a claim about any real, named project\'s actual capital, ownership, or '
                    'operational status.'
                ),
                total_committed_capital_usd=100_000_000, total_capex_usd=86_000_000,
                insurance_coverage_usd=62_000_000, insurance_expiry_date=today + datetime.timedelta(days=47),
                data_sources='Synthetic demonstration figures only — not real project data.',
                data_last_updated=today, is_demo=True,
            ),
        )

        # --- SPV & Governance ---
        ProjectGovernance.objects.update_or_create(
            project=project,
            defaults=dict(
                founder_holdco_pct=50.0, investor_spv_pct=50.0,
                founder_board_seats=2, investor_board_seats=2, independent_chair_seats=1,
                reserved_matters_active=True, escrow_account_active=True, investor_first_waterfall_active=True,
                quarterly_audit_active=True, independent_technical_adviser_active=True,
                insurance_monitoring_active=True, milestone_based_capital_release_active=True,
                is_demo=True,
            ),
        )

        # --- CAPEX budget (headline CAPEX Budget/Actual figures) ---
        CapitalBudgetLine.objects.update_or_create(
            project=project, label='Processing Plant & Mining Equipment',
            defaults=dict(
                category='processing_plant', planned_usd=86_000_000, committed_usd=88_924_000, spent_usd=31_800_000,
            ),
        )

        # --- Milestones (Project Completion ≈ 31%, Next Milestone Payment $8.5M) ---
        milestones_spec = [
            ('exploration', 'complete', datetime.date(2022, 1, 1), datetime.date(2023, 6, 1), None, None, False, 'not_required'),
            ('licensing', 'complete', datetime.date(2023, 6, 1), datetime.date(2024, 6, 1), None, None, True, 'verified'),
            ('construction', 'in_progress', today - datetime.timedelta(days=180), today + datetime.timedelta(days=150), 16.0, 8_500_000, True, 'pending'),
            ('processing_plant', 'not_started', today + datetime.timedelta(days=150), today + datetime.timedelta(days=330), None, 15_000_000, False, 'not_required'),
            ('production', 'not_started', today + datetime.timedelta(days=330), today + datetime.timedelta(days=700), None, None, False, 'not_required'),
            ('expansion', 'not_started', today + datetime.timedelta(days=1500), today + datetime.timedelta(days=2000), None, None, False, 'not_required'),
        ]
        milestones = {}
        for phase, status, planned_start, planned_end, completion_override, capital_required, verification_required, verification_status in milestones_spec:
            m, _ = MineTimelineMilestone.objects.update_or_create(
                project=project, phase=phase,
                defaults=dict(
                    status=status, planned_start=planned_start, planned_end=planned_end,
                    completion_pct_override=completion_override, capital_required_usd=capital_required,
                    capital_released_usd=(capital_required * 0.6) if capital_required and status != 'not_started' else None,
                    verification_required=verification_required, verification_status=verification_status,
                    delay_risk='low' if status != 'not_started' else '',
                    responsible_party='EPC Contractor' if phase in ('construction', 'processing_plant') else 'Project Team',
                ),
            )
            milestones[phase] = m

        # --- Equipment (manufacturer names are illustrative examples only) ---
        equipment_spec = [
            ('crusher', 'Primary Crusher', 'Metso', 'Metso Outotec Kazakhstan (illustrative)', 12_000_000, 6_000_000, 10, 'complete', 'passed', 'complete', 'complete', 'in_progress', 'not_started'),
            ('mill', 'SAG Mill', 'FLSmidth', 'FLSmidth Central Asia (illustrative)', 5_600_000, 5_600_000, 14, 'in_progress', 'not_started', 'not_started', 'not_started', 'not_started', 'not_started'),
            ('mill', 'Ball Mill', 'Metso', 'Metso Outotec Kazakhstan (illustrative)', 8_200_000, 2_000_000, 14, 'in_progress', 'not_started', 'not_started', 'not_started', 'not_started', 'not_started'),
            ('conveyor', 'Overland Conveyor System', 'ABB', 'ABB Kazakhstan (illustrative)', 4_100_000, 1_000_000, 8, 'not_started', 'not_applicable', 'not_started', 'not_started', 'not_started', 'not_started'),
            ('cil', 'Leaching Tanks (CIL Circuit)', 'Weir', 'Weir Minerals (illustrative)', 9_800_000, 2_500_000, 12, 'not_started', 'not_applicable', 'not_started', 'not_started', 'not_started', 'not_started'),
            ('electrowinning', 'Electrowinning Cells', 'Siemens', 'Siemens Process Systems (illustrative)', 2_400_000, 500_000, 9, 'not_started', 'not_applicable', 'not_started', 'not_started', 'not_started', 'not_started'),
            ('smelting_furnace', 'Smelting Furnace', 'ABB', 'ABB Kazakhstan (illustrative)', 3_200_000, 800_000, 11, 'not_started', 'not_applicable', 'not_started', 'not_started', 'not_started', 'not_started'),
            ('haul_truck', 'CAT Haul Trucks (fleet of 6)', 'Caterpillar', 'Caterpillar Kazakhstan (illustrative)', 7_800_000, 7_800_000, 6, 'complete', 'passed', 'complete', 'complete', 'complete', 'complete'),
            ('excavator', 'Hydraulic Excavators (fleet of 3)', 'Komatsu', 'Komatsu Central Asia (illustrative)', 4_500_000, 4_500_000, 5, 'complete', 'passed', 'complete', 'complete', 'complete', 'complete'),
        ]
        equipment = {}
        for (equipment_type, label, manufacturer, supplier, capex, deposit, lead_time,
             manufacturing_status, fat_status, shipping_status, delivery_status, installation_status, commissioning_status) in equipment_spec:
            e, _ = EquipmentSpec.objects.update_or_create(
                project=project, label=label,
                defaults=dict(
                    equipment_type=equipment_type, manufacturer=manufacturer, supplier=supplier,
                    capex_usd=capex, deposit_paid_usd=deposit, lead_time_months=lead_time,
                    manufacturing_status=manufacturing_status, fat_status=fat_status,
                    shipping_status=shipping_status, delivery_status=delivery_status,
                    installation_status=installation_status, commissioning_status=commissioning_status,
                    warranty_status='in_progress' if manufacturing_status == 'complete' else 'not_applicable',
                    performance_guarantee_status='in_progress' if manufacturing_status == 'complete' else 'not_applicable',
                    insurance_status='in_progress' if deposit else 'not_started',
                    maintenance_status='in_progress' if commissioning_status == 'complete' else 'not_applicable',
                    inspection_status='passed' if commissioning_status == 'complete' else 'not_started',
                ),
            )
            equipment[label] = e

        # --- Capital Trace (6 named demo transactions + 2 supplementary,
        # summing to exactly the $42,300,000 deployed headline figure) ---
        entries_spec = [
            ('Crusher Deposit', 3_200_000, 'mining_equipment', 'Metso Outotec Kazakhstan (illustrative)', equipment['Primary Crusher'], None, 'paid', 'approved', 'not_required', 'verified'),
            ('SAG Mill Engineering Payment', 5_600_000, 'mining_equipment', 'FLSmidth Central Asia (illustrative)', equipment['SAG Mill'], milestones['construction'], 'paid', 'approved', 'not_required', 'verified'),
            ('Geological Drilling Campaign', 1_850_000, 'other', 'Independent Drilling Contractor (illustrative)', None, milestones['exploration'], 'paid', 'approved', 'not_required', 'verified'),
            ('EPC Advance Payment', 12_000_000, 'processing_plant', 'EPC Contractor (illustrative)', None, milestones['construction'], 'paid', 'approved', 'not_required', 'pending'),
            ('Insurance Premium', 740_000, 'other', 'Insurance Broker (illustrative)', None, None, 'paid', 'approved', 'not_required', 'verified'),
            ('Independent Technical Adviser', 420_000, 'other', 'Independent Technical Adviser (illustrative)', None, None, 'paid', 'approved', 'pending', 'verified'),
            ('Site Preparation Works', 12_500_000, 'infrastructure', 'Civil Works Contractor (illustrative)', None, milestones['construction'], 'paid', 'approved', 'not_required', 'unverified'),
            ('Camp & Accommodation Setup', 5_990_000, 'infrastructure', 'Camp Contractor (illustrative)', None, None, 'paid', 'approved', 'not_required', 'unverified'),
        ]
        trace_entries = {}
        for purpose, amount, category, supplier, related_equipment, related_milestone, payment_status, approval_status, investor_approval_status, verification_status in entries_spec:
            budget_line = CapitalBudgetLine.objects.filter(project=project, category=category).first() if category != 'other' else None
            entry, _ = CapitalTraceEntry.objects.update_or_create(
                project=project, purpose=purpose,
                defaults=dict(
                    date=today - datetime.timedelta(days=30), amount_usd=amount, currency='USD',
                    budget_category=budget_line, supplier=supplier,
                    approval_status=approval_status, investor_approval_status=investor_approval_status,
                    verification_status=verification_status, insurance_status='insured',
                    payment_status=payment_status, related_equipment=related_equipment,
                    related_milestone=related_milestone, is_demo=True,
                ),
            )
            trace_entries[purpose] = entry

        # --- Real evidence documents for the verified capital movements ---
        from evidence_memory.models import EvidenceMemory

        for purpose in ('Crusher Deposit', 'SAG Mill Engineering Payment', 'Geological Drilling Campaign', 'Insurance Premium', 'Independent Technical Adviser'):
            entry = trace_entries[purpose]
            EvidenceMemory.objects.update_or_create(
                source_reference=f'capital_guardian.CapitalTraceEntry:{entry.pk}',
                defaults=dict(
                    text_chunk=f'Synthetic demonstration evidence document supporting the "{purpose}" capital movement ({entry.trace_id}).',
                    source_type='manual', confidence=80.0, is_demo=True,
                ),
            )

        # --- Mining Digital Twin operational snapshot ---
        OperationalSnapshot.objects.update_or_create(
            project=project, date=today,
            defaults=dict(
                ore_mined_tonnes=18_400, plant_throughput_tph=780, gold_grade_g_per_tonne=1.8,
                recovery_rate_pct=91.7, dore_produced_kg=42, equipment_availability_pct=94.0,
                energy_use_mwh=22.4, water_recycled_pct=76.0, environmental_status='green', is_demo=True,
            ),
        )

        # --- Red Flag Engine: real detection over the data just seeded ---
        flags = detect_red_flags(project)

        self.stdout.write(self.style.SUCCESS(
            f'Capital Guardian demo ready: project "{project.name}" '
            f'({project.capital_trace_entries.count()} capital movements, {project.equipment_specs.count()} equipment items, '
            f'{project.timeline_milestones.count()} milestones, {len(flags)} red flags detected).',
        ))
