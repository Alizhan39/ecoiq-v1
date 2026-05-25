"""
EcoIQ Score Explainability Engine
===================================
Generates structured, analyst-grade per-pillar explanations for EcoIQ scores.

Each pillar explanation contains:
  drivers   – positive factors that raise the score
  penalties – negative factors that suppress the score
  missing   – undisclosed data gaps that limit confidence
  risks     – forward-looking risk signals
  trend     – score movement narrative

Sources drawn from:
  • Company projects (EnvironmentalProject)
  • Evidence documents (Evidence)
  • Score history (ScoreHistory)
  • Linked AIAnalysisJob findings (AIFinding)
  • AIScoreEstimate reasoning + data_gaps + greenwashing_signals

Usage:
    from league.explainability import explain_company
    explanations = explain_company(company, ctx)   # list of 5 dicts
"""
from __future__ import annotations

import re
from typing import List, Dict, Any, Optional


# ── Constants ──────────────────────────────────────────────────────────────────

SEVERITY_CRITICAL = 'critical'
SEVERITY_HIGH     = 'high'
SEVERITY_MEDIUM   = 'medium'
SEVERITY_LOW      = 'low'
SEVERITY_POSITIVE = 'positive'

CAT_DRIVER  = 'driver'
CAT_PENALTY = 'penalty'
CAT_MISSING = 'missing'
CAT_RISK    = 'risk'
CAT_TREND   = 'trend'

# AI finding type → pillar key
_FINDING_PILLAR = {
    'co2_metric':      'pollution',
    'methane_metric':  'pollution',
    'so2_metric':      'pollution',
    'pm25_metric':     'pollution',
    'nox_metric':      'pollution',
    'waste_metric':    'pollution',
    'pollution_other': 'pollution',
    'water_metric':    'transparency',
    'investment':      'investment',
    'project':         'reduction',
    'coal_replacement':'reduction',
    'transparency':    'transparency',
}

# Severity → integer for ordering
_SEV_ORDER = {
    SEVERITY_CRITICAL: 0,
    SEVERITY_HIGH:     1,
    SEVERITY_MEDIUM:   2,
    SEVERITY_LOW:      3,
    SEVERITY_POSITIVE: 4,
}


# ── Helper builders ────────────────────────────────────────────────────────────

def _f(
    category:    str,
    severity:    str,
    text:        str,
    rationale:   str        = '',
    source:      str        = 'rule',
    source_label:str        = '',
    confidence:  float      = 0.75,
    score_impact:float      = 0.0,
    quote:       str        = '',
    evidence_url:str        = '',
    year:        Optional[int] = None,
    numeric_value: Optional[float] = None,
    unit:        str        = '',
) -> Dict[str, Any]:
    return dict(
        category=category, severity=severity, text=text, rationale=rationale,
        source=source, source_label=source_label or source.replace('_', ' ').title(),
        confidence=confidence, score_impact=score_impact,
        quote=quote, evidence_url=evidence_url,
        year=year, numeric_value=numeric_value, unit=unit,
        confidence_pct=round(confidence * 100),
    )


def _pillar_result(
    key:    str,
    name:   str,
    name_ru:str,
    weight: int,
    score:  int,
    color:  str,
    factors: List[Dict],
    delta_3m:  Optional[float] = None,
    delta_12m: Optional[float] = None,
) -> Dict[str, Any]:
    drivers  = [f for f in factors if f['category'] == CAT_DRIVER]
    penalties= [f for f in factors if f['category'] == CAT_PENALTY]
    missing  = [f for f in factors if f['category'] == CAT_MISSING]
    risks    = [f for f in factors if f['category'] == CAT_RISK]
    trends   = [f for f in factors if f['category'] == CAT_TREND]

    # Overall explanation confidence = weighted average of factor confidences
    all_conf = [f['confidence'] for f in factors]
    confidence = round(sum(all_conf) / max(len(all_conf), 1), 2) if all_conf else 0.5

    # Trend label
    if delta_12m is not None:
        if   delta_12m >= 3:    trend = 'improving'
        elif delta_12m <= -3:   trend = 'declining'
        else:                   trend = 'stable'
    elif delta_3m is not None:
        if   delta_3m >= 1:     trend = 'improving'
        elif delta_3m <= -1:    trend = 'declining'
        else:                   trend = 'stable'
    else:
        trend = 'unknown'

    return dict(
        key=key, name=name, name_ru=name_ru, weight=weight,
        score=score, color=color,
        trend=trend, delta_3m=delta_3m, delta_12m=delta_12m,
        confidence=confidence, confidence_pct=round(confidence * 100),
        drivers=drivers, penalties=penalties,
        missing=missing, risks=risks, trends=trends,
        has_data=(len(factors) > 0),
    )


# ── AI reasoning parser ────────────────────────────────────────────────────────

_PILLAR_PATTERNS = {
    'pollution':    r'Pollution\s+Footprint.*?(?=Reduction Progress|Investment|Transparency|Community|$)',
    'reduction':    r'Reduction\s+Progress.*?(?=Investment|Transparency|Community|$)',
    'investment':   r'Investment.*?(?=Transparency|Community|$)',
    'transparency': r'Transparency.*?(?=Community Impact|Community|$)',
    'community':    r'Community.*',
}

def _extract_pillar_reasoning(reasoning: str, pillar_key: str) -> str:
    """Extract the per-pillar portion of the AI score estimate reasoning."""
    if not reasoning:
        return ''
    pattern = _PILLAR_PATTERNS.get(pillar_key, '')
    if not pattern:
        return ''
    m = re.search(pattern, reasoning, re.IGNORECASE | re.DOTALL)
    if m:
        txt = m.group(0).strip()
        # Remove the leading "Pillar Name (XX/100):" header
        txt = re.sub(r'^[A-Za-z\s]+\(\d+/100\):\s*', '', txt).strip()
        return txt[:320]
    return ''


# ── Pillar explainers ──────────────────────────────────────────────────────────

def _explain_pollution(company, ctx: Dict) -> Dict:
    """Pollution Footprint — weight 35%"""
    score    = company.score_pollution_footprint
    factors  = []
    projects = ctx['all_projects']
    evidence = ctx['evidence']
    ai_fndgs = ctx.get('ai_findings', [])
    se       = ctx.get('ai_score_estimate')
    d3m      = ctx.get('delta_3m_pollution')
    d12m     = ctx.get('delta_12m_pollution')

    ev_types = {e.doc_type for e in evidence}

    # ── DRIVERS ───────────────────────────────────────────────────────────────

    pm25_projects = [p for p in projects if (p.pm25_reduction_kg or 0) > 0]
    co2_projects  = [p for p in projects if (p.co2_reduction_tonnes or 0) > 0]
    total_pm25 = sum(p.pm25_reduction_kg or 0 for p in pm25_projects)
    total_co2  = sum(p.co2_reduction_tonnes or 0 for p in co2_projects)

    if pm25_projects:
        factors.append(_f(
            CAT_DRIVER, SEVERITY_POSITIVE,
            f'PM2.5 reduction: {total_pm25:,.0f} kg/yr across {len(pm25_projects)} project(s)',
            'Direct particulate matter reduction at source — highest-weight component of Pollution Footprint.',
            source='projects', source_label='Project metrics',
            confidence=0.92, score_impact=+6.0,
        ))

    if co2_projects:
        factors.append(_f(
            CAT_DRIVER, SEVERITY_POSITIVE,
            f'CO₂ avoided: {total_co2:,.0f} t/yr across {len(co2_projects)} project(s)',
            'Measured CO₂ reduction from completed and active environmental projects.',
            source='projects', source_label='Project metrics',
            confidence=0.90, score_impact=+5.0,
        ))

    # AI finding: positive emission reductions
    for f in ai_fndgs:
        if f.finding_type in ('co2_metric', 'so2_metric', 'pm25_metric') and f.numeric_value:
            # A year-on-year comparison — if 2023 < 2022 it's positive
            if f.year and f.finding_type == 'co2_metric':
                prev = next((x for x in ai_fndgs
                             if x.finding_type == 'co2_metric' and x.year == f.year - 1), None)
                if prev and prev.numeric_value and f.numeric_value < prev.numeric_value:
                    delta_t = prev.numeric_value - f.numeric_value
                    pct = round(delta_t / prev.numeric_value * 100, 1)
                    factors.append(_f(
                        CAT_DRIVER, SEVERITY_POSITIVE,
                        f'GHG emissions declined {pct}% YoY ({f.numeric_value/1e6:.1f} → {prev.numeric_value/1e6:.1f} MtCO₂e)',
                        f'Year-on-year reduction detected in AI document analysis.',
                        source='ai_finding', source_label='AI Document Analysis',
                        confidence=f.confidence_score, score_impact=+4.0,
                        quote=f.source_quote[:160] if f.source_quote else '',
                        year=f.year,
                    ))

    if 'engineering_audit' in ev_types:
        factors.append(_f(
            CAT_DRIVER, SEVERITY_LOW,
            'Engineering audit on file — emissions measurement methodology verified',
            'Independent technical audit supports the reliability of pollution data.',
            source='evidence', source_label='Evidence base',
            confidence=0.82, score_impact=+2.0,
        ))

    # ── PENALTIES ─────────────────────────────────────────────────────────────

    if score < 40:
        factors.append(_f(
            CAT_PENALTY, SEVERITY_CRITICAL,
            f'Pollution Footprint {score}/100 — Major Polluter tier',
            'Score below 40 indicates absolute emissions far exceed sector-transition benchmarks. '
            'Institutional investors using MSCI ESG or Bloomberg ESG frameworks typically flag '
            'companies below this threshold.',
            source='rule', source_label='EcoIQ scoring',
            confidence=0.98, score_impact=-15.0,
        ))
    elif score < 60:
        factors.append(_f(
            CAT_PENALTY, SEVERITY_HIGH,
            f'Pollution Footprint {score}/100 — below Clean Transition threshold (60)',
            'Score below 60 indicates pollution intensity above the sector median. '
            'Clean Transition threshold requires demonstrated monitoring, reduction plans, '
            'and third-party verification.',
            source='rule', source_label='EcoIQ scoring',
            confidence=0.95, score_impact=-8.0,
        ))

    # AI: large absolute emissions
    for f in ai_fndgs:
        if f.finding_type == 'co2_metric' and f.numeric_value and f.numeric_value > 5e6:
            factors.append(_f(
                CAT_PENALTY, SEVERITY_CRITICAL,
                f'Absolute GHG: {f.numeric_value/1e6:.1f} MtCO₂e ({f.year or "latest"})',
                'High absolute emission volume places this company among the sector\'s largest '
                'emitters. Even with efficiency improvements, decarbonisation trajectory is '
                'insufficient at current rate.',
                source='ai_finding', source_label='AI Document Analysis',
                confidence=f.confidence_score, score_impact=-12.0,
                quote=f.source_quote[:160] if f.source_quote else '',
                year=f.year, numeric_value=f.numeric_value, unit='tCO₂e',
            ))
        if f.finding_type == 'methane_metric' and f.numeric_value and f.numeric_value > 10000:
            factors.append(_f(
                CAT_PENALTY, SEVERITY_HIGH,
                f'Methane: {f.numeric_value:,.0f} t — elevated fugitive emissions',
                'Methane has 80× GWP vs CO₂ over 20 years. MSCI ESG and TCFD frameworks '
                'heavily penalise undisclosed or unmitigated methane above sector thresholds.',
                source='ai_finding', source_label='AI Document Analysis',
                confidence=f.confidence_score, score_impact=-8.0,
                quote=f.source_quote[:160] if f.source_quote else '',
                year=f.year, numeric_value=f.numeric_value, unit='tonnes',
            ))
        if f.finding_type == 'so2_metric' and f.numeric_value and f.numeric_value > 5000:
            factors.append(_f(
                CAT_PENALTY, SEVERITY_HIGH,
                f'SO₂: {f.numeric_value:,.0f} t — above regulatory attention threshold',
                'SO₂ above 5,000 t/yr triggers mandatory monitoring requirements under '
                'Kazakhstan Environmental Code (Art. 193) and attracts IFC Performance Standard scrutiny.',
                source='ai_finding', source_label='AI Document Analysis',
                confidence=f.confidence_score, score_impact=-5.0,
                quote=f.source_quote[:160] if f.source_quote else '',
                year=f.year, numeric_value=f.numeric_value, unit='tonnes SO₂',
            ))

    # Trend penalty
    if d12m is not None and d12m <= -3:
        factors.append(_f(
            CAT_PENALTY, SEVERITY_MEDIUM,
            f'Score declined {abs(d12m):.1f} pts over 12 months',
            'Sustained decline in Pollution Footprint score suggests worsening emissions '
            'intensity, reduced mitigation effort, or loss of verified data.',
            source='score_history', source_label='Score History',
            confidence=0.95, score_impact=d12m,
        ))

    # ── MISSING DISCLOSURES ───────────────────────────────────────────────────

    if 'satellite' not in ev_types:
        factors.append(_f(
            CAT_MISSING, SEVERITY_HIGH,
            'Scope 1+2 emissions not independently verified via satellite',
            'No GHGSat or Sentinel-5P satellite verification in evidence base. Satellite data '
            'provides tamper-evident, facility-level verification required for MSCI ESG Tier 1 '
            'environmental data quality rating.',
            source='evidence', source_label='Evidence base',
            confidence=0.88, score_impact=-4.0,
        ))

    # Check AI data gaps
    data_gaps = (se.data_gaps if se else []) or []
    for gap in data_gaps:
        if any(kw in gap.lower() for kw in ('scope 3', 'upstream', 'value chain')):
            factors.append(_f(
                CAT_MISSING, SEVERITY_HIGH,
                'Scope 3 emissions not disclosed',
                gap,
                source='ai_finding', source_label='AI Data Gap Analysis',
                confidence=0.92, score_impact=-5.0,
            ))
        if any(kw in gap.lower() for kw in ('nox', 'nitrogen')):
            factors.append(_f(
                CAT_MISSING, SEVERITY_MEDIUM,
                'NOₓ emissions not disclosed',
                gap,
                source='ai_finding', source_label='AI Data Gap Analysis',
                confidence=0.85, score_impact=-2.0,
            ))

    if not any(e.doc_type == 'government_report' for e in evidence):
        factors.append(_f(
            CAT_MISSING, SEVERITY_MEDIUM,
            'No government environmental permit or compliance report',
            'Regulatory permits and state environmental inspection reports are the primary '
            'legal verification instrument for emissions levels in Kazakhstan and CIS markets.',
            source='evidence', source_label='Evidence base',
            confidence=0.80, score_impact=-3.0,
        ))

    # ── RISKS ─────────────────────────────────────────────────────────────────

    # Greenwashing signals related to pollution
    for f in ai_fndgs:
        if f.finding_type == 'greenwashing' and any(
            kw in (f.title + f.description).lower()
            for kw in ('scope 3', 'methane', 'emission', 'pollution', 'flare')
        ):
            factors.append(_f(
                CAT_RISK, SEVERITY_HIGH,
                f.title[:90],
                f.description[:240],
                source='ai_finding', source_label='AI Greenwashing Signal',
                confidence=f.confidence_score, score_impact=-4.0,
                quote=f.source_quote[:120] if f.source_quote else '',
            ))

    # Regulatory risk from sector
    if company.sector in ('oil_gas', 'mining', 'chemical', 'power'):
        if 'satellite' not in ev_types and not any(
            f.finding_type == 'methane_metric' for f in ai_fndgs
        ):
            factors.append(_f(
                CAT_RISK, SEVERITY_MEDIUM,
                'No methane monitoring data — elevated regulatory risk',
                'Oil, gas, and mining operations are subject to Kazakhstan\'s 2022 '
                'Environmental Code methane reporting requirements (Art. 169). Absence '
                'of LDAR or continuous monitoring creates compliance exposure.',
                source='rule', source_label='Regulatory framework',
                confidence=0.78, score_impact=-3.0,
            ))

    return _pillar_result('pollution', 'Pollution Footprint', 'Pollution',
                          35, score, '#ef4444', factors, d3m, d12m)


def _explain_reduction(company, ctx: Dict) -> Dict:
    """Reduction Progress — weight 25%"""
    score    = company.score_reduction_progress
    factors  = []
    projects = ctx['all_projects']
    evidence = ctx['evidence']
    ai_fndgs = ctx.get('ai_findings', [])
    se       = ctx.get('ai_score_estimate')
    d3m      = ctx.get('delta_3m_reduction')
    d12m     = ctx.get('delta_12m_reduction')

    completed  = [p for p in projects if p.status == 'completed']
    active     = [p for p in projects if p.status == 'active']
    ev_types   = {e.doc_type for e in evidence}
    data_gaps  = (se.data_gaps if se else []) or []

    # ── DRIVERS ───────────────────────────────────────────────────────────────

    if completed:
        total_co2 = sum(p.co2_reduction_tonnes or 0 for p in completed)
        factors.append(_f(
            CAT_DRIVER, SEVERITY_POSITIVE,
            f'{len(completed)} completed project(s) with verified emission reduction',
            f'Completed projects demonstrate executed (not just planned) emission reduction. '
            f'Total: {total_co2:,} t CO₂/yr' if total_co2 else
            'Completed projects signal operational capability.',
            source='projects', source_label='Project records',
            confidence=0.90, score_impact=+6.0,
        ))

    # Active methane / gasification projects
    clean_active = [p for p in active
                    if p.project_type in ('methane', 'gasification', 'renewable', 'power_modern')]
    if clean_active:
        factors.append(_f(
            CAT_DRIVER, SEVERITY_POSITIVE,
            f'{len(clean_active)} active clean-tech project(s) underway',
            'Active gasification, methane capture, or renewable projects signal forward momentum '
            'on emission reduction trajectory.',
            source='projects', source_label='Active projects',
            confidence=0.85, score_impact=+4.0,
        ))

    # Positive trend
    if d12m is not None and d12m >= 3:
        factors.append(_f(
            CAT_DRIVER, SEVERITY_POSITIVE,
            f'Reduction Progress improved {d12m:+.1f} pts in 12 months',
            'Sustained score improvement over a rolling 12-month window indicates consistent '
            'progress on emission reduction KPIs.',
            source='score_history', source_label='Score History',
            confidence=0.95, score_impact=+d12m,
        ))

    # AI-sourced reduction data
    for f in ai_fndgs:
        if f.finding_type == 'project' and f.confidence_score >= 0.8:
            factors.append(_f(
                CAT_DRIVER, SEVERITY_POSITIVE,
                f.title[:80],
                f.description[:220],
                source='ai_finding', source_label='AI Document Analysis',
                confidence=f.confidence_score, score_impact=+3.0,
                quote=f.source_quote[:140] if f.source_quote else '',
                year=f.year,
            ))

    # ── PENALTIES ─────────────────────────────────────────────────────────────

    if score < 40:
        factors.append(_f(
            CAT_PENALTY, SEVERITY_CRITICAL,
            f'Reduction Progress {score}/100 — no credible decarbonisation pathway',
            'Score below 40 indicates absence of measurable, time-bound emission reduction '
            'commitments. Under MSCI ESG methodology, this triggers a company-level ESG '
            'controversy flag.',
            source='rule', source_label='EcoIQ scoring',
            confidence=0.97, score_impact=-12.0,
        ))
    elif score < 60:
        factors.append(_f(
            CAT_PENALTY, SEVERITY_HIGH,
            f'Reduction Progress {score}/100 — below transition benchmark',
            'Score reflects limited quantified year-on-year reduction progress. Transition '
            'Leaders require independently verified absolute reduction targets with defined '
            'interim milestones.',
            source='rule', source_label='EcoIQ scoring',
            confidence=0.93, score_impact=-7.0,
        ))

    if d12m is not None and d12m <= -3:
        factors.append(_f(
            CAT_PENALTY, SEVERITY_HIGH,
            f'Score declined {abs(d12m):.1f} pts in 12 months',
            'Persistent decline in Reduction Progress pillar suggests slowing or reversing '
            'decarbonisation trajectory.',
            source='score_history', source_label='Score History',
            confidence=0.95, score_impact=d12m,
        ))

    # ── MISSING DISCLOSURES ───────────────────────────────────────────────────

    for gap in data_gaps:
        if any(kw in gap.lower() for kw in ('milestone', 'interim', 'target', 'net.?zero', 'baseline')):
            factors.append(_f(
                CAT_MISSING, SEVERITY_HIGH,
                'No interim net-zero milestones',
                gap,
                source='ai_finding', source_label='AI Data Gap Analysis',
                confidence=0.88, score_impact=-5.0,
            ))
            break

    # Check for SBTi / science-based target
    sbti_signals = any(
        any(kw in (e.title + ' ' + e.get_doc_type_display()).lower()
            for kw in ('sbti', 'science based', 'science-based', 'net zero'))
        for e in evidence
    )
    if not sbti_signals:
        factors.append(_f(
            CAT_MISSING, SEVERITY_HIGH,
            'Science Based Targets (SBTi) commitment not found',
            'No SBTi 1.5°C-aligned commitment detected in evidence base. SBTi validation is '
            'required for MSCI ESG "AA" rating and is a standard screen in sustainable '
            'investment mandates. Without it, absolute targets are unverified.',
            source='evidence', source_label='Evidence base',
            confidence=0.82, score_impact=-5.0,
        ))

    for gap in data_gaps:
        if any(kw in gap.lower() for kw in ('scope 3', 'value chain', 'upstream')):
            factors.append(_f(
                CAT_MISSING, SEVERITY_HIGH,
                'Scope 3 emissions not measured — reduction baseline incomplete',
                f'Without Scope 3 accounting, declared reduction targets cover only a fraction '
                f'of total value-chain emissions. {gap}',
                source='ai_finding', source_label='AI Data Gap Analysis',
                confidence=0.90, score_impact=-4.0,
            ))
            break

    # ── RISKS ─────────────────────────────────────────────────────────────────

    # Greenwashing signals on reduction claims
    for f in ai_fndgs:
        if f.finding_type == 'greenwashing' and any(
            kw in (f.title + f.description).lower()
            for kw in ('net-zero', 'net zero', 'target', 'milestone', 'commitment', 'pathway')
        ):
            factors.append(_f(
                CAT_RISK, SEVERITY_HIGH,
                f.title[:90],
                f.description[:240],
                source='ai_finding', source_label='AI Greenwashing Signal',
                confidence=f.confidence_score, score_impact=-4.0,
                quote=f.source_quote[:120] if f.source_quote else '',
            ))

    return _pillar_result('reduction', 'Reduction Progress', 'Reduction',
                          25, score, '#22c55e', factors, d3m, d12m)


def _explain_investment(company, ctx: Dict) -> Dict:
    """Investment — weight 20%"""
    score    = company.score_investment
    factors  = []
    projects = ctx['all_projects']
    evidence = ctx['evidence']
    ai_fndgs = ctx.get('ai_findings', [])
    se       = ctx.get('ai_score_estimate')
    d3m      = ctx.get('delta_3m_investment')
    d12m     = ctx.get('delta_12m_investment')

    data_gaps = (se.data_gaps if se else []) or []
    inv_projects = [p for p in projects if (p.investment_usd or 0) > 0]
    total_inv = sum(p.investment_usd or 0 for p in inv_projects)

    # ── DRIVERS ───────────────────────────────────────────────────────────────

    if total_inv >= 1_000_000:
        total_inv_m = total_inv / 1_000_000
        factors.append(_f(
            CAT_DRIVER, SEVERITY_POSITIVE,
            f'${total_inv_m:,.1f}M total environmental capital deployed',
            f'Across {len(inv_projects)} project(s). Substantive investment signals '
            'genuine commitment rather than token compliance.',
            source='projects', source_label='Project investment data',
            confidence=0.92, score_impact=+7.0,
            numeric_value=total_inv_m, unit='USD million',
        ))

    # AI investment findings
    for f in ai_fndgs:
        if f.finding_type == 'investment' and f.numeric_value:
            inv_val = f.numeric_value
            lbl = f'${inv_val/1e6:.1f}M' if inv_val >= 1e6 else f'${inv_val:,.0f}'
            factors.append(_f(
                CAT_DRIVER, SEVERITY_POSITIVE,
                f'{lbl} — {f.title[:60]}',
                f.description[:220],
                source='ai_finding', source_label='AI Document Analysis',
                confidence=f.confidence_score, score_impact=+5.0,
                quote=f.source_quote[:160] if f.source_quote else '',
                year=f.year, numeric_value=f.numeric_value, unit='USD',
            ))

    high_impact_types = {'methane', 'gasification', 'renewable', 'power_modern', 'filters'}
    hi_projects = [p for p in inv_projects if p.project_type in high_impact_types]
    if hi_projects:
        factors.append(_f(
            CAT_DRIVER, SEVERITY_POSITIVE,
            f'{len(hi_projects)} high-impact investment(s) in clean technology',
            'Gasification, renewable energy, and industrial filters receive higher weighting '
            'in EcoIQ investment scoring due to measurable emissions impact.',
            source='projects', source_label='Project records',
            confidence=0.87, score_impact=+4.0,
        ))

    # ── PENALTIES ─────────────────────────────────────────────────────────────

    if score < 40:
        factors.append(_f(
            CAT_PENALTY, SEVERITY_CRITICAL,
            f'Investment pillar {score}/100 — environmental capex below critical threshold',
            'Score implies clean investment well below the 0.5% of estimated revenue '
            'threshold. MSCI ESG methodology classifies companies below this threshold '
            'as "Low ESG Commitment" regardless of other disclosures.',
            source='rule', source_label='EcoIQ scoring',
            confidence=0.96, score_impact=-10.0,
        ))
    elif score < 60:
        factors.append(_f(
            CAT_PENALTY, SEVERITY_HIGH,
            f'Investment pillar {score}/100 — below sector benchmark (60)',
            'Investment level below sector median suggests environmental capex does not '
            'keep pace with the company\'s pollution intensity or revenue scale.',
            source='rule', source_label='EcoIQ scoring',
            confidence=0.90, score_impact=-6.0,
        ))

    # ── MISSING DISCLOSURES ───────────────────────────────────────────────────

    if company.annual_revenue_usd is None:
        factors.append(_f(
            CAT_MISSING, SEVERITY_MEDIUM,
            'Annual revenue not disclosed — investment ratio cannot be computed',
            'Without revenue data, environmental capex as % of revenue — a key MSCI ESG '
            'and Bloomberg ESG metric — cannot be verified.',
            source='rule', source_label='Company data',
            confidence=0.85, score_impact=-3.0,
        ))
    elif total_inv > 0 and company.annual_revenue_usd > 0:
        ratio = total_inv / company.annual_revenue_usd * 100
        if ratio < 0.5:
            factors.append(_f(
                CAT_MISSING, SEVERITY_HIGH,
                f'Environmental capex ~{ratio:.2f}% of revenue — below 1% MSCI threshold',
                'MSCI ESG benchmark for "credible" environmental commitment in industrial '
                'sectors is ≥1% of annual revenue directed to clean investment. '
                f'Current ratio ({ratio:.2f}%) falls below this.',
                source='rule', source_label='Revenue analysis',
                confidence=0.80, score_impact=-4.0,
            ))

    for gap in data_gaps:
        if any(kw in gap.lower() for kw in ('capex', 'investment', 'capital', 'fund', 'spend')):
            factors.append(_f(
                CAT_MISSING, SEVERITY_MEDIUM,
                'Green capital allocation breakdown not disclosed',
                gap,
                source='ai_finding', source_label='AI Data Gap Analysis',
                confidence=0.82, score_impact=-2.0,
            ))
            break

    # ── RISKS ─────────────────────────────────────────────────────────────────

    if not inv_projects and score >= 50:
        factors.append(_f(
            CAT_RISK, SEVERITY_MEDIUM,
            'Investment score not supported by project-level evidence',
            'Investment pillar score is above 50 but no project-level investment data is '
            'recorded in the EcoIQ evidence base. Score may rely on unverified claims.',
            source='rule', source_label='Data quality check',
            confidence=0.75, score_impact=-3.0,
        ))

    return _pillar_result('investment', 'Investment', 'Investment',
                          20, score, '#3b82f6', factors, d3m, d12m)


def _explain_transparency(company, ctx: Dict) -> Dict:
    """Transparency — weight 10%"""
    score    = company.score_transparency
    factors  = []
    evidence = ctx['evidence']
    ai_fndgs = ctx.get('ai_findings', [])
    se       = ctx.get('ai_score_estimate')
    d3m      = ctx.get('delta_3m_transparency')
    d12m     = ctx.get('delta_12m_transparency')

    ev_total    = len(evidence)
    ev_verified = sum(1 for e in evidence if e.verification_status == 'verified')
    ev_types    = {e.doc_type for e in evidence}
    data_gaps   = (se.data_gaps if se else []) or []

    # ── DRIVERS ───────────────────────────────────────────────────────────────

    if ev_verified > 0:
        factors.append(_f(
            CAT_DRIVER, SEVERITY_POSITIVE,
            f'{ev_verified}/{ev_total} evidence document(s) independently verified',
            'Verified documents indicate third-party validation of environmental claims, '
            'which is the primary mechanism for Transparency pillar scoring.',
            source='evidence', source_label='Evidence base',
            confidence=0.92, score_impact=+ev_verified * 2.5,
        ))

    _REQUIRED_TYPES = {'audit_report', 'government_report', 'engineering_audit', 'satellite'}
    types_present = ev_types & _REQUIRED_TYPES
    if len(types_present) >= 2:
        factors.append(_f(
            CAT_DRIVER, SEVERITY_POSITIVE,
            f'{len(types_present)} of 4 priority evidence categories present',
            f'Includes: {", ".join(t.replace("_"," ").title() for t in sorted(types_present))}. '
            'Diversity of document types signals multi-source verification, valued by GRI and CDP frameworks.',
            source='evidence', source_label='Evidence diversity',
            confidence=0.88, score_impact=+4.0,
        ))

    # AI transparency findings
    for f in ai_fndgs:
        if f.finding_type == 'transparency' and f.confidence_score >= 0.75:
            factors.append(_f(
                CAT_DRIVER if 'positive' not in f.description.lower() else CAT_DRIVER,
                SEVERITY_POSITIVE,
                f.title[:80],
                f.description[:220],
                source='ai_finding', source_label='AI Document Analysis',
                confidence=f.confidence_score, score_impact=+3.0,
                quote=f.source_quote[:140] if f.source_quote else '',
                year=f.year,
            ))

    # ── PENALTIES ─────────────────────────────────────────────────────────────

    if ev_verified == 0 and ev_total > 0:
        factors.append(_f(
            CAT_PENALTY, SEVERITY_HIGH,
            f'0/{ev_total} evidence documents independently verified',
            'All documents remain in "Pending" or "Rejected" state. Third-party verification '
            'is the foundation of the Transparency pillar — absence means claims are unconfirmed.',
            source='evidence', source_label='Evidence base',
            confidence=0.95, score_impact=-8.0,
        ))
    elif ev_total == 0:
        factors.append(_f(
            CAT_PENALTY, SEVERITY_CRITICAL,
            'No evidence documents in the EcoIQ evidence base',
            'Transparency score cannot be substantiated without disclosure documents. '
            'Companies with zero documented evidence receive a maximum score of 15/100 '
            'in the Transparency pillar.',
            source='evidence', source_label='Evidence base',
            confidence=0.99, score_impact=-15.0,
        ))

    if score < 60:
        factors.append(_f(
            CAT_PENALTY, SEVERITY_MEDIUM,
            f'Transparency score {score}/100 — insufficient public disclosure depth',
            'Score below 60 indicates disclosure gaps that prevent institutional investors '
            'from conducting full ESG due diligence under MSCI, TCFD, or GRI Standards.',
            source='rule', source_label='EcoIQ scoring',
            confidence=0.88, score_impact=-5.0,
        ))

    # ── MISSING DISCLOSURES ───────────────────────────────────────────────────

    std_frameworks = ('gri', 'tcfd', 'cdp', 'sustainability report', 'esg report')
    has_framework = any(
        any(kw in e.title.lower() for kw in std_frameworks) for e in evidence
    )
    if not has_framework:
        factors.append(_f(
            CAT_MISSING, SEVERITY_HIGH,
            'No GRI/TCFD/CDP-aligned report detected',
            'Annual sustainability report aligned to GRI Standards, TCFD framework, or CDP '
            'questionnaire is required for MSCI ESG rating category A/AA. Its absence is the '
            'single largest driver of below-60 Transparency scores.',
            source='evidence', source_label='Evidence base',
            confidence=0.85, score_impact=-6.0,
        ))

    for gap in data_gaps:
        if any(kw in gap.lower() for kw in ('cdp', 'gri', 'tcfd', 'report', 'disclosure', 'histor')):
            factors.append(_f(
                CAT_MISSING, SEVERITY_MEDIUM,
                f'Disclosure gap: {gap[:80]}',
                gap,
                source='ai_finding', source_label='AI Data Gap Analysis',
                confidence=0.83, score_impact=-2.0,
            ))
            break

    # ── RISKS ─────────────────────────────────────────────────────────────────

    for f in ai_fndgs:
        if f.finding_type == 'greenwashing' and any(
            kw in (f.title + f.description).lower()
            for kw in ('disclosure', 'report', 'transparent', 'hidden', 'undisclosed', 'not report')
        ):
            factors.append(_f(
                CAT_RISK, SEVERITY_HIGH,
                f.title[:90],
                f.description[:240],
                source='ai_finding', source_label='AI Greenwashing Signal',
                confidence=f.confidence_score, score_impact=-4.0,
                quote=f.source_quote[:120] if f.source_quote else '',
            ))

    return _pillar_result('transparency', 'Transparency', 'Transparency',
                          10, score, '#f59e0b', factors, d3m, d12m)


def _explain_community(company, ctx: Dict) -> Dict:
    """Community Impact — weight 10%"""
    score    = company.score_community_impact
    factors  = []
    projects = ctx['all_projects']
    evidence = ctx['evidence']
    ai_fndgs = ctx.get('ai_findings', [])
    se       = ctx.get('ai_score_estimate')
    d3m      = ctx.get('delta_3m_community')
    d12m     = ctx.get('delta_12m_community')

    data_gaps = (se.data_gaps if se else []) or []

    total_hh = sum(p.households_helped or 0 for p in projects)
    community_types = {'coal_stove', 'tree_planting', 'water_cleanup', 'filters'}
    community_projects = [p for p in projects if p.project_type in community_types]

    # ── DRIVERS ───────────────────────────────────────────────────────────────

    if total_hh > 0:
        factors.append(_f(
            CAT_DRIVER, SEVERITY_POSITIVE,
            f'{total_hh:,} households directly benefiting from environmental projects',
            'Direct household-level impact is the primary Community Impact metric. '
            'Coal-stove replacement and clean water access score highest in this pillar.',
            source='projects', source_label='Project metrics',
            confidence=0.91, score_impact=+8.0,
            numeric_value=float(total_hh), unit='households',
        ))

    if community_projects:
        factors.append(_f(
            CAT_DRIVER, SEVERITY_POSITIVE,
            f'{len(community_projects)} community-focused project(s) active or completed',
            'Direct community-impact project types (coal stove replacement, tree planting, '
            'water clean-up) receive maximum Community Impact weighting.',
            source='projects', source_label='Project types',
            confidence=0.88, score_impact=+5.0,
        ))

    if d12m is not None and d12m >= 3:
        factors.append(_f(
            CAT_DRIVER, SEVERITY_POSITIVE,
            f'Community Impact improved {d12m:+.1f} pts in 12 months',
            'Sustained improvement over 12-month window — trend indicates expanding '
            'community programme coverage.',
            source='score_history', source_label='Score History',
            confidence=0.94, score_impact=+d12m,
        ))

    # ── PENALTIES ─────────────────────────────────────────────────────────────

    if score < 40:
        factors.append(_f(
            CAT_PENALTY, SEVERITY_HIGH,
            f'Community Impact {score}/100 — limited measurable community benefit',
            'Score below 40 indicates absence of documented community-level impact. '
            'For industrial operators near populated areas, this represents a significant '
            'social licence risk.',
            source='rule', source_label='EcoIQ scoring',
            confidence=0.93, score_impact=-8.0,
        ))
    elif score < 60:
        factors.append(_f(
            CAT_PENALTY, SEVERITY_MEDIUM,
            f'Community Impact {score}/100 — below transition benchmark',
            'Transition Leaders require evidence of measurable community health outcomes '
            '(air quality, health data) and documented community engagement processes.',
            source='rule', source_label='EcoIQ scoring',
            confidence=0.87, score_impact=-4.0,
        ))

    # ── MISSING DISCLOSURES ───────────────────────────────────────────────────

    if total_hh == 0:
        factors.append(_f(
            CAT_MISSING, SEVERITY_HIGH,
            'No household or community beneficiary data recorded',
            'Community Impact cannot be quantified without beneficiary data. Open-data '
            'air quality sensor networks, community health surveys, and '
            'documented stakeholder engagement are standard evidence inputs.',
            source='evidence', source_label='Evidence base',
            confidence=0.88, score_impact=-6.0,
        ))

    for gap in data_gaps:
        if any(kw in gap.lower() for kw in ('community', 'social', 'health', 'household', 'population')):
            factors.append(_f(
                CAT_MISSING, SEVERITY_MEDIUM,
                f'Social impact gap: {gap[:80]}',
                gap,
                source='ai_finding', source_label='AI Data Gap Analysis',
                confidence=0.82, score_impact=-2.0,
            ))
            break

    if not any(p.project_type in community_types for p in projects):
        factors.append(_f(
            CAT_MISSING, SEVERITY_MEDIUM,
            'No direct community-benefit projects detected',
            'No coal-stove replacement, tree planting, water clean-up, or community filter '
            'projects found. These project types are the primary evidence-based drivers of '
            'Community Impact scoring.',
            source='rule', source_label='Project analysis',
            confidence=0.80, score_impact=-4.0,
        ))

    # ── RISKS ─────────────────────────────────────────────────────────────────

    # If sector is high-impact and community score is low
    if company.sector in ('oil_gas', 'mining', 'chemical') and score < 55:
        factors.append(_f(
            CAT_RISK, SEVERITY_MEDIUM,
            'Low community engagement score for high-impact industrial sector',
            f'{company.get_sector_display()} operations near populated areas require '
            'community liaison, health monitoring, and regular stakeholder reporting. '
            'Absence creates social licence risk and potential regulatory exposure.',
            source='rule', source_label='Sector analysis',
            confidence=0.76, score_impact=-3.0,
        ))

    return _pillar_result('community', 'Community Impact', 'Community',
                          10, score, '#8b5cf6', factors, d3m, d12m)


# ── Delta helpers ──────────────────────────────────────────────────────────────

def _pillar_deltas(company, field_name: str) -> tuple:
    """Return (delta_3m, delta_12m) for a pillar from ScoreHistory."""
    from datetime import date, timedelta
    qs = company.history.order_by('-date')

    current = getattr(company, field_name, None)
    if current is None:
        return None, None

    snap3  = qs.filter(date__lte=date.today() - timedelta(days=90)).first()
    snap12 = qs.filter(date__lte=date.today() - timedelta(days=365)).first()

    d3m  = round(current - getattr(snap3,  field_name, current), 1) if snap3  else None
    d12m = round(current - getattr(snap12, field_name, current), 1) if snap12 else None
    return d3m, d12m


# ── Main entry point ───────────────────────────────────────────────────────────

def explain_company(company, view_ctx: Dict) -> List[Dict]:
    """
    Generate explainability data for all 5 EcoIQ pillars.

    Parameters
    ----------
    company  : Company instance (with prefetched projects, evidence, history)
    view_ctx : dict already assembled in company_profile() view

    Returns
    -------
    List of 5 dicts, one per pillar, ready for Django template rendering.
    """

    ctx = dict(view_ctx)

    # ── Per-pillar score deltas ────────────────────────────────────────────────
    for field, key in [
        ('score_pollution_footprint', 'pollution'),
        ('score_reduction_progress',  'reduction'),
        ('score_investment',          'investment'),
        ('score_transparency',        'transparency'),
        ('score_community_impact',    'community'),
    ]:
        d3, d12 = _pillar_deltas(company, field)
        ctx[f'delta_3m_{key}']  = d3
        ctx[f'delta_12m_{key}'] = d12

    return [
        _explain_pollution   (company, ctx),
        _explain_reduction   (company, ctx),
        _explain_investment  (company, ctx),
        _explain_transparency(company, ctx),
        _explain_community   (company, ctx),
    ]
