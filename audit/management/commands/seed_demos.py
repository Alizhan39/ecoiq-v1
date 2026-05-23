"""
Management command: seed demo audit sessions.

Creates two pre-configured demo facilities with realistic Q&A data
and runs the full AI analysis pipeline for each.

Usage:
    python manage.py seed_demos          # creates + analyses both demos
    python manage.py seed_demos --skip-ai  # creates sessions + Q&A only (no AI call)
    python manage.py seed_demos --name refinery   # only refinery demo
    python manage.py seed_demos --name warehouse  # only warehouse demo
"""

import time
from django.core.management.base import BaseCommand
from audit.models import AuditSession, AuditResponse
from audit.ai import run_full_analysis

# ── Demo 1: Oil Refinery ──────────────────────────────────────────────────────

REFINERY = {
    "facility_name": "Gulf Coast Petroleum Refinery",
    "sector": "oil_gas",
    "location": "Houston, TX, USA",
    "facility_age": 32,
    "headcount": 850,
    "annual_revenue": 480_000_000,
    "notes": (
        "Crude distillation capacity 120,000 bbl/day. "
        "Three CDUs, two FCC units, one coker. "
        "Built in 1992, last major turnaround 2018. "
        "Subject to EPA Tier 3 compliance deadlines 2026."
    ),
}

REFINERY_QA = [
    ("energy_consumption",
     "Total facility power draw averages 48 MW. Primary consumers: CDU furnaces (18 MW), "
     "rotating equipment / compressors (14 MW), steam generation (9 MW), lighting & HVAC (7 MW). "
     "Natural gas cost is the largest single operating expense at ~$3.2M/month."),

    ("energy_losses",
     "Stack temperature on CDU F-101 runs consistently at 380°C vs design of 310°C, "
     "indicating fouling in the convection section. Estimated heat loss ~12 GJ/hr. "
     "Steam trap survey from 2021 found 23% of traps failed-open."),

    ("downtime_frequency",
     "Unplanned shutdowns average 11 events per year, totalling ~420 hours of lost production. "
     "Top causes: pump seal failures (35%), heat exchanger tube leaks (28%), "
     "instrumentation faults (22%), compressor trips (15%)."),

    ("maintenance_strategy",
     "Predominantly reactive and time-based preventive. Vibration monitoring exists on "
     "18 of 47 rotating machines. No CMMS integration with procurement. "
     "Mean time to repair on pump failures averages 6.2 hours."),

    ("production_efficiency",
     "Current OEE estimated at 71%. Target is 88%. Primary losses: unplanned downtime (11%), "
     "throughput reduction during feed slate changes (9%), quality giveaway on naphtha spec (4%). "
     "FCC unit operating at 87% of nameplate capacity due to regenerator constraint."),

    ("safety_incidents",
     "Three recordable incidents in the last 12 months, two LTI-free. "
     "Near-miss reporting rate is low — approx 0.8 per month suggesting under-reporting culture. "
     "Process safety: two PSV activations in H2 unit, one confirmed overpressure event on K-101."),

    ("infrastructure_age",
     "Control system: Honeywell TDC 3000 vintage 1997, spare parts on extended lead times (16+ weeks). "
     "P&IDs last formally updated 2015. Cooling tower structural inspection overdue by 14 months. "
     "Electrical one-lines not reconciled with as-built since 2009 expansion."),

    ("environmental_compliance",
     "NOx emissions averaging 142 ppm on CDU furnaces, current permit limit 110 ppm — "
     "in violation requiring variance. CO2 footprint approx 890,000 tCO2e/yr. "
     "Flaring volumes: 2.1 MMscfd routine flaring, of which 60% is recoverable with compression. "
     "API 653 tank inspection programme 3 tanks overdue."),

    ("digital_systems",
     "No plant-wide data historian. OSIsoft PI deployed only on the FCC unit. "
     "Laboratory LIMS is standalone with no DCS integration. "
     "Shift handover is paper-based. No mobile maintenance work orders."),

    ("workforce_skills",
     "18% of process operators and 24% of instrument technicians eligible to retire within 3 years. "
     "No formal knowledge capture programme. Training uses 1997-era CBT modules. "
     "Contractor ratio for turnaround work: 70%, with recurring quality rework issues."),

    ("improvement_priorities",
     "Board priorities for next capital cycle: 1) Reliability improvement to reduce insurance premium "
     "(currently $8.4M/yr). 2) NOx compliance to avoid consent order. "
     "3) Digital transformation roadmap. 4) Reduce carbon intensity 30% by 2030."),

    ("budget_constraints",
     "Annual maintenance OPEX budget: $22M. Capital improvement budget for 2024-2026: $45M total. "
     "Turnaround scheduled Q3 2025 — ideal window for major upgrades. "
     "ROI threshold: 18-month payback for OPEX projects, 36 months for CAPEX."),
]

# ── Demo 2: Logistics Warehouse ───────────────────────────────────────────────

WAREHOUSE = {
    "facility_name": "Midlands Regional Distribution Centre",
    "sector": "logistics",
    "location": "Birmingham, UK",
    "facility_age": 18,
    "headcount": 420,
    "annual_revenue": 62_000_000,
    "notes": (
        "1.2M sq ft ambient and chilled multi-client 3PL warehouse. "
        "Handles FMCG, pharma, and automotive parts. "
        "Three shifts, 363 days/year. "
        "Lease renewal negotiation due 2027."
    ),
}

WAREHOUSE_QA = [
    ("energy_consumption",
     "Total monthly electricity bill averaging £185,000 (~£2.2M/yr). "
     "Breakdown: refrigeration plant 38%, lighting 26%, dock equipment (chargers, conveyors) 21%, "
     "HVAC 12%, IT/office 3%. No sub-metering below zone level. "
     "Currently on a fixed-rate tariff until Dec 2024."),

    ("energy_losses",
     "Refrigeration COP measured at 1.8 against modern benchmark of 2.8+. "
     "Compressors running continuously with no inverter control. "
     "Average dock door open time is 42 minutes per trailer, causing significant cold chain loss. "
     "Lighting: T8 fluorescent throughout ambient area — no occupancy sensing."),

    ("downtime_frequency",
     "Conveyor system averages 4.3 unplanned stoppages per shift of >10 min duration. "
     "Sorter jams account for 60% of conveyor downtime. "
     "WMS outages: 8 incidents >30 min in past 12 months. "
     "Dock leveller failures: 7 per month requiring maintenance call-out."),

    ("maintenance_strategy",
     "MHE serviced on 6-month fixed intervals regardless of usage. "
     "No predictive monitoring on conveyor drives. "
     "Battery management for 94 counterbalance forklifts: opportunity charging, "
     "average battery life 3.2 years vs industry 5-year norm."),

    ("production_efficiency",
     "Pick accuracy: 99.1% vs customer SLA of 99.8%. "
     "Lines picked per hour (LPH) average 112 against competitor benchmark of 145. "
     "Despatch cut-off missed on 8.3% of shifts due to late replenishment. "
     "Returns processing backlog: average 3.4 days to putaway vs SLA of 1 day."),

    ("safety_incidents",
     "RIDDOR reportable incidents: 4 in past 12 months (2 manual handling, 1 MHE collision, 1 fall). "
     "Near-miss reporting: 2.1 per week — low for a site this size. "
     "Three pedestrian/MHE proximity incidents recorded in CCTV review. "
     "Fire damper test compliance: 73% (27% overdue)."),

    ("infrastructure_age",
     "Racking installed 2006, no formal SEMA inspection since 2020. "
     "Sprinkler system: FM Global classified, last flow test 2019. "
     "Roof: 14 identified leak points, 3 causing operational impact in wet weather. "
     "Loading bay concrete apron: significant cracking, 2 levellers sunk."),

    ("environmental_compliance",
     "No current solar on roof despite 68,000 sq ft suitable south-facing surface. "
     "All 94 forklifts LPG — fleet transition to electric in 2026 business plan but no project plan. "
     "Waste: 31% to landfill, rest to trade waste, no composting or reuse scheme. "
     "ISO 14001 certification lapsed 2022."),

    ("digital_systems",
     "WMS: Manhattan SCALE v2014 — 3 major versions behind current. "
     "No real-time inventory accuracy tracking (cycle count revealed 94.2% location accuracy). "
     "Labour management: Excel-based. No voice or RF-directed picking. "
     "CCTV: 480p analogue cameras, poor coverage in pallet storage. "
     "No integration between WMS, TMS, and ERP."),

    ("workforce_skills",
     "Annual labour turnover: 42% — vs industry average of 28%. "
     "Average time-to-productivity for new pickers: 3.8 weeks with current paper-based training. "
     "Agency staff ratio: 55% on nights. Overtime costs: £680,000/yr. "
     "No structured lean or CI training. Supervisor grade has 9 vacancies."),

    ("improvement_priorities",
     "Operational priorities: 1) Reduce energy costs to protect margin on repriced contracts. "
     "2) Hit 99.8% pick accuracy to retain largest FMCG client (£14M revenue, contract renewal Q2). "
     "3) Reduce turnover costs — currently estimated at £1.1M/yr. "
     "4) Modernise WMS before 2027 lease decision."),

    ("budget_constraints",
     "OPEX budget for facilities: £1.8M/yr. Capex availability: £3.5M over 24 months. "
     "Any energy project must show <24-month payback. "
     "Owner prefers phased investments with clear milestone gates. "
     "Green bond financing available for qualifying projects (UKGIB scheme)."),
]

DEMO_MAP = {
    "refinery":  (REFINERY,  REFINERY_QA),
    "warehouse": (WAREHOUSE, WAREHOUSE_QA),
}

# Map friendly question keys to QUESTIONS question_text for DB storage
# (We store free-form key names; question_text can be the key itself for demo purposes)
QUESTION_TEXT_MAP = {
    "energy_consumption":      "Describe your current energy consumption profile.",
    "energy_losses":           "Where are the main sources of energy loss or waste?",
    "downtime_frequency":      "How often does unplanned downtime occur, and what are the main causes?",
    "maintenance_strategy":    "Describe your current maintenance strategy and systems.",
    "production_efficiency":   "What is your current production/operational efficiency level?",
    "safety_incidents":        "Describe recent safety incidents and near-miss trends.",
    "infrastructure_age":      "What is the age and condition of key infrastructure?",
    "environmental_compliance":"Describe your environmental compliance status and challenges.",
    "digital_systems":         "What digital systems and data infrastructure are in place?",
    "workforce_skills":        "Describe workforce skills, gaps, and retention challenges.",
    "improvement_priorities":  "What are the top improvement priorities from leadership?",
    "budget_constraints":      "What budget and financial constraints apply to improvements?",
}


class Command(BaseCommand):
    help = "Seed demo audit sessions (Oil Refinery + Logistics Warehouse) with AI analysis."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-ai",
            action="store_true",
            help="Create sessions and Q&A only — skip the AI analysis call.",
        )
        parser.add_argument(
            "--name",
            choices=["refinery", "warehouse"],
            help="Only seed a specific demo (refinery or warehouse).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-create demo even if a session with the same name already exists.",
        )

    def handle(self, *args, **options):
        skip_ai   = options["skip_ai"]
        name_filter = options.get("name")
        force     = options["force"]

        demos = (
            [(name_filter, *DEMO_MAP[name_filter])]
            if name_filter
            else [("refinery", *DEMO_MAP["refinery"]), ("warehouse", *DEMO_MAP["warehouse"])]
        )

        for demo_name, profile_data, qa_data in demos:
            self._seed_one(demo_name, profile_data, qa_data, skip_ai, force)

    def _seed_one(self, demo_name, profile_data, qa_data, skip_ai, force):
        fname = profile_data["facility_name"]
        self.stdout.write(f"\n── {fname} ──")

        existing = AuditSession.objects.filter(facility_name=fname).first()
        if existing and not force:
            self.stdout.write(
                self.style.WARNING(
                    f"  Already exists (pk={existing.pk}, status={existing.status}). "
                    "Use --force to recreate."
                )
            )
            return

        if existing and force:
            existing.delete()
            self.stdout.write("  Deleted existing session.")

        # Create session
        session = AuditSession.objects.create(
            facility_name  = profile_data["facility_name"],
            sector         = profile_data["sector"],
            location       = profile_data.get("location", ""),
            facility_age   = profile_data.get("facility_age"),
            headcount      = profile_data.get("headcount"),
            annual_revenue = profile_data.get("annual_revenue"),
            notes          = profile_data.get("notes", ""),
            extracted_text = "",
            status         = "processing",
        )
        self.stdout.write(f"  Created session pk={session.pk}")

        # Save Q&A
        for key, answer in qa_data:
            AuditResponse.objects.update_or_create(
                session=session,
                question_key=key,
                defaults={
                    "question_text": QUESTION_TEXT_MAP.get(key, key),
                    "answer": answer,
                },
            )
        self.stdout.write(f"  Saved {len(qa_data)} Q&A responses")

        if skip_ai:
            self.stdout.write(self.style.WARNING("  Skipping AI analysis (--skip-ai)."))
            return

        # Run AI analysis
        self.stdout.write("  Running AI analysis — this takes 3-5 minutes…")
        t0 = time.time()
        try:
            report = run_full_analysis(session)
            session.status = "complete"
            session.save(update_fields=["status", "updated_at"])
            elapsed = int(time.time() - t0)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Done in {elapsed}s — "
                    f"Scores: {report.overall_efficiency_score} → {report.modernization_score}  "
                    f"Savings: ${report.total_savings_potential:,}/yr"
                )
            )
        except Exception as exc:
            session.status = "error"
            session.save(update_fields=["status", "updated_at"])
            self.stdout.write(self.style.ERROR(f"  FAILED: {exc}"))
            raise
