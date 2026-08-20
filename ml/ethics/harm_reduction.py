"""
ml/ethics/harm_reduction.py — Harm quantification and mitigation assessment.

Converts the pollution level, harm_penalty, and controversy_risk_score
into a normalised harm score and a mitigation signal that indicates how
actively a company is working to reduce its negative footprint.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from companies.models import CompanyProfile

from core.unknown import clamp, mean_of_known, weighted_mean_of_known


_POLLUTION_HARM_BASE = {
    'low':    10.0,
    'medium': 30.0,
    'high':   60.0,
    'severe': 85.0,
}

_MITIGATION_FROM_ENERGY_TRANSITION = [
    (75, 'strong'),
    (55, 'moderate'),
    (40, 'early'),
    (0,  'minimal'),
]


# One authority for unknown handling — core.unknown (D2b). Was a private
# `float(v or 0)`, one of six identical copies across ml/ethics alone, each of
# which turned an unmeasured score into 0 and a genuine 0.0 into 0 as well.
_clamp = clamp
_avg = mean_of_known
_weighted = weighted_mean_of_known


def compute_harm_reduction(profile: 'CompanyProfile') -> dict:
    """
    Returns a dict with:
        harm_score       — composite harm level (0-100, higher = worse)
        mitigation_level — 'strong' | 'moderate' | 'early' | 'minimal'
        controversy_risk — normalised controversy risk
        harm_penalty_pts — raw harm_penalty deducted from EcoIQ total
        net_harm         — harm_score after mitigation discount
    """
    # `or 'medium'` substituted a medium-pollution classification for one we do
    # not have, and medium is a real observation about a real company.
    raw_level       = getattr(profile, 'pollution_level', None)
    pollution_level = raw_level.lower() if raw_level else None
    harm_base       = _POLLUTION_HARM_BASE.get(pollution_level)

    # Was `_clamp(x or 0)`: unknown controversy became ZERO harm, which is not
    # silence but a positive claim that the company is uncontroversial.
    controversy  = _clamp(profile.controversy_risk_score)
    harm_penalty = _clamp(profile.harm_penalty, hi=100.0)

    # Composite harm = 60% pollution base + 40% controversy, re-normalised so an
    # unknown channel is dropped rather than counted as no harm at all.
    harm_score = _weighted((harm_base, 0.60), (controversy, 0.40))

    # Mitigation signal from energy_transition_score. Unknown earns no discount:
    # a mitigation discount is a claim that the company is actively reducing
    # harm, and absence of evidence is not evidence of effort.
    energy_tr = _clamp(profile.energy_transition_score)
    mitigation = 'unknown' if energy_tr is None else 'minimal'
    if energy_tr is not None:
        for threshold, label in _MITIGATION_FROM_ENERGY_TRANSITION:
            if energy_tr >= threshold:
                mitigation = label
                break

    mitigation_discount = {
        'strong':   0.30,
        'moderate': 0.15,
        'early':    0.05,
        'minimal':  0.00,
        'unknown':  0.00,
    }[mitigation]

    net_harm = (None if harm_score is None
                else _clamp(harm_score * (1 - mitigation_discount)))

    def _r(value):
        return None if value is None else round(value, 2)

    return {
        'harm_score':       _r(harm_score),
        'mitigation_level': mitigation,
        'controversy_risk': _r(controversy),
        'harm_penalty_pts': _r(harm_penalty),
        'net_harm':         _r(net_harm),
    }
