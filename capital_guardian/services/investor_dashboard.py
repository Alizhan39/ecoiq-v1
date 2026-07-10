"""
capital_guardian/services/investor_dashboard.py — assembles the Investor
Dashboard's headline figures. Pure aggregation over real data already
computed elsewhere (gold_intelligence.services.project_finance/aggregates,
capital_guardian.services.capital_trace/capital_protection/red_flag_engine)
— no new computation invented here.
"""
from gold_intelligence.services import aggregates as gold_aggregates

from capital_guardian.services import capital_protection, capital_trace, red_flag_engine


def overall_completion_pct(project):
    """Real average over milestones that have a determinate completion —
    never an invented in-between percentage for milestones with no real
    reported progress."""
    values = [m.completion_pct for m in project.timeline_milestones.all() if m.completion_pct is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 1)


def next_milestone(project):
    upcoming = (
        project.timeline_milestones.exclude(status='complete')
        .exclude(planned_end__isnull=True).order_by('planned_end').first()
    )
    return upcoming


def build_dashboard_context(project):
    entries = project.capital_trace_entries.all()
    evidence_with, evidence_total = capital_trace.evidence_coverage(entries)
    verified, verification_total = capital_trace.verification_coverage(entries)

    return {
        'economics': _project_economics(project),
        'capital_committed_usd': project.total_committed_capital_usd,
        'capital_deployed_usd': capital_trace.capital_deployed(project),
        'capex_summary': gold_aggregates.capital_tracker_summary(project),
        'completion_pct': overall_completion_pct(project),
        'capital_protection': capital_protection.compute_capital_protection_score(project),
        'insurance_coverage_usd': project.insurance_coverage_usd,
        'next_milestone': next_milestone(project),
        'active_red_flags': list(red_flag_engine.detect_red_flags(project)),
        'evidence_coverage': {'with_evidence': evidence_with, 'total': evidence_total},
        'verification_coverage': {'verified': verified, 'total': verification_total},
    }


def _project_economics(project):
    from gold_intelligence.services import project_finance
    return project_finance.compute_project_economics(project)
