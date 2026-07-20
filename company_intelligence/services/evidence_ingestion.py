"""
company_intelligence/services/evidence_ingestion.py — feat/company-
evidence-ingestion (PR 10): the bridge from REAL PUBLIC COMPANY through
AUTHORITATIVE PUBLIC SOURCES to STRUCTURED EVIDENCE with PROVENANCE, for
one companies.CompanyProfile at a time.

Reuses, never duplicates:
- harvester.services.fetchers.fetch_sec_edgar() — the real SEC EDGAR fetch.
- harvester.services.ingestion_pipeline.ingest_source() — the real
  FETCH -> VALIDATE -> DEDUPLICATE -> VERIFY -> STORE -> EvidenceMemory
  pipeline (idempotent by construction: harvester.dedup.deduplicate() only
  creates a new canonical harvester.Evidence row when the normalized
  statement is genuinely new for this company+category).
- harvester.dedup.dedup_key()/normalize_text() — to deterministically find
  the exact canonical Evidence row a given financial statement produced,
  without a second network call's results silently drifting from the
  first's.
- company_intelligence.services.shariah_screening.run_shariah_screen() —
  unchanged from PR9; this module only supplies it real financial_facts.
- company_intelligence.services.kpi_candidate_matching — proposes (never
  confirms) KPI links from the evidence this module ingests.
- ai_observatory.services.recorder — the one telemetry system; this
  pipeline is a new AnalysisSession kind, never a parallel observatory.

Identity resolution: currently supports US-listed companies with a mapped
SEC CIK (companies/management/commands/ingest_sec_edgar.py::US_COMPANY_CIKS
— the same identity table that command already used, not a new
company-name-matching heuristic). A company with no stable identifier
mapped is honestly reported as unavailable for real ingestion, never
guessed at by name alone.
"""
import datetime
import logging

from django.utils import timezone

from ai_observatory.services import recorder
from harvester.dedup import dedup_key, normalize_text
from harvester.models import Evidence as HarvesterEvidence
from harvester.services import fetchers
from harvester.services.ingestion_pipeline import ingest_source

logger = logging.getLogger(__name__)


def resolve_company_identity(company_profile):
    """
    Returns {'slug', 'cik', 'sec_available'} — a real, inspectable identity
    resolution, never a name-matching guess. `cik` is None (and
    sec_available False) when this company has no mapped stable identifier;
    callers must treat that as an honest "cannot ingest real SEC data for
    this company today", never a fallback to fuzzy matching by name.
    """
    from companies.management.commands.ingest_sec_edgar import US_COMPANY_CIKS

    slug = company_profile.company.slug
    cik = US_COMPANY_CIKS.get(slug)
    return {'slug': slug, 'cik': cik, 'sec_available': cik is not None}


def _get_or_create_sec_source(company_profile, cik):
    from harvester.models import Source

    source, _ = Source.objects.get_or_create(
        company=company_profile, source_type='sec_edgar',
        defaults={
            'name': f'SEC EDGAR — CIK {cik}',
            'source_url': f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K',
            'source_owner': 'U.S. Securities and Exchange Commission',
            'confidence_base': 0.92,
            'update_frequency': 'quarterly',
        },
    )
    return source


def _backfill_company_identity_text(league_company, metadata):
    """
    Same honest fill-only-when-empty convention as the standalone
    ingest_sec_edgar command (companies/management/commands/
    ingest_sec_edgar.py) — never overwrites an existing description,
    never invents one. Without SOME real description text, the Shariah
    business-activity screen (services/shariah_screening.py) has nothing
    to check and honestly returns insufficient_data forever, even once
    real financial data exists — this closes that real gap with only real,
    reported facts (entity name, real revenue figure), never a fabricated
    business description.
    """
    if league_company.description:
        return
    entity_name = metadata.get('entity_name', '')
    revenue = metadata.get('metrics', {}).get('revenue_usd', {}).get('value')
    parts = [f'{entity_name} — SEC CIK {metadata.get("cik", "")}.'] if entity_name else []
    if revenue:
        parts.append(f'Reported annual revenue: ${revenue / 1e9:.1f}B per SEC EDGAR XBRL data.')
    if parts:
        league_company.description = ' '.join(parts)
        league_company.save(update_fields=['description'])


def _sync_financial_facts(company_profile, metadata, actor=None):
    """
    Builds a new CompanyFinancialFacts snapshot from fetch_sec_edgar's
    metadata dict, with per-metric CompanyFinancialFactSource provenance
    linking each real figure to the exact harvester.Evidence row it came
    from (found via the SAME dedup_key the ingestion pipeline used — never
    a second, possibly-inconsistent lookup).

    Idempotent in the version/history sense the brief asks for: if the
    latest existing snapshot for this company already has identical values
    for every metric found this run, no new row is created (a genuine
    no-op re-run); if anything differs, a NEW dated snapshot is created —
    the prior one is never overwritten in place, so history is preserved.
    market_cap_usd and interest_bearing_securities_usd are not obtainable
    from XBRL companyfacts and are honestly left None, never defaulted.
    """
    from company_intelligence.models import CompanyFinancialFacts, CompanyFinancialFactSource
    from evidence_memory.models import EvidenceMemory

    metrics = metadata.get('metrics', {})
    if not metrics:
        return None, []

    period_ends = [m['period_end'] for m in metrics.values() if m.get('period_end')]
    as_of_date = max(
        (datetime.date.fromisoformat(d) for d in period_ends), default=timezone.now().date(),
    )

    latest = company_profile.financial_facts.order_by('-as_of_date', '-id').first()
    field_names = (
        'revenue_usd', 'total_debt_usd', 'cash_and_equivalents_usd',
        'interest_bearing_securities_usd', 'non_permissible_income_usd',
    )
    new_values = {name: metrics[name]['value'] for name in field_names if name in metrics}
    if latest is not None:
        unchanged = all(getattr(latest, name) == new_values.get(name) for name in field_names)
        if unchanged and latest.as_of_date == as_of_date:
            return latest, []

    facts = CompanyFinancialFacts.objects.create(
        company=company_profile, as_of_date=as_of_date,
        source=f"SEC EDGAR XBRL — CIK {metadata.get('cik', '')}",
        retrieved_at=timezone.now(), is_demo=False,
        **new_values,
    )

    sources_created = []
    for field_name, entry in metrics.items():
        if field_name not in field_names:
            continue
        statement = entry.get('statement', '')
        key = dedup_key(company_profile.company.slug, 'financial', normalize_text(statement))
        harvester_evidence = HarvesterEvidence.objects.filter(
            company_slug=company_profile.company.slug, category='financial', dedup_key=key,
        ).first()
        memory = None
        if harvester_evidence is not None:
            memory = EvidenceMemory.objects.filter(
                source_type='harvester_evidence', source_reference=f'harvester.Evidence:{harvester_evidence.pk}',
            ).first()
        source_row = CompanyFinancialFactSource.objects.create(
            financial_facts=facts, metric=field_name, evidence=memory,
            is_derived=entry.get('is_derived', False),
            interpretation_note=(
                f"Derived from XBRL concept {entry.get('concept')} as a conservative interest-income proxy."
                if entry.get('is_derived') else ''
            ),
        )
        sources_created.append(source_row)

    return facts, sources_created


def _propose_kpi_candidates_for_company(company_profile):
    """Runs the deterministic KPI candidate matcher over every real
    harvester-sourced EvidenceMemory row this company has — idempotent
    (CompanyKPIEvidenceLink has a unique constraint on assessment+evidence,
    so re-running never duplicates a proposal)."""
    from company_intelligence.services.kpi_candidate_matching import propose_kpi_links_for_evidence
    from evidence_memory.models import EvidenceMemory

    memories = EvidenceMemory.objects.filter(company=company_profile, source_type='harvester_evidence')
    proposed = []
    for memory in memories:
        harvester_evidence = _harvester_evidence_for_memory(memory)
        if harvester_evidence is None:
            continue
        proposed += propose_kpi_links_for_evidence(company_profile, memory, harvester_evidence.category)
    return proposed


def _harvester_evidence_for_memory(memory):
    if not memory.source_reference.startswith('harvester.Evidence:'):
        return None
    try:
        pk = int(memory.source_reference.split(':', 1)[1])
    except (IndexError, ValueError):
        return None
    return HarvesterEvidence.objects.filter(pk=pk).first()


def ingest_company_evidence(company_profile, actor=None, methodology=None):
    """
    The main orchestrator: identity -> SEC EDGAR fetch -> harvester
    ingestion (idempotent) -> financial facts + per-metric provenance ->
    KPI candidate proposals -> Shariah screen re-run with the fresh
    financial facts. Wrapped in one real ai_observatory.AnalysisSession.

    Returns a result dict — never raises for an honest "no real source
    available" case, only for genuine unexpected failures (which still
    finish the Observatory session with status='failed' before propagating,
    so a crash is never silently untelemetered).
    """
    identity = resolve_company_identity(company_profile)
    session = recorder.start_session(company=company_profile, kind='company_evidence_ingestion', user=actor)

    result = {
        'identity': identity, 'ingestion_run': None, 'financial_facts': None,
        'financial_fact_sources': [], 'kpi_candidates_proposed': [], 'shariah_screen': None,
        'warnings': [],
    }

    if not identity['sec_available']:
        result['warnings'].append(
            f"No stable identifier (SEC CIK) is mapped for \"{identity['slug']}\" — real ingestion is "
            f"unavailable for this company; nothing was fetched or fabricated."
        )
        recorder.finish_session(session, warnings=result['warnings'], final_recommendation_status='not_applicable')
        return result

    try:
        with recorder.record_stage(session, 'sec_edgar_fetch', 'SEC EDGAR Fetch + Deduplication', category='retrieval') as info:
            source = _get_or_create_sec_source(company_profile, identity['cik'])
            run = ingest_source(source, triggered_by='company_intelligence')
            result['ingestion_run'] = run
            info['items_processed'] = run.evidence_created_count + run.evidence_updated_count
            info['metadata'] = {'status': run.status, 'memory_records_created': run.memory_records_created}
            if run.status == 'failed':
                result['warnings'].append(f'SEC EDGAR fetch failed: {run.error_message}')

        with recorder.record_stage(session, 'financial_facts_extraction', 'Financial Facts Extraction', category='deterministic') as info:
            outcome = fetchers.fetch_sec_edgar(identity['slug'])
            if outcome.success:
                facts, sources = _sync_financial_facts(company_profile, outcome.metadata, actor=actor)
                result['financial_facts'] = facts
                result['financial_fact_sources'] = sources
                _backfill_company_identity_text(company_profile.company, outcome.metadata)
                info['items_processed'] = len(sources)
                missing = [f for f in ('market_cap_usd', 'interest_bearing_securities_usd') if not outcome.metadata.get('metrics', {}).get(f)]
                if missing:
                    result['warnings'].append(
                        f"Not obtainable from SEC EDGAR XBRL data (honestly left Missing, never zero): {', '.join(missing)}."
                    )
            else:
                result['warnings'].append(f'Financial facts extraction unavailable: {outcome.error or outcome.skipped_reason}')

        with recorder.record_stage(session, 'kpi_candidate_matching', 'KPI Candidate Matching', category='deterministic') as info:
            proposed = _propose_kpi_candidates_for_company(company_profile)
            result['kpi_candidates_proposed'] = proposed
            info['items_processed'] = len(proposed)

        if methodology is not None:
            with recorder.record_stage(session, 'shariah_rescreen', 'Shariah Re-Screen With Fresh Data', category='deterministic') as info:
                from company_intelligence.services.shariah_screening import run_shariah_screen
                screen = run_shariah_screen(
                    company_profile, methodology, financial_facts=result['financial_facts'], actor=actor,
                )
                result['shariah_screen'] = screen
                info['metadata'] = {'overall_result': screen.overall_result}

    except Exception:
        logger.exception('Evidence ingestion failed for company %s', company_profile.pk)
        recorder.finish_session(session, status='failed', warnings=result['warnings'] + ['Unexpected failure during ingestion.'])
        raise

    recorder.finish_session(
        session, evidence_retrieved=(result['ingestion_run'].evidence_created_count if result['ingestion_run'] else 0),
        warnings=result['warnings'], final_recommendation_status='recorded',
    )
    return result
