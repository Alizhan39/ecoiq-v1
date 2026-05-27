"""
EcoIQ Ethical Intelligence Scoring Engine.

Three Master Formulas (public-facing):
  NEI  Net Ethical Impact          — does this company create more than it destroys?
  TSS  Transition Stewardship Score — is this company actively reducing harm over time?
  RVI  Regenerative Value Index    — is this company building lasting societal value?

These compress a 33-formula internal framework into three investor-grade lenses.
All computations use existing CompanyProfile field values as inputs.
No additional data collection is required.

Maqasid mapping is internal / methodology-level only.
Do NOT expose maqasid terminology in public-facing copy.
Use: stewardship, balance, public benefit, long-term resilience, ethical intelligence.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from companies.models import CompanyProfile
    from ethics.models import CompanyEthicsProfile

import logging
log = logging.getLogger('ethics.scoring')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clamp(v, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v or 0)))


_POLLUTION_HARM = {'low': 8, 'medium': 25, 'high': 55, 'severe': 80}
_POLLUTION_DISC = {'low': +4, 'medium': 0,  'high': -8, 'severe': -16}


# ── Master Formula A: Net Ethical Impact ──────────────────────────────────────

def compute_net_ethical_impact(
    profile: 'CompanyProfile',
) -> tuple[float, float, float]:
    """
    NEI = Total_Benefit  −  (Total_Harm × 0.30)

    Benefit (0-100): equal-weighted average of the 6 EcoIQ pillars.
    Harm    (0-100): weighted composite of pollution severity,
                     controversy risk, and opacity penalty.

    Returns (nei, total_benefit, total_harm) all clamped to 0-100.

    Preservation links (internal):
      Benefit pillars → society, intellect, wealth, trust
      Pollution harm  → life
      Opacity harm    → intellect
      Controversy     → trust
    """
    benefits = [
        _clamp(profile.public_benefit_score),
        _clamp(profile.environmental_responsibility_score),
        _clamp(profile.modernization_score),
        _clamp(profile.transparency_anti_corruption_score),
        _clamp(profile.anti_corruption_score),
        _clamp(profile.ethical_alignment_score),
    ]
    total_benefit = sum(benefits) / len(benefits)

    pollution_harm   = _POLLUTION_HARM.get(profile.pollution_level, 25)
    controversy_harm = _clamp(profile.controversy_risk_score or 0)
    opacity_harm     = _clamp(
        (50.0 - _clamp(profile.transparency_score_detail or 50.0)) * 2
    )

    total_harm = (
        pollution_harm   * 0.50 +
        controversy_harm * 0.30 +
        opacity_harm     * 0.20
    )

    # Harm can reduce NEI by at most 30 points
    nei = _clamp(total_benefit - total_harm * 0.30)
    return round(nei, 1), round(total_benefit, 1), round(total_harm, 1)


# ── Master Formula B: Transition Stewardship Score ────────────────────────────

def compute_transition_stewardship(profile: 'CompanyProfile') -> float:
    """
    TSS = (Restoration + Modernization + Efficiency + Transparency) / 4
          adjusted by harm burden and modernization momentum.

    Distinguishes between:
    - Static high-impact operators (low TSS)
    - Companies in genuine modernization transition (higher TSS)

    A high-polluter actively investing in transition can score higher
    on TSS than a low-polluter that is stagnant.

    Preservation links (internal):
      Restoration  → life, society
      Modernization → wealth, intellect
      Efficiency   → wealth
      Transparency → trust, intellect
    """
    restoration   = _clamp(profile.environmental_responsibility_score)
    modernization = _clamp(profile.modernization_score)
    efficiency    = (
        _clamp(profile.energy_transition_score) +
        _clamp(profile.future_readiness_score)
    ) / 2
    transparency  = _clamp(profile.transparency_anti_corruption_score)

    base = (restoration + modernization + efficiency + transparency) / 4

    # Harm burden adjustment
    if   profile.pollution_level == 'severe': adjustment = -12
    elif profile.pollution_level == 'high':   adjustment =  -6
    elif profile.pollution_level == 'low':    adjustment =  +3
    else:                                     adjustment =   0

    # Controversy burden
    if (profile.controversy_risk_score or 0) >= 70:
        adjustment -= 4

    # Modernization momentum bonus (reward genuine transition effort)
    if modernization >= 70:
        adjustment += 5
    elif modernization >= 55:
        adjustment += 2

    return round(_clamp(base + adjustment), 1)


# ── Master Formula C: Regenerative Value Index ────────────────────────────────

def compute_regenerative_value(profile: 'CompanyProfile') -> float:
    """
    RVI = Weighted future societal value creation,
          discounted by pollution burden, rewarded for transparency.

    Forward-looking metric: measures the lasting value a company
    creates for communities, ecosystems, and future generations —
    relative to the resources and environment it consumes.

    High RVI companies create durable infrastructure, employment
    quality, knowledge systems, and ecosystem resilience.

    Preservation links (internal):
      National value, regional dev → society, wealth
      Future readiness, digital    → intellect, wealth
      Ethical alignment            → trust
      Jobs quality                 → society, life
      Biodiversity                 → life
    """
    future_value = (
        _clamp(profile.national_value_score)            * 0.22 +
        _clamp(profile.regional_development_score)      * 0.18 +
        _clamp(profile.future_readiness_score)          * 0.18 +
        _clamp(profile.ethical_alignment_score)         * 0.15 +
        _clamp(profile.jobs_created_score)              * 0.12 +
        _clamp(profile.biodiversity_impact_score)       * 0.10 +
        _clamp(profile.infrastructure_contribution_score) * 0.05
    )

    # Pollution burden discount / premium
    pollution_adj = _POLLUTION_DISC.get(profile.pollution_level, 0)

    # Transparency disclosure premium
    trans = _clamp(profile.transparency_score_detail)
    disclosure_bonus = 3.0 if trans >= 70 else (1.0 if trans >= 50 else 0.0)

    rvi = _clamp(future_value + pollution_adj + disclosure_bonus)
    return round(rvi, 1)


# ── KPI Improvement Opportunities ────────────────────────────────────────────

def generate_improvement_opportunities(profile: 'CompanyProfile') -> list[dict]:
    """
    Return a prioritised list of evidence-based KPI improvement opportunities,
    each mapped to a formula category, pillar, expected score gain,
    effort level, timeline, and measurable KPI metric.

    Each opportunity links internally to a Maqasid preservation principle
    but this mapping is NOT exposed in public-facing copy.
    """
    opps: list[dict] = []

    def _add(title, desc, cat, pillar, gain, effort, months, kpi, maqasid=''):
        opps.append({
            'title':               title,
            'description':         desc,
            'formula_category':    cat,
            'pillar':              pillar,
            'expected_score_gain': gain,
            'effort_level':        effort,
            'timeline_months':     months,
            'kpi_metric':          kpi,
            'maqasid_principle':   maqasid,
        })

    p = profile.pollution_level

    # ── Environmental Balance ──────────────────────────────────────────────────
    if p in ('high', 'severe'):
        gain = 12 if p == 'severe' else 7
        _add('Reduce Pollution Intensity',
             'Deploy filtration, emission controls, and cleaner production processes '
             'to move from high/severe to medium classification. Quantify and report '
             'emissions reductions with verified measurement data.',
             'environmental_balance', 'Environmental Stewardship', gain,
             'high', 18, 'Annual PM2.5/NOx index (tonnes/yr)', 'life')

    if _clamp(profile.waste_management_score) < 55:
        _add('Implement Circular Waste Systems',
             'Deploy industrial recycling loops, waste-to-energy conversion, or '
             'zero-liquid-discharge systems. Publish waste-to-resource ratios in '
             'annual sustainability disclosure.',
             'restoration_regeneration', 'Environmental Stewardship', 4,
             'medium', 12, 'Waste recycled / total waste generated (%)', 'life')

    if _clamp(profile.water_impact_score) < 55:
        _add('Improve Water Stewardship',
             'Conduct a basin-level water risk assessment (aligned with WRI Aqueduct). '
             'Implement water recycling and publish water withdrawal versus consumption data.',
             'environmental_balance', 'Environmental Stewardship', 3,
             'medium', 12, 'Water recycled (%) / water intensity (m³/unit output)', 'life')

    # ── Industrial Efficiency / Modernization ──────────────────────────────────
    if _clamp(profile.energy_transition_score) < 55:
        _add('Accelerate Energy Transition',
             'Develop a renewable energy integration roadmap with measurable interim '
             'targets. Prioritise solar, wind, or hydro based on site geography. '
             'Consider Power Purchase Agreements (PPAs) as a lower-capex pathway.',
             'industrial_efficiency', 'Responsible Modernization', 6,
             'high', 24, 'Renewable energy share (% of total energy consumed)', 'wealth')

    if _clamp(profile.digitalization_score) < 50:
        _add('Launch Digital Transformation Programme',
             'Commission a technology modernization audit. Prioritise IoT-based '
             'emissions monitoring, predictive maintenance platforms, and ERP '
             'integration for real-time operational data.',
             'long_term_sustainability', 'Responsible Modernization', 4,
             'medium', 18, 'Digital maturity assessment score (0-100)', 'intellect')

    if _clamp(profile.infrastructure_upgrade_score) < 50:
        _add('Upgrade Industrial Infrastructure',
             'Commission a capital expenditure audit focused on modernization ROI. '
             'Prioritise equipment upgrades with dual benefits: operational efficiency '
             'and emissions reduction.',
             'industrial_efficiency', 'Responsible Modernization', 3,
             'high', 24, 'Capex directed to modernization (USD/yr)', 'wealth')

    # ── Transparency & Governance ──────────────────────────────────────────────
    if _clamp(profile.transparency_score_detail) < 60:
        _add('Publish Annual ESG / Sustainability Report',
             'Commission a GRI Standards or CDP-aligned sustainability disclosure. '
             'Third-party verification adds credibility and unlocks ESG fund eligibility. '
             'Start with a brief integrated report if a full report is premature.',
             'transparency_governance', 'Transparent Governance', 7,
             'low', 6, 'Annual ESG report: published (Y/N) + verification status', 'intellect')

    if _clamp(profile.audit_quality_score) < 55:
        _add('Upgrade Audit Standards',
             'Engage an independent auditor for environmental and social accounting '
             'in addition to financial audit. A separate environmental audit report '
             'significantly improves institutional investor confidence.',
             'transparency_governance', 'Transparent Governance', 4,
             'medium', 9, 'Audit independence rating (1-5 scale)', 'trust')

    if _clamp(profile.procurement_transparency_score) < 50:
        _add('Publish Procurement Transparency Policy',
             'Adopt and publish a supplier code of conduct. Disclose top-10 supplier '
             'categories and social/environmental procurement criteria.',
             'transparency_governance', 'Transparent Governance', 3,
             'low', 6, 'Suppliers screened vs. ESG criteria (% of spend)', 'trust')

    # ── Anti-Corruption & Accountability ──────────────────────────────────────
    if _clamp(profile.anti_corruption_score) < 60:
        _add('Implement ISO 37001 Anti-Bribery System',
             'Adopt ISO 37001 anti-bribery management and commission an independent '
             'corruption risk assessment. Implement anonymous whistleblower hotline '
             'and publish anti-corruption policy.',
             'anti_corruption', 'Anti-Corruption', 5,
             'medium', 12, 'ISO 37001 certification: achieved (Y/N)', 'trust')

    # ── Public Benefit ────────────────────────────────────────────────────────
    if _clamp(profile.jobs_created_score) < 60:
        _add('Invest in Quality Employment',
             'Create formal workforce development programmes, skills training academies, '
             'and community hiring initiatives. Benchmark wages against regional median '
             'and publish a people report alongside the annual disclosure.',
             'public_benefit', 'Public Benefit', 4,
             'medium', 12, 'Average wage vs. regional median (% premium)', 'society')

    if _clamp(profile.regional_development_score) < 55:
        _add('Formalise Community Investment',
             'Establish a community investment fund with transparent governance. '
             'Publish local procurement targets and social enterprise partnerships. '
             'Report community investment as USD per employee.',
             'public_benefit', 'Public Benefit', 3,
             'low', 6, 'Community investment (USD per employee per year)', 'society')

    # ── Long-Term Sustainability ───────────────────────────────────────────────
    if _clamp(profile.future_readiness_score) < 50:
        _add('Build Future Readiness',
             'Commission a strategic technology foresight study. Develop a five-year '
             'modernization and innovation roadmap with measurable milestones. '
             'Align with emerging regulatory requirements in target markets.',
             'long_term_sustainability', 'Responsible Modernization', 4,
             'medium', 18, 'Future readiness assessment score (0-100)', 'intellect')

    if _clamp(profile.biodiversity_impact_score) < 50:
        _add('Conduct Biodiversity Impact Assessment',
             'Engage an ecology specialist for a TNFD-aligned nature-risk assessment. '
             'Commit to nature-positive operational practices and disclose biodiversity '
             'impact alongside climate-related disclosures.',
             'restoration_regeneration', 'Environmental Stewardship', 3,
             'medium', 9, 'TNFD biodiversity risk disclosure: completed (Y/N)', 'life')

    # Sort by expected gain descending, cap at 8 recommendations
    opps.sort(key=lambda x: x['expected_score_gain'], reverse=True)
    return opps[:8]


# ── Key Harms Signal Analysis ─────────────────────────────────────────────────

def generate_key_harms(profile: 'CompanyProfile') -> list[dict]:
    """Return ranked list of key harm signals with severity and Maqasid link."""
    harms = []

    if profile.pollution_level == 'severe':
        harms.append({
            'label':    'Severe Pollution Impact',
            'detail':   'Operating at severe pollution classification — maximum environmental harm tier.',
            'severity': 'critical',
            'maqasid':  'life',
        })
    elif profile.pollution_level == 'high':
        harms.append({
            'label':    'Elevated Pollution Impact',
            'detail':   'High-pollution operations impose a significant environmental burden on surrounding communities.',
            'severity': 'elevated',
            'maqasid':  'life',
        })

    if (profile.controversy_risk_score or 0) >= 70:
        harms.append({
            'label':    'High Controversy Risk',
            'detail':   'Significant controversy signals identified — reputational and governance risk.',
            'severity': 'elevated',
            'maqasid':  'trust',
        })

    if _clamp(profile.transparency_score_detail) < 30:
        harms.append({
            'label':    'Transparency Deficit',
            'detail':   'Insufficient public disclosure — below minimum accountability standards.',
            'severity': 'elevated',
            'maqasid':  'intellect',
        })

    if _clamp(profile.anti_corruption_score) < 40:
        harms.append({
            'label':    'Anti-Corruption Gap',
            'detail':   'Anti-corruption controls are below recommended institutional standards.',
            'severity': 'moderate',
            'maqasid':  'trust',
        })

    p = profile.pollution_level
    if p in ('high', 'severe') and _clamp(profile.modernization_score) < 40:
        harms.append({
            'label':    'Transition Gap',
            'detail':   'High-impact operations without adequate modernization investment.',
            'severity': 'elevated',
            'maqasid':  'society',
        })

    if (
        _clamp(profile.profit_extraction_score) > 75 and
        _clamp(profile.public_benefit_score) < 50
    ):
        harms.append({
            'label':    'Low Public Benefit Return',
            'detail':   'High profit extraction relative to public benefit generated.',
            'severity': 'moderate',
            'maqasid':  'wealth',
        })

    return harms


# ── Key Benefits Signal Analysis ──────────────────────────────────────────────

def generate_key_benefits(profile: 'CompanyProfile') -> list[dict]:
    """Return ranked list of key benefit signals."""
    benefits = []

    if profile.pollution_level == 'low':
        benefits.append({
            'label':    'Clean Operations',
            'detail':   'Low pollution classification — within responsible environmental operating standards.',
            'strength': 'strong',
            'maqasid':  'life',
        })

    if _clamp(profile.public_benefit_score) >= 65:
        benefits.append({
            'label':    'Strong Public Benefit',
            'detail':   'High-quality employment, regional development, and community value creation.',
            'strength': 'strong',
            'maqasid':  'society',
        })

    if _clamp(profile.transparency_score_detail) >= 65:
        benefits.append({
            'label':    'Transparent Reporting',
            'detail':   'Strong disclosure standards — meets institutional investor transparency requirements.',
            'strength': 'strong',
            'maqasid':  'intellect',
        })

    if _clamp(profile.modernization_score) >= 65:
        benefits.append({
            'label':    'Active Modernization',
            'detail':   'Committed to technology and energy transition with measurable future readiness.',
            'strength': 'strong',
            'maqasid':  'wealth',
        })

    if _clamp(profile.anti_corruption_score) >= 65:
        benefits.append({
            'label':    'Anti-Corruption Leadership',
            'detail':   'Strong governance controls and ethical procurement standards.',
            'strength': 'strong',
            'maqasid':  'trust',
        })

    if _clamp(profile.national_value_score) >= 65:
        benefits.append({
            'label':    'Long-Term National Value',
            'detail':   'Significant contribution to national economic development and resilience.',
            'strength': 'moderate',
            'maqasid':  'society',
        })

    if _clamp(profile.ethical_alignment_score) >= 65:
        benefits.append({
            'label':    'High Ethical Alignment',
            'detail':   'Consistent long-term ethical value creation and stakeholder trust.',
            'strength': 'moderate',
            'maqasid':  'trust',
        })

    if _clamp(profile.biodiversity_impact_score) >= 65:
        benefits.append({
            'label':    'Ecosystem Stewardship',
            'detail':   'Active biodiversity protection and nature-positive practices.',
            'strength': 'moderate',
            'maqasid':  'life',
        })

    return benefits


# ── Confidence Computation ────────────────────────────────────────────────────

def compute_data_confidence(profile: 'CompanyProfile') -> float:
    """
    0-1: data completeness and analysis reliability indicator.
    Uses the same logic as _get_ai_confidence() in companies/views.py
    but returns 0-1 for storage on CompanyEthicsProfile.
    """
    score = 0

    # AI content completeness (40 pts)
    for field in ('ai_summary', 'ai_modernization_report', 'ai_investment_opportunity', 'ai_risk_notes'):
        val = getattr(profile, field, '') or ''
        if len(val) > 80:
            score += 10

    # Source citations (20 pts)
    try:
        src_count = profile.cited_sources.count()
        score += min(src_count * 5, 20)
    except Exception:
        pass

    # Score diversity — penalise many fields at default 50 (10 pts)
    check_fields = [
        'jobs_created_score', 'regional_development_score', 'waste_management_score',
        'energy_transition_score', 'transparency_score_detail', 'anti_corruption_score',
    ]
    defaults = sum(1 for f in check_fields if abs(getattr(profile, f, 50) - 50.0) < 0.5)
    score += max(0, 10 - defaults * 2)

    # Verification & public data (30 pts)
    if profile.is_verified:
        score += 30
    else:
        if profile.annual_report_url:
            score += 10
        if profile.sustainability_report_url:
            score += 8
        if profile.ai_recommendations:
            score += 7
        score += 5  # baseline

    return round(min(score, 100) / 100, 3)


# ── Master computation entry point ────────────────────────────────────────────

def compute_ethics_profile(profile: 'CompanyProfile') -> dict:
    """
    Compute all three master formula scores plus supporting intelligence
    for a CompanyProfile. Returns a dict suitable for bulk-saving to
    CompanyEthicsProfile (and ImprovementMilestone records).

    Does NOT write to the database — call compute_and_save() for that.
    """
    nei, total_benefit, total_harm = compute_net_ethical_impact(profile)
    tss  = compute_transition_stewardship(profile)
    rvi  = compute_regenerative_value(profile)
    opps = generate_improvement_opportunities(profile)
    harms    = generate_key_harms(profile)
    benefits = generate_key_benefits(profile)
    conf = compute_data_confidence(profile)

    top3 = opps[:3]
    expected_gain = round(sum(o['expected_score_gain'] for o in top3), 1)

    return {
        'net_ethical_impact':         nei,
        'transition_stewardship':     tss,
        'regenerative_value':         rvi,
        'total_benefit_score':        total_benefit,
        'total_harm_score':           total_harm,
        'key_harms':                  harms,
        'key_benefits':               benefits,
        'improvement_opportunities':  opps,
        'next_best_actions':          [o['title'] for o in top3],
        'expected_score_improvement': expected_gain,
        'data_confidence':            conf,
        'formula_version':            '1.0',
    }


def compute_and_save(profile: 'CompanyProfile') -> 'CompanyEthicsProfile':
    """
    Compute master scores and persist to CompanyEthicsProfile.
    Rebuilds ImprovementMilestone records (clears old 'recommended' ones).
    Safe to call repeatedly — uses update_or_create.
    """
    from ethics.models import CompanyEthicsProfile, ImprovementMilestone

    data = compute_ethics_profile(profile)
    opps = data.pop('improvement_opportunities', [])

    ethics, created = CompanyEthicsProfile.objects.update_or_create(
        profile=profile,
        defaults=data,
    )

    # Rebuild milestones for 'recommended' status only
    ethics.milestones.filter(status='recommended').delete()
    for i, opp in enumerate(opps, 1):
        ImprovementMilestone.objects.create(
            ethics_profile=ethics,
            title=opp['title'],
            description=opp['description'],
            formula_category=opp.get('formula_category', ''),
            pillar=opp.get('pillar', ''),
            expected_score_gain=opp.get('expected_score_gain', 0.0),
            effort_level=opp.get('effort_level', 'medium'),
            timeline_months=opp.get('timeline_months', 12),
            kpi_metric=opp.get('kpi_metric', ''),
            maqasid_principle=opp.get('maqasid_principle', ''),
            priority=i,
            status='recommended',
        )

    log.info(
        'Ethics profile computed for %s: NEI=%.1f TSS=%.1f RVI=%.1f',
        profile.company.name, ethics.net_ethical_impact,
        ethics.transition_stewardship, ethics.regenerative_value,
    )
    return ethics


def get_or_compute(profile: 'CompanyProfile') -> 'CompanyEthicsProfile':
    """
    Return existing CompanyEthicsProfile or compute fresh.
    Used in views for lazy on-demand computation.
    Silently catches errors to avoid breaking company pages.
    """
    from ethics.models import CompanyEthicsProfile
    try:
        return profile.ethics
    except CompanyEthicsProfile.DoesNotExist:
        try:
            return compute_and_save(profile)
        except Exception as exc:
            log.warning('ethics get_or_compute failed for %s: %s', profile, exc)
            return None
