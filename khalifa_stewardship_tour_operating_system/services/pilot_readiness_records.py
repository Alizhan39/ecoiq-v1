"""
khalifa_stewardship_tour_operating_system/services/pilot_readiness_records.py
— idempotent creators for the real pilot readiness layer: beneficiaries,
consent, supplier quotes, incidents. Same get_or_create + explicit field
sync shape as services/tours.py — never delete-then-recreate.
"""
from django.utils import timezone

from khalifa_stewardship_tour_operating_system.models import (
    ConsentRecord, IncidentReport, SupplierQuote, TourBeneficiary,
)

HIGH_SEVERITY_LEVELS = {'high', 'critical'}


def create_tour_beneficiary(stewardship_problem, display_reference, **fields):
    beneficiary, _ = TourBeneficiary.objects.get_or_create(
        stewardship_problem=stewardship_problem, display_reference=display_reference, defaults={},
    )
    for field, value in fields.items():
        setattr(beneficiary, field, value)
    beneficiary.save()
    return beneficiary


def record_consent(beneficiary, tour, consent_type, status='requested', **fields):
    """
    Idempotent via get_or_create on the (beneficiary, tour, consent_type)
    unique-together key — this is the structural mechanism that makes
    consent specific: there is no way to record "consented" without naming
    the exact consent_type.
    """
    consent, _ = ConsentRecord.objects.get_or_create(
        beneficiary=beneficiary, tour=tour, consent_type=consent_type, defaults={},
    )
    consent.status = status
    for field, value in fields.items():
        setattr(consent, field, value)
    if status == 'granted' and not consent.granted_at:
        consent.granted_at = timezone.now()
    consent.save()
    return consent


def withdraw_consent(beneficiary, tour, consent_type):
    """Never deletes the row — sets status='withdrawn' + withdrawn_at, preserving the audit trail."""
    consent = ConsentRecord.objects.get(beneficiary=beneficiary, tour=tour, consent_type=consent_type)
    consent.status = 'withdrawn'
    consent.withdrawn_at = timezone.now()
    consent.save()
    return consent


def create_supplier_quote(intervention, supplier_name, amount, **fields):
    quote, _ = SupplierQuote.objects.get_or_create(
        intervention=intervention, supplier_name=supplier_name, defaults={'amount': amount},
    )
    quote.amount = amount
    for field, value in fields.items():
        setattr(quote, field, value)
    quote.save()
    return quote


def report_incident(tour, incident_type, description, severity='low', escalated_to='', **fields):
    """
    Real escalation validation, not a notification system: high/critical
    incidents must name who they were escalated to.
    """
    if severity in HIGH_SEVERITY_LEVELS and not escalated_to:
        raise ValueError(
            f"Incident severity '{severity}' requires a non-empty escalated_to before it can be reported."
        )
    return IncidentReport.objects.create(
        tour=tour, incident_type=incident_type, description=description,
        severity=severity, escalated_to=escalated_to, **fields,
    )
