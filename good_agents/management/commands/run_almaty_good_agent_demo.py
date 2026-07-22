"""
run_almaty_good_agent_demo — the first end-to-end 114 Good Agents
demonstration (Phase 11), run against the existing Almaty Clean Heating
Pilot GoldProject (seed_clean_heating_pilot), reusing the existing capital
pipeline unchanged.

Path proven (Phase 27's required path — a full run touches all of):

    SIGNAL (high heating cost + coal pollution in the Almaty region)
    -> GoodAgentOrchestrator (deterministic Layer 1-3 filter, then one
       combined Layer 4 reasoning call via SimulatedDemoAdapter — never
       one call per lens)
    -> relevant Good Agent lenses (6 seeded principles; not all 114)
    -> Evidence checked (existing Evidence/EvidenceMemory patterns; marked
       insufficient_evidence honestly where no real measurement exists)
    -> GoodOpportunity
    -> OperationalLoss (existing model, illustrative demo figures only)
    -> Better Way comparison (existing capital_guardian service, real
       ranking over do_nothing / heat pump / district heating options)
    -> OpportunityCostAssessment
    -> RedTeamReview
    -> CapitalAllocationDecision (existing bridge) -> human approval
       (the same admin-gated field every other decision in this repo uses)
    -> GoodDeedAction(s) with autonomy classes enforced
    -> ImpactReceipt with an MRV PLAN (no fabricated "measured" figures —
       see services/pipeline.py's module docstring for why)
    -> evidence_memory (existing app, unchanged)

Every financial figure below is explicitly illustrative — this pilot has
no real household enrolment or measured baseline yet (see
GoldProject.data_sources on the pilot row itself). Idempotent: re-running
this command updates the same rows rather than duplicating them.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from good_agents.models import GoodOpportunity
from good_agents.services import good_deeds_engine, pipeline
from good_agents.services.discovery_run import run_discovery
from good_agents.services.orchestrator import Signal

PILOT_SLUG = 'almaty-clean-heating-pilot-200-homes'
DEMO_IDEMPOTENCY_KEY = 'almaty-clean-heating-pilot-good-agent-demo'

SIGNAL_TEXT = (
    'High household heating costs and visible coal-smoke air pollution reported across a defined '
    'pilot portfolio of approximately 200 coal-heated homes in the Almaty region during winter. '
    'Households report energy poverty; no clean-heating alternative has been offered to this cohort yet.'
)

# Hand-authored fixture for the combined Layer 4 reasoning call — mirrors
# the codebase's existing SimulatedDemoAdapter convention (never invents
# output, always a fixture the caller supplies). Deliberately preserves
# disagreement (Phase 10) rather than manufacturing consensus: the
# equitable-access lens raises a real affordability concern.
DEEP_REASONING_FIXTURE = {
    'positions': [
        {'principle_id': 34, 'position': 'support', 'confidence': 75,
         'recommended_next_analysis': 'Confirm technical feasibility and cost basis for heat pump vs district heating.'},
        {'principle_id': 4, 'position': 'support', 'confidence': 70,
         'concern': 'Vulnerable/elderly households need a subsidised path — cannot assume upfront affordability.'},
        {'principle_id': 9, 'position': 'support', 'confidence': 65,
         'recommended_next_analysis': 'Obtain a real air-quality baseline measurement before claiming an emissions benefit.'},
        {'principle_id': 45, 'position': 'concerns', 'confidence': 55,
         'concern': 'Without a subsidy or financing mechanism, this intervention may only reach households that could already afford the switch.'},
        {'principle_id': 19, 'position': 'support', 'confidence': 60,
         'recommended_next_analysis': 'Name the accountable implementing body before any capital is committed.'},
        {'principle_id': 91, 'position': 'support', 'confidence': 60,
         'recommended_next_analysis': 'Evaluate a shared/district heating model against individual heat-pump ownership.'},
    ],
}


class Command(BaseCommand):
    help = 'Runs the first end-to-end 114 Good Agents demonstration against the Almaty Clean Heating Pilot.'

    def handle(self, *args, **options):
        call_command('seed_clean_heating_pilot')
        call_command('seed_good_agent_definitions')

        from gold_intelligence.models import GoldProject
        project = GoldProject.objects.get(slug=PILOT_SLUG)

        signal = Signal(
            text=SIGNAL_TEXT,
            domains=['energy', 'social', 'environment', 'housing', 'justice'],
            geography='Kazakhstan / Almaty region',
            urgency_hint=70.0,
        )

        def opportunity_factory(sig, activations):
            existing = GoodOpportunity.objects.filter(project=project, title__startswith='Almaty coal-to-clean').first()
            if existing is not None:
                return existing
            return GoodOpportunity.objects.create(
                title='Almaty coal-to-clean-heating transition — 200-home pilot',
                theme='energy',
                problem_statement=sig.text,
                unmet_need_or_waste=(
                    'Coal heating imposes ongoing fuel cost and health/air-quality harm on households with no '
                    'clean alternative currently offered.'
                ),
                geography=project.country,
                region=project.region,
                sector='heating / energy transition',
                affected_population='~200 coal-heated households (pilot design target, not a verified enrolment count)',
                project=project,
                detected_signals=[sig.text],
                relevant_principle_ids=[a.agent.principle_id for a in activations],
                evidence_refs=[],
                insufficient_evidence=True,  # no real measured baseline exists yet — stated honestly
                baseline='Coal-fired individual home heating; no measured fuel cost or emissions baseline collected yet.',
                potential_intervention=(
                    'Transition to heat pumps and/or district heating connection, financed via a mix of '
                    'existing energy-efficiency programmes and impact capital rather than EcoIQ-owned funds.'
                ),
                potential_benefit={
                    'people_helped': {'value': 200, 'unit': 'households', 'stage': 'target'},
                    'coal_use_avoided': {'value': None, 'unit': 'tonnes/year', 'stage': 'estimated'},
                },
                risk='Affordability gap for lower-income households if no subsidy mechanism is secured.',
                confidence=40.0,
                urgency=70.0,
                feasibility=55.0,
                scalability='Portfolio approach could extend to other coal-heated districts if the pilot succeeds.',
                capital_required_usd=None,
                zero_capital_possible=True,
                zero_capital_action_plan=(
                    'Identify and connect the pilot cohort to existing municipal/government energy-efficiency '
                    'or heating-transition programmes and impact investors already active in the region — no '
                    'capital owned by EcoIQ is required for this identification/connection step.'
                ),
                status='potential',
            )

        run = run_discovery(
            mission='Find and qualify coal-to-clean-heating opportunities in Kazakhstan',
            signals=[signal],
            geography='Kazakhstan',
            themes=['energy', 'housing', 'justice'],
            cost_budget_usd=5.0,
            idempotency_key=DEMO_IDEMPOTENCY_KEY,
            execution_mode='simulated_demo',
            opportunity_factory=opportunity_factory,
            fixture_output=DEEP_REASONING_FIXTURE,
        )

        opportunity = GoodOpportunity.objects.filter(discovery_run=run).first() or opportunity_factory(signal, [])
        if opportunity is None:
            self.stdout.write(self.style.ERROR('No opportunity was created — aborting.'))
            return

        # --- Capital pipeline (existing, unmodified services) ---------------
        # Idempotent: reuse the opportunity's existing OperationalLoss rather
        # than creating a second one (and cascading a second, redundant
        # CapitalAllocationDecision) on every re-run.
        loss = opportunity.operational_loss or pipeline.create_loss_for_opportunity(
            opportunity, project,
            financial_loss_amount=45000.0,  # illustrative annual coal-fuel cost across the pilot cohort — NOT measured
            evidence_quality='weak',
            loss_type='heat_loss', unit='USD/year', period='annual (illustrative)',
        )
        from waste_to_value_capital_allocation_engine.models import LossEvidence
        LossEvidence.objects.get_or_create(
            operational_loss=loss, evidence_reference='pilot-design-assumption-v1',
            defaults=dict(
                evidence_type='illustrative_estimate',
                source_document='No measured baseline collected yet — see GoldProject.data_sources.',
                public_private_status='private', evidence_quality='weak', confidence=20.0,
            ),
        )

        if not loss.interventions.exists():
            pipeline.add_intervention_option(
                loss, title='Continue coal heating (do nothing)', intervention_type='do_nothing',
                classification='estimated', description='Baseline — no change to current coal heating.',
            )
            pipeline.add_intervention_option(
                loss, title='Heat pump retrofit (illustrative)', intervention_type='equipment_upgrade',
                classification='estimated',
                description='Individual air-source heat pump retrofit per home.',
                capex_estimate=8000.0, estimated_annual_savings=1200.0, estimated_payback_months=80,
                risk_level='medium',
            )
            pipeline.add_intervention_option(
                loss, title='District heating connection (illustrative)', intervention_type='infrastructure_upgrade',
                classification='estimated',
                description='Shared district heating network connection for the pilot cohort.',
                capex_estimate=25000.0, estimated_annual_savings=1800.0, estimated_payback_months=167,
                risk_level='high',
            )

        better_way_result, cost_assessment = pipeline.run_better_way_and_opportunity_cost(opportunity, project, loss)
        decision, option = pipeline.create_capital_decision(project, loss, better_way_result)

        if decision is not None:
            pipeline.mark_decision_approved(
                decision,
                conditions_note=(
                    'Approved for pilot scope only, contingent on real household enrolment and a measured '
                    'baseline before any capital is disbursed.'
                ),
            )
            receipt = pipeline.build_impact_receipt(
                opportunity, decision, better_way_result,
                mrv_methodology=(
                    'Planned: collect a real fuel-cost and air-quality baseline for the enrolled cohort before '
                    'transition, then re-measure the same metrics 12 months after transition. No figure below '
                    'is a measured result yet.'
                ),
            )
        else:
            receipt = None

        for action in opportunity.actions.filter(autonomy_class='green', status='proposed'):
            good_deeds_engine.approve_action(action)
            good_deeds_engine.complete_action(action, output_summary='Prepared as part of the demo run.')
        for action in opportunity.actions.filter(autonomy_class='yellow', status='proposed'):
            good_deeds_engine.approve_action(action)  # simulates a human approving the YELLOW action

        self.stdout.write(self.style.SUCCESS(
            f'\nGoodDiscoveryRun #{run.pk}: {run.status} — '
            f'{run.signals_reviewed} signal(s) reviewed, {run.agents_activated} agent-activations, '
            f'{run.opportunities_detected} opportunity(ies) detected, {run.qualified_opportunities} qualified, '
            f'{run.zero_capital_opportunities} zero-capital.'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'GoodOpportunity #{opportunity.pk} "{opportunity.title}" — status={opportunity.status}'
        ))
        if decision is not None:
            self.stdout.write(self.style.SUCCESS(
                f'CapitalAllocationDecision #{decision.pk} — approval_status={decision.approval_status} '
                f'for intervention "{option.title}"'
            ))
        if receipt is not None:
            self.stdout.write(self.style.SUCCESS(f'ImpactReceipt #{receipt.pk} created (MRV plan, not yet measured).'))
        self.stdout.write(self.style.WARNING(
            'All financial figures in this demo are illustrative pilot-design assumptions, not measured data.'
        ))
