"""
ml/ethics/capital_integrity.py — EcoIQ Capital Integrity Score.

Evaluates a financing instrument, project, or transaction across seven
dimensions to determine whether climate or transition capital is likely
to create real public benefit — or whether it is structured to extract
value, generate reputational optics, or obscure a weak underlying project.

Seven dimensions (weights):
  1. Use of Proceeds Clarity          (0.20)
  2. Public Benefit Potential         (0.20)
  3. Greenwashing Risk                (0.20) ← inverted: high score = low risk
  4. Ownership & Procurement Transp.  (0.15)
  5. Community & Social Impact        (0.10)
  6. Measurable Emissions/Resilience  (0.10)
  7. Ethical Finance Compatibility    (0.05)

Label tiers:
  high-integrity  ≥ 80
  strong          ≥ 65
  moderate        ≥ 45
  weak            < 45

ML integration note:
  Replace score_capital_integrity() with:
      from joblib import load
      clf = load('ml/models/capital_integrity_clf.joblib')
      fv  = capital_integrity_feature_vector(inp)
      scores = clf.predict([list(fv.values())])[0]  # 7 dimension scores
  once training data (historical green bond outcomes, greenwashing cases,
  CBI certification data) is available.

Public-facing language: transparent, beneficial, evidence-based, responsible.
Internal CIS ↔ ethical framework mapping: docs/capital-integrity-score.md
Do NOT expose principle-level names (Maqasid etc.) in any output field.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# ── Dimension weights (must sum to 1.0) ───────────────────────────────────────

CIS_DIMENSION_WEIGHTS: dict[str, float] = {
    'proceeds_clarity':       0.20,
    'public_benefit':         0.20,
    'greenwashing_risk':      0.20,   # inverted: high score = low risk
    'ownership_transparency': 0.15,
    'community_impact':       0.10,
    'measurable_impact':      0.10,
    'ethical_compatibility':  0.05,
}

# ── Label tiers ───────────────────────────────────────────────────────────────

CIS_LABELS: list[tuple[float, str]] = [
    (80.0, 'high-integrity'),
    (65.0, 'strong'),
    (45.0, 'moderate'),
    (0.0,  'weak'),
]

# ── Lookup tables ─────────────────────────────────────────────────────────────

# Instrument type → base proceeds-clarity score
# Asset-backed or project-specific instruments start higher.
_INSTRUMENT_CLARITY_BASE: dict[str, float] = {
    'green_bond':               72.0,
    'sustainability_bond':      68.0,
    'sustainability_linked_loan': 55.0,
    'transition_bond':          58.0,
    'sukuk':                    75.0,    # inherently asset-backed by structure
    'blended_finance':          62.0,
    'project_finance':          78.0,
    'social_bond':              65.0,
    'other':                    45.0,
    '':                         40.0,
}

# Specificity declaration → clarity modifier
_SPECIFICITY_MODIFIER: dict[str, float] = {
    'specific':  20.0,
    'general':    0.0,
    'vague':    -25.0,
    'none':     -40.0,
    '':         -20.0,
}

# Sector → public benefit potential base (0-100)
_SECTOR_BENEFIT_BASE: dict[str, float] = {
    'renewables':      90.0,
    'energy':          70.0,   # depends heavily on renewable mix
    'infrastructure':  75.0,
    'transport':       62.0,
    'agriculture':     60.0,
    'water':           82.0,
    'health':          85.0,
    'education':       80.0,
    'housing':         72.0,
    'nature':          88.0,
    'forestry':        85.0,
    'biodiversity':    87.0,
    'waste':           65.0,
    'technology':      55.0,
    'finance':         50.0,
    'mining':          35.0,
    'metallurgy':      38.0,
    'chemical':        32.0,
    'oil_gas':         15.0,
    'coal':             5.0,
    'other':           45.0,
    '':                40.0,
}

# Procurement framework → ownership/transparency base score
_PROCUREMENT_BASE: dict[str, float] = {
    'IFC':         88.0,
    'EBRD':        88.0,
    'ADB':         83.0,
    'World Bank':  83.0,
    'EU Taxonomy': 80.0,
    'GBP':         75.0,    # Green Bond Principles
    'ICMA':        75.0,
    'national':    52.0,
    'none':        22.0,
    '':            22.0,
}

# Community consultation level → community impact base
_CONSULTATION_BASE: dict[str, float] = {
    'fpic_aligned': 88.0,   # Free, Prior and Informed Consent-aligned
    'standard':     55.0,
    'minimal':      28.0,
    'none':         10.0,
    '':             25.0,
}

# Issuer track record → credibility modifier applied to greenwashing risk
_TRACK_RECORD_MODIFIER: dict[str, float] = {
    'strong':   12.0,
    'moderate':  0.0,
    'weak':    -20.0,
    'unknown':  -8.0,
    '':         -5.0,
}

# Sector high-greenwash-risk list (label-substance mismatch risk)
_HIGH_GREENWASH_SECTORS = frozenset({
    'oil_gas', 'coal', 'mining', 'chemical', 'metallurgy',
})

# Instrument types that carry a label-mismatch risk if misapplied
_LABEL_MISMATCH_RISK_INSTRUMENTS = frozenset({
    'green_bond', 'sustainability_bond', 'sustainability_linked_loan',
    'transition_bond', 'sukuk',
})

# Sectors excluded by major ethical/responsible finance frameworks
_EXCLUDED_SECTORS = frozenset({
    'tobacco', 'weapons', 'arms', 'gambling', 'adult_entertainment',
    'coal',           # absolute exclusion in most frameworks
})


# ── Helper ────────────────────────────────────────────────────────────────────

def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v or 0)))


def _cis_label(score: float) -> str:
    for threshold, label in CIS_LABELS:
        if score >= threshold:
            return label
    return 'weak'


# ── Input dataclass ───────────────────────────────────────────────────────────

@dataclass
class CapitalIntegrityInput:
    """
    Structured input for Capital Integrity scoring.

    Required: instrument_type, sector
    All other fields are optional with conservative defaults.
    """
    # Instrument identity
    name:             str = 'Unnamed Instrument'
    instrument_type:  str = 'other'       # green_bond | sustainability_linked_loan | transition_bond | sukuk | blended_finance | project_finance | other
    sector:           str = 'other'
    country:          str = ''

    # Proceeds
    use_of_proceeds_specificity: str = 'general'   # specific | general | vague | none
    proceeds_amount_usd: Optional[float] = None

    # Third-party oversight
    third_party_verified:       bool = False   # CBI / second-party opinion / external certification
    reporting_commitment:       str  = 'none'  # annual | bi-annual | none

    # Community
    community_consultation:     str  = 'none'  # fpic_aligned | standard | minimal | none
    gender_inclusion:           bool = False
    local_employment_commitment: bool = False

    # Ownership and procurement
    ownership_disclosed:        bool = False   # beneficial ownership published
    procurement_framework:      str  = 'none'  # IFC | EBRD | ADB | GBP | national | none

    # Quantified impact
    emission_reduction_target:  bool = False   # specific, time-bound target
    impact_measurement_plan:    bool = False   # independent verification plan
    baseline_data_available:    bool = False   # quantified baselines provided
    independent_verification_plan: bool = False

    # Additionality
    additionality_demonstrated: bool = False   # capital would not flow otherwise

    # Integrity flags
    label_matches_project:      bool = True    # is the instrument label consistent with the project?
    sector_excluded:            bool = False   # excluded by major ethical finance frameworks
    issuer_track_record:        str  = 'unknown'  # strong | moderate | weak | unknown

    # Optional: link to existing EcoIQ company profile (slug)
    existing_ecoiq_profile:     str  = ''

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'CapitalIntegrityInput':
        valid = {f for f in cls.__dataclass_fields__}   # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in valid})


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class CapitalIntegrityResult:
    """
    Full Capital Integrity Score output — seven dimension scores plus
    aggregate label, red flags, positive indicators, and narrative fields.

    Fully serialisable via .to_dict().
    All dimension_scores values are in range 0 – 100.
    """
    capital_integrity_score: float
    label:                   str       # 'high-integrity' | 'strong' | 'moderate' | 'weak'

    dimension_scores: dict[str, float]   # all 7 raw dimension scores

    red_flags:          list[str]
    positive_indicators: list[str]

    investor_note:           str
    islamic_finance_note:    str
    due_diligence_required:  list[str]
    recommended_next_actions: list[str]

    confidence:  str   = 'model-estimate'
    methodology: str   = field(default='EcoIQ Capital Integrity Score v1 — rule-based; ML integration pending')

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Feature vector (ML-ready) ─────────────────────────────────────────────────

def capital_integrity_feature_vector(inp: CapitalIntegrityInput) -> dict[str, float]:
    """
    Pre-compute a normalised feature vector for scikit-learn integration.

    All features are floats in range [0.0, 100.0].
    Feed directly into StandardScaler → RandomForest / GradientBoosting.

    # ML-HOOK: replace rule-based dimension formulas with:
    #   from joblib import load
    #   clf = load('ml/models/capital_integrity_clf.joblib')
    #   fv  = capital_integrity_feature_vector(inp)
    #   scores = clf.predict([list(fv.values())])[0]  # 7 dimension scores
    """
    sector_lower = inp.sector.lower()
    instr_lower  = inp.instrument_type.lower()

    return {
        # Proceeds clarity signals
        'instrument_clarity_base':   _INSTRUMENT_CLARITY_BASE.get(instr_lower, 40.0),
        'specificity_modifier':      _SPECIFICITY_MODIFIER.get(inp.use_of_proceeds_specificity, -20.0) + 50.0,  # centre on 50
        'has_reporting_commitment':  100.0 if inp.reporting_commitment in ('annual', 'bi-annual') else 0.0,
        'third_party_verified':      100.0 if inp.third_party_verified else 0.0,

        # Public benefit signals
        'sector_benefit_base':       _SECTOR_BENEFIT_BASE.get(sector_lower, 40.0),
        'additionality':             100.0 if inp.additionality_demonstrated else 0.0,
        'proceeds_log':              math.log10(max(inp.proceeds_amount_usd or 1.0, 1.0)),

        # Greenwashing risk signals (lower = more risk)
        'is_high_greenwash_sector':  100.0 if sector_lower in _HIGH_GREENWASH_SECTORS else 0.0,
        'label_matches_project':     100.0 if inp.label_matches_project else 0.0,
        'track_record_modifier':     _TRACK_RECORD_MODIFIER.get(inp.issuer_track_record, -5.0) + 50.0,  # centre on 50
        'has_baseline_data':         100.0 if inp.baseline_data_available else 0.0,
        'has_independent_verif':     100.0 if inp.independent_verification_plan else 0.0,

        # Ownership transparency signals
        'ownership_disclosed':       100.0 if inp.ownership_disclosed else 0.0,
        'procurement_base':          _PROCUREMENT_BASE.get(inp.procurement_framework, 22.0),

        # Community signals
        'consultation_base':         _CONSULTATION_BASE.get(inp.community_consultation, 25.0),
        'gender_inclusion':          100.0 if inp.gender_inclusion else 0.0,
        'local_employment':          100.0 if inp.local_employment_commitment else 0.0,

        # Measurable impact signals
        'has_emission_target':       100.0 if inp.emission_reduction_target else 0.0,
        'has_impact_plan':           100.0 if inp.impact_measurement_plan else 0.0,

        # Ethical compatibility signals
        'sector_excluded':           100.0 if inp.sector_excluded else 0.0,
    }


# ── Narrative builders ────────────────────────────────────────────────────────

def _ci_investor_note(score: float, label: str, red_flags: list[str]) -> str:
    top = '; '.join(red_flags[:2])
    suffix = f' Key concerns: {top}.' if top else ''
    if score >= 80:
        return (
            'This instrument demonstrates high integrity across all seven Capital Integrity '
            'dimensions. Proceeds clarity, public benefit potential, and greenwashing risk '
            f'are all within responsible finance thresholds. Subject to independent verification, '
            f'suitable for responsible capital labelling.{suffix}'
        )
    if score >= 65:
        return (
            'Strong Capital Integrity profile with minor gaps. The instrument meets the '
            'threshold for responsible finance consideration. Conditions or remediation '
            f'may apply before full labelling is awarded.{suffix}'
        )
    if score >= 45:
        return (
            'Moderate Capital Integrity. The instrument has partial alignment with responsible '
            'finance standards. Specific remediation — particularly in proceeds clarity, '
            f'verification, and impact measurement — is required before eligibility.{suffix}'
        )
    return (
        'Weak Capital Integrity profile. Material failures identified across multiple '
        'dimensions. This instrument is not suitable for responsible finance labelling '
        f'without fundamental restructuring.{suffix}'
    )


def _ci_ethical_finance_note(
    score: float,
    label: str,
    proceeds_clarity: float,
    public_benefit: float,
    greenwashing_risk: float,
    ownership_transparency: float,
    red_flags: list[str],
) -> str:
    """
    Professional compatibility note for ethical and responsible finance institutions.
    Uses principle-based language only.
    Do NOT expose religious terminology — see docs/capital-integrity-score.md (internal).
    """
    weak_dims = [
        name for name, s in [
            ('proceeds clarity', proceeds_clarity),
            ('public benefit', public_benefit),
            ('greenwashing controls', greenwashing_risk),
            ('ownership transparency', ownership_transparency),
        ]
        if s < 50
    ]

    if score >= 75 and not weak_dims:
        return (
            "EcoIQ's Capital Integrity Score evaluates whether climate capital is transparent, "
            'beneficial, and free from greenwashing — criteria that align with the foundational '
            'requirements of ethical and responsible finance, including Shariah-compatible '
            'investment screening. This instrument demonstrates strong alignment: proceeds are '
            'clearly specified, public benefit is credible and traceable, and ownership structures '
            'meet transparency standards. Subject to formal review, this instrument is structurally '
            'compatible with responsible finance frameworks.'
        )
    if score >= 45:
        gaps = ', '.join(weak_dims) if weak_dims else 'specific dimensions'
        return (
            'Partial alignment with ethical and responsible finance principles. '
            f'Improvement in {gaps} is required before this instrument can be considered '
            'fully compatible with responsible capital frameworks. Engagement-based '
            'financing with structured improvement conditions may be appropriate.'
        )
    return (
        'This instrument does not currently meet the threshold for ethical finance '
        'compatibility. Material deficiencies in proceeds transparency, public benefit '
        'credibility, or greenwashing controls prevent responsible finance labelling. '
        'Fundamental restructuring of the instrument terms is recommended.'
    )


def _ci_red_flags(inp: CapitalIntegrityInput, dim: dict[str, float]) -> list[str]:
    flags: list[str] = []

    # Automatic red flags per docs/capital-integrity-score.md
    if inp.use_of_proceeds_specificity in ('none', 'vague'):
        flags.append('No use-of-proceeds specificity — "general purposes" label is insufficient for responsible finance')

    if not inp.third_party_verified and inp.instrument_type in _LABEL_MISMATCH_RISK_INSTRUMENTS:
        flags.append('No third-party verification for a labelled instrument (green/sustainable/sukuk)')

    if inp.sector.lower() in ('oil_gas', 'coal') and not inp.additionality_demonstrated:
        flags.append('High-carbon sector — transition label requires a credible phase-out commitment')

    if not inp.ownership_disclosed:
        flags.append('Beneficial ownership not disclosed')

    if not inp.impact_measurement_plan and not inp.emission_reduction_target:
        flags.append('No impact measurement plan or emission reduction target declared')

    if not inp.label_matches_project:
        flags.append('Instrument label does not match the underlying project type — label-substance mismatch')

    if inp.sector_excluded:
        flags.append('Sector is excluded by major ethical and responsible finance frameworks')

    # Score-derived flags
    if dim['proceeds_clarity'] < 40:
        flags.append('Proceeds clarity score below minimum threshold')
    if dim['greenwashing_risk'] < 40:
        flags.append('Elevated greenwashing risk — independent verification urgently required')
    if dim['ownership_transparency'] < 35:
        flags.append('Ownership and procurement transparency deficit')

    return flags


def _ci_positive_indicators(inp: CapitalIntegrityInput, dim: dict[str, float]) -> list[str]:
    indicators: list[str] = []

    if inp.third_party_verified:
        indicators.append('Third-party verified — CBI certification or equivalent second-party opinion')
    if inp.emission_reduction_target and inp.baseline_data_available:
        indicators.append('Specific emission reduction target with quantified baselines')
    if inp.community_consultation in ('fpic_aligned',):
        indicators.append('FPIC-aligned community consultation documented')
    if inp.procurement_framework in ('IFC', 'EBRD', 'ADB', 'World Bank'):
        indicators.append(f'{inp.procurement_framework} procurement framework applied')
    if inp.independent_verification_plan:
        indicators.append('Independent impact verification plan in place')
    if inp.ownership_disclosed:
        indicators.append('Beneficial ownership disclosed in a well-regulated jurisdiction')
    if inp.additionality_demonstrated:
        indicators.append('Additionality clearly demonstrated')
    if inp.gender_inclusion and inp.local_employment_commitment:
        indicators.append('Gender inclusion and local employment commitments in place')
    if inp.reporting_commitment == 'annual':
        indicators.append('Annual independent impact reporting committed')
    if inp.issuer_track_record == 'strong':
        indicators.append('Issuer has a strong track record on previous sustainability commitments')

    return indicators


def _ci_due_diligence(
    inp: CapitalIntegrityInput,
    red_flags: list[str],
    dim: dict[str, float],
) -> list[str]:
    items: list[str] = []

    if not inp.third_party_verified:
        items.append('Commission an independent second-party opinion or CBI certification')
    if dim['proceeds_clarity'] < 60:
        items.append('Request a detailed use-of-proceeds framework with project-level breakdown')
    if not inp.ownership_disclosed:
        items.append('Verify beneficial ownership structure — UBO registry or legal disclosure required')
    if not inp.impact_measurement_plan:
        items.append('Require a quantified impact measurement and reporting plan before drawdown')
    if not inp.baseline_data_available:
        items.append('Establish baseline emissions or resilience data for impact attribution')
    if inp.sector.lower() in _HIGH_GREENWASH_SECTORS:
        items.append('Conduct sector-specific greenwashing assessment — label-substance alignment required')
    if inp.procurement_framework in ('none', ''):
        items.append('Apply a recognised procurement framework (IFC, EBRD, or national standards)')
    if inp.community_consultation in ('none', 'minimal'):
        items.append('Conduct community consultation with grievance and remedy mechanisms')
    if inp.issuer_track_record in ('weak', 'unknown'):
        items.append("Review issuer's previous green/sustainability commitments and delivery record")

    if not items:
        items = [
            'Standard due diligence applies — confirm third-party verification is current',
            'Annual impact report review required at each reporting date',
        ]
    return items


def _ci_recommended_actions(dim: dict[str, float], inp: CapitalIntegrityInput) -> list[str]:
    _map = {
        'proceeds_clarity': (
            'Strengthen the use-of-proceeds framework: add project-level specificity, '
            'a defined exclusion list, and a contractual ring-fence for capital deployment.'
        ),
        'public_benefit': (
            'Document additionality — demonstrate that the capital enables a project '
            'that would not otherwise proceed. Quantify direct community beneficiaries.'
        ),
        'greenwashing_risk': (
            'Obtain an independent third-party second-party opinion or CBI certification. '
            'Align label terminology strictly with the underlying project type.'
        ),
        'ownership_transparency': (
            'Publish beneficial ownership structure and apply a recognised procurement '
            'framework. Disclose any related-party transactions in the offering documents.'
        ),
        'community_impact': (
            'Introduce a formal community consultation process (FPIC-aligned where applicable). '
            'Add grievance and remedy mechanisms and local employment commitments.'
        ),
        'measurable_impact': (
            'Set specific, time-bound emission reduction or resilience targets with a '
            'quantified baseline year and an independent verification schedule.'
        ),
        'ethical_compatibility': (
            'Review sector exclusion lists against IFC Performance Standards, EBRD Policy, '
            'and responsible finance framework exclusions before issuance.'
        ),
    }
    ranked = sorted(
        [(v, k) for k, v in dim.items()],
    )
    actions = [_map[k] for _, k in ranked[:4] if dim[k] < 70]
    if not actions:
        actions = [
            'Maintain current integrity standards across all seven CIS dimensions.',
            'Pursue annual independent impact reporting to reinforce investor confidence.',
        ]
    return actions


# ── Capital Integrity scorer ───────────────────────────────────────────────────

def score_capital_integrity(inp: CapitalIntegrityInput) -> CapitalIntegrityResult:
    """
    Rule-based Capital Integrity scoring across seven dimensions.

    # ML-HOOK: replace this function body with a sklearn model call:
    #   fv = list(capital_integrity_feature_vector(inp).values())
    #   scores = model.predict([fv])[0]  # 7 dimension scores
    #   final  = np.dot(scores, list(CIS_DIMENSION_WEIGHTS.values()))
    """
    fv = capital_integrity_feature_vector(inp)

    sector_lower = inp.sector.lower()
    instr_lower  = inp.instrument_type.lower()

    proc_base = _PROCUREMENT_BASE.get(inp.procurement_framework, 22.0)
    cb_base   = _CONSULTATION_BASE.get(inp.community_consultation, 25.0)
    tr_mod    = _TRACK_RECORD_MODIFIER.get(inp.issuer_track_record, -5.0)

    # ── 1. Use of Proceeds Clarity ────────────────────────────────────────────
    instr_base = _INSTRUMENT_CLARITY_BASE.get(instr_lower, 40.0)
    spec_mod   = _SPECIFICITY_MODIFIER.get(inp.use_of_proceeds_specificity, -20.0)
    reporting_bonus = 10.0 if inp.reporting_commitment == 'annual' else (5.0 if inp.reporting_commitment == 'bi-annual' else 0.0)
    tpv_bonus  = 12.0 if inp.third_party_verified else 0.0

    proceeds_clarity = _clamp(instr_base + spec_mod + reporting_bonus + tpv_bonus)

    # ── 2. Public Benefit Potential ───────────────────────────────────────────
    sector_benefit = _SECTOR_BENEFIT_BASE.get(sector_lower, 40.0)
    additionality_bonus = 10.0 if inp.additionality_demonstrated else 0.0
    # Large instruments have marginal scale benefit — log-scaled
    scale_bonus = min(math.log10(max(inp.proceeds_amount_usd or 1.0, 1.0)) * 1.2, 10.0)

    public_benefit = _clamp(sector_benefit + additionality_bonus + scale_bonus)

    # ── 3. Greenwashing Risk (inverted: high score = low risk) ────────────────
    # Start from a neutral 70 and apply penalties/bonuses
    gw_base = 70.0

    # Sector risk
    if sector_lower in _HIGH_GREENWASH_SECTORS:
        gw_base -= 28.0

    # Label–substance mismatch
    if not inp.label_matches_project:
        gw_base -= 35.0

    # Third-party verification is the primary mitigant
    if inp.third_party_verified:
        gw_base += 15.0

    # Baseline data — substantiates claims
    if inp.baseline_data_available:
        gw_base += 8.0

    # Independent verification plan
    if inp.independent_verification_plan:
        gw_base += 8.0

    # Issuer track record
    gw_base += tr_mod

    greenwashing_risk = _clamp(gw_base)

    # ── 4. Ownership & Procurement Transparency ───────────────────────────────
    # ownership_base: 80 = disclosed, 0 = not disclosed (binary flag)
    # blended 50/50 with procurement framework score
    ownership_base = 80.0 if inp.ownership_disclosed else 0.0
    ownership_transparency = _clamp(
        ownership_base * 0.50
        + proc_base    * 0.50
    )

    # ── 5. Community & Social Impact ──────────────────────────────────────────
    gender_bonus  = 8.0 if inp.gender_inclusion else 0.0
    employ_bonus  = 8.0 if inp.local_employment_commitment else 0.0

    community_impact = _clamp(cb_base + gender_bonus + employ_bonus)

    # ── 6. Measurable Emissions / Resilience Impact ───────────────────────────
    target_score  = 55.0 if inp.emission_reduction_target else 10.0
    plan_bonus    = 20.0 if inp.impact_measurement_plan else 0.0
    baseline_bonus = 15.0 if inp.baseline_data_available else 0.0
    verif_bonus   = 12.0 if inp.independent_verification_plan else 0.0

    measurable_impact = _clamp(target_score + plan_bonus + baseline_bonus + verif_bonus)

    # ── 7. Ethical Finance Compatibility ──────────────────────────────────────
    ethical_base = 80.0

    if inp.sector_excluded:
        ethical_base = 0.0   # hard exclusion
    elif sector_lower in _HIGH_GREENWASH_SECTORS:
        ethical_base -= 20.0

    if not inp.ownership_disclosed:
        ethical_base -= 10.0
    if inp.issuer_track_record == 'weak':
        ethical_base -= 15.0
    if not inp.label_matches_project:
        ethical_base -= 20.0

    ethical_compatibility = _clamp(ethical_base)

    # ── Weighted final score ──────────────────────────────────────────────────
    w = CIS_DIMENSION_WEIGHTS
    final = _clamp(
        proceeds_clarity       * w['proceeds_clarity']
        + public_benefit       * w['public_benefit']
        + greenwashing_risk    * w['greenwashing_risk']
        + ownership_transparency * w['ownership_transparency']
        + community_impact     * w['community_impact']
        + measurable_impact    * w['measurable_impact']
        + ethical_compatibility * w['ethical_compatibility']
    )

    dim = {
        'proceeds_clarity':       round(proceeds_clarity,       2),
        'public_benefit':         round(public_benefit,         2),
        'greenwashing_risk':      round(greenwashing_risk,      2),
        'ownership_transparency': round(ownership_transparency, 2),
        'community_impact':       round(community_impact,       2),
        'measurable_impact':      round(measurable_impact,      2),
        'ethical_compatibility':  round(ethical_compatibility,  2),
    }

    label     = _cis_label(final)
    flags     = _ci_red_flags(inp, dim)
    positives = _ci_positive_indicators(inp, dim)

    return CapitalIntegrityResult(
        capital_integrity_score  = round(final, 2),
        label                    = label,
        dimension_scores         = dim,
        red_flags                = flags,
        positive_indicators      = positives,
        investor_note            = _ci_investor_note(final, label, flags),
        islamic_finance_note     = _ci_ethical_finance_note(
            final, label,
            proceeds_clarity, public_benefit, greenwashing_risk, ownership_transparency,
            flags,
        ),
        due_diligence_required   = _ci_due_diligence(inp, flags, dim),
        recommended_next_actions = _ci_recommended_actions(dim, inp),
        confidence               = 'model-estimate',
    )
