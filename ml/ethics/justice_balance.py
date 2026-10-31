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

from core.unknown import clamp, mean_of_known, weighted_mean_of_known


# One authority for unknown handling — core.unknown (D2b). Was a private
# `float(v or 0)`, one of six identical copies across ml/ethics alone, each of
# which turned an unmeasured score into 0 and a genuine 0.0 into 0 as well.
_clamp = clamp
_avg = mean_of_known
_weighted = weighted_mean_of_known


def compute_justice_balance(profile: 'CompanyProfile') -> dict:
    """
    Returns a dict with:
        score               — justice balance composite (0-100)
        community_share     — how well community interests are served
        governance_quality  — governance and transparency composite
        accountability      — anti-corruption and audit quality signal
        balance_gap         — gap between governance promise and delivery
    """
    # Community interests — three measures of the same thing, so the known ones
    # are averaged and the gap is reported by evidence coverage, not by a zero.
    community_share = _avg(
        profile.jobs_created_score,
        profile.regional_development_score,
        profile.national_value_score,
    )

    # Governance quality
    audit = _clamp(profile.audit_quality_score)
    gov_quality = _avg(
        profile.transparency_anti_corruption_score,
        profile.audit_quality_score,
        profile.procurement_transparency_score,
    )

    # Accountability
    anti_c = _clamp(profile.anti_corruption_score)
    accountability = _avg(anti_c, audit)

    # Balance gap: high controversy with high governance claims = gap.
    # Needs BOTH halves known — the gap is a comparison, and comparing against
    # an unknown controversy level asserts the level.
    controversy = _clamp(profile.controversy_risk_score)
    balance_gap = (None if gov_quality is None or controversy is None
                   else max(0.0, (gov_quality - (100 - controversy)) / 2))

    # Composite justice score. balance_gap is a PENALTY term, so it is excluded
    # from re-normalisation when unknown rather than re-weighted — re-weighting
    # a missing penalty across the positive terms would inflate the score.
    positives = _weighted(
        (community_share, 0.35), (gov_quality, 0.30), (accountability, 0.25),
    )
    if positives is None:
        score = None
    else:
        score = _clamp(positives * 0.90 - (balance_gap or 0.0) * 0.10)

    def _r(value):
        return None if value is None else round(value, 2)

    return {
        'score':              _r(score),
        'community_share':    _r(community_share),
        'governance_quality': _r(gov_quality),
        'accountability':     _r(accountability),
        'balance_gap':        _r(balance_gap),
    }
