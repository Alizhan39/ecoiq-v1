"""
partner_participation/services/opportunity_preferences.py — routing
preferences, never acceptance guarantees (Phase 7's own instruction).
"""
from partner_participation.models import OpportunityPreference
from partner_participation.services.membership import NotAuthorisedError, can_edit


def set_preference(organisation, theme, membership, **fields):
    if not can_edit(organisation, membership.user):
        raise NotAuthorisedError(f'{membership.user} is not an editor/admin for {organisation}.')
    fields['set_by'] = membership.user
    preference, _ = OpportunityPreference.objects.update_or_create(
        organisation=organisation, theme=theme, defaults=fields,
    )
    return preference
