"""
khalifa_stewardship_tour_operating_system/services/human_approval_gate.py —
reuses agent_runtime_model_router's gate directly rather than forking it,
exactly matching every prior app's wrapper shape.

Adds 10 new action types not covered by the base 8 (`public_impact_claim`
is already one of the base 8 — not duplicated here): `participant_recruitment`,
`payment_collection`, `supplier_appointment`, `local_partner_appointment`,
`household_intervention`, `food_redistribution_action`,
`vulnerable_person_filming`, `household_story_publishing`,
`technical_work_authorization`, `travel_launch_authorization`.
"""
from agent_runtime_model_router.services.human_approval_gate import (
    ACTIONS_REQUIRING_APPROVAL as _BASE_ACTIONS,
    HumanApprovalRequiredError,
    require_human_approval as _base_require_human_approval,
)

ADDITIONAL_ACTIONS_REQUIRING_APPROVAL = frozenset({
    'participant_recruitment',
    'payment_collection',
    'supplier_appointment',
    'local_partner_appointment',
    'household_intervention',
    'food_redistribution_action',
    'vulnerable_person_filming',
    'household_story_publishing',
    'technical_work_authorization',
    'travel_launch_authorization',
})

ACTIONS_REQUIRING_APPROVAL = _BASE_ACTIONS | ADDITIONAL_ACTIONS_REQUIRING_APPROVAL


def require_human_approval(action_type, approvable):
    """
    Reuses the base gate for the 8 shared actions; handles this app's 10
    additional action types the same way (raise unless human_approved is
    exactly True). `approvable` is typically a StewardshipTour,
    TourLocalPartner, or TourFundingPlan.
    """
    if action_type in ADDITIONAL_ACTIONS_REQUIRING_APPROVAL:
        if getattr(approvable, 'human_approved', None) is not True:
            raise HumanApprovalRequiredError(
                f"Action '{action_type}' requires human approval before it can proceed "
                f'(id={getattr(approvable, "pk", None)}, human_approved={getattr(approvable, "human_approved", None)!r}).'
            )
        return True
    return _base_require_human_approval(action_type, approvable)
