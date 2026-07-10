"""
capital_guardian/services/ai_director.py — Phase 3 "AI Project Director"
Morning Briefing. This is NOT a second AI/LLM system and makes no model
call: it is a deterministic narrative template over data every other
Capital Guardian service already computed (red flags, capital trace,
equipment health, operational snapshots) — the same discipline as
red_flag_engine.py. Decision Studio remains the one place an LLM answers an
open-ended question; this briefing only assembles real findings into
sections, exactly like a human analyst reading five reports would.
"""
from capital_guardian.services import equipment_health, investor_dashboard, red_flag_engine


def _production_section(project):
    snapshot = project.operational_snapshots.order_by('-date').first()
    if snapshot is None:
        return {'available': False, 'reason': 'No operational snapshot recorded yet.'}
    lines = []
    if snapshot.recovery_rate_pct is not None:
        lines.append(f'Recovery rate: {snapshot.recovery_rate_pct}% as of {snapshot.date}.')
    if snapshot.equipment_availability_pct is not None:
        lines.append(f'Equipment availability: {snapshot.equipment_availability_pct}%.')
    if snapshot.dore_produced_kg is not None:
        lines.append(f'Doré produced: {snapshot.dore_produced_kg} kg.')
    return {'available': bool(lines), 'lines': lines, 'date': snapshot.date}


def _finance_section(project):
    capex_summary = None
    from gold_intelligence.services import aggregates as gold_aggregates
    capex_summary = gold_aggregates.capital_tracker_summary(project)
    deployed = None
    from capital_guardian.services import capital_trace
    deployed = capital_trace.capital_deployed(project)
    lines = []
    if capex_summary.get('available') and capex_summary.get('variance_usd') is not None:
        variance_pct = round(capex_summary['variance_usd'] / capex_summary['planned_usd'] * 100, 1) if capex_summary.get('planned_usd') else None
        if variance_pct is not None:
            lines.append(f'CAPEX variance: {"+" if variance_pct >= 0 else ""}{variance_pct}%.')
    if deployed is not None:
        lines.append(f'Capital deployed to date: ${deployed:,.0f}.')
    return {'available': bool(lines), 'lines': lines}


def _maintenance_section(project):
    recommendations = []
    for equipment in project.equipment_specs.all():
        rec = equipment_health.maintenance_recommendation(equipment)
        if rec['available'] and rec['urgency'] in ('due_soon', 'overdue'):
            recommendations.append(rec['message'])
    return {'available': bool(recommendations), 'lines': recommendations}


def _supply_chain_section(project):
    lines = []
    for equipment in project.equipment_specs.exclude(delivery_status='complete'):
        if equipment.delivery_status in ('not_started', 'in_progress'):
            lines.append(f'{equipment}: delivery status {equipment.get_delivery_status_display()}.')
    return {'available': bool(lines), 'lines': lines}


def _risk_section(project):
    flags = red_flag_engine.detect_red_flags(project)
    open_flags = [f for f in flags if f.resolution_status == 'open']
    lines = [f'{f.get_severity_display()}: {f.description}' for f in open_flags[:5]]
    return {'available': bool(lines), 'lines': lines, 'total_open': len(open_flags)}


def build_morning_briefing(project):
    """Every section is real, already-derived data — a section with nothing
    real to report says so honestly rather than inventing filler."""
    return {
        'project': project,
        'production': _production_section(project),
        'finance': _finance_section(project),
        'maintenance': _maintenance_section(project),
        'supply_chain': _supply_chain_section(project),
        'risk': _risk_section(project),
    }
