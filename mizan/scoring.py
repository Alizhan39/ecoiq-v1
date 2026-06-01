"""
mizan/scoring.py — EcoIQ Mizan Engine Core Scoring.

Evaluates companies and countries across six ethical dimensions.
All scoring is rule-based. ML integration point is marked with
# ML-HOOK comments for future scikit-learn classifier replacement.

Public-facing language: Mizan Engine, ethical balance, stewardship,
  harm reduction, justice, transparency, evidence confidence.

Internal Maqasid mapping: docs/mizan-engine.md — INTERNAL ONLY.
Do NOT expose Maqasid terminology in any output field or error message.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from ml.ethics.greenwashing_risk import (
    GreenwashingInput, assess_greenwashing_risk,
    _POLLUTION_TO_FF,
)


# ── Dimension weights (must sum to 1.0) ───────────────────────────────────────
DIMENSION_WEIGHTS: dict[str, float] = {
    'public_benefit':               0.25,
    'harm_reduction':               0.25,
    'justice_distribution':         0.20,
    'transparency_accountability':  0.15,
    'stewardship':                  0.10,
    'evidence_confidence':          0.05,
}

# ── Mizan label tiers ─────────────────────────────────────────────────────────
MIZAN_LABELS: list[tuple[float, str]] = [
    (85.0, 'Exemplary'),
    (70.0, 'Strong'),
    (55.0, 'Moderate'),
    (40.0, 'Developing'),
    (0.0,  'Deficient'),
]

# ── Pollution → base harm value ───────────────────────────────────────────────
_POLLUTION_HARM_BASE: dict[str, float] = {
    'low':    8.0,
    'medium': 28.0,
    'high':   58.0,
    'severe': 82.0,
}

# ── Placeholder phrases that flag ai-seeded profiles ─────────────────────────
_PLACEHOLDER_MARKERS = (
    'seeded by',
    'focus_target_markets',
    'add_400_companies',
    'lorem ipsum',
    'placeholder',
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v or 0)))


def _mean(*vals: float) -> float:
    vals = [v for v in vals if v is not None]
    return _clamp(sum(vals) / len(vals)) if vals else 0.0


def _mizan_label(score: float) -> str:
    for threshold, label in MIZAN_LABELS:
        if score >= threshold:
            return label
    return 'Deficient'


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class MizanResult:
    """
    Full Mizan Engine output — six dimension scores plus aggregates,
    risk flags, and three narrative fields.

    Fully serialisable via .to_dict().
    All float fields are in range 0 – 100.
    """
    # Six dimensions
    public_benefit_score:               float
    harm_reduction_score:               float
    justice_distribution_score:         float
    transparency_accountability_score:  float
    stewardship_score:                  float
    evidence_confidence_score:          float

    # Aggregate
    final_mizan_score:  float
    mizan_label:        str       # 'Exemplary' | 'Strong' | 'Moderate' | 'Developing' | 'Deficient'

    # Narrative
    risk_flags:                list[str]
    investor_note:             str
    islamic_finance_note:      str
    due_diligence_note:        str
    recommended_next_actions:  list[str]

    # Metadata
    data_source: str   # 'company_profile' | 'country_aggregate' | 'project_model'
    confidence:  str   # 'verified' | 'analyst-reviewed' | 'ai-seeded' | 'model-estimate'
    methodology: str   = field(default='EcoIQ Mizan Engine v1 — rule-based; ML integration pending')

    # Greenwashing risk assessment (included automatically for company + project scores)
    greenwashing_risk: dict = field(default_factory=dict)

    # Islamic & Ethical Finance Fit (included automatically for project scores)
    islamic_finance_fit: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Narrative builders ────────────────────────────────────────────────────────

def _investor_note(score: float, risk_flags: list[str]) -> str:
    top_flags = '; '.join(risk_flags[:2])
    suffix    = f' Key concerns: {top_flags}.' if top_flags else ''
    if score >= 85:
        return (
            'Exemplary Mizan alignment across all six dimensions. Strong candidate for '
            f'ethical and responsible finance consideration, subject to verification.{suffix}'
        )
    if score >= 70:
        return (
            'Strong Mizan profile with minor improvement areas. Meets threshold for '
            f'responsible capital consideration under standard due diligence.{suffix}'
        )
    if score >= 55:
        return (
            'Moderate Mizan alignment. Suitable for monitored investment with an agreed '
            f'improvement pathway. Not yet eligible for full responsible finance labelling.{suffix}'
        )
    if score >= 40:
        return (
            'Developing Mizan profile. Material gaps require remediation before responsible '
            f'finance eligibility can be established. Engagement capital may be appropriate.{suffix}'
        )
    return (
        'Below Mizan threshold. Significant improvement in public benefit, harm reduction, '
        f'and governance transparency is required before capital consideration.{suffix}'
    )


def _islamic_finance_note(
    score: float,
    pb: float,
    hr: float,
    jd: float,
    risk_flags: list[str],
) -> str:
    """
    Professional compatibility note for ethical/responsible finance institutions.
    Uses principle-based language only.
    No religious terminology — see docs/mizan-engine.md for internal mapping.
    """
    weak = [
        name for name, s in [
            ('public benefit delivery', pb),
            ('harm reduction', hr),
            ('justice & fair distribution', jd),
        ]
        if s < 50
    ]

    if score >= 70 and not weak:
        return (
            'This profile demonstrates strong alignment with the foundational principles of '
            'ethical capital allocation: genuine public benefit, active harm reduction, '
            'equitable value distribution, and transparent long-term stewardship of resources. '
            'Subject to independent verification, this profile is compatible with responsible '
            'finance frameworks that prioritise justice, trust, and avoidance of harm.'
        )
    if score >= 55:
        gaps = ', '.join(weak) if weak else 'specific areas'
        return (
            f'Partial alignment with ethical finance principles. Improvement in {gaps} '
            'is recommended before full compatibility with responsible capital frameworks '
            'can be established. Engagement-based financing with improvement conditions may apply.'
        )
    return (
        'This profile does not currently meet the threshold for ethical finance framework '
        'compatibility. Material improvement is required in public benefit delivery, '
        'harm reduction, and governance transparency before this profile can be considered '
        'compatible with responsible capital standards.'
    )


def _due_diligence_note(confidence: str, risk_flags: list[str]) -> str:
    base = {
        'verified': (
            'Standard due diligence applies. Review latest annual report, sustainability '
            'disclosures, and independent audit findings.'
        ),
        'analyst-reviewed': (
            'Enhanced due diligence recommended. Cross-reference EcoIQ analyst notes '
            'with primary company disclosures and third-party ESG data sources.'
        ),
        'ai-seeded': (
            'Extended due diligence required. This is an AI-assisted profile based on '
            'public sector and seeded data. Third-party verification of environmental, '
            'governance, and financial disclosures is mandatory before investment use.'
        ),
        'model-estimate': (
            'Indicative assessment only. Project-level due diligence, site visits, and '
            'an independent Environmental and Social Impact Assessment (ESIA) are required '
            'before any capital commitment.'
        ),
    }.get(confidence, 'Independent due diligence required.')

    if 'Severe environmental harm detected' in risk_flags:
        base += ' Environmental harm signals require an independent environmental audit.'
    if 'Material controversy exposure' in risk_flags:
        base += ' Controversy flags require legal and reputational risk review.'
    if 'No environmental impact assessment declared' in risk_flags:
        base += ' Commission an ESIA before project approval.'
    return base


def _recommended_actions(
    pb: float, hr: float, jd: float,
    ta: float, st: float, ec: float,
) -> list[str]:
    """Return up to 4 prioritised, actionable recommendations."""
    _map = {
        'public_benefit': (
            'Quantify community benefit commitments — publish job quality metrics, '
            'local procurement rates, and regional reinvestment figures.'
        ),
        'harm_reduction': (
            'Publish a time-bound decarbonisation roadmap with verified scope 1 & 2 '
            'emission targets and annual progress reporting.'
        ),
        'justice_distribution': (
            'Improve stakeholder engagement and procurement transparency; disclose '
            'supply chain audit results and grievance mechanism outcomes.'
        ),
        'transparency_accountability': (
            'Upgrade governance disclosure: board-level climate oversight, third-party '
            'audit of ESG claims, and operational whistleblower protections.'
        ),
        'stewardship': (
            'Develop a long-term stewardship plan covering water, biodiversity, and '
            'workforce transition with measurable multi-year milestones.'
        ),
        'evidence_confidence': (
            'Submit verified disclosures to EcoIQ to upgrade profile confidence '
            'from AI-seeded to analyst-reviewed or fully verified status.'
        ),
    }
    ranked = sorted([
        (pb, 'public_benefit'),
        (hr, 'harm_reduction'),
        (jd, 'justice_distribution'),
        (ta, 'transparency_accountability'),
        (st, 'stewardship'),
        (ec, 'evidence_confidence'),
    ])
    actions = [_map[name] for score, name in ranked[:4] if score < 70]
    if not actions:
        actions = [
            'Maintain current performance across all six Mizan dimensions.',
            'Pursue verified profile status to strengthen investor confidence.',
        ]
    return actions


# ── Company scorer ─────────────────────────────────────────────────────────────

def score_company(profile: Any) -> MizanResult:
    """
    Compute full Mizan score from a CompanyProfile instance.

    Accepts any object with the standard CompanyProfile field values.
    Returns a MizanResult (fully serialisable via .to_dict()).

    # ML-HOOK: replace individual dimension formulas with
    #   clf.predict_proba(feature_vector(profile)) * 100
    # once a trained scikit-learn model is available.
    """
    # ── 1. Public Benefit ─────────────────────────────────────────────────────
    pb = _mean(
        _clamp(profile.public_benefit_score),
        _clamp(profile.jobs_created_score),
        _clamp(profile.regional_development_score),
        _clamp(profile.national_value_score),
        _clamp(profile.infrastructure_contribution_score),
    )

    # ── 2. Harm Reduction ─────────────────────────────────────────────────────
    pollution = (getattr(profile, 'pollution_level', 'medium') or 'medium').lower()
    harm_base  = _POLLUTION_HARM_BASE.get(pollution, 30.0)
    controversy = _clamp(profile.controversy_risk_score)
    energy_tr   = _clamp(profile.energy_transition_score)

    # Composite harm (0-100, higher = worse)
    raw_harm = _clamp(harm_base * 0.60 + controversy * 0.40)

    # Mitigation discount: active energy transition reduces net harm
    discount = (
        0.30 if energy_tr >= 70 else
        0.15 if energy_tr >= 50 else
        0.07 if energy_tr >= 35 else
        0.0
    )
    net_harm = _clamp(raw_harm * (1 - discount))
    hr = _clamp(100.0 - net_harm)   # invert: high score = low harm

    # ── 3. Justice & Fair Distribution ────────────────────────────────────────
    jd_raw = _mean(
        _clamp(profile.transparency_anti_corruption_score),
        _clamp(profile.anti_corruption_score),
        _clamp(profile.audit_quality_score),
        _clamp(profile.procurement_transparency_score),
    )
    # Governance-vs-controversy gap penalty
    gap_penalty = max(0.0, (jd_raw - (100.0 - controversy)) / 2.0)
    jd = _clamp(jd_raw - gap_penalty)

    # ── 4. Transparency & Accountability ──────────────────────────────────────
    ta = _mean(
        _clamp(profile.transparency_score_detail),
        _clamp(profile.audit_quality_score),
        _clamp(profile.procurement_transparency_score),
        _clamp(profile.transparency_anti_corruption_score),
    )
    # Verified profiles get a 5 % uplift (capped at 100)
    if getattr(profile, 'is_verified', False):
        ta = _clamp(ta * 1.05)

    # ── 5. Stewardship ────────────────────────────────────────────────────────
    st = _mean(
        _clamp(profile.future_readiness_score),
        _clamp(profile.energy_transition_score),
        _clamp(profile.water_impact_score),
        _clamp(profile.biodiversity_impact_score),
        _clamp(profile.ethical_alignment_score),
        _clamp(profile.waste_management_score),
    )

    # ── 6. Evidence Confidence ────────────────────────────────────────────────
    is_verified = getattr(profile, 'is_verified', False)
    status      = str(getattr(profile, 'status', 'public') or 'public')
    summary     = str(getattr(profile, 'ai_summary', '') or '').lower()

    if is_verified:
        ec, confidence = 92.0, 'verified'
    elif any(marker in summary for marker in _PLACEHOLDER_MARKERS):
        ec, confidence = 40.0, 'ai-seeded'
    elif status == 'public':
        ec, confidence = 55.0, 'ai-seeded'
    else:
        ec, confidence = 30.0, 'ai-seeded'

    # ── Weighted final score ──────────────────────────────────────────────────
    w = DIMENSION_WEIGHTS
    final = _clamp(
        pb  * w['public_benefit']
        + hr * w['harm_reduction']
        + jd * w['justice_distribution']
        + ta * w['transparency_accountability']
        + st * w['stewardship']
        + ec * w['evidence_confidence']
    )

    # ── Risk flags ────────────────────────────────────────────────────────────
    flags: list[str] = []
    if pollution == 'severe':
        flags.append('Severe environmental harm detected')
    if pollution == 'high':
        flags.append('High pollution — active mitigation plan required')
    if controversy >= 60:
        flags.append('Material controversy exposure')
    if pb  < 40: flags.append('Below-threshold public benefit delivery')
    if ta  < 40: flags.append('Governance transparency deficit')
    if jd  < 40: flags.append('Justice & distribution gap identified')
    if st  < 40: flags.append('Weak long-term stewardship signal')
    if float(getattr(profile, 'harm_penalty', 0) or 0) >= 12:
        flags.append('Maximum harm penalty applied to EcoIQ total score')
    if confidence == 'ai-seeded':
        flags.append('AI-assisted profile — independent verification required')

    # ── Greenwashing risk assessment ──────────────────────────────────────────
    is_verified = getattr(profile, 'is_verified', False)

    gw_inp = GreenwashingInput(
        climate_claims_strength     = round(_clamp(energy_tr * 0.55 + _clamp(profile.future_readiness_score) * 0.45), 2),
        verified_emissions_data     = round(90.0 if is_verified else _clamp(_clamp(profile.audit_quality_score) * 0.35), 2),
        third_party_assurance       = round(85.0 if is_verified else _clamp(_clamp(profile.audit_quality_score) * 0.30), 2),
        transition_capex_disclosure = round(_clamp(energy_tr * 0.55 + _clamp(profile.infrastructure_upgrade_score) * 0.45), 2),
        fossil_fuel_exposure        = round(_clamp(_POLLUTION_TO_FF.get(pollution, 35.0) * (1.0 - energy_tr / 250.0)), 2),
        target_quality              = round(_clamp(profile.future_readiness_score), 2),
        evidence_confidence         = round(92.0 if is_verified else (55.0 if str(getattr(profile, 'status', 'public')) == 'public' else 35.0), 2),
        controversy_flags           = (3 if controversy >= 80 else 2 if controversy >= 60 else 1 if controversy >= 40 else 0),
        ownership_transparency      = round(_clamp((_clamp(profile.transparency_anti_corruption_score) + _clamp(profile.procurement_transparency_score)) / 2.0), 2),
        entity_type                 = 'company',
    )
    gw_result = assess_greenwashing_risk(gw_inp)

    # Surface greenwashing flags into the main risk_flags list
    if gw_result.risk_level in ('high', 'severe'):
        flags.append(
            f'Greenwashing risk indicators: {gw_result.risk_level} '
            f'(score {gw_result.greenwashing_risk_score:.0f}/100, public-data based) — '
            'independent verification of climate claims required'
        )

    return MizanResult(
        public_benefit_score               = round(pb,    2),
        harm_reduction_score               = round(hr,    2),
        justice_distribution_score         = round(jd,    2),
        transparency_accountability_score  = round(ta,    2),
        stewardship_score                  = round(st,    2),
        evidence_confidence_score          = round(ec,    2),
        final_mizan_score                  = round(final, 2),
        mizan_label                        = _mizan_label(final),
        risk_flags                         = flags,
        investor_note                      = _investor_note(final, flags),
        islamic_finance_note               = _islamic_finance_note(final, pb, hr, jd, flags),
        due_diligence_note                 = _due_diligence_note(confidence, flags),
        recommended_next_actions           = _recommended_actions(pb, hr, jd, ta, st, ec),
        data_source                        = 'company_profile',
        confidence                         = confidence,
        greenwashing_risk                  = gw_result.to_dict(),
    )


# ── Country aggregate scorer ──────────────────────────────────────────────────

def score_country(profiles: list[Any]) -> MizanResult:
    """
    Aggregate Mizan scores across all CompanyProfile instances in a country.
    Each company is scored individually; results are arithmetic-meaned.

    # ML-HOOK: Replace per-company loop with a pre-computed embedding
    #   and a country-level classifier once training data is available.
    """
    if not profiles:
        raise ValueError('No profiles provided for country aggregate scoring.')

    results = [score_company(p) for p in profiles]
    n = len(results)

    def _avg(attr: str) -> float:
        return _clamp(sum(getattr(r, attr) for r in results) / n)

    pb  = _avg('public_benefit_score')
    hr  = _avg('harm_reduction_score')
    jd  = _avg('justice_distribution_score')
    ta  = _avg('transparency_accountability_score')
    st  = _avg('stewardship_score')
    ec  = _avg('evidence_confidence_score')

    w = DIMENSION_WEIGHTS
    final = _clamp(
        pb * w['public_benefit']
        + hr * w['harm_reduction']
        + jd * w['justice_distribution']
        + ta * w['transparency_accountability']
        + st * w['stewardship']
        + ec * w['evidence_confidence']
    )

    # Aggregate flags: keep those appearing in ≥20 % of profiles
    all_flags: list[str] = [f for r in results for f in r.risk_flags]
    threshold  = max(1, int(n * 0.20))
    agg_flags  = [
        flag for flag, cnt in Counter(all_flags).most_common(6)
        if cnt >= threshold
    ]

    # Confidence: downgrade if fewer than 30 % of profiles are verified
    verified_n = sum(1 for r in results if r.confidence == 'verified')
    confidence = (
        'verified'         if verified_n >= n * 0.70 else
        'analyst-reviewed' if verified_n >= n * 0.30 else
        'ai-seeded'
    )

    # ── Country-level greenwashing aggregate ─────────────────────────────────
    gw_scores = [
        r.greenwashing_risk.get('greenwashing_risk_score', 0.0)
        for r in results
        if r.greenwashing_risk
    ]
    gw_levels = [
        r.greenwashing_risk.get('risk_level', 'low')
        for r in results
        if r.greenwashing_risk
    ]
    avg_gw_score = round(sum(gw_scores) / len(gw_scores), 2) if gw_scores else 0.0
    gw_level_dist = dict(Counter(gw_levels).most_common())
    dominant_gw_level = gw_levels[0] if gw_levels else 'low'  # already ordered by most_common
    if gw_level_dist:
        dominant_gw_level = max(gw_level_dist, key=gw_level_dist.get)  # type: ignore[arg-type]
    high_risk_n  = sum(1 for lvl in gw_levels if lvl in ('high', 'severe'))
    country_gw = {
        'greenwashing_risk_score':    avg_gw_score,
        'risk_level':                 dominant_gw_level,
        'high_or_severe_count':       high_risk_n,
        'high_or_severe_pct':         round(high_risk_n / len(results) * 100, 1) if results else 0.0,
        'risk_level_distribution':    gw_level_dist,
        'confidence_note':            (
            'Country greenwashing risk is aggregated from individual company assessments '
            'based on public data only. It reflects the weighted average of company-level '
            'indicators and should be treated as indicative, not conclusive.'
        ),
    }

    return MizanResult(
        public_benefit_score               = round(pb,    2),
        harm_reduction_score               = round(hr,    2),
        justice_distribution_score         = round(jd,    2),
        transparency_accountability_score  = round(ta,    2),
        stewardship_score                  = round(st,    2),
        evidence_confidence_score          = round(ec,    2),
        final_mizan_score                  = round(final, 2),
        mizan_label                        = _mizan_label(final),
        risk_flags                         = agg_flags,
        investor_note                      = _investor_note(final, agg_flags),
        islamic_finance_note               = _islamic_finance_note(final, pb, hr, jd, agg_flags),
        due_diligence_note                 = _due_diligence_note(confidence, agg_flags),
        recommended_next_actions           = _recommended_actions(pb, hr, jd, ta, st, ec),
        data_source                        = 'country_aggregate',
        confidence                         = confidence,
        greenwashing_risk                  = country_gw,
    )
