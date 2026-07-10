"""
capital_guardian/services/equipment_health.py — Phase 3: a deterministic
remaining-useful-life estimate for one piece of equipment. This is
explicitly NOT a machine-learning prediction — it is plain arithmetic over
two real, declared inputs (EquipmentSpec.commissioned_date and
.expected_lifespan_years), matching the same "real data in, plain
arithmetic, honest None when an input is missing" discipline as
red_flag_engine.py. A "recommended service window" is derived the same way,
standing in for the spec's "AI Prediction / Expected Failure Date" without
inventing a black-box predictor.
"""
import datetime

SERVICE_WINDOW_WARNING_YEARS_REMAINING = 1.0


def remaining_useful_life(equipment):
    """(years_remaining, expected_end_date) — None, None unless BOTH real
    inputs (commissioned_date, expected_lifespan_years) are present."""
    if equipment.commissioned_date is None or equipment.expected_lifespan_years is None:
        return None, None
    expected_end_date = equipment.commissioned_date + datetime.timedelta(days=equipment.expected_lifespan_years * 365.25)
    years_remaining = round((expected_end_date - datetime.date.today()).days / 365.25, 1)
    return years_remaining, expected_end_date


def maintenance_recommendation(equipment):
    """A real, explainable recommendation derived only from
    remaining_useful_life() — never fabricated when the real inputs are
    missing."""
    years_remaining, expected_end_date = remaining_useful_life(equipment)
    if years_remaining is None:
        return {
            'available': False,
            'reason': 'No commissioned date and/or expected lifespan recorded for this equipment yet.',
        }
    if years_remaining <= 0:
        urgency = 'overdue'
        message = f'{equipment} is past its declared expected lifespan (was expected to end {expected_end_date}). Recommend inspection and replacement planning now.'
    elif years_remaining <= SERVICE_WINDOW_WARNING_YEARS_REMAINING:
        urgency = 'due_soon'
        message = f'{equipment} has an estimated {years_remaining} year(s) of remaining useful life (declared end date {expected_end_date}). Recommend scheduling a service/replacement review.'
    else:
        urgency = 'ok'
        message = f'{equipment} has an estimated {years_remaining} year(s) of remaining useful life (declared end date {expected_end_date}).'
    return {
        'available': True, 'years_remaining': years_remaining, 'expected_end_date': expected_end_date,
        'urgency': urgency, 'message': message,
    }
