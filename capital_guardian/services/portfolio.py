"""
capital_guardian/services/portfolio.py — Phase 2: multi-project institutional
investor portfolio intelligence. Genuinely new (Phase 1 only ever showed one
GoldProject at a time) — but every number here is a plain aggregation over
per-project services that already exist (capital_trace, capital_protection,
red_flag_engine, investor_dashboard). No second scoring/orchestration system.

`project_status` is a deterministic classification (never an LLM judgement)
derived from real, already-computed signals: open red flag severities and
the real Capital Protection Score. A project with no real data at all is
honestly reported as 'unknown', never defaulted to 'On Track'.
"""
import pandas as pd

from capital_guardian.services import capital_protection, capital_trace, investor_dashboard, red_flag_engine

STATUS_ON_TRACK = 'on_track'
STATUS_MONITOR = 'monitor'
STATUS_AT_RISK = 'at_risk'
STATUS_UNKNOWN = 'unknown'

STATUS_LABELS = {
    STATUS_ON_TRACK: 'On Track', STATUS_MONITOR: 'Monitor', STATUS_AT_RISK: 'At Risk', STATUS_UNKNOWN: 'Unknown',
}


def project_status(protection_score, open_red_flags):
    """Deterministic, explainable status — never fabricated:
    - At Risk: any open HIGH severity red flag, or a real protection score below 40.
    - Monitor: any open red flag at all, or a real protection score 40-70.
    - On Track: a real protection score >= 70 and no open red flags.
    - Unknown: no real protection score AND no red flags to reason from.
    """
    high_open = any(f.severity == 'high' for f in open_red_flags)
    if high_open or (protection_score is not None and protection_score < 40):
        return STATUS_AT_RISK
    if open_red_flags or (protection_score is not None and protection_score < 70):
        return STATUS_MONITOR
    if protection_score is not None:
        return STATUS_ON_TRACK
    return STATUS_UNKNOWN


def project_summary(project):
    """One row of real, already-computed per-project figures — reuses every
    existing Capital Guardian service rather than recomputing anything."""
    deployed = capital_trace.capital_deployed(project)
    committed = project.total_committed_capital_usd
    protection = capital_protection.compute_capital_protection_score(project)
    open_flags = list(project.red_flags.filter(resolution_status='open'))
    entries = project.capital_trace_entries.all()
    evidence_with, evidence_total = capital_trace.evidence_coverage(entries)
    status = project_status(protection['score'] if protection['available'] else None, open_flags)

    insurance_ratio = None
    if project.insurance_coverage_usd is not None and deployed:
        insurance_ratio = min(100.0, project.insurance_coverage_usd / deployed * 100)

    return {
        'project': project,
        'committed_usd': committed,
        'deployed_usd': deployed,
        'remaining_usd': (round(committed - deployed, 2) if committed is not None and deployed is not None else None),
        'completion_pct': investor_dashboard.overall_completion_pct(project),
        'protection_score': protection['score'] if protection['available'] else None,
        'protection_available': protection['available'],
        'evidence_coverage': {'with_evidence': evidence_with, 'total': evidence_total},
        'insurance_coverage_usd': project.insurance_coverage_usd,
        'insurance_ratio_pct': insurance_ratio,
        'active_red_flags': len(open_flags),
        'high_red_flags': sum(1 for f in open_flags if f.severity == 'high'),
        'next_milestone': investor_dashboard.next_milestone(project),
        'status': status,
        'status_label': STATUS_LABELS[status],
    }


def build_portfolio(projects, refresh_red_flags=True):
    """Runs (optionally refreshing) red-flag detection and builds one
    summary row per project. `refresh_red_flags=False` is used by read-only
    call sites (e.g. tests asserting no writes) that only want to read
    already-detected flags."""
    rows = []
    for project in projects:
        if refresh_red_flags:
            red_flag_engine.detect_red_flags(project)
        rows.append(project_summary(project))
    return rows


def portfolio_totals(rows):
    """Real sums/counts over the rows already built by build_portfolio — a
    weighted Capital Protection Score (weighted by committed capital, the
    same pandas weighted-average technique capital_protection.py already
    uses) rather than a naive mean, since a $240M project's health matters
    more to the portfolio than a $10M one's."""
    if not rows:
        return {'available': False, 'reason': 'No projects recorded yet.'}

    committed_values = [r['committed_usd'] for r in rows if r['committed_usd'] is not None]
    deployed_values = [r['deployed_usd'] for r in rows if r['deployed_usd'] is not None]
    total_committed = sum(committed_values) if committed_values else None
    total_deployed = sum(deployed_values) if deployed_values else None
    total_remaining = (
        round(total_committed - total_deployed, 2) if total_committed is not None and total_deployed is not None else None
    )

    scored = [r for r in rows if r['protection_score'] is not None and r['committed_usd']]
    weighted_protection_score = None
    if scored:
        df = pd.DataFrame({
            'score': [r['protection_score'] for r in scored],
            'weight': [r['committed_usd'] for r in scored],
        })
        df['weight'] = df['weight'] / df['weight'].sum()
        weighted_protection_score = round(float((df['score'] * df['weight']).sum()), 1)

    insured = [r for r in rows if r['insurance_coverage_usd'] is not None]
    total_insurance = sum(r['insurance_coverage_usd'] for r in insured) if insured else None

    evidence_with = sum(r['evidence_coverage']['with_evidence'] for r in rows)
    evidence_total = sum(r['evidence_coverage']['total'] for r in rows)

    upcoming_payments = [
        r['next_milestone'].capital_required_usd for r in rows
        if r['next_milestone'] is not None and r['next_milestone'].capital_required_usd is not None
    ]

    return {
        'available': True,
        'project_count': len(rows),
        'total_committed_usd': total_committed,
        'total_deployed_usd': total_deployed,
        'total_remaining_usd': total_remaining,
        'weighted_protection_score': weighted_protection_score,
        'weighted_protection_score_basis': f'{len(scored)} of {len(rows)} project(s)',
        'on_track_count': sum(1 for r in rows if r['status'] == STATUS_ON_TRACK),
        'attention_count': sum(1 for r in rows if r['status'] in (STATUS_MONITOR, STATUS_AT_RISK)),
        'active_red_flags': sum(r['active_red_flags'] for r in rows),
        'total_insurance_usd': total_insurance,
        'evidence_coverage': {'with_evidence': evidence_with, 'total': evidence_total},
        'upcoming_milestone_payments_usd': round(sum(upcoming_payments), 2) if upcoming_payments else None,
    }


FILTER_KEYS = ('country', 'commodity', 'status')
SORT_KEYS = {
    'protection_score': lambda r: (r['protection_score'] is None, r['protection_score'] or 0),
    'completion_pct': lambda r: (r['completion_pct'] is None, r['completion_pct'] or 0),
    'deployed_usd': lambda r: (r['deployed_usd'] is None, r['deployed_usd'] or 0),
    'red_flag_count': lambda r: r['active_red_flags'],
    'name': lambda r: r['project'].name.lower(),
}


def filter_rows(rows, country=None, commodity=None, status=None):
    """Plain-Python filtering over already-built rows — computed fields
    (protection score, status) don't exist in the database to filter on."""
    filtered = rows
    if country:
        filtered = [r for r in filtered if r['project'].country_id and str(r['project'].country_id) == str(country)]
    if commodity:
        filtered = [r for r in filtered if r['project'].commodity == commodity]
    if status:
        filtered = [r for r in filtered if r['status'] == status]
    return filtered


def sort_rows(rows, sort_key, descending=True):
    key_fn = SORT_KEYS.get(sort_key)
    if key_fn is None:
        return rows
    return sorted(rows, key=key_fn, reverse=descending)
