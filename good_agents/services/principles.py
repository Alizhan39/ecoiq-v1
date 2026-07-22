"""
good_agents/services/principles.py — the ONLY place that reads
core.esg_principles_data.PRINCIPLES for the Good Agents framework.

core.esg_principles_data.PRINCIPLES was chosen as the canonical 114-
principle source (over the two other "114" datasets in this repo —
core/views.py's hardcoded _SURAHS list and content/tazkiyah114/surah_seeds.json)
because it is the only one that is public, English, DB-independent, and
does not carry an unresolved scholar-review status. See
docs/114_GOOD_AGENTS.md for the full comparison.
"""
from core.esg_principles_data import PRINCIPLES

_BY_ID = {p['id']: p for p in PRINCIPLES}


def get_principle(principle_id):
    """Returns the raw canonical dict for one principle id (1-114), or None."""
    return _BY_ID.get(principle_id)


def all_principle_ids():
    return sorted(_BY_ID.keys())
