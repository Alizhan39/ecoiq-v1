"""
good_agents/services/discovery_engine.py — GlobalGoodDiscoveryEngine (PR3).

This is the NEW front door that gets a GoodOpportunity created without a
human submitting the problem by hand. It does NOT replace or rewrite
anything from PR2:

    - Orchestration (Layer 1-4 lens activation, deep reasoning) is still
      `good_agents.services.orchestrator` — called here unchanged.
    - Qualification (RedTeamReview + default GoodDeedActions) is still
      `good_agents.services.pipeline.qualify_opportunity` — called here
      unchanged.
    - Better Way / Capital Guardian / MRV / ImpactReceipt / Evidence Memory
      remain a SEPARATE, opt-in step a caller invokes afterwards on a
      qualified opportunity that has a real capital angle — exactly the
      pattern the Almaty demo command already uses. This engine does not
      auto-invoke that chain, because not every discovered opportunity has
      (or needs) one — a zero-capital NGO/food-surplus match never touches
      OperationalLoss at all.

`good_agents.services.discovery_run.run_discovery` (PR2) is UNCHANGED and
still used by `run_almaty_good_agent_demo` — this module is additive.

Stages (PR3 Phase 13), each checkpointed on the GoodDiscoveryRun so a
second call with the same idempotency_key resumes rather than redoing
work:

    fetch_signals -> normalise -> deduplicate -> cluster -> triage
    -> activate_agents -> verify_evidence -> create_candidates
    -> match_resources -> run_better_way -> rank -> generate_brief
"""
from good_agents.models import GoodAgentDefinition, GoodDiscoveryRun, GoodOpportunity
from good_agents.services import (
    agent_groups, circular_economy, clustering, evidence_gate, funding_matcher, matcher, morning_brief,
    need_resource, notify, prioritisation, signals as signal_service, zero_capital_strategy,
)
from good_agents.services.orchestrator import Signal, classify_relevant_agents, record_activations, run_deep_reasoning
from good_agents.services.pipeline import qualify_opportunity

PROBLEM_SIGNAL_TYPES = frozenset({
    'need', 'harm', 'waste', 'risk', 'emergency', 'opportunity',
    # PR4 Phase 3 — real-world signal classes from real SignalProvider adapters.
    'public_need', 'environmental_risk', 'infrastructure_opportunity',
    'waste_or_unused_resource', 'community_need',
})
RESOURCE_SIGNAL_TYPES = frozenset({'resource', 'funding', 'resource_available', 'funding_available'})
NOISE_SIGNAL_TYPES = frozenset({'policy_change', 'technology_change', 'price_change'})
NOISE_SEVERITY_ESCALATION_THRESHOLD = 70.0

THEME_TO_NEED_TYPE = {
    'energy': 'energy', 'water': 'water', 'food': 'food', 'housing': 'housing', 'health': 'health',
    'education': 'education', 'employment': 'employment', 'poverty': 'financial_inclusion',
    'justice': 'justice', 'environment': 'environment', 'biodiversity': 'biodiversity', 'waste': 'waste',
    'circular_economy': 'waste', 'climate_adaptation': 'climate', 'infrastructure': 'infrastructure',
    'government_efficiency': 'justice', 'financial_inclusion': 'financial_inclusion',
    'digital_access': 'digital_access', 'community_resilience': 'community_resilience',
}


def _get_or_create_run(mission_config, idempotency_key):
    if idempotency_key:
        run, created = GoodDiscoveryRun.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults=dict(
                mission=mission_config.name, mission_config=mission_config,
                geography=', '.join(mission_config.geographies), themes=mission_config.themes,
                capital_budget_usd=mission_config.capital_budget_usd,
                cost_budget_usd=mission_config.run_cost_budget_usd,
            ),
        )
        return run, created
    run = GoodDiscoveryRun.objects.create(
        mission=mission_config.name, mission_config=mission_config,
        geography=', '.join(mission_config.geographies), themes=mission_config.themes,
        capital_budget_usd=mission_config.capital_budget_usd, cost_budget_usd=mission_config.run_cost_budget_usd,
    )
    return run, True


def _triage_cluster(cluster):
    """
    Returns 'problem', 'resource', 'needs_review', or 'noise'. A cluster
    can be both problem and resource-bearing; problem wins. 'unknown'-typed
    signals never get silently discarded as noise — Phase 3 explicitly asks
    for NEEDS_REVIEW rather than a forced classification when evidence is
    insufficient to say more; a human, not this triage step, resolves them.
    """
    signal_types = {s.signal_type for s in cluster.signals.all()}
    if signal_types & PROBLEM_SIGNAL_TYPES:
        return 'problem'
    if signal_types & RESOURCE_SIGNAL_TYPES:
        return 'resource'
    if 'unknown' in signal_types:
        return 'needs_review'
    max_severity = max((s.severity for s in cluster.signals.all()), default=0.0)
    if signal_types & NOISE_SIGNAL_TYPES and max_severity < NOISE_SEVERITY_ESCALATION_THRESHOLD:
        return 'noise'
    return 'noise'


FUNDING_SIGNAL_TYPES = frozenset({'funding', 'funding_available'})


def _resource_type_from_signal(signal):
    """
    A raw signal can carry an explicit `resource_type:xxx` tag (set by
    whoever supplied it — a provider adaptor or a demo/test fixture) to
    avoid guessing a resource type from free text. Falls back to a
    conservative default by signal_type when no explicit tag is present.
    Must recognise BOTH the original PR3 signal types ('funding') and
    PR4's real-world ones ('funding_available') — a real bug caught during
    PR4 development: real GOV.UK funding signals were silently defaulting
    to resource_type='technology' here, which then bypassed the
    promiscuous-type keyword-relevance check in services/matcher.py
    entirely (a 'technology' match doesn't require it), letting an
    earthquake match an unrelated home-energy grant purely on category.
    """
    for tag in signal.tags:
        if tag.startswith('resource_type:'):
            return tag.split(':', 1)[1]
    return 'government_programme' if signal.signal_type in FUNDING_SIGNAL_TYPES else 'technology'


def _register_resource_from_cluster(cluster):
    signal = cluster.signals.first()
    if signal is None:
        return None
    resource_type = _resource_type_from_signal(signal)
    availability = 'available' if signal.raw_evidence_ref else 'unknown'
    resource, _ = need_resource.create_resource(
        resource_type=resource_type, title=signal.title, geography=signal.geography, region=signal.region,
        availability=availability, source=signal.publisher,
        evidence_refs=[signal.raw_evidence_ref] if signal.raw_evidence_ref else [],
        confidence=signal.confidence,
    )
    return resource


def _default_opportunity_from_cluster(cluster, activations, gate_result, mission_config):
    signals = list(cluster.signals.all())
    lead_signal = signals[0]
    theme = next(iter(lead_signal.tags), '') if lead_signal.tags else ''
    if theme not in dict(GoodOpportunity._meta.get_field('theme').choices):
        theme = ''

    opportunity = GoodOpportunity.objects.create(
        title=cluster.representative_title,
        theme=theme,
        problem_statement=' '.join(s.summary or s.title for s in signals),
        geography=lead_signal.geography,
        region=lead_signal.region,
        sector=lead_signal.sector,
        affected_population=lead_signal.potential_affected_population,
        detected_signals=[s.title for s in signals],
        relevant_principle_ids=[a.agent.principle_id for a in activations],
        evidence_refs=[s.raw_evidence_ref for s in signals if s.raw_evidence_ref],
        insufficient_evidence=(gate_result.decision in ('monitor', 'insufficient_evidence')),
        confidence=gate_result.confidence,
        urgency=max((s.severity for s in signals), default=0.0),
        status='potential',
    )
    return opportunity


def run_global_discovery(mission_config, raw_signals, *, execution_mode='simulated_demo',
                         opportunity_builder=None, fixture_output=None, idempotency_key=None):
    """
    mission_config: a GoodMission row.
    raw_signals: list of plain dicts (see services/signals.normalise_signal for shape).
    opportunity_builder(cluster, activations, gate_result, mission_config) -> GoodOpportunity | None
        optional override for how a qualifying cluster becomes a GoodOpportunity.

    Returns (run, brief_dict).
    """
    from ai_observatory.services.recorder import finish_session, record_stage, start_session

    run, created = _get_or_create_run(mission_config, idempotency_key)
    if not created and run.status == 'completed':
        return run, morning_brief.build_brief(run)

    run.mark_running()
    builder = opportunity_builder or _default_opportunity_from_cluster

    # Reuses the existing AI Observatory telemetry system (Phase 7 — "no
    # second telemetry system"). A discovery run has no single GoldProject/
    # CompanyProfile to anchor to, so 'good_agents_discovery' was added to
    # ai_observatory.models.NO_ANCHOR_ALLOWED_KINDS, the same mechanism
    # already used for cross-company discovery/review-workbench sessions.
    observatory_session = start_session(kind='good_agents_discovery', human_review_required=True)
    if observatory_session is not None and not run.stage_checkpoints.get('_observatory_session_reference'):
        run.stage_checkpoints = {**run.stage_checkpoints, '_observatory_session_reference': f'ai_observatory.AnalysisSession:{observatory_session.pk}'}
        run.save(update_fields=['stage_checkpoints'])

    try:
        # --- FETCH_SIGNALS + NORMALISE -------------------------------------------------
        new_signals = []
        if not run.stage_done('normalise'):
            with record_stage(observatory_session, 'fetch_normalise', 'Fetch + Normalise Signals', category='retrieval') as info:
                for raw in raw_signals:
                    # Real ingestion (services/ingestion.py) tags each raw dict with the
                    # actual SignalProvider instance that supplied it; fixture/demo
                    # signals simply omit this key and normalise as provider=None.
                    provider = raw.pop('_provider', None)
                    signal, was_created = signal_service.normalise_signal(raw, provider=provider)
                    if was_created:
                        new_signals.append(signal)
                    run.signals_reviewed += 1
                info['items_processed'] = len(raw_signals)
            run.checkpoint('fetch_signals')
            run.checkpoint('normalise')
        else:
            new_signals = list(signal_service.WorldSignal.objects.filter(status='new'))

        # --- DEDUPLICATE + CLUSTER ------------------------------------------------------
        from good_agents.models import SignalCluster
        if not run.stage_done('cluster'):
            with record_stage(observatory_session, 'deduplicate_cluster', 'Deduplicate + Cluster', category='deterministic') as info:
                result = clustering.deduplicate_and_cluster(new_signals)
                run.duplicates_removed += result['duplicates_removed']
                info['items_processed'] = len(result['clusters'])
                info['metadata'] = {'duplicates_removed': result['duplicates_removed']}
            run.checkpoint('deduplicate')
            run.checkpoint('cluster')
        # Always re-derive the working set from every 'open' cluster, not just
        # the ones freshly created by THIS call's new_signals — lets a second
        # GoodMission in the same command invocation (e.g.
        # run_good_while_you_sleep serving several missions from one fetch)
        # reconsider a cluster an earlier mission's triage saw but didn't
        # claim (left 'open': noise clusters are claimed/'discarded', matched
        # problem/resource clusters are claimed/'triaged' — only 'needs_review'
        # and not-yet-triaged clusters stay open for a later mission).
        clusters = list(SignalCluster.objects.filter(status='open'))

        # --- TRIAGE -----------------------------------------------------------------
        problem_clusters, resource_clusters, noise_clusters, needs_review_clusters = [], [], [], []
        with record_stage(observatory_session, 'triage', 'Triage: Problem / Resource / Noise', category='deterministic') as info:
            for cluster in clusters:
                kind = _triage_cluster(cluster)
                if kind == 'problem':
                    problem_clusters.append(cluster)
                elif kind == 'resource':
                    resource_clusters.append(cluster)
                    _register_resource_from_cluster(cluster)
                    cluster.status = 'triaged'
                    cluster.save(update_fields=['status', 'updated_at'])
                elif kind == 'needs_review':
                    # Left 'open', not 'discarded' — a human, not this triage step,
                    # decides whether an unclassifiable signal matters (Phase 3).
                    needs_review_clusters.append(cluster)
                else:
                    noise_clusters.append(cluster)
                    cluster.status = 'discarded'
                    cluster.save(update_fields=['status', 'updated_at'])
            info['items_processed'] = len(clusters)
            info['metadata'] = {
                'problem': len(problem_clusters), 'resource': len(resource_clusters),
                'noise_rejected': len(noise_clusters), 'needs_review': len(needs_review_clusters),
            }
        run.checkpoint('triage')

        # --- ACTIVATE_AGENTS + VERIFY_EVIDENCE + CREATE_CANDIDATES ----------------------
        candidate_agents = None
        if mission_config.principle_ids:
            candidate_agents = GoodAgentDefinition.objects.filter(
                principle_id__in=mission_config.principle_ids, is_active=True,
            )

        created_opportunities = []
        agents_considered_count = 0
        for cluster in problem_clusters:
            lead_signal = cluster.signals.first()
            if lead_signal is None:
                continue
            signal = Signal(
                text=f'{lead_signal.title}. {lead_signal.summary}',
                domains=([lead_signal.sector] if lead_signal.sector else []) + list(lead_signal.tags),
                geography=lead_signal.region,
            )
            agents_considered_count += (
                candidate_agents.count() if candidate_agents is not None
                else GoodAgentDefinition.objects.filter(is_active=True).count()
            )
            activations = classify_relevant_agents(signal, candidate_agents=candidate_agents)
            run.agents_activated += len(activations)
            for a in activations:
                a.agent.mark_activated()

            if not activations:
                # No relevant principle lens found (Phase 6/18): this is a
                # valid, honest outcome, not an error — the signal simply
                # isn't a "Good Opportunity" for this framework. Never
                # create an opportunity with zero activated principles.
                # Left 'open' (not discarded) so a wider/future mission
                # (more principle_ids, or all 114) can reconsider it.
                continue

            gate_result = evidence_gate.evaluate_cluster(cluster)
            if gate_result.confidence < mission_config.min_confidence and gate_result.decision == 'qualify':
                gate_result.decision = 'monitor'
                gate_result.reason += f' (below mission min_confidence {mission_config.min_confidence:.0f}%)'

            if gate_result.decision == 'reject':
                run.rejected_opportunities += 1
                cluster.status = 'discarded'
                cluster.save(update_fields=['status', 'updated_at'])
                continue
            if gate_result.decision == 'insufficient_evidence':
                run.insufficient_evidence_count += 1
                continue
            if len(created_opportunities) >= mission_config.max_opportunities:
                continue

            deep_output, reasoning_metadata = run_deep_reasoning(
                signal, activations, execution_mode=execution_mode, fixture_output=fixture_output,
            )
            run.estimated_run_cost_usd += (reasoning_metadata or {}).get('estimated_cost_usd', 0.0) or 0.0
            if reasoning_metadata and not reasoning_metadata.get('skipped'):
                from ai_observatory.services.recorder import record_model_invocation
                record_model_invocation(
                    observatory_session,
                    provider=reasoning_metadata.get('model_provider', ''),
                    succeeded=reasoning_metadata.get('adapter_status', 'success') == 'success',
                )

            opportunity = builder(cluster, activations, gate_result, mission_config)
            if opportunity is None:
                continue
            opportunity.discovery_run = run
            opportunity.save(update_fields=['discovery_run', 'updated_at'])
            run.opportunities_detected += 1

            records = record_activations(opportunity, activations, deep_output, reasoning_metadata)
            qualify_opportunity(opportunity, records)
            if opportunity.status == 'qualified':
                run.qualified_opportunities += 1

            need_type = THEME_TO_NEED_TYPE.get(opportunity.theme, 'community_resilience')
            need, _ = need_resource.create_need(
                need_type=need_type, title=opportunity.title, opportunity=opportunity, signal=lead_signal,
                geography=opportunity.geography, region=opportunity.region,
                affected_group=opportunity.affected_population, urgency=opportunity.urgency,
                evidence_refs=opportunity.evidence_refs,
            )
            cluster.status = 'triaged'
            cluster.save(update_fields=['status', 'updated_at'])
            created_opportunities.append(opportunity)

        with record_stage(
            observatory_session, 'activate_verify_create', 'Activate Agents + Verify Evidence + Create Candidates',
            category='llm' if run.estimated_run_cost_usd > 0 else 'deterministic',
        ) as info:
            info['items_processed'] = len(created_opportunities)
            info['metadata'] = {
                'clusters_considered': len(problem_clusters), 'agents_considered': agents_considered_count,
                'agents_activated': run.agents_activated, 'opportunities_created': len(created_opportunities),
            }
        run.checkpoint('activate_agents')
        run.checkpoint('verify_evidence')
        run.checkpoint('create_candidates')

        # --- MATCH_RESOURCES ----------------------------------------------------------
        with record_stage(observatory_session, 'match_resources', 'Need/Resource/Funding/Zero-Capital Matching', category='deterministic') as info:
            for opportunity in created_opportunities:
                for need in opportunity.needs.all():
                    if need.need_type == 'waste':
                        circular_economy.match_circular_economy(need)
                    else:
                        matcher.match_need(need)
                zero_capital_strategy.rank_actions_for_opportunity(opportunity)
                funding_matcher.suggest_funding_matches(opportunity)
                if opportunity.zero_capital_possible:
                    run.zero_capital_opportunities += 1
            info['items_processed'] = len(created_opportunities)
        run.checkpoint('match_resources')

        # --- RUN_BETTER_WAY -------------------------------------------------------------
        # Deliberately delegated to the caller (see module docstring) — not every
        # discovered opportunity has a capital angle. This stage just marks that the
        # discovery engine reached the point where a caller CAN invoke
        # good_agents.services.pipeline.* for opportunities that do.
        run.checkpoint('run_better_way')

        # --- RANK -----------------------------------------------------------------------
        ranked = prioritisation.rank_opportunities(created_opportunities)
        run.checkpoint('rank')

        # Notifications (Phase 13) — reuses notifications.AdminNotification,
        # only for meaningful events, deduplicated per opportunity/reason.
        for opportunity, result in ranked:
            notify.notify_for_opportunity(opportunity, result)
        for opportunity in created_opportunities:
            for need in opportunity.needs.all():
                for match in need.matches.filter(confidence__gte=notify.STRONG_MATCH_CONFIDENCE_THRESHOLD):
                    notify.notify_for_strong_resource_match(match)

        run.save()
        brief = morning_brief.build_brief(run)
        run.checkpoint('generate_brief')
        run.mark_completed()
        finish_session(
            observatory_session, status='completed',
            final_recommendation_status='produced' if created_opportunities else 'not_applicable',
            human_review_completed=False,
        )
        return run, brief
    except Exception as exc:
        run.save()
        run.mark_failed(str(exc))
        finish_session(observatory_session, status='failed', warnings=[str(exc)])
        raise
