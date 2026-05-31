"""
ml/ethics/justice_balance.py — Equitable value distribution assessment.

Measures whether a company distributes value fairly across stakeholders:
workers, communities, the environment, and investors. Imbalance (high
profit extraction with low public benefit) reduces the score.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from companies.models import CompanyProfile


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v or 0)))


def compute_justice_balance(profile: 'CompanyProfile') -> dict:
    """
    Returns a dict with:
        score               — justice balance composite (0-100)
        community_share     — how well community interests are served
        governance_quality  — governance and transparency composite
        accountability      — anti-corruption and audit quality signal
        balance_gap         — gap between governance promise and delivery
    """
    # Community interests
    jobs   = _clamp(profile.jobs_created_score)
    reg    = _clamp(profile.regional_development_score)
    nv     = _clamp(profile.national_value_score)
    community_share = (jobs + reg + nv) / 3

    # Governance quality
    transp  = _clamp(profile.transparency_anti_corruption_score)
    audit   = _clamp(profile.audit_quality_score)
    procure = _clamp(profile.procurement_transparency_score)
    gov_quality = (transp + audit + procure) / 3

    # Accountability
    anti_c      = _clamp(profile.anti_corruption_score)
    accountability = (anti_c + audit) / 2

    # Balance gap: high controversy with high governance claims = gap
    controversy = _clamp(profile.controversy_risk_score)
    balance_gap = max(0.0, (gov_quality - (100 - controversy)) / 2)

    # Composite justice score
    score = _clamp(
        community_share * 0.35
        + gov_quality   * 0.30
        + accountability * 0.25
        - balance_gap   * 0.10
    )

    return {
        'score':              round(score,           2),
        'community_share':    round(community_share, 2),
        'governance_quality': round(gov_quality,     2),
        'accountability':     round(accountability,  2),
        'balance_gap':        round(balance_gap,     2),
    }
