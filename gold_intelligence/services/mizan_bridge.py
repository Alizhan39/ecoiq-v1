"""Read-only bridge from GoldProject inputs to EcoIQ Mizan evidence readiness.

Do not turn user-entered inputs, historic/demo data, or national/regional
risk proxies into a verified ethical, environmental or mining assessment.
Mizan states require versioned, externally justified limits and reviewed
site-specific evidence. This adapter never supplies or guesses those limits.
"""
from __future__ import annotations

from math import isfinite

from mizan.system_balance import (
    INSUFFICIENT_DATA,
    MIZAN_DIMENSIONS,
    BalanceDimension,
    assess_balance,
)

# Raw inputs already present on GoldProject. These are observations, NOT
# verified site-specific evidence or automatically graded Mizan dimensions.
# Keep this mapping separate from the 33 descriptive company sub-formulas.
GOLD_INPUT_FIELDS = (
    ('ore_grade_g_per_tonne', 'resource_efficiency', 'Ore grade', 'g/t'),
    ('recovery_rate_pct', 'resource_efficiency', 'Recovery assumption', '%'),
    ('expected_annual_production_oz', 'resource_efficiency', 'Expected annual production', 'oz/year'),
    ('total_capex_usd', 'economic', 'Initial CAPEX', 'USD'),
    ('annual_opex_usd', 'economic', 'Annual OPEX', 'USD/year'),
    ('aisc_usd_per_oz', 'economic', 'AISC assumption', 'USD/oz'),
    ('gold_price_assumption_usd_per_oz', 'economic', 'Gold price assumption', 'USD/oz'),
)


def _declared_number(value):
    """A finite declared input, not evidence that the input was verified."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if isfinite(value) else None


def build_gold_mizan_readiness(project):
    """Collect declared project inputs and produce an honest Mizan gap assessment.

    Read-only; no queries and no writes. A free-text source citation is not a
    verified source. Even with complete financial input fields, the assessment
    must remain INSUFFICIENT_DATA until independently reviewed evidence and
    defensible, versioned dimension criteria are available.
    """
    source = (getattr(project, 'data_sources', '') or '').strip()
    demo = bool(getattr(project, 'is_demo', True))
    observations = []
    for field, dimension, label, unit in GOLD_INPUT_FIELDS:
        value = _declared_number(getattr(project, field, None))
        observations.append({
            'field': field,
            'dimension': dimension,
            'label': label,
            'value': value,
            'unit': unit,
            'declared_source': source or None,
            'source_status': (
                'MISSING_VALUE' if value is None else
                'DEMO_UNVERIFIED' if demo else
                'CITED_UNVERIFIED' if source else 'SOURCE_MISSING'
            ),
        })

    observed_dimensions = {item['dimension'] for item in observations if item['value'] is not None}
    dimensions = tuple(
        BalanceDimension(
            key=dimension,
            status=INSUFFICIENT_DATA,
            notes=(
                'Declared project inputs exist, but reviewed site-specific '
                'evidence and approved assessment criteria are required.'
                if dimension in observed_dimensions else
                'No site-specific evidence and approved assessment criteria are available.'
            ),
        )
        for dimension in MIZAN_DIMENSIONS
    )

    # Operational KPIs are a separate readiness track. Internal review does
    # not establish independently certified thresholds or system balance.
    from gold_intelligence.services.mine_kpis import mine_kpi_readiness
    mine_kpis = (
        mine_kpi_readiness(project) if getattr(project, 'pk', None) is not None
        and hasattr(project, 'mine_kpi_observations') else
        {'observations': [], 'reviewed_count': 0, 'observed_count': 0}
    )

    return {
        'assessment': assess_balance(scope_level='facility', dimensions=dimensions),
        'observations': observations,
        'operational_kpis': mine_kpis,
        'declared_count': sum(item['value'] is not None for item in observations),
        'total_count': len(observations),
        'is_demo': demo,
        'verified_count': 0,  # never inferred from a free-text citation
        'explanation': (
            'Declared inputs are not verified resource estimates or Mizan scores. '
            'Independent evidence, a site-specific baseline, and reviewed criteria '
            'are required before any dimension can be classified.'
        ),
    }
