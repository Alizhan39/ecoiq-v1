"""
backend_intelligence_engine/tasks.py — the three real background workflows.

Every task follows the same shape: create a BackgroundTaskRun row first
(status='queued' -> 'running', already saved before any real work starts),
then mark it 'completed' or 'failed' at the end — never leave a task
invisible. Each wraps EXISTING EcoIQ services; no task here contains new
scoring, climate, or agent execution logic of its own.

Every invocation — including each automatic retry — creates its own
BackgroundTaskRun row rather than trying to find and mutate a previous
attempt's row: Celery does not guarantee a stable task id across
`autoretry_for` retries across versions, so correlating by id would be
fragile. `retry_count` on each row (from `self.request.retries`) makes the
retry sequence for one target fully reconstructable via `target_reference`
without relying on that guarantee.

Retries are bounded and explicit (`autoretry_for`, `max_retries`,
`retry_backoff`) — nothing retries forever, per the platform-wide safety
requirement.
"""
import logging

from celery import shared_task

from backend_intelligence_engine.models import BackgroundTaskRun

logger = logging.getLogger(__name__)


def _start_run(task_type, target_repr, target_reference, request, task_kwargs=None):
    run = BackgroundTaskRun.objects.create(
        task_type=task_type, target_repr=target_repr, target_reference=target_reference,
        task_kwargs=task_kwargs or {}, celery_task_id=request.id or '', retry_count=request.retries,
    )
    run.mark_running()
    return run


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=60,
             max_retries=2, retry_jitter=True)
def company_intelligence_refresh(self, company_profile_id):
    """
    Company Intelligence Refresh — reuses, in order:
      intelligence.compute.check_monitor_target(watch)   — evidence refresh
      companies.scoring.recalculate_and_save(profile)    — score recalculation
      pandas_scoring_engine...compute_company_intelligence_score(profile) —
        explainable intelligence-score recalculation, attached to the SAME
        snapshot below (not a second snapshot) — this is the "company
        intelligence refresh should be able to trigger score recalculation"
        connection point.
      CompanyScoreSnapshot.create_from_profile(...)       — intelligence snapshot
    No new scoring or evidence logic is introduced here.
    """
    from companies.models import CompanyProfile, CompanyScoreSnapshot
    from companies.scoring import recalculate_and_save
    from intelligence.compute import check_monitor_target
    from pandas_scoring_engine.services.scoring import compute_company_intelligence_score

    target_reference = f'companies.CompanyProfile:{company_profile_id}'

    try:
        profile = CompanyProfile.objects.select_related('company').get(pk=company_profile_id)
    except CompanyProfile.DoesNotExist:
        run = _start_run(
            'company_intelligence_refresh', f'CompanyProfile #{company_profile_id} (not found)',
            target_reference, self.request, task_kwargs={'company_profile_id': company_profile_id},
        )
        run.mark_failed(f'CompanyProfile {company_profile_id} does not exist.')
        return {'status': 'failed', 'reason': 'not_found'}

    run = _start_run(
        'company_intelligence_refresh', profile.company.name if profile.company_id else f'Profile #{profile.pk}',
        target_reference, self.request, task_kwargs={'company_profile_id': company_profile_id},
    )

    score_before = profile.ecoiq_total_score
    watches_checked = 0
    watches_changed = 0

    if profile.company_id:
        for watch in profile.company.monitors.all():
            watches_checked += 1
            if check_monitor_target(watch):
                watches_changed += 1

    recalculate_and_save(profile)
    profile.refresh_from_db()

    intelligence_scores = compute_company_intelligence_score(profile)
    snapshot = CompanyScoreSnapshot.create_from_profile(
        profile, trigger='background_refresh',
        notes=f'Automated background refresh (Celery task {self.request.id}).',
        intelligence_scores=intelligence_scores,
    )

    result_summary = {
        'score_before': score_before, 'score_after': profile.ecoiq_total_score,
        'watches_checked': watches_checked, 'watches_changed': watches_changed,
        'snapshot_id': snapshot.pk, 'intelligence_score': intelligence_scores['intelligence_score'],
    }
    run.mark_completed(result_summary)

    # Only surface a notification for a real, meaningful change — not noise
    # on every routine refresh where nothing moved.
    score_delta = abs((profile.ecoiq_total_score or 0) - (score_before or 0))
    if score_delta >= 2.0:
        from notifications.models import create_notification
        create_notification(
            title=f'{profile.company.name if profile.company_id else profile}: score moved {score_delta:.1f} points',
            source_type='background_task', message=f'EcoIQ total score: {score_before} → {profile.ecoiq_total_score}.',
            priority='normal', metadata=result_summary,
        )

    return {'status': 'completed', **result_summary}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=60,
             max_retries=2, retry_jitter=True)
def geo_intelligence_refresh(self, city_name=None):
    """
    Geo Intelligence Refresh — reuses geo_intelligence.services.weather
    exactly as the Phase 1 map page does. Proactively re-warms the 24h
    Django cache Meteostat already sits behind (see weather.py), so a
    visitor never pays the live-fetch cost the cache is meant to avoid.
    Creates no new persistence: this app's own Phase 1 design intentionally
    does not store a climate time-series, and this task does not change
    that — "last successful refresh" is this BackgroundTaskRun row itself.
    """
    from geo_intelligence.services import weather

    unknown = city_name and city_name not in weather.KAZAKHSTAN_CITIES
    target_reference = f'geo_intelligence.city:{city_name or "all"}'
    run = _start_run(
        'geo_intelligence_refresh', city_name or 'All Kazakhstan reference cities',
        target_reference, self.request, task_kwargs={'city_name': city_name},
    )

    if unknown:
        run.mark_failed(f'"{city_name}" is not a supported Geo Intelligence city.')
        return {'status': 'failed', 'reason': 'unsupported_city'}

    cities = {city_name: weather.KAZAKHSTAN_CITIES[city_name]} if city_name else weather.KAZAKHSTAN_CITIES
    refreshed = {}
    for name, coords in cities.items():
        summary = weather.get_city_climate_summary(name, coords['latitude'], coords['longitude'], coords.get('elevation', 0))
        refreshed[name] = {'available': summary['available'], 'reason': summary.get('reason', '')}

    result_summary = {'cities': refreshed}
    if any(r['available'] for r in refreshed.values()):
        run.mark_completed(result_summary)
        return {'status': 'completed', **result_summary}

    # Every city's live fetch failed (e.g. no network) — an honest failure,
    # never papered over with fabricated data.
    run.result_summary = result_summary
    run.mark_failed('Meteostat fetch unavailable for every requested city — see result_summary.')
    return {'status': 'failed', **result_summary}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=60,
             max_retries=2, retry_jitter=True)
def run_ai_analysis(self, agent_slug, case_slug=None, execution_mode='deterministic_test', input_summary='',
                     company_profile_id=None, country_slug=None):
    """
    AI Analysis Background Task — reuses the existing, already-complete
    execution pipeline exactly as-is:
      create_agent_run -> execute_agent -> submit_agent_position_to_council
    No duplicate execution architecture. Persists through the real
    AgentRun/AgentTask/CouncilRun models the AI Agent Workbench already
    reads — a completed run here is immediately visible there, at
    /ai-agents/workbench/?case=<case_slug>&agent=<agent_slug>.

    execution_mode='live' is honestly supported: without ANTHROPIC_API_KEY
    configured it will legitimately end as 'needs_human_review' (missing
    credentials, not fabricated success) — see agent_runtime_model_router's
    own adapters, which this task does not modify.

    Evidence Memory integration: relevant prior memory (scoped to
    company_profile_id/country_slug when given) is retrieved and appended to
    input_summary BEFORE execute_agent runs, so it genuinely reaches the
    agent's prompt (see build_agent_instruction, which builds the prompt
    directly from input_summary) — not decoration, real context. On success,
    the finding is saved back to memory so the next run has more to draw on.
    """
    from django.utils.text import slugify

    from ai_agent_council.agents import OPERATIONAL_AGENTS
    from ai_agent_workbench.services import demo_cases
    from agent_runtime_model_router.services.execution import (
        create_agent_run, execute_agent, submit_agent_position_to_council,
    )
    from evidence_memory.services.memory import create_memory_from_agent_run, search_similar

    agent_entry = next((a for a in OPERATIONAL_AGENTS if slugify(a['name']) == agent_slug), None)
    target_reference = f'ai_agent_workbench.agent:{agent_slug}:{case_slug or ""}'
    run = _start_run(
        'ai_analysis', f'{agent_entry["name"] if agent_entry else agent_slug} — {case_slug or "standalone"}',
        target_reference, self.request,
        task_kwargs={
            'agent_slug': agent_slug, 'case_slug': case_slug, 'execution_mode': execution_mode,
            'company_profile_id': company_profile_id, 'country_slug': country_slug,
        },
    )

    if agent_entry is None:
        run.mark_failed(f'"{agent_slug}" is not a real operational agent slug.')
        return {'status': 'failed', 'reason': 'unknown_agent'}

    company = None
    if company_profile_id is not None:
        from companies.models import CompanyProfile
        company = CompanyProfile.objects.filter(pk=company_profile_id).first()
    country = None
    if country_slug:
        from countries.models import CountryProfile
        country = CountryProfile.objects.filter(slug=country_slug).first()

    demo_case = demo_cases.get_demo_case(case_slug) if case_slug else None
    council_run = demo_cases.council_run_for_case(demo_case) if demo_case else None

    base_input = input_summary or f'Background analysis requested via Celery task {self.request.id}.'
    memory_query = input_summary or (demo_case['question'] if demo_case else agent_entry['name'])
    relevant_memories = search_similar(memory_query, top_k=3, company=company, country=country)
    memory_ids = [m.pk for m in relevant_memories]
    if relevant_memories:
        memory_context = '\n'.join(f'- {m.text_chunk}' for m in relevant_memories)
        full_input_summary = f'{base_input}\n\nRelevant prior evidence (from EcoIQ memory):\n{memory_context}'
    else:
        full_input_summary = base_input

    task_type = f'background_analysis_{agent_slug}'
    agent_run = create_agent_run(
        agent_entry['name'], task_type, council_case=council_run, execution_mode=execution_mode,
        input_summary=full_input_summary,
    )
    agent_run = execute_agent(agent_run)

    council_task_id = None
    if agent_run.status == 'completed' and agent_run.schema_valid and council_run is not None:
        next_order = council_run.tasks.count() + 1
        council_task = submit_agent_position_to_council(agent_run, collaboration_mode='solo', order=next_order)
        council_task_id = council_task.pk

    memory_saved_id = None
    if agent_run.status in ('completed', 'needs_human_review') and agent_run.parsed_output:
        memory_saved_id = create_memory_from_agent_run(agent_run, company=company, country=country).pk

    result_summary = {
        'agent_run_id': agent_run.pk, 'agent_run_status': agent_run.status,
        'schema_valid': agent_run.schema_valid, 'safety_status': agent_run.safety_status,
        'council_task_id': council_task_id,
        'memories_retrieved': memory_ids, 'memory_saved_id': memory_saved_id,
    }

    if agent_run.status == 'failed':
        run.result_summary = result_summary
        run.mark_failed(agent_run.failure_reason or 'Agent execution failed.')
        return {'status': 'failed', **result_summary}

    run.mark_completed(result_summary)
    return {'status': 'completed', **result_summary}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=60,
             max_retries=2, retry_jitter=True)
def refresh_evidence_memory(self, company_profile_id, limit=50):
    """
    Evidence Memory Refresh — reuses evidence_memory.services.memory.
    create_memory_from_evidence() over a company's real, already-harvested
    and deduplicated harvester.Evidence rows. `limit` bounds the batch size
    (cost control: this never processes "every company's every evidence
    row" in one task — see Backend Intelligence Engine's own cost-control
    precedent). Idempotent — re-running just updates existing memory rows
    for evidence already seen (get_or_create on source_reference).
    """
    from companies.models import CompanyProfile
    from evidence_memory.services.memory import create_memory_from_evidence
    from harvester.models import Evidence

    target_reference = f'evidence_memory.company:{company_profile_id}'
    try:
        profile = CompanyProfile.objects.get(pk=company_profile_id)
    except CompanyProfile.DoesNotExist:
        run = _start_run(
            'evidence_memory_refresh', f'CompanyProfile #{company_profile_id} (not found)',
            target_reference, self.request, task_kwargs={'company_profile_id': company_profile_id, 'limit': limit},
        )
        run.mark_failed(f'CompanyProfile {company_profile_id} does not exist.')
        return {'status': 'failed', 'reason': 'not_found'}

    run = _start_run(
        'evidence_memory_refresh', profile.company.name if profile.company_id else f'Profile #{profile.pk}',
        target_reference, self.request, task_kwargs={'company_profile_id': company_profile_id, 'limit': limit},
    )

    evidence_qs = Evidence.objects.filter(company=profile).order_by('-retrieved_at')[:limit]
    embedded, failed = 0, 0
    for evidence in evidence_qs:
        memory = create_memory_from_evidence(evidence)
        if memory.embedding_status == 'embedded':
            embedded += 1
        else:
            failed += 1

    result_summary = {'evidence_processed': embedded + failed, 'embedded': embedded, 'failed': failed}
    run.mark_completed(result_summary)
    return {'status': 'completed', **result_summary}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=60,
             max_retries=2, retry_jitter=True)
def recalculate_scores_background(self, company_profile_id=None, limit=25):
    """
    Intelligence Score Recalculation — reuses pandas_scoring_engine.services.
    scoring.compute_company_intelligence_score() exactly as the management
    command does, and records each result as a new CompanyScoreSnapshot (not
    a new/duplicate scoring model). `limit` bounds the batch when no single
    company_profile_id is given (cost control — never "every company" by
    accident; matches recalculate_ecoiq_scores' own default).
    """
    from companies.models import CompanyProfile, CompanyScoreSnapshot
    from pandas_scoring_engine.services.scoring import compute_company_intelligence_score

    if company_profile_id is not None:
        queryset = CompanyProfile.objects.filter(pk=company_profile_id).select_related('company')
        target_reference = f'companies.CompanyProfile:{company_profile_id}'
        target_repr_default = f'CompanyProfile #{company_profile_id}'
    else:
        queryset = CompanyProfile.objects.filter(status__in=('public', 'verified')).select_related('company')[:limit]
        target_reference = f'companies.CompanyProfile:batch:{limit}'
        target_repr_default = f'Batch of up to {limit} companies'

    run = _start_run(
        'intelligence_score_recalculation', target_repr_default, target_reference, self.request,
        task_kwargs={'company_profile_id': company_profile_id, 'limit': limit},
    )

    if company_profile_id is not None and not queryset.exists():
        run.mark_failed(f'CompanyProfile {company_profile_id} does not exist.')
        return {'status': 'failed', 'reason': 'not_found'}

    processed, snapshot_ids = 0, []
    for profile in queryset:
        scores = compute_company_intelligence_score(profile)
        snapshot = CompanyScoreSnapshot.create_from_profile(
            profile, trigger='intelligence_score_recalc',
            notes=f'Background recalculation (Celery task {self.request.id}).',
            intelligence_scores=scores,
        )
        snapshot_ids.append(snapshot.pk)
        processed += 1

    result_summary = {'companies_processed': processed, 'snapshot_ids': snapshot_ids}
    run.mark_completed(result_summary)
    return {'status': 'completed', **result_summary}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=60,
             max_retries=2, retry_jitter=True)
def run_langgraph_intelligence_workflow(self, user_request='', target_id=None, target_type=None,
                                         latitude=None, longitude=None, execution_mode='deterministic_test'):
    """
    LangGraph Intelligence Workflow — reuses langgraph_orchestration.graph.
    run_orchestration() exactly; this task's only job is Celery-level
    tracking (BackgroundTaskRun) plus a langgraph_orchestration.models.
    OrchestrationRun row for graph-level detail (which nodes ran, which one
    failed, the full structured result) — the orchestrator itself contains
    no scoring/evidence/geo/agent logic of its own, every node it runs calls
    an existing service.

    A raised exception from run_orchestration() itself (as opposed to a node
    inside the graph failing, which the graph already catches per-node) is
    genuinely unexpected — this task's own autoretry/BackgroundTaskRun
    failure path still applies, same as every other task in this module.
    """
    from langgraph_orchestration.graph import run_orchestration
    from langgraph_orchestration.models import OrchestrationRun

    target_reference = f'langgraph_orchestration:{target_type or "location"}:{target_id or f"{latitude},{longitude}"}'
    run = _start_run(
        'langgraph_intelligence_workflow', user_request[:80] or 'Untitled request',
        target_reference, self.request,
        task_kwargs={
            'user_request': user_request, 'target_id': target_id, 'target_type': target_type,
            'latitude': latitude, 'longitude': longitude, 'execution_mode': execution_mode,
        },
    )

    orchestration_run = OrchestrationRun.objects.create(
        user_request=user_request, target_type=target_type or 'unknown',
        target_reference=target_reference, celery_task_id=self.request.id or '',
    )

    final_state = run_orchestration(
        user_request=user_request, target_id=target_id, target_type=target_type,
        latitude=latitude, longitude=longitude, execution_mode=execution_mode,
    )

    target_repr = (final_state.get('company') or final_state.get('country') or {}).get('name', final_state.get('target_type', ''))
    orchestration_run.target_repr = target_repr
    orchestration_run.mark_completed(final_state)

    result_summary = {
        'orchestration_run_id': orchestration_run.pk, 'status': final_state.get('status'),
        'confidence': final_state.get('confidence'), 'nodes_executed': final_state.get('nodes_executed'),
        'failed_node': final_state.get('failed_node'),
    }

    if final_state.get('status') == 'failed':
        run.result_summary = result_summary
        run.mark_failed(f'Graph node "{final_state.get("failed_node")}" failed — see OrchestrationRun #{orchestration_run.pk}.')
        return {'status': 'failed', **result_summary}

    run.mark_completed(result_summary)
    return {'status': 'completed', **result_summary}


# Cost control: never ingest an unbounded number of sources in one task run.
INGEST_ENABLED_SOURCES_LIMIT = 20


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=60,
             max_retries=2, retry_jitter=True)
def ingest_source(self, source_id):
    """
    Data Ingestion Engine — fetches, validates, deduplicates and stores
    evidence for ONE harvester.Source row, reusing harvester.services.
    ingestion_pipeline.ingest_source() exactly (no duplicate fetch/dedup
    logic here). Records both a BackgroundTaskRun (this Celery task's own
    lifecycle) and a harvester.IngestionRun (what the fetch actually found)
    — two different, complementary granularities, matching the same pattern
    already used for OrchestrationRun alongside BackgroundTaskRun.
    """
    from harvester.models import Source
    from harvester.services.ingestion_pipeline import ingest_source as run_ingestion

    target_reference = f'harvester.Source:{source_id}'
    try:
        source = Source.objects.select_related('company__company').get(pk=source_id)
    except Source.DoesNotExist:
        run = _start_run(
            'ingest_source', f'Source #{source_id} (not found)', target_reference, self.request,
            task_kwargs={'source_id': source_id},
        )
        run.mark_failed(f'Source {source_id} does not exist.')
        return {'status': 'failed', 'reason': 'not_found'}

    run = _start_run(
        'ingest_source', source.name, target_reference, self.request, task_kwargs={'source_id': source_id},
    )

    ingestion_run = run_ingestion(source, triggered_by=f'celery:{self.request.id}')
    result_summary = {
        'ingestion_run_id': ingestion_run.pk, 'ingestion_status': ingestion_run.status,
        'evidence_created': ingestion_run.evidence_created_count, 'evidence_updated': ingestion_run.evidence_updated_count,
        'memory_records_created': ingestion_run.memory_records_created,
    }

    if ingestion_run.status == 'failed':
        run.result_summary = result_summary
        run.mark_failed(ingestion_run.error_message or 'Ingestion failed.')
        return {'status': 'failed', **result_summary}

    run.mark_completed(result_summary)
    return {'status': 'completed', **result_summary}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=60,
             max_retries=2, retry_jitter=True)
def ingest_enabled_sources(self, limit=INGEST_ENABLED_SOURCES_LIMIT):
    """
    Batch ingestion — iterates enabled harvester.Source rows, calling
    ingest_source's own pipeline for each. `limit` bounds the batch (cost
    control, matches every other batch task in this module) — never "every
    source" unboundedly.
    """
    from harvester.models import Source
    from harvester.services.ingestion_pipeline import ingest_source as run_ingestion

    sources = Source.objects.filter(is_active=True).select_related('company__company')[:limit]
    target_reference = f'harvester.Source:batch:{limit}'
    run = _start_run(
        'ingest_enabled_sources', f'Batch of up to {limit} enabled sources', target_reference, self.request,
        task_kwargs={'limit': limit},
    )

    outcomes = {'new': 0, 'updated': 0, 'unchanged': 0, 'failed': 0, 'skipped': 0}
    ingestion_run_ids = []
    for source in sources:
        ingestion_run = run_ingestion(source, triggered_by=f'celery:{self.request.id}')
        outcomes[ingestion_run.status] += 1
        ingestion_run_ids.append(ingestion_run.pk)

    result_summary = {'sources_processed': len(sources), 'outcomes': outcomes, 'ingestion_run_ids': ingestion_run_ids}
    run.mark_completed(result_summary)
    return {'status': 'completed', **result_summary}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=60,
             max_retries=2, retry_jitter=True)
def refresh_entity_evidence(self, company_profile_id):
    """
    Downstream-refresh eligibility — ingests every enabled Source linked to
    one company, and ONLY when genuinely new or updated evidence resulted,
    queues the existing, already-built downstream refresh (score
    recalculation) rather than running it unconditionally. This is the
    explicit "do not automatically run the entire expensive pipeline after
    every tiny change" eligibility rule the spec requires — an
    'unchanged'/'failed'/'skipped' outcome never triggers a recalculation.
    """
    from companies.models import CompanyProfile
    from harvester.models import Source
    from harvester.services.ingestion_pipeline import ingest_source as run_ingestion

    target_reference = f'companies.CompanyProfile:{company_profile_id}'
    try:
        profile = CompanyProfile.objects.select_related('company').get(pk=company_profile_id)
    except CompanyProfile.DoesNotExist:
        run = _start_run(
            'refresh_entity_evidence', f'CompanyProfile #{company_profile_id} (not found)',
            target_reference, self.request, task_kwargs={'company_profile_id': company_profile_id},
        )
        run.mark_failed(f'CompanyProfile {company_profile_id} does not exist.')
        return {'status': 'failed', 'reason': 'not_found'}

    run = _start_run(
        'refresh_entity_evidence', profile.company.name if profile.company_id else f'Profile #{profile.pk}',
        target_reference, self.request, task_kwargs={'company_profile_id': company_profile_id},
    )

    sources = Source.objects.filter(company=profile, is_active=True)
    genuinely_changed = False
    ingestion_run_ids = []
    for source in sources:
        ingestion_run = run_ingestion(source, triggered_by=f'celery:{self.request.id}')
        ingestion_run_ids.append(ingestion_run.pk)
        if ingestion_run.status in ('new', 'updated'):
            genuinely_changed = True

    scoring_task_id = None
    if genuinely_changed:
        recalculate_scores_background.delay(company_profile_id=profile.pk)
        scoring_task_id = 'queued'

    result_summary = {
        'sources_ingested': len(ingestion_run_ids), 'ingestion_run_ids': ingestion_run_ids,
        'genuinely_changed': genuinely_changed, 'score_recalculation': scoring_task_id,
    }
    run.mark_completed(result_summary)
    return {'status': 'completed', **result_summary}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=60,
             max_retries=2, retry_jitter=True)
def run_agent_evaluation(self, agent_id, evaluation_version='v1'):
    """
    Agent Evaluation Engine — reuses agent_training_evaluation_lab.services.
    evaluation_engine.run_agent_evaluation() exactly: computes real metrics
    from the agent's already-persisted AgentRun history, never runs a new
    agent execution itself. Recorded via the same BackgroundTaskRun pattern
    as every other task in this module.
    """
    from agent_runtime_model_router.models import AgentRegistryEntry
    from agent_training_evaluation_lab.services.evaluation_engine import run_agent_evaluation as run_evaluation

    target_reference = f'agent_runtime_model_router.AgentRegistryEntry:{agent_id}'
    try:
        entry = AgentRegistryEntry.objects.get(pk=agent_id)
    except AgentRegistryEntry.DoesNotExist:
        run = _start_run(
            'run_agent_evaluation', f'AgentRegistryEntry #{agent_id} (not found)', target_reference, self.request,
            task_kwargs={'agent_id': agent_id, 'evaluation_version': evaluation_version},
        )
        run.mark_failed(f'AgentRegistryEntry {agent_id} does not exist.')
        return {'status': 'failed', 'reason': 'not_found'}

    run = _start_run(
        'run_agent_evaluation', entry.agent_name, target_reference, self.request,
        task_kwargs={'agent_id': agent_id, 'evaluation_version': evaluation_version},
    )

    evaluation = run_evaluation(entry, evaluation_version=evaluation_version)
    result_summary = {
        'evaluation_run_id': evaluation.pk, 'overall_score': evaluation.overall_score,
        'runs_evaluated_count': evaluation.runs_evaluated_count,
        'golden_cases_passed': evaluation.golden_cases_passed, 'golden_cases_checked': evaluation.golden_cases_checked,
    }
    run.mark_completed(result_summary)
    return {'status': 'completed', **result_summary}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=60,
             max_retries=2, retry_jitter=True)
def detect_agent_regressions(self, evaluation_run_id):
    """
    Regression Detection — reuses agent_training_evaluation_lab.services.
    regression_detection.detect_regressions() exactly. Never modifies the
    agent, its training pack, or any production configuration — a
    regression is a human-observable AgentRegression row only.
    """
    from agent_training_evaluation_lab.models import AgentEvaluationRun
    from agent_training_evaluation_lab.services.regression_detection import detect_regressions

    target_reference = f'agent_training_evaluation_lab.AgentEvaluationRun:{evaluation_run_id}'
    try:
        evaluation = AgentEvaluationRun.objects.select_related('agent').get(pk=evaluation_run_id)
    except AgentEvaluationRun.DoesNotExist:
        run = _start_run(
            'detect_agent_regressions', f'AgentEvaluationRun #{evaluation_run_id} (not found)', target_reference,
            self.request, task_kwargs={'evaluation_run_id': evaluation_run_id},
        )
        run.mark_failed(f'AgentEvaluationRun {evaluation_run_id} does not exist.')
        return {'status': 'failed', 'reason': 'not_found'}

    run = _start_run(
        'detect_agent_regressions', evaluation.agent.agent_name, target_reference, self.request,
        task_kwargs={'evaluation_run_id': evaluation_run_id},
    )

    findings = detect_regressions(evaluation)
    result_summary = {'regressions_found': len(findings), 'regression_ids': [f.pk for f in findings]}
    run.mark_completed(result_summary)
    return {'status': 'completed', **result_summary}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=60,
             max_retries=2, retry_jitter=True)
def run_agent_benchmark(self, agent_id, evaluation_version='v1'):
    """
    Agent Benchmarking — the combined workflow: evaluate, then detect
    regressions against the immediately-prior evaluation, then generate
    improvement recommendations. Reuses run_agent_evaluation +
    detect_agent_regressions (this same module) and agent_training_
    evaluation_lab.services.recommendations.generate_recommendations() —
    no separate benchmarking execution path.
    """
    from agent_runtime_model_router.models import AgentRegistryEntry
    from agent_training_evaluation_lab.services.evaluation_engine import run_agent_evaluation as run_evaluation
    from agent_training_evaluation_lab.services.recommendations import generate_recommendations
    from agent_training_evaluation_lab.services.regression_detection import detect_regressions

    target_reference = f'agent_runtime_model_router.AgentRegistryEntry:{agent_id}'
    try:
        entry = AgentRegistryEntry.objects.get(pk=agent_id)
    except AgentRegistryEntry.DoesNotExist:
        run = _start_run(
            'run_agent_benchmark', f'AgentRegistryEntry #{agent_id} (not found)', target_reference, self.request,
            task_kwargs={'agent_id': agent_id, 'evaluation_version': evaluation_version},
        )
        run.mark_failed(f'AgentRegistryEntry {agent_id} does not exist.')
        return {'status': 'failed', 'reason': 'not_found'}

    run = _start_run(
        'run_agent_benchmark', entry.agent_name, target_reference, self.request,
        task_kwargs={'agent_id': agent_id, 'evaluation_version': evaluation_version},
    )

    evaluation = run_evaluation(entry, evaluation_version=evaluation_version)
    regressions = detect_regressions(evaluation)
    recommendations = generate_recommendations(evaluation)

    result_summary = {
        'evaluation_run_id': evaluation.pk, 'overall_score': evaluation.overall_score,
        'score_delta': evaluation.score_delta.get('overall_score'),
        'regressions_found': len(regressions), 'recommendations_generated': len(recommendations),
    }
    run.mark_completed(result_summary)
    return {'status': 'completed', **result_summary}
