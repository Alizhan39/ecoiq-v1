"""
seed_capital_guardian_suppliers_demo — Phase 3: seeds SupplierProfile rows
for the project-independent Supplier Comparison page.

IMPORTANT: every rating below is a SYNTHETIC, ILLUSTRATIVE figure invented
for demonstration purposes only — it is NOT a real assessment of any named
company's actual risk, financial standing, ESG performance, price,
service, or availability. Company names are real, used as clearly-labelled
illustrative examples (matching the same convention already used for
EquipmentSpec.manufacturer in seed_capital_guardian_demo) — never a claim
that the company is actually involved in any real project. Every page that
displays these ratings carries a prominent disclaimer.

Idempotent: update_or_create everywhere, safe to re-run.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seeds synthetic, illustrative SupplierProfile rows for the Supplier Comparison page.'

    def handle(self, *args, **options):
        from capital_guardian.models import SupplierProfile

        # name, country, specialty, lead_time_weeks, warranty_years, perf_guarantee_years, insurance_backed,
        # price_index, service, availability, energy_efficiency, co2, risk, financial, esg, why_selected
        suppliers = [
            ('Metso', 'Finland', 'Crushers, Mills', 26, 2, 2, True, 62, 78, 82, 74, 70, 80, 82, 76,
             'Illustrative: strong regional service network and track record on comparable crusher/mill packages.'),
            ('FLSmidth', 'Denmark', 'Mills, Processing Plants', 30, 2, 3, True, 58, 80, 78, 80, 78, 78, 80, 82,
             'Illustrative: selected for SAG mill engineering depth and processing-plant integration experience.'),
            ('Weir', 'United Kingdom', 'Pumps, CIL/Leaching Equipment', 24, 2, 2, True, 60, 75, 80, 70, 68, 76, 78, 74,
             'Illustrative: strong slurry-handling and leaching-circuit specialization.'),
            ('Caterpillar', 'United States', 'Haul Trucks, Heavy Equipment', 18, 3, 2, True, 55, 85, 88, 72, 65, 84, 90, 78,
             'Illustrative: fleet standardization and parts availability across the region.'),
            ('Komatsu', 'Japan', 'Excavators, Haul Trucks', 20, 3, 2, True, 57, 82, 85, 76, 72, 82, 86, 80,
             'Illustrative: comparable excavator fleet reliability and dealer support.'),
            ('Liebherr', 'Switzerland', 'Excavators, Cranes', 22, 3, 2, True, 65, 80, 76, 78, 75, 82, 84, 78,
             'Illustrative example — not selected for this demo project, shown for comparison.'),
            ('ABB', 'Switzerland', 'Electrical, Automation, Conveyors', 20, 2, 2, True, 63, 76, 80, 82, 80, 78, 82, 84,
             'Illustrative: electrification and automation package for materials handling and smelting.'),
            ('Siemens', 'Germany', 'Electrical, Process Control', 22, 2, 2, True, 64, 77, 79, 83, 81, 79, 84, 85,
             'Illustrative: process control and electrowinning systems integration.'),
            ('Epiroc', 'Sweden', 'Drilling, Underground Equipment', 20, 2, 1, False, 59, 74, 77, 73, 71, 74, 76, 75,
             'Illustrative example — not selected for this demo project, shown for comparison.'),
            ('Sandvik', 'Sweden', 'Crushers, Drilling Equipment', 24, 2, 2, True, 61, 76, 79, 75, 73, 77, 80, 77,
             'Illustrative example — not selected for this demo project, shown for comparison.'),
        ]

        for (name, country, specialty, lead_time, warranty, perf_guarantee, insured,
             price, service, availability, energy, co2, risk, financial, esg, why) in suppliers:
            SupplierProfile.objects.update_or_create(
                name=name,
                defaults=dict(
                    country=country, equipment_specialty=specialty,
                    typical_lead_time_weeks=lead_time, typical_warranty_years=warranty,
                    performance_guarantee_years=perf_guarantee, insurance_backed=insured,
                    illustrative_price_index=price, illustrative_service_rating=service,
                    illustrative_availability_rating=availability, illustrative_energy_efficiency_rating=energy,
                    illustrative_co2_rating=co2, illustrative_risk_rating=risk,
                    illustrative_financial_rating=financial, illustrative_esg_rating=esg,
                    why_selected_notes=why, is_demo=True,
                ),
            )

        self.stdout.write(self.style.SUCCESS(f'Supplier Comparison demo ready: {len(suppliers)} synthetic supplier profiles.'))
