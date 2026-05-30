"""
ml/responsible_finance.py — Responsible Finance alignment scoring.

Maps EcoIQ pillar scores to five long-term stewardship dimensions,
producing a composite Responsible Finance score (0–100) and
eligibility assessments for ethical capital market instruments.

This is an INTERNAL module — computational logic only.
All public-facing API fields use neutral ESG terminology.

Framework: five universal stewardship objectives grounded in
sustainable development, intergenerational equity, and ethical economics.
"""

# ── Stewardship dimension weights ──────────────────────────────────────────
#
# Five objectives (internal labels for computation only):
#   D1  Life & Wellbeing          — human health, safety, community
#   D2  Knowledge & Innovation    — education, technology, capacity
#   D3  Intergenerational Equity  — sustainability, long-term thinking
#   D4  Ethical Economics         — fair distribution, anti-corruption
#   D5  Environmental Stewardship — nature, climate, biodiversity
#
# EcoIQ pillar → dimension weight mappings

_DIMENSION_CONFIG = {
    'D1': {
        'label': 'Life & Wellbeing',
        'desc': 'Human health, community benefit, and social value',
        'pillars': {
            'public_benefit_score': 0.35,
            'environmental_score':  0.35,
            'anti_corruption_score':0.30,
        },
        'total_weight': 0.30,
    },
    'D2': {
        'label': 'Knowledge & Innovation',
        'desc': 'Technology leadership, digital readiness, future capacity',
        'pillars': {
            'modernization_score':       0.50,
            'governance_score':          0.30,
            'ethical_alignment_score':   0.20,
        },
        'total_weight': 0.15,
    },
    'D3': {
        'label': 'Intergenerational Equity',
        'desc': 'Long-term sustainability and future-generations thinking',
        'pillars': {
            'environmental_score':   0.50,
            'public_benefit_score':  0.30,
            'modernization_score':   0.20,
        },
        'total_weight': 0.25,
    },
    'D4': {
        'label': 'Ethical Economics',
        'desc': 'Anti-corruption, fair governance, and equitable distribution',
        'pillars': {
            'anti_corruption_score': 0.40,
            'governance_score':      0.35,
            'public_benefit_score':  0.25,
        },
        'total_weight': 0.20,
    },
    'D5': {
        'label': 'Environmental Stewardship',
        'desc': 'Ecological responsibility, climate action, biodiversity',
        'pillars': {
            'environmental_score':     0.60,
            'public_benefit_score':    0.25,
            'ethical_alignment_score': 0.15,
        },
        'total_weight': 0.10,
    },
}

# Sectors with inherent responsible-finance concerns (research-based exclusions)
_EXCLUDED_SECTORS = {
    'alcohol':    -80,
    'gambling':   -80,
    'tobacco':    -60,
    'weapons':    -40,
}

# Pollution penalty — environmental harm degrades responsible finance score
_POLLUTION_PENALTY = {
    'low':    0,
    'medium': -5,
    'high':   -15,
    'severe': -30,
}


def compute_responsible_finance_score(profile):
    """
    Compute a Responsible Finance alignment score for a CompanyProfile.

    Accepts a companies.models.CompanyProfile instance.

    Returns a dict with public-safe neutral field names:
      responsible_finance_score  — 0–100 composite score
      ethical_grade              — A / B / C / D / F
      dimension_scores           — per-dimension breakdown
      ethical_capital_eligible   — bool (green sukuk / ethical bond analogue)
      responsible_insurance_eligible — bool (takaful / mutual insurance analogue)
      pollution_penalty          — penalty applied (negative number or 0)
      summary_factors            — list of plain-English key factors
    """
    pillars = {
        'public_benefit_score':   float(getattr(profile, 'public_benefit_score', 50) or 50),
        'environmental_score':    float(getattr(profile, 'environmental_responsibility_score', 50) or 50),
        'modernization_score':    float(getattr(profile, 'modernization_score', 50) or 50),
        'governance_score':       float(getattr(profile, 'transparency_anti_corruption_score', 50) or 50),
        'anti_corruption_score':  float(getattr(profile, 'anti_corruption_score', 50) or 50),
        'ethical_alignment_score':float(getattr(profile, 'ethical_alignment_score', 50) or 50),
    }

    # ── Dimension scores ────────────────────────────────────────────────────
    dimension_scores = {}
    weighted_total = 0.0

    for dim_id, cfg in _DIMENSION_CONFIG.items():
        dim_score = sum(
            pillars.get(p, 50) * w for p, w in cfg['pillars'].items()
        )
        dimension_scores[dim_id] = {
            'label': cfg['label'],
            'desc':  cfg['desc'],
            'score': round(dim_score, 1),
        }
        weighted_total += dim_score * cfg['total_weight']

    # ── Penalties ───────────────────────────────────────────────────────────
    pollution_level  = getattr(profile, 'pollution_level', 'medium') or 'medium'
    pollution_penalty = _POLLUTION_PENALTY.get(pollution_level, 0)
    weighted_total   += pollution_penalty

    harm_penalty = float(getattr(profile, 'harm_penalty', 0) or 0)
    weighted_total -= harm_penalty * 0.5   # 50% weight for responsible finance

    # Sector exclusion adjustment
    sector = ''
    try:
        sector = (profile.company.sector or '').lower()
    except Exception:
        pass
    sector_penalty = _EXCLUDED_SECTORS.get(sector, 0)
    weighted_total += sector_penalty

    # ── Clamp and round ─────────────────────────────────────────────────────
    rf_score = round(max(0.0, min(100.0, weighted_total)), 1)

    # ── Grade ───────────────────────────────────────────────────────────────
    if rf_score >= 80:   grade = 'A'
    elif rf_score >= 65: grade = 'B'
    elif rf_score >= 50: grade = 'C'
    elif rf_score >= 35: grade = 'D'
    else:                grade = 'F'

    # ── Eligibility flags ───────────────────────────────────────────────────
    # ethical_capital_eligible: analogous to ethical/green bond eligibility
    ethical_capital_eligible = (
        rf_score >= 60 and pollution_penalty >= -5 and sector_penalty == 0
    )
    # responsible_insurance_eligible: analogous to mutual/cooperative insurance
    responsible_insurance_eligible = rf_score >= 55 and sector_penalty == 0

    # ── Plain-language summary ──────────────────────────────────────────────
    summary_factors = []
    if pollution_penalty < -10:
        summary_factors.append(
            f'High pollution level ({pollution_level}) — environmental harm penalty of '
            f'{abs(pollution_penalty)} pts applied.'
        )
    if pillars['anti_corruption_score'] < 50:
        summary_factors.append(
            'Below-median anti-corruption score — governance improvement recommended.'
        )
    if pillars['environmental_score'] > 75:
        summary_factors.append(
            'Strong environmental stewardship — positive alignment with responsible finance criteria.'
        )
    if rf_score >= 80:
        summary_factors.append(
            'Score qualifies for ethical capital markets and responsible investment screening.'
        )
    if harm_penalty > 5:
        summary_factors.append(
            f'Active harm penalty ({harm_penalty:.0f} pts) reduces responsible finance score.'
        )
    if sector_penalty < 0:
        summary_factors.append(
            'Sector carries responsible-finance exclusion concerns — reduced eligibility.'
        )
    if not summary_factors:
        summary_factors.append('Score within normal range. Continue improving pillar scores.')

    return {
        'responsible_finance_score':       rf_score,
        'ethical_grade':                   grade,
        'dimension_scores':                dimension_scores,
        'ethical_capital_eligible':        ethical_capital_eligible,
        'responsible_insurance_eligible':  responsible_insurance_eligible,
        'pollution_penalty':               pollution_penalty,
        'summary_factors':                 summary_factors,
    }


def get_responsible_finance_score(profile) -> float:
    """Convenience — returns just the score (0–100)."""
    return compute_responsible_finance_score(profile)['responsible_finance_score']
