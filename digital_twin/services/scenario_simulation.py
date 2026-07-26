"""
digital_twin/services/scenario_simulation.py — the deterministic Scenario
Simulator.

Reuses `gold_intelligence.services.project_finance` for NPV/IRR/payback
maths (Newton's-method IRR, discounted-cashflow NPV, interpolated payback)
rather than re-deriving them — those functions operate on a plain
`cash_flows` list and have no GoldProject-specific dependency. The
downside/expected/upside cases are persisted onto the existing
`InterventionScenario` model (get_or_create, idempotent), not a new one.

Every calculated value returned by `simulate_scenario()` is wrapped by
`_result()` so it always exposes: formula, inputs, assumptions, output,
unit, confidence, missing_inputs — never just a bare number.
"""
from gold_intelligence.services.project_finance import (
    SENSITIVITY_SWING_PCT, compute_irr, compute_npv, compute_payback_years,
)

SIMULATION_FORMULA_VERSION = '1.0.0'
DEFAULT_DISCOUNT_RATE_PCT = 8.0
DEFAULT_EVALUATION_HORIZON_YEARS = 10

CASE_SWINGS = {
    # (capex_multiplier, savings_multiplier) — downside is worse on both
    # axes, upside better, matching gold_intelligence's ±20% tornado swing.
    'downside': (1 + SENSITIVITY_SWING_PCT / 100, 1 - SENSITIVITY_SWING_PCT / 100),
    'expected': (1.0, 1.0),
    'upside': (1 - SENSITIVITY_SWING_PCT / 100, 1 + SENSITIVITY_SWING_PCT / 100),
}

SENSITIVITY_CASE_MAP = {'downside': 'downside', 'expected': 'base', 'upside': 'upside'}


def _result(label, formula, inputs, output, unit, confidence, assumptions=None, missing_inputs=None):
    return {
        'label': label,
        'formula': formula,
        'inputs': inputs,
        'assumptions': assumptions or [],
        'output': output,
        'unit': unit,
        'confidence': confidence,
        'missing_inputs': missing_inputs or [],
    }


def _evaluation_horizon_years(scenario):
    component = scenario.component
    if component and component.expected_useful_life_years:
        return min(component.expected_useful_life_years, 30), False
    return DEFAULT_EVALUATION_HORIZON_YEARS, True


def _build_cash_flows(capex, opex_change, annual_savings, horizon_years):
    annual_net_cash_flow = annual_savings - opex_change
    return [-capex] + [annual_net_cash_flow] * int(horizon_years)


def _compute_case(scenario, intervention, case_key, horizon_years, horizon_is_default):
    capex_mult, savings_mult = CASE_SWINGS[case_key]
    capex = round(intervention.capex_estimate * capex_mult, 2)
    annual_savings = round(intervention.estimated_annual_savings * savings_mult, 2)
    opex_change = intervention.opex_change

    cash_flows = _build_cash_flows(capex, opex_change, annual_savings, horizon_years)
    npv = compute_npv(cash_flows, DEFAULT_DISCOUNT_RATE_PCT)
    irr_pct = compute_irr(cash_flows)
    payback_years = compute_payback_years(cash_flows)
    simple_payback_months = round(capex / (annual_savings / 12), 2) if annual_savings else None

    confidence = scenario.confidence
    confidence_adjusted_benefit = (
        round(annual_savings * (confidence / 100), 2) if confidence is not None else None
    )

    assumptions = [
        f'{SENSITIVITY_SWING_PCT:g}% {case_key} swing applied to CAPEX and annual savings.' if case_key != 'expected' else 'No swing applied — expected/base case.',
        f'Evaluation horizon: {horizon_years} years'
        + (' (default — no component expected_useful_life_years recorded).' if horizon_is_default else ' (from component.expected_useful_life_years).'),
        f'Discount rate: {DEFAULT_DISCOUNT_RATE_PCT:g}% (platform default).',
    ]

    missing_inputs = []
    if confidence is None:
        missing_inputs.append('scenario.confidence not set — confidence-adjusted benefit unavailable.')

    return {
        'capex': _result(
            'CAPEX', 'intervention.capex_estimate * case_multiplier',
            {'capex_estimate': intervention.capex_estimate, 'multiplier': capex_mult}, capex, 'USD', None, assumptions,
        ),
        'annual_savings': _result(
            'Annual savings', 'intervention.estimated_annual_savings * case_multiplier',
            {'estimated_annual_savings': intervention.estimated_annual_savings, 'multiplier': savings_mult},
            annual_savings, 'USD/year', None, assumptions,
        ),
        'operating_cost_change': _result(
            'Operating cost change', 'intervention.opex_change (positive = increase, negative = decrease)',
            {'opex_change': opex_change}, opex_change, 'USD/year', None,
        ),
        'throughput_change_pct': _result(
            'Throughput change', 'scenario.production_impact_pct (direct input, not derived)',
            {'production_impact_pct': scenario.production_impact_pct}, scenario.production_impact_pct, '%',
            scenario.confidence, missing_inputs=(['scenario.production_impact_pct not set'] if scenario.production_impact_pct is None else []),
        ),
        'downtime_change_hours': _result(
            'Downtime change', 'scenario.downtime_impact_hours (direct input, not derived)',
            {'downtime_impact_hours': scenario.downtime_impact_hours}, scenario.downtime_impact_hours, 'hours',
            scenario.confidence, missing_inputs=(['scenario.downtime_impact_hours not set'] if scenario.downtime_impact_hours is None else []),
        ),
        'energy_reduction': _result(
            'Energy impact', 'scenario.energy_impact (direct input; negative = reduction)',
            {'energy_impact': scenario.energy_impact}, scenario.energy_impact,
            scenario.energy_impact_unit.symbol if scenario.energy_impact_unit else None, scenario.confidence,
            missing_inputs=(['scenario.energy_impact not set'] if scenario.energy_impact is None else []),
        ),
        'water_reduction': _result(
            'Water impact', 'scenario.water_impact (direct input; negative = reduction)',
            {'water_impact': scenario.water_impact}, scenario.water_impact,
            scenario.water_impact_unit.symbol if scenario.water_impact_unit else None, scenario.confidence,
            missing_inputs=(['scenario.water_impact not set'] if scenario.water_impact is None else []),
        ),
        'waste_reduction': _result(
            'Waste impact', 'scenario.waste_impact (direct input; negative = reduction)',
            {'waste_impact': scenario.waste_impact}, scenario.waste_impact,
            scenario.waste_impact_unit.symbol if scenario.waste_impact_unit else None, scenario.confidence,
            missing_inputs=(['scenario.waste_impact not set'] if scenario.waste_impact is None else []),
        ),
        'emissions_reduction': _result(
            'Emissions impact', 'scenario.emissions_impact (direct input; negative = reduction)',
            {'emissions_impact': scenario.emissions_impact}, scenario.emissions_impact,
            scenario.emissions_impact_unit.symbol if scenario.emissions_impact_unit else None, scenario.confidence,
            missing_inputs=(['scenario.emissions_impact not set'] if scenario.emissions_impact is None else []),
        ),
        'simple_payback_months': _result(
            'Simple payback', 'capex / (annual_savings / 12)',
            {'capex': capex, 'annual_savings': annual_savings}, simple_payback_months, 'months', None,
            missing_inputs=(['annual_savings is 0 — payback undefined'] if not annual_savings else []),
        ),
        'npv': _result(
            'NPV', 'sum(cf / (1+rate)**t for t, cf in enumerate(cash_flows))',
            {'cash_flows': cash_flows, 'discount_rate_pct': DEFAULT_DISCOUNT_RATE_PCT}, npv, 'USD', None, assumptions,
        ),
        'irr_pct': _result(
            "IRR", "Newton's-method root-search on NPV(rate) = 0",
            {'cash_flows': cash_flows}, irr_pct, '%', None,
            missing_inputs=(["cash-flow shape has no real IRR root"] if irr_pct is None else []),
        ),
        'payback_years': _result(
            'Payback (years)', 'cumulative cash-flow break-even, linearly interpolated',
            {'cash_flows': cash_flows}, payback_years, 'years', None,
            missing_inputs=(['project never pays back within the modelled horizon'] if payback_years is None else []),
        ),
        'confidence_adjusted_benefit': _result(
            'Confidence-adjusted benefit', 'annual_savings * (scenario.confidence / 100)',
            {'annual_savings': annual_savings, 'confidence': confidence}, confidence_adjusted_benefit, 'USD/year',
            confidence, missing_inputs=missing_inputs,
        ),
    }


def simulate_scenario(scenario):
    """Pure function — computes downside/expected/upside cases for one
    ModernisationScenario. Never writes to the database."""
    intervention = scenario.intervention
    horizon_years, horizon_is_default = _evaluation_horizon_years(scenario)
    cases = {
        case_key: _compute_case(scenario, intervention, case_key, horizon_years, horizon_is_default)
        for case_key in ('downside', 'expected', 'upside')
    }
    return {
        'scenario_id': scenario.pk,
        'intervention_id': intervention.pk,
        'formula_version': SIMULATION_FORMULA_VERSION,
        'evaluation_horizon_years': horizon_years,
        'discount_rate_pct': DEFAULT_DISCOUNT_RATE_PCT,
        'cases': cases,
    }


def persist_scenario_cases(scenario):
    """Writes the downside/expected/upside cases onto the EXISTING
    InterventionScenario model (get_or_create by intervention + sensitivity
    case — idempotent, never duplicated), and updates the parent
    InterventionOption's headline fields from the expected case."""
    from waste_to_value_capital_allocation_engine.models import InterventionScenario

    simulation = simulate_scenario(scenario)
    intervention = scenario.intervention
    saved = []
    for case_key, case in simulation['cases'].items():
        sensitivity_case = SENSITIVITY_CASE_MAP[case_key]
        row, _ = InterventionScenario.objects.get_or_create(
            intervention=intervention, sensitivity_case=sensitivity_case,
            defaults={'scenario_name': f'{intervention.title} — {case_key}', 'scenario_type': intervention.intervention_type},
        )
        row.scenario_name = f'{intervention.title} — {case_key}'
        row.scenario_type = intervention.intervention_type
        row.capex = case['capex']['output']
        row.opex = case['operating_cost_change']['output'] or 0.0
        row.annual_savings = case['annual_savings']['output']
        row.payback = case['payback_years']['output']
        row.assumptions = case['capex']['assumptions']
        row.risk_flags = scenario.technical_risks or []
        row.save()
        saved.append(row)

    expected = simulation['cases']['expected']
    intervention.estimated_payback_months = expected['simple_payback_months']['output']
    intervention.save(update_fields=['estimated_payback_months'])

    return saved, simulation
