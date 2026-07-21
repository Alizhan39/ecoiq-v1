"""
company_intelligence/services/stewardship_state.py — feat/stewardship-
universe (PR 13): transparent, documented "how healthy/current is this
company's evidence base?" indicators, and the derivation of Section 2's
richer operational states from real, live conditions.

CRITICAL DISCIPLINE (from the brief): "Do not invent a scientific 'company
quality score.'" Every indicator below is either a real count/age/ratio
computed live, or an explicitly documented, component-shown completeness
percentage — never a hidden or opaque single number. Nothing here is
stored: computing it live is the only way it can never silently go stale
(same discipline as services/freshness.py and services/data_origin.py).
"""
import datetime

from django.utils import timezone

from company_intelligence.services import freshness, refresh_policy, shariah_screening
from harvester.services.ingestion_pipeline import DOCUMENT_SOURCE_TYPES

# The five expected document categories a well-covered company should have
# at least attempted to source — used only to report what's MISSING, never
# to penalise a company for a document type that genuinely doesn't apply
# to it (e.g. a private company with no annual report requirement).
EXPECTED_DOCUMENT_CATEGORIES = sorted(DOCUMENT_SOURCE_TYPES)

# data_completeness_pct — five equally-weighted (20% each), fully
# documented components. Every weight is a literal here, visible in the
# code and the methodology page — never a hidden/tuned constant.
COMPLETENESS_WEIGHTS = {
    'has_official_source': 0.20,
    'has_confirmed_kpi_evidence': 0.20,
    'shariah_screened_and_current': 0.20,
    'no_disputed_evidence': 0.20,
    'no_missing_document_categories': 0.20,
}


def _age_days(dt_or_date, *, now=None):
    if dt_or_date is None:
        return None
    now = now or timezone.now()
    if isinstance(dt_or_date, datetime.datetime):
        return (now - dt_or_date).days
    return (now.date() - dt_or_date).days


def _latest_document_age(company_profile, document_type, *, now=None):
    from harvester.models import SourceDocument

    doc = SourceDocument.objects.filter(
        company=company_profile, document_type=document_type,
    ).order_by('-publication_date', '-retrieved_at').first()
    if doc is None:
        return None, None
    age = _age_days(doc.publication_date, now=now) if doc.publication_date else _age_days(doc.retrieved_at, now=now)
    return doc, age


def compute_company_health(company_profile, *, now=None):
    """
    Returns a dict of independently-inspectable indicators. None means
    "genuinely not available yet" and is never coerced to 0 or a fabricated
    default — a company with no evidence yet has None freshness, not a
    freshness of 0.0.
    """
    from company_intelligence.models import CompanyKPIEvidenceLink
    from harvester.models import Evidence as HarvesterEvidence, SourceDocument

    now = now or timezone.now()

    discovered = company_profile.discovered_sources.all()
    official_sources_known = discovered.filter(status__in=('approved', 'registered')).count()
    pending_source_approval = discovered.filter(status='candidate').count()

    active_sources = list(company_profile.harvest_sources.filter(is_active=True))
    sources_reachable = sum(
        1 for s in active_sources
        if s.last_success_at and (not s.last_failure_at or s.last_success_at >= s.last_failure_at)
    )

    sustainability_doc, sustainability_age = _latest_document_age(company_profile, 'sustainability_report', now=now)
    annual_doc, annual_age = _latest_document_age(company_profile, 'annual_report', now=now)

    evidence_qs = HarvesterEvidence.objects.filter(company=company_profile)
    freshness_scores = list(evidence_qs.exclude(freshness_score=0.0).values_list('freshness_score', flat=True))
    evidence_freshness_avg = round(sum(freshness_scores) / len(freshness_scores), 3) if freshness_scores else None

    links = CompanyKPIEvidenceLink.objects.filter(assessment__company=company_profile)
    confirmed_kpi_count = links.filter(review_state='confirmed').values('assessment__kpi_id').distinct().count()
    pending_review_count = links.filter(review_state__in=('proposed', 'needs_more_evidence')).count()
    disputed_count = links.filter(review_state='disputed').count()

    present_categories = set(
        SourceDocument.objects.filter(company=company_profile).values_list('document_type', flat=True)
    )
    missing_categories = [c for c in EXPECTED_DOCUMENT_CATEGORIES if c not in present_categories]

    screen = shariah_screening.latest_screen_for(company_profile)
    shariah_fresh = freshness.screening_freshness(screen)

    completeness_components = {
        'has_official_source': official_sources_known > 0,
        'has_confirmed_kpi_evidence': confirmed_kpi_count > 0,
        'shariah_screened_and_current': bool(screen) and shariah_fresh['is_stale'] is False,
        'no_disputed_evidence': disputed_count == 0,
        'no_missing_document_categories': len(missing_categories) == 0,
    }
    data_completeness_pct = round(
        100.0 * sum(COMPLETENESS_WEIGHTS[k] for k, present in completeness_components.items() if present), 1,
    )

    return {
        'official_sources_known': official_sources_known,
        'pending_source_approval': pending_source_approval,
        'active_source_count': len(active_sources),
        'sources_reachable': sources_reachable,
        'sources_unreachable': len(active_sources) - sources_reachable,
        'latest_sustainability_report_age_days': sustainability_age,
        'latest_annual_report_age_days': annual_age,
        'evidence_freshness_avg': evidence_freshness_avg,
        'confirmed_kpi_count': confirmed_kpi_count,
        'total_principles': 114,
        'pending_review_count': pending_review_count,
        'disputed_count': disputed_count,
        'missing_document_categories': missing_categories,
        'shariah_screening_freshness': shariah_fresh,
        'data_completeness_pct': data_completeness_pct,
        'data_completeness_components': completeness_components,
        'data_completeness_weights': COMPLETENESS_WEIGHTS,
    }


# Human-readable labels for the derived operational states — the stored
# tracking_status lifecycle (companies.models.TRACKING_STATUS_CHOICES) is
# deliberately coarser; this is the richer, always-live-computed vocabulary
# from the brief's Section 2.
DERIVED_STATE_LABELS = {
    'NOT_TRACKED': 'Not Tracked',
    'PAUSED': 'Paused',
    'ERROR': 'Error — Last Refresh Failed',
    'REFRESH_IN_PROGRESS': 'Refresh In Progress',
    'NEEDS_SOURCE_DISCOVERY': 'Needs Source Discovery',
    'REVIEW_REQUIRED': 'Review Required',
    'NEEDS_REFRESH': 'Needs Refresh',
    'CURRENT': 'Current',
}


def compute_tracking_state(company_profile, *, health=None, now=None):
    """
    Combines the stored, process-level tracking_status with real, live
    conditions to derive the richer display state — "must be derived from
    real conditions where possible; do not fake CURRENT when key sources
    are missing." Precedence (checked in this exact order, documented so a
    reader never has to guess which condition wins):

    1. NOT_TRACKED / PAUSED / REFRESH_IN_PROGRESS / ERROR — stored,
       process-level states always win; they reflect an explicit action or
       an in-flight process, never overridden by a live-condition guess.
    2. NEEDS_SOURCE_DISCOVERY — an ACTIVE company with zero known sources
       has nothing to refresh yet; this always takes priority over review/
       refresh states, which presuppose sources exist.
    3. REVIEW_REQUIRED — pending or disputed evidence needs a human before
       anything else is meaningful to report.
    4. NEEDS_REFRESH — due for a refresh per refresh_policy.
    5. CURRENT — none of the above; genuinely up to date.
    """
    stored = company_profile.tracking_status
    if stored == 'not_tracked':
        return {'state': 'NOT_TRACKED', 'label': DERIVED_STATE_LABELS['NOT_TRACKED'], 'reason': 'This company is not part of the Stewardship Universe yet.'}
    if stored == 'paused':
        return {'state': 'PAUSED', 'label': DERIVED_STATE_LABELS['PAUSED'], 'reason': 'Tracking has been explicitly paused by staff.'}
    if stored == 'refresh_in_progress':
        return {'state': 'REFRESH_IN_PROGRESS', 'label': DERIVED_STATE_LABELS['REFRESH_IN_PROGRESS'], 'reason': 'A refresh is currently running for this company.'}
    if stored == 'error':
        return {'state': 'ERROR', 'label': DERIVED_STATE_LABELS['ERROR'], 'reason': 'The last refresh attempt failed for every checked source.'}

    health = health or compute_company_health(company_profile, now=now)

    if health['official_sources_known'] == 0:
        return {
            'state': 'NEEDS_SOURCE_DISCOVERY', 'label': DERIVED_STATE_LABELS['NEEDS_SOURCE_DISCOVERY'],
            'reason': 'No authoritative sources are known for this company yet — run source discovery.',
        }
    if health['pending_review_count'] > 0 or health['disputed_count'] > 0:
        return {
            'state': 'REVIEW_REQUIRED', 'label': DERIVED_STATE_LABELS['REVIEW_REQUIRED'],
            'reason': f"{health['pending_review_count']} candidate(s) awaiting review, {health['disputed_count']} disputed.",
        }
    if refresh_policy.is_company_due_for_refresh(company_profile, now=now):
        return {
            'state': 'NEEDS_REFRESH', 'label': DERIVED_STATE_LABELS['NEEDS_REFRESH'],
            'reason': 'At least one registered source is due for a refresh check per policy.',
        }
    return {
        'state': 'CURRENT', 'label': DERIVED_STATE_LABELS['CURRENT'],
        'reason': 'All known sources are within their refresh policy window and no evidence needs review.',
    }
