"""
companies/screening.py — deterministic ethical screening classification.

Produces the 4-state result used by the EcoIQ Ethical Screening Badge and
the API's /ethical-screening/ endpoint: passed | review_required | failed |
insufficient_evidence. This is NOT an AI call — it's a transparent rule
table over data EcoIQ already computes (CompanyProfile pillar scores,
harm_penalty, controversy_risk_score, verification status), the same
"deterministic, versioned methodology" pattern used by
investor_portfolio/methodology.py for portfolio exposure scoring.

Islamic screening is handled separately by qdf.scoring (the existing
Quranic Decision Filter engine) — see api/commercial_views.py — and is NOT
duplicated here.
"""
METHODOLOGY_VERSION = 'v1'

STATUS_CHOICES = ('passed', 'review_required', 'failed', 'insufficient_evidence')

# Thresholds are intentionally simple and auditable — a screening result
# must be explainable in one sentence, not a black box.
FAIL_HARM_PENALTY = 20.0          # harm_penalty at/above this -> failed outright
FAIL_CONTROVERSY = 75.0           # controversy_risk_score at/above this -> failed outright
REVIEW_HARM_PENALTY = 8.0
REVIEW_CONTROVERSY = 55.0
REVIEW_POLLUTION_LEVELS = ('high', 'severe')

MIN_DATA_POINTS_FOR_SCREENING = 2  # profile must have at least this many real signals to screen at all


def _has_sufficient_evidence(profile) -> bool:
    """A profile with almost nothing recorded should not be screened either way."""
    signals = 0
    if profile.is_verified:
        signals += 1
    if profile.cited_sources.exists():
        signals += 1
    if profile.pollution_level:
        signals += 1
    if profile.controversy_risk_score not in (None, 30.0):  # 30.0 is the model default, i.e. "not set"
        signals += 1
    return signals >= MIN_DATA_POINTS_FOR_SCREENING


def compute_ethical_screening(profile) -> dict:
    """
    Returns {status, methodology_version, reasons: [str], confidence: 'low'|'medium'|'high'}.
    `profile` is a companies.models.CompanyProfile.
    """
    if not _has_sufficient_evidence(profile):
        return {
            'status': 'insufficient_evidence',
            'methodology_version': METHODOLOGY_VERSION,
            'reasons': ['EcoIQ does not yet hold enough recorded signals to screen this company.'],
            'confidence': 'low',
        }

    reasons = []
    status = 'passed'

    if profile.harm_penalty >= FAIL_HARM_PENALTY:
        status = 'failed'
        reasons.append(f'Harm penalty of {profile.harm_penalty:.1f} pts exceeds the fail threshold.')
    elif profile.controversy_risk_score >= FAIL_CONTROVERSY:
        status = 'failed'
        reasons.append(f'Controversy risk score of {profile.controversy_risk_score:.0f}/100 exceeds the fail threshold.')
    elif profile.harm_penalty >= REVIEW_HARM_PENALTY:
        status = 'review_required'
        reasons.append(f'Harm penalty of {profile.harm_penalty:.1f} pts warrants manual review.')
    elif profile.controversy_risk_score >= REVIEW_CONTROVERSY:
        status = 'review_required'
        reasons.append(f'Controversy risk score of {profile.controversy_risk_score:.0f}/100 warrants manual review.')
    elif profile.pollution_level in REVIEW_POLLUTION_LEVELS:
        status = 'review_required'
        reasons.append(f'Pollution level is classified as "{profile.pollution_level}".')

    if not profile.is_verified:
        reasons.append('Underlying company profile is unverified by EcoIQ.')

    if not reasons:
        reasons.append('No recorded harm, controversy, or pollution signals exceeded screening thresholds.')

    confidence = 'high' if profile.is_verified and profile.cited_sources.exists() else 'medium'

    return {
        'status': status,
        'methodology_version': METHODOLOGY_VERSION,
        'reasons': reasons,
        'confidence': confidence,
    }
