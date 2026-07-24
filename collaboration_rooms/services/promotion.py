"""
collaboration_rooms/services/promotion.py — Phase 17-18: turning an
ACCEPTED NextStepProposal into a real governed record. This module
creates NOTHING itself — every real action/project row is created by
PR9's existing partner_participation.services.next_step functions (which
themselves only ever propose into PR5's existing ActionPathway/
ConnectionCandidate/ProjectCandidate machinery). Never a parallel
promotion path: this is purely the "is this proposal actually ready, and
which existing function does its type map to" dispatcher.
"""
from partner_participation.services import next_step as pp_next_step

from collaboration_rooms.services import rooms as rooms_service
from collaboration_rooms.services.timeline import record_event


class PromotionNotAllowedError(Exception):
    pass


# proposal_type -> (pp_next_step function, extra-kwarg name required on the proposal, room status after promotion)
_MEETING_LIKE_TYPES = frozenset({'technical_discussion', 'introduction', 'site_assessment'})


def promote_proposal(proposal, *, actor):
    if proposal.status != 'accepted':
        raise PromotionNotAllowedError(
            f'NextStepProposal {proposal.pk} is {proposal.status!r}, not "accepted" — every required party must '
            f'consent before this can be promoted.'
        )
    if actor is None or not getattr(actor, 'is_staff', False):
        raise PromotionNotAllowedError('Promoting a next-step proposal requires a real EcoIQ staff actor.')

    candidate = proposal.room.routing_candidate
    proposal_type = proposal.proposal_type

    try:
        if proposal_type in _MEETING_LIKE_TYPES:
            result = pp_next_step.create_meeting_request(candidate, actor=actor, notes=proposal.description or proposal.get_proposal_type_display())
            reference = f'partner_participation.NextStepAction:{result.pk}'
            new_room_status = 'promoted_to_action'
        elif proposal_type == 'share_dataset':
            result = pp_next_step.create_data_exchange_request(candidate, actor=actor, notes=proposal.description or 'Requested dataset to be shared.')
            reference = f'partner_participation.NextStepAction:{result.pk}'
            new_room_status = 'promoted_to_action'
        elif proposal_type == 'verify_resource':
            if proposal.linked_resource_match_id is None:
                raise PromotionNotAllowedError('A "verify resource" proposal requires a linked ResourceMatch before it can be promoted.')
            result = pp_next_step.create_resource_match_followup(
                candidate, actor=actor, resource_match=proposal.linked_resource_match, notes=proposal.description,
            )
            reference = f'partner_participation.NextStepAction:{result.pk}'
            new_room_status = 'promoted_to_action'
        elif proposal_type == 'funding_eligibility_review':
            if proposal.linked_funding_match_id is None:
                raise PromotionNotAllowedError('A funding-eligibility-review proposal requires a linked FundingMatch before it can be promoted.')
            result = pp_next_step.create_funding_eligibility_review(
                candidate, actor=actor, funding_match=proposal.linked_funding_match, notes=proposal.description,
            )
            reference = f'partner_participation.NextStepAction:{result.pk}'
            new_room_status = 'promoted_to_action'
        elif proposal_type == 'project_candidate':
            result = pp_next_step.propose_project_candidate(candidate, actor=actor, rationale=proposal.description)
            reference = f'partner_participation.NextStepAction:{result.pk}'
            new_room_status = 'promoted_to_project'
        elif proposal_type == 'reject_close':
            result = None
            reference = ''
            new_room_status = 'closed'
        else:
            raise PromotionNotAllowedError(f'Unsupported proposal type: {proposal_type!r}.')
    except pp_next_step.NextStepNotAllowedError as exc:
        raise PromotionNotAllowedError(str(exc)) from exc

    proposal.promoted_reference = reference
    proposal.status = 'completed'
    proposal.save(update_fields=['promoted_reference', 'status', 'updated_at'])

    if proposal_type == 'reject_close':
        rooms_service.close_room(proposal.room, actor=actor, reason='Rejected via next-step proposal.')
    else:
        proposal.room.promoted_action_reference = reference
        proposal.room.status = new_room_status
        proposal.room.save(update_fields=['promoted_action_reference', 'status', 'updated_at'])
        event_type = 'project_candidate_created' if proposal_type == 'project_candidate' else 'action_created'
        record_event(proposal.room, event_type, actor=actor, source_object_reference=reference)
    return result
