"""
mizan/project.py — Project-level Mizan scoring.

Takes a structured project description and returns a MizanResult
using rule-based logic derived from sector, country, governance
framework, and declared project characteristics.

ML integration note:
  The feature vector produced by `project_feature_vector()` is
  already normalised and ready for scikit-learn integration.
  Replace the rule-based body of `score_project()` with:

      from joblib import load
      clf = load('ml/models/mizan_project_clf.joblib')
      fv  = project_feature_vector(inp)
      dim_scores = clf.predict(list(fv.values()))
      # map dim_scores → MizanResult fields

  once training data (historical project outcomes) is available.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

from mizan.scoring import (
    MizanResult,
    DIMENSION_WEIGHTS,
    _clamp, _mean, _mizan_label,
    _investor_note, _islamic_finance_note,
    _due_diligence_note, _recommended_actions,
)


# ── Lookup tables ─────────────────────────────────────────────────────────────

# Sector → base harm score (0-100). Higher = more harmful baseline.
SECTOR_HARM_BASE: dict[str, float] = {
    'coal_mining':     90.0,
    'oil_gas':         72.0,
    'gas':             65.0,
    'heavy_chemicals': 62.0,
    'cement':          60.0,
    'mining':          55.0,
    'chemical':        52.0,
    'metallurgy':      55.0,
    'steel':           58.0,
    'transport':       42.0,
    'agriculture':     35.0,
    'energy':          30.0,   # modified heavily by renewable_share
    'infrastructure':  25.0,
    'services':        12.0,
    'technology':      10.0,
    'finance':          8.0,
    'renewables':       5.0,
    'other':           30.0,
}

# Country → governance context bonus/penalty (−15 to +12)
COUNTRY_GOVERNANCE_CONTEXT: dict[str, float] = {
    'United Kingdom': 10.0,
    'Germany':        10.0,
    'Norway':         12.0,
    'Sweden':         11.0,
    'Netherlands':     9.0,
    'France':          8.0,
    'Canada':          8.0,
    'Australia':       7.0,
    'Japan':           8.0,
    'Türkiye':         0.0,
    'Kazakhstan':     -5.0,
    'Saudi Arabia':   -3.0,
    'United Arab Emirates': -2.0,
    'India':          -2.0,
    'China':          -8.0,
    'Russia':        -15.0,
}

# Recognised governance framework → base transparency/accountability score
GOVERNANCE_FRAMEWORK_BASE: dict[str, float] = {
    'IFC':         85.0,
    'EBRD':        85.0,
    'ADB':         80.0,
    'World Bank':  80.0,
    'EU Taxonomy': 82.0,
    'GBP':         76.0,    # Green Bond Principles
    'TCFD':        75.0,
    'national':    55.0,
    'none':        30.0,
    '':            30.0,
}

# Community benefit declaration → score contribution
COMMUNITY_BENEFIT_BASE: dict[str, float] = {
    'high':   82.0,
    'medium': 58.0,
    'low':    32.0,
    'none':   10.0,
    '':       32.0,
}


# ── Input dataclass ───────────────────────────────────────────────────────────

@dataclass
class ProjectInput:
    """
    Structured input for project-level Mizan scoring.

    Required: sector
    All other fields are optional with conservative defaults.
    """
    name:                    str            = 'Unnamed Project'
    sector:                  str            = 'other'
    country:                 str            = ''
    project_type:            str            = 'infrastructure'
    description:             str            = ''

    # Scale
    budget_usd:              Optional[float] = None
    duration_years:          Optional[float] = None

    # Environmental profile
    renewable_energy_share:  float = 0.0     # 0 – 100 (% of energy output that is renewable)

    # Social profile
    direct_jobs:             int   = 0
    local_procurement_pct:   float = 0.0     # 0 – 100

    # Governance declarations
    community_benefit:       str   = 'medium'   # high | medium | low | none
    environmental_assessment: bool = False        # EIA conducted
    governance_framework:    str   = 'none'       # IFC | EBRD | ADB | GBP | national | none
    gender_inclusion_plan:   bool  = False
    climate_risk_disclosure: bool  = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ProjectInput':
        valid = {f for f in cls.__dataclass_fields__}   # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in valid})


# ── Feature vector (ML-ready) ─────────────────────────────────────────────────

def project_feature_vector(inp: ProjectInput) -> dict[str, float]:
    """
    Pre-compute a normalised feature vector for future scikit-learn integration.

    All features are floats in range [0.0, 100.0] except log-scale fields.
    Feed directly into StandardScaler → RandomForest / GradientBoosting.
    """
    jobs_per_million = 0.0
    if inp.budget_usd and inp.budget_usd > 0 and inp.direct_jobs > 0:
        jobs_per_million = min(inp.direct_jobs / (inp.budget_usd / 1_000_000.0), 500.0)

    sector_harm = SECTOR_HARM_BASE.get(inp.sector.lower(), 30.0)
    gov_boost   = COUNTRY_GOVERNANCE_CONTEXT.get(inp.country, 0.0)
    gov_score   = GOVERNANCE_FRAMEWORK_BASE.get(inp.governance_framework, 30.0)
    cb_score    = COMMUNITY_BENEFIT_BASE.get(inp.community_benefit, 32.0)

    return {
        'renewable_share':      inp.renewable_energy_share,
        'local_procurement':    inp.local_procurement_pct,
        'community_benefit':    cb_score,
        'has_eia':              100.0 if inp.environmental_assessment else 0.0,
        'has_governance':       100.0 if inp.governance_framework not in ('none', '') else 0.0,
        'gender_inclusion':     100.0 if inp.gender_inclusion_plan else 0.0,
        'climate_disclosure':   100.0 if inp.climate_risk_disclosure else 0.0,
        'jobs_per_million':     min(jobs_per_million * 10, 100.0),  # 10 jobs/M → 100
        'budget_log':           math.log10(max(inp.budget_usd or 1.0, 1.0)),
        'sector_harm_base':     sector_harm,
        'country_gov_boost':    gov_boost + 50.0,    # centre on 50 for ML
        'governance_score':     gov_score,
    }


# ── Project scorer ─────────────────────────────────────────────────────────────

def score_project(inp: ProjectInput) -> MizanResult:
    """
    Rule-based project Mizan scoring.

    # ML-HOOK: replace this function with a sklearn model call:
    #   fv = list(project_feature_vector(inp).values())
    #   scores = model.predict([fv])[0]  # 6 dimension scores
    #   final  = np.dot(scores, list(DIMENSION_WEIGHTS.values()))
    """
    fv = project_feature_vector(inp)

    sector_lower   = inp.sector.lower()
    gov_score      = fv['governance_score']
    cb_score       = fv['community_benefit']
    country_boost  = COUNTRY_GOVERNANCE_CONTEXT.get(inp.country, 0.0)

    # ── 1. Public Benefit ─────────────────────────────────────────────────────
    jobs_score  = _clamp(fv['jobs_per_million'])
    local_score = inp.local_procurement_pct
    pb = _clamp(
        jobs_score   * 0.35
        + local_score * 0.30
        + cb_score    * 0.35
    )

    # ── 2. Harm Reduction ─────────────────────────────────────────────────────
    sector_harm = fv['sector_harm_base']

    # Renewable share mitigates energy sector harm
    if sector_lower in ('energy', 'renewables', 'infrastructure', 'transport'):
        renewable_discount = (inp.renewable_energy_share / 100.0) * 0.65
        sector_harm = _clamp(sector_harm * (1 - renewable_discount))

    eia_bonus = 10.0 if inp.environmental_assessment else 0.0
    hr = _clamp(100.0 - sector_harm + eia_bonus)

    # ── 3. Justice & Fair Distribution ────────────────────────────────────────
    gender_bonus = 5.0 if inp.gender_inclusion_plan else 0.0
    local_bonus  = inp.local_procurement_pct * 0.25
    jd = _clamp(
        gov_score     * 0.45
        + cb_score    * 0.30
        + local_bonus
        + gender_bonus
        + country_boost
    )

    # ── 4. Transparency & Accountability ──────────────────────────────────────
    eia_score  = 75.0 if inp.environmental_assessment else 20.0
    climate_d  = 15.0 if inp.climate_risk_disclosure else 0.0
    ta = _clamp(eia_score * 0.40 + gov_score * 0.45 + climate_d)

    # ── 5. Stewardship ────────────────────────────────────────────────────────
    duration_signal = _clamp((inp.duration_years or 3.0) * 6.0)  # years × 6, capped at 100
    st = _clamp(
        inp.renewable_energy_share * 0.35
        + duration_signal          * 0.25
        + cb_score                 * 0.25
        + (15.0 if inp.environmental_assessment else 0.0)
    )

    # ── 6. Evidence Confidence ────────────────────────────────────────────────
    ec = 35.0   # base: model estimate
    if inp.environmental_assessment:  ec += 15.0
    if inp.governance_framework not in ('none', ''): ec += 15.0
    if inp.climate_risk_disclosure:   ec += 10.0
    ec = _clamp(ec)
    confidence = 'model-estimate'

    # ── Weighted final score ──────────────────────────────────────────────────
    w = DIMENSION_WEIGHTS
    final = _clamp(
        pb * w['public_benefit']
        + hr * w['harm_reduction']
        + jd * w['justice_distribution']
        + ta * w['transparency_accountability']
        + st * w['stewardship']
        + ec * w['evidence_confidence']
    )

    # ── Risk flags ────────────────────────────────────────────────────────────
    flags: list[str] = []
    if sector_lower in ('coal_mining', 'oil_gas'):
        flags.append('High-carbon sector — enhanced decarbonisation commitments required')
    if not inp.environmental_assessment:
        flags.append('No environmental impact assessment declared')
    if inp.governance_framework in ('none', ''):
        flags.append('No recognised governance framework applied')
    if inp.renewable_energy_share < 20 and sector_lower == 'energy':
        flags.append('Low renewable energy share for an energy sector project')
    if pb < 40:
        flags.append('Insufficient public benefit evidence provided')
    if jd < 40:
        flags.append('Justice & distribution gap — local community benefit unclear')
    # Always include this for project-model scores
    flags.append('Project scoring is indicative — independent ESIA is required')

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
        data_source                        = 'project_model',
        confidence                         = confidence,
    )
