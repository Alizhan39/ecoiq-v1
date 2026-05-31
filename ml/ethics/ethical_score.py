"""
ml/ethics/ethical_score.py — Top-level ethical intelligence orchestrator.

Combines all sub-module results into a single ethical intelligence payload
suitable for the API response at:
  GET /api/v1/companies/<slug>/ethical-intelligence/
  GET /api/v1/countries/<slug>/ethical-intelligence/  (country aggregate)
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from companies.models import CompanyProfile

from .public_benefit    import compute_public_benefit_composite
from .harm_reduction     import compute_harm_reduction
from .justice_balance    import compute_justice_balance
from .stewardship        import compute_stewardship
from .evidence_confidence import compute_evidence_confidence


_OVERALL_LABEL = [
    (80, 'Ethical Leader'),
    (65, 'Responsible Operator'),
    (50, 'Transitioning'),
    (35, 'High-Risk'),
    (0,  'Critical Concern'),
]


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v or 0)))


def compute_ethical_intelligence(profile: 'CompanyProfile') -> dict:
    """
    Compute full ethical intelligence payload for a single CompanyProfile.

    Returns a dict ready for JSON serialisation:
    {
        "overall_score":    float,          # 0-100 weighted composite
        "label":            str,            # human-readable tier
        "public_benefit":   {...},
        "harm_reduction":   {...},
        "justice_balance":  {...},
        "stewardship":      {...},
        "evidence":         {...},
        "ecoiq_total_score": float,         # the base EcoIQ score for context
        "methodology_note": str,
    }
    """
    pb  = compute_public_benefit_composite(profile)
    hr  = compute_harm_reduction(profile)
    jb  = compute_justice_balance(profile)
    st  = compute_stewardship(profile)
    ev  = compute_evidence_confidence(profile)

    # Weighted overall ethical intelligence score
    #   Public benefit   30%
    #   Justice balance  25%
    #   Stewardship      25%
    #   Harm penalty     20% (inverted: lower harm = higher contribution)
    harm_inverted = _clamp(100 - hr['net_harm'])
    overall = _clamp(
        pb['score']  * 0.30
        + jb['score'] * 0.25
        + st['score'] * 0.25
        + harm_inverted * 0.20
    )

    # Apply evidence confidence discount: ai-seeded profiles are deflated slightly
    if ev['confidence_tier'] == 'ai-seeded':
        overall = _clamp(overall * ev['confidence_score'] / 0.55)

    label = 'Critical Concern'
    for threshold, lbl in _OVERALL_LABEL:
        if overall >= threshold:
            label = lbl
            break

    return {
        'overall_score':     round(overall, 2),
        'label':             label,
        'public_benefit':    pb,
        'harm_reduction':    hr,
        'justice_balance':   jb,
        'stewardship':       st,
        'evidence':          ev,
        'ecoiq_total_score': float(profile.ecoiq_total_score or 0),
        'methodology_note': (
            'EcoIQ Ethical Intelligence scores are derived from existing pillar data. '
            'They reflect evidence-based stewardship, public benefit delivery, and '
            'harm mitigation — not investment advice. '
            'Profiles marked ai-seeded require independent verification.'
        ),
    }
