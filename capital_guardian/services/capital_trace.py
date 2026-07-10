"""
capital_guardian/services/capital_trace.py — real capital-movement
aggregation. Every figure here is a plain sum/count over real, already-stored
CapitalTraceEntry rows — nothing computed is invented, and "capital
deployed" specifically means capital that has actually been paid
(payment_status='paid'), not merely approved or committed.
"""


def _sum(queryset, field):
    from django.db.models import Sum
    return queryset.aggregate(total=Sum(field))['total']


def capital_deployed(project):
    return _sum(project.capital_trace_entries.filter(payment_status='paid'), 'amount_usd')


def evidence_coverage(entries):
    """(entries_with_evidence, total_entries) — real EvidenceMemory rows
    only, via the entry's existing source_reference lookup."""
    entries = list(entries)
    if not entries:
        return 0, 0
    with_evidence = sum(1 for e in entries if e.evidence_documents.exists())
    return with_evidence, len(entries)


def verification_coverage(entries):
    entries = list(entries)
    if not entries:
        return 0, 0
    verified = sum(1 for e in entries if e.verification_status == 'verified')
    return verified, len(entries)


def trace_chain_for_entry(entry):
    """
    The conceptual chain this whole app is built around, made concrete for
    one real entry:
    Investor Capital → Project SPV → Escrow/Controlled Account →
    Approved Budget → Supplier/Contractor → Physical Asset or Service →
    Independent Verification → Project Milestone.
    Every step below reflects this entry's REAL stored status — a step is
    marked incomplete/unavailable rather than assumed done.
    """
    governance = getattr(entry.project, 'governance', None)
    return [
        {'step': 'Investor Capital', 'complete': True, 'detail': f'{entry.currency} {entry.amount_usd:,.0f}'},
        {'step': 'Project SPV', 'complete': bool(governance), 'detail': entry.project.name},
        {
            'step': 'Escrow / Controlled Account', 'complete': bool(governance and governance.escrow_account_active),
            'detail': 'Active' if governance and governance.escrow_account_active else 'Not confirmed active',
        },
        {
            'step': 'Approved Budget', 'complete': entry.approval_status == 'approved',
            'detail': entry.get_approval_status_display(),
        },
        {
            'step': 'Supplier / Contractor', 'complete': bool(entry.supplier),
            'detail': entry.supplier or 'Not recorded',
        },
        {
            'step': 'Physical Asset or Service', 'complete': entry.related_equipment_id is not None,
            'detail': str(entry.related_equipment) if entry.related_equipment_id else 'No linked equipment',
        },
        {
            'step': 'Independent Verification', 'complete': entry.verification_status == 'verified',
            'detail': entry.get_verification_status_display(),
        },
        {
            'step': 'Project Milestone', 'complete': entry.related_milestone_id is not None,
            'detail': str(entry.related_milestone) if entry.related_milestone_id else 'No linked milestone',
        },
    ]


def capital_protection_chain_for_entry(entry):
    """
    Phase 3 — the Capital Protection page's granular chain: Investor →
    Escrow → Board Approval → Supplier → Factory → Shipment → Site →
    Commissioning → Operating Asset. When a real EquipmentSpec is linked,
    the last 5 steps read its REAL manufacturing/shipping/delivery/
    installation/commissioning status fields directly — a genuinely more
    granular view than trace_chain_for_entry's generic "Physical Asset"
    step, not a duplicate of it. Falls back to the generic 3-step ending
    (Physical Asset / Verification / Milestone) when no equipment is linked.
    """
    governance = getattr(entry.project, 'governance', None)
    chain = [
        {'step': 'Investor Capital', 'complete': True, 'detail': f'{entry.currency} {entry.amount_usd:,.0f}'},
        {
            'step': 'Escrow / Controlled Account', 'complete': bool(governance and governance.escrow_account_active),
            'detail': 'Active' if governance and governance.escrow_account_active else 'Not confirmed active',
        },
        {
            'step': 'Board Approval', 'complete': entry.approval_status == 'approved',
            'detail': entry.get_approval_status_display(),
        },
        {
            'step': 'Supplier', 'complete': bool(entry.supplier),
            'detail': entry.supplier or 'Not recorded',
        },
    ]
    equipment = entry.related_equipment
    if equipment is not None:
        chain += [
            {'step': 'Factory', 'complete': equipment.manufacturing_status == 'complete', 'detail': equipment.get_manufacturing_status_display()},
            {'step': 'Shipment', 'complete': equipment.shipping_status == 'complete', 'detail': equipment.get_shipping_status_display()},
            {'step': 'Site', 'complete': equipment.delivery_status == 'complete', 'detail': equipment.get_delivery_status_display()},
            {'step': 'Commissioning', 'complete': equipment.commissioning_status == 'complete', 'detail': equipment.get_commissioning_status_display()},
            {
                'step': 'Operating Asset', 'complete': equipment.installation_status == 'complete' and equipment.commissioning_status == 'complete',
                'detail': str(equipment),
            },
        ]
    else:
        chain += [
            {
                'step': 'Physical Asset or Service', 'complete': False,
                'detail': 'No linked equipment',
            },
            {
                'step': 'Independent Verification', 'complete': entry.verification_status == 'verified',
                'detail': entry.get_verification_status_display(),
            },
            {
                'step': 'Operating Asset', 'complete': entry.related_milestone_id is not None,
                'detail': str(entry.related_milestone) if entry.related_milestone_id else 'No linked milestone',
            },
        ]
    return chain
