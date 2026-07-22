"""
company_intelligence/services/alignment_metrics.py — feat/global-
stewardship-universe (PR 15): Section 7's transparent stewardship
alignment metrics. Every number here is a real, live count — reuses
kpi_engine.kpi_alignment_profile() (the ONE canonical per-company 114-row
profile) rather than re-querying CompanyKPIEvidenceLink from scratch.
Never invents a single "ESG score" — see services/discovery_engine.py for
the separately-documented, fully-componentised Evidence-Backed
Stewardship Alignment Indicator this module's metrics also feed.
"""
from company_intelligence.services import kpi_engine

SUPPORT_STATUSES = {'strong_support', 'support'}


def stewardship_alignment_metrics(company_profile):
    """
    Returns real counts only — every key here is documented in Section 7
    and directly inspectable back to CompanyKPIEvidenceLink rows via
    Explain Company.
    """
    from company_intelligence.models import CompanyKPIEvidenceLink
    from company_intelligence.services import change_detection

    profile_data = kpi_engine.kpi_alignment_profile(company_profile)
    counts = profile_data['counts']

    confirmed_supported = counts.get('strong_support', 0) + counts.get('support', 0)
    total_with_evidence = profile_data['assessed']

    links = CompanyKPIEvidenceLink.objects.filter(
        assessment__company=company_profile,
    ).select_related('assessment', 'evidence')

    confirmed_links = [l for l in links if l.review_state == 'confirmed']
    proposed_links = [l for l in links if l.review_state == 'proposed']
    disputed_links = [l for l in links if l.review_state == 'disputed']

    human_reviewed_kpi_ids = {l.assessment.kpi_id for l in confirmed_links}
    total_kpi_ids_with_any_link = {l.assessment.kpi_id for l in links}
    human_reviewed_coverage_pct = (
        round(100.0 * len(human_reviewed_kpi_ids) / len(total_kpi_ids_with_any_link), 1)
        if total_kpi_ids_with_any_link else None
    )

    stale_count = sum(1 for l in confirmed_links if change_detection.evidence_status_label(l) == 'STALE')

    categories_with_confirmed_evidence = {
        l.assessment.kpi_id for l in confirmed_links if l.relationship == 'supports'
    }
    from core.esg_principles_data import PRINCIPLES

    principles_by_id = {p['id']: p for p in PRINCIPLES}
    categories_represented = {
        principles_by_id[kpi_id]['category'] for kpi_id in categories_with_confirmed_evidence if kpi_id in principles_by_id
    }

    return {
        'confirmed_kpis_supported': confirmed_supported,
        'total_kpis_with_evidence': total_with_evidence,
        'total_kpis': profile_data['total'],
        'human_reviewed_kpi_count': len(human_reviewed_kpi_ids),
        'human_reviewed_coverage_pct': human_reviewed_coverage_pct,
        'proposed_pending_count': len(proposed_links),
        'disputed_kpi_count': len({l.assessment.kpi_id for l in disputed_links}),
        'confirmed_conflict_count': counts.get('conflict', 0) + counts.get('mixed', 0),
        'stale_evidence_count': stale_count,
        'evidence_breadth_category_count': len(categories_represented),
        'evidence_breadth_total_categories': 10,
    }
