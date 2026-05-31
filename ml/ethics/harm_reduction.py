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


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v or 0)))


def compute_harm_reduction(profile: 'CompanyProfile') -> dict:
    """
    Returns a dict with:
        harm_score       — composite harm level (0-100, higher = worse)
        mitigation_level — 'strong' | 'moderate' | 'early' | 'minimal'
        controversy_risk — normalised controversy risk
        harm_penalty_pts — raw harm_penalty deducted from EcoIQ total
        net_harm         — harm_score after mitigation discount
    """
    pollution_level = (getattr(profile, 'pollution_level', None) or 'medium').lower()
    harm_base       = _POLLUTION_HARM_BASE.get(pollution_level, 30.0)
    controversy     = _clamp(profile.controversy_risk_score)
    harm_penalty    = float(profile.harm_penalty or 0)

    # Composite harm = 60% pollution base + 40% controversy
    harm_score = _clamp(harm_base * 0.60 + controversy * 0.40)

    # Mitigation signal from energy_transition_score
    energy_tr = _clamp(profile.energy_transition_score)
    mitigation = 'minimal'
    for threshold, label in _MITIGATION_FROM_ENERGY_TRANSITION:
        if energy_tr >= threshold:
            mitigation = label
            break

    mitigation_discount = {
        'strong':   0.30,
        'moderate': 0.15,
        'early':    0.05,
        'minimal':  0.00,
    }[mitigation]

    net_harm = _clamp(harm_score * (1 - mitigation_discount))

    return {
        'harm_score':       round(harm_score,    2),
        'mitigation_level': mitigation,
        'controversy_risk': round(controversy,   2),
        'harm_penalty_pts': round(harm_penalty,  2),
        'net_harm':         round(net_harm,      2),
    }
