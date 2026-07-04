"""
waste_to_value_capital_allocation_engine/services/capital_risk.py — lifecycle
steps 2-3: quantify capital currently at risk, predict recoverable value, and
compute the Waste Risk Score.

Never present projected loss as an actual verified loss — every value
returned here is labelled by the caller as estimated/projected/forecast,
never "actual" or "verified" (those only ever come from
mrv_outcomes.record_verified_outcome()).
"""
WASTE_RISK_WEIGHTS = {
    'financial_loss_exposure':   0.30,
    'physical_loss_rate':        0.25,
    'spoilage_probability':      0.20,
    'downtime':                  0.10,
    'inventory_ageing':          0.08,
    'forecast_uncertainty':      0.07,
}
WASTE_RISK_DAMPENER_WEIGHTS = {
    'evidence_quality':           0.05,
    'intervention_availability':  0.05,
    'management_controls':        0.05,
}


def calculate_capital_at_risk(inventory_value, historical_loss_rate):
    """
    capital_at_risk = inventory_value * historical_loss_rate.
    Reference worked example: inventory_value=80000, historical_loss_rate=0.15
    -> capital_at_risk = 12000.0 (exact).
    """
    return round(inventory_value * historical_loss_rate, 2)


def predict_recoverable_value(expected_value_recovered, intervention_cost):
    """
    estimated_net_value_recovered = expected_value_recovered - intervention_cost.
    Reference worked example: 8500 - 1200 = 7300.0 (exact).
    """
    return round(expected_value_recovered - intervention_cost, 2)


def calculate_waste_risk_score(financial_loss_exposure, physical_loss_rate, spoilage_probability,
                                downtime, inventory_ageing, forecast_uncertainty,
                                evidence_quality, intervention_availability, management_controls):
    """
    Weighted 0-100 score. Positive drivers raise the score; evidence
    quality / intervention availability / management controls act as
    smaller-weighted dampeners (good controls reduce — but never reverse —
    the underlying exposure). All inputs are 0-100.

    Reference worked example (verified against this implementation):
    financial_loss_exposure=96, physical_loss_rate=75, spoilage_probability=80,
    downtime=60, inventory_ageing=55, forecast_uncertainty=65,
    evidence_quality=45, intervention_availability=50, management_controls=40
    -> waste_risk_score = 72.
    """
    raw = (
        WASTE_RISK_WEIGHTS['financial_loss_exposure'] * financial_loss_exposure
        + WASTE_RISK_WEIGHTS['physical_loss_rate'] * physical_loss_rate
        + WASTE_RISK_WEIGHTS['spoilage_probability'] * spoilage_probability
        + WASTE_RISK_WEIGHTS['downtime'] * downtime
        + WASTE_RISK_WEIGHTS['inventory_ageing'] * inventory_ageing
        + WASTE_RISK_WEIGHTS['forecast_uncertainty'] * forecast_uncertainty
        - WASTE_RISK_DAMPENER_WEIGHTS['evidence_quality'] * evidence_quality
        - WASTE_RISK_DAMPENER_WEIGHTS['intervention_availability'] * intervention_availability
        - WASTE_RISK_DAMPENER_WEIGHTS['management_controls'] * management_controls
    )
    return max(0, min(100, round(raw)))
