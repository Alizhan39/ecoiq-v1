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


# ── Risk level tiers ──────────────────────────────────────────────────────────

RISK_LEVELS: list[tuple[float, str]] = [
    (70.0, 'severe'),
    (50.0, 'high'),
    (30.0, 'medium'),
    (0.0,  'low'),
]

# ── Pollution level → fossil fuel exposure proxy ──────────────────────────────

_POLLUTION_TO_FF: dict[str, float] = {
    'low':    10.0,
    'medium': 35.0,
    'high':   65.0,
    'severe': 85.0,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v or 0)))


def _risk_level(score: float) -> str:
    for threshold, label in RISK_LEVELS:
        if score >= threshold:
            return label
    return 'low'


# ── Input dataclass ───────────────────────────────────────────────────────────

@dataclass
class GreenwashingInput:
    """
    Structured inputs for the Greenwashing Risk Detector.

    All float fields are normalised to 0–100.
    controversy_flags is an integer count (0, 1, 2, 3 …).
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
    greenwashing_risk_score:    float       # 0-100 (higher = more risk indicators)
    risk_level:                 str         # 'low' | 'medium' | 'high' | 'severe'
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
    return _clamp(
        inp.verified_emissions_data  * 0.30
        + inp.third_party_assurance  * 0.30
        + inp.target_quality         * 0.25
        + inp.evidence_confidence    * 0.15
    )


def _score_components(inp: GreenwashingInput) -> dict[str, float]:
    """
    Compute each risk component as a 0–100 score.
    Higher component score = more risk signal for that factor.
    """
    ev_composite = _evidence_composite(inp)

    # 1. Claim-to-evidence gap: the primary greenwashing signal.
    #    High claims with low evidence = high gap risk.
    claim_evidence_gap = _clamp(inp.climate_claims_strength - ev_composite)

    # 2. Fossil fuel amplifier: high FF exposure combined with high green claims.
    #    A coal company claiming carbon neutrality is the extreme case.
    ff_risk = _clamp(
        (inp.fossil_fuel_exposure / 100.0) * (inp.climate_claims_strength / 100.0) * 100.0
    )

    # 3. Controversy signal: each verified controversy flag is direct risk evidence.
    controversy_score = _clamp(inp.controversy_flags * 25.0)

    # 4. Transition capex gap: claiming transition ambition without disclosing investment.
    capex_gap = _clamp(inp.climate_claims_strength - inp.transition_capex_disclosure)

    # 5. Ownership opacity: opaque structures prevent independent verification.
    ownership_opacity = _clamp(70.0 - inp.ownership_transparency)

    return {
        'claim_evidence_gap': round(claim_evidence_gap, 2),
        'ff_risk':            round(ff_risk,            2),
        'controversy_score':  round(controversy_score,  2),
        'capex_gap':          round(capex_gap,          2),
        'ownership_opacity':  round(ownership_opacity,  2),
    }


# ── Narrative builders ────────────────────────────────────────────────────────

def _main_red_flags(inp: GreenwashingInput, comp: dict[str, float]) -> list[str]:
    """
    Generate specific, evidence-based red flags using cautious language.
    Each flag cites the signal — not the conclusion.
    """
    flags: list[str] = []

    if comp['claim_evidence_gap'] >= 40:
        flags.append(
            'Large gap between stated climate ambition and available verification evidence — '
            'may indicate claims are not fully substantiated by independent data'
        )
    elif comp['claim_evidence_gap'] >= 20:
        flags.append(
            'Moderate gap between climate claims and verification evidence — '
            'requires third-party assurance to confirm accuracy'
        )

    if inp.fossil_fuel_exposure >= 60 and inp.climate_claims_strength >= 55:
        flags.append(
            f'High fossil fuel or high-carbon exposure (indicator: {inp.fossil_fuel_exposure:.0f}/100) '
            'alongside strong green claims — transition credibility requires verification'
        )

    if inp.controversy_flags >= 2:
        flags.append(
            f'{inp.controversy_flags} active controversy signal(s) detected — '
            'public-data indicators of potential misalignment between stated and actual performance'
        )
    elif inp.controversy_flags == 1:
        flags.append(
            '1 controversy signal detected — warrants review of stated sustainability commitments'
        )

    if comp['capex_gap'] >= 45 and inp.climate_claims_strength >= 50:
        flags.append(
            'Transition capital expenditure disclosure is low relative to climate claims — '
            'investment evidence does not yet corroborate stated ambition'
        )

    if inp.third_party_assurance < 20 and inp.climate_claims_strength >= 50:
        flags.append(
            'No or minimal third-party assurance identified for entities making climate claims — '
            'independent verification required'
        )

    if inp.ownership_transparency < 35:
        flags.append(
            'Low ownership and governance transparency (indicator: '
            f'{inp.ownership_transparency:.0f}/100) — opaque structures limit independent assessment'
        )

    if inp.target_quality < 25 and inp.climate_claims_strength >= 50:
        flags.append(
            'Climate targets appear vague, time-unbound, or unquantified relative to the '
            'strength of claims being made — specific, measurable targets with baseline years required'
        )

    return flags


def _missing_evidence(inp: GreenwashingInput) -> list[str]:
    """Identify the most important missing verification items."""
    items: list[str] = []

    if inp.verified_emissions_data < 30:
        items.append('Independently verified emissions data (Scope 1, 2, and 3)')
    if inp.third_party_assurance < 25:
        items.append('Third-party assurance, certification, or second-party opinion')
    if inp.target_quality < 30:
        items.append('Specific, time-bound, quantified climate targets with a stated baseline year')
    if inp.transition_capex_disclosure < 25:
        items.append('Disclosed capital expenditure allocated to transition activities')
    if inp.ownership_transparency < 40:
        items.append('Beneficial ownership disclosure and governance transparency')
    if inp.evidence_confidence < 50:
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
        if comp['claim_evidence_gap'] >= 30:
            detail.append(
                f'a significant claim-to-evidence gap ({comp["claim_evidence_gap"]:.0f} points)'
            )
        if comp['ff_risk'] >= 40:
            detail.append('high fossil fuel or carbon-intensive exposure alongside green claims')
        if inp.controversy_flags >= 1:
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

    if inp.verified_emissions_data < 40:
        items.append(
            'Commission an independent GHG inventory audit (Scope 1, 2, and material Scope 3 '
            'categories) against a verifiable baseline year'
        )
    if inp.third_party_assurance < 30:
        items.append(
            'Obtain a third-party second-party opinion, CBI certification, or equivalent '
            'external assurance for all climate-related claims'
        )
    if inp.target_quality < 35:
        items.append(
            'Require publication of specific, time-bound, science-aligned targets '
            '(SBTi-validated or equivalent) with annual progress disclosure'
        )
    if inp.transition_capex_disclosure < 30:
        items.append(
            'Request a detailed transition capital expenditure breakdown — confirm '
            'investment in low-carbon assets is material and independently verifiable'
        )
    if inp.fossil_fuel_exposure >= 55:
        items.append(
            'Conduct a credible transition pathway assessment — verify any phase-out '
            'commitments are time-bound and backed by disclosed investment plans'
        )
    if inp.controversy_flags >= 1:
        items.append(
            'Review all active controversies and enforcement actions — confirm that '
            'stated sustainability performance has not been subject to regulatory findings '
            'or material misrepresentation'
        )
    if inp.ownership_transparency < 40:
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
    comp  = _score_components(inp)

    raw_score = _clamp(
        comp['claim_evidence_gap'] * 0.40
        + comp['ff_risk']          * 0.25
        + comp['controversy_score'] * 0.20
        + comp['capex_gap']        * 0.10
        + comp['ownership_opacity'] * 0.05
    )

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
    def _f(attr: str) -> float:
        return _clamp(float(getattr(profile, attr, 0) or 0))

    is_verified = bool(getattr(profile, 'is_verified', False))
    status      = str(getattr(profile, 'status', 'public') or 'public')

    energy_tr   = _f('energy_transition_score')
    future_r    = _f('future_readiness_score')
    audit_q     = _f('audit_quality_score')
    infra_u     = _f('infrastructure_upgrade_score')
    controversy = _f('controversy_risk_score')

    # Climate claims: how actively the company is projecting a green/transition identity
    climate_claims = _clamp(energy_tr * 0.55 + future_r * 0.45)

    # Verified data: conservative — unverified audit scores only partially count
    verified_data  = 90.0 if is_verified else _clamp(audit_q * 0.35)
    third_party    = 85.0 if is_verified else _clamp(audit_q * 0.30)

    # Transition capex: investment signals
    transition_capex = _clamp(energy_tr * 0.55 + infra_u * 0.45)

    # Fossil fuel exposure: pollution level as proxy, discounted by active transition
    pollution_level = (getattr(profile, 'pollution_level', 'medium') or 'medium').lower()
    ff_base         = _POLLUTION_TO_FF.get(pollution_level, 35.0)
    # Active energy transition partially mitigates FF exposure signal
    ff_exposure     = _clamp(ff_base * (1.0 - energy_tr / 250.0))

    # Target quality: future readiness as proxy for target specificity
    target_q = future_r

    # Evidence confidence tier → 0-100 numeric
    if is_verified:
        ev_conf = 92.0
    elif status == 'public':
        ev_conf = 55.0
    else:
        ev_conf = 35.0

    # Controversy count
    if controversy >= 80:
        controversy_flags = 3
    elif controversy >= 60:
        controversy_flags = 2
    elif controversy >= 40:
        controversy_flags = 1
    else:
        controversy_flags = 0

    # Ownership transparency
    t_anti  = _f('transparency_anti_corruption_score')
    procure = _f('procurement_transparency_score')
    ownership_transp = _clamp((t_anti + procure) / 2.0)

    inp = GreenwashingInput(
        climate_claims_strength     = round(climate_claims, 2),
        verified_emissions_data     = round(verified_data,  2),
        third_party_assurance       = round(third_party,    2),
        transition_capex_disclosure = round(transition_capex, 2),
        fossil_fuel_exposure        = round(ff_exposure,    2),
        target_quality              = round(target_q,       2),
        evidence_confidence         = round(ev_conf,        2),
        controversy_flags           = controversy_flags,
        ownership_transparency      = round(ownership_transp, 2),
        entity_type                 = 'company',
    )
    return assess_greenwashing_risk(inp)
