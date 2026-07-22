"""
company_intelligence/services/coverage_matrix.py — feat/global-stewardship-
universe (PR 15): the transparent per-company coverage matrix (Section 5).

Every row uses the same five-value honest vocabulary — AVAILABLE, PARTIAL,
MISSING, STALE, NOT_APPLICABLE — and every row's `detail` is a real,
computed sentence, never a fabricated placeholder. This module does not
recompute health signals itself; it translates the SAME real numbers
services/stewardship_state.py::compute_company_health() already computes
into this row-based, publication-ready shape. Missing data is always shown
as MISSING, never silently coerced into a 0 or a false positive.
"""
from django.utils import timezone

AVAILABLE = 'AVAILABLE'
PARTIAL = 'PARTIAL'
MISSING = 'MISSING'
STALE = 'STALE'
NOT_APPLICABLE = 'NOT_APPLICABLE'

STALE_DOCUMENT_AGE_DAYS = 365


def _identity_row(company_profile):
    from company_intelligence.models import CompanyListing

    listing = CompanyListing.objects.filter(company=company_profile.company, is_primary=True).first()
    if listing is None or not listing.identity_source:
        return {'status': MISSING, 'detail': 'No regulatory identifier or verified official domain on file for this company.'}

    parts = []
    if listing.sec_cik:
        parts.append(f'SEC CIK {listing.sec_cik}')
    if listing.companies_house_number:
        parts.append(f'Companies House #{listing.companies_house_number}')
    if listing.official_domain:
        parts.append(f'official domain {listing.official_domain} ({listing.get_domain_status_display()})')
    status = AVAILABLE if (listing.sec_cik or listing.companies_house_number) else PARTIAL
    return {'status': status, 'detail': '; '.join(parts) or 'Identity partially known.'}


def _regulatory_row(company_profile):
    from harvester.models import Source

    reg_sources = Source.objects.filter(company=company_profile, source_type__in=('sec_edgar', 'companies_house'))
    if not reg_sources.exists():
        return {'status': MISSING, 'detail': 'No regulatory filing source registered.'}
    succeeded = reg_sources.filter(last_success_at__isnull=False)
    if not succeeded.exists():
        return {'status': PARTIAL, 'detail': 'Regulatory source registered but never successfully fetched yet.'}
    return {'status': AVAILABLE, 'detail': f'{succeeded.count()} regulatory source(s) successfully fetched.'}


def _financial_row(company_profile):
    facts = company_profile.financial_facts.order_by('-as_of_date', '-id').first()
    if facts is None:
        return {'status': MISSING, 'detail': 'No financial facts on file — Shariah financial-ratio screening cannot run.'}
    age_days = (timezone.now().date() - facts.as_of_date).days if facts.as_of_date else None
    if age_days is not None and age_days > STALE_DOCUMENT_AGE_DAYS:
        return {'status': STALE, 'detail': f'Financial facts are {age_days} days old (as of {facts.as_of_date}).'}
    return {'status': AVAILABLE, 'detail': f'Financial facts as of {facts.as_of_date}.'}


def _sustainability_document_row(health):
    missing = health['missing_document_categories']
    if health['official_sources_known'] == 0:
        return {'status': MISSING, 'detail': 'No sustainability/ESG/annual document sources known yet.'}
    if not missing:
        return {'status': AVAILABLE, 'detail': 'All expected document categories have at least one document on file.'}
    return {'status': PARTIAL, 'detail': f'Missing document categories: {", ".join(missing)}.'}


def _kpi_evidence_row(health):
    confirmed = health['confirmed_kpi_count']
    total = health['total_principles']
    if confirmed == 0:
        return {'status': MISSING, 'detail': f'0/{total} KPIs have confirmed evidence.'}
    if confirmed < total * 0.1:
        return {'status': PARTIAL, 'detail': f'{confirmed}/{total} KPIs have confirmed evidence.'}
    return {'status': AVAILABLE, 'detail': f'{confirmed}/{total} KPIs have confirmed evidence.'}


def _human_reviewed_row(health):
    pending = health['pending_review_count']
    confirmed = health['confirmed_kpi_count']
    if pending == 0 and confirmed == 0:
        return {'status': MISSING, 'detail': 'No evidence has been proposed or reviewed yet.'}
    if pending > 0 and confirmed == 0:
        return {'status': PARTIAL, 'detail': f'{pending} candidate(s) awaiting human review; none confirmed yet.'}
    if pending > 0:
        return {'status': PARTIAL, 'detail': f'{pending} candidate(s) still awaiting review alongside {confirmed} confirmed KPI(s).'}
    return {'status': AVAILABLE, 'detail': f'{confirmed} confirmed KPI(s); no items currently awaiting review.'}


def _shariah_row(company_profile):
    from company_intelligence.services import shariah_screening

    screen = shariah_screening.latest_screen_for(company_profile)
    if screen is None:
        return {'status': MISSING, 'detail': 'Not screened yet.'}
    from company_intelligence.services import freshness

    fresh = freshness.screening_freshness(screen)
    if fresh['is_stale']:
        return {'status': STALE, 'detail': fresh['reason']}
    return {'status': AVAILABLE, 'detail': f'Screened {screen.get_overall_result_display()} under {screen.methodology}.'}


def _monitoring_row(company_profile):
    if company_profile.tracking_status == 'not_tracked':
        return {'status': NOT_APPLICABLE, 'detail': 'Not part of the Stewardship Universe yet.'}
    if company_profile.tracking_status == 'paused':
        return {'status': PARTIAL, 'detail': 'Tracking is paused.'}
    open_alerts = company_profile.stewardship_alerts.exclude(state__in=('resolved', 'dismissed')).count()
    if open_alerts:
        return {'status': PARTIAL, 'detail': f'{open_alerts} open monitoring alert(s).'}
    if company_profile.last_refresh_at is None:
        return {'status': MISSING, 'detail': 'Tracked, but never successfully refreshed.'}
    return {'status': AVAILABLE, 'detail': f'Last refreshed {company_profile.last_refresh_at:%Y-%m-%d}, no open alerts.'}


def coverage_matrix_for_company(company_profile):
    """
    Returns an ordered dict of row-key -> {'status', 'detail'} covering
    Section 5's eight coverage dimensions. Never collapses missing data
    into zero — every row states in plain language what is and isn't
    known.
    """
    from company_intelligence.services import stewardship_state

    health = stewardship_state.compute_company_health(company_profile)

    return {
        'identity': _identity_row(company_profile),
        'regulatory_data': _regulatory_row(company_profile),
        'financial_data': _financial_row(company_profile),
        'sustainability_documents': _sustainability_document_row(health),
        'kpi_evidence': _kpi_evidence_row(health),
        'human_reviewed_evidence': _human_reviewed_row(health),
        'shariah_screening': _shariah_row(company_profile),
        'monitoring': _monitoring_row(company_profile),
    }


COVERAGE_ROW_LABELS = {
    'identity': 'Identity Coverage',
    'regulatory_data': 'Regulatory Data Coverage',
    'financial_data': 'Financial Data Coverage',
    'sustainability_documents': 'Sustainability-Document Coverage',
    'kpi_evidence': 'KPI Evidence Coverage',
    'human_reviewed_evidence': 'Human-Reviewed Evidence Coverage',
    'shariah_screening': 'Shariah Screening Coverage',
    'monitoring': 'Monitoring Status',
}
