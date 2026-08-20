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

from core.unknown import clamp, mean_of_known, weighted_mean_of_known

from ml.ethics.greenwashing_risk import (
    RISK_INSUFFICIENT_EVIDENCE, GreenwashingInput, assess_greenwashing_risk,
    greenwashing_from_profile, _POLLUTION_TO_FF,
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

# core.unknown is the single authority (D2b). Was `float(v or 0)`.
#
# STEP 8 classification: this is a MISSING-INPUT FALLBACK, not a Mizan domain
# midpoint. The genuine midpoints in this module — `s < 50` at the weak-dimension
# check and the `energy_tr >= 50` mitigation tier — are thresholds applied to
# already-computed dimension scores, and they are left exactly as they are.
_clamp = clamp
_weighted = weighted_mean_of_known


def _mean(*vals):
    """
    Mean of the known values, or None when none are known.

    Was `... if vals else 0.0`. Invisible to the `or 50` / `float(v or 0)`
    sweeps that found everything else in this programme, and worse than either:
    every dimension of an unassessed company came back as 0.0, so the profile
    collected all four deficiency flags, the 'Deficient' Mizan label, and a full
    set of remediation recommendations.

    Found by a test rather than by grep, which is the argument for writing the
    behavioural tests before trusting the pattern search.
    """
    return mean_of_known(*vals)


def _known_and(value, predicate) -> bool:
    """Apply a threshold only when the value is known. Unknown asserts nothing."""
    return value is not None and predicate(value)


def _r2(value):
    """round(v, 2) that leaves unknown alone."""
    return None if value is None else round(value, 2)


# Outside the ordered tiers: not a degree of balance, but the absence of an
# assessment. 'Deficient' was the fall-through, so an unassessed company landed
# on the harshest Mizan label by default.
LABEL_INSUFFICIENT_EVIDENCE = 'Insufficient Evidence'


def _mizan_label(score) -> str:
    if score is None:
        return LABEL_INSUFFICIENT_EVIDENCE
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
    All float fields are in range 0 – 100, or None where the underlying
    evidence does not exist. See LABEL_INSUFFICIENT_EVIDENCE.
    """
    # Six dimensions. Each is None where EcoIQ has no evidence to compute it —
    # never 0, which on a 0-100 balance scale is the worst possible finding.
    public_benefit_score:               float | None
    harm_reduction_score:               float | None
    justice_distribution_score:         float | None
    transparency_accountability_score:  float | None
    stewardship_score:                  float | None
    evidence_confidence_score:          float | None

    # Aggregate
    final_mizan_score:  float | None
    mizan_label:        str  # 'Exemplary'|'Strong'|'Moderate'|'Developing'|'Deficient'|'Insufficient Evidence'

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

def _investor_note(score, risk_flags: list[str]) -> str:
    top_flags = '; '.join(risk_flags[:2])
    suffix    = f' Key concerns: {top_flags}.' if top_flags else ''
    if score is None:
        return (
            'No Mizan score has been produced for this profile because the underlying '
            'evidence is not available to EcoIQ. This is a statement about the data, '
            f'not about the entity, and it is not a negative finding.{suffix}'
        )
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
    # A dimension we could not compute is not a WEAK dimension. Listing it as
    # one would name it in the note as an area the company falls short in.
    weak = [
        name for name, s in [
            ('public benefit delivery', pb),
            ('harm reduction', hr),
            ('justice & fair distribution', jd),
        ]
        if s is not None and s < 50
    ]

    if score is None:
        return (
            'EcoIQ does not hold enough evidence to assess this profile against the '
            'principles of ethical capital allocation. No compatibility conclusion has '
            'been drawn in either direction, and the absence of one must not be read '
            'as either alignment or misalignment.'
        )

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


def _recommended_actions(pb, hr, jd, ta, st, ec) -> list[str]:
    """
    Return up to 4 prioritised, actionable recommendations.

    Dimensions we could not compute are EXCLUDED from the ranking. A
    recommendation here asserts that a specific dimension falls short of 70 and
    tells the company how to fix it; with the pre-D2c _clamp an unassessed
    profile scored 0 on everything, sorted to the top of the ranking, and
    received the full set of four.
    """
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
    ranked = sorted(
        (score, name) for score, name in [
            (pb, 'public_benefit'),
            (hr, 'harm_reduction'),
            (jd, 'justice_distribution'),
            (ta, 'transparency_accountability'),
            (st, 'stewardship'),
            (ec, 'evidence_confidence'),
        ]
        if score is not None
    )
    actions = [_map[name] for score, name in ranked[:4] if score < 70]
    if not actions:
        # Distinguish "nothing to improve" from "nothing to go on". The old
        # code returned the first message in both cases, congratulating a
        # company on performance nobody had measured.
        if all(v is None for v in (pb, hr, jd, ta, st)):
            actions = [
                'Submit verified disclosures to EcoIQ so a Mizan assessment can be '
                'produced — no dimension currently has enough evidence to score.'
            ]
        else:
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
    # `or 'medium'` substituted a real pollution classification for a missing one.
    raw_pollution = getattr(profile, 'pollution_level', None)
    pollution   = raw_pollution.lower() if raw_pollution else None
    harm_base   = _POLLUTION_HARM_BASE.get(pollution)
    controversy = _clamp(profile.controversy_risk_score)
    energy_tr   = _clamp(profile.energy_transition_score)

    # Composite harm (0-100, higher = worse), re-normalised across the known
    # channels. The old form counted an unknown controversy score as zero harm,
    # which is a positive claim rather than silence.
    raw_harm = _clamp(_weighted((harm_base, 0.60), (controversy, 0.40)))

    # Mitigation discount: active energy transition reduces net harm. Unknown
    # earns none — a discount asserts the company is actively reducing harm.
    discount = (
        0.30 if _known_and(energy_tr, lambda v: v >= 70) else
        0.15 if _known_and(energy_tr, lambda v: v >= 50) else
        0.07 if _known_and(energy_tr, lambda v: v >= 35) else
        0.0
    )
    net_harm = _clamp(None if raw_harm is None else raw_harm * (1 - discount))
    hr = _clamp(None if net_harm is None else 100.0 - net_harm)   # invert

    # ── 3. Justice & Fair Distribution ────────────────────────────────────────
    jd_raw = _mean(
        _clamp(profile.transparency_anti_corruption_score),
        _clamp(profile.anti_corruption_score),
        _clamp(profile.audit_quality_score),
        _clamp(profile.procurement_transparency_score),
    )
    # Governance-vs-controversy gap penalty. A gap is a COMPARISON, so both
    # halves must be known — comparing against an unknown controversy level
    # asserts the level.
    if jd_raw is None:
        jd = None
    elif controversy is None:
        jd = _clamp(jd_raw)
    else:
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
    if ta is not None and getattr(profile, 'is_verified', False):
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
    # Re-normalised across the known dimensions. evidence_confidence is always
    # known (it is derived from status and verification, not from a score), so
    # the composite is None only when every substantive dimension is unknown —
    # at which point the remaining term would be evidence confidence alone, and
    # a Mizan score built purely from "how much we trust data we do not have"
    # is not a score.
    w = DIMENSION_WEIGHTS
    substantive = (pb, hr, jd, ta, st)
    if all(v is None for v in substantive):
        final = None
    else:
        final = _clamp(_weighted(
            (pb, w['public_benefit']),
            (hr, w['harm_reduction']),
            (jd, w['justice_distribution']),
            (ta, w['transparency_accountability']),
            (st, w['stewardship']),
            (ec, w['evidence_confidence']),
        ))

    # ── Risk flags ────────────────────────────────────────────────────────────
    flags: list[str] = []
    if pollution == 'severe':
        flags.append('Severe environmental harm detected')
    if pollution == 'high':
        flags.append('High pollution — active mitigation plan required')
    if _known_and(controversy, lambda v: v >= 60):
        flags.append('Material controversy exposure')
    # Each of these is a finding about the company. With the old _clamp an
    # unassessed profile scored 0 on every dimension and collected all four.
    if _known_and(pb, lambda v: v < 40): flags.append('Below-threshold public benefit delivery')
    if _known_and(ta, lambda v: v < 40): flags.append('Governance transparency deficit')
    if _known_and(jd, lambda v: v < 40): flags.append('Justice & distribution gap identified')
    if _known_and(st, lambda v: v < 40): flags.append('Weak long-term stewardship signal')
    # Classified per STEP 8 as a MISSING-INPUT FALLBACK, not a domain midpoint.
    # Its direction was already safe — unknown became 0, which never reaches the
    # 12-point trigger, so no flag was fabricated. Made explicit so it stays
    # safe once harm_penalty becomes nullable, and so a genuine measured 0.0 is
    # no longer indistinguishable from an unmeasured one.
    _harm = clamp(getattr(profile, 'harm_penalty', None), hi=100.0)
    if _harm is not None and _harm >= 12:
        flags.append('Maximum harm penalty applied to EcoIQ total score')
    if confidence == 'ai-seeded':
        flags.append('AI-assisted profile — independent verification required')

    # ── Greenwashing risk assessment ──────────────────────────────────────────
    is_verified = getattr(profile, 'is_verified', False)

    # Was a second, inline copy of greenwashing_from_profile's derivation —
    # the same nine formulas, written out again. Two copies of a greenwashing
    # derivation is two places for it to drift, and the copy here carried the
    # same `_clamp(None) -> 0` defect. Delegating means one derivation, already
    # corrected, and mizan inherits the insufficient_evidence state for free.
    gw_result = greenwashing_from_profile(profile)

    # Surface greenwashing flags into the main risk_flags list
    if (gw_result.risk_level in ('high', 'severe')
            and gw_result.greenwashing_risk_score is not None):
        flags.append(
            f'Greenwashing risk indicators: {gw_result.risk_level} '
            f'(score {gw_result.greenwashing_risk_score:.0f}/100, public-data based) — '
            'independent verification of climate claims required'
        )

    return MizanResult(
        public_benefit_score               = _r2(pb),
        harm_reduction_score               = _r2(hr),
        justice_distribution_score         = _r2(jd),
        transparency_accountability_score  = _r2(ta),
        stewardship_score                  = _r2(st),
        evidence_confidence_score          = _r2(ec),
        final_mizan_score                  = _r2(final),
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

    def _avg(attr: str):
        """
        Mean over the companies that HAVE this dimension.

        The old form summed every company's value and divided by n, so a
        company we could not assess entered the country average as a 0 — and
        with the pre-D2c _clamp, unassessed companies were all zeros. A country
        of unmeasured companies averaged near the bottom of the scale, and the
        result was published as that country's Mizan standing.

        None when no company in the country has the dimension.
        """
        return _clamp(mean_of_known(*[getattr(r, attr) for r in results]))

    pb  = _avg('public_benefit_score')
    hr  = _avg('harm_reduction_score')
    jd  = _avg('justice_distribution_score')
    ta  = _avg('transparency_accountability_score')
    st  = _avg('stewardship_score')
    ec  = _avg('evidence_confidence_score')

    w = DIMENSION_WEIGHTS
    if all(v is None for v in (pb, hr, jd, ta, st)):
        final = None
    else:
        final = _clamp(_weighted(
            (pb, w['public_benefit']),
            (hr, w['harm_reduction']),
            (jd, w['justice_distribution']),
            (ta, w['transparency_accountability']),
            (st, w['stewardship']),
            (ec, w['evidence_confidence']),
        ))

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
    # `.get(..., 0.0)` treated an unassessable company as zero greenwashing
    # risk — the most favourable value on the scale — and `.get(..., 'low')`
    # said the same in words. Companies without an assessment are excluded from
    # the country aggregate rather than counted as clean.
    gw_scores = [
        r.greenwashing_risk['greenwashing_risk_score']
        for r in results
        if r.greenwashing_risk
        and r.greenwashing_risk.get('greenwashing_risk_score') is not None
    ]
    gw_levels = [
        r.greenwashing_risk['risk_level']
        for r in results
        if r.greenwashing_risk
        and r.greenwashing_risk.get('risk_level') not in (None, RISK_INSUFFICIENT_EVIDENCE)
    ]
    avg_gw_score = round(sum(gw_scores) / len(gw_scores), 2) if gw_scores else None
    gw_level_dist = dict(Counter(gw_levels).most_common())
    dominant_gw_level = gw_levels[0] if gw_levels else RISK_INSUFFICIENT_EVIDENCE
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
        public_benefit_score               = _r2(pb),
        harm_reduction_score               = _r2(hr),
        justice_distribution_score         = _r2(jd),
        transparency_accountability_score  = _r2(ta),
        stewardship_score                  = _r2(st),
        evidence_confidence_score          = _r2(ec),
        final_mizan_score                  = _r2(final),
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
