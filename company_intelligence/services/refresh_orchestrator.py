"""
company_intelligence/services/refresh_orchestrator.py — feat/stewardship-
universe (PR 13): the ONE orchestration service for
"Company -> discover sources -> register -> fetch -> version -> extract
evidence -> generate KPI candidates -> review queue -> recompute -> record
telemetry -> return a structured result."

Every step reuses an existing, already-idempotent primitive rather than a
new parallel one:
  - source_discovery.discover_sources_for_company()   (DiscoveredSource,
    unique on company+url)
  - source_registry.register_discovered_source()      (harvester.Source,
    get_or_create on company+source_type+source_url)
  - harvester.services.ingestion_pipeline.ingest_source()  (SourceDocument
    unique on content_hash, Evidence dedup_key, both already proven in
    PR10/11)
  - company_intelligence.services.evidence_ingestion.
    propose_kpi_candidates_for_company()              (CompanyKPIEvidenceLink
    unique on assessment+evidence)

One failed source's exception is caught and recorded as a warning/error for
THAT source only — it never aborts the rest of the company's refresh, and
never corrupts sources that succeeded (Section 11's "one failed source must
not corrupt successful results from other sources").

dry_run=True performs genuinely ZERO database writes: it reports what
WOULD be checked (this company's existing active sources and their real
due-for-refresh status) without calling discovery, registration, or any
fetch. This is a real, honest preview, not a simulation of hypothetical
future discovery results.
"""
import logging

from django.utils import timezone

from ai_observatory.services import recorder
from company_intelligence.services import evidence_ingestion, refresh_policy, source_discovery, source_registry

logger = logging.getLogger(__name__)


def _dry_run_preview(company_profile):
    sources = list(company_profile.harvest_sources.filter(is_active=True))
    due = [s for s in sources if refresh_policy.is_source_due(s)]
    return {
        'dry_run': True,
        'company_slug': company_profile.company.slug,
        'would_check_sources': [
            {'id': s.pk, 'name': s.name, 'source_type': s.source_type, 'is_due': s in due}
            for s in sources
        ],
        'sources_total': len(sources),
        'sources_due': len(due),
        'note': (
            'Dry run — no discovery, registration, fetch, or database write was performed. '
            'This reflects only this company\'s EXISTING registered sources and their real '
            'refresh-policy due status.'
        ),
    }


def refresh_company_intelligence(company_profile, actor=None, triggered_by='manual', dry_run=False):
    """
    Returns a CompanyRefreshRun (persisted) for a real run, or a plain dict
    for dry_run=True (no row is ever created for a dry run — a
    CompanyRefreshRun row is itself a mutation).
    """
    if dry_run:
        return _dry_run_preview(company_profile)

    if company_profile.tracking_status == 'paused':
        return {
            'error': 'paused', 'company_slug': company_profile.company.slug,
            'note': 'This company\'s tracking is paused — resume it explicitly before refreshing.',
        }

    from company_intelligence.models import CompanyRefreshRun

    was_not_tracked = company_profile.tracking_status == 'not_tracked'
    company_profile.tracking_status = 'refresh_in_progress'
    company_profile.save(update_fields=['tracking_status'])

    session = recorder.start_session(company=company_profile, kind='stewardship_refresh', user=actor)
    run = CompanyRefreshRun.objects.create(
        company=company_profile, observatory_session=session, triggered_by=triggered_by, actor=actor,
    )

    warnings, errors = [], []
    sources_checked = sources_failed = 0
    documents_new = documents_updated = documents_unchanged = 0
    evidence_created_total = 0

    try:
        with recorder.record_stage(session, 'source_discovery', 'Authoritative Source Discovery', category='deterministic') as info:
            discovered = source_discovery.discover_sources_for_company(company_profile)
            info['items_processed'] = len(discovered)

        with recorder.record_stage(session, 'source_registration', 'Register Approved Sources', category='deterministic') as info:
            registered_count = 0
            for candidate in company_profile.discovered_sources.filter(status='approved'):
                try:
                    source_registry.register_discovered_source(candidate, actor=actor)
                    registered_count += 1
                except ValueError as exc:
                    warnings.append(f'Could not register {candidate.url}: {exc}')
            info['items_processed'] = registered_count

        active_sources = list(company_profile.harvest_sources.filter(is_active=True))
        with recorder.record_stage(session, 'source_fetch', 'Fetch + Deduplicate Registered Sources', category='retrieval') as info:
            for source in active_sources:
                sources_checked += 1
                try:
                    from harvester.services.ingestion_pipeline import ingest_source

                    ingestion_run = ingest_source(source, triggered_by=f'stewardship_refresh:{triggered_by}')
                    if ingestion_run.status == 'new':
                        documents_new += 1
                        evidence_created_total += ingestion_run.evidence_created_count
                    elif ingestion_run.status == 'updated':
                        documents_updated += 1
                        evidence_created_total += ingestion_run.evidence_updated_count
                    elif ingestion_run.status == 'unchanged':
                        documents_unchanged += 1
                    elif ingestion_run.status == 'failed':
                        sources_failed += 1
                        errors.append(f'{source.name}: {ingestion_run.error_message}')
                    # 'skipped' — inactive/no mapping/robots-disallowed; not a failure, not a change.
                except Exception as exc:
                    sources_failed += 1
                    errors.append(f'{source.name}: unexpected error — {type(exc).__name__}: {exc}')
                    logger.exception('Stewardship refresh: source %s failed for company %s', source.pk, company_profile.pk)
            info['items_processed'] = sources_checked
            info['metadata'] = {'sources_failed': sources_failed}

        with recorder.record_stage(session, 'kpi_candidate_matching', 'KPI Candidate Matching', category='deterministic') as info:
            proposed = evidence_ingestion.propose_kpi_candidates_for_company(company_profile)
            info['items_processed'] = len(proposed)

        from company_intelligence.models import CompanyKPIEvidenceLink

        review_required_count = CompanyKPIEvidenceLink.objects.filter(
            assessment__company=company_profile, review_state__in=('proposed', 'needs_more_evidence', 'disputed'),
        ).count()

    except Exception:
        logger.exception('Stewardship refresh failed unexpectedly for company %s', company_profile.pk)
        run.status = 'failed'
        run.completed_at = timezone.now()
        run.errors = errors + ['Unexpected failure during refresh — see server logs.']
        run.warnings = warnings
        run.save()
        recorder.finish_session(session, status='failed', warnings=warnings)
        company_profile.tracking_status = 'error'
        company_profile.last_refresh_at = timezone.now()
        company_profile.save(update_fields=['tracking_status', 'last_refresh_at'])
        return run

    if sources_checked == 0:
        status = 'complete'  # nothing registered yet is not a failure of this run
    elif sources_failed == 0:
        status = 'complete'
    elif sources_failed < sources_checked:
        status = 'partial'
    else:
        status = 'failed'

    run.status = status
    run.completed_at = timezone.now()
    run.sources_checked = sources_checked
    run.sources_failed = sources_failed
    run.documents_new = documents_new
    run.documents_updated = documents_updated
    run.documents_unchanged = documents_unchanged
    run.evidence_created = evidence_created_total
    run.kpi_candidates_proposed = len(proposed)
    run.review_required_count = review_required_count
    run.warnings = warnings
    run.errors = errors
    run.save()

    recorder.finish_session(
        session, status='completed' if status != 'failed' else 'failed',
        evidence_retrieved=evidence_created_total, warnings=warnings,
        final_recommendation_status='recorded',
    )

    company_profile.tracking_status = 'error' if status == 'failed' else 'active'
    company_profile.last_refresh_at = timezone.now()
    company_profile.next_refresh_due_at = refresh_policy.company_next_refresh_due_at(company_profile)
    company_profile.save(update_fields=['tracking_status', 'last_refresh_at', 'next_refresh_due_at'])

    if was_not_tracked and status != 'failed':
        logger.info('Stewardship refresh implicitly started tracking for company %s', company_profile.pk)

    return run
