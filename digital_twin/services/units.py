"""
digital_twin/services/units.py — safe quantity arithmetic.

No unit-of-measure model existed anywhere in the repo before this app (units
were baked into field names like `_kw`/`_pct`/`_m3_per_hour` elsewhere).
Every conversion here is plain arithmetic against `Unit.to_base_multiplier`
— never a fabricated or assumed conversion factor.
"""


class IncompatibleUnitsError(ValueError):
    """Raised when two quantities from different UnitCategory rows are
    combined — never silently coerced."""


def convert(value, from_unit, to_unit):
    """Converts `value` from `from_unit` to `to_unit`. Both must belong to
    the same UnitCategory. Never guesses a cross-category conversion."""
    if from_unit.category_id != to_unit.category_id:
        raise IncompatibleUnitsError(
            f'Cannot convert {from_unit.code} ({from_unit.category.code}) to '
            f'{to_unit.code} ({to_unit.category.code}) — different unit categories.'
        )
    base_value = value * from_unit.to_base_multiplier
    return base_value / to_unit.to_base_multiplier


def to_base(value, unit):
    """Converts `value` in `unit` to its category's base unit value."""
    return value * unit.to_base_multiplier


def assert_same_category(*units):
    """Raises IncompatibleUnitsError unless every given unit shares one
    UnitCategory. Used before summing quantities across ResourceFlow rows."""
    categories = {u.category_id for u in units if u is not None}
    if len(categories) > 1:
        raise IncompatibleUnitsError(
            f'Quantities span {len(categories)} different unit categories — cannot be combined directly.'
        )
