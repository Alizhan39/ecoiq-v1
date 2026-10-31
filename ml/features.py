"""
ml/features.py — Feature extraction for EcoIQ ML pipeline.

Pulls from both league.Company (base model) and companies.CompanyProfile
(pillar scores). Returns a dict suitable for model input.
"""
from __future__ import annotations

import math
import numpy as np


POLLUTION_LEVEL_MAP = {
    'none':     0,
    'low':      1,
    'medium':   2,
    'high':     3,
    'critical': 4,
}

SECTOR_MAP = {
    'energy':        0,
    'mining':        1,
    'manufacturing': 2,
    'transport':     3,
    'agriculture':   4,
    'finance':       5,
    'technology':    6,
    'retail':        7,
    'healthcare':    8,
    'construction':  9,
    'utilities':    10,
    'telecom':      11,
    'media':        12,
    'other':        13,
}


# ── Missingness and the trained model ────────────────────────────────────────
#
# READ THIS BEFORE CHANGING _safe_float OR ANY FEATURE DEFINITION.
#
# The estimator is a scikit-learn GradientBoostingRegressor loaded from a
# COMMITTED artefact (ml/models/scoring_gbr.joblib, with scoring_scaler.joblib).
# Two consequences follow, and they pull in opposite directions:
#
#   1. GBR.predict() requires a dense float matrix. It cannot accept None or
#      NaN. sklearn's HistGradientBoosting can; this estimator cannot.
#
#   2. The scaler's means and variances, and every split the trees learned, were
#      fitted on a matrix in which missing values were ALREADY 50.0. Changing
#      what a feature means — including making its missingness explicit — would
#      silently invalidate the fitted artefact, because the model would receive
#      a distribution it was never trained on.
#
# So the vector is NOT changed here, and `_safe_float` keeps its behaviour
# exactly. That is a deliberate decision, not an oversight: correcting the
# imputation would require retraining, and inventing a statistical imputation
# methodology is out of scope for this change.
#
# What changes instead is the BOUNDARY. `missing_material_features()` reports,
# separately from the vector, which material inputs are unknown, and
# EcoIQScoringModel.predict_company() refuses before predicting rather than
# feeding a 50 the model will read as an average company. Fail closed at the
# gate; leave the trained artefact's contract untouched.
#
# The correct long-term fix is one of:
#   A. retrain on nullable inputs with a missingness-aware estimator, or
#   B. retrain with explicit `<feature>_missing` indicator columns.
# Both need a retraining pass, and neither belongs in a semantics PR.


def _safe_float(value, default=50.0) -> float:
    """
    Return float or default if None / NaN.

    The 50.0 default is a TRAINING-TIME ARTEFACT, not a claim that an unmeasured
    company is average. See the note above: it is preserved on purpose so the
    committed model receives the input distribution it was fitted on. Callers
    must consult `missing_material_features()` to learn what is actually known.
    """
    try:
        v = float(value)
        return default if math.isnan(v) else v
    except (TypeError, ValueError):
        return default


def _safe_log(value, default=0.0) -> float:
    """log10 of positive value, or default."""
    try:
        v = float(value)
        return math.log10(v) if v > 0 else default
    except (TypeError, ValueError):
        return default


def extract_features(company) -> dict:
    """
    Extract a flat feature dict from a league.Company instance.

    Accesses profile via company.profile (OneToOne to companies.CompanyProfile).
    Returns floats/ints only — suitable for numpy conversion.
    """
    profile = getattr(company, 'profile', None)

    # ── Base league.Company scores ────────────────────────────────────────
    pollution_fp = _safe_float(company.score_pollution_footprint)
    reduction    = _safe_float(company.score_reduction_progress)
    investment   = _safe_float(company.score_investment)
    transparency = _safe_float(company.score_transparency)
    community    = _safe_float(company.score_community_impact)

    # ── CompanyProfile pillar scores ──────────────────────────────────────
    if profile:
        pb_score      = _safe_float(profile.public_benefit_score)
        env_score     = _safe_float(profile.environmental_responsibility_score)
        modern_score  = _safe_float(profile.modernization_score)
        transp_score  = _safe_float(profile.transparency_anti_corruption_score)
        ethical_score = _safe_float(profile.ethical_alignment_score)
        anti_corr     = _safe_float(profile.anti_corruption_score)
        harm_penalty  = _safe_float(profile.harm_penalty, default=0.0)

        # Pollution level → ordinal integer
        poll_level_raw = getattr(profile, 'pollution_level', 'medium') or 'medium'
        poll_level = POLLUTION_LEVEL_MAP.get(poll_level_raw.lower(), 2)

        # Sub-pillar scores where available
        waste_mgmt   = _safe_float(getattr(profile, 'waste_management_score', None))
        water_impact = _safe_float(getattr(profile, 'water_impact_score', None))
        biodiv       = _safe_float(getattr(profile, 'biodiversity_impact_score', None))
        energy_trans = _safe_float(getattr(profile, 'energy_transition_score', None))
        digital      = _safe_float(getattr(profile, 'digitalization_score', None))
        future_rdns  = _safe_float(getattr(profile, 'future_readiness_score', None))
        audit_qual   = _safe_float(getattr(profile, 'audit_quality_score', None))
        controversy  = _safe_float(getattr(profile, 'controversy_risk_score', 30.0))

        employees    = profile.employees or company.employee_count
        annual_rev   = profile.annual_revenue or company.annual_revenue_usd
    else:
        pb_score = env_score = modern_score = transp_score = ethical_score = 50.0
        anti_corr = harm_penalty = 0.0
        poll_level = 2
        waste_mgmt = water_impact = biodiv = energy_trans = digital = 50.0
        future_rdns = audit_qual = 50.0
        controversy = 30.0
        employees  = company.employee_count
        annual_rev = company.annual_revenue_usd

    # ── Evidence coverage (derived): fraction of pillar scores != 50.0 ────
    # This feature INFERS missingness from the value being 50 — the exact
    # conflation the D-programme removes everywhere else. It is left untouched
    # because it is a fitted model input: changing its definition would shift
    # the distribution the committed artefact was trained on. Superseded by
    # missing_material_features() everywhere outside the vector.
    pillar_vals   = [pollution_fp, reduction, investment, transparency, community]
    evidence_cov  = sum(1 for v in pillar_vals if abs(v - 50.0) > 5) / max(len(pillar_vals), 1)

    # ── Historical score variance (derived from ScoreHistory) ─────────────
    try:
        history_scores = list(
            company.history.order_by('-date').values_list('ecoiq_score', flat=True)[:12]
        )
        if len(history_scores) >= 2:
            score_variance = float(np.var([float(s) for s in history_scores]))
            score_trend    = float(history_scores[0]) - float(history_scores[-1])
        else:
            score_variance = 0.0
            score_trend    = 0.0
    except Exception:
        score_variance = 0.0
        score_trend    = 0.0

    # ── Company meta ──────────────────────────────────────────────────────
    sector_enc = SECTOR_MAP.get((company.sector or 'other').lower(), 13)
    is_public  = 1 if company.is_public else 0
    verified   = 1 if company.verified else 0
    emp_log    = _safe_log(employees)
    rev_log    = _safe_log(annual_rev)

    return {
        # Base pillar scores (league)
        'score_pollution_footprint': pollution_fp,
        'score_reduction_progress':  reduction,
        'score_investment':          investment,
        'score_transparency':        transparency,
        'score_community_impact':    community,

        # Profile pillar scores
        'public_benefit_score':               pb_score,
        'environmental_responsibility_score': env_score,
        'modernization_score':                modern_score,
        'transparency_anti_corruption_score': transp_score,
        'ethical_alignment_score':            ethical_score,
        'anti_corruption_score':              anti_corr,
        'harm_penalty':                       harm_penalty,

        # Sub-pillar
        'waste_management_score':      waste_mgmt,
        'water_impact_score':          water_impact,
        'biodiversity_impact_score':   biodiv,
        'energy_transition_score':     energy_trans,
        'digitalization_score':        digital,
        'future_readiness_score':      future_rdns,
        'audit_quality_score':         audit_qual,
        'controversy_risk_score':      controversy,

        # Environmental / operational
        'pollution_level_enc':         float(poll_level),

        # Derived
        'evidence_coverage':           evidence_cov,
        'score_variance':              score_variance,
        'score_trend':                 score_trend,

        # Meta
        'sector_enc':                  float(sector_enc),
        'is_public':                   float(is_public),
        'verified':                    float(verified),
        'employee_count_log':          emp_log,
        'annual_revenue_log':          rev_log,
    }


FEATURE_NAMES = list(extract_features.__doc__ and [] or [])  # populated at import


def get_feature_names() -> list[str]:
    """Return the ordered list of feature names (requires a dummy call)."""
    # Use fixed canonical order
    return [
        'score_pollution_footprint',
        'score_reduction_progress',
        'score_investment',
        'score_transparency',
        'score_community_impact',
        'public_benefit_score',
        'environmental_responsibility_score',
        'modernization_score',
        'transparency_anti_corruption_score',
        'ethical_alignment_score',
        'anti_corruption_score',
        'harm_penalty',
        'waste_management_score',
        'water_impact_score',
        'biodiversity_impact_score',
        'energy_transition_score',
        'digitalization_score',
        'future_readiness_score',
        'audit_quality_score',
        'controversy_risk_score',
        'pollution_level_enc',
        'evidence_coverage',
        'score_variance',
        'score_trend',
        'sector_enc',
        'is_public',
        'verified',
        'employee_count_log',
        'annual_revenue_log',
    ]


# Inputs whose absence makes a prediction a statement about nothing. Not every
# feature: the model tolerates a missing employee count, but it cannot say
# anything meaningful about a company whose pillar scores are all unknown.
MATERIAL_FEATURE_SOURCES: tuple[str, ...] = (
    'public_benefit_score',
    'environmental_responsibility_score',
    'modernization_score',
    'transparency_anti_corruption_score',
    'ethical_alignment_score',
    'anti_corruption_score',
)


def missing_material_features(company) -> list[str]:
    """
    Material model inputs that are UNKNOWN for this company.

    Reported separately from the feature vector, because the vector must keep
    the shape and imputation the committed artefact was fitted on (see the note
    at the top of this module). This is how a caller learns the difference
    between "the model saw 50" and "we do not know", which the vector itself can
    no longer express.

    Empty list means every material input is known.
    """
    profile = getattr(company, 'profile', None)
    if profile is None:
        return list(MATERIAL_FEATURE_SOURCES)
    return [
        name for name in MATERIAL_FEATURE_SOURCES
        if getattr(profile, name, None) is None
    ]


def company_to_vector(company) -> np.ndarray:
    """
    Extract features and return as numpy array in canonical order.

    Missing values become 50.0 — deliberately, to match the fitted artefact.
    Check missing_material_features() BEFORE calling this if the result will be
    presented as a finding about the company.
    """
    feats = extract_features(company)
    names = get_feature_names()
    return np.array([feats.get(n, 50.0) for n in names], dtype=np.float64)
