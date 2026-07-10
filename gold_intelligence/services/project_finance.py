"""
gold_intelligence/services/project_finance.py — real project economics:
CAPEX/AISC-driven cash flow construction, IRR/NPV/payback, sensitivity
(tornado) and scenario analysis.

No external financial library is available in this repo (no numpy_financial,
no scipy) — IRR is found with a standard Newton's-method root-search over
NPV(rate) = 0, the same technique spreadsheet IRR functions use internally,
not a black box.

Every function operates only on real, already-stored GoldProject fields.
When a required real input is missing, the function returns
{'available': False, 'reason': 'Data source required for <field>.'} —
never a fabricated number, matching every other scoring/finance module in
this platform (see e.g. core/globe.py's LIMITED_COVERAGE convention).

Cash-flow model: a single upfront CAPEX outflow at year 0, followed by
`mine_life_years` identical annual net cash flows (production_oz × (gold
price − AISC or cash cost)). This is the standard simplified project-finance
model used when only totals (not a year-by-year schedule) are known — it is
not the Capital Tracker's job (see CapitalBudgetLine / views.capital_tracker)
which tracks actual planned/committed/spent execution separately.
"""
import copy

NOT_AVAILABLE_REASON = 'Data source required for {field}.'


def _unavailable(field):
    return {'available': False, 'reason': NOT_AVAILABLE_REASON.format(field=field)}


def _cost_basis(project):
    """Prefers AISC (the standard all-in sustaining cost metric) over the
    narrower direct cash cost when both are absent/present — never blends
    the two, and always reports honestly which one was actually used."""
    if project.aisc_usd_per_oz is not None:
        return 'aisc', project.aisc_usd_per_oz
    if project.cash_cost_usd_per_oz is not None:
        return 'cash_cost', project.cash_cost_usd_per_oz
    return None, None


def build_cash_flow_series(project):
    """Returns {'available': True, 'cash_flows': [...], 'cost_basis': ..., ...}
    or an honest {'available': False, 'reason': ...} when a required real
    input is missing."""
    if project.total_capex_usd is None:
        return _unavailable('total CAPEX (USD)')
    if project.expected_annual_production_oz is None:
        return _unavailable('expected annual production (oz)')
    if project.gold_price_assumption_usd_per_oz is None:
        return _unavailable('gold price assumption (USD/oz)')
    if project.mine_life_years is None:
        return _unavailable('mine life (years)')

    cost_basis, cost_per_oz = _cost_basis(project)
    if cost_basis is None:
        return _unavailable('AISC or cash cost (USD/oz)')

    annual_net_cash_flow = project.expected_annual_production_oz * (
        project.gold_price_assumption_usd_per_oz - cost_per_oz
    )
    cash_flows = [-project.total_capex_usd] + [annual_net_cash_flow] * project.mine_life_years
    return {
        'available': True,
        'cash_flows': cash_flows,
        'cost_basis': cost_basis,
        'annual_net_cash_flow_usd': round(annual_net_cash_flow, 2),
        'capex_usd': project.total_capex_usd,
    }


def compute_npv(cash_flows, discount_rate_pct):
    rate = discount_rate_pct / 100.0
    return round(sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows)), 2)


def compute_irr(cash_flows, max_iterations=200, tolerance=1e-6):
    """Newton's-method root-search for NPV(rate) = 0. Returns None (never a
    guess) when the cash-flow shape has no real root or the search doesn't
    converge — e.g. an all-positive or all-negative series."""
    if not cash_flows or cash_flows[0] >= 0:
        return None
    if all(cf <= 0 for cf in cash_flows[1:]):
        return None

    rate = 0.1
    for _ in range(max_iterations):
        npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))
        d_npv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
        if abs(d_npv) < 1e-12:
            return None
        new_rate = rate - npv / d_npv
        if not (-0.99 < new_rate < 10):
            return None
        if abs(new_rate - rate) < tolerance:
            return round(new_rate * 100, 2)
        rate = new_rate
    return None


def compute_payback_years(cash_flows):
    """Cumulative-cash-flow break-even, linearly interpolated within the
    year it crosses zero. None when the project never pays back within the
    modeled mine life."""
    cumulative = 0.0
    for t, cf in enumerate(cash_flows):
        previous_cumulative = cumulative
        cumulative += cf
        if t > 0 and cumulative >= 0:
            fraction = -previous_cumulative / cf if cf else 0.0
            return round((t - 1) + fraction, 2)
    return None


def compute_project_economics(project):
    """The Investment Dashboard's headline CAPEX/IRR/NPV/Payback block."""
    series = build_cash_flow_series(project)
    if not series['available']:
        return series

    result = {
        'available': True,
        'capex_usd': series['capex_usd'],
        'cost_basis': series['cost_basis'],
        'annual_net_cash_flow_usd': series['annual_net_cash_flow_usd'],
        'irr_pct': compute_irr(series['cash_flows']),
        'payback_years': compute_payback_years(series['cash_flows']),
    }
    if project.discount_rate_pct is not None:
        result['npv_usd'] = compute_npv(series['cash_flows'], project.discount_rate_pct)
    else:
        result['npv_usd'] = None
        result['npv_unavailable_reason'] = NOT_AVAILABLE_REASON.format(field='discount rate (%)')
    return result


SENSITIVITY_VARIABLES = [
    ('gold_price_assumption_usd_per_oz', 'Gold Price'),
    ('total_capex_usd', 'CAPEX'),
    ('aisc_usd_per_oz', 'AISC'),
    ('cash_cost_usd_per_oz', 'Cash Cost'),
    ('expected_annual_production_oz', 'Annual Production'),
]
SENSITIVITY_SWING_PCT = 20.0


def _irr_with_override(project, field, value):
    """Computes IRR under a single-field what-if override, without ever
    writing to the database (a shallow in-memory copy of the instance)."""
    shadow = copy.copy(project)
    setattr(shadow, field, value)
    series = build_cash_flow_series(shadow)
    if not series['available']:
        return None
    return compute_irr(series['cash_flows'])


def run_sensitivity_analysis(project, swing_pct=SENSITIVITY_SWING_PCT):
    """Classic one-at-a-time tornado sensitivity: each real base-case input
    is swung ±swing_pct% while holding every other input at its real,
    stored value. A variable with no real base-case value is honestly
    skipped, never assigned an invented baseline."""
    base = compute_project_economics(project)
    if not base['available']:
        return base
    base_irr = base['irr_pct']
    if base_irr is None:
        return {'available': False, 'reason': 'Base-case IRR could not be computed from the current real inputs.'}

    variables = []
    for field, label in SENSITIVITY_VARIABLES:
        base_value = getattr(project, field)
        if base_value is None:
            continue
        low_irr = _irr_with_override(project, field, base_value * (1 - swing_pct / 100))
        high_irr = _irr_with_override(project, field, base_value * (1 + swing_pct / 100))
        variables.append({
            'variable': label, 'field': field, 'base_value': base_value,
            'low_irr_pct': low_irr, 'high_irr_pct': high_irr, 'swing_pct': swing_pct,
        })

    def _spread(v):
        values = [x for x in (v['low_irr_pct'], v['high_irr_pct'], base_irr) if x is not None]
        return (max(values) - min(values)) if values else 0

    variables.sort(key=_spread, reverse=True)
    return {'available': True, 'base_irr_pct': base_irr, 'variables': variables}


def run_scenario_analysis(project):
    """Re-runs full project economics under each real, stored
    ScenarioAssumption. A scenario field left null means that input is NOT
    overridden — the base-case value is used, never a fabricated substitute."""
    base = compute_project_economics(project)
    scenarios = []
    for scenario in project.scenarios.all():
        shadow = copy.copy(project)
        if scenario.gold_price_usd_per_oz is not None:
            shadow.gold_price_assumption_usd_per_oz = scenario.gold_price_usd_per_oz
        if scenario.capex_multiplier is not None and project.total_capex_usd is not None:
            shadow.total_capex_usd = project.total_capex_usd * scenario.capex_multiplier
        if scenario.opex_multiplier is not None:
            if project.aisc_usd_per_oz is not None:
                shadow.aisc_usd_per_oz = project.aisc_usd_per_oz * scenario.opex_multiplier
            elif project.cash_cost_usd_per_oz is not None:
                shadow.cash_cost_usd_per_oz = project.cash_cost_usd_per_oz * scenario.opex_multiplier
        result = compute_project_economics(shadow)
        scenarios.append({'scenario_id': scenario.pk, 'name': scenario.name, 'notes': scenario.notes, **result})
    return {'available': True, 'base_case': base, 'scenarios': scenarios}
