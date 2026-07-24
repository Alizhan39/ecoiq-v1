"""
capability_graph/services/capabilities.py — recording and verifying
evidence-backed capability claims. `record_capability()` is the ONLY
sanctioned way to create/update an OrganisationCapability row — it
refuses to create one with no evidence at all, enforcing "never infer
that an organisation can perform a capability merely from its name or
sector."
"""
from django.utils import timezone

from capability_graph.models import OrganisationCapability


class NoEvidenceError(Exception):
    """Raised when a caller tries to record a capability with no evidence source or URL at all."""


class VerificationNotAllowedError(Exception):
    """Raised when promoting to 'independently_verified' without a real human actor."""


def record_capability(
    organisation, capability, *, jurisdiction='', topic_domain='',
    evidence_source='', evidence_url='', limitations='', verification_state='documented',
):
    """
    Creates or updates the (organisation, capability, jurisdiction,
    topic_domain) edge. Requires at least one real evidence pointer —
    raises `NoEvidenceError` otherwise, rather than silently recording an
    unsupported claim. Never auto-sets verification_state to
    'independently_verified' — that requires a human, via `verify_capability()`.
    """
    if not evidence_source and not evidence_url:
        raise NoEvidenceError(
            f'Refusing to record {organisation} -> {capability} with no evidence_source or evidence_url. '
            f'Capabilities must never be inferred from an organisation\'s name or sector alone.'
        )
    if verification_state == 'independently_verified':
        raise VerificationNotAllowedError(
            'record_capability() cannot set independently_verified directly — call verify_capability() '
            'with a real human actor instead.'
        )
    edge, _ = OrganisationCapability.objects.update_or_create(
        organisation=organisation, capability=capability, jurisdiction=jurisdiction, topic_domain=topic_domain,
        defaults=dict(
            evidence_source=evidence_source, evidence_url=evidence_url,
            limitations=limitations, verification_state=verification_state,
        ),
    )
    return edge


def verify_capability(edge, *, actor):
    """
    The ONLY way an OrganisationCapability can reach 'independently_verified'
    — requires a real, logged-in human actor (mirrors PR5's
    responsible_party.confirm()/action_gate.transition() actor requirement).
    """
    if actor is None:
        raise VerificationNotAllowedError('Independent verification requires a real human actor.')
    edge.verification_state = 'independently_verified'
    edge.last_verified_at = timezone.now()
    edge.verified_by = actor
    edge.save(update_fields=['verification_state', 'last_verified_at', 'verified_by', 'updated_at'])
    return edge
