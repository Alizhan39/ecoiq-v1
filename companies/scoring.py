"""
EcoIQ Ethical Innovation Scoring Engine.

Calculates a company's EcoIQ Total Score (0-100) from six dimensions:

  Public Benefit            × 0.25
  Environmental Stewardship × 0.25
  Responsible Modernization × 0.20
  Transparent Governance    × 0.15
  Anti-Corruption           × 0.10
  Ethical Alignment         × 0.05
  — Harm Penalty

Profit Extraction Score is a standalone risk indicator only.
It does NOT contribute to the total — it warns.

Moral Labels:
  85–100  Regenerative Leader
  70–84   Responsible Builder
  60–69   Public-Benefit Oriented
  50–59   Transitional Company
  30–49   Profit-First Operator
  0–29    Extractive / Harmful
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from companies.models import CompanyProfile


# ── Pillar calculators ─────────────────────────────────────────────────────────

def _clamp(v, lo=0.0, hi=100.0) -> float:
    return max(lo, min(hi, float(v or 0)))


def _avg(*values) -> float:
    filtered = [_clamp(v) for v in values if v is not None]
    return sum(filtered) / len(filtered) if filtered else 50.0


def _pollution_to_env_base(pollution_level: str) -> float:
    """Convert categorical pollution level to a 0-100 base score."""
    return {'low': 85.0, 'medium': 60.0, 'high': 30.0, 'severe': 10.0}.get(
        pollution_level, 50.0
    )


def calculate_public_benefit(p: 'CompanyProfile') -> float:
    """0-100: How much the company generates tangible public benefit."""
    return _avg(
        p.jobs_created_score,
        p.regional_development_score,
        p.infrastructure_contribution_score,
        p.national_value_score,
    )


def calculate_environmental_responsibility(p: 'CompanyProfile') -> float:
    """0-100: Quality of environmental stewardship across all dimensions."""
    pollution_base = _pollution_to_env_base(p.pollution_level)
    return _avg(
        pollution_base,
        p.waste_management_score,
        p.water_impact_score,
        p.biodiversity_impact_score,
    )


def calculate_modernization(p: 'CompanyProfile') -> float:
    """0-100: Commitment to responsible modernization and future readiness."""
    return _avg(
        p.energy_transition_score,
        p.digitalization_score,
        p.infrastructure_upgrade_score,
        p.future_readiness_score,
    )


def calculate_transparency(p: 'CompanyProfile') -> float:
    """0-100: Governance quality and transparency of operations."""
    return (
        _clamp(p.transparency_score_detail)  * 0.40 +
        _clamp(p.audit_quality_score)        * 0.35 +
        _clamp(p.procurement_transparency_score) * 0.25
    )


def calculate_anti_corruption(p: 'CompanyProfile') -> float:
    """0-100: Anti-corruption practices and ethical procurement."""
    return _clamp(p.anti_corruption_score)


def calculate_ethical_alignment(p: 'CompanyProfile') -> float:
    """
    0-100: Alignment with long-term ethical value creation.
    High controversy risk and low national value reduce this score.
    """
    inv_controversy = _clamp(100.0 - _clamp(p.controversy_risk_score))
    return _avg(inv_controversy, p.national_value_score)


# ── Harm penalty ───────────────────────────────────────────────────────────────

def calculate_harm_penalty(p: 'CompanyProfile') -> float:
    """
    Deduction applied when a company causes significant harm
    without adequate mitigation or transparency.
    """
    penalty = 0.0

    # Pollution severity
    if p.pollution_level == 'severe':
        penalty += 15.0
    elif p.pollution_level == 'high':
        penalty += 8.0

    # High controversy without remediation
    if _clamp(p.controversy_risk_score) >= 70:
        penalty += 5.0

    # Opacity — very low transparency
    if _clamp(p.transparency_score_detail) < 30:
        penalty += 5.0

    # Profit extraction without public benefit
    if (
        _clamp(p.profit_extraction_score) > 75 and
        _clamp(p.public_benefit_score) < 50
    ):
        penalty += 5.0

    # Severe pollution + no modernization = high transition need penalty
    if p.pollution_level in ('high', 'severe') and _clamp(p.modernization_score) < 40:
        penalty += 3.0

    return min(penalty, 30.0)  # cap penalty at 30 points


# ── Main scoring entry point ───────────────────────────────────────────────────

def compute_ecoiq_profile_score(p: 'CompanyProfile') -> dict:
    """
    Compute all six EcoIQ dimensions + penalty + total score.
    Returns a dict of results — does NOT save to the model.
    Caller is responsible for calling profile.save() after applying results.
    """
    pb  = calculate_public_benefit(p)
    env = calculate_environmental_responsibility(p)
    mod = calculate_modernization(p)
    trn = calculate_transparency(p)
    ac  = calculate_anti_corruption(p)
    eth = calculate_ethical_alignment(p)

    base = (
        pb  * 0.25 +
        env * 0.25 +
        mod * 0.20 +
        trn * 0.15 +
        ac  * 0.10 +
        eth * 0.05
    )

    penalty = calculate_harm_penalty(p)
    total   = round(_clamp(base - penalty), 1)
    label   = get_moral_label(total)

    return {
        'public_benefit_score':              round(pb, 1),
        'environmental_responsibility_score': round(env, 1),
        'modernization_score':               round(mod, 1),
        'transparency_anti_corruption_score':round(trn, 1),
        'anti_corruption_score':             round(ac, 1),
        'ethical_alignment_score':           round(eth, 1),
        'ecoiq_total_score':                 total,
        'moral_label':                       label,
        'ecoiq_category':                    get_ecoiq_category(total),
        'harm_penalty':                      round(penalty, 1),
        '_base_score':                       round(base, 1),
    }


def recalculate_and_save(profile: 'CompanyProfile') -> 'CompanyProfile':
    """
    Compute EcoIQ scores, apply to profile fields, and save.
    Returns the updated profile instance.
    """
    results = compute_ecoiq_profile_score(profile)

    profile.public_benefit_score               = results['public_benefit_score']
    profile.environmental_responsibility_score = results['environmental_responsibility_score']
    profile.modernization_score                = results['modernization_score']
    profile.transparency_anti_corruption_score = results['transparency_anti_corruption_score']
    profile.ethical_alignment_score            = results['ethical_alignment_score']
    profile.harm_penalty                       = results['harm_penalty']
    profile.ecoiq_total_score                  = results['ecoiq_total_score']
    profile.moral_label                        = results['moral_label']
    profile.ecoiq_category                     = results['ecoiq_category']

    profile.save(update_fields=[
        'public_benefit_score', 'environmental_responsibility_score',
        'modernization_score', 'transparency_anti_corruption_score',
        'ethical_alignment_score', 'harm_penalty', 'ecoiq_total_score',
        'moral_label', 'ecoiq_category', 'updated_at',
    ])
    return profile


# ── Label helpers ──────────────────────────────────────────────────────────────

def get_moral_label(score: float) -> str:
    """Return canonical moral_label key for storage."""
    if score >= 85: return 'regenerative_leader'
    if score >= 70: return 'responsible_builder'
    if score >= 60: return 'public_benefit_oriented'
    if score >= 50: return 'transitional_company'
    if score >= 30: return 'profit_first_operator'
    return 'extractive_harmful'


def get_moral_label_display(score: float) -> str:
    """Return human-readable moral label."""
    labels = {
        'regenerative_leader':    'Regenerative Leader',
        'responsible_builder':    'Responsible Builder',
        'public_benefit_oriented':'Public-Benefit Oriented',
        'transitional_company':   'Transitional Company',
        'profit_first_operator':  'Profit-First Operator',
        'extractive_harmful':     'Extractive / Harmful',
    }
    return labels.get(get_moral_label(score), 'Unknown')


def get_ecoiq_category(score: float) -> str:
    if score >= 85: return 'Exceptional'
    if score >= 70: return 'Strong'
    if score >= 60: return 'Moderate'
    if score >= 50: return 'Fair'
    if score >= 30: return 'Below Average'
    return 'Critical'


def get_moral_label_color(label_key: str) -> str:
    colours = {
        'regenerative_leader':    '#00e89a',
        'responsible_builder':    '#58a6ff',
        'public_benefit_oriented':'#8b5cf6',
        'transitional_company':   '#f4a261',
        'profit_first_operator':  '#e63946',
        'extractive_harmful':     '#b91c1c',
    }
    return colours.get(label_key, '#888')


# ── Path-to-100 advisor ────────────────────────────────────────────────────────

def get_path_to_100_actions(profile: 'CompanyProfile') -> list[dict]:
    """
    Return a prioritised list of improvement actions that would most
    increase EcoIQ score. Used for the 'Path to 100%' section.
    """
    actions = []

    def _add(title, description, potential_gain, pillar):
        actions.append({
            'title': title,
            'description': description,
            'potential_gain': potential_gain,
            'pillar': pillar,
        })

    if profile.pollution_level in ('high', 'severe'):
        _add(
            'Reduce Pollution Intensity',
            'Invest in filtration, emissions controls, and cleaner processes '
            'to move from high/severe to medium pollution classification.',
            10 if profile.pollution_level == 'severe' else 6,
            'Environmental Stewardship',
        )

    if _clamp(profile.transparency_score_detail) < 60:
        _add(
            'Improve Public Reporting',
            'Publish an annual sustainability/ESG report aligned with GRI or CDP '
            'standards to boost transparency and investor confidence.',
            7, 'Transparent Governance',
        )

    if _clamp(profile.energy_transition_score) < 50:
        _add(
            'Accelerate Energy Transition',
            'Develop a renewable energy integration plan and set measurable '
            'interim targets for clean energy share.',
            6, 'Responsible Modernization',
        )

    if _clamp(profile.anti_corruption_score) < 60:
        _add(
            'Strengthen Anti-Corruption Controls',
            'Implement ISO 37001 anti-bribery management system and independent '
            'procurement audits.',
            5, 'Anti-Corruption',
        )

    if _clamp(profile.jobs_created_score) < 60:
        _add(
            'Invest in Quality Employment',
            'Create formal workforce development programmes and community '
            'hiring initiatives to increase regional employment quality.',
            4, 'Public Benefit',
        )

    if _clamp(profile.future_readiness_score) < 50:
        _add(
            'Build Future Readiness',
            'Commission a technology modernization audit and develop a '
            'five-year digital transformation roadmap.',
            4, 'Responsible Modernization',
        )

    if _clamp(profile.biodiversity_impact_score) < 50:
        _add(
            'Address Biodiversity Impact',
            'Conduct a biodiversity impact assessment and commit to '
            'nature-positive operational practices.',
            3, 'Environmental Stewardship',
        )

    # Sort by highest potential gain
    actions.sort(key=lambda x: x['potential_gain'], reverse=True)
    return actions[:7]
