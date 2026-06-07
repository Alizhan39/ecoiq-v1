"""
Khalifa Heat — boiler sizing & package recommendation logic.

Pure functions, no Django imports — easy to unit-test. Used by the calculator
view and the HomeAssessment admin.
"""
import math

# Cold-climate heat demand by insulation quality (W per m²).
W_PER_M2 = {'poor': 130, 'medium': 100, 'good': 70}

# Standard electric-boiler sizes (kW).
STANDARD_KW = [6, 8, 9, 12, 15, 18, 24]

# Package price ranges (KZT) — keyed by calculator/package slug.
PACKAGE_PRICES = {
    'diy_basic':      (900_000, 1_500_000),
    'assisted':       (1_700_000, 2_700_000),
    'full_install':   (2_500_000, 3_800_000),
    'smart_electric': (3_500_000, 5_000_000),
    'ready_plus':     (4_000_000, 6_000_000),
}

PACKAGE_LABELS = {
    'diy_basic':      'Khalifa Heat DIY Basic',
    'assisted':       'Khalifa Heat Assisted',
    'full_install':   'Khalifa Heat Full Install',
    'smart_electric': 'Khalifa Heat Smart Electric',
    'ready_plus':     'Khalifa Heat Ready+',
}

LARGE_HOME_SURCHARGE = 0.15  # +15% if large home / many rooms


def recommend_boiler_kw(area_m2, insulation):
    """Return a standard boiler size (kW) for the area + insulation."""
    wm2 = W_PER_M2.get(insulation, 100)
    raw = (max(area_m2, 0) * wm2) / 1000.0
    for size in STANDARD_KW:
        if size >= raw:
            return size
    return STANDARD_KW[-1]


def recommend(area_m2, insulation, rooms, has_radiators,
              electricity, available_kw, package, install_type):
    """
    Compute a full recommendation dict from calculator inputs.

    Returns keys:
      recommended_kw, estimated_cost_min, estimated_cost_max,
      installation_warning, capacity_warning, insulation_recommendation,
      radiator_recommendation, hp_ready_recommended, warnings (list)
    """
    area_m2 = int(area_m2 or 0)
    rooms = int(rooms or 0)
    available_kw = float(available_kw or 0)

    kw = recommend_boiler_kw(area_m2, insulation)

    # Estimated cost from selected package, +surcharge for large homes.
    price_min, price_max = PACKAGE_PRICES.get(package, (0, 0))
    large_home = kw >= 15 or rooms >= 5
    if large_home and price_min:
        price_min = int(round(price_min * (1 + LARGE_HOME_SURCHARGE)))
        price_max = int(round(price_max * (1 + LARGE_HOME_SURCHARGE)))

    warnings = []

    # Electricity capacity / phase.
    capacity_warning = ''
    if electricity == '220' and kw > 8:
        capacity_warning = (
            f'A {kw} kW boiler needs 380V three-phase. Single-phase 220V is '
            f'not sufficient — a supply/phase upgrade is required.'
        )
    elif available_kw and (kw + 3) > available_kw:
        capacity_warning = (
            f'Available supply ({available_kw:g} kW) is too low for a {kw} kW '
            f'boiler plus headroom. An electricity supply upgrade is needed.'
        )
    if capacity_warning:
        warnings.append(capacity_warning)

    # Installation warning (DIY on demanding setups).
    installation_warning = ''
    if install_type == 'diy' and (kw >= 12 or electricity == '380'):
        installation_warning = (
            'Professional installation is required for this configuration '
            '(high power and/or three-phase) — DIY is not recommended.'
        )
    if installation_warning:
        warnings.append(installation_warning)

    # Insulation.
    insulation_recommendation = ''
    if insulation == 'poor':
        insulation_recommendation = (
            'Insulate first: weatherization can cut the required boiler size by '
            'about one tier and reduce running costs by ~20–30%.'
        )
        warnings.append(insulation_recommendation)

    # Radiators.
    radiator_recommendation = ''
    if not has_radiators:
        radiator_recommendation = (
            'No existing radiators detected — radiator installation will be '
            'required and adds to cost and scope.'
        )
        warnings.append(radiator_recommendation)

    # Heat-pump readiness.
    hp_ready_recommended = (
        area_m2 >= 120 or insulation == 'good' or package in ('smart_electric', 'ready_plus')
    )

    return {
        'recommended_kw': kw,
        'estimated_cost_min': price_min,
        'estimated_cost_max': price_max,
        'large_home_surcharge': large_home,
        'installation_warning': installation_warning,
        'capacity_warning': capacity_warning,
        'insulation_recommendation': insulation_recommendation,
        'radiator_recommendation': radiator_recommendation,
        'hp_ready_recommended': hp_ready_recommended,
        'warnings': warnings,
    }
