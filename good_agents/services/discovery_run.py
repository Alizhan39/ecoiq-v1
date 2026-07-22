"""
good_agents/services/discovery_run.py — GoodDiscoveryRun runner (Phase 12;
this IS the Observatory's actual unit of work — see docs/GOOD_WHILE_YOU_SLEEP.md
for why a separate "Observatory" model doesn't exist). Bounded, resumable,
idempotent on `idempotency_key`.

Signal SOURCING (continuously scanning the world for candidate signals) is
explicitly out of scope for this slice — this runner consumes an explicit
list of Signal objects the caller already assembled. Marked TODO in
docs/GOOD_AGENTS_PROGRESS.md.
"""
from good_agents.models import GoodDiscoveryRun
from good_agents.services.orchestrator import classify_relevant_agents, record_activations, run_deep_reasoning
from good_agents.services.pipeline import qualify_opportunity


def run_discovery(mission, signals, *, geography='', themes=None, cost_budget_usd=5.0,
                  idempotency_key=None, execution_mode='simulated_demo', opportunity_factory=None,
                  fixture_output=None):
    """
    opportunity_factory: callable(signal, activations) -> GoodOpportunity or
    None. None means "no real opportunity here" (e.g. below threshold,
    insufficient evidence). Kept injectable so this runner stays
    domain-agnostic — the Almaty demo command supplies the concrete
    GoodOpportunity-building logic for its one scenario.

    fixture_output: optional hand-authored dict passed straight through to
    run_deep_reasoning for execution_mode='simulated_demo' — this is how a
    caller supplies a real (non-invented) Layer 4 reasoning result, same
    convention as every other SimulatedDemoAdapter use in this repo.
    """
    if idempotency_key:
        run, created = GoodDiscoveryRun.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults=dict(mission=mission, geography=geography, themes=themes or [], cost_budget_usd=cost_budget_usd),
        )
        if not created and run.status == 'completed':
            return run  # idempotent — already ran to completion
    else:
        run = GoodDiscoveryRun.objects.create(
            mission=mission, geography=geography, themes=themes or [], cost_budget_usd=cost_budget_usd,
        )

    run.mark_running()
    try:
        for signal in signals:
            run.signals_reviewed += 1
            activations = classify_relevant_agents(signal)
            if not activations:
                continue
            run.agents_activated += len(activations)

            if run.over_budget():
                run.errors = [*run.errors, f'Cost budget exceeded before processing signal: {signal.text[:80]}']
                break

            deep_output, metadata = run_deep_reasoning(
                signal, activations, execution_mode=execution_mode, fixture_output=fixture_output,
            )
            run.estimated_run_cost_usd += metadata.get('estimated_cost_usd', 0.0) or 0.0

            opportunity = opportunity_factory(signal, activations) if opportunity_factory else None
            if opportunity is None:
                continue
            run.opportunities_detected += 1
            opportunity.discovery_run = run
            opportunity.save(update_fields=['discovery_run', 'updated_at'])

            records = record_activations(opportunity, activations, deep_output, metadata)
            qualify_opportunity(opportunity, records)
            if opportunity.status == 'qualified':
                run.qualified_opportunities += 1
            if opportunity.zero_capital_possible:
                run.zero_capital_opportunities += 1

        run.save()  # persist every counter accumulated above
        run.mark_completed()
    except Exception as exc:
        run.save()  # persist whatever was accumulated before the failure
        run.mark_failed(str(exc))
        raise
    return run
