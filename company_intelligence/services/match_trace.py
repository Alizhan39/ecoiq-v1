"""
company_intelligence/services/match_trace.py — feat/company-discovery-
ranking (PR 11): "Why does Company X appear in these discovery results,
and why does it rank where it does?"

Reuses capital_guardian.services.decision_trace.TraceNode verbatim (same
convention as company_trace.py's "Explain Company" trace) and computes
NOTHING new — every value here comes straight from
company_intelligence.services.discovery_engine.rank_company_matches(),
called for this one company under the user's own selected criteria, so the
explanation is deterministic from already-stored data. No LLM anywhere in
this module; no unsupported investment narrative.

Distinct from company_trace.build_company_trace() (the generic, criteria-
free "Explain Company Assessment" page): this trace is always framed by
the SPECIFIC criteria a user selected on the Discover Companies page —
which KPIs, which Shariah statuses, which sector/country/tier filters —
and ends with the ranking components that actually produced this
company's position in THIS result set.
"""
from dataclasses import dataclass, field

from capital_guardian.services.decision_trace import NOT_AVAILABLE, TraceNode

from company_intelligence.services import discovery_engine
from core.esg_principles_data import PRINCIPLES

PRINCIPLES_BY_ID = {p['id']: p for p in PRINCIPLES}


@dataclass
class CompanyMatchTrace:
    company: object
    criteria: dict = field(default_factory=dict)
    nodes: list = field(default_factory=list)
    composite: float = None


def _criteria_summary(criteria):
    parts = []
    if criteria.get('kpi_ids'):
        titles = [PRINCIPLES_BY_ID[k]['title'] for k in criteria['kpi_ids'] if k in PRINCIPLES_BY_ID]
        parts.append(f"KPIs: {', '.join(titles)}")
    if criteria.get('shariah_status'):
        parts.append(f"Shariah status in: {', '.join(criteria['shariah_status'])}")
    if criteria.get('sector'):
        parts.append(f"Sector: {criteria['sector']}")
    if criteria.get('country'):
        parts.append(f"Country contains: {criteria['country']}")
    if criteria.get('min_source_tier') is not None:
        parts.append(f"Minimum source tier: {criteria['min_source_tier']}")
    if criteria.get('require_current_screening'):
        parts.append('Current (non-stale) Shariah screening required')
    if criteria.get('controversy_state', 'any') != 'any':
        parts.append(f"Controversy state: {criteria['controversy_state']}")
    return '; '.join(parts) if parts else 'No filters selected — showing all real, non-demo companies.'


def explain_company_match(company_profile, criteria=None):
    """
    Returns a CompanyMatchTrace with nodes:
    Selected Criteria -> Company Identity -> Shariah Screening ->
    Selected KPI(s) -> Supporting Evidence -> Conflicting Evidence ->
    Evidence Quality -> Freshness -> Data Gaps -> Ranking Components ->
    Why This Company Appears Here.
    """
    from django.urls import reverse

    def _url(name, *args):
        try:
            return reverse(name, args=args)
        except Exception:
            return None

    criteria = criteria or {}
    league_company = company_profile.company
    match = discovery_engine.compare_companies([company_profile], criteria=criteria)
    match = match[0] if match else discovery_engine.rank_company_matches([company_profile], criteria=criteria)[0]

    nodes = []

    # ---- 1. Selected Criteria -------------------------------------------
    nodes.append(TraceNode(
        stage='selected_criteria', title='Selected Criteria', status='Applied',
        status_kind='deterministic',
        summary=_criteria_summary(criteria),
        data_quality=['deterministic'],
        extra={'criteria': criteria},
    ))

    # ---- 2. Company Identity ----------------------------------------------
    nodes.append(TraceNode(
        stage='company_identity', title='Company Identity', status='Identified',
        status_kind='measured',
        summary=f'{league_company.name} — {league_company.get_sector_display()}, {league_company.country}. '
                f'Data origin: {match["data_origin"]["label"]}.',
        source_url=_url('companies:detail', league_company.slug),
        source_label='View Company Profile →',
        data_quality=['demo'] if match['data_origin']['origin'] == 'demo' else ['measured'],
        extra={'data_origin': match['data_origin']},
    ))

    # ---- 3. Shariah Screening -----------------------------------------------
    screen = match['shariah_screen']
    if screen is not None:
        stale_suffix = ' — Screening Requires Refresh' if match['freshness']['is_stale'] else ''
        nodes.append(TraceNode(
            stage='shariah_screening', title='Shariah Screening',
            status=screen.get_overall_result_display() + stale_suffix,
            status_kind=(
                'blocked' if screen.overall_result == 'fail' else
                'estimated' if match['freshness']['is_stale'] else
                'verified' if screen.overall_result == 'pass' else 'missing'
            ),
            summary=f'Screened according to {screen.methodology.name} v{screen.methodology.version}. '
                    f'Data completeness: {screen.data_completeness_pct}%. {match["freshness"]["reason"]}',
            timestamp=screen.screened_at,
            data_quality=['demo'] if screen.is_demo else ['deterministic'],
            extra={'freshness': match['freshness']},
        ))
    else:
        nodes.append(TraceNode(
            stage='shariah_screening', title='Shariah Screening', status='Not Screened',
            status_kind='missing', summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 4. Selected KPI(s) -------------------------------------------------
    kpi = match['kpi_detail']
    selected_titles = (
        [PRINCIPLES_BY_ID[k]['title'] for k in criteria.get('kpi_ids', []) if k in PRINCIPLES_BY_ID]
        if criteria.get('kpi_ids') else ['All 114 principles (no KPI filter selected)']
    )
    nodes.append(TraceNode(
        stage='selected_kpis', title='Selected KPI(s)', status=f"{kpi['selected_count']} principle(s) considered",
        status_kind='measured',
        summary=f"Considered: {', '.join(selected_titles[:8])}" + (' …' if len(selected_titles) > 8 else ''),
        data_quality=['measured'],
        extra={'selected_kpi_ids': criteria.get('kpi_ids') or []},
    ))

    # ---- 5. Supporting Evidence ----------------------------------------------
    supported = kpi['supported_kpi_ids']
    nodes.append(TraceNode(
        stage='supporting_evidence', title='Supporting Evidence', status=f'{len(supported)} KPI(s) supported',
        status_kind='verified' if supported else 'missing',
        summary=(
            f"Confirmed supporting evidence exists for: "
            f"{', '.join(PRINCIPLES_BY_ID[k]['title'] for k in supported[:6])}" + (' …' if len(supported) > 6 else '')
            if supported else 'No selected KPI currently has confirmed supporting evidence for this company.'
        ),
        source_url=(
            f"{_url('companies:detail', league_company.slug)}#ci-kpi-heading"
            if supported and _url('companies:detail', league_company.slug) else None
        ),
        source_label='Inspect underlying evidence →' if supported else '',
        data_quality=['deterministic'], available=bool(supported),
        extra={'supported_kpi_ids': supported},
    ))

    # ---- 6. Conflicting Evidence ---------------------------------------------
    conflicting = kpi['conflicting_kpi_ids']
    controversies = match['controversies']
    nodes.append(TraceNode(
        stage='conflicting_evidence', title='Conflicting Evidence',
        status=f'{len(conflicting)} KPI conflict(s), {len(controversies)} controversy record(s)',
        status_kind='disputed' if (conflicting or controversies) else 'measured',
        summary=(
            f"Conflicting evidence: {', '.join(PRINCIPLES_BY_ID[k]['title'] for k in conflicting)}. "
            if conflicting else 'No conflicting evidence for the selected KPI(s). '
        ) + f'{len(controversies)} controversy record(s) on file for this company — never suppressed by a '
            f'positive-looking ranking elsewhere.',
        data_quality=['deterministic'], available=bool(conflicting or controversies),
        extra={'conflicting_kpi_ids': conflicting, 'controversies': controversies},
    ))

    # ---- 7. Evidence Quality --------------------------------------------------
    eq = match['evidence_quality_detail']
    nodes.append(TraceNode(
        stage='evidence_quality', title='Evidence Quality',
        status=f"{eq['harvester_backed_count']} of {eq['evidence_count']} evidence row(s) source-verified",
        status_kind='measured' if eq['harvester_backed_count'] else 'missing',
        summary=(
            f"Source authority: {eq['source_authority']}. Recency: {eq['recency']}. "
            f"Corroboration: {eq['corroboration']}. Component metrics only — never one blended score."
        ),
        data_quality=['measured'], available=bool(eq['evidence_count']),
        extra=eq,
    ))

    # ---- 8. Freshness -----------------------------------------------------------
    fresh = match['freshness']
    nodes.append(TraceNode(
        stage='match_freshness', title='Freshness', status=fresh['label'],
        status_kind='estimated' if fresh['is_stale'] else ('measured' if fresh['is_stale'] is False else 'missing'),
        summary=fresh['reason'],
        data_quality=['deterministic'],
        extra=fresh,
    ))

    # ---- 9. Data Gaps -----------------------------------------------------------
    gap_notes = []
    if kpi['not_assessed_kpi_ids']:
        gap_notes.append(f"{len(kpi['not_assessed_kpi_ids'])} selected KPI(s) have no evidence linked yet.")
    if kpi['insufficient_kpi_ids']:
        gap_notes.append(f"{len(kpi['insufficient_kpi_ids'])} selected KPI(s) have evidence but not enough to conclude.")
    if screen is None:
        gap_notes.append('No Shariah screen has been run for this company.')
    nodes.append(TraceNode(
        stage='match_data_gaps', title='Data Gaps', status=f'{len(gap_notes)} gap(s) noted',
        status_kind='missing' if gap_notes else 'measured',
        summary='; '.join(gap_notes) if gap_notes else 'No material data gaps for this criteria selection.',
        data_quality=['missing'] if gap_notes else ['measured'],
        available=bool(gap_notes),
        extra={'not_assessed_kpi_ids': kpi['not_assessed_kpi_ids'], 'insufficient_kpi_ids': kpi['insufficient_kpi_ids']},
    ))

    # ---- 10. Ranking Components --------------------------------------------------
    components = match['components']
    component_lines = ', '.join(f'{k}={v}' for k, v in components.items())
    nodes.append(TraceNode(
        stage='ranking_components', title='Ranking Components',
        status=f"Composite: {match['composite']}" if match['composite'] is not None else 'No qualifying evidence',
        status_kind='deterministic',
        summary=f'Components ({component_lines}) combined with documented weights '
                f'({match["weights_used"]}) — every component shown, never hidden behind the composite. '
                f'Missing components are excluded from the average, never treated as zero.',
        data_quality=['deterministic'],
        extra={'components': components, 'weights': match['weights_used'], 'composite': match['composite']},
    ))

    # ---- 11. Why This Company Appears Here ---------------------------------------
    reasons = []
    if supported:
        reasons.append(f'{len(supported)} of the selected KPI(s) have confirmed supporting evidence')
    if screen is not None and criteria.get('shariah_status') and screen.overall_result in criteria['shariah_status']:
        reasons.append(f'its Shariah screen ({screen.get_overall_result_display()}) matches the selected filter')
    if not reasons:
        reasons.append('it matched the sector/country/tier filters selected, independent of KPI evidence')
    nodes.append(TraceNode(
        stage='why_here', title='Why This Company Appears Here',
        status='Deterministic — Not Investment Advice',
        status_kind='deterministic',
        summary=(
            '; '.join(reasons) + '. This is research and stewardship intelligence — it is not personalised '
            'investment advice and contains no buy/sell recommendation.'
        ),
        data_quality=['deterministic'],
        extra={'composite': match['composite']},
    ))

    return CompanyMatchTrace(company=company_profile, criteria=criteria, nodes=nodes, composite=match['composite'])
