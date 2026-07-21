"""
company_intelligence/services/company_trace.py — feat/company-halal-
intelligence (PR 9): "Why does EcoIQ classify this company this way?"

Reuses capital_guardian.services.decision_trace.TraceNode verbatim (that
dataclass is fully generic — no field is typed against a project or a
decision) rather than inventing a second trace-node shape. Does NOT reuse
build_decision_trace() itself or its DecisionTrace dataclass, since that
function is hard-coupled by convention to GoldProject/CapitalAllocationDecision
(direct attribute access, project-specific service imports) — this module
is the company-scoped parallel PR8's own audit predicted would be needed.

Like PR8's decision trace, this module computes nothing new: every value
is read from company_intelligence.services.shariah_screening,
company_intelligence.services.kpi_engine, and the real, already-persisted
CompanyShariahScreen/CompanyKPIAssessment/CompanyControversy rows. No LLM
call anywhere in this module.

feat/company-evidence-ingestion (PR 10): extended from PR9's 10 nodes to
12 — added 'sources' (right after company identity: real harvester.Source
registry entries + the real/demo data-origin classification) and
'evidence_review' (right after KPI evidence: pending ingestion-proposed
KPI links + the human review audit trail) — matching the brief's fuller
"Company Identity -> Sources -> Extracted Evidence -> Reviewed Evidence ->
... -> Final Research Profile" trace shape. The Shariah Result node now
also surfaces real freshness/staleness (services/freshness.py).

feat/global-stewardship-universe (PR 15): extended from 12 nodes to 13 —
added 'coverage_matrix' right before the final overall-profile node,
reusing services/coverage_matrix.py verbatim (Section 5's transparent
AVAILABLE/PARTIAL/MISSING/STALE/NOT_APPLICABLE per-dimension breakdown).
"""
from dataclasses import dataclass, field

from capital_guardian.services.decision_trace import NOT_AVAILABLE, TraceNode

from company_intelligence.services import kpi_engine, shariah_screening


@dataclass
class CompanyTrace:
    company: object
    generated_at: object = None
    summary: dict = field(default_factory=dict)
    nodes: list = field(default_factory=list)
    data_gaps: list = field(default_factory=list)


def build_company_trace(company_profile, user=None):
    from django.urls import reverse
    from django.utils import timezone

    from evidence_memory.services.retrieval_policy import is_company_record_accessible

    league_company = company_profile.company
    nodes = []
    data_gaps = []

    def _url(name, *args):
        try:
            return reverse(name, args=args)
        except Exception:
            return None

    # ---- 1. Company ---------------------------------------------------
    nodes.append(TraceNode(
        stage='company', title='Company', status='Identified',
        status_kind='measured',
        summary=f'{league_company.name} — {league_company.get_sector_display()}, {league_company.country}.',
        source_url=_url('companies:detail', league_company.slug),
        source_label='View Company Profile →',
        data_quality=['measured'],
        extra={
            'listings': list(league_company.listings.all()) if hasattr(league_company, 'listings') else [],
            'is_public': league_company.is_public,
            'verified': league_company.verified,
        },
    ))

    # ---- 2. Sources (feat/company-evidence-ingestion, PR 10) ---------------
    from company_intelligence.services.data_origin import company_data_origin

    origin = company_data_origin(company_profile)
    sources = list(company_profile.harvest_sources.all())
    if sources:
        nodes.append(TraceNode(
            stage='sources', title='Sources', status=f'{len(sources)} source(s) — {origin["label"]}',
            status_kind=('demo' if origin['origin'] == 'demo' else 'measured'),
            summary=(
                f'{origin["real_count"]} real record(s), {origin["demo_count"]} demo record(s) on file for '
                f'this company across Shariah screens, financial facts, KPI assessments and controversies.'
            ),
            data_quality=['demo'] if origin['origin'] == 'demo' else ['measured'],
            extra={'sources': sources, 'data_origin': origin},
        ))
    else:
        data_gaps.append('No source registry entries exist for this company yet — no real ingestion has run.')
        nodes.append(TraceNode(
            stage='sources', title='Sources', status=origin['label'],
            status_kind='missing' if origin['origin'] == 'unverified_import' else 'demo',
            summary='No harvester source registry entries recorded for this company.',
            data_quality=['missing'], available=False,
            extra={'data_origin': origin},
        ))

    screen = shariah_screening.latest_screen_for(company_profile)

    # ---- 3. Shariah methodology -----------------------------------------
    if screen is not None:
        methodology = screen.methodology
        nodes.append(TraceNode(
            stage='methodology', title='Shariah Methodology', status=f'{methodology.name} v{methodology.version}',
            status_kind='deterministic',
            summary=methodology.description,
            data_quality=['deterministic'],
            extra={'source_reference': methodology.source_reference, 'effective_date': methodology.effective_date},
        ))
    else:
        data_gaps.append('No Shariah screen has been run for this company yet.')
        nodes.append(TraceNode(
            stage='methodology', title='Shariah Methodology', status='Not Screened',
            status_kind='missing', summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 4. Business activity evidence ----------------------------------
    if screen is not None:
        nodes.append(TraceNode(
            stage='business_activity', title='Business Activity Evidence',
            status=screen.get_business_activity_result_display(),
            status_kind=('blocked' if screen.business_activity_result == 'fail' else 'deterministic'),
            summary=screen.business_activity_reason or NOT_AVAILABLE,
            data_quality=['deterministic'],
            extra={'evidence_refs': screen.business_activity_evidence_refs},
        ))
    else:
        nodes.append(TraceNode(
            stage='business_activity', title='Business Activity Evidence', status='Not Screened',
            status_kind='missing', summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 5. Financial evidence -------------------------------------------
    if screen is not None and screen.financial_facts is not None:
        ff = screen.financial_facts
        nodes.append(TraceNode(
            stage='financial_evidence', title='Financial Evidence', status=ff.source or 'Recorded',
            status_kind='measured',
            summary=f'Financial facts as of {ff.as_of_date}, source: {ff.source or NOT_AVAILABLE}.',
            timestamp=ff.retrieved_at,
            data_quality=['demo'] if ff.is_demo else ['measured'],
            extra={
                'market_cap_usd': ff.market_cap_usd, 'total_debt_usd': ff.total_debt_usd,
                'cash_and_equivalents_usd': ff.cash_and_equivalents_usd,
                'interest_bearing_securities_usd': ff.interest_bearing_securities_usd,
                'non_permissible_income_usd': ff.non_permissible_income_usd,
                'revenue_usd': ff.revenue_usd,
                'ratio_detail': screen.financial_ratio_detail,
            },
        ))
    else:
        data_gaps.append('No financial facts recorded — the financial-ratio screen could not run.')
        nodes.append(TraceNode(
            stage='financial_evidence', title='Financial Evidence', status='Not Available',
            status_kind='missing', summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 6. Shariah result -------------------------------------------------
    if screen is not None:
        from company_intelligence.services.freshness import screening_freshness

        fresh = screening_freshness(screen)
        stale_suffix = ' — Screening Requires Refresh' if fresh['is_stale'] else ''
        nodes.append(TraceNode(
            stage='shariah_result', title='Shariah Result', status=screen.get_overall_result_display() + stale_suffix,
            status_kind=(
                'blocked' if screen.overall_result == 'fail' else
                'estimated' if fresh['is_stale'] else
                'verified' if screen.overall_result == 'pass' else
                'missing' if screen.overall_result == 'insufficient_data' else 'estimated'
            ),
            summary=(
                f'Screened according to {screen.methodology.name} v{screen.methodology.version}. '
                f'Data completeness: {screen.data_completeness_pct}%. Review status: {screen.get_review_status_display()}. '
                f'{fresh["reason"]}'
            ),
            timestamp=screen.screened_at,
            confidence=screen.get_review_status_display(),
            data_quality=['demo'] if screen.is_demo else ['deterministic'],
            extra={
                'business': screen.business_activity_result, 'financial': screen.financial_ratio_result,
                'freshness': fresh,
            },
        ))
    else:
        nodes.append(TraceNode(
            stage='shariah_result', title='Shariah Result', status='Not Screened', status_kind='missing',
            summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 7. KPI evidence ---------------------------------------------------
    profile = kpi_engine.kpi_alignment_profile(company_profile)
    accessible_rows = []
    for row in profile['rows']:
        assessment = row['assessment']
        if assessment is None:
            accessible_rows.append(row)
            continue
        links = list(assessment.evidence_links.select_related('evidence').all())
        visible_links = [l for l in links if is_company_record_accessible(l.evidence, company_profile)]
        accessible_rows.append({**row, 'evidence_links': visible_links})

    total_links = sum(len(r.get('evidence_links', [])) for r in accessible_rows)
    nodes.append(TraceNode(
        stage='kpi_evidence', title='114-KPI Evidence', status=f"{profile['assessed']} of {profile['total']} assessed",
        status_kind='measured',
        summary=f"{total_links} evidence link(s) across {profile['assessed']} assessed KPI(s). "
                f"Coverage: {profile['coverage_pct']}% of the 114-KPI framework.",
        data_quality=['measured'],
        extra={'counts': profile['counts']},
    ))

    # ---- 8. Evidence Review (feat/company-evidence-ingestion, PR 10) -------
    from company_intelligence.models import EvidenceReviewAction

    pending_review_total = profile.get('pending_review_total', 0)
    review_actions = list(
        EvidenceReviewAction.objects
        .filter(kpi_evidence_link__assessment__company=company_profile)
        .select_related('reviewer', 'kpi_evidence_link')[:20]
    )
    nodes.append(TraceNode(
        stage='evidence_review', title='Evidence Review',
        status=f'{pending_review_total} proposed link(s) awaiting review',
        status_kind='estimated' if pending_review_total else 'measured',
        summary=(
            f'{len(review_actions)} review action(s) recorded. Proposed (ingestion-matched) KPI links never '
            f'move a company\'s KPI status until a human reviewer confirms them.'
        ),
        data_quality=['human_approved'] if review_actions else ['deterministic'],
        extra={'review_actions': review_actions, 'pending_review_total': pending_review_total},
        available=bool(review_actions or pending_review_total),
    ))

    # ---- 9. Positive alignment ----------------------------------------------
    positive_rows = [r for r in accessible_rows if r['status'] in ('strong_support', 'support')]
    nodes.append(TraceNode(
        stage='positive_alignment', title='Positive Alignment', status=f'{len(positive_rows)} KPI(s)',
        status_kind='verified' if positive_rows else 'missing',
        summary=(f'{len(positive_rows)} of 114 KPIs have supporting evidence.' if positive_rows
                 else 'No KPIs currently have supporting evidence.'),
        data_quality=['deterministic'],
        extra={'rows': positive_rows}, available=bool(positive_rows),
    ))

    # ---- 10. Conflicting evidence -------------------------------------------
    conflict_rows = [r for r in accessible_rows if r['status'] == 'conflict']
    controversies = list(company_profile.controversies.select_related('evidence').all())
    nodes.append(TraceNode(
        stage='conflicting_evidence', title='Conflicting Evidence',
        status=f'{len(conflict_rows)} KPI conflict(s), {len(controversies)} controversy record(s)',
        status_kind='disputed' if (conflict_rows or controversies) else 'measured',
        summary=(
            f'{len(conflict_rows)} KPI(s) have conflicting evidence; {len(controversies)} controversy '
            f'record(s) are on file for this company. Positive-appearing status elsewhere never suppresses '
            f'these.'
        ),
        data_quality=['deterministic'],
        extra={'kpi_rows': conflict_rows, 'controversies': controversies},
        available=bool(conflict_rows or controversies),
    ))

    # ---- 11. Evidence gaps ---------------------------------------------------
    insufficient_rows = [r for r in accessible_rows if r['status'] == 'insufficient_evidence']
    not_assessed_count = profile['counts'].get('not_assessed', 0)
    gap_notes = list(data_gaps)
    if insufficient_rows:
        gap_notes.append(f'{len(insufficient_rows)} KPI(s) have evidence linked but not enough to reach a conclusion.')
    if not_assessed_count:
        gap_notes.append(f'{not_assessed_count} of 114 KPIs have no evidence linked yet.')
    nodes.append(TraceNode(
        stage='evidence_gaps', title='Evidence Gaps', status=f'{len(gap_notes)} gap(s) noted',
        status_kind='missing' if gap_notes else 'measured',
        summary='; '.join(gap_notes) if gap_notes else 'No material evidence gaps currently recorded.',
        data_quality=['missing'] if gap_notes else ['measured'],
        extra={'insufficient_rows': insufficient_rows, 'not_assessed_count': not_assessed_count},
        available=bool(gap_notes),
    ))

    # ---- 12. Coverage Matrix (feat/global-stewardship-universe, PR 15) -------
    # Section 5's transparent per-dimension coverage — reuses
    # coverage_matrix.py verbatim (which itself reuses stewardship_state's
    # compute_company_health(), never a second health computation). Missing
    # data is always shown as MISSING, never silently coerced into a 0 or a
    # false positive.
    from company_intelligence.services.coverage_matrix import COVERAGE_ROW_LABELS, coverage_matrix_for_company

    matrix = coverage_matrix_for_company(company_profile)
    missing_or_stale = [k for k, v in matrix.items() if v['status'] in ('MISSING', 'STALE')]
    # Django templates cannot look up a dict value by a loop variable key
    # (no `{{ dict|attr:key }}` filter) — resolved here in Python, same
    # discipline as PR10's CompanyFinancialFactSource.value property.
    matrix_rows = [{'key': k, 'label': COVERAGE_ROW_LABELS[k], **v} for k, v in matrix.items()]
    nodes.append(TraceNode(
        stage='coverage_matrix', title='Coverage Matrix',
        status=f'{len(matrix) - len(missing_or_stale)} of {len(matrix)} dimensions available',
        status_kind='missing' if missing_or_stale else 'measured',
        summary=(
            f'{len(missing_or_stale)} coverage dimension(s) currently MISSING or STALE: '
            f'{", ".join(COVERAGE_ROW_LABELS[k] for k in missing_or_stale)}.' if missing_or_stale
            else 'All coverage dimensions are AVAILABLE or NOT_APPLICABLE — no missing or stale data currently.'
        ),
        data_quality=['deterministic'],
        extra={'matrix': matrix, 'matrix_rows': matrix_rows},
    ))

    # ---- 13. Overall research profile ---------------------------------------
    shariah_label = screen.get_overall_result_display() if screen is not None else 'Not Screened'
    nodes.append(TraceNode(
        stage='overall_profile', title='Overall Research Profile', status='Research Intelligence — Not Investment Advice',
        status_kind='deterministic',
        summary=(
            f'Data origin: {origin["label"]}. Shariah: {shariah_label} (methodology-based screening, not a '
            f'religious ruling). 114-KPI coverage: {profile["coverage_pct"]}% assessed, {len(positive_rows)} '
            f'supported, {len(conflict_rows)} in conflict. This is research and stewardship intelligence — it '
            f'is not personalised investment advice and contains no buy/sell recommendation.'
        ),
        data_quality=['deterministic'],
        extra={'shariah_result': screen.overall_result if screen else None, 'kpi_profile': profile, 'data_origin': origin},
    ))

    summary = {
        'company_name': league_company.name,
        'data_origin': origin,
        'shariah_result': shariah_label,
        'kpi_coverage_pct': profile['coverage_pct'],
        'kpi_supported': len(positive_rows),
        'kpi_conflicts': len(conflict_rows),
        'controversy_count': len(controversies),
        'data_gaps': gap_notes or ['No material evidence gaps currently recorded.'],
    }

    return CompanyTrace(
        company=company_profile, generated_at=timezone.now(), summary=summary, nodes=nodes, data_gaps=gap_notes,
    )
