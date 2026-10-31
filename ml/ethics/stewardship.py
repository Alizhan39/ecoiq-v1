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

from core.unknown import clamp, mean_of_known, weighted_mean_of_known


# One authority for unknown handling — core.unknown (D2b). Was a private
# `float(v or 0)`, one of six identical copies across ml/ethics alone, each of
# which turned an unmeasured score into 0 and a genuine 0.0 into 0 as well.
_clamp = clamp
_avg = mean_of_known
_weighted = weighted_mean_of_known


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
    future_orientation = _weighted(
        (profile.future_readiness_score,      0.35),
        (profile.energy_transition_score,     0.35),
        (profile.digitalization_score,        0.15),
        (profile.infrastructure_upgrade_score, 0.15),
    )

    # Environmental care: stewardship of natural resources
    env_care = _avg(
        profile.water_impact_score,
        profile.biodiversity_impact_score,
        profile.waste_management_score,
    )

    # Ethical alignment pillar
    ethical_al = _clamp(profile.ethical_alignment_score)

    # Stewardship composite
    score = _clamp(_weighted(
        (future_orientation, 0.40), (env_care, 0.35), (ethical_al, 0.25),
    ))

    # `stewardship_deficit` is the worst tier, and it was the default: with the
    # old _clamp an unassessed company scored 0 and was labelled deficient.
    # Unknown now gets its own label instead of the bottom one.
    label = 'insufficient_evidence' if score is None else 'stewardship_deficit'
    if score is not None:
        for threshold, lbl in _STEWARDSHIP_LABEL:
            if score >= threshold:
                label = lbl
                break

    def _r(value):
        return None if value is None else round(value, 2)

    return {
        'score':               _r(score),
        'label':               label,
        'future_orientation':  _r(future_orientation),
        'environmental_care':  _r(env_care),
        'ethical_alignment':   _r(ethical_al),
    }
