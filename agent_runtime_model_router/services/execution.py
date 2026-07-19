"""
agent_runtime_model_router/services/execution.py — the orchestration layer.

Council Case -> Agent Selection -> Training Pack Loader -> Model Router ->
Agent Execution -> Structured Output Validation -> Safety Assertions ->
Council Position -> (Cross-Examination / Council Decision / Human Approval
/ Institutional Memory happen in ai_agent_council, untouched by this app).

No Django template coupling — every function here operates on model
instances and plain dicts only.
"""
import hashlib
import json

from django.utils import timezone

from agent_runtime_model_router.models import AgentRegistryEntry, AgentRun
from agent_runtime_model_router.services.confidence_calibration import calibrate_confidence
from agent_runtime_model_router.services.cost_policy import check_cost_policy
from agent_runtime_model_router.services.human_approval_gate import require_human_approval
from agent_runtime_model_router.services.model_adapters import get_adapter
from agent_runtime_model_router.services.model_router import select_model_route
from agent_runtime_model_router.services.safety_assertions import (
    aggregate_safety_status, run_safety_assertions,
)
from agent_runtime_model_router.services.schema_validation import validate_agent_output
from agent_runtime_model_router.services.training_pack_loader import (
    load_training_pack, validate_training_pack,
)

MAX_LIVE_RETRIES = 1

# ── feat/model-router-observatory ──────────────────────────────────────────
# Every adapter call in execute_agent() goes through _run_adapter_observed()
# below — the single shared boundary between EcoIQ and every model provider.
# One PHYSICAL provider request produces exactly one
# ai_observatory.ModelInvocation row; the router's bounded same-provider
# retry and its fallback-provider attempt are separate physical requests and
# therefore separate rows (retry_count records which attempt each row was,
# per provider: 0 = first attempt, 1 = the single bounded retry).
#
# NOT recorded, deliberately:
# - deterministic / simulated adapters (no model is invoked — recording them
#   would poison the Observatory's honest "zero model calls" story);
# - failures where no provider request was ever sent (missing_credentials,
#   unsupported_capability): nothing physical happened, so nothing is
#   counted.
#
# Telemetry can never break the model request: recording happens after the
# adapter returns, inside its own try/except, and the recorder itself also
# swallows failures. Only provider-reported usage values are stored —
# estimates stay in AgentRun.estimated_* where they always lived, and are
# never copied into the Observatory's measured columns. Prompts, responses
# and API keys are never passed to the recorder.

LIVE_PROVIDERS = {'anthropic', 'openai', 'gemini', 'azure_openai'}
_NO_REQUEST_FAILURES = {'missing_credentials', 'unsupported_capability'}


def _normalise_usage(provider, usage):
    """Maps each provider's own usage-dict shape onto (input_tokens,
    output_tokens, cached_tokens, model_version). Absent values stay None —
    never estimated, never zero-filled."""
    usage = usage or {}
    if provider == 'anthropic':
        return (
            usage.get('input_tokens'), usage.get('output_tokens'),
            usage.get('cache_read_input_tokens'), usage.get('model') or '',
        )
    if provider in ('openai', 'azure_openai'):
        cached = (usage.get('prompt_tokens_details') or {}).get('cached_tokens')
        return (
            usage.get('prompt_tokens'), usage.get('completion_tokens'),
            cached, usage.get('model') or '',
        )
    if provider == 'gemini':
        return (
            usage.get('promptTokenCount'), usage.get('candidatesTokenCount'),
            usage.get('cachedContentTokenCount'), usage.get('modelVersion') or '',
        )
    return None, None, None, ''


def _run_adapter_observed(adapter, instruction, agent_run, attempt, observatory_session=None):
    """Runs one adapter call and records it in the AI Observatory when (and
    only when) a physical provider request actually happened. The adapter's
    result — success or failure — is returned untouched."""
    import time as _time

    started = _time.perf_counter()
    result = adapter.run(instruction)
    duration_ms = max(0, int((_time.perf_counter() - started) * 1000))

    try:
        provider = getattr(adapter, 'provider', '')
        if provider in LIVE_PROVIDERS and result.failure_reason not in _NO_REQUEST_FAILURES:
            from ai_observatory.services import recorder as observatory_recorder

            input_tokens, output_tokens, cached_tokens, model_version = _normalise_usage(
                provider, result.actual_usage,
            )
            observatory_recorder.record_model_invocation(
                observatory_session,
                provider=provider,
                model_name=result.model_name or instruction.get('model_name', ''),
                model_version=model_version,
                prompt_version=agent_run.prompt_version or '',
                input_tokens=input_tokens, output_tokens=output_tokens,
                cached_tokens=cached_tokens,
                streaming=False,  # every adapter here uses non-streaming APIs — a known value, not a guess
                retry_count=attempt,
                duration_ms=duration_ms,
                succeeded=(result.status == 'success'),
                agent_run=agent_run if agent_run.pk else None,
            )
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Observatory instrumentation failed for AgentRun %s', agent_run.pk)

    return result

# Illustrative per-1000-token pricing, USD — for the "estimated cost" label
# only, never presented as an actual provider bill.
ESTIMATED_PRICE_PER_1K_TOKENS = {
    'anthropic': 0.015, 'openai': 0.010, 'gemini': 0.007, 'azure_openai': 0.012,
    'deterministic': 0.0, 'simulated': 0.0,
}

FORBIDDEN_EVIDENCE_UPGRADES = {
    ('weak', 'strong'), ('estimated', 'verified'), ('missing', 'complete'),
}


def _log_event(agent_run, event, detail=''):
    agent_run.audit_trail = agent_run.audit_trail + [
        {'ts': timezone.now().isoformat(), 'event': event, 'detail': detail},
    ]


def _compute_idempotency_key(council_case_id, agent_id, task_type, input_evidence_version,
                              training_pack_version, execution_mode_requested):
    raw = '|'.join(str(part) for part in (
        council_case_id, agent_id, task_type, input_evidence_version,
        training_pack_version, execution_mode_requested,
    ))
    return hashlib.sha256(raw.encode()).hexdigest()


def create_agent_run(agent_name, task_type, council_case=None, execution_mode='live',
                      input_summary='', evidence_provenance=None, rerun_reason=''):
    """
    Idempotent: returns the existing completed run for the same
    (case, agent, task_type, evidence, training-pack version, mode) unless
    an explicit rerun_reason is given, in which case a new run is created
    and linked via `rerun_of`.
    """
    agent = AgentRegistryEntry.objects.get(agent_name=agent_name)
    evidence_provenance = evidence_provenance or []

    if evidence_provenance:
        version_source = json.dumps(evidence_provenance, sort_keys=True)
    else:
        version_source = input_summary
    input_evidence_version = hashlib.sha256(version_source.encode()).hexdigest()[:16]

    idempotency_key = _compute_idempotency_key(
        council_case.id if council_case else None, agent.agent_id, task_type,
        input_evidence_version, agent.training_pack_version, execution_mode,
    )

    existing = AgentRun.objects.filter(
        idempotency_key=idempotency_key, status='completed',
    ).order_by('-created_at').first()

    if existing and not rerun_reason:
        return existing

    return AgentRun.objects.create(
        council_case=council_case, agent=agent, task_type=task_type,
        execution_mode_requested=execution_mode, input_summary=input_summary,
        evidence_provenance=evidence_provenance, idempotency_key=idempotency_key,
        rerun_of=existing if (existing and rerun_reason) else None,
        rerun_reason=rerun_reason, status='pending',
    )


def build_agent_instruction(agent_run, training_pack, model_name, fixture_output=None):
    aliases = training_pack['aliases']
    prompt_text = (
        f"{aliases['system_prompt']}\n\n{aliases['task_prompt']}\n\n"
        f"Task: {agent_run.task_type}\nInput: {agent_run.input_summary}"
    )
    return {
        'agent_name': agent_run.agent.agent_name,
        'task_type': agent_run.task_type,
        'prompt_text': prompt_text,
        'model_name': model_name,
        'test_cases': training_pack['test_cases'],
        'fixture_output': fixture_output,
    }


def _estimate_cost(provider, prompt_text):
    input_tokens = max(1, len(prompt_text) // 4)
    output_tokens = 300
    price = ESTIMATED_PRICE_PER_1K_TOKENS.get(provider, 0.010)
    cost = (input_tokens + output_tokens) / 1000 * price
    return input_tokens, output_tokens, round(cost, 4)


def check_no_evidence_upgrade(evidence_provenance, prior_evidence_by_id):
    """
    Blocks a downstream run from silently upgrading an evidence item's
    quality label (weak->strong, estimated->verified, missing->complete)
    without new provenance (a different source_document/source_ref)
    justifying it. Returns a list of violation dicts.
    """
    violations = []
    for item in evidence_provenance:
        evidence_id = item.get('evidence_id')
        prior = prior_evidence_by_id.get(evidence_id)
        if not prior:
            continue
        transition = (prior.get('quality'), item.get('quality'))
        same_source = (
            item.get('source_document') == prior.get('source_document')
            and item.get('source_ref') == prior.get('source_ref')
        )
        if transition in FORBIDDEN_EVIDENCE_UPGRADES and same_source:
            violations.append({
                'pattern_id': 'evidence_upgrade_violation', 'severity': 'blocking',
                'detail': (
                    f"Evidence '{evidence_id}' silently upgraded from '{transition[0]}' to "
                    f"'{transition[1]}' with no new supporting source."
                ),
            })
    return violations


def _prior_evidence_by_id(agent_run):
    prior_runs = AgentRun.objects.filter(council_case=agent_run.council_case)
    if agent_run.pk:
        prior_runs = prior_runs.exclude(pk=agent_run.pk)
    by_id = {}
    for run in prior_runs:
        for item in run.evidence_provenance:
            by_id[item.get('evidence_id')] = item
    return by_id


def execute_agent(agent_run, sensitivity_level='standard', requires_vision=False,
                   requires_reasoning=False, context_length=0, cost_class='standard',
                   fixture_output=None, allow_deterministic_fallback=False,
                   evidence_quality_score=70, unresolved_disagreements=0,
                   contradiction_severity='none', reviewer_status='pending',
                   observatory_session=None):
    """
    Runs the full pipeline for one AgentRun: load pack -> route -> execute
    (with fallback handling) -> validate -> safety-check -> calibrate. Never
    relabels a failed live run as simulated_demo — see the fallback branch.

    observatory_session (feat/model-router-observatory): an optional
    ai_observatory.AnalysisSession the caller ALREADY owns for the project
    this run belongs to. When provided, each recorded ModelInvocation links
    to it; when absent, invocations are recorded honestly unlinked
    (session=NULL) — the router has no reliable project context of its own
    (AgentRun knows only its council case), and a guessed link would weaken
    project isolation.
    """
    agent_run.status = 'running'
    agent_run.started_at = timezone.now()
    _log_event(agent_run, 'execution_started', agent_run.execution_mode_requested)

    validation = validate_training_pack(agent_run.agent.agent_name)
    if not validation['valid'] and agent_run.execution_mode_requested != 'simulated_demo':
        agent_run.status = 'failed'
        agent_run.failure_reason = 'schema_failure'
        _log_event(agent_run, 'training_pack_invalid', json.dumps(validation))
        agent_run.completed_at = timezone.now()
        agent_run.save()
        return agent_run

    training_pack = load_training_pack(agent_run.agent.agent_name)
    agent_run.training_pack_path = agent_run.agent.training_pack_path
    agent_run.training_pack_version = agent_run.agent.training_pack_version
    agent_run.training_pack_content_hash = agent_run.agent.content_hash
    agent_run.prompt_version = 'v1'
    agent_run.schema_version = 'v1'
    agent_run.safety_rules_version = 'v1'
    agent_run.golden_test_version = 'v1'

    route = select_model_route(
        agent_run.agent.agent_name, agent_run.task_type, agent_run.execution_mode_requested,
        sensitivity_level, requires_vision, requires_reasoning, context_length, cost_class,
    )
    agent_run.model_provider = route['selected_provider']
    agent_run.model_name = route['selected_model']
    agent_run.routing_reason = route['reason']
    agent_run.sensitivity_level = route['sensitivity_level']
    agent_run.required_capability = route['required_capability']
    agent_run.cost_class = route['cost_class']
    agent_run.rejected_routes = route['rejected_alternatives']
    agent_run.fallback_route = route['fallback_route']

    instruction = build_agent_instruction(agent_run, training_pack, route['selected_model'], fixture_output)

    input_tokens, output_tokens, estimated_cost = _estimate_cost(route['selected_provider'], instruction['prompt_text'])
    agent_run.estimated_input_tokens = input_tokens
    agent_run.estimated_output_tokens = output_tokens
    agent_run.estimated_cost_usd = estimated_cost

    cost_check = check_cost_policy(estimated_cost, agent_run.council_case, cost_class)
    if not cost_check['allowed']:
        agent_run.status = 'blocked'
        agent_run.budget_exceeded = True
        agent_run.human_approval_required = True
        agent_run.failure_reason = ''
        _log_event(agent_run, 'blocked_by_cost_policy', cost_check['reason'])
        agent_run.completed_at = timezone.now()
        agent_run.save()
        return agent_run
    if cost_check['requires_human_approval']:
        agent_run.human_approval_required = True

    fallback_chain = []
    adapter = get_adapter(route['selected_provider'])
    result = _run_adapter_observed(adapter, instruction, agent_run, 0, observatory_session)

    if result.status == 'failed' and agent_run.execution_mode_requested == 'live':
        fallback_chain.append({
            'provider': route['selected_provider'], 'model': route['selected_model'],
            'outcome': 'failed', 'reason': result.failure_reason,
        })
        # Allowed outcome 1: one bounded retry on the same provider.
        result = _run_adapter_observed(adapter, instruction, agent_run, 1, observatory_session)
        if result.status == 'failed':
            fallback_chain.append({
                'provider': route['selected_provider'], 'model': route['selected_model'],
                'outcome': 'failed_retry', 'reason': result.failure_reason,
            })
            # Allowed outcome 2: the configured live fallback provider,
            # running ITS OWN configured model. fix/router-fallback-model:
            # the previous code passed instruction.copy() unchanged, so the
            # fallback adapter was asked to run the PRIMARY provider's model
            # string (e.g. Anthropic asked for "gpt-4o") and could never
            # succeed. Model selection is provider-specific: provider ->
            # default_model_for(provider), from the same configuration the
            # router itself uses. A fallback provider with no configured
            # model is skipped with an explicit reason, never attempted
            # with a model it cannot serve. FALLBACK_MAP is a static
            # one-hop map and this branch runs exactly once, so no
            # fallback chain/loop is possible.
            from agent_runtime_model_router.services.model_router import default_model_for

            fallback_provider = route['fallback_route']
            fallback_model_name = default_model_for(fallback_provider)
            if fallback_provider and fallback_model_name:
                fallback_adapter = get_adapter(fallback_provider)
                fallback_instruction = dict(instruction, model_name=fallback_model_name)
                result = _run_adapter_observed(fallback_adapter, fallback_instruction, agent_run, 0, observatory_session)
            if result.status == 'success':
                agent_run.model_provider = fallback_provider
                agent_run.model_name = result.model_name
                fallback_chain.append({
                    'provider': fallback_provider, 'model': result.model_name,
                    'outcome': 'success', 'reason': 'live fallback provider succeeded',
                })
            elif not (fallback_provider and fallback_model_name):
                fallback_chain.append({
                    'provider': fallback_provider or 'none', 'model': '',
                    'outcome': 'skipped', 'reason': 'no_fallback_model_configured',
                })
            else:
                fallback_chain.append({
                    'provider': fallback_provider, 'model': fallback_model_name,
                    'outcome': 'failed', 'reason': result.failure_reason,
                })
            if result.status == 'failed' and allow_deterministic_fallback:
                # Allowed outcome 3 — ONLY when explicitly requested
                # (test/CI harness). Reachable whether the live fallback
                # failed or was skipped for lack of a configured model.
                # Deterministic adapter = no model invoked = never recorded
                # in the Observatory.
                deterministic_result = _run_adapter_observed(
                    get_adapter('deterministic'), instruction, agent_run, 0, observatory_session,
                )
                if deterministic_result.status == 'success':
                    result = deterministic_result
                    agent_run.execution_mode_used = 'deterministic_test'
                    agent_run.fallback_reason = 'Live providers failed; explicit deterministic_test fallback was allowed.'
                    fallback_chain.append({
                        'provider': 'deterministic', 'model': 'deterministic-test-v1',
                        'outcome': 'success', 'reason': 'explicit deterministic fallback',
                    })

    agent_run.fallback_chain = fallback_chain

    # Hard invariant (hardening requirement 1): a live request can never
    # silently resolve to simulated_demo. This check is an explicit
    # conditional (not `assert`) so it can never be stripped by -O.
    if not agent_run.execution_mode_used:
        agent_run.execution_mode_used = agent_run.execution_mode_requested
    if agent_run.execution_mode_requested == 'live' and agent_run.execution_mode_used == 'simulated_demo':
        raise RuntimeError('A live request must never be silently relabelled as simulated_demo.')

    if result.status == 'failed':
        agent_run.status = 'needs_human_review'
        agent_run.human_approval_required = True
        agent_run.failure_reason = result.failure_reason or 'empty_response'
        agent_run.fallback_reason = agent_run.fallback_reason or f'All routes failed: {result.failure_reason}'
        _log_event(agent_run, 'execution_failed', result.failure_reason)
        agent_run.completed_at = timezone.now()
        agent_run.save()
        return agent_run

    agent_run.raw_output = result.raw_text
    agent_run.parsed_output = result.output or {}
    agent_run.raw_confidence = agent_run.parsed_output.get('confidence')
    agent_run.evidence_used = agent_run.parsed_output.get('evidence_used', [])
    agent_run.missing_data = agent_run.parsed_output.get('missing_data', [])
    agent_run.risk_flags = agent_run.parsed_output.get('risk_flags', [])
    agent_run.actual_usage = result.actual_usage

    schema_valid, validation_errors = validate_agent_output(agent_run.parsed_output)
    agent_run.schema_valid = schema_valid
    agent_run.validation_errors = validation_errors

    safety_findings = run_safety_assertions(agent_run.parsed_output, agent_run.agent.agent_name)
    evidence_violations = check_no_evidence_upgrade(agent_run.evidence_provenance, _prior_evidence_by_id(agent_run))
    all_findings = safety_findings + evidence_violations
    agent_run.safety_findings = all_findings
    agent_run.safety_status = aggregate_safety_status(all_findings)

    breakdown = calibrate_confidence(
        evidence_quality_score=evidence_quality_score,
        num_supporting_sources=len(agent_run.evidence_used),
        missing_data=agent_run.missing_data,
        schema_valid=agent_run.schema_valid,
        unresolved_disagreements=unresolved_disagreements,
        contradiction_severity=contradiction_severity,
        maturity_stage=agent_run.agent.maturity_stage,
        reviewer_status=reviewer_status,
        safety_findings=all_findings,
    )
    agent_run.calibrated_confidence = breakdown['final']
    agent_run.confidence_calibration_explanation = breakdown

    if agent_run.safety_status == 'blocking':
        agent_run.status = 'blocked'
        agent_run.human_approval_required = True
    elif agent_run.safety_status == 'needs_review' or not agent_run.schema_valid:
        agent_run.status = 'needs_human_review'
        agent_run.human_approval_required = True
    else:
        agent_run.status = 'completed'

    _log_event(agent_run, 'execution_completed', agent_run.status)
    agent_run.completed_at = timezone.now()
    agent_run.save()
    return agent_run


def submit_agent_position_to_council(agent_run, collaboration_mode='council', order=0, action_type=None):
    """
    Only a trustworthy run (schema-valid, not safety-blocked, completed) may
    become a Council AgentTask. If `action_type` names one of the 8
    approval-gated actions, human approval is enforced before proceeding.
    """
    if agent_run.status != 'completed' or not agent_run.schema_valid or agent_run.safety_status == 'blocking':
        raise ValueError(
            f'AgentRun {agent_run.pk} is not trustworthy enough to enter Council reasoning '
            f'(status={agent_run.status}, schema_valid={agent_run.schema_valid}, safety_status={agent_run.safety_status}).'
        )

    if action_type:
        require_human_approval(action_type, agent_run)

    from ai_agent_council.models import AgentTask

    parsed = agent_run.parsed_output
    task = AgentTask.objects.create(
        run=agent_run.council_case,
        agent_name=agent_run.agent.agent_name,
        collaboration_mode=collaboration_mode,
        status='completed',
        input_summary=agent_run.input_summary,
        output_summary=json.dumps(parsed),
        position_summary=parsed.get('output_summary', agent_run.input_summary),
        confidence=agent_run.calibrated_confidence,
        confidence_breakdown=agent_run.confidence_calibration_explanation,
        evidence_refs=agent_run.evidence_used,
        missing_data=agent_run.missing_data,
        risk_flags=agent_run.risk_flags,
        order=order,
    )
    agent_run.council_position = task
    agent_run.save()
    return task
