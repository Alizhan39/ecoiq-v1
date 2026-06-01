"""
ml/finance/islamic_finance_fit.py — EcoIQ Islamic & Ethical Finance Fit assessment.

PUBLIC NAME: Islamic & Ethical Finance Fit

Assesses whether a transition project may be structurally suitable for
Islamic finance instruments (sukuk, murabaha, musharakah), ethical
finance frameworks, or development-bank blended finance.

⚠ IMPORTANT LANGUAGE RULES — enforce in all output fields:
  ✓ "potentially suitable for Islamic finance review"
  ✓ "requires qualified Shariah scholar / advisory board review"
  ✓ "indicative only — not a religious ruling or Shariah determination"
  ✓ "may be compatible with Islamic finance principles"
  ✗ Never write: "Shariah-compliant", "halal", "haram", "fatwa"
  ✗ Never issue rulings, certifications, or religious determinations
  ✗ Never claim or imply Shariah approval

Nine assessment dimensions (weights sum to 1.0):
  1. Real asset / real economy linkage          0.15
  2. Public benefit                             0.15
  3. Transparency of use of proceeds            0.15
  4. Harm reduction                             0.12
  5. Avoidance of excessive uncertainty         0.10
  6. Fair risk-sharing potential                0.10
  7. Governance and accountability              0.10
  8. Environmental stewardship                  0.08
  9. Measurable impact                          0.05

Label tiers:
  high-potential  ≥ 75   Strong structural fit across core dimensions
  strong          ≥ 58   Good fit with manageable gaps
  possible        ≥ 38   Partial fit — specific conditions must be met first
  weak            < 38   Poor structural fit for Islamic / ethical finance instruments

ML integration note:
  # ML-HOOK: replace assess_islamic_finance_fit() with:
  #   from joblib import load
  #   clf = load('ml/models/islamic_finance_fit_clf.joblib')
  #   fv  = islamic_finance_feature_vector(inp)
  #   scores = clf.predict([list(fv.values())])[0]   # 9 dimension scores
  # Training data: historical sukuk issuance outcomes, AAOIFI-aligned
  # project assessments, IFC-financed Islamic tranche data.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# ── Dimension weights ─────────────────────────────────────────────────────────

DIMENSION_WEIGHTS: dict[str, float] = {
    'real_asset_linkage':          0.15,
    'public_benefit':              0.15,
    'transparency_proceeds':       0.15,
    'harm_reduction':              0.12,
    'uncertainty_avoidance':       0.10,
    'fair_risk_sharing':           0.10,
    'governance_accountability':   0.10,
    'environmental_stewardship':   0.08,
    'measurable_impact':           0.05,
}

# ── Label tiers ───────────────────────────────────────────────────────────────

FIT_LABELS: list[tuple[float, str]] = [
    (75.0, 'high-potential'),
    (58.0, 'strong'),
    (38.0, 'possible'),
    (0.0,  'weak'),
]

# ── Lookup tables ─────────────────────────────────────────────────────────────

# Sectors excluded by most Islamic and responsible finance frameworks.
# "coal" is listed as severely cautionary (some frameworks exclude, others restrict).
_IF_EXCLUDED_SECTORS = frozenset({
    'tobacco', 'alcohol', 'weapons', 'arms', 'defence_controversial',
    'gambling', 'adult_entertainment', 'pork', 'conventional_banking',
    'speculative_trading',
})

_IF_CAUTIONARY_SECTORS = frozenset({
    'coal', 'coal_mining',       # near-universal exclusion in green-aligned IF frameworks
    'heavy_chemicals',           # depends on product mix
    'arms',                      # country-specific
})

# Sectors with natural real-asset linkage for sukuk structuring
_ASSET_BACKED_SECTORS = frozenset({
    'renewables', 'energy', 'infrastructure', 'transport', 'water',
    'agriculture', 'forestry', 'housing', 'real_estate', 'manufacturing',
    'mining', 'metallurgy', 'health', 'education',
})

# Project types suited to Istisna (construction financing)
_ISTISNA_ELIGIBLE_TYPES = frozenset({
    'renewable_energy', 'infrastructure', 'manufacturing', 'construction',
    'water_treatment', 'transport_corridor', 'industrial_facility',
})

# Governance framework → base governance score
_GOVERNANCE_BASE: dict[str, float] = {
    'IFC':         88.0,
    'EBRD':        88.0,
    'ADB':         83.0,
    'World Bank':  83.0,
    'EU Taxonomy': 80.0,
    'GBP':         75.0,
    'ICMA':        75.0,
    'AAOIFI':      82.0,      # AAOIFI — Islamic finance standard
    'IFSB':        80.0,      # Islamic Financial Services Board
    'national':    52.0,
    'none':        18.0,
    '':            18.0,
}

# Community benefit declaration → public benefit base
_CB_BASE: dict[str, float] = {
    'high':   85.0,
    'medium': 58.0,
    'low':    30.0,
    'none':   8.0,
    '':       35.0,
}

# Proceeds specificity → transparency base
_SPECIFICITY_BASE: dict[str, float] = {
    'specific':  82.0,
    'general':   52.0,
    'vague':     22.0,
    'none':       5.0,
    '':          30.0,
}

# Project stage → uncertainty score (more advanced = less uncertainty)
_STAGE_CERTAINTY: dict[str, float] = {
    'operational':  90.0,
    'construction': 70.0,
    'development':  52.0,
    'feasibility':  32.0,
    '':             40.0,
}

# Contractual clarity → uncertainty modifier
_CLARITY_BASE: dict[str, float] = {
    'high':     85.0,
    'standard': 58.0,
    'low':      28.0,
    '':         45.0,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v or 0)))


def _fit_label(score: float) -> str:
    for threshold, label in FIT_LABELS:
        if score >= threshold:
            return label
    return 'weak'


# ── Input dataclass ───────────────────────────────────────────────────────────

@dataclass
class IslamicFinanceFitInput:
    """
    Structured input for Islamic & Ethical Finance Fit assessment.

    Required: sector
    All other fields are optional with conservative defaults.
    Use from_dict() to construct from a request body.
    """
    name:         str = 'Unnamed Project'
    sector:       str = 'other'
    country:      str = ''
    project_type: str = 'infrastructure'
    description:  str = ''

    # Scale
    budget_usd:     Optional[float] = None
    duration_years: Optional[float] = None

    # Dimension 1: Real asset / real economy linkage
    tangible_asset_linked:        bool = False   # Is there a specific, identifiable underlying asset?
    asset_ownership_transferable: bool = False   # Can ownership / beneficial interest transfer to investors?
    asset_generates_income:       bool = False   # Does the asset generate recurring income (rent, revenue)?

    # Dimension 2: Public benefit
    community_benefit:       str   = 'medium'    # high | medium | low | none
    direct_jobs:             int   = 0
    local_procurement_pct:   float = 0.0         # 0–100
    additionality_demonstrated: bool = False     # Capital would not flow without this instrument

    # Dimension 3: Transparency of use of proceeds
    use_of_proceeds_specificity: str  = 'general'   # specific | general | vague | none
    third_party_verified:        bool = False
    reporting_commitment:        str  = 'none'       # annual | bi-annual | none
    ring_fenced_account:         bool = False        # Proceeds held in dedicated account

    # Dimension 4: Harm reduction
    sector_excluded:            bool = False    # Excluded by Islamic / ethical finance frameworks
    sector_cautionary:          bool = False    # Cautionary but not universally excluded
    environmental_assessment:   bool = False    # EIA conducted
    pollution_mitigation_plan:  bool = False    # Active pollution mitigation plan

    # Dimension 5: Avoidance of excessive uncertainty
    project_stage:        str  = 'feasibility'  # feasibility | development | construction | operational
    contractual_clarity:  str  = 'standard'     # high | standard | low
    performance_guarantees: bool = False         # Performance bonds or completion guarantees in place

    # Dimension 6: Fair risk-sharing potential
    profit_loss_sharing:          bool = False   # True = P&L sharing structure (equity-like)
    investor_equity_participation: bool = False  # Investors hold equity or quasi-equity stake
    fixed_return_only:            bool = False   # True = conventional fixed-interest structure only
    community_benefit_sharing:    bool = False   # Community holds a share of project benefits

    # Dimension 7: Governance and accountability
    governance_framework:      str  = 'none'    # IFC | EBRD | ADB | AAOIFI | IFSB | national | none
    ownership_disclosed:       bool = False
    independent_board_oversight: bool = False
    shariah_advisory_engaged:  bool = False      # Shariah advisory board already engaged (not a ruling)

    # Dimension 8: Environmental stewardship
    renewable_energy_share:  float = 0.0         # 0–100
    nature_positive:         bool  = False
    climate_risk_disclosure: bool  = False
    biodiversity_plan:       bool  = False

    # Dimension 9: Measurable impact
    emission_reduction_target:    bool = False
    impact_measurement_plan:      bool = False
    baseline_data_available:      bool = False
    independent_verification_plan: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'IslamicFinanceFitInput':
        valid = {f for f in cls.__dataclass_fields__}   # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in valid})


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class IslamicFinanceFitResult:
    """
    Full Islamic & Ethical Finance Fit output.

    Fully serialisable via .to_dict().
    All language uses cautious, indicative framing.
    No religious rulings. No Shariah compliance claims.
    """
    finance_fit_score:   float       # 0–100
    label:               str         # 'weak' | 'possible' | 'strong' | 'high-potential'
    dimension_scores:    dict[str, float]    # all 9 dimension scores

    suitable_instruments:       list[str]   # Instrument types to explore
    sukuk_potential:            str         # 'none' | 'low' | 'moderate' | 'high'
    blended_finance_potential:  str         # 'none' | 'low' | 'moderate' | 'high'

    required_evidence:   list[str]   # What must be established before formal review
    structuring_notes:   list[str]   # Professional structuring considerations
    investor_note:       str         # Investor-facing summary
    sharia_review_note:  str         # Shariah advisory review guidance (no rulings)

    confidence_note:     str   = field(default=(
        'This assessment is indicative only, based on declared project parameters. '
        'It does not constitute a religious ruling, Shariah determination, or '
        'certification of any kind. Formal Islamic finance suitability requires '
        'review by a qualified Shariah scholar or accredited Shariah advisory board.'
    ))
    methodology:         str   = field(default='EcoIQ Islamic & Ethical Finance Fit v1 — rule-based')

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Dimension scorers ─────────────────────────────────────────────────────────

def _score_real_asset(inp: IslamicFinanceFitInput) -> float:
    """
    Dimension 1: Real asset / real economy linkage.

    Sukuk structures require a specific, identifiable underlying asset.
    Project finance and murabaha require a tangible transaction.
    High score = strong asset foundation for structuring.
    """
    score = 15.0   # baseline — any project has some real economy exposure

    if inp.tangible_asset_linked:
        score += 42.0
    if inp.asset_ownership_transferable:
        score += 22.0   # transferable beneficial interest enables sukuk SPV
    if inp.asset_generates_income:
        score += 15.0   # income-generating asset suits Ijara / lease structures

    # Sector bonus: sectors with natural tangible assets
    if inp.sector.lower() in _ASSET_BACKED_SECTORS:
        score += 8.0

    # Scale signal: larger projects have more developed asset documentation
    if inp.budget_usd and inp.budget_usd >= 50_000_000:
        score += 5.0

    return _clamp(score)


def _score_public_benefit(inp: IslamicFinanceFitInput) -> float:
    """
    Dimension 2: Public benefit.

    Islamic finance prioritises projects that create genuine public value.
    Mechanisms: direct jobs, community benefit-sharing, regional development.
    """
    base     = _CB_BASE.get(inp.community_benefit, 35.0)
    jobs_b   = _clamp(min(inp.direct_jobs * 0.06, 12.0))
    local_b  = _clamp(inp.local_procurement_pct * 0.10)
    addl_b   = 8.0 if inp.additionality_demonstrated else 0.0
    share_b  = 5.0 if inp.community_benefit_sharing else 0.0

    return _clamp(base + jobs_b + local_b + addl_b + share_b)


def _score_transparency(inp: IslamicFinanceFitInput) -> float:
    """
    Dimension 3: Transparency of use of proceeds.

    Proceeds must be clearly specified and ring-fenced.
    Ambiguity in deployment creates uncertainty that undermines trust.
    """
    base        = _SPECIFICITY_BASE.get(inp.use_of_proceeds_specificity, 30.0)
    tpv_bonus   = 14.0 if inp.third_party_verified else 0.0
    ring_bonus  = 10.0 if inp.ring_fenced_account else 0.0
    report_b    = 8.0  if inp.reporting_commitment == 'annual' else (4.0 if inp.reporting_commitment == 'bi-annual' else 0.0)

    return _clamp(base + tpv_bonus + ring_bonus + report_b)


def _score_harm_reduction(inp: IslamicFinanceFitInput) -> float:
    """
    Dimension 4: Harm reduction.

    Excluded sectors score zero (hard fail).
    Cautionary sectors score low.
    Projects with active mitigation plans score higher.
    """
    if inp.sector_excluded:
        return 0.0

    base = 55.0   # default for non-excluded projects

    if inp.sector_cautionary or inp.sector.lower() in _IF_CAUTIONARY_SECTORS:
        base = 18.0

    if inp.environmental_assessment:
        base += 22.0
    if inp.pollution_mitigation_plan:
        base += 14.0

    # Renewable energy share as proxy for low harm
    base += _clamp(inp.renewable_energy_share * 0.10)   # max 10 pts

    return _clamp(base)


def _score_uncertainty_avoidance(inp: IslamicFinanceFitInput) -> float:
    """
    Dimension 5: Avoidance of excessive uncertainty (gharar reduction).

    Ambiguous contractual terms, unclear delivery timelines, and speculative
    elements create structural uncertainty that complicates Islamic finance
    structuring. More advanced project stages have lower uncertainty.
    """
    stage_score   = _STAGE_CERTAINTY.get(inp.project_stage, 40.0)
    clarity_score = _CLARITY_BASE.get(inp.contractual_clarity, 45.0)
    perf_bonus    = 12.0 if inp.performance_guarantees else 0.0

    # Proceeds clarity reduces uncertainty about capital deployment
    spec_bonus = {
        'specific': 10.0,
        'general':   3.0,
        'vague':    -8.0,
        'none':    -15.0,
    }.get(inp.use_of_proceeds_specificity, 0.0)

    score = (stage_score * 0.45 + clarity_score * 0.40) + perf_bonus + spec_bonus
    return _clamp(score)


def _score_risk_sharing(inp: IslamicFinanceFitInput) -> float:
    """
    Dimension 6: Fair risk-sharing potential.

    Islamic finance favours profit-and-loss sharing over pure debt.
    Equity or quasi-equity participation aligns with musharakah/mudarabah.
    Fixed-return-only structures (pure debt) score lower but are not excluded
    — many Islamic structures (murabaha, sukuk) provide fixed returns through
    permissible mechanisms.
    """
    if inp.fixed_return_only and not inp.profit_loss_sharing:
        # Conventional fixed-interest debt — lowest compatibility
        return 20.0

    score = 30.0   # base

    if inp.profit_loss_sharing:
        score += 40.0   # P&L sharing is the ideal Islamic finance structure
    if inp.investor_equity_participation:
        score += 20.0   # equity stake aligns with musharakah
    if inp.community_benefit_sharing:
        score += 12.0   # community holds a share = fairness signal

    return _clamp(score)


def _score_governance(inp: IslamicFinanceFitInput) -> float:
    """
    Dimension 7: Governance and accountability.

    Trustworthy governance is foundational to Islamic finance — the principle
    of amanah (trustworthiness) requires transparent structures, disclosed
    ownership, and independent oversight.
    """
    gov_base     = _GOVERNANCE_BASE.get(inp.governance_framework, 18.0)
    ownership_b  = 12.0 if inp.ownership_disclosed else 0.0
    board_b      = 10.0 if inp.independent_board_oversight else 0.0
    # Engagement of Shariah advisory board is a positive structural signal
    # (it does NOT imply compliance — just that a review process is underway)
    shariah_b    = 8.0  if inp.shariah_advisory_engaged else 0.0

    return _clamp(gov_base * 0.70 + ownership_b + board_b + shariah_b)


def _score_environmental_stewardship(inp: IslamicFinanceFitInput) -> float:
    """
    Dimension 8: Environmental stewardship.

    Long-horizon custodianship of natural and human capital.
    High renewable share and positive biodiversity signals score well.
    """
    renewable_b  = _clamp(inp.renewable_energy_share * 0.55)   # max 55
    nature_b     = 18.0 if inp.nature_positive else 0.0
    climate_b    = 14.0 if inp.climate_risk_disclosure else 0.0
    biodiv_b     = 10.0 if inp.biodiversity_plan else 0.0

    return _clamp(renewable_b + nature_b + climate_b + biodiv_b)


def _score_measurable_impact(inp: IslamicFinanceFitInput) -> float:
    """
    Dimension 9: Measurable impact.

    Evidence-based accountability: outcomes must be verifiable.
    All four impact-evidence signals contribute.
    """
    score = 10.0   # base — any project has some outcome intention
    if inp.emission_reduction_target:    score += 25.0
    if inp.impact_measurement_plan:      score += 25.0
    if inp.baseline_data_available:      score += 22.0
    if inp.independent_verification_plan: score += 15.0
    return _clamp(score)


# ── Instrument and potential determination ────────────────────────────────────

def _suitable_instruments(
    inp: IslamicFinanceFitInput,
    dim: dict[str, float],
) -> list[str]:
    """
    Identify instruments potentially suitable for this project profile.
    All items use cautious, conditional language.
    """
    instruments: list[str] = []
    sec = inp.sector.lower()
    excluded = inp.sector_excluded

    if excluded:
        return [
            'Sector is commonly excluded by Islamic and ethical finance frameworks — '
            'standard Islamic finance structuring is not indicated for this project type.'
        ]

    # Green Sukuk (Wakala / Ijara) — primary Islamic capital market instrument
    if (dim['real_asset_linkage'] >= 52
            and dim['transparency_proceeds'] >= 45
            and dim['public_benefit'] >= 40):
        instruments.append(
            'Green Sukuk (Wakala or Ijara structure) — potentially suitable pending '
            'Shariah advisory review and identification of a qualifying underlying asset'
        )

    # Ijara Sukuk — lease-based, ideal for income-generating assets
    if (inp.tangible_asset_linked
            and inp.asset_generates_income
            and inp.asset_ownership_transferable
            and not excluded):
        instruments.append(
            'Ijara Sukuk — lease-based structure potentially applicable where the '
            'underlying asset generates recurring income (e.g. renewable energy plant, '
            'infrastructure facility); requires SPV and AAOIFI-aligned documentation'
        )

    # Istisna Sukuk / construction financing — for projects in early stages
    if (inp.project_type in _ISTISNA_ELIGIBLE_TYPES
            and inp.project_stage in ('feasibility', 'development', 'construction')
            and dim['transparency_proceeds'] >= 38
            and not excluded):
        instruments.append(
            'Istisna financing — construction-phase financing converting to Ijara on '
            'completion; milestone-based drawdowns and progress certificates recommended'
        )

    # Murabaha — cost-plus facility for specific asset acquisition
    if (inp.tangible_asset_linked
            and not excluded
            and not inp.fixed_return_only
            and dim['transparency_proceeds'] >= 42):
        instruments.append(
            'Murabaha facility — cost-plus financing for a defined asset purchase; '
            'requires a clear cost basis, delivery mechanism, and agreed profit margin'
        )

    # Musharakah / Mudarabah — profit-sharing partnerships
    if (inp.profit_loss_sharing
            and not excluded
            and dim['public_benefit'] >= 50):
        instruments.append(
            'Musharakah or Mudarabah — profit-and-loss sharing partnership structure '
            'potentially applicable where investors share in project returns and losses; '
            'requires a clearly defined profit-sharing ratio agreed at outset'
        )

    # Diminishing Musharakah — co-ownership with progressive buyout
    if (inp.investor_equity_participation
            and inp.tangible_asset_linked
            and not excluded):
        instruments.append(
            'Diminishing Musharakah — co-ownership structure with progressive investor '
            'buyout; suitable where the project operator intends to acquire full ownership '
            'over the financing period'
        )

    # IFC / EBRD / ADB Blended Finance
    if (inp.governance_framework in ('IFC', 'EBRD', 'ADB', 'World Bank')
            and dim['public_benefit'] >= 45
            and not excluded):
        instruments.append(
            f'{inp.governance_framework} Blended Finance — development finance co-investment '
            'structure; a first-loss or concessional tranche may de-risk the commercial '
            'and Islamic finance investor tranches'
        )

    # Green Bond (conventional — for broader ethical finance investor base)
    if (dim['transparency_proceeds'] >= 58
            and inp.third_party_verified
            and not excluded
            and dim['environmental_stewardship'] >= 45):
        instruments.append(
            'Green Bond (ICMA Green Bond Principles-aligned) — conventional ethical '
            'finance instrument for investors not requiring Islamic finance structure'
        )

    # Social Impact Bond / Development Finance Facility
    if (dim['public_benefit'] >= 65
            and dim['measurable_impact'] >= 45
            and not excluded):
        instruments.append(
            'Social Impact Bond or Development Finance Facility — impact-first structure '
            'suited to high-benefit projects with quantified, verifiable outcomes'
        )

    # JETP / Climate Transition Finance
    if (inp.renewable_energy_share >= 50
            and dim['public_benefit'] >= 45
            and not excluded):
        instruments.append(
            'Just Energy Transition Partnership (JETP) or Climate Transition Finance — '
            'applicable where the project contributes to national NDC commitments'
        )

    return instruments or [
        'No standard instrument pattern matched — further structuring analysis required. '
        'Engage an Islamic finance advisory team to identify a bespoke structure.'
    ]


def _sukuk_potential(inp: IslamicFinanceFitInput, dim: dict[str, float]) -> str:
    """Qualitative sukuk suitability signal — not a Shariah ruling."""
    if inp.sector_excluded:
        return 'none'
    if (dim['real_asset_linkage'] >= 68
            and dim['transparency_proceeds'] >= 58
            and dim['governance_accountability'] >= 55
            and not inp.sector_excluded):
        return 'high'
    if (dim['real_asset_linkage'] >= 48
            and dim['transparency_proceeds'] >= 42
            and not inp.sector_excluded):
        return 'moderate'
    if dim['real_asset_linkage'] >= 30 and not inp.sector_excluded:
        return 'low'
    return 'none'


def _blended_finance_potential(inp: IslamicFinanceFitInput, dim: dict[str, float]) -> str:
    """Qualitative blended finance potential — development bank lens."""
    if inp.sector_excluded:
        return 'none'
    if (inp.governance_framework in ('IFC', 'EBRD', 'ADB', 'World Bank')
            and dim['public_benefit'] >= 58
            and not inp.sector_excluded):
        return 'high'
    if (inp.governance_framework not in ('none', '')
            and dim['public_benefit'] >= 42
            and not inp.sector_excluded):
        return 'moderate'
    if dim['public_benefit'] >= 35 and not inp.sector_excluded:
        return 'low'
    return 'none'


# ── Narrative builders ────────────────────────────────────────────────────────

def _required_evidence(inp: IslamicFinanceFitInput, dim: dict[str, float]) -> list[str]:
    items: list[str] = []

    if not inp.tangible_asset_linked:
        items.append(
            'Identification and documentation of a specific, identifiable underlying '
            'asset — required for sukuk and most Islamic finance structures'
        )
    if not inp.asset_ownership_transferable:
        items.append(
            'Confirmation that beneficial ownership or usage rights in the asset can '
            'be transferred to investors or an SPV (special purpose vehicle)'
        )
    if dim['transparency_proceeds'] < 58:
        items.append(
            'Detailed use-of-proceeds framework with ring-fenced account and project-level '
            'breakdown — AAOIFI-aligned prospectus documentation recommended'
        )
    if not inp.third_party_verified:
        items.append(
            'Independent second-party opinion or Shariah advisory pre-screening on the '
            'proposed instrument structure'
        )
    if dim['measurable_impact'] < 40:
        items.append(
            'Quantified impact targets with baseline year and independent verification '
            'plan — required for green sukuk and ethical finance labelling'
        )
    if not inp.ownership_disclosed:
        items.append(
            'Beneficial ownership disclosure of the project company and any SPV '
            'in a well-regulated jurisdiction'
        )
    if not inp.environmental_assessment and inp.sector.lower() in _ASSET_BACKED_SECTORS:
        items.append(
            'Environmental Impact Assessment (EIA) aligned with IFC Performance Standards '
            'or EBRD Environmental Policy'
        )
    if inp.fixed_return_only and not inp.profit_loss_sharing:
        items.append(
            'Clarification of the investor return structure — Shariah advisory review '
            'required to determine whether a permissible mechanism (e.g. murabaha margin, '
            'Ijara rental) can substitute for a conventional interest rate'
        )

    return items or [
        'Project appears broadly ready for Islamic finance advisory review. '
        'Standard due diligence and Shariah pre-screening recommended as a next step.'
    ]


def _structuring_notes(
    inp: IslamicFinanceFitInput,
    dim: dict[str, float],
    sukuk: str,
    blended: str,
) -> list[str]:
    notes: list[str] = []

    if sukuk in ('high', 'moderate'):
        if inp.asset_ownership_transferable and inp.asset_generates_income:
            notes.append(
                'Ijara or Wakala sukuk: beneficial interest in the income-generating asset '
                'may be transferred to an SPV, which issues certificates to investors. '
                'Rental or usage fee income is distributed as periodic returns. '
                'Ownership transfers back to the project company at maturity. '
                'AAOIFI Standard 17 (Investment Sukuk) and Standard 18 (Possession) apply.'
            )
        if inp.project_stage in ('feasibility', 'development', 'construction'):
            notes.append(
                'Istisna-to-Ijara forward structure: construction financing under Istisna '
                '(manufacturing / build-to-order contract) converts to Ijara (lease) on '
                'practical completion. Milestone-based drawdowns aligned with construction '
                'progress certificates reduce uncertainty during the build phase.'
            )

    if inp.profit_loss_sharing:
        notes.append(
            'Musharakah or Mudarabah: a profit-and-loss sharing arrangement can align the '
            'instrument with Islamic finance risk-sharing principles. Requires: (i) clearly '
            'defined profit-sharing ratio agreed at inception; (ii) no guaranteed fixed '
            'return; (iii) transparent accounting of project revenues and costs.'
        )

    if blended in ('high', 'moderate') and inp.governance_framework in ('IFC', 'EBRD', 'ADB', 'World Bank'):
        notes.append(
            f'{inp.governance_framework} Blended Finance tranche: a first-loss or '
            'concessional tranche from the development finance institution absorbs '
            'downside risk, improving the risk-return profile for Islamic finance '
            'investors in the senior or mezzanine tranche. This structure is used '
            'in GCC and Central Asian renewable energy projects.'
        )

    if not inp.ring_fenced_account and dim['transparency_proceeds'] < 68:
        notes.append(
            'Ring-fenced proceeds account: establish a dedicated project account with '
            'independent trustee oversight to ensure proceeds are deployed exclusively '
            'to the stated project assets. This strengthens both proceeds transparency '
            'and uncertainty-avoidance signals.'
        )

    if inp.shariah_advisory_engaged:
        notes.append(
            'A Shariah advisory board has been indicated as engaged. This is a positive '
            'structural signal. Ensure advisory engagement covers the full instrument '
            'term sheet, SPV structure, and ongoing Shariah supervisory review — not '
            'only initial pre-screening.'
        )
    else:
        notes.append(
            'Shariah advisory engagement not yet indicated. Before progressing to '
            'formal marketing, engage an accredited Shariah advisory board (AAOIFI- or '
            'IFSB-recognised) to review the proposed instrument structure. '
            'This is a prerequisite for any Islamic finance labelling.'
        )

    return notes or ['Further structuring analysis required — engage an Islamic finance advisory team.']


def _investor_note(score: float, label: str, inp: IslamicFinanceFitInput, dim: dict[str, float]) -> str:
    if inp.sector_excluded:
        return (
            f'This project operates in a sector ({inp.sector}) commonly excluded by Islamic '
            'and ethical finance frameworks. Islamic finance structuring is not indicated '
            'based on current project parameters. Responsible finance consideration may '
            'require fundamental changes to the project scope.'
        )

    if label == 'high-potential':
        return (
            f'This project demonstrates strong structural characteristics for Islamic and '
            f'ethical finance instruments (Finance Fit Score: {score:.0f}/100). '
            'Real asset linkage, use-of-proceeds clarity, and public benefit indicators '
            'are aligned with Islamic finance structuring requirements. '
            'Potential instruments include green sukuk, blended development finance, and '
            'profit-sharing structures. Shariah advisory review and independent verification '
            'are required before formal instrument structuring.'
        )
    if label == 'strong':
        gaps = [
            g for g, cond in [
                ('asset documentation', dim['real_asset_linkage'] < 60),
                ('proceeds transparency', dim['transparency_proceeds'] < 60),
                ('governance framework', dim['governance_accountability'] < 55),
            ] if cond
        ]
        gap_str = f'Specific gaps — {", ".join(gaps)} — should be addressed. ' if gaps else ''
        return (
            f'This project shows a strong fit for Islamic and ethical finance consideration '
            f'(Finance Fit Score: {score:.0f}/100). {gap_str}'
            'Shariah advisory review is recommended before formal instrument structuring. '
            'Blended finance or sukuk structuring is potentially viable.'
        )
    if label == 'possible':
        return (
            f'This project shows partial structural compatibility with Islamic and ethical '
            f'finance frameworks (Finance Fit Score: {score:.0f}/100). '
            'Key conditions — real asset linkage, proceeds specificity, and governance '
            'documentation — would need to be strengthened before a productive Shariah '
            'advisory review. Conventional ethical finance instruments may be accessible '
            'sooner than full Islamic finance structuring.'
        )
    return (
        f"This project's current structure shows limited compatibility with Islamic and "
        f'ethical finance frameworks (Finance Fit Score: {score:.0f}/100). '
        'Material restructuring in asset linkage, proceeds transparency, and governance '
        'is recommended before Islamic finance structuring is considered. '
        'Development finance or conventional green finance may be more immediately accessible.'
    )


def _sharia_review_note(
    score: float,
    label: str,
    inp: IslamicFinanceFitInput,
    dim: dict[str, float],
) -> str:
    """
    Guidance on the Shariah advisory review process.
    This is process guidance — NOT a religious ruling, determination, or fatwa.
    """
    base_caveat = (
        'This assessment is indicative only and does not constitute a religious ruling, '
        'Shariah determination, or certification of any kind. '
        'EcoIQ does not issue religious opinions or Shariah compliance certifications. '
        'All Islamic finance suitability conclusions must be reached by a qualified '
        'Shariah scholar or accredited Shariah advisory board.'
    )

    if inp.sector_excluded:
        return (
            f'This project operates in a sector ({inp.sector}) that is commonly excluded '
            'under Islamic finance screening criteria applied by most Islamic financial '
            'institutions. Progressing to Shariah advisory review is unlikely to be '
            'productive without fundamental changes to the project scope. '
            f'{base_caveat}'
        )

    if inp.sector_cautionary or inp.sector.lower() in _IF_CAUTIONARY_SECTORS:
        return (
            f'This project operates in a sector ({inp.sector}) that is treated as cautionary '
            'under some Islamic finance frameworks. Individual Islamic financial institutions '
            'apply different sector screens — Shariah advisory review should address the '
            'specific project activities and outputs, not only the broad sector label. '
            f'{base_caveat}'
        )

    if label in ('high-potential', 'strong'):
        weak_dims = [
            name.replace('_', ' ') for name, s in dim.items() if s < 50
        ]
        gap_note = (
            f' Key dimensions requiring attention before Shariah review: '
            f'{", ".join(weak_dims)}.' if weak_dims else ''
        )
        return (
            'This project demonstrates structural characteristics that may be compatible '
            'with Islamic finance principles — including real asset linkage, use-of-proceeds '
            'clarity, public benefit orientation, and governance transparency. '
            f'These are structural indicators only, not a Shariah determination.{gap_note} '
            'Recommended next step: engage an AAOIFI- or IFSB-recognised Shariah advisory '
            'board for a formal pre-screening of the proposed instrument structure. '
            f'{base_caveat}'
        )

    if label == 'possible':
        return (
            'This project shows partial structural compatibility with Islamic finance '
            'requirements. Before engaging a Shariah advisory board, we recommend '
            'strengthening: (i) asset documentation and beneficial ownership transfer '
            'mechanism; (ii) use-of-proceeds specificity and ring-fencing; '
            '(iii) governance framework to IFC or AAOIFI-recognised standard. '
            'A Shariah advisory pre-screening at feasibility stage is advisable. '
            f'{base_caveat}'
        )

    return (
        'In its current form, this project\'s structure presents significant challenges '
        'for Islamic finance structuring — particularly in asset linkage and proceeds '
        'transparency. Fundamental restructuring is recommended before engaging a '
        'Shariah advisory board, as an early review on a structurally weak proposal '
        'may generate negative findings that are difficult to reverse. '
        f'{base_caveat}'
    )


# ── Feature vector (ML-ready) ─────────────────────────────────────────────────

def islamic_finance_feature_vector(inp: IslamicFinanceFitInput) -> dict[str, float]:
    """
    Pre-compute a normalised feature vector for future scikit-learn integration.

    All features are floats in [0.0, 100.0].
    Feed directly into StandardScaler → RandomForest / GradientBoosting.

    # ML-HOOK: replace assess_islamic_finance_fit() with:
    #   from joblib import load
    #   clf = load('ml/models/islamic_finance_fit_clf.joblib')
    #   fv  = islamic_finance_feature_vector(inp)
    #   scores = clf.predict([list(fv.values())])[0]  # 9 dimension scores
    """
    cb_base  = _CB_BASE.get(inp.community_benefit, 35.0)
    gov_base = _GOVERNANCE_BASE.get(inp.governance_framework, 18.0)
    spec_base = _SPECIFICITY_BASE.get(inp.use_of_proceeds_specificity, 30.0)
    stage_cert = _STAGE_CERTAINTY.get(inp.project_stage, 40.0)
    clarity_b  = _CLARITY_BASE.get(inp.contractual_clarity, 45.0)

    return {
        # Real asset signals
        'tangible_asset':          100.0 if inp.tangible_asset_linked else 0.0,
        'ownership_transferable':  100.0 if inp.asset_ownership_transferable else 0.0,
        'income_generating':       100.0 if inp.asset_generates_income else 0.0,
        'asset_backed_sector':     100.0 if inp.sector.lower() in _ASSET_BACKED_SECTORS else 0.0,

        # Public benefit
        'community_benefit_base':  cb_base,
        'jobs_score':              _clamp(min(inp.direct_jobs * 0.06, 12.0) * 8.0),
        'local_procurement':       inp.local_procurement_pct,
        'additionality':           100.0 if inp.additionality_demonstrated else 0.0,

        # Transparency
        'specificity_base':        spec_base,
        'third_party_verified':    100.0 if inp.third_party_verified else 0.0,
        'ring_fenced':             100.0 if inp.ring_fenced_account else 0.0,
        'reporting_annual':        100.0 if inp.reporting_commitment == 'annual' else 0.0,

        # Harm
        'sector_excluded':         100.0 if inp.sector_excluded else 0.0,
        'has_eia':                 100.0 if inp.environmental_assessment else 0.0,
        'has_mitigation':          100.0 if inp.pollution_mitigation_plan else 0.0,
        'renewable_share':         inp.renewable_energy_share,

        # Uncertainty
        'stage_certainty':         stage_cert,
        'contractual_clarity':     clarity_b,
        'has_perf_guarantees':     100.0 if inp.performance_guarantees else 0.0,

        # Risk sharing
        'profit_loss_sharing':     100.0 if inp.profit_loss_sharing else 0.0,
        'equity_participation':    100.0 if inp.investor_equity_participation else 0.0,
        'fixed_return_only':       100.0 if inp.fixed_return_only else 0.0,

        # Governance
        'governance_base':         gov_base,
        'ownership_disclosed':     100.0 if inp.ownership_disclosed else 0.0,
        'board_oversight':         100.0 if inp.independent_board_oversight else 0.0,
        'shariah_advisory':        100.0 if inp.shariah_advisory_engaged else 0.0,

        # Stewardship
        'nature_positive':         100.0 if inp.nature_positive else 0.0,
        'climate_disclosure':      100.0 if inp.climate_risk_disclosure else 0.0,
        'biodiversity_plan':       100.0 if inp.biodiversity_plan else 0.0,

        # Impact
        'has_emission_target':     100.0 if inp.emission_reduction_target else 0.0,
        'has_impact_plan':         100.0 if inp.impact_measurement_plan else 0.0,
        'has_baseline':            100.0 if inp.baseline_data_available else 0.0,
        'has_verification_plan':   100.0 if inp.independent_verification_plan else 0.0,

        # Scale
        'budget_log': math.log10(max(inp.budget_usd or 1.0, 1.0)),
    }


# ── Main assessment function ──────────────────────────────────────────────────

def assess_islamic_finance_fit(inp: IslamicFinanceFitInput) -> IslamicFinanceFitResult:
    """
    Rule-based Islamic & Ethical Finance Fit assessment across nine dimensions.

    # ML-HOOK: replace this function body with:
    #   fv = list(islamic_finance_feature_vector(inp).values())
    #   scores = model.predict([fv])[0]   # 9 dimension scores
    #   final  = np.dot(scores, list(DIMENSION_WEIGHTS.values()))
    """
    d1  = _score_real_asset(inp)
    d2  = _score_public_benefit(inp)
    d3  = _score_transparency(inp)
    d4  = _score_harm_reduction(inp)
    d5  = _score_uncertainty_avoidance(inp)
    d6  = _score_risk_sharing(inp)
    d7  = _score_governance(inp)
    d8  = _score_environmental_stewardship(inp)
    d9  = _score_measurable_impact(inp)

    w   = DIMENSION_WEIGHTS
    final = _clamp(
        d1 * w['real_asset_linkage']
        + d2 * w['public_benefit']
        + d3 * w['transparency_proceeds']
        + d4 * w['harm_reduction']
        + d5 * w['uncertainty_avoidance']
        + d6 * w['fair_risk_sharing']
        + d7 * w['governance_accountability']
        + d8 * w['environmental_stewardship']
        + d9 * w['measurable_impact']
    )

    # Hard cap for excluded sectors — regardless of other dimension scores,
    # an excluded sector cannot qualify as 'possible' or above.
    if inp.sector_excluded:
        final = min(final, 37.9)   # ceiling of 'weak' tier

    dim = {
        'real_asset_linkage':        round(d1, 2),
        'public_benefit':            round(d2, 2),
        'transparency_proceeds':     round(d3, 2),
        'harm_reduction':            round(d4, 2),
        'uncertainty_avoidance':     round(d5, 2),
        'fair_risk_sharing':         round(d6, 2),
        'governance_accountability': round(d7, 2),
        'environmental_stewardship': round(d8, 2),
        'measurable_impact':         round(d9, 2),
    }

    label   = _fit_label(final)
    sukuk   = _sukuk_potential(inp, dim)
    blended = _blended_finance_potential(inp, dim)

    return IslamicFinanceFitResult(
        finance_fit_score          = round(final, 2),
        label                      = label,
        dimension_scores           = dim,
        suitable_instruments       = _suitable_instruments(inp, dim),
        sukuk_potential            = sukuk,
        blended_finance_potential  = blended,
        required_evidence          = _required_evidence(inp, dim),
        structuring_notes          = _structuring_notes(inp, dim, sukuk, blended),
        investor_note              = _investor_note(final, label, inp, dim),
        sharia_review_note         = _sharia_review_note(final, label, inp, dim),
    )
