"""
ml/ethics/stewardship.py — Long-horizon stewardship signal.

Stewardship captures whether a company acts as a responsible custodian
of its assets, workforce, environment, and the communities in which it
operates — with a long-term rather than short-term orientation.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from companies.models import CompanyProfile


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v or 0)))


_STEWARDSHIP_LABEL = [
    (80, 'exemplary_steward'),
    (65, 'active_steward'),
    (50, 'partial_steward'),
    (35, 'reactive_steward'),
    (0,  'stewardship_deficit'),
]


def compute_stewardship(profile: 'CompanyProfile') -> dict:
    """
    Returns a dict with:
        score             — stewardship composite (0-100)
        label             — qualitative stewardship tier
        future_orientation — forward-looking score (future_readiness + energy_transition)
        environmental_care — water, biodiversity, waste composite
        ethical_alignment  — raw ethical_alignment_score pillar
    """
    # Future orientation: is the company investing in its own transition?
    future_r  = _clamp(profile.future_readiness_score)
    energy_tr = _clamp(profile.energy_transition_score)
    digital   = _clamp(profile.digitalization_score)
    infra_u   = _clamp(profile.infrastructure_upgrade_score)
    future_orientation = (future_r * 0.35 + energy_tr * 0.35 + digital * 0.15 + infra_u * 0.15)

    # Environmental care: stewardship of natural resources
    water    = _clamp(profile.water_impact_score)
    biodiv   = _clamp(profile.biodiversity_impact_score)
    waste    = _clamp(profile.waste_management_score)
    env_care = (water + biodiv + waste) / 3

    # Ethical alignment pillar
    ethical_al = _clamp(profile.ethical_alignment_score)

    # Stewardship composite
    score = _clamp(
        future_orientation * 0.40
        + env_care         * 0.35
        + ethical_al       * 0.25
    )

    label = 'stewardship_deficit'
    for threshold, lbl in _STEWARDSHIP_LABEL:
        if score >= threshold:
            label = lbl
            break

    return {
        'score':               round(score,               2),
        'label':               label,
        'future_orientation':  round(future_orientation,  2),
        'environmental_care':  round(env_care,            2),
        'ethical_alignment':   round(ethical_al,          2),
    }
