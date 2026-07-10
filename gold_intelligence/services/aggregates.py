"""
gold_intelligence/services/aggregates.py — real, stored-data aggregation for
the Capital Tracker and Equipment Intelligence sections. No computation
here invents a figure: every total is a plain sum over real
CapitalBudgetLine/EquipmentSpec rows, honestly reporting `available: False`
when a project has none recorded yet.
"""


def _sum_attr(rows, attr):
    values = [getattr(r, attr) for r in rows if getattr(r, attr) is not None]
    return round(sum(values), 2) if values else None


def capital_tracker_summary(project):
    lines = list(project.capital_budget_lines.all())
    if not lines:
        return {'available': False, 'reason': 'No capital budget lines recorded for this project yet.', 'lines': []}
    planned = _sum_attr(lines, 'planned_usd')
    committed = _sum_attr(lines, 'committed_usd')
    spent = _sum_attr(lines, 'spent_usd')
    remaining = round(planned - spent, 2) if planned is not None and spent is not None else None
    variance = round(committed - planned, 2) if committed is not None and planned is not None else None
    return {
        'available': True, 'planned_usd': planned, 'committed_usd': committed, 'spent_usd': spent,
        'remaining_usd': remaining, 'variance_usd': variance, 'line_count': len(lines), 'lines': lines,
    }


def equipment_summary(project):
    specs = list(project.equipment_specs.all())
    if not specs:
        return {'available': False, 'reason': 'No equipment specs recorded for this project yet.', 'specs': []}
    return {
        'available': True, 'equipment_count': len(specs),
        'total_capex_usd': _sum_attr(specs, 'capex_usd'),
        'total_power_usage_kw': _sum_attr(specs, 'power_usage_kw'),
        'total_water_usage_m3_per_hour': _sum_attr(specs, 'water_usage_m3_per_hour'),
        'specs': specs,
    }


def timeline_summary(project):
    milestones = list(project.timeline_milestones.all())
    return {'available': bool(milestones), 'milestones': milestones}
