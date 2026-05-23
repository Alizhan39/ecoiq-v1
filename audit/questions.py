"""
15-question industrial audit questionnaire for manufacturing facilities.
3 questions per area × 5 areas.
Each entry: (key, area_label, area_color, question_text, placeholder)
"""

QUESTIONS = [
    # ── Energy ───────────────────────────────────────────────────────────────
    ('en_1', 'Energy', '#fef3c7',
     'What are your primary energy sources and approximate annual energy cost (electricity, gas, steam)?',
     'e.g. Grid electricity ~$2.4M/yr, natural gas ~$800K/yr, no sub-metering in place…'),

    ('en_2', 'Energy', '#fef3c7',
     'Which processes or systems consume the most energy in your facility?',
     'e.g. Compressor room accounts for ~35%, HVAC ~20%, furnaces ~25%…'),

    ('en_3', 'Energy', '#fef3c7',
     'Describe any current energy efficiency measures or monitoring systems you have.',
     'e.g. Some lighting converted to LED, no real-time energy monitoring, no ISO 50001…'),

    # ── Production ────────────────────────────────────────────────────────────
    ('pr_1', 'Production', '#dcfce7',
     'What is your current Overall Equipment Effectiveness (OEE) or utilisation rate? What causes the most downtime?',
     'e.g. OEE ~55%, main causes: unplanned breakdowns ~40%, changeovers ~30%, quality rejects ~30%…'),

    ('pr_2', 'Production', '#dcfce7',
     'Describe your current production bottlenecks and any known throughput constraints.',
     'e.g. Assembly line 3 is the constraint — max 800 units/day vs demand of 1,100…'),

    ('pr_3', 'Production', '#dcfce7',
     'What is your current scrap, rework, or waste rate, and what are the main quality failure modes?',
     'e.g. ~4% scrap rate, mainly dimensional defects from aging CNC tooling and manual inspection errors…'),

    # ── Maintenance ───────────────────────────────────────────────────────────
    ('mn_1', 'Maintenance', '#ede9fe',
     'Describe your current maintenance strategy and how maintenance work orders are managed.',
     'e.g. Mostly reactive, CMMS used but not consistently, 6 maintenance technicians for 120 machines…'),

    ('mn_2', 'Maintenance', '#ede9fe',
     'Which equipment or systems fail most frequently, and what is the approximate cost of unplanned downtime?',
     'e.g. Hydraulic presses fail ~4×/month, each incident costs ~$12K in lost production…'),

    ('mn_3', 'Maintenance', '#ede9fe',
     'Do you have any condition monitoring, vibration analysis, or predictive maintenance tools in place?',
     'e.g. No predictive tools, some thermal imaging done annually by a contractor…'),

    # ── Systems & Automation ──────────────────────────────────────────────────
    ('au_1', 'Automation & Systems', '#fce7f3',
     'What is the current automation level of your production lines, and how old are your control systems (PLCs, SCADA, DCS)?',
     'e.g. Semi-automated, PLCs are 15–20 years old, no SCADA, manual data entry for production reporting…'),

    ('au_2', 'Automation & Systems', '#fce7f3',
     'Which processes currently rely on manual labour that could realistically be automated or digitised?',
     'e.g. Quality inspection is 100% manual, material handling between stations is manual, production reporting is paper-based…'),

    ('au_3', 'Automation & Systems', '#fce7f3',
     'Describe your current data collection and reporting systems (ERP, MES, historian, spreadsheets).',
     'e.g. ERP for finance only, no MES, production data collected on paper then entered into Excel end of shift…'),

    # ── Infrastructure & Safety ───────────────────────────────────────────────
    ('in_1', 'Infrastructure & Safety', '#dbeafe',
     'What is the condition of your physical infrastructure — building, utilities, compressed air, water treatment?',
     'e.g. Building is 30 years old, compressed air system has significant leaks (~25% loss), water treatment needs upgrade…'),

    ('in_2', 'Infrastructure & Safety', '#dbeafe',
     'Describe your safety incident rate and any recurring safety issues or near-misses.',
     'e.g. 3 recordable incidents in past 12 months, ergonomic issues at manual stations, no real-time safety monitoring…'),

    ('in_3', 'Infrastructure & Safety', '#dbeafe',
     'Are there any planned capital investments or modernisation projects already budgeted?',
     'e.g. $500K budgeted for new compressor next year, no other capex planned, management open to ROI-justified proposals…'),
]

AREA_META = {
    'Energy':                  {'color': '#fef3c7', 'icon': '⚡'},
    'Production':              {'color': '#dcfce7', 'icon': '⚙️'},
    'Maintenance':             {'color': '#ede9fe', 'icon': '🔧'},
    'Automation & Systems':    {'color': '#fce7f3', 'icon': '🤖'},
    'Infrastructure & Safety': {'color': '#dbeafe', 'icon': '🏭'},
}


def grouped():
    groups = {}
    for key, area, color, text, placeholder in QUESTIONS:
        if area not in groups:
            groups[area] = {'color': color, 'icon': AREA_META[area]['icon'], 'questions': []}
        groups[area]['questions'].append((key, text, placeholder))
    return groups
