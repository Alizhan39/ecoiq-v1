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
from core.unknown import clamp, weighted_mean_of_known

# The six pillar keys this module scores on, named once.
_ALL_PILLARS = (
    'public_benefit_score', 'environmental_score', 'modernization_score',
    'governance_score', 'anti_corruption_score', 'ethical_alignment_score',
)

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


def _insufficient_evidence(profile) -> dict:
    """
    The output when no pillar is evidenced.

    Score and grade are None, not 0 and not 'F'. An 'F' grade would be the
    harshest verdict this module can issue, delivered to a company nobody has
    assessed; a 0 would be read the same way. Both eligibility flags are False,
    which is the safe direction — we are not asserting the company fails to
    qualify, only that we cannot assert it qualifies.
    """
    return {
        'responsible_finance_score':      None,
        'ethical_grade':                  None,
        'dimension_scores':               {
            dim_id: {'label': cfg['label'], 'desc': cfg['desc'], 'score': None}
            for dim_id, cfg in _DIMENSION_CONFIG.items()
        },
        'ethical_capital_eligible':       False,
        'responsible_insurance_eligible': False,
        'pollution_penalty':              None,
        'summary_factors': [
            'EcoIQ does not hold evidenced pillar scores for this organisation, so '
            'no responsible finance assessment has been produced. This is a '
            'statement about the available evidence, not a finding about the '
            'organisation, and it must not be read as ineligibility.'
        ],
        'unknown_pillars': list(_ALL_PILLARS),
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

    When no pillar is known the function refuses: responsible_finance_score is
    None, ethical_grade is None, and both eligibility flags are False. A
    financing classification is a claim about a specific company, and there is
    no such thing as a default applicant.
    """
    # Was `float(getattr(profile, 'x', 50) or 50)` — three collapses in one
    # expression: a missing attribute, an unmeasured score, and a genuine
    # measured 0.0 all became 50. The last is the damaging one here: a company
    # with the worst possible governance score was fed to the eligibility
    # thresholds as an average one.
    pillars = {
        'public_benefit_score':    clamp(getattr(profile, 'public_benefit_score', None)),
        'environmental_score':     clamp(getattr(profile, 'environmental_responsibility_score', None)),
        'modernization_score':     clamp(getattr(profile, 'modernization_score', None)),
        'governance_score':        clamp(getattr(profile, 'transparency_anti_corruption_score', None)),
        'anti_corruption_score':   clamp(getattr(profile, 'anti_corruption_score', None)),
        'ethical_alignment_score': clamp(getattr(profile, 'ethical_alignment_score', None)),
    }

    if all(v is None for v in pillars.values()):
        return _insufficient_evidence(profile)

    # ── Dimension scores ────────────────────────────────────────────────────
    # Re-normalised across the known pillars, so a company is not scored lower
    # for an input nobody assessed. A dimension whose pillars are all unknown
    # reports None and is excluded from the composite rather than counted as 50.
    dimension_scores = {}
    dim_pairs = []

    for dim_id, cfg in _DIMENSION_CONFIG.items():
        dim_score = weighted_mean_of_known(
            *[(pillars.get(p), w) for p, w in cfg['pillars'].items()]
        )
        dimension_scores[dim_id] = {
            'label': cfg['label'],
            'desc':  cfg['desc'],
            'score': None if dim_score is None else round(dim_score, 1),
        }
        dim_pairs.append((dim_score, cfg['total_weight']))

    weighted_total = weighted_mean_of_known(*dim_pairs)
    if weighted_total is None:
        return _insufficient_evidence(profile)

    # ── Penalties ───────────────────────────────────────────────────────────
    # Was `getattr(profile, 'pollution_level', 'medium') or 'medium'` — an
    # unclassified company was silently treated as a medium polluter and
    # docked 5 points. That is an adverse finding invented from an absence,
    # and it is the same fabrication greenwashing_from_profile already fixed
    # ("`or 'medium'` substituted a real classification for a missing one").
    #
    # Unknown now applies no penalty, matching the harm_penalty treatment
    # immediately below: absence of evidence is not evidence of harm. The
    # unknown is surfaced rather than swallowed, so it is not mistaken for a
    # measured 'low'.
    raw_pollution    = getattr(profile, 'pollution_level', None)
    pollution_level  = raw_pollution.lower() if raw_pollution else None
    pollution_penalty = (0 if pollution_level is None
                         else _POLLUTION_PENALTY.get(pollution_level, 0))
    weighted_total   += pollution_penalty

    # An unknown harm penalty applies no deduction — absence of evidence is not
    # evidence of harm — but it is not silently treated as a measured zero
    # either; the caller sees it in summary_factors only when it is real.
    harm_penalty = clamp(getattr(profile, 'harm_penalty', None), hi=100.0)
    weighted_total -= (harm_penalty or 0.0) * 0.5   # 50% weight for responsible finance

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
    # Guarded on the value being known. Each of these is a claim: the first two
    # about the company's governance and environmental performance, and neither
    # may be produced by an input nobody measured.
    anti_c = pillars['anti_corruption_score']
    env    = pillars['environmental_score']
    if anti_c is not None and anti_c < 50:
        summary_factors.append(
            'Below-median anti-corruption score — governance improvement recommended.'
        )
    if env is not None and env > 75:
        summary_factors.append(
            'Strong environmental stewardship — positive alignment with responsible finance criteria.'
        )
    if rf_score >= 80:
        summary_factors.append(
            'Score qualifies for ethical capital markets and responsible investment screening.'
        )
    if harm_penalty is not None and harm_penalty > 5:
        summary_factors.append(
            f'Active harm penalty ({harm_penalty:.0f} pts) reduces responsible finance score.'
        )
    if sector_penalty < 0:
        summary_factors.append(
            'Sector carries responsible-finance exclusion concerns — reduced eligibility.'
        )
    if pollution_level is None:
        summary_factors.append(
            'Pollution level is not classified for this organisation, so no '
            'environmental harm penalty has been applied. This is a gap in the '
            'evidence, not a finding that the organisation is low-polluting.'
        )
    unknown_pillars = [name for name, value in pillars.items() if value is None]
    if unknown_pillars:
        summary_factors.append(
            f'{len(unknown_pillars)} of {len(pillars)} pillar scores are not yet '
            'evidenced — this score is computed from the pillars that are, and '
            'coverage should be considered before relying on it.'
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
        'unknown_pillars':                 unknown_pillars,
    }


def get_responsible_finance_score(profile) -> float | None:
    """Convenience — returns just the score (0–100), or None if unassessable."""
    return compute_responsible_finance_score(profile)['responsible_finance_score']


# ── Derived provenance (D3C-3f) ───────────────────────────────────────────────

RESPONSIBLE_FINANCE_METHOD = 'ecoiq-responsible-finance-stewardship'
RESPONSIBLE_FINANCE_VERSION = '1'
RESPONSIBLE_FINANCE_METRIC_KEY = 'ml.responsible_finance'

#: Registry keys this scorer reads. Five of the six pillars are DERIVED, so
#: the lineage points at pillar provenance rows rather than being flattened to
#: their material ancestors; company.harm_penalty is derived too.
#:
#: NOT the same thing as financing.readiness (#252). That metric is persisted
#: on CompanyFinancingProfile and computed by financing/matching.py, which has
#: no reference to this module in either direction. Two independent
#: assessments that both concern capital, not one wrapping the other.
RESPONSIBLE_FINANCE_INPUTS: tuple[str, ...] = (
    'company.public_benefit',
    'company.environmental',
    'company.modernization',
    'company.transparency_governance',
    'anti_corruption_score',
    'company.ethical_alignment',
    'company.harm_penalty',
)

#: KNOWN GAPS — pollution_level (penalty up to -30) and company.sector
#: (exclusion penalty) have no provenance rows. See
#: docs/product/CALCULATION_CONTEXT_PROVENANCE.md.


def compute_and_record(profile) -> dict:
    """
    Compute the Responsible Finance assessment AND record its lineage.

    Separate from `compute_responsible_finance_score`, which is pure and is
    called per request from api/views.py.

    ml.responsible_finance is EPHEMERAL — the scorer returns a dict and nothing
    persists the composite — so the provenance row carries `recorded_value`.

    An insufficient-evidence result records nothing: the score is None there,
    and both eligibility flags are False because we cannot assert eligibility,
    not because we found ineligibility. A provenance row would turn that
    absence into an assertion.

    Returns the result dict with a 'provenance_status' key added.
    """
    from django.db import transaction
    from companies import provenance as prov

    with transaction.atomic():
        result = compute_responsible_finance_score(profile)
        result['provenance_status'] = prov.record_calculated(
            profile, RESPONSIBLE_FINANCE_METRIC_KEY,
            result['responsible_finance_score'], RESPONSIBLE_FINANCE_INPUTS,
            writer='ml.responsible_finance.compute_and_record',
            methodology=RESPONSIBLE_FINANCE_METHOD,
            calculation_version=RESPONSIBLE_FINANCE_VERSION,
        )
    return result
