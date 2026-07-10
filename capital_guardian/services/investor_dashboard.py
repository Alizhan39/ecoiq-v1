"""
capital_guardian/services/investor_dashboard.py — assembles the Investor
Dashboard's headline figures. Pure aggregation over real data already
computed elsewhere (gold_intelligence.services.project_finance/aggregates,
capital_guardian.services.capital_trace/capital_protection/red_flag_engine)
— no new computation invented here.

--- Phase 3 additions ---
Enterprise Value / Equity Value / Cash Position / Free Cash Flow / Today's
Gold Produced / Today's Revenue / Current Gold Price / Construction
Progress / Project Health Score are all real derivations over fields that
already exist (project_finance's NPV/IRR engine, ProjectGovernance's
investor_spv_pct, the latest OperationalSnapshot, GoldProject's own
gold_price_assumption_usd_per_oz) — never a new data source. Each is
labelled in the template with exactly what it represents (e.g. "price
assumption used for project economics", not "live market price") so
nothing is overclaimed.
"""
from gold_intelligence.services import aggregates as gold_aggregates

from capital_guardian.services import capital_protection, capital_trace, project_health, red_flag_engine

TROY_OUNCE_GRAMS = 31.1034768


def overall_completion_pct(project):
    """Real average over milestones that have a determinate completion —
    never an invented in-between percentage for milestones with no real
    reported progress."""
    values = [m.completion_pct for m in project.timeline_milestones.all() if m.completion_pct is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 1)


def construction_progress_pct(project):
    """The 'construction' phase milestone's own completion — falls back to
    overall_completion_pct() only if no construction milestone is recorded."""
    milestone = project.timeline_milestones.filter(phase='construction').first()
    if milestone is not None and milestone.completion_pct is not None:
        return milestone.completion_pct
    return overall_completion_pct(project)


def next_milestone(project):
    upcoming = (
        project.timeline_milestones.exclude(status='complete')
        .exclude(planned_end__isnull=True).order_by('planned_end').first()
    )
    return upcoming


def equity_value_usd(npv_usd, investor_spv_pct):
    """Investor's proportional real claim on modeled project NPV — labelled
    in the template as such, never presented as a live market valuation."""
    if npv_usd is None or investor_spv_pct is None:
        return None
    return round(npv_usd * investor_spv_pct / 100, 2)


def todays_gold_estimate(project):
    """(gold_oz, revenue_usd) from the latest OperationalSnapshot's real
    dore_produced_kg and the project's own declared gold price assumption —
    explicitly an ILLUSTRATIVE estimate (assumes 100% gold content; real
    doré assay/purity is not modeled), never a real settled revenue figure."""
    snapshot = project.operational_snapshots.order_by('-date').first()
    if snapshot is None or snapshot.dore_produced_kg is None or project.gold_price_assumption_usd_per_oz is None:
        return None, None
    gold_oz = round(snapshot.dore_produced_kg * 1000 / TROY_OUNCE_GRAMS, 2)
    revenue_usd = round(gold_oz * project.gold_price_assumption_usd_per_oz, 2)
    return gold_oz, revenue_usd


def build_dashboard_context(project):
    entries = project.capital_trace_entries.all()
    evidence_with, evidence_total = capital_trace.evidence_coverage(entries)
    verified, verification_total = capital_trace.verification_coverage(entries)
    economics = _project_economics(project)
    governance = getattr(project, 'governance', None)
    investor_spv_pct = governance.investor_spv_pct if governance else None
    npv_usd = economics.get('npv_usd') if economics.get('available') else None
    gold_oz_today, revenue_usd_today = todays_gold_estimate(project)

    return {
        'economics': economics,
        'capital_committed_usd': project.total_committed_capital_usd,
        'capital_deployed_usd': capital_trace.capital_deployed(project),
        'capex_summary': gold_aggregates.capital_tracker_summary(project),
        'completion_pct': overall_completion_pct(project),
        'construction_progress_pct': construction_progress_pct(project),
        'capital_protection': capital_protection.compute_capital_protection_score(project),
        'project_health': project_health.compute_project_health_score(project),
        'insurance_coverage_usd': project.insurance_coverage_usd,
        'next_milestone': next_milestone(project),
        'active_red_flags': list(red_flag_engine.detect_red_flags(project)),
        'evidence_coverage': {'with_evidence': evidence_with, 'total': evidence_total},
        'verification_coverage': {'verified': verified, 'total': verification_total},
        # Phase 3
        'investor_ownership_pct': investor_spv_pct,
        'enterprise_value_usd': npv_usd,
        'equity_value_usd': equity_value_usd(npv_usd, investor_spv_pct),
        'irr_forecast_pct': economics.get('irr_pct') if economics.get('available') else None,
        'annual_free_cash_flow_usd': economics.get('annual_net_cash_flow_usd') if economics.get('available') else None,
        'current_gold_price_usd_per_oz': project.gold_price_assumption_usd_per_oz,
        'todays_gold_produced_oz': gold_oz_today,
        'todays_revenue_usd': revenue_usd_today,
    }


def _project_economics(project):
    from gold_intelligence.services import project_finance
    return project_finance.compute_project_economics(project)
