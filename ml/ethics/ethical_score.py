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

from core.unknown import clamp, weighted_mean_of_known

from .public_benefit      import compute_public_benefit_composite
from .harm_reduction       import compute_harm_reduction
from .justice_balance      import compute_justice_balance
from .stewardship          import compute_stewardship
from .evidence_confidence  import compute_evidence_confidence
from .greenwashing_risk    import greenwashing_from_profile


_OVERALL_LABEL = [
    (80, 'Ethical Leader'),
    (65, 'Responsible Operator'),
    (50, 'Transitioning'),
    (35, 'High-Risk'),
    (0,  'Critical Concern'),
]

# Outside the ordered tiers: not a degree of ethical performance, but the
# absence of an assessment. Mirrors greenwashing_risk.RISK_INSUFFICIENT_EVIDENCE
# and companies.evidence — one vocabulary, not a new framework.
LABEL_INSUFFICIENT_EVIDENCE = 'Insufficient Evidence'


# core.unknown is the single authority (D2b). Was `float(v or 0)`.
_clamp = clamp


def compute_ethical_intelligence(profile: 'CompanyProfile') -> dict:
    """
    Compute full ethical intelligence payload for a single CompanyProfile.

    Returns a dict ready for JSON serialisation:
    {
        "overall_score":    float | None,   # 0-100 weighted composite, or null
        "label":            str,            # human-readable tier, or the
                                            #   explicit insufficient-evidence state
        "public_benefit":   {...},
        "harm_reduction":   {...},
        "justice_balance":  {...},
        "stewardship":      {...},
        "evidence":         {...},
        "ecoiq_total_score": float | None,  # the base EcoIQ score for context
        "methodology_note": str,
    }

    This is the DOMAIN calculation, and it now tells the truth: overall_score is
    None when the four contributing dimensions cannot be established. The v1 API
    boundary is responsible for whatever compatibility shim it needs — see
    api/views.py. Domain semantics are not bent to fit a legacy serialiser.
    """
    pb  = compute_public_benefit_composite(profile)
    hr  = compute_harm_reduction(profile)
    jb  = compute_justice_balance(profile)
    st  = compute_stewardship(profile)
    ev  = compute_evidence_confidence(profile)
    gw  = greenwashing_from_profile(profile)

    # Weighted overall ethical intelligence score
    #   Public benefit   30%
    #   Justice balance  25%
    #   Stewardship      25%
    #   Harm penalty     20% (inverted: lower harm = higher contribution)
    #
    # Re-normalised across the known dimensions. `harm_inverted` is the one to
    # watch: with the old `_clamp(None) -> 0`, an unknown net_harm became
    # 100 - 0 = 100, the maximum possible contribution — so a company nobody had
    # assessed for harm scored as though it had been assessed and found harmless.
    harm_inverted = (None if hr['net_harm'] is None
                     else _clamp(100 - hr['net_harm']))
    overall = _clamp(weighted_mean_of_known(
        (pb['score'],   0.30),
        (jb['score'],   0.25),
        (st['score'],   0.25),
        (harm_inverted, 0.20),
    ))

    # Apply evidence confidence discount: ai-seeded profiles are deflated slightly
    if overall is not None and ev['confidence_tier'] == 'ai-seeded':
        overall = _clamp(overall * ev['confidence_score'] / 0.55)

    # 'Critical Concern' is the worst tier, and it was the fall-through: an
    # unassessed company landed there by default. Unknown gets its own state.
    if overall is None:
        label = LABEL_INSUFFICIENT_EVIDENCE
    else:
        label = 'Critical Concern'
        for threshold, lbl in _OVERALL_LABEL:
            if overall >= threshold:
                label = lbl
                break

    return {
        'overall_score':     None if overall is None else round(overall, 2),
        'label':             label,
        'public_benefit':    pb,
        'harm_reduction':    hr,
        'justice_balance':   jb,
        'stewardship':       st,
        'evidence':          ev,
        'greenwashing_risk': gw.to_dict(),
        'ecoiq_total_score': _clamp(profile.ecoiq_total_score),
        'methodology_note': (
            'EcoIQ Ethical Intelligence scores are derived from existing pillar data. '
            'They reflect evidence-based stewardship, public benefit delivery, and '
            'harm mitigation — not investment advice. '
            'Profiles marked ai-seeded require independent verification. '
            'Greenwashing risk indicators are public-data based and require '
            'independent verification before use in capital decisions.'
        ),
    }
