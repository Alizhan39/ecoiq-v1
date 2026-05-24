"""
Management command: seed three investor-demo EcoIQ audit sessions.

Creates complete, realistic industrial scenarios with questionnaire
responses and pre-built findings — no AI API call required.

Usage:
    python manage.py seed_demos           # seed all three scenarios
    python manage.py seed_demos --reset   # delete existing demos first
    python manage.py seed_demos --only refinery
    python manage.py seed_demos --only logistics
    python manage.py seed_demos --only mining
"""

from django.core.management.base import BaseCommand
from core.models import Assessment, QuestionnaireResponse, Finding


# ═══════════════════════════════════════════════════════════════════════════════
#  SCENARIO 1 — OIL REFINERY
# ═══════════════════════════════════════════════════════════════════════════════

REFINERY = {
    "company_name": "Midland Petroleum Refining Co.",
    "notes": (
        "32-year-old continuous-process refinery · 850 employees · "
        "95,000 bbl/day throughput · Three CDUs, two VDUs, one coker · "
        "ETS-obligated · Last full turnaround: 2021 · "
        "Audit scope: energy efficiency, NOx compliance, compressor reliability, "
        "digital transformation readiness."
    ),
    "extracted_text": """\
FACILITY TECHNICAL BRIEFING — MIDLAND PETROLEUM REFINING CO.
Prepared for EcoIQ Audit · Confidential
═══════════════════════════════════════════════════════════════

FACILITY OVERVIEW
Refinery commissioned 1992 · Crude slate: North Sea Brent (60%), West African medium sour (40%)
Design throughput: 95,000 bbl/day CDU feed · Current operating rate: 91,200 bbl/day
Primary process units: CDU-1, CDU-2, CDU-3; VDU-1, VDU-2; Delayed Coker; FCC; HDS; Alkylation
Steam system: 6-bar and 16-bar headers · Steam generation: 4× D-type boilers, 1 WHR unit

ENERGY PROFILE
Total site energy intensity: 87 kg CO₂e / tonne throughput
Sector median (comparable asset age): 71 kg CO₂e / tonne — gap: +23%
Primary energy consumers: CDU furnaces (F-101, F-102, F-103) · Rotating equipment (47 machines)
CDU F-101 stack temperature: current 378°C · design 310°C · Δ = 68°C above design
Steam trap population: 1,847 traps · Last survey (2021): 23% failed-open (estimated £340K/yr loss)
Compressor fleet: 12 reciprocating, 8 centrifugal · Average age: 24 years

EMISSIONS & COMPLIANCE
Scope 1 CO₂e (2023 actuals): 892,000 tCO₂e
UK ETS surrender obligation: 847,000 tCO₂e · ETS units purchased: 45,000 at avg £48.20/unit = £2.17M
NOx — CDU furnaces (Stack 4 & 5): measured 138–146 ppm · permit limit 110 mg/m³ (equiv.) · EXCEEDANCE
Regulatory notifications issued: 16 of last 24 months · Enforcement notice under review by EA
Flare volumes (routine): 1.94 MMscfd · Estimated recoverable fraction: 58% via VRU compression
Flare CO₂e contribution: ~4,100 tCO₂e/yr

RELIABILITY & MAINTENANCE
Unplanned downtime events (12-month): 13 events · Total lost hours: 447
MTBF rotating equipment: 7.8 months · Industry upper-quartile: 14.2 months
Top failure modes: mechanical seal failures (38%), heat exchanger fouling (26%), instrument faults (21%)
Vibration monitoring coverage: 19 of 47 rotating machines (40%)
CMMS: legacy SAP PM module, not integrated with procurement or planning

DIGITAL SYSTEMS
Process historian: OSIsoft PI — CDU-1 only (12% of tag count)
DCS: Honeywell TDC 3000 (commissioned 1997) · spare parts lead time: 14–18 weeks
P&ID revision status: last formal update 2015 · 23 active red-line markups not incorporated
Mobile maintenance: paper-based work orders
LIMS: standalone, no DCS integration

WORKFORCE
Total headcount: 850 (680 direct, 170 contract)
Process operators eligible to retire within 36 months: 18%
Instrument technicians eligible to retire within 36 months: 24%
Near-miss reporting rate: 0.9/month (low for site scale — indicates under-reporting culture)

CAPITAL PROGRAMME 2024-2026
Total approved capex: £47M
DCS migration (TDC3000 → Experion PKS): £3.8M (approved)
Process historian expansion (site-wide): £1.1M (approved)
SCR feasibility study: £180K (in progress)
Flare gas VRU: pre-FEED commissioned Q1 2024
ML fouling detection pilot (E-304 exchanger): live — 18-month trial
""",
    "scores": {
        "environment": 34,
        "social":      52,
        "governance":  61,
        "ethics":      57,
        "innovation":  41,
        "overall":     49,
    },
    "summary": """\
Midland Petroleum Refining Co. presents a risk profile characteristic of a mature, capital-constrained heavy-process facility navigating the transition from legacy operations to sustainability-aligned performance. The overall EcoIQ score of 49/100 reflects genuine commitment at policy level — evidenced by ETS compliance, ISO 14001 certification, and a declared 2030 emissions target — offset by a persistent gap between declared ambition and operational execution.

The most material finding is the ongoing NOx permit exceedance at Stack 4 and Stack 5 (CDU furnace flue gas), which has triggered formal regulatory notifications in 16 of the past 24 months. Without investment in selective catalytic reduction (SCR) or low-NOx burner upgrades, this exposure will intensify as Industrial Emissions Directive limits tighten. At current ETS carbon pricing (£48.20/unit), the annual cost of unrecovered flare gas is approximately £197K in carbon liability alone — with a further £120K–£180K in fuel value — yielding a combined economic case for flare gas recovery of £317K–£377K per annum. Indicative VRU capital costs suggest a payback period of 2.8–3.5 years.

Compressor reliability and heat exchanger fouling are the dominant operational loss drivers. CDU furnace F-101 is running 68°C above design stack temperature, representing a recoverable heat loss of approximately 12 GJ/hr. The ML fouling-prediction pilot on exchanger E-304 has demonstrated that data-driven maintenance is technically viable at this site; scaling that capability across the full CDU/VDU heat exchanger network (estimated 31 units) and integrating predictive alerts into the DCS migration currently underway is the highest-leverage digital investment available. Turnaround planning for Q3 2025 should incorporate a structured energy-optimisation scope targeting an aggregate heat recovery improvement of 5–8 MW across the primary process trains.

On governance and ethics, the facility performs credibly for its sector and vintage. Board-level ESG committee oversight, third-party emissions verification (Bureau Veritas), and an active whistleblowing mechanism are all in place. The primary governance gap is the absence of ESG KPIs in long-term executive incentive structures — a credibility gap that investor and regulatory scrutiny will increasingly expose. The sub-Tier-1 supply chain human-rights due diligence gap is addressable at low cost through a targeted Tier 2 assessment of the top 20 chemical suppliers by spend.

Priority actions for the next 12 months: (1) commission SCR feasibility study to completion and secure board approval for NOx compliance capital before enforcement notice escalation; (2) extend ML fouling-prediction model to all CDU/VDU heat exchanger trains — target 6 MW recoverable heat; (3) progress flare gas VRU to pre-FEED completion and investment case sign-off; (4) integrate ESG KPIs into long-term incentive plan design ahead of 2025 remuneration review; (5) conduct Tier 2 supplier human-rights assessment for top 20 chemical suppliers. Illustrative annual savings from full programme execution: £1.4M–£2.1M OPEX reduction plus £380K carbon cost avoidance (all figures illustrative and subject to engineering validation).""",
    "pillar_notes": {
        "environment": (
            "NOx permit exceedance (16 of 24 months) and unrecovered flare gas (1.94 MMscfd, "
            "58% recoverable) are the two most material environmental liabilities — both technically "
            "addressable within 18–30 months. The 2030 30% emissions reduction commitment lacks a "
            "funded capital programme, which undermines credibility with regulators and institutional investors."
        ),
        "social": (
            "Workforce safety performance (RIDDOR rate 1.2/200K hrs) sits at industry average, "
            "above the upper-quartile benchmark of 0.7, indicating structural room for improvement "
            "through systematic behaviour-based safety investment. The near-miss reporting rate of "
            "0.9/month is conspicuously low for a site of this scale and process hazard level — "
            "a leading indicator of cultural under-reporting that warrants priority attention."
        ),
        "governance": (
            "Board structure, audit committee oversight, and third-party emissions verification are "
            "appropriately robust for a facility of this scale and regulatory exposure. The absence "
            "of ESG-linked long-term incentive components is a credibility gap that peer comparison "
            "and investor scrutiny will increasingly expose through the proxy advisory cycle."
        ),
        "ethics": (
            "Ethics governance mechanisms — anonymous hotline, conflict-of-interest register, Code "
            "of Business Conduct — are functional and actively used. The material gap is human-rights "
            "due diligence depth in the chemical supply chain; the most recent Sedex assessment "
            "explicitly flags the absence of sub-Tier-1 coverage as an unresolved finding."
        ),
        "innovation": (
            "The ML fouling-prediction pilot on E-304 and IoT vibration monitoring on three critical "
            "pumps demonstrate genuine data-driven operational capability and management willingness "
            "to invest in OT. Capital constraints and legacy DCS architecture (TDC3000, 1997 vintage) "
            "are the primary barriers to scaling; the approved DCS migration provides the technical "
            "foundation for accelerated digital deployment from 2025."
        ),
    },
    "qa": [
        (
            "env_1",
            "Describe your company's approach to reducing carbon emissions and environmental footprint.",
            "We operate under UK ETS obligations with a Scope 1 footprint of approximately 892,000 tCO₂e "
            "(2023 actuals). Current CO₂e intensity is 87 kg per tonne of throughput — approximately 23% "
            "above the sector median for our asset age class. Our most material gap is routine flaring: "
            "1.94 MMscfd of process gas is flared, of which we estimate 58% is recoverable through a "
            "dedicated vapour recovery unit and compressor train. We have committed to a 30% absolute "
            "emissions reduction by 2030 against a 2019 baseline, but no capital programme to achieve "
            "this target has been formally approved or funded to date."
        ),
        (
            "env_2",
            "What environmental certifications, targets, or reporting standards does your company follow?",
            "ISO 14001:2015 certified across all three process units. We report to the Environment Agency "
            "under IPPC permit EP3836/A and publish annual E-PRTR emissions data. NOx emissions at Stack 4 "
            "and Stack 5 (CDU flue gas) have been in exceedance of our permit limit (110 mg/m³) for 16 of "
            "the past 24 months, requiring formal regulatory notifications; an enforcement notice is under "
            "active review by the Environment Agency. We are not yet aligned to TCFD at site level, though "
            "our parent group has signed the TCFD disclosure pledge at board level. SCR investment to "
            "address the NOx exceedance is currently in commercial feasibility review."
        ),
        (
            "soc_1",
            "How does your company support employee wellbeing, diversity, and inclusion?",
            "We operate a mandatory HSE induction programme and maintain a RIDDOR-reportable injury rate "
            "of 1.2 per 200,000 hours worked — at industry average but above the upper-quartile benchmark "
            "of 0.7. Employee mental health provision includes access to an Employee Assistance Programme "
            "and an on-site occupational health team. Gender representation at supervisory level is 14% "
            "female, reflecting structural challenges in the oil and gas talent pipeline. A structured "
            "diversity recruitment programme targeting STEM graduates was launched in 2023. Near-miss "
            "reporting at 0.9/month is below expected levels for a site of this complexity and hazard "
            "profile, suggesting a cultural under-reporting issue that is a priority for our safety leadership."
        ),
        (
            "soc_2",
            "Describe your community engagement and broader social impact initiatives.",
            "The facility contributes approximately £38M annually to the regional economy through wages, "
            "procurement, and induced spend. We maintain a community liaison committee with quarterly "
            "public meetings and a £150K annual community fund supporting local skills-training, STEM "
            "education, and infrastructure initiatives. A formal community impact assessment has not been "
            "conducted since 2018. Odour complaints from residential communities within 2 km of the "
            "facility — 19 in the past 12 months — remain a reputational and social-licence risk that "
            "the proposed process optimisation programme would partially address through reduced routine flaring."
        ),
        (
            "gov_1",
            "How is ethical decision-making embedded in your leadership and governance structure?",
            "We operate under a Group board with an independent non-executive ESG and Audit Committee "
            "that reviews HSE and environmental performance quarterly. Executive remuneration incorporates "
            "an HSE performance multiplier (15% of short-term incentive). No formal ESG KPI weighting "
            "is applied to long-term incentive plans — a gap we are actively reviewing for the 2025 "
            "remuneration cycle. A formal ethics committee was established in 2022 and reports directly "
            "to the Audit Committee. Internal audit includes ESG risk as a standing item in the annual "
            "enterprise risk framework review."
        ),
        (
            "gov_2",
            "What transparency and stakeholder reporting mechanisms does your company have?",
            "We publish an annual Sustainability Report aligned to GRI Standards (Core option) and submit "
            "Group-level TCFD disclosures. Site-level energy data, emissions data, and water consumption "
            "are reported monthly to the Environment Agency and quarterly to Group ESG function. "
            "Third-party verification of Scope 1 and Scope 2 emissions is conducted annually by Bureau "
            "Veritas. No public-facing real-time environmental data dashboard exists at site level; "
            "this is identified as a transparency improvement in our 2024 stakeholder engagement plan."
        ),
        (
            "eth_1",
            "How does your company handle conflicts of interest, whistleblowing, and ethical breaches?",
            "An anonymous ethics and whistleblowing hotline (operated by Expolink, available 24/7) is "
            "accessible to all employees and contractors. In the past 12 months, 8 reports were received: "
            "4 resolved at line-manager level, 3 escalated to HR, 1 referred to legal counsel. No material "
            "upheld breaches of the Code of Business Conduct were recorded. A conflict-of-interest register "
            "is maintained and reviewed annually by the Audit Committee. Anti-bribery and corruption "
            "training is mandatory for all grade-7 and above employees, with a 94% completion rate."
        ),
        (
            "eth_2",
            "Describe your supply chain ethics and responsible sourcing practices.",
            "Chemical and catalyst procurement operates under a Supplier Code of Conduct requiring compliance "
            "with ILO core labour conventions, anti-corruption commitments, and environmental minimum "
            "standards. Tier 1 supplier audits are conducted every two years for spend above £500K "
            "(covering 78% of Tier 1 spend by value in the past cycle). Conflict-mineral disclosures "
            "(Dodd-Frank 3TG) are not material to our product type. We have not conducted formal human-rights "
            "due diligence below Tier 1 suppliers — a gap explicitly flagged in our most recent Sedex "
            "assessment and acknowledged as requiring a structured Tier 2 assessment programme."
        ),
        (
            "inn_1",
            "What sustainable or ethical innovations has your company introduced in the last two years?",
            "An ML-based fouling-prediction model was deployed on heat exchanger train E-304 (CDU-1) in "
            "Q2 2023, reducing unplanned cleaning interventions by 2 per year and improving energy recovery "
            "by approximately 1.8 MW on the monitored circuit. A pilot of IoT vibration monitoring on three "
            "critical centrifugal pumps has demonstrated a 35% reduction in maintenance call-outs on those "
            "units. Approximately 94% of process water is recycled within closed-loop cooling circuits. "
            "Sulphur by-product (98% purity) is sold to fertiliser manufacturers, eliminating the "
            "historical disposal cost of £180K/yr. No formal circular economy programme is in place."
        ),
        (
            "inn_2",
            "How does your company invest in future-focused, responsible technology or processes?",
            "The approved 2024–2026 capital programme includes £3.8M for DCS migration (TDC3000 → "
            "Honeywell Experion PKS) and £1.1M for process historian expansion to site-wide coverage. "
            "A flare gas VRU pre-FEED study was commissioned Q1 2024 with completion expected Q3 2024. "
            "No dedicated R&D or green-technology budget exists at site level. A feasibility study for "
            "CCUS integration was commissioned in 2023 but deprioritised pending clarity on the UK "
            "government's CCUS industrial cluster incentive framework. The Experion migration will "
            "provide the data infrastructure foundation required to scale the ML maintenance pilot "
            "across the full rotating equipment fleet."
        ),
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
#  SCENARIO 2 — LOGISTICS / COLD-CHAIN DISTRIBUTION CENTRE
# ═══════════════════════════════════════════════════════════════════════════════

LOGISTICS = {
    "company_name": "Nordic ColdChain Logistics BV",
    "notes": (
        "Multi-temperature refrigerated distribution centre · 340 employees · "
        "68,000 m² footprint · 1.2M case movements/month · "
        "Sectors: food retail, pharmaceutical, dairy · "
        "Audit scope: refrigeration efficiency, conveyor reliability, "
        "labour productivity, WMS integration, carbon reduction pathway."
    ),
    "extracted_text": """\
FACILITY TECHNICAL BRIEFING — NORDIC COLDCHAIN LOGISTICS BV
Prepared for EcoIQ Audit · Confidential
═══════════════════════════════════════════════════════════════

FACILITY OVERVIEW
Distribution centre commissioned 2006 · Location: Rotterdam, Netherlands
Total footprint: 68,000 m² · Temperature zones: Ambient (24,000 m²), Chilled +4°C (28,000 m²),
Frozen -22°C (12,000 m²), Blast-freeze tunnels -35°C (4,000 m²)
Throughput: 1.2M case movements/month · Peak throughput: 1.65M cases/month (November–December)
Operational model: 3 shifts × 363 days/year · Unionised workforce (78% covered by CBA)

REFRIGERATION SYSTEM
Primary refrigerant: R-404A (GWP: 3,922) — seven condensing units in chilled and frozen zones
Blast-freeze tunnels: HFC-134a (GWP: 1,430) — three units
Annual refrigerant leakage rate: 8.3% of total charge (R-404A circuits)
Industry benchmark leakage rate: <2% · Current rate: 4.15× benchmark
F-Gas compliance: annual audit by certified partner · 3 of 7 R-404A units lack functioning leak detection
Refrigeration COP (measured): 1.8 · Modern CO₂ transcritical benchmark: 2.6–3.1
Estimated annual refrigerant replacement cost: €31,400 (R-404A at current market price)

ENERGY PROFILE
Total electricity consumption: 14.2 GWh/year · Average purchased price: £0.188/kWh
Annual electricity cost: approximately £2.67M
Energy breakdown: Refrigeration 41%, Lighting 24%, Conveyor/MHE 19%, HVAC 11%, IT/Office 5%
Lighting: T5 fluorescent (ambient zone) — no occupancy sensing; LED in 40% of frozen zone
Demand-side response agreement signed 2023: ~£92K grid revenue in year 1

CONVEYOR & SORTATION SYSTEM
Primary sorter: cross-belt sorter — 12,000 units/hour design capacity
Operating throughput: 9,800 units/hour (82% of design)
Unplanned stoppage events: 4.1/shift of >10-minute duration (monitored circuits)
Root causes: sorter jams 57%, drive motor faults 23%, sensor faults 20%
Vibration monitoring pilot (primary sorter, circuit 1): deployed Q4 2023 — 18% stoppage reduction
Remaining 4 sorter circuits: no condition monitoring in place

WORKFORCE & PRODUCTIVITY
Total headcount: 340 (220 permanent, 120 agency)
Annual turnover (pick & dispatch operations): 34% · Sector average: 22%
Lines picked per hour (LPH): 118 · Internal target: 140 · Best-practice benchmark: 155+
Pick accuracy: 99.3% · Customer SLA requirement: 99.7%
WMS: Infor WMS (2014 implementation) · TMS: Blue Yonder (implemented 2022)
WMS-TMS integration stability: 94.7% uptime (target: 99.5%)

CAPITAL PROGRAMME 2024–2026
Conveyor upgrade and sorter expansion: €1.8M (approved)
WMS enhancement programme: €420K (approved)
Refrigerant transition (blast-freeze tunnels to CO₂ transcritical): scoped, not approved
AMR proof-of-concept (ambient pick zone): evaluated Q4 2023, deferred
LED upgrade (ambient zone): £180K (in procurement)
""",
    "scores": {
        "environment": 44,
        "social":      58,
        "governance":  55,
        "ethics":      63,
        "innovation":  50,
        "overall":     54,
    },
    "summary": """\
Nordic ColdChain Logistics BV presents a mid-tier performance profile reflective of a well-managed but operationally constrained refrigerated distribution centre navigating a challenging combination of legacy refrigerant infrastructure, conveyor reliability exposure, and persistent workforce retention pressure. The overall EcoIQ score of 54/100 reflects genuine compliance foundations — ISO 14001, GRI-aligned group reporting, F-Gas management programme, and an active demand-side response contract — offset by a refrigerant leakage rate of 8.3% annually for R-404A systems that is more than four times the industry benchmark and constitutes both the largest single environmental liability and a growing direct cost exposure.

The refrigerant leakage gap translates to an estimated 94 tCO₂e annually from R-404A circuit losses alone (GWP 3,922), at a current replacement cost of approximately €31,400/year — before accounting for the compounding energy efficiency penalty of operating degraded refrigeration circuits. Accelerating the transition timeline for the two highest-leakage blast-freeze units from the planned 2027 end-of-life replacement to a managed 2025–2026 programme would recover this cost exposure and is estimated to improve system COP from 1.8 to approximately 2.4 on the converted circuits, delivering an additional £82K–£110K per annum in electricity cost reduction (illustrative, based on current consumed kWh and measured COP differential).

Conveyor reliability is the primary operational throughput risk. The 18% reduction in unplanned stoppage time achieved through the vibration-sensor pilot on sorter circuit 1 validates the technical approach with an internal, site-specific proof point. Extension of sensor coverage to the remaining four sorter circuits and establishment of a predictive maintenance workflow integrated with the CMMS is the highest-leverage near-term operational investment. Based on the pilot results, a system-wide deployment is estimated to recover approximately 6–9 hours of annual unplanned downtime per circuit — with a throughput value of £38K–£64K per circuit-hour depending on shift pattern and product mix.

Labour productivity and WMS fragmentation are structurally interconnected. The WMS-TMS integration achieved a 22% improvement in order processing time; stabilising integration uptime from 94.7% to the 99.5% target and resolving the AMR proof-of-concept deferral would enable the next phase of pick productivity improvement. At current throughput volumes, a 5-percentage-point improvement in pick accuracy (from 99.3% to 99.7%, meeting customer SLA) would save an estimated 2,900 rework hours annually and remove the SLA exposure risk for the two largest pharmaceutical clients.

Priority actions for the next 12 months: (1) accelerate blast-freeze refrigerant transition for the two highest-leakage R-404A units — business case estimated at €380K capex, 2.8-year payback; (2) complete Dräger leak-sensor installation on all remaining R-404A units and integrate alarms into BMS; (3) extend conveyor vibration monitoring to all five sorter circuits and establish predictive maintenance protocol; (4) stabilise WMS-TMS integration to 99.5% uptime target and re-open AMR proof-of-concept review; (5) implement structured pick-zone ergonomics programme for the 6 remaining high-risk stations identified in the 2023 union ergonomics review. Illustrative aggregate annual savings from full programme: £195K–£280K energy and refrigerant cost reduction, plus estimated £85K–£120K labour efficiency improvement (all figures illustrative, subject to operational validation).""",
    "pillar_notes": {
        "environment": (
            "The R-404A refrigerant leakage rate of 8.3% — against an industry benchmark below 2% — "
            "is the dominant environmental exposure: 94 tCO₂e annually at a direct replacement cost "
            "of ~€31K/year, with an additional energy efficiency penalty. Demand-side response and LED "
            "initiatives demonstrate genuine efficiency commitment at the margin, but the refrigerant "
            "transition programme is the material lever for environmental performance improvement."
        ),
        "social": (
            "Labour relations are structured and constructive, with active union collaboration on "
            "ergonomics delivering measurable safety improvements. The 34% annual turnover rate in "
            "pick and dispatch — 55% above sector average — represents a meaningful productivity and "
            "training cost that structured onboarding, shift-pattern optimisation, and the proposed "
            "AMR deployment could partially address."
        ),
        "governance": (
            "Group governance frameworks are well-structured and compliant; the performance gap is "
            "in cascading ESG KPIs to site-level individual performance frameworks, and in the "
            "€250K group capital-approval threshold that has created delays in time-sensitive "
            "refrigerant compliance investments. A site-level ESG KPI dashboard would strengthen "
            "management accountability."
        ),
        "ethics": (
            "Ethics governance is comprehensive at group level, actively used, and extended to suppliers "
            "through biennial self-assessments. The two most actionable gaps are the absence of a "
            "site-level anti-bribery risk assessment and the 35% of packaging spend with suppliers "
            "lacking formal sustainability certification — both addressable within the existing "
            "procurement framework."
        ),
        "innovation": (
            "The WMS-TMS integration (22% order processing improvement) and the conveyor vibration-sensor "
            "pilot (18% stoppage reduction on circuit 1) demonstrate real operational technology capability "
            "with measurable, internal proof points. The deferred AMR evaluation and absence of a "
            "site-level green-technology R&D budget reflect capital prioritisation rather than innovation "
            "appetite — the approved 2024–2026 programme provides a foundation for deployment acceleration."
        ),
    },
    "qa": [
        (
            "env_1",
            "Describe your company's approach to reducing carbon emissions and environmental footprint.",
            "Our Scope 1 emissions arise primarily from refrigerant leakage — the annual R-404A leakage "
            "rate of 8.3% from our chilled and frozen circuits is our most material environmental "
            "exposure, representing approximately 94 tCO₂e per year. Scope 2 electricity consumption "
            "is 14.2 GWh per year, representing 85% of total energy cost. We committed in 2022 to "
            "transitioning all blast-freeze tunnels to natural refrigerant (CO₂ transcritical) by 2027 "
            "as existing equipment reaches end-of-life; no managed early-replacement programme has been "
            "triggered. LED lighting upgrades to the frozen zone were completed in 2022, saving "
            "approximately 160 MWh annually. A demand-side response contract with the local grid "
            "operator signed in 2023 generated approximately £92K in frequency-response revenue in "
            "the first year, utilising our refrigeration thermal mass as a controllable load."
        ),
        (
            "env_2",
            "What environmental certifications, targets, or reporting standards does your company follow?",
            "ISO 14001:2015 certified (last recertification 2023). We report Scope 1 and 2 emissions "
            "within our parent group's GRI Standards-aligned annual sustainability report. We have not "
            "set an SBTi-validated target at entity level, though the group has committed to develop "
            "a validated pathway by 2025. F-Gas regulatory returns are filed annually; the most recent "
            "compliance audit identified that 3 of our 7 R-404A condensing units lack functioning "
            "refrigerant leak detection — a finding we are remediating by retrofitting Dräger sensors "
            "on all units, with completion targeted Q3 2024. EU F-Gas Regulation phase-down schedule "
            "will restrict R-404A availability from 2025, adding urgency to the transition programme."
        ),
        (
            "soc_1",
            "How does your company support employee wellbeing, diversity, and inclusion?",
            "We operate a unionised workforce under a collective bargaining agreement covering 78% of "
            "operational staff. Shift rotation policies comply with the Working Time Directive and "
            "are structured to limit continuous night-shift exposure. Our Lost Time Injury Frequency "
            "Rate was 3.4 per million hours in the prior year, with manual handling incidents in the "
            "ambient pick zone representing 60% of recordable events. A collaborative ergonomics review "
            "with the union safety committee identified 12 high-risk picking stations; 6 have been "
            "addressed through powered-assist trolley deployment. Annual staff turnover of 34% in "
            "pick and dispatch — against a sector average of 22% — is a persistent workforce challenge. "
            "No formal mental health support programme exists beyond the statutory EAP entitlement."
        ),
        (
            "soc_2",
            "Describe your community engagement and broader social impact initiatives.",
            "We employ 85% of permanent staff from within a 15 km radius, supporting employment in "
            "a region with above-average structural unemployment. We sponsor a regional food-bank "
            "volunteer programme (140 employee volunteer days in the past year) and maintain a "
            "partnership with a regional logistics college supporting 10 supply-chain apprenticeships. "
            "We have not conducted a formal community impact assessment. Our environmental permit "
            "requires annual reporting to the local authority on refrigerant and ammonia contingency "
            "planning; community-facing disclosure of this risk information is limited to the annual "
            "permit compliance report."
        ),
        (
            "gov_1",
            "How is ethical decision-making embedded in your leadership and governance structure?",
            "Governance operates through our Dutch parent group, with a local site management board "
            "meeting monthly. A group ESG working group was established in 2022, but site-level ESG "
            "KPIs have not yet been cascaded into individual performance frameworks — a gap we have "
            "committed to address in the 2025 performance management cycle. Capital approval for "
            "environmental investments requires group-level sign-off above €250K, which has created "
            "delays for the refrigerant compliance capex. A local ethics and compliance policy is in "
            "place and reviewed annually. The site General Manager's quarterly review agenda includes "
            "standing items for energy, safety, and quality KPIs."
        ),
        (
            "gov_2",
            "What transparency and stakeholder reporting mechanisms does your company have?",
            "Annual group sustainability report aligned to GRI Standards. Site-level energy, "
            "refrigerant leakage, and safety data are reported quarterly to the group ESG function. "
            "No public-facing disclosure of site-level performance data exists. Internal management "
            "accounts include an energy cost dashboard reviewed monthly by the site General Manager. "
            "F-Gas regulatory returns are filed annually with the Netherlands Enterprise Agency. "
            "ISO 14001 management review includes regulatory compliance status and significant "
            "environmental aspect performance review twice per year."
        ),
        (
            "eth_1",
            "How does your company handle conflicts of interest, whistleblowing, and ethical breaches?",
            "A group-level ethics hotline is available in six languages to all employees and contractors. "
            "No site-specific reports were received in the past 12 months. Our Code of Conduct is "
            "signed by all employees at onboarding and reviewed every two years. Anti-bribery and "
            "corruption training is mandatory for all supervisory and management grades. No formal "
            "site-level anti-bribery risk assessment has been conducted — the group-level policy and "
            "training programme are in place, but a site-specific assessment of our highest-risk "
            "procurement and contractor relationships has not been completed."
        ),
        (
            "eth_2",
            "Describe your supply chain ethics and responsible sourcing practices.",
            "Procurement of refrigeration chemicals, packaging materials, and third-party logistics "
            "services is managed under a group Supplier Code of Conduct. Tier 1 supplier self-assessments "
            "are conducted biennially for suppliers above a €100K annual spend threshold. Approximately "
            "38% of our packaging spend is with suppliers certified to FSC or PEFC standards — below "
            "our 2025 target of 60%. Cold-chain food-safety requirements impose additional supplier "
            "qualification criteria through our BRC Global Standard audit process. We conduct "
            "refrigerant supplier qualification annually through our F-Gas compliance partner."
        ),
        (
            "inn_1",
            "What sustainable or ethical innovations has your company introduced in the last two years?",
            "In the past 18 months we implemented a WMS-TMS integration layer connecting our legacy "
            "Infor WMS with the Blue Yonder TMS, reducing order processing time by 22% and eliminating "
            "approximately 1,300 manual data-entry hours per month. A trial of automated conveyor fault "
            "detection using vibration sensors on our primary sorter circuit (circuit 1 of 5) has "
            "delivered an 18% reduction in unplanned stoppage time on the monitored segment. A "
            "proof-of-concept for autonomous mobile robots in the ambient pick zone was evaluated "
            "in Q4 2023 but deferred pending WMS integration stability improvements. We signed a "
            "demand-side response agreement utilising refrigeration load as a controllable DSR asset, "
            "generating £92K in grid revenue in year 1."
        ),
        (
            "inn_2",
            "How does your company invest in future-focused, responsible technology or processes?",
            "Capital investment in technology is governed by the group's three-year capex cycle. "
            "The 2024–2026 programme approved €1.8M for conveyor upgrade and sorter expansion and "
            "€420K for WMS enhancement. No site-level green-technology R&D budget exists. The group "
            "has joined the Global Cold Chain Alliance sustainability working group, providing access "
            "to benchmarking data and best-practice sharing. The vibration-sensor pilot represents "
            "our first internal proof point for predictive maintenance in the DC environment; "
            "the 2025 technology roadmap under development will incorporate extension of this approach "
            "to all five sorter circuits and to the refrigeration compressor fleet."
        ),
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
#  SCENARIO 3 — MINING / METALLURGY (COPPER SMELTING)
# ═══════════════════════════════════════════════════════════════════════════════

MINING = {
    "company_name": "Atlas Metallurgical Works",
    "notes": (
        "Integrated copper smelting and refining operation · 620 employees · "
        "180,000 tpa refined copper equivalent · Flash furnace + Peirce-Smith converters · "
        "ICMM member · Copper Mark certified · "
        "Audit scope: process energy intensity, heat recovery, water circuit efficiency, "
        "mobile equipment emissions, process stability, ESG posture."
    ),
    "extracted_text": """\
FACILITY TECHNICAL BRIEFING — ATLAS METALLURGICAL WORKS
Prepared for EcoIQ Audit · Confidential
═══════════════════════════════════════════════════════════════

FACILITY OVERVIEW
Smelter commissioned 1987 (major expansion 2004) · Location: Northern Chile
Annual throughput: 180,000 tonnes refined copper equivalent
Process route: Flash furnace → Peirce-Smith converters (×4) → Anode furnace → Tankhouse
Concentrate feed: 65% own mine production, 35% purchased concentrate
Employees: 620 direct (380 operational, 140 maintenance, 100 technical/support)
Contractors: 210 (primarily turnaround and construction)
ICMM member since 2011 · Copper Mark certified since 2022

ENERGY PROFILE
Specific energy consumption: 2.8 GJ per tonne refined copper
Global benchmark (upper-quartile operations): 2.4 GJ/t · Gap: +17%
Primary electricity consumer: Tankhouse electrolysis (52%), compressed air systems (18%),
water pumping (14%), process gas handling (11%), auxiliary (5%)
Diesel consumption (mobile equipment fleet): 8.4M litres/year
Mobile equipment: 34 haul trucks (150t capacity), 18 LHDs, 24 light vehicles
Diesel as % of Scope 1 emissions: 28%

HEAT RECOVERY SYSTEM
Flash furnace off-gas waste heat boiler (WHB): capacity 42 MW thermal
Current heat capture rate: 42% of recoverable off-gas enthalpy
Remaining 58% rejected through gas-cleaning system (electrostatic precipitator + wet scrubber)
Pre-feasibility study (2023): identified 12 MW additional WHR opportunity via extended off-gas duct
Process steam demand: 28 MW continuous (mostly flash furnace oxygen preheating + tankhouse)
Gap between WHR supply and steam demand: partially covered by 3× diesel-fired auxiliary boilers

WATER MANAGEMENT
Process water circuit: closed-loop (primary + secondary circuits)
Total water abstraction: 2.1 ML/day from regional aquifer (regulated under water-use licence)
Water licence limit: 2.4 ML/day · Internal 2025 target: 1.8 ML/day
Recirculation rate: 91% (measured; loss through evaporation and blowdown)
Secondary circuit pump efficiency: 68% hydraulic efficiency (design: 82%) — identified as primary gap
Primary circuit pumps: 8 units × 280 kW · Secondary circuit pumps: 16 units × 185 kW

EMISSIONS
Scope 1 CO₂e (2023): 312,000 tCO₂e
  — Diesel combustion: 87,200 tCO₂e (28%)
  — Process electricity (Scope 2 / grid factor): 94,000 tCO₂e equivalent (not Scope 1)
  — Auxiliary boiler combustion: 38,400 tCO₂e (12%)
SO₂ from smelter: 1,840 tonnes (2023) · Permit cap: 2,200 tonnes · Headroom: 16%
Acid plant SO₂ capture efficiency: 96.8% (target: >97.5%)

PROCESS STABILITY
Flash furnace oxygen enrichment: target 72% O₂ · measured variance: ±4.2% (2022 baseline)
Process instability events (oxygen upset → burden adjustment): 38 events in 2022
Post-stability-system deployment: 26 events in 2023 · Reduction: 31.6%
Copper recovery rate (2022): 98.6% · Copper recovery rate (2023): 99.0% · Δ = +0.4 pp
Estimated value of 0.4 pp recovery improvement: ~720 tpa additional refined copper × market price

SAFETY
TRIFR (2023): 4.2 per million hours worked
ICMM member median TRIFR: 3.1 · Gap: +35% vs median
Near-miss reporting rate: +68% increase post-BBS implementation (2022–2023)
Lost Time Injury rate: 1.8 (2023) vs 2.4 (2021) — improving trend
Indigenous Employment Programme: 34% of workforce from local communities
""",
    "scores": {
        "environment": 38,
        "social":      54,
        "governance":  62,
        "ethics":      64,
        "innovation":  46,
        "overall":     53,
    },
    "summary": """\
Atlas Metallurgical Works presents a performance profile characteristic of a responsible but operationally intensive primary metals producer actively managing the tension between legacy energy infrastructure and a credible modernisation trajectory. The overall EcoIQ score of 53/100 reflects strong governance and ethics foundations — ICMM membership, Copper Mark certification, Deloitte-assured ESG reporting — alongside material operational gaps in process energy intensity, heat recovery utilisation, and mobile equipment emissions that constrain environmental performance well below upper-quartile peer benchmarks.

The single highest-value identified opportunity is the expansion of waste heat recovery from the flash furnace and converter off-gases. The 2023 pre-feasibility study identifies a 12 MW additional WHR opportunity via an extended off-gas duct and secondary heat exchange train. At a conservative valuation of USD 44/MWh for displaced diesel-fired auxiliary steam generation, full realisation of this opportunity generates approximately USD 4.6M in annual energy cost avoidance. Against an estimated pre-FEED and detailed design cost of USD 680K and a capital expenditure of USD 6.2M, the project offers an unlevered payback of approximately 2.7 years at current diesel prices — a compelling return profile that also eliminates approximately 38,000 tCO₂e annually from auxiliary boiler combustion (illustrative; subject to engineering validation and actual off-gas enthalpy measurement).

Process water circuit efficiency is the second priority. The gap between current fresh water abstraction (2.1 ML/day) and the internal 2025 target (1.8 ML/day) is attributable primarily to hydraulic efficiency degradation in the secondary circuit pumps, which are operating at 68% hydraulic efficiency against a design specification of 82%. The condition monitoring pilot on the primary circuit has already identified two pumps with bearing wear profiles predictive of failure within 60–90 days — enabling proactive replacement rather than reactive response. Extending condition monitoring to all 24 pumps across both circuits and executing a structured hydraulic efficiency refurbishment programme is estimated to recover 0.25–0.35 ML/day of fresh water abstraction, advancing the internal 2025 target achievement by approximately 12–18 months.

The flash furnace process stability system is the standout innovation achievement of the past two years. The 31% reduction in oxygen-enrichment instability events and the resulting 0.4 percentage-point improvement in copper recovery represent a directly measurable, sustained operational gain with a quantifiable value of approximately USD 5.2M per annum in additional refined copper output at current LME pricing. Extending this approach to the Peirce-Smith converter circuit — the next highest-variability unit operation — with a comparable sensor and ML model deployment would be the logical next scale step, with a comparable order of magnitude benefit reasonably projectable given the structural similarity of the control problem.

Mobile equipment diesel consumption (8.4M litres/year, 28% of Scope 1 CO₂e) requires a structured transition programme. Light vehicle electrification is approved; haul truck electrification is capital-intensive but is moving from experimental to early-commercial deployment in peer operations globally. Participating in an OEM development programme or pilot partnership in 2025–2026 would position Atlas ahead of the regulatory and customer-driven requirement rather than responding under duress — consistent with the proactive positioning that Copper Mark certification and ICMM membership signal to the market.

Priority actions for the next 12 months: (1) advance WHR expansion to pre-FEED completion and secure board approval for USD 6.2M capex — target Q3 2024 sanction for Q1 2026 commissioning; (2) extend pump condition monitoring to all 24 circuit pumps and initiate the hydraulic efficiency refurbishment programme; (3) deploy flash furnace stability system approach to Peirce-Smith converter circuit 1; (4) initiate haul truck electrification market assessment and formal OEM engagement; (5) publish external real-time energy and water performance dashboard as committed in the 2025 transparency plan. Illustrative aggregate annual benefit from full programme: USD 8M–USD 11M operational improvement plus approximately 42,000 tCO₂e annual emissions reduction (illustrative, subject to engineering validation).""",
    "pillar_notes": {
        "environment": (
            "Specific energy intensity of 2.8 GJ/t copper against a 2.4 GJ/t upper-quartile benchmark "
            "and the 58% uncaptured fraction of recoverable off-gas enthalpy are the dominant "
            "environmental performance gaps — both technically addressable within the existing "
            "Technology Roadmap capital envelope. SO₂ permit headroom (16%) provides near-term "
            "regulatory buffer, but acid plant capture efficiency below target requires sustained focus."
        ),
        "social": (
            "The TRIFR of 4.2 per million hours is 35% above the ICMM member median and the primary "
            "social performance priority for the board safety committee. The BBS programme implementation "
            "and the 68% increase in near-miss reporting indicate positive directional momentum — the "
            "challenge is converting leading indicator improvement into lagging indicator reduction, "
            "which typically requires 18–24 months of sustained cultural reinforcement."
        ),
        "governance": (
            "ICMM alignment, Deloitte-assured ESG reporting, and executive incentive linkage to HSE "
            "performance (20% STI weighting) are credibly implemented and represent sector-appropriate "
            "governance maturity. The planned 2025 publication of a real-time external energy and water "
            "performance dashboard would further strengthen the transparency positioning consistent "
            "with Copper Mark certification."
        ),
        "ethics": (
            "Copper Mark certification and an ICMM-compliant Responsible Sourcing Policy represent "
            "genuine ethical performance leadership among primary copper producers. The two ongoing "
            "ethics investigations related to contractor labour practices — the most frequent category "
            "in the 2023 ethics report — require careful, transparent resolution to protect the "
            "social licence and maintain ICMM membership in good standing."
        ),
        "innovation": (
            "The flash furnace process stability system is a genuine operational technology achievement: "
            "31% reduction in instability events and a measurable 0.4 percentage-point copper recovery "
            "improvement (~720 tpa additional output) sustained over 18 months. The USD 28M Technology "
            "Roadmap provides a credible investment framework; the primary execution risk is contractor "
            "and specialised equipment availability in the current capital goods market, which warrants "
            "early procurement engagement for the WHR expansion programme."
        ),
    },
    "qa": [
        (
            "env_1",
            "Describe your company's approach to reducing carbon emissions and environmental footprint.",
            "Our smelting operations have a specific energy consumption of 2.8 GJ per tonne of refined "
            "copper — approximately 17% above the global upper-quartile benchmark of 2.4 GJ/t. Diesel "
            "mobile equipment (34 haul trucks, 18 LHDs) accounts for 28% of our Scope 1 emissions at "
            "8.4M litres per year. An electric vehicle transition plan for light vehicles was approved "
            "in 2023; haul truck electrification is not yet in scope given capital requirements and "
            "charging infrastructure constraints. Heat recovery from converter and flash furnace off-gases "
            "captures approximately 42% of recoverable waste enthalpy via a waste heat boiler; the "
            "remaining 58% is rejected through the gas-cleaning circuit. A 2023 pre-feasibility study "
            "identified a 12 MW additional WHR opportunity. Three diesel-fired auxiliary boilers provide "
            "supplementary process steam — this represents the most immediately addressable Scope 1 "
            "emissions reduction target through WHR expansion."
        ),
        (
            "env_2",
            "What environmental certifications, targets, or reporting standards does your company follow?",
            "ISO 14001:2015 certified. We report under the Mining Association of Canada's Towards "
            "Sustainable Mining (TSM) protocol and publish an annual sustainability report aligned "
            "to GRI Standards (Comprehensive option) and the ICMM Principles. Third-party assurance "
            "of Scope 1 and 2 emissions, water abstraction data, and TRIFR is provided by Deloitte. "
            "Our SO₂ emissions (1,840 tonnes, 2023) operate with 16% headroom below the permit cap "
            "of 2,200 tonnes; however, acid plant SO₂ capture efficiency at 96.8% is below our "
            "internal target of >97.5% and is a continuous improvement priority. Process water "
            "abstraction of 2.1 ML/day is 12% below our licence limit but 17% above our internal "
            "2025 target of 1.8 ML/day due to hydraulic efficiency degradation in the secondary "
            "pumping circuit. A community water monitoring programme with real-time public data "
            "sharing was launched in 2023."
        ),
        (
            "soc_1",
            "How does your company support employee wellbeing, diversity, and inclusion?",
            "Mining and metallurgical operations present inherent safety risk. Our Total Recordable "
            "Injury Frequency Rate was 4.2 per million hours worked in 2023 — 35% above the ICMM "
            "member median of 3.1 — and remains the primary focus area for our board safety committee. "
            "A behaviour-based safety programme launched in 2022 has delivered a 68% increase in "
            "near-miss reporting; Lost Time Injury rate improved from 2.4 (2021) to 1.8 (2023), "
            "though lagging indicator improvement has not yet fully reflected leading indicator gains. "
            "34% of our workforce are from local indigenous communities, supported by a formal "
            "Indigenous Employment Programme including mentoring, technical training, and career "
            "progression pathways. No formal mental health support programme exists beyond the "
            "statutory EAP entitlement; this is identified as a gap in our 2024 social performance plan."
        ),
        (
            "soc_2",
            "Describe your community engagement and broader social impact initiatives.",
            "We maintain a formal Community Development Agreement (CDA) with the regional indigenous "
            "council governing land access, employment preference, procurement preference, and community "
            "investment commitments. Annual community investment is approximately USD 1.8M, directed "
            "towards infrastructure, education, and health programmes in surrounding communities. "
            "Independent social impact monitoring is conducted every two years; the 2022 assessment "
            "identified water security and road-haulage noise as the two most significant community "
            "concerns. The community water monitoring programme launched in 2023 — with real-time "
            "publicly accessible data — was a direct response to these findings and has been well "
            "received by community stakeholders and the regional water authority."
        ),
        (
            "gov_1",
            "How is ethical decision-making embedded in your leadership and governance structure?",
            "Our parent group maintains an independent board with a dedicated Sustainability and Risk "
            "Committee reviewing HSE and environmental performance quarterly. Site-level governance "
            "operates through a monthly management review against 24 defined operational and "
            "sustainability KPIs. Executive short-term incentive includes a 20% weighting for HSE "
            "and environmental performance outcomes. A group-level Ethics and Compliance Policy applies "
            "to all employees and contractors, reinforced through annual mandatory training (97% "
            "completion rate, 2023). No formal site-level ethics committee exists; the group-level "
            "Audit and Ethics Committee exercises oversight of site escalations."
        ),
        (
            "gov_2",
            "What transparency and stakeholder reporting mechanisms does your company have?",
            "Annual sustainability report published to GRI Standards (Comprehensive) and ICMM Principles. "
            "Third-party assurance by Deloitte covers Scope 1 and 2 emissions, water abstraction, "
            "TRIFR, and community investment data. Site-level energy and water KPIs are reported "
            "monthly to the group ESG function and disclosed in the annual report. An internal real-time "
            "energy and water KPI dashboard is available to management and technical staff. Publication "
            "of this dashboard externally is planned for 2025 as part of our expanded transparency "
            "commitments under the Copper Mark framework. TSM protocol performance is disclosed "
            "annually through the Mining Association of Canada's public reporting system."
        ),
        (
            "eth_1",
            "How does your company handle conflicts of interest, whistleblowing, and ethical breaches?",
            "A 24/7 anonymous ethics hotline accessible in three languages is operated by an independent "
            "third party. In 2023, 11 reports were received: 6 resolved at site level, 3 escalated to "
            "group HR, 2 under investigation at year-end. The most frequent concern category was "
            "contractor labour practices — reflecting the complexity of managing a 210-person contractor "
            "workforce across multiple specialist disciplines. A formal ethics risk assessment conducted "
            "in 2023 identified contractor oversight and procurement integrity as the two highest-rated "
            "ethical risk areas. An enhanced contractor labour standards audit programme was commissioned "
            "in Q1 2024 in response."
        ),
        (
            "eth_2",
            "Describe your supply chain ethics and responsible sourcing practices.",
            "Responsible sourcing is a material issue given ICMM membership obligations and growing "
            "downstream customer due diligence requirements. We operate under an ICMM-compliant "
            "Responsible Sourcing Policy and achieved Copper Mark certification in 2022 — the most "
            "rigorous third-party assurance standard specific to the copper value chain. All major "
            "reagent and consumable suppliers above USD 500K annual spend are subject to a supplier "
            "sustainability assessment; 76% have completed an assessment in the past two years. "
            "The vehicle electrification programme is prompting a systematic review of our diesel "
            "supply chain transition, including supplier qualification for charging infrastructure "
            "and battery management systems — a new supply chain category requiring new ethical "
            "sourcing controls including battery material provenance and responsible disposal frameworks."
        ),
        (
            "inn_1",
            "What sustainable or ethical innovations has your company introduced in the last two years?",
            "The most significant operational innovation is the deployment of a process stability "
            "monitoring system on the flash furnace in Q2 2022. The system uses real-time multi-sensor "
            "data (oxygen enrichment, burden temperature, off-gas composition) to detect instability "
            "precursors and automatically adjust operating parameters. Measurable outcomes over 18 months: "
            "instability events reduced by 31% (from 38 to 26 events/year), copper recovery rate "
            "improved by 0.4 percentage points (from 98.6% to 99.0%), representing approximately "
            "720 additional tonnes of refined copper annually at current throughput. A separate pilot "
            "of condition monitoring on the 8 primary water circuit pumps has identified 2 units with "
            "bearing wear patterns predictive of failure within 60–90 days, enabling proactive scheduled "
            "replacement and avoiding unplanned pump failures on a critical circuit."
        ),
        (
            "inn_2",
            "How does your company invest in future-focused, responsible technology or processes?",
            "Technology investment is guided by a five-year Technology Roadmap adopted in 2023, with "
            "total planned expenditure of USD 28M. Priority programmes: process electrification "
            "(USD 8M, light vehicle fleet and fixed-plant compressed-air systems); WHR system expansion "
            "(USD 6.2M capex, targeting 12 MW additional heat recovery); digital process control "
            "upgrades (USD 4.5M, including converter circuit stability system scale-out); water "
            "efficiency programme (USD 2.1M, pump refurbishment and secondary circuit optimisation). "
            "A formal responsible AI and data governance policy was adopted in Q1 2024 to govern "
            "the increasing use of ML models in process control. The Copper Mark certification "
            "process included a structured technology and innovation assessment — scores in this "
            "dimension were the highest achieved across all Copper Mark criteria."
        ),
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
#  COMMAND
# ═══════════════════════════════════════════════════════════════════════════════

DEMO_REGISTRY = {
    "refinery":  REFINERY,
    "logistics": LOGISTICS,
    "mining":    MINING,
}


class Command(BaseCommand):
    help = (
        "Seed three investor-demo EcoIQ audit sessions — Oil Refinery, "
        "Logistics/Cold-Chain, and Mining/Metallurgy — with pre-built findings."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo assessments before seeding.",
        )
        parser.add_argument(
            "--only",
            choices=list(DEMO_REGISTRY.keys()),
            help="Seed only one specific scenario.",
        )

    def handle(self, *args, **options):
        reset    = options["reset"]
        only_key = options.get("only")

        if only_key:
            targets = {only_key: DEMO_REGISTRY[only_key]}
        else:
            targets = DEMO_REGISTRY

        for key, data in targets.items():
            self._seed(key, data, reset)

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Seeded {len(targets)} demo scenario(s). "
            "Visit /esg/ to view the assessments."
        ))

    # ── internal ──────────────────────────────────────────────────────────────

    def _seed(self, key: str, data: dict, reset: bool):
        name = data["company_name"]
        self.stdout.write(f"\n── {name} ──")

        existing = Assessment.objects.filter(company_name=name).first()
        if existing:
            if reset:
                existing.delete()
                self.stdout.write("  Deleted existing record.")
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Already exists (pk={existing.pk}). Use --reset to recreate."
                    )
                )
                return

        # Create Assessment
        assessment = Assessment.objects.create(
            company_name   = name,
            status         = Assessment.STATUS_COMPLETE,
            notes          = data.get("notes", ""),
            extracted_text = data.get("extracted_text", ""),
        )
        self.stdout.write(f"  Created assessment pk={assessment.pk}")

        # Create QuestionnaireResponses
        for q_key, q_text, q_answer in data["qa"]:
            QuestionnaireResponse.objects.create(
                assessment    = assessment,
                question_key  = q_key,
                question_text = q_text,
                answer        = q_answer,
            )
        self.stdout.write(f"  Saved {len(data['qa'])} questionnaire responses")

        # Create Finding
        sc = data["scores"]
        Finding.objects.create(
            assessment         = assessment,
            score_environment  = sc["environment"],
            score_social       = sc["social"],
            score_governance   = sc["governance"],
            score_ethics       = sc["ethics"],
            score_innovation   = sc["innovation"],
            score_overall      = sc["overall"],
            summary            = data["summary"],
            pillar_notes       = data["pillar_notes"],
            raw_ai_response    = "",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"  Finding created — Overall: {sc['overall']}/100 "
                f"(E:{sc['environment']} S:{sc['social']} G:{sc['governance']} "
                f"Eth:{sc['ethics']} I:{sc['innovation']})"
            )
        )
