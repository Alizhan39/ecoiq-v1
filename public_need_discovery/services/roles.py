"""
public_need_discovery/services/roles.py — Phase 6: organisation role
separation. An organisation may hold several roles for the same
candidate, but each is its own independently-evidenced row — never
inferred from the organisation's name or sector alone, and never
collapsed into a single field the way outreach_readiness's
`recipient_role` deliberately is (that field describes ONE final choice
made after this layer's broader review, not the full set of real
relationships found here).
"""
from django.utils import timezone

from public_need_discovery.models import ROLES_THAT_JUSTIFY_ACTIONABILITY, CandidateOrganisationRole


class RoleNotAllowedError(Exception):
    pass


def record_role(candidate, organisation, role, *, actor, evidence_reference='', rationale='', confirmed=False):
    """
    Idempotent per (candidate, organisation, role) — re-recording the same
    claim updates it in place rather than creating a duplicate row.
    `confirmed` stays False until a real human sets it True; a suggested
    role (e.g. auto-populated from capability_graph matches) is not the
    same claim as a human-checked one.
    """
    role_record, _ = CandidateOrganisationRole.objects.update_or_create(
        candidate=candidate, organisation=organisation, role=role,
        defaults=dict(evidence_reference=evidence_reference, rationale=rationale),
    )
    if confirmed:
        if actor is None:
            raise RoleNotAllowedError('Confirming an organisation role requires a real actor.')
        role_record.confirmed = True
        role_record.confirmed_by = actor
        role_record.confirmed_at = timezone.now()
        role_record.save(update_fields=['confirmed', 'confirmed_by', 'confirmed_at'])
    return role_record


def suggest_roles_from_capability_graph(candidate):
    """
    Read-only suggestion pass — reuses the same real, evidence-backed
    OrganisationCapability rows the Capability Graph already holds
    (never a new resolution mechanism). Every suggestion is created
    `confirmed=False`; only a human confirming it via `record_role(...,
    confirmed=True)` makes it count toward `has_confirmed_justifying_role`.
    """
    opportunity = candidate.opportunity
    suggestions = []
    for party in opportunity.responsible_parties.select_related('organisation').all():
        if party.organisation_id is None:
            continue
        organisation = party.organisation
        # A ResponsibleParty resolved from the triggering signal's own
        # publisher field is, by construction, the evidence publisher —
        # never assumed to be anything more without independent capability
        # evidence (Phase 2's own "do not default to the publisher" test).
        suggestions.append(record_role(
            candidate, organisation, 'evidence_publisher', actor=None,
            evidence_reference=party.evidence_ref, rationale=f'Resolved as the responsible party for this opportunity: {party.name}.',
        ))
        for capability_edge in organisation.capabilities.exclude(verification_state__in=('disputed', 'expired')):
            role = _capability_to_role(capability_edge.capability)
            if role is None:
                continue
            suggestions.append(record_role(
                candidate, organisation, role, actor=None,
                evidence_reference=capability_edge.evidence_source or f'capability_graph.OrganisationCapability:{capability_edge.pk}',
                rationale=(
                    f'Evidence-backed "{capability_edge.get_capability_display()}" capability '
                    f'({capability_edge.get_verification_state_display()})'
                    f'{f" for {capability_edge.topic_domain}" if capability_edge.topic_domain else ""}.'
                ),
            ))
    return suggestions


# Deterministic capability -> role mapping — never inferred from the
# organisation's name/sector, only from a real evidence-backed
# OrganisationCapability edge that already required its own evidence_source.
_CAPABILITY_TO_ROLE = {
    'regulate': 'responsible_authority', 'authorise': 'responsible_authority', 'permit': 'responsible_authority',
    'respond_to_emergency': 'responsible_authority', 'audit': 'responsible_authority', 'verify': 'responsible_authority',
    'install': 'potential_implementer', 'transport': 'potential_implementer', 'collect': 'potential_implementer',
    'recycle': 'potential_implementer', 'reuse': 'potential_implementer', 'supply': 'potential_implementer',
    'manufacture': 'potential_implementer', 'provide_technology': 'potential_implementer',
    'provide_expertise': 'potential_implementer', 'train': 'potential_implementer', 'employ': 'potential_implementer',
    'fund': 'funder', 'grant': 'funder', 'lend': 'funder', 'donate': 'funder', 'procure': 'funder',
    'host': 'resource_provider',
    'refer': 'referral_body', 'coordinate': 'referral_body',
    'research': None, 'measure': None,
}


def _capability_to_role(capability):
    return _CAPABILITY_TO_ROLE.get(capability)


def has_confirmed_justifying_role(candidate):
    """
    Phase 6/2's structural test, one stage before outreach_readiness's own
    identical discipline: a candidate cannot be actionable on the strength
    of an evidence_publisher/jurisdiction_authority role alone.
    """
    return candidate.organisation_roles.filter(role__in=ROLES_THAT_JUSTIFY_ACTIONABILITY, confirmed=True).exists()


def confirmed_justifying_roles(candidate):
    return candidate.organisation_roles.filter(role__in=ROLES_THAT_JUSTIFY_ACTIONABILITY, confirmed=True).select_related('organisation')
