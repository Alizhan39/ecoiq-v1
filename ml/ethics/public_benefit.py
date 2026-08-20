"""
ml/ethics/public_benefit.py — Expanded public benefit composite.

Computes a weighted composite from the four public benefit sub-scores
and the overall public_benefit_score pillar, with a jobs multiplier
that rewards genuine employment creation in the local economy.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from companies.models import CompanyProfile

from core.unknown import clamp, mean_of_known, weighted_mean_of_known


# One authority for unknown handling — core.unknown (D2b). Was a private
# `float(v or 0)`, one of six identical copies across ml/ethics alone, each of
# which turned an unmeasured score into 0 and a genuine 0.0 into 0 as well.
_clamp = clamp
_avg = mean_of_known
_weighted = weighted_mean_of_known


def compute_public_benefit_composite(profile: 'CompanyProfile') -> dict:
    """
    Returns a dict with:
        score          — weighted composite (0-100)
        jobs           — jobs_created_score normalised
        regional       — regional_development_score normalised
        infrastructure — infrastructure_contribution_score normalised
        national_value — national_value_score normalised
        pillar_base    — raw public_benefit_score pillar
    """
    jobs   = _clamp(profile.jobs_created_score)
    reg    = _clamp(profile.regional_development_score)
    infra  = _clamp(profile.infrastructure_contribution_score)
    nv     = _clamp(profile.national_value_score)
    pillar = _clamp(profile.public_benefit_score)

    # Weighted composite: pillar 40 %, jobs 20 %, regional 15 %, infra 15 %, NV 10 %
    # Re-normalised across the known terms, so a company is not scored lower
    # purely for an input it was never assessed on. None when nothing is known.
    composite = _weighted(
        (pillar, 0.40), (jobs, 0.20), (reg, 0.15), (infra, 0.15), (nv, 0.10),
    )

    def _r(value):
        return None if value is None else round(value, 2)

    return {
        'score':          _r(_clamp(composite)),
        'jobs':           _r(jobs),
        'regional':       _r(reg),
        'infrastructure': _r(infra),
        'national_value': _r(nv),
        'pillar_base':    _r(pillar),
    }
