"""
company_intelligence/services/source_registry.py — feat/stewardship-
universe (PR 13): turns an approved DiscoveredSource candidate into a real,
fetchable harvester.Source row (Section 7's "Source Registry"), and builds
the display rows the Stewardship Universe/company-status pages need —
Source / Type / Tier / Publisher / First discovered / Last checked / Last
successful fetch / Latest document version / Status / Evidence produced /
KPI candidates produced, joined from the real underlying tables, never a
second copy of any of it.
"""
from django.utils import timezone

from company_intelligence.services.url_safety import is_safe_external_url


def register_discovered_source(discovered, actor=None):
    """
    Creates (or reuses) the real harvester.Source row for one APPROVED
    DiscoveredSource candidate, gated by the SSRF guard (a PROBABLE/
    staff-entered URL is exactly the case this guard exists for — an
    auto-approved SEC EDGAR/Companies House/curated-domain URL will always
    pass it too, since those are real, known-public government/company
    domains). Never registers a 'candidate' or 'rejected' row — only
    'approved' (including rows auto-approved at discovery time).

    Idempotent: re-registering an already-'registered' candidate is a
    no-op that returns the existing harvester_source, never a duplicate.
    """
    from harvester.models import Source

    if discovered.status == 'registered' and discovered.harvester_source_id:
        return discovered.harvester_source, False

    if discovered.status != 'approved':
        raise ValueError(f'Cannot register a DiscoveredSource with status "{discovered.status}" — approve it first.')

    is_safe, reason = is_safe_external_url(discovered.url)
    if not is_safe:
        discovered.status = 'rejected'
        discovered.review_notes = f'Registration blocked by URL safety check: {reason}'
        discovered.reviewed_at = timezone.now()
        discovered.save(update_fields=['status', 'review_notes', 'reviewed_at'])
        raise ValueError(f'Refusing to register unsafe URL: {reason}')

    confidence_base = discovered.confidence if discovered.confidence is not None else {
        1: 0.9, 2: 0.75, 3: 0.6, 4: 0.5,
    }.get(discovered.tier, 0.5)

    from harvester.constants import SOURCE_TYPES

    source_type_label = dict(SOURCE_TYPES).get(discovered.source_type, discovered.source_type or 'Source')
    source, created = Source.objects.get_or_create(
        company=discovered.company, source_type=discovered.source_type, source_url=discovered.url,
        defaults={
            'name': f'{source_type_label} — {discovered.domain or discovered.url}',
            'source_owner': discovered.publisher, 'confidence_base': confidence_base,
        },
    )
    discovered.harvester_source = source
    discovered.status = 'registered'
    discovered.save(update_fields=['harvester_source', 'status'])
    return source, created


def approve_discovered_source(discovered, actor, notes='', auto_register=True):
    """Staff approval of a candidate (typically one discovered via a
    staff-entered field, since the three deterministic discovery methods
    are already auto-approved at discovery time). Immediately registers it
    as a real harvester.Source unless auto_register=False, matching the
    pipeline's own discover -> register -> fetch ordering."""
    discovered.status = 'approved'
    discovered.reviewed_by = actor
    discovered.reviewed_at = timezone.now()
    discovered.review_notes = notes
    discovered.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes'])
    if auto_register:
        register_discovered_source(discovered, actor=actor)
    return discovered


def reject_discovered_source(discovered, actor, reason=''):
    """Never deletes the row — historical provenance of what was found and
    why it was rejected is preserved, matching Section 7's "do not delete
    historical provenance" instruction."""
    discovered.status = 'rejected'
    discovered.reviewed_by = actor
    discovered.reviewed_at = timezone.now()
    discovered.review_notes = reason
    discovered.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes'])
    return discovered


def source_registry_rows(company_profile):
    """
    One real, joined row per DiscoveredSource for this company — never a
    duplicate structure of the underlying models, just a read-time join.
    """
    from evidence_memory.models import EvidenceMemory
    from harvester.models import Evidence as HarvesterEvidence
    from harvester.models import SourceDocument
    from company_intelligence.models import CompanyKPIEvidenceLink

    rows = []
    for discovered in company_profile.discovered_sources.all():
        source = discovered.harvester_source
        documents = SourceDocument.objects.filter(source=source).order_by('-retrieved_at') if source else SourceDocument.objects.none()
        latest_document = documents.first()
        evidence_qs = HarvesterEvidence.objects.filter(source=source) if source else HarvesterEvidence.objects.none()
        evidence_count = evidence_qs.count()

        kpi_candidates_count = 0
        if evidence_count:
            memory_refs = [f'harvester.Evidence:{pk}' for pk in evidence_qs.values_list('pk', flat=True)]
            memory_ids = list(EvidenceMemory.objects.filter(
                source_type='harvester_evidence', source_reference__in=memory_refs,
            ).values_list('pk', flat=True))
            kpi_candidates_count = CompanyKPIEvidenceLink.objects.filter(evidence_id__in=memory_ids).count()

        rows.append({
            'discovered': discovered,
            'source': source,
            'documents_count': documents.count(),
            'latest_document': latest_document,
            'evidence_count': evidence_count,
            'kpi_candidates_count': kpi_candidates_count,
            'last_success_at': source.last_success_at if source else None,
            'last_failure_at': source.last_failure_at if source else None,
            'last_failure_reason': source.last_failure_reason if source else '',
            'is_reachable': bool(source and source.last_success_at and (
                not source.last_failure_at or source.last_success_at >= source.last_failure_at
            )),
        })
    return rows
