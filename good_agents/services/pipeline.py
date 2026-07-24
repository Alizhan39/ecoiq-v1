"""
good_agents/services/pipeline.py — wires a qualified GoodOpportunity into
the EXISTING, unmodified capital pipeline:

    GoodOpportunity
      -> OperationalLoss + LossEvidence           (waste_to_value_capital_allocation_engine, unchanged)
      -> InterventionOption(s)                    (waste_to_value_capital_allocation_engine, unchanged)
      -> Better Way comparison                     (capital_guardian.services.better_way, unchanged)
      -> OpportunityCostAssessment                 (good_agents — reframes the same ranking)
      -> RedTeamReview                             (good_agents)
      -> CapitalAllocationDecision                 (capital_guardian.services.capital_decision_bridge, unchanged)
      -> [human approval — same admin-gated field every other decision uses]
      -> GoodDeedAction(s)                         (good_agents.services.good_deeds_engine)
      -> ImpactReceipt with an MRV PLAN            (good_agents — measured_result stays empty
                                                     until real after-data exists; see module
                                                     note below on why no VerifiedCapitalOutcome
                                                     is fabricated here)
      -> evidence_memory                           (existing app, unchanged)

No new Evidence, Project, or MRV model is created anywhere in this module.

Why no VerifiedCapitalOutcome here: waste_to_value_capital_allocation_engine
.services.demo_pipeline (the existing Meat Cold-Chain reference demo)
deliberately does not create one either — its own docstring: "No
VerifiedCapitalOutcome is created here... creating one would silently turn
a projected result into a verified one." This module follows the same
discipline for the Almaty demo. `record_verified_outcome_and_sync` below
exists and is fully wired (see tests.py) for the case where real after-data
genuinely exists — it is simply not called by the demo command, because
real after-data does not exist yet for a pilot that hasn't been built.
"""
from django.utils import timezone

from capital_guardian.services.better_way import compare_interventions, tag_classification
from capital_guardian.services.capital_decision_bridge import create_decision_from_better_way
from capital_guardian.services.execution_monitoring import record_monitoring_outcome
from evidence_memory.services.memory import (
    create_memory_from_manual_project_evidence, create_memory_from_verified_outcome,
)
from waste_to_value_capital_allocation_engine.models import InterventionOption
from waste_to_value_capital_allocation_engine.services.loss_intake import create_operational_loss

from good_agents.models import ImpactReceipt
from good_agents.services import good_deeds_engine, notify, opportunity_cost, red_team
from good_agents.services.timeline import record_event


def create_loss_for_opportunity(opportunity, project, *, financial_loss_amount, classification='estimated',
                                 evidence_quality='weak', **extra_loss_fields):
    """
    Creates the OperationalLoss this opportunity is really about. Uses the
    existing, unmodified `create_operational_loss()` — no new field, no new
    model. `classification`/`evidence_quality` default to 'estimated'/'weak'
    because a freshly-discovered opportunity has, by definition, not yet
    been independently verified.
    """
    loss = create_operational_loss(
        project=project.name,
        country=project.country.name if project.country else '',
        location=opportunity.region,
        sector=opportunity.sector,
        title=opportunity.title,
        description=opportunity.problem_statement,
        financial_loss_amount=financial_loss_amount,
        evidence_quality=evidence_quality,
        status='detected',
        **extra_loss_fields,
    )
    opportunity.operational_loss = loss
    opportunity.save(update_fields=['operational_loss', 'updated_at'])
    return loss


def add_intervention_option(loss, *, title, intervention_type, classification='estimated', **fields):
    return InterventionOption.objects.create(
        operational_loss=loss, title=title, intervention_type=intervention_type,
        description=tag_classification(fields.pop('description', ''), classification),
        **fields,
    )


def run_better_way_and_opportunity_cost(opportunity, project, loss):
    """Better Way (Phase 7) + Opportunity Cost (Phase 8) — both reuse existing/real ranking, no new scoring."""
    better_way_result = compare_interventions(project, loss)
    cost_assessment = opportunity_cost.assess_from_better_way(opportunity, better_way_result)
    return better_way_result, cost_assessment


def create_capital_decision(project, loss, better_way_result):
    """
    Selects the top-ranked, non-blocked option (if any) and creates the
    governed decision via the existing bridge. Returns (decision_or_None,
    selected_option_or_None). Never bypasses BlockedInterventionError.
    """
    if not better_way_result.ranked:
        return None, None
    top = better_way_result.ranked[0]
    option = top['option']
    decision = create_decision_from_better_way(project, loss, option)
    return decision, option


def mark_decision_approved(decision, conditions_note=''):
    """
    The same mechanism every other CapitalAllocationDecision in this repo
    uses today (an admin-editable field) — this function exists so the
    approval step is callable from a management command/test without
    driving the Django admin UI, not a second approval workflow.
    """
    decision.approval_status = 'approved'
    if conditions_note:
        decision.conditions = [*decision.conditions, conditions_note]
    decision.save(update_fields=['approval_status', 'conditions'])
    return decision


def build_impact_receipt(opportunity, decision, better_way_result, mrv_methodology):
    """
    Closes the loop with an MRV PLAN (Phase 27's required path — "plan", not
    "verified outcome"). `measured_result` stays empty: nothing has been
    measured yet. Pushes a manual evidence-memory entry describing the
    plan so later runs can retrieve it (Phase 16's self-learning loop feeds
    on this over time as real outcomes replace plans).
    """
    principles_applied = list(opportunity.relevant_principle_ids)
    receipt, _ = ImpactReceipt.objects.update_or_create(
        opportunity=opportunity,
        defaults=dict(
            decision=decision,
            problem=opportunity.problem_statement,
            baseline=opportunity.baseline,
            evidence_summary=opportunity.evidence_refs,
            principles_applied=principles_applied,
            decision_summary=decision.decision if decision else '',
            alternative_considered=opportunity.opportunity_cost_assessment.best_alternative
            if hasattr(opportunity, 'opportunity_cost_assessment') else '',
            better_way_summary=better_way_result.why_top_ranked or better_way_result.baseline_warning,
            capital_resources_used=(
                f'Capital required: ${opportunity.capital_required_usd:,.0f}'
                if opportunity.capital_required_usd else 'Zero-capital path'
            ),
            action_taken='Awaiting execution — see linked GoodDeedAction rows.',
            expected_result=opportunity.potential_benefit,
            measured_result={},
            mrv_methodology=mrv_methodology,
            evidence_after_implementation=[],
            lessons_learned='',
            confidence=opportunity.confidence,
        ),
    )

    create_memory_from_manual_project_evidence(
        opportunity.project,
        title=f'Good Opportunity — {opportunity.title} (MRV plan)',
        text=(
            f'{opportunity.problem_statement}\n\nMRV plan: {mrv_methodology}\n\n'
            f'Expected result (estimated, not yet measured): {opportunity.potential_benefit}'
        ),
        source_url='', source_type='manual', document_category='other',
        verification_status='pending', review_tier='uploaded', is_demo=opportunity.project.is_demo,
        date_collected=timezone.now().date(),
    )
    return receipt


def qualify_opportunity(opportunity, activation_records):
    """Runs RedTeamReview and, if it clears, advances the opportunity's ledger status (Phase 14)."""
    review = red_team.build_review(opportunity, activation_records)
    if opportunity.status == 'potential':
        opportunity.status = 'qualified' if review.cleared else 'potential'
        opportunity.save(update_fields=['status', 'updated_at'])
    good_deeds_engine.propose_default_actions(opportunity)
    return review


def record_verified_outcome_and_sync(decision, *, mrv_status, evidence_quality, capex_actual,
                                     loss_avoided_actual, savings_actual=0, reviewer_note=''):
    """
    Fully wired MRV -> Evidence Memory path (Phase 12/16), for use once real
    after-data genuinely exists. Not called by the demo command — see this
    module's docstring for why. Exercised directly in tests.py to prove the
    wiring is real, using clearly-synthetic test figures.

    PR5 Phase 21-23 — closes the loop onto GoodOpportunity.status, which has
    'measured'/'verified' choices nothing previously set. This function can
    only ever reach 'measured': record_monitoring_outcome() (called below)
    refuses mrv_status='verified' by design (see execution_monitoring.py's
    own safety-gate docstring — "the same user entering a result does not
    automatically make it independently verified"). The 'verified' half of
    the loop is closed by good_agents/signals.py reacting to the one real
    path to independent verification: a staff member editing the existing
    VerifiedCapitalOutcome admin change form directly.
    """
    outcome = record_monitoring_outcome(
        decision, mrv_status=mrv_status, evidence_quality=evidence_quality,
        capex_actual=capex_actual, loss_avoided_actual=loss_avoided_actual,
        savings_actual=savings_actual, reviewer_note=reviewer_note,
    )
    memory = create_memory_from_verified_outcome(outcome)
    receipt = ImpactReceipt.objects.filter(decision=decision).first()
    if receipt is not None:
        receipt.verified_outcome = outcome
        receipt.measured_result = {
            'capex_actual': capex_actual, 'loss_avoided_actual': loss_avoided_actual,
            'savings_actual': savings_actual, 'stage': 'measured',
        }
        receipt.save(update_fields=['verified_outcome', 'measured_result'])

        opportunity = receipt.opportunity
        if opportunity.status not in ('measured', 'verified'):
            opportunity.status = 'measured'
            opportunity.save(update_fields=['status'])
        record_event(
            opportunity, 'outcome_measured',
            source_object_reference=f'good_agents.ImpactReceipt:{receipt.pk}',
            notes='Real after-data recorded — independent verification still required.',
        )
        notify.notify_outcome_measured(opportunity)
    return outcome, memory
