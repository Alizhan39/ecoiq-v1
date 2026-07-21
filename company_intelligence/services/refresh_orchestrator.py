"""
company_intelligence/services/refresh_orchestrator.py — feat/stewardship-
universe (PR 13), extended by feat/stewardship-monitor (PR 14): the ONE
orchestration service for
"Company -> discover sources -> register -> fetch -> version -> extract
evidence -> generate KPI candidates -> detect changes -> flag potential
conflicts -> generate alerts -> review queue -> recompute -> record
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

PR 14 additions (Continuous Stewardship Monitor):
  - A genuine, backend-portable concurrency lock (an atomic
    UPDATE ... WHERE tracking_status != 'refresh_in_progress', not
    SELECT ... FOR UPDATE, which SQLite doesn't support) — a second
    concurrent trigger for the SAME company is refused rather than double-
    running (Section 15's "prevent overlapping refreshes for the same
    company").
  - Per-source due-date gating for any non-'manual' trigger (a scheduled/
    batch run only fetches sources refresh_policy says are actually due —
    never re-hammers a provider on every batch tick just because the
    COMPANY was due; a staff-initiated manual refresh still rechecks every
    active source, unchanged from PR13, since that's a deliberate human
    action). Skipped-not-due sources are tracked separately and never
    counted as checked/failed.
  - Deterministic change detection (services/change_detection.py) and
    conservative potential-conflict flagging (services/conflict_detection.py)
    run against this run's OWN real results only — never a re-scan of
    unrelated history — and every real change becomes exactly one
    StewardshipAlert (services/stewardship_alerts.py). An unchanged run
    produces zero change events and zero alerts.
"""
import logging

from django.utils import timezone

from ai_observatory.services import recorder
from company_intelligence.services import (
    change_detection, conflict_detection, evidence_ingestion, rate_limiter, refresh_policy,
    source_discovery, source_registry, stewardship_alerts,
)

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


def _try_acquire_refresh_lock(company_profile):
    """
    Atomic compare-and-swap: only transitions tracking_status to
    'refresh_in_progress' if the row is NOT already in that state right
    now, in a single UPDATE ... WHERE statement — this is atomic per-row on
    every backend Django supports (SQLite included), unlike
    select_for_update(), which SQLite cannot honour. If a concurrent
    refresh is genuinely already running for this company, this returns
    False and the caller must not proceed.
    """
    from companies.models import CompanyProfile

    updated = CompanyProfile.objects.filter(pk=company_profile.pk).exclude(
        tracking_status='refresh_in_progress',
    ).update(tracking_status='refresh_in_progress')
    if updated:
        company_profile.tracking_status = 'refresh_in_progress'
    return bool(updated)


def refresh_company_intelligence(company_profile, actor=None, triggered_by='manual', dry_run=False):
    """
    Returns a CompanyRefreshRun (persisted) for a real run, or a plain dict
    for dry_run=True / paused / lock-unavailable (no CompanyRefreshRun row
    is ever created for any of those three cases — each is itself a
    genuine non-mutation outcome, not a failure).
    """
    if dry_run:
        return _dry_run_preview(company_profile)

    if company_profile.tracking_status == 'paused':
        return {
            'error': 'paused', 'company_slug': company_profile.company.slug,
            'note': 'This company\'s tracking is paused — resume it explicitly before refreshing.',
        }

    was_not_tracked = company_profile.tracking_status == 'not_tracked'
    if not _try_acquire_refresh_lock(company_profile):
        return {
            'error': 'already_refreshing', 'company_slug': company_profile.company.slug,
            'note': 'A refresh is already running for this company — this trigger was refused, not queued or retried.',
        }

    from company_intelligence.models import CompanyRefreshRun

    session = recorder.start_session(company=company_profile, kind='stewardship_refresh', user=actor)
    run = CompanyRefreshRun.objects.create(
        company=company_profile, observatory_session=session, triggered_by=triggered_by, actor=actor,
    )

    warnings, errors = [], []
    sources_checked = sources_failed = sources_skipped_not_due = 0
    documents_new = documents_updated = documents_unchanged = 0
    evidence_created_total = 0
    change_events = []
    is_manual = (triggered_by == 'manual')

    try:
        with recorder.record_stage(session, 'source_discovery', 'Authoritative Source Discovery', category='deterministic') as info:
            discovered = source_discovery.discover_sources_for_company(company_profile)
            info['items_processed'] = len(discovered)

        with recorder.record_stage(session, 'source_registration', 'Register Approved Sources', category='deterministic') as info:
            registered_count = 0
            for candidate in company_profile.discovered_sources.filter(status='approved'):
                try:
                    harvester_source, created = source_registry.register_discovered_source(candidate, actor=actor)
                    registered_count += 1
                    if created:
                        change_events.append(change_detection.record_new_source(candidate, harvester_source, refresh_run=run))
                except ValueError as exc:
                    warnings.append(f'Could not register {candidate.url}: {exc}')
            info['items_processed'] = registered_count

        active_sources = list(company_profile.harvest_sources.filter(is_active=True))
        sec_edgar_checked_this_run = False
        # feat/global-stewardship-universe (PR 15) Section 17 — "scale
        # safely": a per-source-type budget for THIS run (never a hidden
        # skip — sources_skipped_not_due already tracks the other kind of
        # skip, so a type-budget skip is folded into the same counter
        # rather than inventing a second, undocumented skip reason) plus a
        # per-domain minimum interval before every outbound fetch.
        source_type_budget = rate_limiter.SourceTypeBudget()
        with recorder.record_stage(session, 'source_fetch', 'Fetch + Deduplicate Registered Sources', category='retrieval') as info:
            for source in active_sources:
                if not is_manual and not refresh_policy.is_source_due(source):
                    sources_skipped_not_due += 1
                    continue
                if not source_type_budget.allow(source.source_type):
                    sources_skipped_not_due += 1
                    warnings.append(
                        f'{source.name}: skipped — per-run budget for source type "{source.source_type}" reached.'
                    )
                    continue
                sources_checked += 1
                if source.source_type == 'sec_edgar':
                    sec_edgar_checked_this_run = True
                try:
                    from company_intelligence.services.known_sources import domain_of
                    from harvester.services.ingestion_pipeline import ingest_source

                    rate_limiter.wait_for_domain_slot(domain_of(source.source_url))
                    ingestion_run = ingest_source(source, triggered_by=f'stewardship_refresh:{triggered_by}')
                    change_events.extend(change_detection.detect_source_change(source, ingestion_run, refresh_run=run))

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
            info['metadata'] = {'sources_failed': sources_failed, 'sources_skipped_not_due': sources_skipped_not_due}

        if sec_edgar_checked_this_run:
            with recorder.record_stage(session, 'shariah_data_check', 'Shariah Financial Data Check', category='deterministic') as info:
                facts, sources_created = evidence_ingestion.sync_financial_facts_for_company(company_profile)
                info['items_processed'] = len(sources_created)
                if sources_created:
                    change_events.append(change_detection.record_shariah_data_changed(company_profile, refresh_run=run))

        with recorder.record_stage(session, 'kpi_candidate_matching', 'KPI Candidate Matching', category='deterministic') as info:
            proposed = evidence_ingestion.propose_kpi_candidates_for_company(company_profile, refresh_run=run)
            info['items_processed'] = len(proposed)
            if proposed:
                event = change_detection.record_new_kpi_candidates(company_profile, proposed, refresh_run=run)
                if event is not None:
                    change_events.append(event)

        with recorder.record_stage(session, 'conflict_detection', 'Potential Conflict Detection', category='deterministic') as info:
            conflict_events = conflict_detection.detect_potential_conflicts_for_refresh(company_profile, proposed, refresh_run=run)
            change_events.extend(conflict_events)
            info['items_processed'] = len(conflict_events)

        with recorder.record_stage(session, 'alert_generation', 'Stewardship Alert Generation', category='deterministic') as info:
            alerts = stewardship_alerts.generate_alerts_for_refresh(company_profile, run, change_events)
            info['items_processed'] = len(alerts)

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
        status = 'complete'  # nothing registered/due yet is not a failure of this run
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
    run.sources_skipped_not_due = sources_skipped_not_due
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
