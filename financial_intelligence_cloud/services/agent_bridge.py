"""
financial_intelligence_cloud/services/agent_bridge.py — bridges the real
capital-at-risk / recoverable-value formulas to the Agent Runtime & Model
Router's execution pipeline, for the FreshBridge Foods flagship accounting
case specifically. Mirrors
waste_to_value_capital_allocation_engine/services/agent_bridge.py's exact
shape — this app never re-derives the arithmetic itself, it imports and
calls the real functions.

Reference worked example (FreshBridge Foods golden case):
inventory_value=1,600,000, historical_loss_rate=0.15 -> capital_at_risk=240,000.0;
expected_value_recovered=175,000, intervention_cost=20,000 -> recoverable_value=155,000.0.
"""
from waste_to_value_capital_allocation_engine.services.capital_risk import (
    calculate_capital_at_risk, predict_recoverable_value,
)

CONFIDENCE_LABELS = [(85, 'High'), (45, 'Medium'), (0, 'Low')]


def _confidence_label(confidence):
    for threshold, label in CONFIDENCE_LABELS:
        if confidence >= threshold:
            return label
    return 'Low'


def build_waste_leakage_fixture(inventory_value, historical_loss_rate, evidence_used, missing_data,
                                 classification='forecast', confidence=60, risk_flags=None,
                                 next_action='', human_approval_required=False, status='completed'):
    """capital_at_risk is always computed by the real calculate_capital_at_risk() — never re-derived here."""
    capital_at_risk = calculate_capital_at_risk(inventory_value, historical_loss_rate)
    confidence_label = _confidence_label(confidence)
    output_summary = (
        f'Projected capital at risk: £{capital_at_risk:,.0f}. '
        f'Classification: {classification.capitalize()}. '
        f'Confidence: {confidence_label}.'
    )
    return {
        'agent_name': 'Waste & Leakage Agent',
        'classification': classification,
        'capital_at_risk': capital_at_risk,
        'capital_already_lost': 0,
        'output_summary': output_summary,
        'evidence_used': evidence_used,
        'missing_data': missing_data,
        'confidence': confidence,
        'risk_flags': risk_flags or [],
        'human_approval_required': human_approval_required,
        'next_action': next_action,
        'status': status,
    }


def build_finance_modelling_fixture(expected_value_recovered, intervention_cost, evidence_used, missing_data=None,
                                     confidence=78, risk_flags=None, next_action='',
                                     human_approval_required=True, status='completed'):
    """potential_recoverable_value is always computed by the real predict_recoverable_value() — never re-derived here."""
    recoverable_value = predict_recoverable_value(expected_value_recovered, intervention_cost)
    output_summary = (
        f'Potential recoverable value: £{recoverable_value:,.0f} / year. '
        f'Estimated, not verified — never presented as a guaranteed return.'
    )
    return {
        'agent_name': 'Finance Modelling Agent',
        'potential_recoverable_value': recoverable_value,
        'output_summary': output_summary,
        'evidence_used': evidence_used,
        'missing_data': missing_data or [],
        'confidence': confidence,
        'risk_flags': risk_flags or [],
        'human_approval_required': human_approval_required,
        'next_action': next_action,
        'status': status,
    }
