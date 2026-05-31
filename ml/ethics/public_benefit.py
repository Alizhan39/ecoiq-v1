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


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v or 0)))


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
    composite = (
        pillar * 0.40
        + jobs   * 0.20
        + reg    * 0.15
        + infra  * 0.15
        + nv     * 0.10
    )

    return {
        'score':          round(_clamp(composite), 2),
        'jobs':           round(jobs,   2),
        'regional':       round(reg,    2),
        'infrastructure': round(infra,  2),
        'national_value': round(nv,     2),
        'pillar_base':    round(pillar, 2),
    }
