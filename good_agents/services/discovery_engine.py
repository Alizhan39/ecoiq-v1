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
from good_agents.models import GoodDiscoveryRun, GoodOpportunity
from good_agents.services import (
    agent_groups, circular_economy, clustering, evidence_gate, funding_matcher, matcher, morning_brief,
    need_resource, prioritisation, signals as signal_service, zero_capital_strategy,
)
from good_agents.services.orchestrator import Signal, classify_relevant_agents, record_activations, run_deep_reasoning
from good_agents.services.pipeline import qualify_opportunity

PROBLEM_SIGNAL_TYPES = frozenset({'need', 'harm', 'waste', 'risk', 'emergency', 'opportunity'})
RESOURCE_SIGNAL_TYPES = frozenset({'resource', 'funding'})
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
    """Returns 'problem', 'resource', or 'noise'. A cluster can be both problem and resource-bearing; problem wins."""
    signal_types = {s.signal_type for s in cluster.signals.all()}
    if signal_types & PROBLEM_SIGNAL_TYPES:
        return 'problem'
    if signal_types & RESOURCE_SIGNAL_TYPES:
        return 'resource'
    max_severity = max((s.severity for s in cluster.signals.all()), default=0.0)
    if signal_types & NOISE_SIGNAL_TYPES and max_severity < NOISE_SEVERITY_ESCALATION_THRESHOLD:
        return 'noise'
    return 'noise'


def _resource_type_from_signal(signal):
    """
    A raw signal can carry an explicit `resource_type:xxx` tag (set by
    whoever supplied it — a provider adaptor or a demo/test fixture) to
    avoid guessing a resource type from free text. Falls back to a
    conservative default by signal_type when no explicit tag is present.
    """
    for tag in signal.tags:
        if tag.startswith('resource_type:'):
            return tag.split(':', 1)[1]
    return 'government_programme' if signal.signal_type == 'funding' else 'technology'


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
    run, created = _get_or_create_run(mission_config, idempotency_key)
    if not created and run.status == 'completed':
        return run, morning_brief.build_brief(run)

    run.mark_running()
    builder = opportunity_builder or _default_opportunity_from_cluster

    try:
        # --- FETCH_SIGNALS + NORMALISE -------------------------------------------------
        new_signals = []
        if not run.stage_done('normalise'):
            for raw in raw_signals:
                signal, was_created = signal_service.normalise_signal(raw)
                if was_created:
                    new_signals.append(signal)
                run.signals_reviewed += 1
            run.checkpoint('fetch_signals')
            run.checkpoint('normalise')
        else:
            new_signals = list(signal_service.WorldSignal.objects.filter(status='new'))

        # --- DEDUPLICATE + CLUSTER ------------------------------------------------------
        if not run.stage_done('cluster'):
            result = clustering.deduplicate_and_cluster(new_signals)
            run.duplicates_removed += result['duplicates_removed']
            clusters = result['clusters']
            run.checkpoint('deduplicate')
            run.checkpoint('cluster')
        else:
            from good_agents.models import SignalCluster
            clusters = list(SignalCluster.objects.filter(status='open'))

        # --- TRIAGE -----------------------------------------------------------------
        problem_clusters, resource_clusters, noise_clusters = [], [], []
        for cluster in clusters:
            kind = _triage_cluster(cluster)
            if kind == 'problem':
                problem_clusters.append(cluster)
            elif kind == 'resource':
                resource_clusters.append(cluster)
                _register_resource_from_cluster(cluster)
                cluster.status = 'triaged'
                cluster.save(update_fields=['status', 'updated_at'])
            else:
                noise_clusters.append(cluster)
                cluster.status = 'discarded'
                cluster.save(update_fields=['status', 'updated_at'])
        run.checkpoint('triage')

        # --- ACTIVATE_AGENTS + VERIFY_EVIDENCE + CREATE_CANDIDATES ----------------------
        candidate_agents = None
        if mission_config.principle_ids:
            from good_agents.models import GoodAgentDefinition
            candidate_agents = GoodAgentDefinition.objects.filter(
                principle_id__in=mission_config.principle_ids, is_active=True,
            )

        created_opportunities = []
        for cluster in problem_clusters:
            lead_signal = cluster.signals.first()
            if lead_signal is None:
                continue
            signal = Signal(
                text=f'{lead_signal.title}. {lead_signal.summary}',
                domains=[lead_signal.sector] if lead_signal.sector else [],
                geography=lead_signal.region,
            )
            activations = classify_relevant_agents(signal, candidate_agents=candidate_agents)
            run.agents_activated += len(activations)
            for a in activations:
                a.agent.mark_activated()

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

        run.checkpoint('activate_agents')
        run.checkpoint('verify_evidence')
        run.checkpoint('create_candidates')

        # --- MATCH_RESOURCES ----------------------------------------------------------
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
        run.checkpoint('match_resources')

        # --- RUN_BETTER_WAY -------------------------------------------------------------
        # Deliberately delegated to the caller (see module docstring) — not every
        # discovered opportunity has a capital angle. This stage just marks that the
        # discovery engine reached the point where a caller CAN invoke
        # good_agents.services.pipeline.* for opportunities that do.
        run.checkpoint('run_better_way')

        # --- RANK -----------------------------------------------------------------------
        prioritisation.rank_opportunities(created_opportunities)
        run.checkpoint('rank')

        run.save()
        brief = morning_brief.build_brief(run)
        run.checkpoint('generate_brief')
        run.mark_completed()
        return run, brief
    except Exception as exc:
        run.save()
        run.mark_failed(str(exc))
        raise
