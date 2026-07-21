"""
company_intelligence/services/change_detection.py — feat/stewardship-
monitor (PR 14): deterministic detection of real, already-happened changes
in a tracked company's evidence base, and the CURRENT/HISTORICAL/POSSIBLY_
SUPERSEDED/STALE semantics that let a reviewer tell fresh evidence apart
from evidence that may no longer be the latest word without ever deleting
or rewriting it.

Every function here is a pure decision over already-stored, already-
idempotent facts (harvester.IngestionRun.status, SourceDocument content
hashes, Source.last_success_at/last_failure_at) — this module never makes
a network call and never invents a change that didn't genuinely happen.
An 'unchanged'/'skipped' IngestionRun NEVER produces a StewardshipChangeEvent
— that is the single most important invariant here (Section 24's "this
source did not change, so EcoIQ generated no false alert").
"""
from company_intelligence.models import StewardshipChangeEvent

# harvester.constants.SOURCE_TYPES that fetch a whole versioned document
# (see harvester.services.ingestion_pipeline.DOCUMENT_SOURCE_TYPES) —
# 'new'/'updated' for these means a document changed; for every other
# source type (sec_edgar, companies_house, csv_dataset, url_recheck) the
# same statuses mean a raw evidence fact changed instead.
from harvester.services.ingestion_pipeline import DOCUMENT_SOURCE_TYPES

SEVERITY_BY_EVENT_TYPE = {
    'new_source': 'info',
    'source_changed': 'low',
    'source_unreachable': 'high',
    'source_recovered': 'info',
    'new_document': 'medium',
    'document_updated': 'medium',
    'document_removed_or_unreachable': 'medium',
    'new_evidence': 'low',
    'evidence_changed': 'medium',
    'new_kpi_candidate': 'low',
    'potential_conflict': 'high',
    'evidence_stale': 'low',
    'shariah_data_changed': 'medium',
    'review_required': 'low',
}


def record_new_source(discovered_source, harvester_source, refresh_run=None):
    """
    Called once, right after a DiscoveredSource is registered as a real,
    fetchable harvester.Source for the first time (never on a repeat
    registration — the caller only invokes this when `created=True`).
    """
    return StewardshipChangeEvent.objects.create(
        company=discovered_source.company, event_type='new_source', severity=SEVERITY_BY_EVENT_TYPE['new_source'],
        source=harvester_source, refresh_run=refresh_run,
        summary=f'New authoritative source registered: {harvester_source.name}.',
        new_state=harvester_source.get_source_type_display(),
    )


def detect_source_change(source, ingestion_run, refresh_run=None):
    """
    Given a harvester.Source and the IngestionRun that was JUST completed
    for it this refresh, returns a LIST of StewardshipChangeEvent rows
    created (empty if nothing changed — 'unchanged'/'skipped' with no
    prior failure is a real no-op, not an event). Always a list, never a
    single possibly-None event, so a recovery detected ALONGSIDE a new/
    updated document is never silently dropped from the caller's own
    change-event/alert list (both genuinely happened this run and both
    deserve their own alert).
    """
    from harvester.models import IngestionRun

    company = source.company
    is_document_source = source.source_type in DOCUMENT_SOURCE_TYPES

    previous_run = (
        IngestionRun.objects.filter(source=source).exclude(pk=ingestion_run.pk).order_by('-created_at').first()
    )
    previously_failed = previous_run is not None and previous_run.status == 'failed'

    if ingestion_run.status == 'failed':
        return [StewardshipChangeEvent.objects.create(
            company=company, event_type='source_unreachable', severity=SEVERITY_BY_EVENT_TYPE['source_unreachable'],
            source=source, refresh_run=refresh_run, review_required=True,
            summary=f'{source.name} is currently unreachable: {ingestion_run.error_message}',
            previous_state='reachable', new_state='unreachable',
        )]

    if ingestion_run.status in ('new', 'updated'):
        event_type = ('new_document' if ingestion_run.status == 'new' else 'document_updated') if is_document_source \
            else ('new_evidence' if ingestion_run.status == 'new' else 'evidence_changed')
        document = None
        if is_document_source:
            document = source.documents.order_by('-retrieved_at').first()
        verb = 'published a new' if ingestion_run.status == 'new' else 'updated its'
        label = source.get_source_type_display()
        events = [StewardshipChangeEvent.objects.create(
            company=company, event_type=event_type, severity=SEVERITY_BY_EVENT_TYPE[event_type],
            source=source, document=document, refresh_run=refresh_run,
            summary=f'{company.company.name} {verb} {label}.',
            new_state=f'{ingestion_run.evidence_created_count + ingestion_run.evidence_updated_count} evidence row(s)',
        )]
        if previously_failed:
            events.append(_record_recovery(source, refresh_run))
        return events

    # 'unchanged' or 'skipped' — the source recovered from a prior failure
    # even though nothing new was found this time (e.g. the same content
    # is reachable again after a transient outage).
    if ingestion_run.status == 'unchanged' and previously_failed:
        return [_record_recovery(source, refresh_run)]

    return []


def record_shariah_data_changed(company_profile, refresh_run=None):
    """
    Called only when refresh_orchestrator's financial-facts sync step
    (evidence_ingestion.sync_financial_facts_for_company) genuinely created
    a NEW CompanyFinancialFacts snapshot this run — never on an unchanged
    re-fetch. This only ever FLAGS the change; it never triggers an
    automatic re-screen with an arbitrarily-chosen methodology, since which
    methodology to screen under remains a Shariah-screening-flow decision,
    not this pipeline's to make.
    """
    return StewardshipChangeEvent.objects.create(
        company=company_profile, event_type='shariah_data_changed', severity=SEVERITY_BY_EVENT_TYPE['shariah_data_changed'],
        refresh_run=refresh_run, review_required=True,
        summary=f'{company_profile.company.name} — new financial data may affect Shariah screening; refresh recommended.',
    )


def _record_recovery(source, refresh_run):
    return StewardshipChangeEvent.objects.create(
        company=source.company, event_type='source_recovered', severity=SEVERITY_BY_EVENT_TYPE['source_recovered'],
        source=source, refresh_run=refresh_run,
        summary=f'{source.name} is reachable again after a previous failure.',
        previous_state='unreachable', new_state='reachable',
    )


def record_new_kpi_candidates(company_profile, newly_created_links, refresh_run=None):
    """
    One aggregate event per refresh for newly-proposed KPI candidates —
    never one row per candidate (Section 2's "do not store giant
    duplicated payloads unnecessarily"). Individual candidates remain
    fully inspectable in the Evidence Review Workbench itself via each
    link's own `proposed_via_refresh_run` FK.
    """
    if not newly_created_links:
        return None
    review_required = len(newly_created_links) > 0
    return StewardshipChangeEvent.objects.create(
        company=company_profile, event_type='new_kpi_candidate', severity=SEVERITY_BY_EVENT_TYPE['new_kpi_candidate'],
        refresh_run=refresh_run, review_required=review_required,
        summary=f'{len(newly_created_links)} new KPI candidate(s) proposed for review.',
        new_state=str(len(newly_created_links)),
    )


# ---------------------------------------------------------------------------
# Current / historical / possibly-superseded / stale semantics — computed
# live, never stored, and never destructive: an older document/evidence row
# is NEVER deleted or rewritten when a newer one arrives (Section 13).
# ---------------------------------------------------------------------------
STALE_FRESHNESS_THRESHOLD = 0.3


def evidence_status_label(link):
    """
    Returns one of CURRENT / HISTORICAL / POSSIBLY_SUPERSEDED / DISPUTED /
    STALE for a CompanyKPIEvidenceLink — a real, deterministic label the UI
    can show without ever concluding that older evidence is false. DISPUTED
    always wins (an explicit human action); STALE/POSSIBLY_SUPERSEDED are
    both honest "this may need a fresh look" signals, never a deletion.
    """
    from company_intelligence.services.evidence_quality import _harvester_evidence_for_memory

    if link.review_state == 'disputed':
        return 'DISPUTED'

    harvester_evidence = _harvester_evidence_for_memory(link.evidence)
    if harvester_evidence is None:
        return 'CURRENT'

    if harvester_evidence.freshness_score is not None and harvester_evidence.freshness_score < STALE_FRESHNESS_THRESHOLD:
        return 'STALE'

    if harvester_evidence.document_id:
        from harvester.models import SourceDocument

        latest_doc = SourceDocument.objects.filter(
            company_slug=harvester_evidence.document.company_slug, url=harvester_evidence.document.url,
        ).order_by('-retrieved_at').first()
        if latest_doc is not None and latest_doc.pk != harvester_evidence.document_id:
            from company_intelligence.models import StewardshipChangeEvent as SCE

            has_conflict_flag = SCE.objects.filter(kpi_evidence_link__evidence=link.evidence, event_type='potential_conflict').exists()
            return 'POSSIBLY_SUPERSEDED' if has_conflict_flag else 'HISTORICAL'

    return 'CURRENT'
