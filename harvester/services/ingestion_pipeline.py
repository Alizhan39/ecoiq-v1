"""
harvester/services/ingestion_pipeline.py — SOURCE -> FETCH -> VALIDATE ->
NORMALISE -> DEDUPLICATE -> ATTRIBUTE -> CONFIDENCE -> STORE -> MEMORY, for
one harvester.Source row at a time.

This is additive alongside harvester/pipeline.py::run_harvest(), not a
replacement — run_harvest() is the existing OFFLINE, company-centric harvest
(adapters.py's DocumentAdapter/ProfileDerivedAdapter, no network). This
module is the NEW, Source-registry-driven, real-network path the Data
Ingestion Engine needs, reusing the SAME dedup/verification engine
(harvester.dedup.deduplicate) so a canonical Evidence row created here is
identical in shape to one created by the offline path — no parallel
Evidence architecture, no parallel dedup logic.
"""
from django.utils import timezone

from harvester.dedup import deduplicate
from harvester.models import Evidence, IngestionRun, SourceDocument
from harvester.services import fetchers
from harvester.verification import source_tier

# feat/company-discovery-ranking (PR 11) — the 5 multi-chunk "document"
# source types, all routed through the ONE new fetch_sustainability_document
# fetcher (never a separate fetcher per document type — the parsing logic
# is identical, only the label differs).
DOCUMENT_SOURCE_TYPES = {
    'annual_report', 'sustainability_report', 'esg_report', 'tcfd_report', 'transition_plan',
}


def _company_slug_for_source(source):
    if not source.company_id or not source.company.company_id:
        return None
    return source.company.company.slug


def ingest_source(source, triggered_by='manual'):
    """
    Fetches, validates, deduplicates and stores evidence for ONE Source row,
    then creates/updates EvidenceMemory for any newly-created canonical
    Evidence. Returns the IngestionRun record — always created, even for a
    SKIPPED/FAILED outcome, so nothing about this attempt is invisible.
    """
    run = IngestionRun.objects.create(source=source, triggered_by=triggered_by, started_at=timezone.now())

    if not source.is_active:
        run.mark_completed('skipped')
        return run

    company_slug = _company_slug_for_source(source)

    if source.source_type == 'companies_house':
        if not company_slug:
            run.mark_completed('skipped')
            return run
        outcome = fetchers.fetch_companies_house(company_slug)
        category_for_count = 'governance'
    elif source.source_type == 'sec_edgar':
        if not company_slug:
            run.mark_completed('skipped')
            return run
        outcome = fetchers.fetch_sec_edgar(company_slug)
        category_for_count = 'financial'
    elif source.source_type in DOCUMENT_SOURCE_TYPES:
        if not source.source_url or not company_slug:
            run.mark_completed('skipped')
            return run
        outcome = fetchers.fetch_sustainability_document(
            source.source_url, company_slug, source.source_type, publisher=source.source_owner,
        )
        category_for_count = None  # a document's chunks can span multiple evidence categories
    elif source.source_type == 'csv_dataset':
        if not source.source_url or not company_slug:
            run.mark_completed('skipped')
            return run
        outcome = fetchers.fetch_csv_dataset(source.source_url, company_slug)
        category_for_count = None  # CSV rows can span multiple categories
    else:
        if not source.source_url or not company_slug:
            run.mark_completed('skipped')
            return run
        outcome = fetchers.fetch_url_recheck(source.source_url, company_slug)
        category_for_count = None

    if not outcome.success:
        if outcome.skipped_reason:
            run.mark_completed('skipped')
            return run
        source.last_failure_at = timezone.now()
        source.last_failure_reason = outcome.error
        source.save(update_fields=['last_failure_at', 'last_failure_reason'])
        run.mark_failed(outcome.error)
        return run

    # Snapshot evidence-before so NEW vs UPDATED can be told apart honestly.
    existing_query = Evidence.objects.filter(company_slug=company_slug)
    if category_for_count:
        existing_query = existing_query.filter(category=category_for_count)
    had_prior_evidence = existing_query.exists()

    profile = source.company

    # feat/company-discovery-ranking (PR 11) — a document-shaped fetch
    # (fetch_sustainability_document) reports whole-document provenance in
    # outcome.metadata['document']; get_or_create on
    # (company_slug, url, content_hash) makes re-ingesting an UNCHANGED
    # document a genuine no-op (same row reused, no duplicate), while a
    # changed document (new content_hash) creates a new, dated,
    # version-preserving row rather than overwriting the old one.
    document = None
    doc_meta = outcome.metadata.get('document') if outcome.metadata else None
    if doc_meta:
        document, _ = SourceDocument.objects.get_or_create(
            company_slug=company_slug, url=source.source_url, content_hash=doc_meta['content_hash'],
            defaults={
                'source': source, 'company': profile, 'title': doc_meta['title'],
                'document_type': doc_meta['document_type'], 'publisher': doc_meta['publisher'],
                'source_tier': source_tier(doc_meta['document_type']), 'chunk_count': doc_meta['chunk_count'],
            },
        )

    stats = deduplicate(outcome.candidates, profile=profile, harvest_job=None, document=document)

    # deduplicate() never sets Evidence.source (it only records the string
    # source_type on EvidenceSourceRef) — attribute the real Source row here,
    # scoped to the category/ies this run's candidates actually touched, so
    # this ingestion never overwrites attribution for unrelated evidence.
    candidate_categories = {c.category for c in outcome.candidates}
    Evidence.objects.filter(
        company_slug=company_slug, category__in=candidate_categories, source__isnull=True,
    ).update(source=source)

    source.last_success_at = timezone.now()
    source.save(update_fields=['last_success_at'])

    if stats['canonical_created'] > 0:
        status = 'updated' if had_prior_evidence else 'new'
    else:
        status = 'unchanged'

    memory_created = 0
    if stats['canonical_created'] > 0:
        from evidence_memory.services.memory import create_memory_from_evidence

        new_evidence = Evidence.objects.filter(company_slug=company_slug).order_by('-id')[: stats['canonical_created']]
        for evidence in new_evidence:
            create_memory_from_evidence(evidence)
            memory_created += 1

    run.mark_completed(
        status,
        evidence_created_count=stats['canonical_created'] if status == 'new' else 0,
        evidence_updated_count=stats['canonical_created'] if status == 'updated' else 0,
        refs_attached_count=stats['refs_created'],
        memory_records_created=memory_created,
    )
    return run
