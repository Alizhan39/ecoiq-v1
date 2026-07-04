"""
waste_to_value_capital_allocation_engine/services/agent_bridge.py — bridges
the real capital-at-risk service to the Agent Runtime & Model Router's
execution pipeline, for the Waste & Leakage Agent specifically.

Keeps agent-orchestration glue out of the pure finance modules
(`capital_risk.py`, `loss_intake.py`) and out of `agent_runtime_model_router`
(which shouldn't need Waste-to-Value-specific knowledge). This module is the
only place that turns a loss-detection scenario into the exact
`fixture_output` shape `execute_agent(fixture_output=...)` expects.
"""
from waste_to_value_capital_allocation_engine.services.capital_risk import calculate_capital_at_risk

VALID_CLASSIFICATIONS = {'actual', 'estimated', 'forecast'}

CONFIDENCE_LABELS = [(85, 'High'), (45, 'Medium'), (0, 'Low')]


def _confidence_label(confidence):
    for threshold, label in CONFIDENCE_LABELS:
        if confidence >= threshold:
            return label
    return 'Low'


def build_loss_detection_fixture(organisation, asset, loss_type, inventory_value, historical_loss_rate,
                                  evidence_used, missing_data, classification='forecast', confidence=60,
                                  capital_already_lost=0, recoverable_value_note='', risk_flags=None,
                                  next_action='', human_approval_required=False, status='completed'):
    """
    Builds the Waste & Leakage Agent's structured output. `capital_at_risk`
    is always computed by the real `calculate_capital_at_risk()` — this
    function never re-derives or overrides that arithmetic.

    Reference worked example (Meat Cold-Chain golden case): inventory_value=80000,
    historical_loss_rate=0.15 -> capital_at_risk=12000.0, classification='forecast'.
    """
    if classification not in VALID_CLASSIFICATIONS:
        raise ValueError(f"classification must be one of {sorted(VALID_CLASSIFICATIONS)}, got {classification!r}")

    capital_at_risk = calculate_capital_at_risk(inventory_value, historical_loss_rate)
    confidence_label = _confidence_label(confidence)

    output_summary = (
        f'Projected capital at risk: £{capital_at_risk:,.0f}. '
        f'Classification: {classification.capitalize()}. '
        f'Confidence: {confidence_label}.'
    )

    return {
        'agent_name': 'Waste & Leakage Agent',
        'organisation': organisation,
        'asset': asset,
        'loss_type': loss_type,
        'classification': classification,
        'capital_at_risk': capital_at_risk,
        'capital_already_lost': capital_already_lost,
        'recoverable_value_estimate': recoverable_value_note,
        'output_summary': output_summary,
        'evidence_used': evidence_used,
        'missing_data': missing_data,
        'confidence': confidence,
        'risk_flags': risk_flags or [],
        'human_approval_required': human_approval_required,
        'next_action': next_action,
        'status': status,
    }
