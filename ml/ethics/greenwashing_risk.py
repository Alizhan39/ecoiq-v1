"""
ml/ethics/greenwashing_risk.py — EcoIQ Greenwashing Risk Detector.

Assesses whether a company, country aggregate, or project may be
overstating climate performance relative to the available evidence.

The detector does NOT make definitive claims. Every output uses
cautious language — "may indicate", "requires verification",
"based on public data". It is a structured signal for investor
due diligence, not a legal finding.

Nine inputs (all normalised 0–100 or int counts):
  climate_claims_strength      — strength of stated environmental / transition claims
  verified_emissions_data      — degree to which emissions figures are independently verified
  third_party_assurance        — level of external certification or audit
  transition_capex_disclosure  — disclosed capital investment towards transition
  fossil_fuel_exposure         — exposure to fossil fuels or high-carbon activities
  target_quality               — specificity and credibility of published climate targets
  evidence_confidence          — overall data quality and profile confidence level
  controversy_flags            — count of active controversy or enforcement signals
  ownership_transparency       — transparency of ownership and governance structures

Risk levels:
  severe  ≥ 70  — Material indicators. Enhanced due diligence required before any capital decision.
  high    ≥ 50  — Significant indicators. Independent verification urgently recommended.
  medium  ≥ 30  — Moderate indicators. Specific gaps in evidence require follow-up.
  low     < 30  — Limited indicators based on available data. Standard due diligence applies.

Integration:
  - Mizan Engine (company, country, project): included as greenwashing_risk dict in MizanResult
  - Ethical Intelligence (company): included as greenwashing_risk dict in compute_ethical_intelligence()
  - Capital Integrity Score: has its own greenwashing_risk dimension (separate)

Important: This module produces public-data-based signals only. Results must NOT be
presented as fact, defamatory assertions, or legal findings about any entity.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from companies.models import CompanyProfile

from core.unknown import clamp, mean_of_known, weighted_mean_of_known


# ── Risk level tiers ──────────────────────────────────────────────────────────

RISK_LEVELS: list[tuple[float, str]] = [
    (70.0, 'severe'),
    (50.0, 'high'),
    (30.0, 'medium'),
    (0.0,  'low'),
]

# A fourth state, outside the ordered tiers because it is not a degree of risk.
#
# Greenwashing is the most sensitive assessment EcoIQ makes, and it failed in
# BOTH directions. With the old `float(v or 0)` an unassessed company produced
# climate_claims_strength=0 and therefore claim_evidence_gap=0 — a computed
# 'low' greenwashing risk, which reads as "we looked, and this company is not
# greenwashing." The same absence pushed ownership_opacity to 70, contributing
# risk from nothing at all. Absence must not become either verdict.
#
# Three states must stay distinct:
#     NO EVIDENCE TO ASSESS      <- this one
#     EVIDENCE OF GREENWASHING   <- 'high' / 'severe'
#     EVIDENCE OF LOW RISK       <- 'low'
RISK_INSUFFICIENT_EVIDENCE = 'insufficient_evidence'

# Assessment needs the claim side AND at least one evidence channel: without a
# claim there is nothing to test for exaggeration, and without evidence there is
# nothing to test it against.
_EVIDENCE_CHANNELS = (
    'verified_emissions_data',
    'third_party_assurance',
    'target_quality',
)

# ── Pollution level → fossil fuel exposure proxy ──────────────────────────────

_POLLUTION_TO_FF: dict[str, float] = {
    'low':    10.0,
    'medium': 35.0,
    'high':   65.0,
    'severe': 85.0,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

# core.unknown is the single authority (D2b). Was `float(v or 0)`.
_clamp = clamp


def _risk_level(score):
    """Risk tier, or the explicit not-assessable state. Never 'low' by default."""
    if score is None:
        return RISK_INSUFFICIENT_EVIDENCE
    for threshold, label in RISK_LEVELS:
        if score >= threshold:
            return label
    return 'low'


# ── Input dataclass ───────────────────────────────────────────────────────────

@dataclass
class GreenwashingInput:
    """
    Structured inputs for the Greenwashing Risk Detector.

    All float fields are normalised to 0–100, or None where the caller does not
    know the value. The defaults are kept as-is so existing direct constructions
    are unchanged; None must be passed EXPLICITLY, by a caller that knows the
    input is unmeasured rather than zero.
    controversy_flags is an integer count (0, 1, 2, 3 …), or None if unassessed.
    entity_type identifies the source: 'company' | 'project' | 'country'.
    """
    climate_claims_strength:     float = 50.0   # 0-100: strength of stated climate / green claims
    verified_emissions_data:     float = 0.0    # 0-100: emissions data independently verified
    third_party_assurance:       float = 0.0    # 0-100: external certification or audit level
    transition_capex_disclosure: float = 0.0    # 0-100: disclosed capital towards transition
    fossil_fuel_exposure:        float = 0.0    # 0-100: exposure to fossil fuels / high-carbon activities
    target_quality:              float = 0.0    # 0-100: specificity of published climate targets
    evidence_confidence:         float = 35.0   # 0-100: overall data quality and confidence
    controversy_flags:           int   = 0      # count of active controversies or enforcement signals
    ownership_transparency:      float = 50.0   # 0-100: ownership and governance transparency
    entity_type:                 str   = 'company'   # 'company' | 'project' | 'country'

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'GreenwashingInput':
        valid = {f for f in cls.__dataclass_fields__}   # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in valid})


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class GreenwashingAssessment:
    """
    Full Greenwashing Risk output.

    Fully serialisable via .to_dict().
    All language uses cautious, public-data-based framing.
    """
    greenwashing_risk_score:    float | None  # 0-100 (higher = more risk), None if unassessable
    risk_level:                 str           # 'low'|'medium'|'high'|'severe'|'insufficient_evidence'
    main_red_flags:             list[str]
    missing_evidence:           list[str]
    explanation:                str
    investor_warning:           str
    recommended_due_diligence:  list[str]
    confidence_note:            str         # always-present caveat on data provenance

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Core scoring ──────────────────────────────────────────────────────────────

def _evidence_composite(inp: GreenwashingInput) -> float:
    """
    Weighted composite of evidence quality signals.
    Higher score = more evidence backing the claims.
    """
    return _clamp(weighted_mean_of_known(
        (inp.verified_emissions_data, 0.30),
        (inp.third_party_assurance,   0.30),
        (inp.target_quality,          0.25),
        (inp.evidence_confidence,     0.15),
    ))


def _score_components(inp: GreenwashingInput) -> dict[str, float]:
    """
    Compute each risk component as a 0–100 score.
    Higher component score = more risk signal for that factor.
    """
    ev_composite = _evidence_composite(inp)
    claims = _clamp(inp.climate_claims_strength)

    def _pair(a, b, fn):
        return None if a is None or b is None else fn(a, b)

    # 1. Claim-to-evidence gap: the primary greenwashing signal.
    #    High claims with low evidence = high gap risk.
    claim_evidence_gap = _clamp(_pair(claims, ev_composite, lambda c, e: c - e))

    # 2. Fossil fuel amplifier: high FF exposure combined with high green claims.
    #    A coal company claiming carbon neutrality is the extreme case.
    ff_risk = _clamp(_pair(
        _clamp(inp.fossil_fuel_exposure), claims,
        lambda f, c: (f / 100.0) * (c / 100.0) * 100.0,
    ))

    # 3. Controversy signal: each verified controversy flag is direct risk
    #    evidence. Unknown is NOT zero flags — zero flags is a finding that the
    #    company has no active controversies, which is a claim in its favour.
    controversy_score = (None if inp.controversy_flags is None
                         else _clamp(inp.controversy_flags * 25.0))

    # 4. Transition capex gap: claiming transition ambition without disclosing investment.
    capex_gap = _clamp(_pair(
        claims, _clamp(inp.transition_capex_disclosure), lambda c, t: c - t,
    ))

    # 5. Ownership opacity: opaque structures prevent independent verification.
    #    Was `70 - _clamp(None)` = 70, so an unmeasured company scored near the
    #    top of this component purely because nobody had looked.
    transparency = _clamp(inp.ownership_transparency)
    ownership_opacity = (None if transparency is None
                         else _clamp(70.0 - transparency))

    def _r(value):
        return None if value is None else round(value, 2)

    return {
        'claim_evidence_gap': _r(claim_evidence_gap),
        'ff_risk':            _r(ff_risk),
        'controversy_score':  _r(controversy_score),
        'capex_gap':          _r(capex_gap),
        'ownership_opacity':  _r(ownership_opacity),
    }


# ── Narrative builders ────────────────────────────────────────────────────────

def _main_red_flags(inp: GreenwashingInput, comp: dict[str, float]) -> list[str]:
    """
    Generate specific, evidence-based red flags using cautious language.
    Each flag cites the signal — not the conclusion.

    Every comparison is guarded on the value being known. A red flag is an
    accusation, and the old bare comparisons produced them from absence: with
    `_clamp(None) -> 0`, `ownership_transparency < 35` was always true, so every
    unassessed entity was flagged for 'Low ownership and governance transparency
    (indicator: 0/100)'.
    """
    flags: list[str] = []

    def _ge(value, threshold: float) -> bool:
        v = _clamp(value)
        return v is not None and v >= threshold

    def _lt(value, threshold: float) -> bool:
        v = _clamp(value)
        return v is not None and v < threshold

    if _ge(comp['claim_evidence_gap'], 40):
        flags.append(
            'Large gap between stated climate ambition and available verification evidence — '
            'may indicate claims are not fully substantiated by independent data'
        )
    elif _ge(comp['claim_evidence_gap'], 20):
        flags.append(
            'Moderate gap between climate claims and verification evidence — '
            'requires third-party assurance to confirm accuracy'
        )

    if _ge(inp.fossil_fuel_exposure, 60) and _ge(inp.climate_claims_strength, 55):
        flags.append(
            f'High fossil fuel or high-carbon exposure (indicator: {inp.fossil_fuel_exposure:.0f}/100) '
            'alongside strong green claims — transition credibility requires verification'
        )

    # Unknown flag count produces no statement in either direction: neither
    # "controversies detected" nor the implicit "none detected".
    if inp.controversy_flags is None:
        pass
    elif inp.controversy_flags >= 2:
        flags.append(
            f'{inp.controversy_flags} active controversy signal(s) detected — '
            'public-data indicators of potential misalignment between stated and actual performance'
        )
    elif inp.controversy_flags == 1:
        flags.append(
            '1 controversy signal detected — warrants review of stated sustainability commitments'
        )

    if _ge(comp['capex_gap'], 45) and _ge(inp.climate_claims_strength, 50):
        flags.append(
            'Transition capital expenditure disclosure is low relative to climate claims — '
            'investment evidence does not yet corroborate stated ambition'
        )

    if _lt(inp.third_party_assurance, 20) and _ge(inp.climate_claims_strength, 50):
        flags.append(
            'No or minimal third-party assurance identified for entities making climate claims — '
            'independent verification required'
        )

    if _lt(inp.ownership_transparency, 35):
        flags.append(
            'Low ownership and governance transparency (indicator: '
            f'{inp.ownership_transparency:.0f}/100) — opaque structures limit independent assessment'
        )

    if _lt(inp.target_quality, 25) and _ge(inp.climate_claims_strength, 50):
        flags.append(
            'Climate targets appear vague, time-unbound, or unquantified relative to the '
            'strength of claims being made — specific, measurable targets with baseline years required'
        )

    return flags


def _missing_evidence(inp: GreenwashingInput) -> list[str]:
    """Identify the most important missing verification items."""
    items: list[str] = []

    # An UNKNOWN input is itself a missing-evidence item, which is exactly what
    # this function is for — so unknown and below-threshold both list it. The
    # bare `<` would have raised TypeError on None.
    def _gap(value, threshold: float) -> bool:
        v = _clamp(value)
        return v is None or v < threshold

    if _gap(inp.verified_emissions_data, 30):
        items.append('Independently verified emissions data (Scope 1, 2, and 3)')
    if _gap(inp.third_party_assurance, 25):
        items.append('Third-party assurance, certification, or second-party opinion')
    if _gap(inp.target_quality, 30):
        items.append('Specific, time-bound, quantified climate targets with a stated baseline year')
    if _gap(inp.transition_capex_disclosure, 25):
        items.append('Disclosed capital expenditure allocated to transition activities')
    if _gap(inp.ownership_transparency, 40):
        items.append('Beneficial ownership disclosure and governance transparency')
    if _gap(inp.evidence_confidence, 50):
        items.append('Analyst-reviewed or independently verified profile data')

    return items or ['No critical evidence gaps identified based on available public data.']


def _explanation(
    inp: GreenwashingInput,
    score: float,
    risk_level: str,
    comp: dict[str, float],
) -> str:
    """
    Human-readable explanation using cautious, public-data-based language.
    """
    ev = _evidence_composite(inp)
    entity = inp.entity_type.lower()

    base = (
        f'Based on publicly available data, this {entity} shows a greenwashing risk '
        f'indicator of {score:.0f}/100 ({risk_level} level). '
    )

    if risk_level == 'low':
        return (
            base +
            'Available evidence is broadly consistent with stated climate claims. '
            'Standard due diligence applies. This assessment is based on public data only '
            'and requires ongoing monitoring as disclosures are updated.'
        )

    if risk_level == 'medium':
        return (
            base +
            f'The stated climate ambition (indicator: {inp.climate_claims_strength:.0f}/100) '
            f'is not fully supported by the available verification evidence '
            f'(composite: {ev:.0f}/100). '
            'This may indicate gaps in disclosure or areas where independent assurance '
            'has not yet been obtained. Independent verification is recommended before '
            'classifying this entity for responsible finance purposes.'
        )

    if risk_level == 'high':
        detail = []
        gap = _clamp(comp['claim_evidence_gap'])
        ff  = _clamp(comp['ff_risk'])
        if gap is not None and gap >= 30:
            detail.append(f'a significant claim-to-evidence gap ({gap:.0f} points)')
        if ff is not None and ff >= 40:
            detail.append('high fossil fuel or carbon-intensive exposure alongside green claims')
        if inp.controversy_flags is not None and inp.controversy_flags >= 1:
            detail.append(f'{inp.controversy_flags} controversy signal(s)')
        detail_str = '; '.join(detail) if detail else 'multiple indicator gaps'
        return (
            base +
            f'Elevated indicators detected, including: {detail_str}. '
            'These are public-data-based signals that may indicate material discrepancies '
            'between stated climate performance and independently verifiable evidence. '
            'Enhanced due diligence is required. Results should not be presented as '
            'confirmed findings without independent investigation.'
        )

    # severe
    return (
        base +
        f'Multiple material indicators detected across claim credibility, '
        f'verification evidence, fossil fuel exposure, and governance transparency. '
        f'Climate claims (indicator: {inp.climate_claims_strength:.0f}/100) appear materially '
        f'unsupported by verification evidence (composite: {ev:.0f}/100). '
        'This public-data-based signal may indicate significant greenwashing risk. '
        'Capital allocation decisions must not proceed without an independent, '
        'comprehensive due diligence review.'
    )


def _investor_warning(score: float, risk_level: str, entity_type: str) -> str:
    entity = entity_type.lower()
    if risk_level == 'low':
        return (
            f'Greenwashing risk indicators for this {entity} are low based on available '
            'public data. Stated climate claims appear broadly evidenced. '
            'Routine monitoring and standard disclosure review recommended.'
        )
    if risk_level == 'medium':
        return (
            f'This {entity} requires verification before reliance on its climate or '
            'transition claims for capital allocation. Gaps in third-party assurance and '
            'disclosed transition investment may indicate the stated performance is not '
            'fully supported by independent evidence. Not suitable for responsible finance '
            'labelling without further due diligence.'
        )
    if risk_level == 'high':
        return (
            f'INVESTOR CAUTION — public-data-based indicators suggest elevated greenwashing '
            f'risk for this {entity}. Stated climate claims may be materially overstated '
            'relative to independently verifiable evidence. Enhanced due diligence is '
            'required. Do not rely on self-reported sustainability metrics for capital '
            'decisions without independent verification. This is a data signal, not a '
            'confirmed finding.'
        )
    return (
        f'INVESTOR ALERT — public-data-based indicators for this {entity} suggest severe '
        'greenwashing risk. Multiple signals — including unverified claims, high fossil '
        'fuel exposure, controversy flags, and/or governance opacity — raise material '
        'questions about the credibility of stated climate performance. '
        'Capital commitment is not recommended without a comprehensive independent audit '
        'of environmental claims, governance structures, and emissions data. '
        'These are public-data signals only and do not constitute a legal finding.'
    )


def _recommended_due_diligence(
    inp: GreenwashingInput,
    risk_level: str,
    comp: dict[str, float],
) -> list[str]:
    items: list[str] = []

    # Two different predicates, deliberately.
    #
    # _gap counts UNKNOWN as a gap: "obtain X" is exactly the right advice when
    # we do not have X, and it is the one recommendation shape the unknown state
    # is allowed to produce — it asks for evidence rather than asserting a
    # finding.
    #
    # _ge does not: those items are triggered by evidence OF a risk, and an
    # unknown must not manufacture one.
    def _gap(value, threshold: float) -> bool:
        v = _clamp(value)
        return v is None or v < threshold

    def _ge(value, threshold: float) -> bool:
        v = _clamp(value)
        return v is not None and v >= threshold

    if _gap(inp.verified_emissions_data, 40):
        items.append(
            'Commission an independent GHG inventory audit (Scope 1, 2, and material Scope 3 '
            'categories) against a verifiable baseline year'
        )
    if _gap(inp.third_party_assurance, 30):
        items.append(
            'Obtain a third-party second-party opinion, CBI certification, or equivalent '
            'external assurance for all climate-related claims'
        )
    if _gap(inp.target_quality, 35):
        items.append(
            'Require publication of specific, time-bound, science-aligned targets '
            '(SBTi-validated or equivalent) with annual progress disclosure'
        )
    if _gap(inp.transition_capex_disclosure, 30):
        items.append(
            'Request a detailed transition capital expenditure breakdown — confirm '
            'investment in low-carbon assets is material and independently verifiable'
        )
    if _ge(inp.fossil_fuel_exposure, 55):
        items.append(
            'Conduct a credible transition pathway assessment — verify any phase-out '
            'commitments are time-bound and backed by disclosed investment plans'
        )
    if inp.controversy_flags is not None and inp.controversy_flags >= 1:
        items.append(
            'Review all active controversies and enforcement actions — confirm that '
            'stated sustainability performance has not been subject to regulatory findings '
            'or material misrepresentation'
        )
    if _gap(inp.ownership_transparency, 40):
        items.append(
            'Verify beneficial ownership structure in a well-regulated jurisdiction — '
            'opaque structures limit the reliability of externally reported figures'
        )
    if risk_level in ('high', 'severe'):
        items.append(
            'Engage an independent ESG data provider to cross-check self-reported metrics '
            'against satellite, regulatory, and third-party environmental data sources'
        )

    if not items:
        items = [
            'Maintain regular monitoring of climate disclosures and annual report updates.',
            'Confirm third-party assurance is current at each reporting date.',
        ]
    return items


# ── Main assessment function ──────────────────────────────────────────────────

def _not_assessable(inp: GreenwashingInput) -> GreenwashingAssessment:
    """
    The output for "we cannot assess this", as distinct from either verdict.

    greenwashing_risk_score is None rather than 0. A 0 here would be read as the
    best possible result — the strongest positive claim this module can make —
    about a company nobody has examined.
    """
    return GreenwashingAssessment(
        greenwashing_risk_score = None,
        risk_level              = RISK_INSUFFICIENT_EVIDENCE,
        main_red_flags          = [],
        missing_evidence        = _missing_evidence(inp),
        explanation             = (
            'EcoIQ does not hold enough public evidence to assess greenwashing risk '
            'for this entity. This is a statement about the available data, not about '
            'the entity: it is neither an indication of greenwashing nor an indication '
            'that the entity is free of it.'
        ),
        investor_warning        = (
            'No greenwashing risk assessment is available. Absence of an assessment '
            'must not be treated as a favourable finding. Independent due diligence '
            'is required before any capital decision.'
        ),
        recommended_due_diligence = [
            'Obtain the entity\'s published climate claims and targets.',
            'Obtain independently verified emissions data (Scope 1, 2 and 3).',
            'Obtain third-party assurance or a second-party opinion.',
        ],
        confidence_note = (
            'No greenwashing risk assessment was produced because the required public '
            'evidence is not available to EcoIQ. This is not a legal finding, a '
            'regulatory determination, or a statement of fact about any entity.'
        ),
    )


def assess_greenwashing_risk(inp: GreenwashingInput) -> GreenwashingAssessment:
    """
    Core Greenwashing Risk assessment.

    Formula:
        greenwashing_risk_score =
            claim_evidence_gap  × 0.40   (primary signal)
          + ff_risk              × 0.25   (sector amplifier)
          + controversy_score    × 0.20   (direct evidence of past misalignment)
          + capex_gap            × 0.10   (investment vs. ambition gap)
          + ownership_opacity    × 0.05   (verification barrier)

    All components are 0–100. Final score is 0–100.
    Risk levels: low < 30, medium 30–49, high 50–69, severe ≥ 70.

    Cautious language is mandatory in all output fields.
    """
    comp = _score_components(inp)

    # Gate BEFORE scoring. The primary signal is the claim-to-evidence gap, and
    # without a claim or without any evidence channel there is no gap to
    # measure — only arithmetic on absences. Re-normalising the remaining
    # components would produce a confident-looking number from the two weakest
    # signals, so this refuses instead.
    claims_known   = _clamp(inp.climate_claims_strength) is not None
    evidence_known = any(
        _clamp(getattr(inp, channel)) is not None for channel in _EVIDENCE_CHANNELS
    )
    if not (claims_known and evidence_known):
        return _not_assessable(inp)

    raw_score = _clamp(weighted_mean_of_known(
        (comp['claim_evidence_gap'],  0.40),
        (comp['ff_risk'],             0.25),
        (comp['controversy_score'],   0.20),
        (comp['capex_gap'],           0.10),
        (comp['ownership_opacity'],   0.05),
    ))
    if raw_score is None:
        return _not_assessable(inp)

    risk_level = _risk_level(raw_score)
    flags      = _main_red_flags(inp, comp)
    missing    = _missing_evidence(inp)

    return GreenwashingAssessment(
        greenwashing_risk_score   = round(raw_score, 2),
        risk_level                = risk_level,
        main_red_flags            = flags,
        missing_evidence          = missing,
        explanation               = _explanation(inp, raw_score, risk_level, comp),
        investor_warning          = _investor_warning(raw_score, risk_level, inp.entity_type),
        recommended_due_diligence = _recommended_due_diligence(inp, risk_level, comp),
        confidence_note           = (
            'This greenwashing risk assessment is based on publicly available data and '
            'EcoIQ profile indicators only. It is not a legal finding, regulatory determination, '
            'or confirmed statement of fact about any entity. All signals are indicative and '
            'require independent professional verification before use in capital decisions.'
        ),
    )


# ── Profile-level helper (used by ml/ethics/ethical_score.py) ─────────────────

def greenwashing_from_profile(profile: 'CompanyProfile') -> GreenwashingAssessment:
    """
    Derive GreenwashingInput from an EcoIQ CompanyProfile and run assessment.

    Input derivation:
      climate_claims_strength      ← energy_transition_score × 0.55 + future_readiness_score × 0.45
      verified_emissions_data      ← is_verified ? 90 : audit_quality_score × 0.35
      third_party_assurance        ← is_verified ? 85 : audit_quality_score × 0.30
      transition_capex_disclosure  ← energy_transition_score × 0.55 + infrastructure_upgrade_score × 0.45
      fossil_fuel_exposure         ← _POLLUTION_TO_FF[pollution_level], discounted by energy_transition
      target_quality               ← future_readiness_score
      evidence_confidence          ← verified=92 / public=55 / other=35
      controversy_flags            ← controversy_risk_score: <40→0, 40–59→1, 60–79→2, ≥80→3
      ownership_transparency       ← mean(transparency_anti_corruption, procurement_transparency)
    """
    # Was `_clamp(float(getattr(profile, attr, 0) or 0))` — a missing attribute
    # AND an unmeasured score AND a genuine 0.0 all collapsed into 0.
    def _f(attr: str):
        return _clamp(getattr(profile, attr, None))

    def _r(value):
        return None if value is None else round(value, 2)

    is_verified = bool(getattr(profile, 'is_verified', False))
    status      = str(getattr(profile, 'status', 'public') or 'public')

    energy_tr   = _f('energy_transition_score')
    future_r    = _f('future_readiness_score')
    audit_q     = _f('audit_quality_score')
    infra_u     = _f('infrastructure_upgrade_score')
    controversy = _f('controversy_risk_score')

    # Climate claims: how actively the company is projecting a green/transition
    # identity. Re-normalised across the known half rather than treating an
    # unknown half as zero ambition.
    climate_claims = _clamp(weighted_mean_of_known((energy_tr, 0.55), (future_r, 0.45)))

    # Verified data: conservative — unverified audit scores only partially count.
    # An unknown audit score is NOT zero assurance: zero assurance is a finding.
    verified_data = 90.0 if is_verified else _clamp(
        None if audit_q is None else audit_q * 0.35)
    third_party   = 85.0 if is_verified else _clamp(
        None if audit_q is None else audit_q * 0.30)

    # Transition capex: investment signals
    transition_capex = _clamp(weighted_mean_of_known((energy_tr, 0.55), (infra_u, 0.45)))

    # Fossil fuel exposure: pollution level as proxy, discounted by active
    # transition. `or 'medium'` substituted a real classification for a missing
    # one; an unrecognised level now yields no exposure figure at all.
    raw_level       = getattr(profile, 'pollution_level', None)
    pollution_level = raw_level.lower() if raw_level else None
    ff_base         = _POLLUTION_TO_FF.get(pollution_level)
    discount        = 0.0 if energy_tr is None else energy_tr / 250.0
    ff_exposure     = _clamp(None if ff_base is None else ff_base * (1.0 - discount))

    # Target quality: future readiness as proxy for target specificity
    target_q = future_r

    # Evidence confidence tier → 0-100 numeric
    if is_verified:
        ev_conf = 92.0
    elif status == 'public':
        ev_conf = 55.0
    else:
        ev_conf = 35.0

    # Controversy count. Unknown is None, not 0 — a count of 0 is the finding
    # "no active controversies", which is a statement in the company's favour.
    if controversy is None:
        controversy_flags = None
    elif controversy >= 80:
        controversy_flags = 3
    elif controversy >= 60:
        controversy_flags = 2
    elif controversy >= 40:
        controversy_flags = 1
    else:
        controversy_flags = 0

    # Ownership transparency
    ownership_transp = _clamp(mean_of_known(
        _f('transparency_anti_corruption_score'),
        _f('procurement_transparency_score'),
    ))

    inp = GreenwashingInput(
        climate_claims_strength     = _r(climate_claims),
        verified_emissions_data     = _r(verified_data),
        third_party_assurance       = _r(third_party),
        transition_capex_disclosure = _r(transition_capex),
        fossil_fuel_exposure        = _r(ff_exposure),
        target_quality              = _r(target_q),
        evidence_confidence         = _r(ev_conf),
        controversy_flags           = controversy_flags,
        ownership_transparency      = _r(ownership_transp),
        entity_type                 = 'company',
    )
    return assess_greenwashing_risk(inp)
