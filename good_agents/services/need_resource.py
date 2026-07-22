"""
good_agents/services/need_resource.py — creation helpers for the Need
(Phase 6) and AvailableResource (Phase 7) models, with the same dedup-key
discipline as WorldSignal (Phase 27 anti-duplication).
"""
from good_agents.services.signals import compute_dedup_key

from good_agents.models import AvailableResource, Need, ResourceStatusChange


def create_need(*, need_type, title, opportunity=None, signal=None, geography=None, region='',
                affected_group='', urgency=0.0, severity=0.0, evidence_refs=None,
                required_capabilities=None, resource_requirements=None, constraints=''):
    dedup_key = compute_dedup_key(need_type, region or (geography.name if geography else ''), '', title)
    existing = Need.objects.filter(dedup_key=dedup_key, status='open').first()
    if existing is not None:
        return existing, False

    need = Need.objects.create(
        need_type=need_type, title=title, opportunity=opportunity, signal=signal,
        geography=geography, region=region, affected_group=affected_group,
        urgency=urgency, severity=severity, evidence_refs=evidence_refs or [],
        required_capabilities=required_capabilities or [], resource_requirements=resource_requirements or [],
        constraints=constraints, dedup_key=dedup_key,
    )
    return need, True


def create_resource(*, resource_type, title, geography=None, region='', availability='unknown',
                    eligibility='', capacity='', constraints='', source='', evidence_refs=None,
                    expiry_date=None, confidence=0.0):
    """Never sets availability='available' without at least one evidence_ref — enforced here, not just documented."""
    evidence_refs = evidence_refs or []
    if availability == 'available' and not evidence_refs:
        availability = 'unknown'

    dedup_key = compute_dedup_key(resource_type, region or (geography.name if geography else ''), '', title)
    existing = AvailableResource.objects.filter(dedup_key=dedup_key, status='active').first()
    if existing is not None:
        return existing, False

    resource = AvailableResource.objects.create(
        resource_type=resource_type, title=title, geography=geography, region=region,
        availability=availability, eligibility=eligibility, capacity=capacity, constraints=constraints,
        source=source, evidence_refs=evidence_refs, expiry_date=expiry_date, confidence=confidence,
        dedup_key=dedup_key,
    )
    return resource, True


def update_resource_status(resource, *, new_status=None, new_availability=None, reason=''):
    """The only sanctioned way to change a resource's status — always logs to ResourceStatusChange (Phase 28)."""
    previous_status, previous_availability = resource.status, resource.availability
    if new_status is None and new_availability is None:
        return resource

    ResourceStatusChange.objects.create(
        resource=resource, previous_status=previous_status, new_status=new_status or previous_status,
        previous_availability=previous_availability, new_availability=new_availability or previous_availability,
        reason=reason,
    )
    if new_status:
        resource.status = new_status
    if new_availability:
        resource.availability = new_availability
    resource.save(update_fields=['status', 'availability', 'updated_at'])
    return resource
