"""
ml/projects/project_readiness.py — EcoIQ Project Readiness Score.

Assesses how ready a transition project is for investor, development bank,
or climate finance review across ten structured dimensions.

Ten dimensions (weights sum to 1.0):
  1.  Problem clarity                  0.12
  2.  Emissions baseline               0.12
  3.  Technical feasibility            0.12
  4.  CAPEX / OPEX clarity             0.12
  5.  Revenue or repayment model       0.12
  6.  Governance and procurement plan  0.10
  7.  Public benefit measurement       0.08
  8.  Risk mitigation                  0.10
  9.  Evidence confidence              0.07
  10. Finance structure readiness      0.05

Label tiers:
  investment-ready  ≥ 75   Bankable. Proceed to mandate / financial close.
  advanced          ≥ 58   Strong. Specific gaps require resolution first.
  developing        ≥ 40   Partial readiness. Project preparation support recommended.
  early-stage       < 40   Foundational work required before finance engagement.

Output:
  project_readiness_score      float 0–100
  readiness_label              str (one of four tiers above)
  dimension_scores             dict — all 10 raw scores
  missing_documents            list[str] — documents absent from the project file
  main_blockers                list[str] — highest-priority structural gaps
  investor_note                str — investor-facing narrative summary
  next_steps                   list[str] — ordered, actionable next steps
  recommended_finance_route    str — most appropriate financing pathway

ML integration note:
  # ML-HOOK: replace assess_project_readiness() body with:
  #   from joblib import load
  #   clf = load('ml/models/project_readiness_clf.joblib')
  #   fv  = project_readiness_feature_vector(inp)
  #   scores = clf.predict([list(fv.values())])[0]   # 10 dimension scores
  # Training data: IFC/EBRD project preparation assessments,
  # Green Climate Fund readiness grant outcomes, MDB project pipeline data,
  # GCF/JETP financial close timelines by project type.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# ── Dimension weights (must sum to 1.0) ────────────────────────────────────────

READINESS_WEIGHTS: dict[str, float] = {
    'problem_clarity':        0.12,
    'emissions_baseline':     0.12,
    'technical_feasibility':  0.12,
    'capex_opex_clarity':     0.12,
    'revenue_model':          0.12,
    'governance_procurement': 0.10,
    'public_benefit':         0.08,
    'risk_mitigation':        0.10,
    'evidence_confidence':    0.07,
    'finance_structure':      0.05,
}

# ── Label tiers ────────────────────────────────────────────────────────────────

READINESS_LABELS: list[tuple[float, str]] = [
    (75.0, 'investment-ready'),
    (58.0, 'advanced'),
    (40.0, 'developing'),
    (0.0,  'early-stage'),
]

# ── Lookup tables ──────────────────────────────────────────────────────────────

_PROBLEM_STATEMENT_BASE: dict[str, float] = {
    'detailed': 85.0,
    'clear':    65.0,
    'partial':  40.0,
    'vague':    20.0,
    'none':      5.0,
    '':          5.0,
}

_TECHNOLOGY_READINESS_BASE: dict[str, float] = {
    'operational': 90.0,
    'proven':      72.0,
    'pilot':       52.0,
    'prototype':   32.0,
    'concept':     12.0,
    '':            12.0,
}

_FEASIBILITY_STUDY_BONUS: dict[str, float] = {
    'bankable':     22.0,
    'standard':     12.0,
    'preliminary':   6.0,
    'none':          0.0,
    '':              0.0,
}

_CAPEX_QUALITY_BASE: dict[str, float] = {
    'detailed':             80.0,
    'order_of_magnitude':   52.0,
    'preliminary':          28.0,
    'none':                  5.0,
    '':                      5.0,
}

_OPEX_QUALITY_BONUS: dict[str, float] = {
    'detailed':             18.0,
    'order_of_magnitude':   10.0,
    'preliminary':           5.0,
    'none':                  0.0,
    '':                      0.0,
}

_REVENUE_MODEL_BASE: dict[str, float] = {
    'contracted': 88.0,
    'hybrid':     70.0,
    'market':     58.0,
    'grant':      50.0,
    'none':        5.0,
    '':            5.0,
}

_GOVERNANCE_BASE: dict[str, float] = {
    'IFC':         88.0,
    'EBRD':        88.0,
    'ADB':         83.0,
    'World Bank':  83.0,
    'EU Taxonomy': 80.0,
    'GBP':         75.0,
    'TCFD':        68.0,
    'national':    52.0,
    'none':        18.0,
    '':            18.0,
}

_COMMUNITY_BENEFIT_BASE: dict[str, float] = {
    'high':   80.0,
    'medium': 55.0,
    'low':    30.0,
    'none':    8.0,
    '':        8.0,
}

_EVIDENCE_TYPE_BASE: dict[str, float] = {
    'verified':          85.0,
    'analyst-reviewed':  65.0,
    'ai-seeded':         40.0,
    'model-estimate':    20.0,
    '':                  20.0,
}

_EMISSIONS_METHODOLOGY_BONUS: dict[str, float] = {
    'iso_14064':        18.0,
    'ghg_protocol':     16.0,
    'sector_specific':  12.0,
    'internal':          6.0,
    'none':              0.0,
    '':                  0.0,
}

# Recognised key document types
_KEY_DOCUMENTS = frozenset({
    'feasibility_study',
    'eia',              # Environmental Impact Assessment / ESIA
    'business_plan',
    'financial_model',
    'legal_opinion',
    'land_rights',
    'offtake_agreement',
    'permits',
    'social_assessment',
    'technical_report',
})

# Sectors where an EIA is a hard finance requirement
_EIA_REQUIRED_SECTORS = frozenset({
    'energy', 'renewables', 'infrastructure', 'transport',
    'water', 'mining', 'oil_gas', 'chemical', 'agriculture',
    'waste', 'forestry',
})

# Sectors that naturally produce infrastructure / tangible assets
_INFRASTRUCTURE_SECTORS = frozenset({
    'renewables', 'energy', 'infrastructure', 'transport',
    'water', 'waste', 'forestry',
})

# DFI frameworks recognised as high-governance
_DFI_FRAMEWORKS = frozenset({'IFC', 'EBRD', 'ADB', 'World Bank'})


# ── Helper ─────────────────────────────────────────────────────────────────────

def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v or 0)))


def _readiness_label(score: float) -> str:
    for threshold, label in READINESS_LABELS:
        if score >= threshold:
            return label
    return 'early-stage'


# ── Input dataclass ────────────────────────────────────────────────────────────

@dataclass
class ProjectReadinessInput:
    """
    Structured input for Project Readiness scoring.

    Required: sector
    All other fields are optional with conservative defaults.
    key_documents_available accepts a list of strings from the set:
      feasibility_study, eia, business_plan, financial_model,
      legal_opinion, land_rights, offtake_agreement, permits,
      social_assessment, technical_report
    """
    # Project identity
    project_name:    str            = 'Unnamed Project'
    sector:          str            = 'other'
    country:         str            = ''
    project_type:    str            = ''          # energy | infrastructure | transport | water | waste | agriculture | forestry | other
    budget_usd:      Optional[float] = None
    duration_years:  Optional[float] = None

    # ── Dimension 1: Problem clarity ──────────────────────────────────────────
    problem_statement:       str  = 'none'   # detailed | clear | partial | vague | none
    quantified_impact_target: bool = False   # specific, time-bound impact target declared
    baseline_problem_data:    bool = False   # supporting data for the problem exists

    # ── Dimension 2: Emissions baseline ──────────────────────────────────────
    emissions_baseline_documented:      bool = False
    baseline_independently_verified:    bool = False
    emissions_measurement_methodology:  str  = 'none'   # iso_14064 | ghg_protocol | sector_specific | internal | none

    # ── Dimension 3: Technical feasibility ───────────────────────────────────
    technology_readiness:          str  = 'concept'   # operational | proven | pilot | prototype | concept
    feasibility_study:             str  = 'none'      # bankable | standard | preliminary | none
    technical_advisor_engaged:     bool = False
    technology_local_availability: bool = False       # technology / supply chain available in-country

    # ── Dimension 4: CAPEX / OPEX clarity ────────────────────────────────────
    capex_estimate_quality:    str  = 'none'   # detailed | order_of_magnitude | preliminary | none
    opex_estimate_quality:     str  = 'none'   # detailed | order_of_magnitude | preliminary | none
    independent_cost_review:   bool = False
    contingency_provision:     bool = False    # contingency budget explicitly provided

    # ── Dimension 5: Revenue or repayment model ───────────────────────────────
    revenue_model:               str  = 'none'   # contracted | market | grant | hybrid | none
    offtake_agreement:           bool = False
    subsidy_or_grant_confirmed:  bool = False
    revenue_projections_available: bool = False

    # ── Dimension 6: Governance and procurement plan ──────────────────────────
    governance_framework:         str  = 'none'   # IFC | EBRD | ADB | World Bank | EU Taxonomy | GBP | TCFD | national | none
    procurement_plan_documented:  bool = False
    ownership_structure_disclosed: bool = False
    shareholder_agreement:        bool = False

    # ── Dimension 7: Public benefit measurement ───────────────────────────────
    community_benefit:            str  = 'none'   # high | medium | low | none
    direct_jobs:                  int  = 0
    public_benefit_metrics_defined: bool = False
    gender_inclusion_plan:        bool = False

    # ── Dimension 8: Risk mitigation ──────────────────────────────────────────
    risk_register_documented:   bool = False
    environmental_assessment:   bool = False   # EIA / ESIA completed or in progress
    social_risk_assessment:     bool = False
    insurance_plan:             bool = False
    force_majeure_coverage:     bool = False

    # ── Dimension 9: Evidence confidence ─────────────────────────────────────
    evidence_type:              str  = 'model-estimate'   # verified | analyst-reviewed | ai-seeded | model-estimate
    key_documents_available:    list = field(default_factory=list)
    legal_land_rights_confirmed: bool = False
    permits_in_progress:        bool = False

    # ── Dimension 10: Finance structure readiness ─────────────────────────────
    finance_instrument:         str  = ''       # green_bond | sukuk | project_finance | blended_finance | grant | equity | other
    financial_model_available:  bool = False
    legal_structure_defined:    bool = False
    co_financing_identified:    bool = False
    development_bank_engaged:   bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ProjectReadinessInput':
        valid = {f for f in cls.__dataclass_fields__}          # type: ignore[attr-defined]
        cleaned = {k: v for k, v in data.items() if k in valid}
        # Guard list field
        if 'key_documents_available' in cleaned:
            val = cleaned['key_documents_available']
            cleaned['key_documents_available'] = list(val) if isinstance(val, (list, tuple)) else []
        return cls(**cleaned)


# ── Output dataclass ───────────────────────────────────────────────────────────

@dataclass
class ProjectReadinessResult:
    """
    Full Project Readiness Score output.

    All dimension_scores values are in range 0–100.
    Fully serialisable via .to_dict().
    """
    project_readiness_score:   float
    readiness_label:           str       # 'investment-ready' | 'advanced' | 'developing' | 'early-stage'
    dimension_scores:          dict[str, float]

    missing_documents:         list[str]
    main_blockers:             list[str]

    investor_note:             str
    next_steps:                list[str]
    recommended_finance_route: str

    confidence:   str = 'model-estimate'
    methodology:  str = field(
        default='EcoIQ Project Readiness Score v1 — rule-based; ML integration pending'
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Feature vector (ML-ready) ──────────────────────────────────────────────────

def project_readiness_feature_vector(inp: ProjectReadinessInput) -> dict[str, float]:
    """
    Pre-compute a normalised feature vector for scikit-learn integration.

    All features are floats in range [0.0, 100.0].
    Feed directly into StandardScaler → GradientBoosting / RandomForest.

    # ML-HOOK: replace dimension formulas in assess_project_readiness() with:
    #   fv     = project_readiness_feature_vector(inp)
    #   scores = clf.predict([list(fv.values())])[0]
    """
    docs = set(str(d).lower() for d in inp.key_documents_available)
    gov  = inp.governance_framework

    return {
        # Problem clarity
        'problem_statement_base':    _PROBLEM_STATEMENT_BASE.get(inp.problem_statement, 5.0),
        'quantified_impact_target':  100.0 if inp.quantified_impact_target else 0.0,
        'baseline_problem_data':     100.0 if inp.baseline_problem_data else 0.0,

        # Emissions baseline
        'emissions_documented':      100.0 if inp.emissions_baseline_documented else 0.0,
        'baseline_verified':         100.0 if inp.baseline_independently_verified else 0.0,
        'methodology_bonus':         _EMISSIONS_METHODOLOGY_BONUS.get(inp.emissions_measurement_methodology, 0.0),

        # Technical feasibility
        'tech_readiness_base':       _TECHNOLOGY_READINESS_BASE.get(inp.technology_readiness, 12.0),
        'feasibility_bonus':         _FEASIBILITY_STUDY_BONUS.get(inp.feasibility_study, 0.0),
        'technical_advisor':         100.0 if inp.technical_advisor_engaged else 0.0,
        'local_tech_available':      100.0 if inp.technology_local_availability else 0.0,

        # CAPEX / OPEX
        'capex_base':                _CAPEX_QUALITY_BASE.get(inp.capex_estimate_quality, 5.0),
        'opex_bonus':                _OPEX_QUALITY_BONUS.get(inp.opex_estimate_quality, 0.0),
        'independent_cost_review':   100.0 if inp.independent_cost_review else 0.0,
        'contingency_provision':     100.0 if inp.contingency_provision else 0.0,

        # Revenue model
        'revenue_base':              _REVENUE_MODEL_BASE.get(inp.revenue_model, 5.0),
        'offtake_agreement':         100.0 if inp.offtake_agreement else 0.0,
        'grant_confirmed':           100.0 if inp.subsidy_or_grant_confirmed else 0.0,
        'revenue_projections':       100.0 if inp.revenue_projections_available else 0.0,

        # Governance
        'governance_base':           _GOVERNANCE_BASE.get(gov, 18.0),
        'procurement_documented':    100.0 if inp.procurement_plan_documented else 0.0,
        'ownership_disclosed':       100.0 if inp.ownership_structure_disclosed else 0.0,
        'shareholder_agreement':     100.0 if inp.shareholder_agreement else 0.0,

        # Public benefit
        'community_base':            _COMMUNITY_BENEFIT_BASE.get(inp.community_benefit, 8.0),
        'direct_jobs_score':         min(inp.direct_jobs * 0.05, 12.0),
        'benefit_metrics_defined':   100.0 if inp.public_benefit_metrics_defined else 0.0,
        'gender_inclusion':          100.0 if inp.gender_inclusion_plan else 0.0,

        # Risk mitigation
        'risk_register':             100.0 if inp.risk_register_documented else 0.0,
        'eia_completed':             100.0 if inp.environmental_assessment else 0.0,
        'social_risk_assessed':      100.0 if inp.social_risk_assessment else 0.0,
        'insurance_plan':            100.0 if inp.insurance_plan else 0.0,
        'force_majeure':             100.0 if inp.force_majeure_coverage else 0.0,

        # Evidence confidence
        'evidence_base':             _EVIDENCE_TYPE_BASE.get(inp.evidence_type, 20.0),
        'doc_count':                 min(len(docs & _KEY_DOCUMENTS) * 8.0, 40.0),
        'land_rights':               100.0 if inp.legal_land_rights_confirmed else 0.0,
        'permits_in_progress':       100.0 if inp.permits_in_progress else 0.0,

        # Finance structure
        'financial_model':           100.0 if inp.financial_model_available else 0.0,
        'legal_structure':           100.0 if inp.legal_structure_defined else 0.0,
        'co_financing':              100.0 if inp.co_financing_identified else 0.0,
        'dfi_engaged':               100.0 if inp.development_bank_engaged else 0.0,
        'instrument_specified':      0.0 if not inp.finance_instrument else 100.0,

        # Budget scale (log-normalised to 0–100)
        'budget_log':                min(math.log10(max(inp.budget_usd or 1.0, 1.0)) * 12.5, 100.0),
    }


# ── Scoring functions (one per dimension) ─────────────────────────────────────

def _score_problem_clarity(inp: ProjectReadinessInput) -> float:
    base   = _PROBLEM_STATEMENT_BASE.get(inp.problem_statement, 5.0)
    target = 10.0 if inp.quantified_impact_target else 0.0
    data   = 8.0  if inp.baseline_problem_data else 0.0
    return _clamp(base + target + data)


def _score_emissions_baseline(inp: ProjectReadinessInput) -> float:
    if not inp.emissions_baseline_documented:
        # A project with no baseline can still score a few points if methodology is declared
        method_bonus = _EMISSIONS_METHODOLOGY_BONUS.get(inp.emissions_measurement_methodology, 0.0)
        return _clamp(5.0 + method_bonus * 0.3)   # heavily discounted
    base     = 55.0
    verified = 25.0 if inp.baseline_independently_verified else 0.0
    method   = _EMISSIONS_METHODOLOGY_BONUS.get(inp.emissions_measurement_methodology, 0.0)
    return _clamp(base + verified + method)


def _score_technical_feasibility(inp: ProjectReadinessInput) -> float:
    base     = _TECHNOLOGY_READINESS_BASE.get(inp.technology_readiness, 12.0)
    feasib   = _FEASIBILITY_STUDY_BONUS.get(inp.feasibility_study, 0.0)
    advisor  = 8.0 if inp.technical_advisor_engaged else 0.0
    local    = 5.0 if inp.technology_local_availability else 0.0
    return _clamp(base + feasib + advisor + local)


def _score_capex_opex(inp: ProjectReadinessInput) -> float:
    capex_base = _CAPEX_QUALITY_BASE.get(inp.capex_estimate_quality, 5.0)
    opex_bonus = _OPEX_QUALITY_BONUS.get(inp.opex_estimate_quality, 0.0)
    ind_review = 12.0 if inp.independent_cost_review else 0.0
    contingency = 8.0 if inp.contingency_provision else 0.0
    return _clamp(capex_base + opex_bonus + ind_review + contingency)


def _score_revenue_model(inp: ProjectReadinessInput) -> float:
    base       = _REVENUE_MODEL_BASE.get(inp.revenue_model, 5.0)
    offtake    = 15.0 if inp.offtake_agreement else 0.0
    grant_conf = 10.0 if inp.subsidy_or_grant_confirmed else 0.0
    projections = 8.0 if inp.revenue_projections_available else 0.0
    return _clamp(base + offtake + grant_conf + projections)


def _score_governance_procurement(inp: ProjectReadinessInput) -> float:
    gov_base     = _GOVERNANCE_BASE.get(inp.governance_framework, 18.0)
    procurement  = 10.0 if inp.procurement_plan_documented else 0.0
    ownership    = 8.0  if inp.ownership_structure_disclosed else 0.0
    shareholders = 5.0  if inp.shareholder_agreement else 0.0
    return _clamp(gov_base + procurement + ownership + shareholders)


def _score_public_benefit(inp: ProjectReadinessInput) -> float:
    base       = _COMMUNITY_BENEFIT_BASE.get(inp.community_benefit, 8.0)
    jobs_bonus = min(inp.direct_jobs * 0.05, 12.0)
    metrics    = 10.0 if inp.public_benefit_metrics_defined else 0.0
    gender     = 6.0  if inp.gender_inclusion_plan else 0.0
    return _clamp(base + jobs_bonus + metrics + gender)


def _score_risk_mitigation(inp: ProjectReadinessInput) -> float:
    risk_reg  = 30.0 if inp.risk_register_documented else 0.0
    eia       = 22.0 if inp.environmental_assessment else 0.0
    social    = 18.0 if inp.social_risk_assessment else 0.0
    insurance = 12.0 if inp.insurance_plan else 0.0
    fm        = 8.0  if inp.force_majeure_coverage else 0.0
    # Base 10 ensures a non-zero starting floor
    return _clamp(10.0 + risk_reg + eia + social + insurance + fm)


def _score_evidence_confidence(inp: ProjectReadinessInput) -> float:
    base     = _EVIDENCE_TYPE_BASE.get(inp.evidence_type, 20.0)
    docs     = set(str(d).lower() for d in inp.key_documents_available)
    doc_pts  = min(len(docs & _KEY_DOCUMENTS) * 8.0, 40.0)
    land     = 12.0 if inp.legal_land_rights_confirmed else 0.0
    permits  = 8.0  if inp.permits_in_progress else 0.0
    return _clamp(base + doc_pts + land + permits)


def _score_finance_structure(inp: ProjectReadinessInput) -> float:
    fm      = 30.0 if inp.financial_model_available else 0.0
    legal   = 22.0 if inp.legal_structure_defined else 0.0
    cofin   = 18.0 if inp.co_financing_identified else 0.0
    dfi     = 15.0 if inp.development_bank_engaged else 0.0
    instr   = 8.0  if inp.finance_instrument.strip() else 0.0
    return _clamp(10.0 + fm + legal + cofin + dfi + instr)


# ── Missing documents detector ─────────────────────────────────────────────────

def _missing_documents(inp: ProjectReadinessInput, dim: dict[str, float]) -> list[str]:
    """
    Identifies documents expected by investors and development banks
    that are absent from the declared project file.
    """
    docs    = set(str(d).lower() for d in inp.key_documents_available)
    sector  = inp.sector.lower()
    missing = []

    if inp.feasibility_study in ('none', '') and 'feasibility_study' not in docs:
        missing.append('Bankable feasibility study (AACE Class 3 or equivalent)')

    if not inp.financial_model_available and 'financial_model' not in docs:
        missing.append('Financial model with 20-year cash flow projections and sensitivity analysis')

    if not inp.environmental_assessment and 'eia' not in docs and sector in _EIA_REQUIRED_SECTORS:
        missing.append('Environmental and Social Impact Assessment (ESIA / EIA)')

    if not inp.emissions_baseline_documented:
        missing.append('Quantified emissions baseline with recognised measurement methodology')

    if not inp.legal_land_rights_confirmed and 'land_rights' not in docs:
        missing.append('Land rights documentation — title, lease, or government allocation letter')

    if not inp.permits_in_progress and 'permits' not in docs:
        missing.append('Permits and regulatory approvals (or evidence they are in progress)')

    if inp.revenue_model not in ('contracted', 'hybrid') and not inp.offtake_agreement and 'offtake_agreement' not in docs:
        missing.append('Offtake agreement or revenue framework (PPA, concession, off-taker commitment)')

    if 'legal_opinion' not in docs and not inp.legal_structure_defined:
        missing.append('Independent legal opinion on project structure and regulatory compliance')

    if not inp.social_risk_assessment and 'social_assessment' not in docs:
        missing.append('Social risk and stakeholder engagement assessment')

    if not inp.ownership_structure_disclosed:
        missing.append('Disclosed ownership and shareholding structure (UBO register or equivalent)')

    return missing


# ── Main blockers ──────────────────────────────────────────────────────────────

def _main_blockers(inp: ProjectReadinessInput, dim: dict[str, float]) -> list[str]:
    """
    Derives the highest-priority structural gaps from dimension scores
    and input signals. Returns up to 5 blockers in order of severity.
    """
    candidates: list[tuple[float, str]] = []

    if dim['revenue_model'] < 35:
        candidates.append((dim['revenue_model'],
            'No credible revenue or repayment model — investors cannot underwrite the project '
            'without a defined cash-flow structure (offtake, concession, or grant framework)'))

    if dim['technical_feasibility'] < 35:
        candidates.append((dim['technical_feasibility'],
            'Technical feasibility not established — a bankable feasibility study by a '
            'recognised technical advisor is required before lender or investor engagement'))

    if dim['capex_opex_clarity'] < 35:
        candidates.append((dim['capex_opex_clarity'],
            'Cost estimates missing or unreliable — project finance requires detailed CAPEX/OPEX '
            'with independent cost review before a lender can assess debt serviceability'))

    if dim['emissions_baseline'] < 20:
        candidates.append((dim['emissions_baseline'],
            'No quantified emissions baseline — climate finance (GCF, JETP, carbon markets) '
            'requires a verified baseline with a recognised measurement methodology'))

    if dim['risk_mitigation'] < 30:
        candidates.append((dim['risk_mitigation'],
            'Risk management framework absent — investors require a documented risk register, '
            'EIA, and insurance/force majeure provisions before financial close'))

    if dim['governance_procurement'] < 30:
        candidates.append((dim['governance_procurement'],
            'Governance framework inadequate — ownership structure, procurement plan, and '
            'applicable development bank / national standards must be in place'))

    if dim['finance_structure'] < 25 and dim['revenue_model'] > 40:
        candidates.append((dim['finance_structure'],
            'Finance structure not defined — legal structure, financial model, and instrument '
            'choice are needed before lender mandate and term sheet discussions'))

    if dim['evidence_confidence'] < 30:
        candidates.append((dim['evidence_confidence'],
            'Insufficient documentation — key documents (feasibility study, EIA, land rights, '
            'financial model) are missing from the project file'))

    if inp.problem_statement in ('none', 'vague'):
        candidates.append((dim['problem_clarity'],
            'Problem statement not clearly defined — investors need a specific, quantified '
            'description of the transition problem the project addresses'))

    # Sort by lowest score first (most severe), return top 5
    candidates.sort(key=lambda x: x[0])
    return [msg for _, msg in candidates[:5]]


# ── Finance route recommender ──────────────────────────────────────────────────

def _recommended_finance_route(inp: ProjectReadinessInput, score: float, dim: dict[str, float]) -> str:
    """
    Returns the most appropriate financing pathway given project stage,
    sector, governance, and revenue characteristics.
    """
    gov      = inp.governance_framework
    sector   = inp.sector.lower()
    budget   = inp.budget_usd or 0.0
    label    = _readiness_label(score)

    # ── Early-stage: project preparation first ────────────────────────────────
    if label == 'early-stage':
        if gov in _DFI_FRAMEWORKS or inp.development_bank_engaged:
            return (
                'Project Preparation Facility: engage the IFC-MCPP Project Preparation Facility, '
                'EBRD Early Transition Countries grant, or GCF Readiness Programme to fund the '
                'bankable feasibility study, EIA, and financial model before investor engagement.'
            )
        return (
            'Technical Assistance (TA) Grant: project is at an early stage and requires '
            'structured project preparation support. Apply for a GCF Readiness Grant, '
            'UNDP/GEF preparation facility, or bilateral donor TA programme before approaching '
            'commercial investors or development banks.'
        )

    # ── Developing: targeted preparation support ──────────────────────────────
    if label == 'developing':
        if inp.development_bank_engaged and gov in _DFI_FRAMEWORKS:
            return (
                'Development Bank Project Preparation: continue DFI engagement to close '
                'documentation gaps. Target IFC Infrastructure Program or EBRD GEFF. '
                'A co-financing structure with DFI first-loss tranche is achievable once '
                'feasibility, revenue model, and EIA are completed.'
            )
        if inp.co_financing_identified:
            return (
                'Blended Finance — Project Preparation Stage: co-financing partners are '
                'identified. Formalise the governance framework, close the feasibility and '
                'EIA gaps, and structure a blended instrument combining grant or concessional '
                'debt with private equity to bridge to bankable stage.'
            )
        return (
            'Impact Equity + TA Grant: engage impact investors (equity) to fund project '
            'preparation, alongside a technical assistance grant for feasibility and '
            'environmental studies. Target climate-focused seed funds or development '
            'finance intermediaries. Target 18–24 months to bankable stage.'
        )

    # ── Advanced: structured debt or blended finance within reach ─────────────
    if label == 'advanced':
        if inp.revenue_model == 'contracted' and inp.offtake_agreement:
            if budget >= 50_000_000:
                return (
                    'Project Finance (Limited Recourse): contracted offtake and project scale '
                    f'(USD {budget:,.0f}) support a senior secured debt structure. '
                    'Engage a lead arranger — commercial bank, DFI, or bond market — '
                    'and complete the independent technical and legal review for financial close.'
                )
            return (
                'Senior Debt Facility: contracted revenue supports a bilateral or club-loan '
                'senior debt structure. Engage DFI or commercial bank for a term sheet. '
                'Close remaining documentation gaps in parallel.'
            )
        if gov in _DFI_FRAMEWORKS or inp.development_bank_engaged:
            return (
                'Blended Finance — DFI Co-Investment: governance framework qualifies for '
                f'{"IFC/EBRD/ADB" if gov in _DFI_FRAMEWORKS else "DFI"} co-finance. '
                'Structure a blended facility: DFI first-loss or concessional tranche + '
                'commercial senior debt + equity. Initiate formal DFI appraisal process.'
            )
        if inp.subsidy_or_grant_confirmed:
            return (
                'Concessional Debt + Grant Co-Financing: confirmed grant/subsidy provides '
                'first-loss cover. Layer a concessional debt facility (bilateral lender or '
                'green bond) above the grant tranche. Formalise the revenue projections '
                'and independent cost review to close the financing structure.'
            )
        return (
            'Blended Finance Structure: project is advanced but lacks a contracted revenue '
            'model or DFI anchor. Target a results-based financing structure (JETP, GCF, '
            'or GEEREF) combined with equity from climate-focused fund managers. '
            'Resolve revenue model gap before approaching senior debt providers.'
        )

    # ── Investment-ready: capital markets or senior project finance ────────────
    # label == 'investment-ready'
    if sector in ('renewables', 'energy') and budget >= 100_000_000 and gov in _DFI_FRAMEWORKS:
        instrument = inp.finance_instrument.lower()
        if 'sukuk' in instrument:
            return (
                'Green Sukuk Issuance: project is structurally ready for Islamic capital market '
                'financing. Engage a Sukuk arranger and Shariah advisory board alongside the '
                'existing DFI framework. Suitable for Wakala or Ijara structure given the '
                'asset-backed nature of the project.'
            )
        return (
            'Green Bond or DFI Senior Facility: project meets investment-grade readiness '
            f'(USD {budget:,.0f}, {gov} framework, renewable sector). Engage a lead arranger '
            'for a Green Bond roadshow or DFI senior secured facility. CBI certification or '
            'second-party opinion recommended to unlock ESG investor demand.'
        )

    if inp.revenue_model == 'contracted' and inp.offtake_agreement and inp.financial_model_available:
        return (
            'Project Finance — Financial Close Ready: contracted revenue profile, available '
            'financial model, and legal structure support a direct path to financial close. '
            'Engage lead arranger for mandate letter, initiate independent engineer review, '
            'and proceed to lender due diligence.'
        )

    return (
        'Investment-Grade Blended Finance or Direct Senior Debt: project readiness score '
        'supports engagement with senior commercial lenders and development finance '
        'institutions. Initiate formal mandate discussions. Close any remaining revenue '
        'or documentation gaps in parallel with lender due diligence.'
    )


# ── Narrative builders ─────────────────────────────────────────────────────────

def _investor_note(score: float, label: str, inp: ProjectReadinessInput, dim: dict[str, float]) -> str:
    budget_str = f'USD {inp.budget_usd:,.0f}' if inp.budget_usd else 'undisclosed budget'
    sector_str = inp.sector or 'unspecified sector'

    if score >= 75:
        return (
            f'This {sector_str} project ({budget_str}) has reached investment-ready status '
            f'across all ten Project Readiness dimensions. Technical feasibility, cost estimates, '
            f'revenue model, and governance framework are sufficiently developed to support '
            f'formal lender engagement. Proceed to mandate discussions, independent technical '
            f'review, and legal due diligence.'
        )
    if score >= 58:
        weak_dims = [k.replace('_', ' ') for k, v in dim.items() if v < 50]
        gap_str   = f' Key gaps: {", ".join(weak_dims[:3])}.' if weak_dims else ''
        return (
            f'This {sector_str} project ({budget_str}) demonstrates advanced readiness with '
            f'addressable gaps. The project has strong foundations in several dimensions but '
            f'requires targeted improvements before formal finance engagement.{gap_str} '
            f'Estimated time to investment-ready stage: 6–12 months with focused preparation.'
        )
    if score >= 40:
        return (
            f'This {sector_str} project ({budget_str}) is at a developing stage. Core '
            f'elements of the project concept are in place but significant documentation, '
            f'technical, or commercial gaps remain. Project preparation support — feasibility '
            f'study, EIA, financial modelling — is required before investor engagement. '
            f'Target: 12–24 months to investment-ready with structured preparation support.'
        )
    return (
        f'This {sector_str} project ({budget_str}) is at an early stage. Foundational '
        f'project development work — problem definition, technology selection, emissions '
        f'baseline, and governance structure — must be completed before approaching '
        f'investors or development banks. A technical assistance grant for project '
        f'preparation is the recommended immediate next step.'
    )


def _next_steps(inp: ProjectReadinessInput, dim: dict[str, float], missing: list[str]) -> list[str]:
    """
    Generates up to 5 ordered, actionable next steps derived from the
    weakest dimensions and highest-priority missing documents.
    """
    steps: list[tuple[float, str]] = []

    if dim['technical_feasibility'] < 60:
        steps.append((dim['technical_feasibility'],
            'Commission a bankable feasibility study from a recognised technical advisor '
            '(AACE Class 3 / IFC-acceptable standard) covering technology selection, '
            'site assessment, and engineering design.'))

    if dim['emissions_baseline'] < 50:
        steps.append((dim['emissions_baseline'],
            'Establish and independently verify an emissions baseline using GHG Protocol '
            'or ISO 14064 methodology. This is a prerequisite for climate finance '
            '(GCF, JETP, carbon market crediting).'))

    if dim['revenue_model'] < 55:
        steps.append((dim['revenue_model'],
            'Define and document the revenue or repayment model — pursue offtake negotiations, '
            'concession agreement, or grant commitment. A contracted cash flow is the single '
            'most important step towards bankability.'))

    if dim['capex_opex_clarity'] < 50:
        steps.append((dim['capex_opex_clarity'],
            'Upgrade cost estimates to AACE Class 3 standard with an independent cost review '
            'and a documented contingency provision (typically 10–15% of CAPEX for this stage).'))

    if dim['risk_mitigation'] < 45:
        steps.append((dim['risk_mitigation'],
            'Complete the Environmental and Social Impact Assessment (ESIA), develop a '
            'risk register covering construction, operational, and country risks, and '
            'initiate insurance scoping.'))

    if dim['finance_structure'] < 45:
        steps.append((dim['finance_structure'],
            'Build a 20-year financial model with three scenarios (base, stress, upside), '
            'define the legal structure and SPV if applicable, and identify co-financing '
            'partners before approaching lead arrangers.'))

    if dim['governance_procurement'] < 50:
        steps.append((dim['governance_procurement'],
            'Adopt a recognised governance framework (IFC Performance Standards or EBRD '
            'Environmental Policy) and document the procurement plan and ownership structure.'))

    if dim['evidence_confidence'] < 45:
        steps.append((dim['evidence_confidence'],
            'Compile the core project document package: feasibility study, EIA, financial '
            'model, legal opinion, land rights, and permits. Investors expect a complete '
            'data room before entering due diligence.'))

    # Sort by lowest score first, deduplicate, cap at 5
    steps.sort(key=lambda x: x[0])
    return [msg for _, msg in steps[:5]]


# ── Main scorer ────────────────────────────────────────────────────────────────

def assess_project_readiness(inp: ProjectReadinessInput) -> ProjectReadinessResult:
    """
    Rule-based Project Readiness scoring across ten dimensions.

    # ML-HOOK: replace this function body with a sklearn model call:
    #   fv = list(project_readiness_feature_vector(inp).values())
    #   scores = model.predict([fv])[0]   # 10 dimension scores
    #   final  = np.dot(scores, list(READINESS_WEIGHTS.values()))
    """
    # ── Compute all ten dimension scores ──────────────────────────────────────
    problem_clarity        = _score_problem_clarity(inp)
    emissions_baseline     = _score_emissions_baseline(inp)
    technical_feasibility  = _score_technical_feasibility(inp)
    capex_opex_clarity     = _score_capex_opex(inp)
    revenue_model          = _score_revenue_model(inp)
    governance_procurement = _score_governance_procurement(inp)
    public_benefit         = _score_public_benefit(inp)
    risk_mitigation        = _score_risk_mitigation(inp)
    evidence_confidence    = _score_evidence_confidence(inp)
    finance_structure      = _score_finance_structure(inp)

    # ── Weighted composite ────────────────────────────────────────────────────
    w = READINESS_WEIGHTS
    final = _clamp(
        problem_clarity        * w['problem_clarity']
        + emissions_baseline   * w['emissions_baseline']
        + technical_feasibility * w['technical_feasibility']
        + capex_opex_clarity   * w['capex_opex_clarity']
        + revenue_model        * w['revenue_model']
        + governance_procurement * w['governance_procurement']
        + public_benefit       * w['public_benefit']
        + risk_mitigation      * w['risk_mitigation']
        + evidence_confidence  * w['evidence_confidence']
        + finance_structure    * w['finance_structure']
    )

    dim = {
        'problem_clarity':        round(problem_clarity,        2),
        'emissions_baseline':     round(emissions_baseline,     2),
        'technical_feasibility':  round(technical_feasibility,  2),
        'capex_opex_clarity':     round(capex_opex_clarity,     2),
        'revenue_model':          round(revenue_model,          2),
        'governance_procurement': round(governance_procurement, 2),
        'public_benefit':         round(public_benefit,         2),
        'risk_mitigation':        round(risk_mitigation,        2),
        'evidence_confidence':    round(evidence_confidence,    2),
        'finance_structure':      round(finance_structure,      2),
    }

    label   = _readiness_label(final)
    missing = _missing_documents(inp, dim)
    blockers = _main_blockers(inp, dim)
    steps   = _next_steps(inp, dim, missing)
    route   = _recommended_finance_route(inp, final, dim)
    note    = _investor_note(final, label, inp, dim)

    # Evidence confidence level follows the input evidence_type
    _evidence_tier_map = {
        'verified':         'verified',
        'analyst-reviewed': 'analyst-reviewed',
        'ai-seeded':        'ai-seeded',
        'model-estimate':   'model-estimate',
    }
    confidence = _evidence_tier_map.get(inp.evidence_type, 'model-estimate')

    return ProjectReadinessResult(
        project_readiness_score   = round(final, 2),
        readiness_label           = label,
        dimension_scores          = dim,
        missing_documents         = missing,
        main_blockers             = blockers,
        investor_note             = note,
        next_steps                = steps,
        recommended_finance_route = route,
        confidence                = confidence,
    )
