"""
good_agents/services/orchestrator.py — GoodAgentOrchestrator: signal in,
relevant Good Agent lenses activated out.

Layered cost control (Phase 2):

  Layer 1  deterministic filters             -- free, always runs, plain Python
  Layer 2  cheap scoring/ranking              -- still deterministic in this
                                                  slice; the seam where a real
                                                  cheap-tier LLM call would
                                                  plug in later without
                                                  changing Layer 3/4's
                                                  interface (marked PARTIAL —
                                                  see docs/GOOD_AGENTS_PROGRESS.md)
  Layer 3  select relevant lenses             -- top-N above a relevance
                                                  threshold, never all 114
  Layer 4  deep reasoning for promising cases -- ONE real
                                                  agent_runtime_model_router
                                                  call covering every
                                                  activated lens together,
                                                  not one call per lens
  Layer 5  human review before consequential  -- delegated to GoodDeedAction's
           action                                autonomy_class + the
                                                  existing
                                                  waste_to_value_capital_allocation_engine
                                                  human_approval_required gate
                                                  further down the pipeline;
                                                  nothing in this module can
                                                  act on its own.

This module never activates all rows of GoodAgentDefinition for one signal
— that is the explicit "do NOT create 114 expensive autonomous LLM loops"
requirement.
"""
from dataclasses import dataclass, field

from agent_runtime_model_router.services.cost_policy import check_cost_policy
from agent_runtime_model_router.services.model_adapters import get_adapter
from agent_runtime_model_router.services.model_router import select_model_route
from agent_runtime_model_router.services.safety_assertions import aggregate_safety_status, run_safety_assertions

from good_agents.models import AgentActivationRecord, GoodAgentDefinition


@dataclass
class Signal:
    """One observed real-world signal fed into the orchestrator."""
    text: str
    domains: list = field(default_factory=list)
    geography: str = ''
    urgency_hint: float = 50.0


@dataclass
class ActivationResult:
    agent: GoodAgentDefinition
    score: float
    reason: str


def _keyword_overlap_score(signal, agent_def):
    """Layer 1 — deterministic domain/signal-type overlap. No LLM, no cost."""
    haystack = signal.text.lower()
    signal_domains = {d.lower() for d in signal.domains}
    domain_hits = [d for d in agent_def.domains if d.lower() in signal_domains]
    signal_type_hits = [s for s in agent_def.signal_types if s.lower() in haystack]
    score = len(domain_hits) * 20 + len(signal_type_hits) * 15
    return score, domain_hits, signal_type_hits


def classify_relevant_agents(signal, candidate_agents=None, min_score=15, max_activated=6):
    """
    Layers 1+2: score every candidate GoodAgentDefinition against `signal`
    deterministically, keep only those at/above `min_score`, cap at
    `max_activated`. This is the control that prevents activating all 114
    lenses for every signal.
    """
    candidates = (
        candidate_agents if candidate_agents is not None
        else GoodAgentDefinition.objects.filter(is_active=True)
    )
    scored = []
    for agent_def in candidates:
        score, domain_hits, signal_type_hits = _keyword_overlap_score(signal, agent_def)
        if score >= min_score:
            reason_bits = []
            if domain_hits:
                reason_bits.append(f'domain match: {", ".join(domain_hits)}')
            if signal_type_hits:
                reason_bits.append(f'signal keywords: {", ".join(signal_type_hits)}')
            reason = '; '.join(reason_bits) or 'matched by default priority'
            scored.append(ActivationResult(agent=agent_def, score=score, reason=reason))
    scored.sort(key=lambda r: (-r.score, r.agent.default_priority))
    return scored[:max_activated]


def run_deep_reasoning(signal, activations, *, execution_mode='simulated_demo', cost_class='low',
                       fixture_output=None, estimated_cost_usd=0.01):
    """
    Layer 4 — one real agent_runtime_model_router call covering every
    activated lens at once. Returns (parsed_output_or_None, metadata_dict).

    `execution_mode='simulated_demo'` (the default here) routes to
    `SimulatedDemoAdapter`, which — like every other simulated-demo pipeline
    in this repo — only ever replays a hand-authored `fixture_output`; it
    never invents a result. Pass `execution_mode='live'` to use a real
    provider once credentials are configured.
    """
    route = select_model_route(
        agent_name='Good Agent Orchestrator',
        task_type='good_opportunity_reasoning',
        execution_mode=execution_mode,
        sensitivity_level='standard',
        requires_reasoning=True,
        cost_class=cost_class,
    )
    cost_check = check_cost_policy(estimated_cost_usd=estimated_cost_usd, council_case=None, cost_class=cost_class)
    if not cost_check.get('allowed', True):
        return None, {'route': route, 'cost_check': cost_check, 'skipped': True}

    adapter = get_adapter(route['selected_provider'])
    default_fixture = {
        'positions': [
            {'principle_id': a.agent.principle_id, 'position': 'support', 'confidence': min(90, 50 + a.score)}
            for a in activations
        ],
    }
    instruction = {
        'signal_text': signal.text,
        'geography': signal.geography,
        'activated_lenses': [
            {'principle_id': a.agent.principle_id, 'name': a.agent.name, 'mission': a.agent.mission}
            for a in activations
        ],
        'fixture_output': fixture_output or default_fixture,
    }
    result = adapter.run(instruction)
    if result.status != 'success':
        return None, {'route': route, 'cost_check': cost_check, 'adapter_status': result.status,
                       'failure_reason': result.failure_reason}

    safety_findings = run_safety_assertions(result.output, agent_name='Good Agent Orchestrator')
    safety_status = aggregate_safety_status(safety_findings)
    metadata = {
        'route': route, 'cost_check': cost_check, 'safety_findings': safety_findings,
        'safety_status': safety_status, 'model_provider': result.model_provider,
        'estimated_cost_usd': estimated_cost_usd,
    }
    return result.output, metadata


def record_activations(opportunity, activations, deep_reasoning_output=None, metadata=None):
    """
    Persist one AgentActivationRecord per activated lens, preserving
    disagreement between lenses rather than averaging it away (Phase 10 —
    do not generate artificial consensus).
    """
    positions_by_principle = {}
    if deep_reasoning_output:
        for pos in deep_reasoning_output.get('positions', []):
            positions_by_principle[pos.get('principle_id')] = pos

    per_agent_cost = (metadata or {}).get('estimated_cost_usd', 0.0) / max(len(activations), 1)
    records = []
    for activation in activations:
        pos = positions_by_principle.get(activation.agent.principle_id, {})
        record, _ = AgentActivationRecord.objects.update_or_create(
            opportunity=opportunity, agent=activation.agent,
            defaults=dict(
                reason_activated=activation.reason,
                evidence_considered=activation.agent.evidence_requirements,
                position=pos.get('position', 'support'),
                confidence=pos.get('confidence', activation.score),
                concern=pos.get('concern', ''),
                recommended_next_analysis=pos.get('recommended_next_analysis', ''),
                cost_usd=per_agent_cost,
                latency_ms=0,
            ),
        )
        records.append(record)
    return records


def summarise_disagreement(records):
    """
    Phase 10 output shape: SUPPORT / CONCERNS / CONFLICTS grouping, no
    artificial consensus.
    """
    return {
        'support': [r.agent.name for r in records if r.position == 'support'],
        'concerns': [r.agent.name for r in records if r.position == 'concerns'],
        'conflicts': [r.agent.name for r in records if r.position == 'conflicts'],
    }
