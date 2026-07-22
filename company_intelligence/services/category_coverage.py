"""
company_intelligence/services/category_coverage.py — feat/global-
stewardship-universe (PR 15), Section 9: per-category breakdown of a
company's 114-KPI alignment, grouped by the EXISTING canonical category
taxonomy (core.esg_principles_data.PRINCIPLE_CATEGORIES) — never a second,
competing taxonomy.
"""
from core.esg_principles_data import PRINCIPLE_CATEGORIES
from company_intelligence.services import kpi_engine

SUPPORT_STATUSES = {'strong_support', 'support'}


def category_coverage_for_company(company_profile):
    """
    Returns an ordered list of {'key', 'label', 'total_kpis',
    'supported_count', 'reviewed_evidence_count', 'missing_count',
    'disputed_count'} — one row per canonical category, in
    PRINCIPLE_CATEGORIES' own declared order.
    """
    profile_data = kpi_engine.kpi_alignment_profile(company_profile)
    rows_by_category = {}
    for row in profile_data['rows']:
        rows_by_category.setdefault(row['category'], []).append(row)

    from company_intelligence.models import CompanyKPIEvidenceLink

    disputed_kpi_ids = set(
        CompanyKPIEvidenceLink.objects.filter(
            assessment__company=company_profile, review_state='disputed',
        ).values_list('assessment__kpi_id', flat=True)
    )

    results = []
    for key, label in PRINCIPLE_CATEGORIES:
        category_rows = rows_by_category.get(key, [])
        supported = sum(1 for r in category_rows if r['status'] in SUPPORT_STATUSES)
        missing = sum(1 for r in category_rows if r['status'] == 'not_assessed')
        reviewed = sum(1 for r in category_rows if r['assessment'] is not None and r['status'] != 'not_assessed')
        disputed = sum(1 for r in category_rows if r['kpi_id'] in disputed_kpi_ids)
        results.append({
            'key': key, 'label': label, 'total_kpis': len(category_rows),
            'supported_count': supported, 'reviewed_evidence_count': reviewed,
            'missing_count': missing, 'disputed_count': disputed,
        })
    return results
