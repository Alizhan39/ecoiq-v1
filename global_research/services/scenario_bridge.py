"""
global_research/services/scenario_bridge.py — promotes a human-approved
ResearchRecommendation into a REAL `digital_twin.ModernisationScenario`.
Never a parallel scenario model (docs/adr/ADR-global-research-engine.md
decision 11). Never hard-binds to one manufacturer/product unless a human
explicitly approved that exact recommendation first — the approval check
happens before anything is created.
"""
from global_research.services.human_approval_gate import require_human_approval


class ScenarioBridgeError(Exception):
    """Raised when a ResearchRecommendation cannot yet become a real
    ModernisationScenario — e.g. no promoted OperationalLoss or no twin to
    attach to. Never silently guesses a substitute."""


def create_scenario_from_recommendation(recommendation, human_decision):
    """Idempotent: if this recommendation already created a scenario,
    returns it unchanged rather than creating a second one."""
    require_human_approval('research_scenario_creation', human_decision)

    if recommendation.created_scenario_id:
        return recommendation.created_scenario

    mission = recommendation.mission
    if not mission.twin_id:
        raise ScenarioBridgeError('ResearchMission has no digital_twin.DigitalTwin set — cannot create a ModernisationScenario without a real twin to attach it to.')
    if not mission.loss_detection_id or not mission.loss_detection.promoted_loss_id:
        raise ScenarioBridgeError(
            'ResearchMission has no promoted OperationalLoss (via loss_detection) — a ModernisationScenario '
            'requires a real, human-approved loss to attach to, exactly like a Digital-Twin-originated scenario.'
        )

    from digital_twin.models import ModernisationScenario
    from waste_to_value_capital_allocation_engine.models import InterventionOption

    real_loss = mission.loss_detection.promoted_loss
    technology_candidate = recommendation.technology_candidate
    product_candidate = recommendation.product_candidate
    if technology_candidate is None:
        raise ScenarioBridgeError('ResearchRecommendation has no technology_candidate — cannot derive a supplier-neutral scenario from nothing.')

    title = product_candidate.product_name if product_candidate else technology_candidate.name

    intervention, _ = InterventionOption.objects.get_or_create(
        operational_loss=real_loss, title=f'{title} (via Global Research)',
        defaults=dict(
            intervention_type='equipment_upgrade',
            description=recommendation.rationale,
            capex_estimate=(product_candidate.indicative_cost or 0.0) if product_candidate else 0.0,
            status='proposed',
        ),
    )

    scenario, _ = ModernisationScenario.objects.get_or_create(
        intervention=intervention,
        defaults=dict(
            twin=mission.twin, component=mission.component, process_node=mission.process_node,
            scenario_type='strategic',
            technology_category=technology_candidate.category.name,
            technical_specification=technology_candidate.technical_mechanism or technology_candidate.description,
            confidence=recommendation.confidence, evidence_references=recommendation.evidence_references,
        ),
    )
    recommendation.created_scenario = scenario
    recommendation.save(update_fields=['created_scenario', 'updated_at'])
    return scenario
