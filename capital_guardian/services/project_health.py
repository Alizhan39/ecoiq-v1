"""
capital_guardian/services/project_health.py — Phase 3: the Project Health
Score, a real, differently-focused composite from the existing Capital
Protection Score. Capital Protection measures capital/evidence/governance
discipline; Project Health measures OPERATIONAL performance (equipment
availability, recovery vs. target, environmental status, construction
progress, equipment lifecycle risk) — reusing the exact same explainable
pandas weighted-average technique as capital_protection.py, never a second
scoring philosophy.
"""
import pandas as pd

from capital_guardian.services import equipment_health, investor_dashboard, red_flag_engine

COMPONENT_WEIGHTS = {
    'equipment_availability': 0.25,
    'recovery_vs_target': 0.20,
    'environmental_status': 0.20,
    'construction_progress': 0.20,
    'equipment_lifecycle': 0.15,
}
_ENVIRONMENTAL_SCORES = {'green': 100.0, 'amber': 60.0, 'red': 20.0}


def _latest_snapshot(project):
    return project.operational_snapshots.order_by('-date').first()


def _equipment_availability_component(project):
    snapshot = _latest_snapshot(project)
    if snapshot is None or snapshot.equipment_availability_pct is None:
        return None
    return {'normalized': min(100.0, snapshot.equipment_availability_pct), 'detail': f'Latest equipment availability: {snapshot.equipment_availability_pct}%.'}


def _recovery_vs_target_component(project):
    if project.recovery_rate_pct is None:
        return None
    snapshot = _latest_snapshot(project)
    if snapshot is None or snapshot.recovery_rate_pct is None:
        return None
    ratio = min(100.0, (snapshot.recovery_rate_pct / project.recovery_rate_pct) * 100)
    return {'normalized': ratio, 'detail': f'Recovery {snapshot.recovery_rate_pct}% vs. target {project.recovery_rate_pct}%.'}


def _environmental_status_component(project):
    snapshot = _latest_snapshot(project)
    if snapshot is None or not snapshot.environmental_status:
        return None
    score = _ENVIRONMENTAL_SCORES.get(snapshot.environmental_status)
    return {'normalized': score, 'detail': f'Environmental status: {snapshot.get_environmental_status_display()}.'}


def _construction_progress_component(project):
    pct = investor_dashboard.overall_completion_pct(project)
    if pct is None:
        return None
    return {'normalized': pct, 'detail': f'Overall milestone completion: {pct}%.'}


def _equipment_lifecycle_component(project):
    equipment = list(project.equipment_specs.all())
    if not equipment:
        return None
    assessed = [equipment_health.remaining_useful_life(e) for e in equipment]
    assessed = [years for years, _end in assessed if years is not None]
    if not assessed:
        return None
    overdue_or_due_soon = sum(1 for years in assessed if years <= equipment_health.SERVICE_WINDOW_WARNING_YEARS_REMAINING)
    pct_healthy = round(100 * (1 - overdue_or_due_soon / len(assessed)), 1)
    return {'normalized': pct_healthy, 'detail': f'{len(assessed) - overdue_or_due_soon}/{len(assessed)} equipment items outside their service-due window.'}


def compute_project_health_score(project):
    components = {
        'equipment_availability': _equipment_availability_component(project),
        'recovery_vs_target': _recovery_vs_target_component(project),
        'environmental_status': _environmental_status_component(project),
        'construction_progress': _construction_progress_component(project),
        'equipment_lifecycle': _equipment_lifecycle_component(project),
    }
    available = {name: c for name, c in components.items() if c is not None}
    if not available:
        return {'available': False, 'score': None, 'components': components, 'reason': 'No real operational data recorded for this project yet.'}

    df = pd.DataFrame({
        'normalized': {n: c['normalized'] for n, c in available.items()},
        'weight': {n: COMPONENT_WEIGHTS[n] for n in available},
    })
    df['weight'] = df['weight'] / df['weight'].sum()
    score = round(float((df['normalized'] * df['weight']).sum()), 1)
    return {'available': True, 'score': score, 'components': components, 'components_available': f'{len(available)} of {len(components)}'}
