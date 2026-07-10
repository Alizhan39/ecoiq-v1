"""
capital_guardian/services/capital_protection.py — the Capital Protection
Score, computed with the exact same explainable-weighted-average technique
already established platform-wide (pandas_scoring_engine._weighted_average,
agent_training_evaluation_lab.services.metrics.compute_overall_score): a
pandas DataFrame of {normalized, weight} per real component, weights
renormalized over only the components that actually have real data. Never
an LLM call, never a fabricated number — a component with no real data is
simply excluded, not defaulted to a guess.
"""
import pandas as pd

from capital_guardian.services import capital_trace

COMPONENT_WEIGHTS = {
    'budget_discipline': 0.25,
    'insurance_coverage': 0.20,
    'evidence_coverage': 0.20,
    'verification_rate': 0.20,
    'milestone_verification': 0.10,
    'red_flag_penalty': 0.05,
}

_RED_FLAG_PENALTY_WEIGHTS = {'high': 20, 'medium': 10, 'low': 5}


def _budget_discipline_component(project):
    lines = list(project.capital_budget_lines.exclude(planned_usd__isnull=True).exclude(committed_usd__isnull=True))
    if not lines:
        return None
    variances_pct = [
        abs(line.variance_usd) / line.planned_usd * 100
        for line in lines if line.planned_usd and line.variance_usd is not None
    ]
    if not variances_pct:
        return None
    mean_variance_pct = sum(variances_pct) / len(variances_pct)
    return {'normalized': max(0.0, 100.0 - mean_variance_pct), 'detail': f'Mean budget variance {mean_variance_pct:.1f}% across {len(variances_pct)} categor{"y" if len(variances_pct) == 1 else "ies"}.'}


def _insurance_coverage_component(project):
    deployed = capital_trace.capital_deployed(project)
    if project.insurance_coverage_usd is None or not deployed:
        return None
    ratio = min(100.0, project.insurance_coverage_usd / deployed * 100)
    return {'normalized': ratio, 'detail': f'Insurance covers {ratio:.0f}% of deployed capital.'}


def _evidence_coverage_component(project):
    entries = project.capital_trace_entries.all()
    with_evidence, total = capital_trace.evidence_coverage(entries)
    if total == 0:
        return None
    pct = round(100 * with_evidence / total, 1)
    return {'normalized': pct, 'detail': f'{with_evidence}/{total} capital movements have real evidence documents.'}


def _verification_rate_component(project):
    entries = project.capital_trace_entries.all()
    verified, total = capital_trace.verification_coverage(entries)
    if total == 0:
        return None
    pct = round(100 * verified / total, 1)
    return {'normalized': pct, 'detail': f'{verified}/{total} capital movements independently verified.'}


def _milestone_verification_component(project):
    milestones = project.timeline_milestones.filter(verification_required=True)
    total = milestones.count()
    if total == 0:
        return None
    verified = milestones.filter(verification_status='verified').count()
    pct = round(100 * verified / total, 1)
    return {'normalized': pct, 'detail': f'{verified}/{total} verification-required milestones verified.'}


def _red_flag_penalty_component(project):
    # "No open red flags" is only a meaningful signal once there's some real
    # underlying data that could genuinely have been flagged — a completely
    # bare project scoring 100/100 here would be a fabricated impression of
    # protection, not a real one.
    has_any_real_data = (
        project.capital_trace_entries.exists() or project.capital_budget_lines.exists()
        or project.timeline_milestones.exists() or project.equipment_specs.exists()
        or project.red_flags.exists()
    )
    if not has_any_real_data:
        return None
    open_flags = list(project.red_flags.filter(resolution_status='open'))
    if not open_flags:
        return {'normalized': 100.0, 'detail': 'No open red flags.'}
    penalty = sum(_RED_FLAG_PENALTY_WEIGHTS.get(f.severity, 5) for f in open_flags)
    return {'normalized': max(0.0, 100.0 - penalty), 'detail': f'{len(open_flags)} open red flag(s) reducing score.'}


def compute_capital_protection_score(project):
    """Returns {'available': bool, 'score': float|None, 'components': {...}}.
    None/available=False only when NOT ONE component has real data yet."""
    components = {
        'budget_discipline': _budget_discipline_component(project),
        'insurance_coverage': _insurance_coverage_component(project),
        'evidence_coverage': _evidence_coverage_component(project),
        'verification_rate': _verification_rate_component(project),
        'milestone_verification': _milestone_verification_component(project),
        'red_flag_penalty': _red_flag_penalty_component(project),
    }
    available = {name: c for name, c in components.items() if c is not None}
    if not available:
        return {'available': False, 'score': None, 'components': components, 'reason': 'No real capital-protection data recorded for this project yet.'}

    df = pd.DataFrame({
        'normalized': {n: c['normalized'] for n, c in available.items()},
        'weight': {n: COMPONENT_WEIGHTS[n] for n in available},
    })
    df['weight'] = df['weight'] / df['weight'].sum()
    score = round(float((df['normalized'] * df['weight']).sum()), 1)

    return {'available': True, 'score': score, 'components': components, 'components_available': f'{len(available)} of {len(components)}'}
