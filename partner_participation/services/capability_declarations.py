"""
partner_participation/services/capability_declarations.py — an
organisation declaring its own capability through the partner portal.
Wraps capability_graph's existing record_capability()/verify_capability()
rather than a second capability model, per PR8's own "preserve the
existing OrganisationCapability architecture" instruction.

A bare self-declaration (no evidence URL yet) is NOT rejected the way
capability_graph.record_capability() normally would be — it is real,
attributable evidence in its own right: a specific, verified-member user
of the organisation made a specific claim on a specific date. That
attribution (never an empty evidence_source) is what
NoEvidenceError actually guards against — an UNATTRIBUTABLE claim, not
an EXTERNALLY-unevidenced one. `verification_state` stays 'self_reported'
until the organisation attaches real evidence or EcoIQ reviews/verifies
it, so it is never displayed as more solid than it is.
"""
from capability_graph.services.capabilities import record_capability
from partner_participation.services.membership import NotAuthorisedError, ReviewNotAllowedError, can_edit


def declare_capability(
    organisation, capability, membership, *, jurisdiction='', topic_domain='', limitations='',
):
    """
    A verified org member (editor/admin) declares a capability with no
    external evidence yet. Starts at verification_state='self_reported',
    provenance='organisation_declared' — never higher.
    """
    if not can_edit(organisation, membership.user):
        raise NotAuthorisedError(f'{membership.user} is not an editor/admin for {organisation}.')
    edge = record_capability(
        organisation, capability, jurisdiction=jurisdiction, topic_domain=topic_domain,
        evidence_source=f'partner_participation.OrganisationMembership:{membership.pk}',
        limitations=limitations, verification_state='self_reported',
    )
    edge.provenance = 'organisation_declared'
    edge.declared_by = membership.user
    edge.save(update_fields=['provenance', 'declared_by', 'updated_at'])
    return edge


def attach_evidence(edge, *, evidence_url, actor):
    """
    The organisation attaches real evidence to its own declaration —
    moves self_reported -> evidence_supported. Never auto-promotes to
    documented/independently_verified; those remain EcoIQ's or a human
    verifier's calls (capability_graph.services.capabilities
    .verify_capability()).
    """
    if edge.provenance != 'organisation_declared':
        raise ValueError('attach_evidence() only applies to organisation-declared capabilities.')
    if not evidence_url:
        raise ValueError('evidence_url is required.')
    edge.evidence_url = evidence_url
    if edge.verification_state == 'self_reported':
        edge.verification_state = 'evidence_supported'
    edge.save(update_fields=['evidence_url', 'verification_state', 'updated_at'])
    return edge


def human_review(edge, *, actor, notes=''):
    """EcoIQ staff reviewed the declaration (short of independent verification)."""
    if actor is None or not getattr(actor, 'is_staff', False):
        raise ReviewNotAllowedError('Human review requires a real EcoIQ staff actor.')
    edge.verification_state = 'human_reviewed'
    if notes:
        edge.limitations = f'{edge.limitations}\n\nEcoIQ review note: {notes}'.strip()
    edge.save(update_fields=['verification_state', 'limitations', 'updated_at'])
    return edge


def dispute(edge, *, reason, actor=None):
    edge.verification_state = 'disputed'
    edge.save(update_fields=['verification_state', 'updated_at'])
    from capability_graph.models import CapabilityConflict
    return CapabilityConflict.objects.create(capability=edge, description=reason)


def expire(edge):
    edge.verification_state = 'expired'
    edge.save(update_fields=['verification_state', 'updated_at'])
    return edge
