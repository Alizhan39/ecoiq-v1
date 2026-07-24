"""
partner_participation/services/conflicts.py — Phase 24: when an
organisation's own declaration disagrees with existing evidence for the
same (organisation, capability, jurisdiction, topic_domain) neighbourhood,
neither claim is silently overwritten. Detection is deliberately narrow
and deterministic: same organisation + capability, overlapping
jurisdiction/topic, but a DIFFERENT provenance and materially different
limitations/verification_state — never an LLM judgement call.
"""
from capability_graph.models import CapabilityConflict, OrganisationCapability


def detect_conflicts_for(edge):
    """
    Looks for other OrganisationCapability rows for the same organisation
    + capability with a different provenance (i.e. one organisation-
    declared, one externally/EcoIQ-sourced) whose verification_state or
    limitations materially differ. Returns the list of CapabilityConflict
    rows created (empty if none found) — never silently drops a
    disagreement.
    """
    candidates = OrganisationCapability.objects.filter(
        organisation=edge.organisation, capability=edge.capability,
    ).exclude(pk=edge.pk).exclude(provenance=edge.provenance)

    created = []
    for other in candidates:
        if _materially_differs(edge, other):
            conflict, was_created = CapabilityConflict.objects.get_or_create(
                capability=edge, conflicting_with=other,
                defaults=dict(
                    description=(
                        f'{edge.organisation} declared "{edge.get_capability_display()}" '
                        f'({edge.get_provenance_display()}, {edge.get_verification_state_display()}) '
                        f'while a separate {other.get_provenance_display()} record for the same capability '
                        f'states different limitations or jurisdiction — review required.'
                    ),
                ),
            )
            if was_created:
                created.append(conflict)
    return created


def _materially_differs(edge_a, edge_b):
    if edge_a.jurisdiction and edge_b.jurisdiction and edge_a.jurisdiction != edge_b.jurisdiction:
        return True
    if edge_a.limitations.strip() and edge_b.limitations.strip() and edge_a.limitations.strip() != edge_b.limitations.strip():
        return True
    return False


def resolve_conflict(conflict, *, resolution, actor, notes=''):
    """Human resolution with a real audit trail — never auto-resolved."""
    if actor is None or not getattr(actor, 'is_staff', False):
        raise PermissionError('Conflict resolution requires a real EcoIQ staff actor.')
    from django.utils import timezone
    conflict.resolution = resolution
    conflict.resolved_by = actor
    conflict.resolved_at = timezone.now()
    conflict.resolution_notes = notes
    conflict.save(update_fields=['resolution', 'resolved_by', 'resolved_at', 'resolution_notes'])
    return conflict
