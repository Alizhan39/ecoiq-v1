"""
ml/ethics/evidence_confidence.py — Data quality and evidence confidence.

Returns a confidence tier and score (0.0–1.0) indicating how reliable
the profile data is. Verified profiles score highest; AI-seeded profiles
score lower and carry a requires_verification flag.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from companies.models import CompanyProfile


_TIER_SCORES = {
    'verified':          0.92,
    'public':            0.55,  # seeded from public data, not analyst-reviewed
    'draft':             0.30,
    'archived':          0.20,
}

_PLACEHOLDER_PHRASES = (
    'seeded by',
    'focus_target_markets',
    'add_400_companies',
    'lorem ipsum',
    'placeholder',
    'TODO',
)


def compute_evidence_confidence(profile: 'CompanyProfile') -> dict:
    """
    Returns a dict with:
        confidence_score    — 0.0 to 1.0
        confidence_tier     — 'verified' | 'analyst-reviewed' | 'ai-seeded' | 'draft'
        requires_verification — bool
        data_notes          — list of human-readable quality flags
    """
    notes: list[str] = []

    # Base score from profile status
    base = _TIER_SCORES.get(str(profile.status), 0.40)

    # Verified profiles get analyst-reviewed tier
    if getattr(profile, 'is_verified', False):
        tier  = 'verified'
        score = 0.92
    elif str(profile.status) == 'public':
        # Check for placeholder ai_summary → definitely ai-seeded
        summary = str(profile.ai_summary or '').lower()
        if any(p in summary for p in _PLACEHOLDER_PHRASES):
            tier  = 'ai-seeded'
            score = 0.40
            notes.append('Profile description contains seed placeholder text.')
        else:
            tier  = 'ai-seeded'
            score = 0.55
            notes.append('Profile is based on AI-assisted scoring from public sector data.')
    else:
        tier  = 'draft'
        score = base

    requires_verification = tier != 'verified'

    if requires_verification:
        notes.append(
            'This profile requires independent analyst review before investment use.'
        )

    return {
        'confidence_score':      round(score, 2),
        'confidence_tier':       tier,
        'requires_verification': requires_verification,
        'data_notes':            notes,
    }
