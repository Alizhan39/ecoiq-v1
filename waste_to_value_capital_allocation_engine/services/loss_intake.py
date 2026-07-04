"""
waste_to_value_capital_allocation_engine/services/loss_intake.py — lifecycle
steps 1-2: detect operational loss, quantify current financial exposure.
"""
from waste_to_value_capital_allocation_engine.models import OperationalLoss

EVIDENCE_QUALITY_CONFIDENCE = {'strong': 90, 'medium': 60, 'weak': 30, 'missing': 10}


def create_operational_loss(**fields):
    """Thin, explicit persistence wrapper — no hidden defaults beyond the model's own."""
    return OperationalLoss.objects.create(**fields)


def quantify_financial_loss(quantity_lost, unit_value, evidence_quality='medium'):
    """
    Plain arithmetic: financial_loss_amount = quantity_lost * unit_value.
    Confidence is derived from evidence quality, never asserted independently.
    Returns {financial_loss_amount, confidence, evidence_quality} — the caller
    decides whether/how to persist this onto an OperationalLoss row.
    """
    financial_loss_amount = round(quantity_lost * unit_value, 2)
    confidence = EVIDENCE_QUALITY_CONFIDENCE.get(evidence_quality, 50)
    return {
        'financial_loss_amount': financial_loss_amount,
        'confidence': confidence,
        'evidence_quality': evidence_quality,
    }
