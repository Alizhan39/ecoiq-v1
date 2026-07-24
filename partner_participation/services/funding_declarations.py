"""
partner_participation/services/funding_declarations.py — a real, durable
funding programme an organisation runs. Never claims a programme is
halal — only ever flags REQUIRES_SHARIA_REVIEW (structurally enforced in
FundingProgrammeDeclaration.save(), mirroring good_agents.FundingMatch).
"""
from partner_participation.models import FundingProgrammeDeclaration
from partner_participation.services.membership import NotAuthorisedError, can_edit


def declare_programme(organisation, programme_name, funder_type, membership, **fields):
    if not can_edit(organisation, membership.user):
        raise NotAuthorisedError(f'{membership.user} is not an editor/admin for {organisation}.')
    return FundingProgrammeDeclaration.objects.create(
        organisation=organisation, programme_name=programme_name, funder_type=funder_type,
        declared_by=membership.user, **fields,
    )


def human_review(declaration, *, actor, notes=''):
    from django.utils import timezone
    if actor is None or not getattr(actor, 'is_staff', False):
        raise PermissionError('Funding programme review requires a real EcoIQ staff actor.')
    declaration.status = 'human_reviewed'
    declaration.reviewed_by = actor
    declaration.reviewed_at = timezone.now()
    declaration.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])
    return declaration
