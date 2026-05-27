"""
EcoIQ Company Intelligence — Improvement Pathway Engine.

Generates an "Improvement Pathway" for a CompanyProfile: a set of scored
milestone cards explaining how the company can raise its EcoIQ score, plus
a score trajectory block showing current → potential range.

All outputs are indicative / AI-assisted. No engineering, legal or investment
advice is implied. Milestones are generated from static templates matched
against actual profile scores — no LLM call, no async work.

Milestone schema
────────────────
  key                str         internal identifier
  title              str         display name
  why_it_matters     str         one-sentence business rationale
  uplift_low         int         conservative estimated score uplift
  uplift_high        int         optimistic estimated score uplift
  difficulty         str         'low' | 'medium' | 'high'
  timeline           str         human-readable estimate
  finance_compat     list[str]   indicative finance instruments
  kpi_improvements   list[str]   measurable KPI changes
  public_benefit     str         expected public-benefit outcome
  governance_reqs    str         governance prerequisites
  status             str         'not_started'|'in_progress'|'achievable'|'advanced'
  status_label       str         display label for status badge
  relevant_score     float       the underlying profile score that drives status
  priority           int         lower = higher priority (for sorting)

Trajectory schema
─────────────────
  current            float       profile.ecoiq_total_score
  potential_low      float       conservative uplift scenario
  potential_high     float       optimistic uplift scenario (capped 95)
  gap_to_100         float       100 - current
  uplift_range_low   int         sum of milestone uplift_low values
  uplift_range_high  int         sum of milestone uplift_high values
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from companies.models import CompanyProfile


# ── Status helpers ────────────────────────────────────────────────────────────

def _status(score: float) -> tuple[str, str]:
    """Return (status_key, status_label) from a 0-100 score."""
    s = float(score or 0)
    if s >= 75:
        return ('advanced',    'Advanced')
    elif s >= 55:
        return ('achievable',  'Achievable')
    elif s >= 40:
        return ('in_progress', 'In Progress')
    else:
        return ('not_started', 'Not Started')


def _clamp(v, lo=0.0, hi=100.0) -> float:
    return max(lo, min(hi, float(v or 0)))


# ── Milestone template library ────────────────────────────────────────────────

def _build_milestones(p: 'CompanyProfile') -> list[dict]:
    """Build the full ordered list of milestone dicts from live profile scores."""

    # Derive convenience fields
    pol        = p.pollution_level           # 'low'|'medium'|'high'|'severe'
    transp     = _clamp(p.transparency_score_detail)
    energy     = _clamp(p.energy_transition_score)
    waste      = _clamp(p.waste_management_score)
    anti_corr  = _clamp(p.anti_corruption_score)
    jobs       = _clamp(p.jobs_created_score)
    biodiv     = _clamp(p.biodiversity_impact_score)
    future     = _clamp(p.future_readiness_score)
    audit      = _clamp(p.audit_quality_score)
    procure    = _clamp(p.procurement_transparency_score)
    renew      = _clamp(p.renewable_energy_share or 0)  # 0-100 %

    # --------------------------------------------------------------------------
    # Emissions Monitoring
    # --------------------------------------------------------------------------
    em_score = min(transp, 100 - (_clamp(p.controversy_risk_score)))
    em_status, em_label = _status(em_score)
    milestones = [
        {
            'key':           'emissions_monitoring',
            'title':         'Establish Emissions Monitoring',
            'why_it_matters':(
                'Accurate, verified baseline data is required by every major financing '
                'body and investor framework. Without it, score ceilings apply across '
                'Environmental Stewardship and Transparent Governance pillars.'
            ),
            'uplift_low':    4,
            'uplift_high':   9,
            'difficulty':    'low',
            'timeline':      '1–6 months',
            'finance_compat':['CDP disclosure frameworks', 'EBRD environmental covenant',
                              'IFC performance standards', 'GCF reporting baseline'],
            'kpi_improvements': [
                'CO₂e baseline established and published',
                'Scope 1 & 2 emissions tracked quarterly',
                'Third-party emissions verification in place',
            ],
            'public_benefit': (
                'Improved air quality and industrial health data transparency '
                'for surrounding communities.'
            ),
            'governance_reqs': (
                'Board-level sign-off on climate disclosure; appoint an environmental '
                'reporting officer or equivalent.'
            ),
            'status':         em_status,
            'status_label':   em_label,
            'relevant_score': em_score,
            'priority':       10 if em_status == 'not_started' else 30,
        },
    ]

    # --------------------------------------------------------------------------
    # Methane Reduction
    # --------------------------------------------------------------------------
    meth_score = energy if pol in ('high', 'severe') else max(energy, 60.0)
    meth_status, meth_label = _status(meth_score)
    milestones.append({
        'key':           'methane_reduction',
        'title':         'Methane and Emissions Leakage Reduction',
        'why_it_matters':(
            'Methane has 80× the warming potency of CO₂ over 20 years. Uncontrolled '
            'leakage creates regulatory exposure under EU CBAM and OGMP 2.0, and '
            'directly depresses the Environmental Stewardship pillar.'
        ),
        'uplift_low':    5,
        'uplift_high':   12,
        'difficulty':    'medium',
        'timeline':      '6–18 months',
        'finance_compat':['EBRD Green Economy Financing', 'IFC Climate Finance',
                          'OGMP 2.0 partner facility', 'EU Innovation Fund'],
        'kpi_improvements': [
            'Methane intensity (tCH₄/production unit) reduced ≥30%',
            'LDAR programme operational across all major sites',
            'Independent emissions verification report published',
        ],
        'public_benefit': (
            'Measurable improvement in local air quality and reduced long-term '
            'climate impact for communities near industrial facilities.'
        ),
        'governance_reqs': (
            'Leak Detection and Repair (LDAR) programme formally adopted; results '
            'subject to independent third-party audit at least annually.'
        ),
        'status':         meth_status,
        'status_label':   meth_label,
        'relevant_score': meth_score,
        'priority':       8 if pol in ('high', 'severe') else 25,
    })

    # --------------------------------------------------------------------------
    # Energy Efficiency Upgrades
    # --------------------------------------------------------------------------
    eff_score  = energy
    eff_status, eff_label = _status(eff_score)
    milestones.append({
        'key':           'energy_efficiency',
        'title':         'Energy Efficiency Upgrades',
        'why_it_matters':(
            'Energy efficiency is the fastest-payback route to improving the '
            'Responsible Modernization score. It reduces operating costs, '
            'lowers emissions, and demonstrates transition commitment to financiers.'
        ),
        'uplift_low':    4,
        'uplift_high':   10,
        'difficulty':    'medium',
        'timeline':      '6–24 months',
        'finance_compat':['KfW Energy Efficiency Programme', 'AIIB co-financing',
                          'Innovate UK Net Zero grants', 'Commercial green bonds'],
        'kpi_improvements': [
            'Energy intensity (kWh / unit output) reduced ≥20%',
            'Heat recovery and cogeneration capacity installed',
            'ISO 50001 energy management certification achieved',
        ],
        'public_benefit': (
            'Lower industrial energy consumption reduces pressure on national grid, '
            'supporting broader energy access and stability.'
        ),
        'governance_reqs': (
            'Energy audit conducted by accredited third party; improvement targets '
            'formally approved by management and disclosed publicly.'
        ),
        'status':         eff_status,
        'status_label':   eff_label,
        'relevant_score': eff_score,
        'priority':       12 if eff_score < 50 else 28,
    })

    # --------------------------------------------------------------------------
    # Renewable Energy Integration
    # --------------------------------------------------------------------------
    ren_score  = max(energy, renew)
    ren_status, ren_label = _status(ren_score)
    milestones.append({
        'key':           'renewable_integration',
        'title':         'Renewable Energy Integration',
        'why_it_matters':(
            'Renewable energy share directly drives the Energy Transition sub-score '
            'and signals bankability to climate-focused debt providers and DFIs. '
            'It is increasingly a prerequisite for institutional export markets.'
        ),
        'uplift_low':    5,
        'uplift_high':   14,
        'difficulty':    'high',
        'timeline':      '1–5 years',
        'finance_compat':['Green Climate Fund', 'ADB Clean Energy Facility',
                          'AIIB renewable co-investment', 'Private PPA structures'],
        'kpi_improvements': [
            'Renewable share of total energy ≥25%',
            'Power Purchase Agreement (PPA) with clean energy supplier signed',
            'On-site solar or wind capacity commissioned',
        ],
        'public_benefit': (
            'Accelerates national renewable capacity build-out and reduces '
            'dependence on fossil-fuel grid electricity.'
        ),
        'governance_reqs': (
            'Board-approved renewable energy strategy with interim targets; '
            'disclosed in annual sustainability report.'
        ),
        'status':         ren_status,
        'status_label':   ren_label,
        'relevant_score': ren_score,
        'priority':       11 if ren_score < 45 else 29,
    })

    # --------------------------------------------------------------------------
    # Waste Reduction Systems
    # --------------------------------------------------------------------------
    waste_status, waste_label = _status(waste)
    milestones.append({
        'key':           'waste_reduction',
        'title':         'Waste Reduction and Management Systems',
        'why_it_matters':(
            'Poor waste management directly penalises Environmental Stewardship '
            'and creates regulatory exposure. Circular waste practices also '
            'generate cost savings and unlock green product premiums.'
        ),
        'uplift_low':    3,
        'uplift_high':   8,
        'difficulty':    'medium',
        'timeline':      '3–12 months',
        'finance_compat':['EBRD Circular Economy facility', 'EIB Green Loan',
                          'National waste-to-resource grants', 'Commercial ESG revolving credit'],
        'kpi_improvements': [
            'Waste-to-landfill reduced ≥40% year-on-year',
            'ISO 14001 environmental management certification achieved',
            'Hazardous waste segregation and tracking systems in place',
        ],
        'public_benefit': (
            'Reduced industrial waste burden on local ecosystems and communities; '
            'cleaner air, water and soil in operational regions.'
        ),
        'governance_reqs': (
            'Formal waste management policy; hazardous waste officer designated; '
            'annual waste audit published in sustainability report.'
        ),
        'status':         waste_status,
        'status_label':   waste_label,
        'relevant_score': waste,
        'priority':       14 if waste < 50 else 32,
    })

    # --------------------------------------------------------------------------
    # Transparency Reporting
    # --------------------------------------------------------------------------
    rep_score  = min(transp, audit)
    rep_status, rep_label = _status(rep_score)
    milestones.append({
        'key':           'transparency_reporting',
        'title':         'Public Transparency Reporting',
        'why_it_matters':(
            'The Transparent Governance pillar (15% of score) directly requires '
            'auditable public disclosures. Strong reporting also unlocks access '
            'to a wider set of institutional financing instruments.'
        ),
        'uplift_low':    4,
        'uplift_high':   10,
        'difficulty':    'low',
        'timeline':      '1–6 months',
        'finance_compat':['CDP A-list access', 'MSCI ESG rating improvement',
                          'IFC performance standards compliance', 'GCF direct access'],
        'kpi_improvements': [
            'GRI-aligned sustainability report published annually',
            'External audit of environmental and social data',
            'CDP climate questionnaire score published',
        ],
        'public_benefit': (
            'Enables informed public, government and community oversight '
            'of industrial environmental and social performance.'
        ),
        'governance_reqs': (
            'Board-approved disclosure policy; audit committee sign-off on '
            'non-financial reporting; external assurance provider engaged.'
        ),
        'status':         rep_status,
        'status_label':   rep_label,
        'relevant_score': rep_score,
        'priority':       9 if rep_score < 50 else 27,
    })

    # --------------------------------------------------------------------------
    # Supply Chain Verification
    # --------------------------------------------------------------------------
    sc_score   = min(anti_corr, procure)
    sc_status, sc_label = _status(sc_score)
    milestones.append({
        'key':           'supply_chain_verification',
        'title':         'Supply Chain Verification',
        'why_it_matters':(
            'Unverified supply chains create hidden ESG risk exposure that '
            'depresses Anti-Corruption and Ethical Alignment scores. '
            'Verified supply chains are increasingly required by export markets.'
        ),
        'uplift_low':    3,
        'uplift_high':   8,
        'difficulty':    'medium',
        'timeline':      '6–18 months',
        'finance_compat':['IFC supplier finance programmes', 'Responsible sourcing bonds',
                          'EU supply chain due diligence compliance finance'],
        'kpi_improvements': [
            'Tier-1 supplier environmental audits completed (100%)',
            'Supplier Code of Conduct adopted and monitored',
            'Beneficial ownership disclosed for major contractors',
        ],
        'public_benefit': (
            'Reduces hidden harm in supply chain; prevents forced labour, '
            'environmental violations and corrupt procurement practices.'
        ),
        'governance_reqs': (
            'Supplier Code of Conduct published; procurement officer trained '
            'in ESG due diligence; third-party supply chain audit commissioned.'
        ),
        'status':         sc_status,
        'status_label':   sc_label,
        'relevant_score': sc_score,
        'priority':       15 if sc_score < 50 else 33,
    })

    # --------------------------------------------------------------------------
    # Worker Safety Modernization
    # --------------------------------------------------------------------------
    ws_score   = jobs
    ws_status, ws_label = _status(ws_score)
    milestones.append({
        'key':           'worker_safety',
        'title':         'Worker Safety Modernization',
        'why_it_matters':(
            'Employment quality is the largest sub-driver of the Public Benefit '
            'pillar (25% of score). Strong safety and welfare practices also '
            'reduce operational disruption risk and improve DFI eligibility.'
        ),
        'uplift_low':    3,
        'uplift_high':   9,
        'difficulty':    'medium',
        'timeline':      '3–12 months',
        'finance_compat':['ILO Better Work finance', 'DFI social performance covenants',
                          'Worker welfare improvement grants', 'Blended finance social bonds'],
        'kpi_improvements': [
            'Lost Time Injury Rate (LTIR) reduced ≥50%',
            'ISO 45001 occupational health and safety certification achieved',
            'Living wage policy implemented for all direct employees',
        ],
        'public_benefit': (
            'Direct reduction in workplace injuries and fatalities; improved '
            'worker welfare and regional economic stability.'
        ),
        'governance_reqs': (
            'Safety management system aligned with ISO 45001; independent '
            'safety audit conducted annually; results disclosed publicly.'
        ),
        'status':         ws_status,
        'status_label':   ws_label,
        'relevant_score': ws_score,
        'priority':       13 if ws_score < 55 else 31,
    })

    # --------------------------------------------------------------------------
    # Circular Economy Improvements
    # --------------------------------------------------------------------------
    circ_score = min(waste, biodiv)
    circ_status, circ_label = _status(circ_score)
    milestones.append({
        'key':           'circular_economy',
        'title':         'Circular Economy Improvements',
        'why_it_matters':(
            'Circular economy practices jointly improve Waste Management and '
            'Biodiversity sub-scores, compound the Environmental Stewardship '
            'pillar score, and create new revenue streams from recovered materials.'
        ),
        'uplift_low':    3,
        'uplift_high':   9,
        'difficulty':    'high',
        'timeline':      '1–4 years',
        'finance_compat':['EBRD Circular Economy Facility', 'EU Circular Economy Fund',
                          'Nature-based finance instruments', 'Commercial green bonds'],
        'kpi_improvements': [
            'Material recirculation rate ≥30% of total inputs',
            'Industrial symbiosis partnerships established',
            'Biodiversity net gain assessment completed and targets set',
        ],
        'public_benefit': (
            'Reduced resource extraction pressure on ecosystems; '
            'improved biodiversity and cleaner local environment.'
        ),
        'governance_reqs': (
            'Circular economy strategy formally adopted; material flow '
            'accounting conducted annually; biodiversity officer designated.'
        ),
        'status':         circ_status,
        'status_label':   circ_label,
        'relevant_score': circ_score,
        'priority':       16 if circ_score < 50 else 34,
    })

    # Sort: not_started first, then in_progress, then achievable, then advanced
    # Within each group, sort by priority (lower = more urgent)
    status_order = {'not_started': 0, 'in_progress': 1, 'achievable': 2, 'advanced': 3}
    milestones.sort(key=lambda m: (status_order[m['status']], m['priority']))
    return milestones


# ── Trajectory ────────────────────────────────────────────────────────────────

def _build_trajectory(p: 'CompanyProfile', milestones: list[dict]) -> dict:
    current = _clamp(p.ecoiq_total_score)
    # Include uplift from not_started, in_progress and achievable (partial credit for achievable)
    active = [m for m in milestones if m['status'] in ('not_started', 'in_progress')]
    partial = [m for m in milestones if m['status'] == 'achievable']
    total_low  = (sum(m['uplift_low']  for m in active)
                  + sum(m['uplift_low']  // 2 for m in partial))
    total_high = (sum(m['uplift_high'] for m in active)
                  + sum(m['uplift_high'] // 3 for m in partial))
    pot_low  = min(95.0, current + total_low)
    pot_high = min(97.0, current + total_high)
    return {
        'current':         round(current, 1),
        'potential_low':   round(pot_low, 1),
        'potential_high':  round(pot_high, 1),
        'gap_to_100':      round(100 - current, 1),
        'uplift_low':      total_low,
        'uplift_high':     total_high,
        # Percentages for the visual bar (0-100 scale = 0-97 EcoIQ)
        'current_pct':     round(min(current / 97 * 100, 100), 1),
        'low_pct':         round(min(pot_low  / 97 * 100, 100), 1),
        'high_pct':        round(min(pot_high / 97 * 100, 100), 1),
    }


# ── Public API ────────────────────────────────────────────────────────────────

DISCLAIMER = (
    'EcoIQ pathways are AI-assisted indicative intelligence and not verified '
    'engineering, legal or investment advice.'
)


def get_improvement_pathway(profile: 'CompanyProfile') -> dict:
    """
    Return the full Improvement Pathway for a CompanyProfile.

    Returns:
      {
        'milestones': list[dict],   — ordered list of milestone cards
        'trajectory': dict,         — score trajectory block
        'disclaimer': str,          — mandatory disclaimer text
      }
    """
    milestones = _build_milestones(profile)
    trajectory = _build_trajectory(profile, milestones)
    return {
        'milestones': milestones,
        'trajectory': trajectory,
        'disclaimer': DISCLAIMER,
    }
