"""
EcoIQ Financing Intelligence — Matching Engine.

Lightweight, synchronous scoring engine:
  get_or_compute(profile)    → CompanyFinancingProfile (lazy)
  compute_and_save(profile)  → CompanyFinancingProfile (always recomputes)
  compute_financing_profile  → dict  (no DB write)

No Celery, no external calls — derives everything from existing CompanyProfile fields.
"""
import logging

from django.db import transaction

from core.unknown import known, weighted_mean_of_known

log = logging.getLogger(__name__)

# ── Country → region mapping ───────────────────────────────────────────────────

_COUNTRY_REGION = {
    # Central Asia
    'Kazakhstan': 'Central Asia', 'Uzbekistan': 'Central Asia',
    'Kyrgyzstan': 'Central Asia', 'Tajikistan': 'Central Asia',
    'Turkmenistan': 'Central Asia', 'Mongolia': 'Central Asia',
    # Eastern Europe
    'Ukraine': 'Eastern Europe', 'Poland': 'Eastern Europe',
    'Romania': 'Eastern Europe', 'Bulgaria': 'Eastern Europe',
    'Serbia': 'Eastern Europe', 'Moldova': 'Eastern Europe',
    'Belarus': 'Eastern Europe', 'Russia': 'Eastern Europe',
    'Hungary': 'Eastern Europe', 'Slovakia': 'Eastern Europe',
    'Czech Republic': 'Eastern Europe', 'Croatia': 'Eastern Europe',
    'Bosnia': 'Eastern Europe', 'North Macedonia': 'Eastern Europe',
    'Albania': 'Eastern Europe', 'Kosovo': 'Eastern Europe',
    # Caucasus
    'Georgia': 'Caucasus', 'Armenia': 'Caucasus', 'Azerbaijan': 'Caucasus',
    # South Asia
    'India': 'South Asia', 'Pakistan': 'South Asia', 'Bangladesh': 'South Asia',
    'Sri Lanka': 'South Asia', 'Nepal': 'South Asia', 'Bhutan': 'South Asia',
    # Southeast Asia
    'Vietnam': 'Southeast Asia', 'Indonesia': 'Southeast Asia',
    'Thailand': 'Southeast Asia', 'Philippines': 'Southeast Asia',
    'Malaysia': 'Southeast Asia', 'Myanmar': 'Southeast Asia',
    'Cambodia': 'Southeast Asia', 'Laos': 'Southeast Asia',
    # Sub-Saharan Africa
    'Nigeria': 'Sub-Saharan Africa', 'South Africa': 'Sub-Saharan Africa',
    'Kenya': 'Sub-Saharan Africa', 'Ghana': 'Sub-Saharan Africa',
    'Tanzania': 'Sub-Saharan Africa', 'Ethiopia': 'Sub-Saharan Africa',
    'Uganda': 'Sub-Saharan Africa', 'Mozambique': 'Sub-Saharan Africa',
    'Zambia': 'Sub-Saharan Africa', 'Zimbabwe': 'Sub-Saharan Africa',
    'Senegal': 'Sub-Saharan Africa', 'Ivory Coast': 'Sub-Saharan Africa',
    # MENA
    'Saudi Arabia': 'MENA', 'UAE': 'MENA', 'Qatar': 'MENA',
    'Kuwait': 'MENA', 'Bahrain': 'MENA', 'Oman': 'MENA',
    'Jordan': 'MENA', 'Egypt': 'MENA', 'Morocco': 'MENA',
    'Algeria': 'MENA', 'Tunisia': 'MENA', 'Iraq': 'MENA',
    'Libya': 'MENA', 'Lebanon': 'MENA', 'Yemen': 'MENA',
    # Latin America
    'Brazil': 'Latin America', 'Mexico': 'Latin America',
    'Colombia': 'Latin America', 'Argentina': 'Latin America',
    'Chile': 'Latin America', 'Peru': 'Latin America',
    'Ecuador': 'Latin America', 'Bolivia': 'Latin America',
    # East Asia
    'China': 'East Asia', 'Japan': 'East Asia',
    'South Korea': 'East Asia', 'Taiwan': 'East Asia',
    # Western Europe
    'France': 'Western Europe', 'Germany': 'Western Europe',
    'Spain': 'Western Europe', 'Italy': 'Western Europe',
    'United Kingdom': 'Western Europe', 'Netherlands': 'Western Europe',
    'Belgium': 'Western Europe', 'Sweden': 'Western Europe',
    'Norway': 'Western Europe', 'Denmark': 'Western Europe',
    'Finland': 'Western Europe', 'Austria': 'Western Europe',
    'Switzerland': 'Western Europe', 'Portugal': 'Western Europe',
    'Greece': 'Western Europe',
    # North America
    'United States': 'North America', 'Canada': 'North America',
    # Pacific
    'Australia': 'Pacific', 'New Zealand': 'Pacific',
    'Papua New Guinea': 'Pacific', 'Fiji': 'Pacific',
}


# ── Unknown handling ──────────────────────────────────────────────────────────

def _known(value):
    """
    A score if it is known, else None.

    Replaces the `value or 50` idiom that appeared 25 times in this module.
    That idiom failed twice over:

      - an unknown score became 50, so a company we had no data about was
        matched, tiered and quoted as if it were average;
      - `or` is falsy-triggered, so a genuine measured 0.0 ALSO became 50 —
        turning the worst real observation into an average one.

    Callers must decide explicitly what an unknown means for them. Where the
    value drives a threshold, the threshold simply does not fire: absence of
    evidence is not evidence that a company needs financing, any more than it is
    evidence of harm.

    Delegates to core.unknown since D2c — one authority, parity asserted by test.
    """
    return known(value)


def _weighted(*pairs):
    """
    Weighted mean over the KNOWN (value, weight) pairs, re-normalised.

    Dropping an unknown term from a weighted sum without re-normalising would
    quietly shrink the dimension — a company missing one input would score lower
    than an identical company that has it, purely for the absence. Re-weighting
    across what is known keeps the scale honest; None when nothing is known.

    Delegates to core.unknown since D2c. Note core's version also clamps each
    value, which this one did not — a difference with no effect here, since
    every caller already passes profile scores bounded to 0-100, and clamping a
    value already inside the range is a no-op. Asserted by test rather than
    assumed.
    """
    return weighted_mean_of_known(*pairs)


def _get_region(country: str) -> str:
    return _COUNTRY_REGION.get(country, 'Other')


# ── Geographic scoring ─────────────────────────────────────────────────────────

def _geo_score(company_country: str, opportunity) -> int:
    """Returns 0–30 geographic match score."""
    eligible_countries = opportunity.eligible_countries or []
    eligible_regions   = opportunity.eligible_regions or []

    if company_country in eligible_countries:
        return 30
    if 'Global' in eligible_regions:
        return 22
    region = _get_region(company_country)
    if region in eligible_regions:
        return 25
    # Partial — Western Europe companies can still access Global DFIs
    if region in ('Western Europe', 'North America'):
        return 10
    return 4


# ── Focus area scoring ─────────────────────────────────────────────────────────

def _focus_score(profile, opportunity) -> int:
    """Returns 0–20 focus area match score."""
    focus  = set(opportunity.focus_areas or [])
    if not focus:
        return 12  # universal instrument

    # `pollution_level or 'medium'` is left alone deliberately: 'medium' is the
    # model's own documented default for that CharField, not a stand-in for
    # missing evidence, and the branch below only fires on high/severe.
    pollution = profile.pollution_level or 'medium'
    mod = _known(profile.modernization_score)
    energy = _known(profile.energy_transition_score)
    transparency = _known(profile.transparency_score_detail)
    water = _known(profile.water_impact_score)

    pts = 0
    # High-pollution companies need coal/industrial transition
    if pollution in ('high', 'severe'):
        if focus & {'coal_transition', 'industrial', 'methane', 'energy_efficiency'}:
            pts += 12
    # Modernization gap
    if mod is not None and mod < 60 and focus & {'industrial', 'energy_efficiency', 'renewable', 'clean_energy'}:
        pts += 6
    # Energy transition
    if energy is not None and energy < 60 and focus & {'renewable', 'clean_energy', 'energy_efficiency'}:
        pts += 5
    # Transparency / governance
    if transparency is not None and transparency < 50 and 'governance' in focus:
        pts += 4
    # Water / biodiversity
    if water is not None and water < 50 and 'water' in focus:
        pts += 3

    return min(pts, 20)


# ── Instrument fitness ─────────────────────────────────────────────────────────

def _instrument_score(profile, opportunity) -> int:
    """Returns 0–10 based on instrument type vs company profile."""
    instrument = opportunity.instrument
    # revenue or 0 is retained: the loan branch below reads it as "how much
    # revenue is demonstrated", and an undemonstrated revenue genuinely scores
    # lowest there. ecoiq is different — unknown is not a low score.
    revenue    = profile.annual_revenue or 0
    ecoiq      = _known(profile.ecoiq_total_score)
    pollution  = profile.pollution_level or 'medium'

    if instrument == 'grant':
        return 10  # grants are broadly accessible
    if instrument in ('carbon_credit',):
        return 10 if pollution in ('high', 'severe') else 4
    if instrument == 'loan':
        if revenue >= 100_000_000: return 10
        if revenue >= 20_000_000:  return 8
        if revenue >= 5_000_000:   return 5
        return 3
    if instrument == 'bond':
        return 4 if ecoiq is None else (10 if ecoiq >= 65 else 4)
    if instrument == 'blended':
        return 9
    if instrument == 'guarantee':
        return 8
    if instrument == 'equity':
        return 7
    if instrument == 'credit_line':
        return 8
    return 6


# ── EcoIQ baseline ────────────────────────────────────────────────────────────

def _ecoiq_score(ecoiq: float | None) -> int:
    """
    0–20 contribution from the EcoIQ total score, or 0 when it is unknown.

    An unknown composite previously arrived here as 0 and scored 2 — a small
    but non-zero contribution invented out of nothing. It now contributes
    nothing, which is the honest weight of an input we do not have.
    """
    if ecoiq is None: return 0
    if ecoiq >= 70: return 20
    if ecoiq >= 55: return 16
    if ecoiq >= 40: return 11
    if ecoiq >= 25: return 6
    return 2


# ── Sector fit ────────────────────────────────────────────────────────────────

def _sector_score(company_sector: str, opportunity) -> int:
    """Returns 0–10 based on sector eligibility."""
    eligible = opportunity.eligible_sectors or []
    if not eligible:
        return 10  # instrument accepts all sectors
    if company_sector in eligible:
        return 10
    return 3


# ── Master match scoring ───────────────────────────────────────────────────────

def _score_opportunity(profile, opportunity) -> float:
    """
    Score a FinancingOpportunity against a CompanyProfile.
    Returns float 0–100.
    """
    company = profile.company
    ecoiq   = _known(profile.ecoiq_total_score)

    geo        = _geo_score(company.country, opportunity)          # 0–30
    sector     = _sector_score(company.sector, opportunity)        # 0–10
    ecoiq_pts  = _ecoiq_score(ecoiq)                               # 0–20
    focus      = _focus_score(profile, opportunity)                # 0–20
    instrument = _instrument_score(profile, opportunity)           # 0–10
    # Bonus: transparency (0–10)
    # No transparency evidence means no transparency bonus — not an average one.
    _trans = _known(profile.transparency_score_detail)
    trans_bonus = 0 if _trans is None else min(int(_trans / 10), 10)

    raw = geo + sector + ecoiq_pts + focus + instrument + trans_bonus
    return min(float(raw), 100.0)


def _tier_from_score(score: float) -> str:
    if score >= 72: return 'eligible'
    if score >= 52: return 'likely'
    if score >= 32: return 'potential'
    return 'unlikely'


# ── Evidence completeness ─────────────────────────────────────────────────────

def _evidence_completeness(profile) -> float:
    score = 0
    if profile.annual_report_url:         score += 25
    if profile.sustainability_report_url: score += 20
    if profile.annual_revenue:            score += 15
    if profile.ai_summary and len(profile.ai_summary) > 200: score += 15
    src_count = profile.cited_sources.count()
    score += min(src_count * 5, 15)
    if profile.is_verified:               score += 10
    return float(min(score, 100))


# ── Readiness scores ──────────────────────────────────────────────────────────

def _clamp(v: float) -> float:
    return float(max(0.0, min(100.0, v)))


def compute_readiness(profile) -> dict:
    """Compute all six readiness dimensions from existing profile fields."""
    ev = _evidence_completeness(profile)
    # `ecoiq_total_score or 0` was the same defect in its other direction: an
    # unknown composite was treated as the worst possible one and dragged
    # financing readiness down. Unknown now simply does not contribute.
    ecoiq   = _known(profile.ecoiq_total_score)
    trans   = _known(profile.transparency_score_detail)
    gov     = _known(profile.transparency_anti_corruption_score)
    ac      = _known(profile.anti_corruption_score)
    mod     = _known(profile.modernization_score)
    energy  = _known(profile.energy_transition_score)
    env     = _known(profile.environmental_responsibility_score)
    waste   = _known(profile.waste_management_score)
    water   = _known(profile.water_impact_score)
    infra   = _known(profile.infrastructure_upgrade_score)
    future  = _known(profile.future_readiness_score)
    audit   = _known(profile.audit_quality_score)
    proc    = _known(profile.procurement_transparency_score)

    controversy = _known(profile.controversy_risk_score)
    inv_controversy = None if controversy is None else max(0, 100 - controversy)

    financing_readiness = _weighted(
        (ecoiq, 0.25), (trans, 0.25), (gov, 0.20), (mod, 0.15), (ev, 0.15))

    modernization_readiness = _weighted(
        (mod, 0.35), (energy, 0.30), (infra, 0.20), (future, 0.15))

    transparency_readiness = _weighted(
        (trans, 0.40), (audit, 0.25), (proc, 0.20), (ev, 0.15))

    climate_readiness = _weighted(
        (env, 0.35), (energy, 0.30), (waste, 0.20), (water, 0.15))

    governance_readiness = _weighted(
        (gov, 0.35), (ac, 0.30), (audit, 0.25), (inv_controversy, 0.10))

    return {
        'financing_readiness':     financing_readiness,
        'modernization_readiness': modernization_readiness,
        'transparency_readiness':  transparency_readiness,
        'climate_readiness':       climate_readiness,
        'governance_readiness':    governance_readiness,
        'evidence_completeness':   ev,
    }


def _readiness_tier(financing_readiness: float | None) -> str:
    # No readiness score means no tier claim. 'early_stage' is a judgement about
    # a company; 'unknown' is a statement about our evidence.
    if financing_readiness is None: return 'unknown'
    if financing_readiness >= 72: return 'investment_ready'
    if financing_readiness >= 55: return 'nearly_ready'
    if financing_readiness >= 38: return 'developing'
    return 'early_stage'


def _funding_urgency(profile) -> str:
    pollution = profile.pollution_level or 'medium'
    # Bound with _known: an unknown input must not trip a threshold. Telling a
    # company it needs to 'raise transparency to 50+' when we have never
    # measured its transparency is a fabricated recommendation.
    mod = _known(profile.modernization_score)
    ecoiq = _known(profile.ecoiq_total_score)
    if pollution == 'severe' and mod is not None and mod < 40:
        return 'critical'
    if pollution in ('severe', 'high') and mod is not None and mod < 55:
        return 'high'
    if ecoiq is not None and ecoiq < 55 and pollution in ('medium', 'high'):
        return 'medium'
    return 'low'


# ── Capex estimation ──────────────────────────────────────────────────────────

def _estimate_capex(profile):
    """
    (low, high, annual_impact) in USD, or (None, None, None).

    Every figure here is a multiple of annual revenue, so revenue is the
    material input: without it there is no estimate, only arithmetic. The old
    version substituted `annual_revenue or 50_000_000` — inventing a $50m
    company — and then floored the output at $2m/$10m, which guaranteed a
    confident-looking range for a company we knew nothing about.

    Returning None is directly storable: estimated_capex_low_usd and its
    siblings are already null=True, and CompanyFinancingProfile.capex_range_label
    already renders 'Not estimated'. That path existed and was simply
    unreachable while this function always produced numbers.
    """
    revenue = profile.annual_revenue
    if revenue is None:
        return None, None, None

    pollution = profile.pollution_level or 'medium'
    modernization = _known(profile.modernization_score)
    # An unknown modernization score means no gap multiplier, not a gap of 20.
    mod_gap = 0 if modernization is None else max(0, 70 - modernization)

    base_pct = {'severe': 0.16, 'high': 0.10, 'medium': 0.06, 'low': 0.03}.get(pollution, 0.06)
    gap_mult = 1.0 + mod_gap / 120

    lo  = max(int(revenue * base_pct * 0.45 * gap_mult), 2_000_000)
    hi  = max(int(revenue * base_pct * 2.20 * gap_mult), 10_000_000)
    imp = max(int((lo + hi) / 2 * 0.18), 1_000_000)
    return lo, hi, imp


# ── Missing requirements ──────────────────────────────────────────────────────

def generate_missing_requirements(profile) -> list:
    reqs = []
    # Bound with _known: an unknown input must not trip a threshold. Telling a
    # company it needs to 'raise transparency to 50+' when we have never
    # measured its transparency is a fabricated recommendation.
    trans = _known(profile.transparency_score_detail)
    ac = _known(profile.anti_corruption_score)
    ecoiq = _known(profile.ecoiq_total_score)

    if not profile.annual_report_url:
        reqs.append({
            'label':    'Annual Report',
            'detail':   'Most DFIs require an audited annual report for financial due diligence.',
            'priority': 'critical',
            'impact':   20,
        })

    if not profile.sustainability_report_url:
        reqs.append({
            'label':    'ESG / Sustainability Disclosure',
            'detail':   'Climate funds require ESG disclosure aligned with GRI, TCFD, or SASB.',
            'priority': 'high',
            'impact':   15,
        })

    if ecoiq is not None and ecoiq < 40:
        reqs.append({
            'label':    'EcoIQ Minimum Score',
            'detail':   f'Score {ecoiq:.0f}/100 — most instruments require 40+ for initial eligibility.',
            'priority': 'high',
            'impact':   25,
        })

    if trans is not None and trans < 50:
        reqs.append({
            'label':    'Transparency Improvement',
            'detail':   f'Transparency {trans:.0f}/100 — DFIs require minimum 50+ for standard programmes.',
            'priority': 'high',
            'impact':   12,
        })

    if ac is not None and ac < 50:
        reqs.append({
            'label':    'Anti-Corruption Policy',
            'detail':   'Documented anti-corruption and compliance framework required by most DFIs.',
            'priority': 'medium',
            'impact':   10,
        })

    if not profile.annual_revenue:
        reqs.append({
            'label':    'Financial Data',
            'detail':   'Revenue and financial metrics are required for loan and guarantee sizing.',
            'priority': 'medium',
            'impact':   8,
        })

    return reqs


def _generate_next_actions(profile, matches) -> list:
    actions = []
    # Bound with _known: an unknown input must not trip a threshold. Telling a
    # company it needs to 'raise transparency to 50+' when we have never
    # measured its transparency is a fabricated recommendation.
    ecoiq = _known(profile.ecoiq_total_score)
    trans = _known(profile.transparency_score_detail)
    pollution = profile.pollution_level or 'medium'
    mod = _known(profile.modernization_score)

    eligible_count = sum(1 for m in matches if m.get('match_tier') == 'eligible')

    if not profile.annual_report_url:
        actions.append('Publish a current annual report to satisfy DFI documentation requirements.')
    if not profile.sustainability_report_url:
        actions.append('Prepare ESG / sustainability disclosure aligned with GRI or TCFD standards.')
    if trans is not None and trans < 50:
        actions.append(f'Increase transparency score from {trans:.0f} to 50+ by improving reporting quality and governance disclosures.')
    if pollution in ('high', 'severe') and mod is not None and mod < 60:
        actions.append('Develop a structured modernization programme with documented milestones and environmental targets.')
    if ecoiq is not None and ecoiq < 55:
        actions.append(f'Raise EcoIQ score from {ecoiq:.0f} to 55+ to expand access to standard DFI programmes.')
    if eligible_count == 0:
        actions.append('Engage a development finance advisor to support application preparation and co-financing structuring.')
    else:
        actions.append(f'Proceed with pre-application discussions with {eligible_count} matched eligible institution(s).')
    if not profile.annual_revenue:
        actions.append('Provide audited financial statements and revenue data to enable instrument sizing.')

    return actions[:6]


# ── Match rationale ────────────────────────────────────────────────────────────

def _match_rationale(profile, opportunity, score: float, tier: str) -> str:
    opp   = opportunity
    parts = []
    company_country = profile.company.country

    if company_country in (opp.eligible_countries or []):
        parts.append(f'{company_country} is a direct eligible country')
    elif 'Global' in (opp.eligible_regions or []):
        parts.append('instrument is globally available')
    else:
        region = _get_region(company_country)
        if region in (opp.eligible_regions or []):
            parts.append(f'{region} region is eligible')

    if opp.focus_areas:
        pollution = profile.pollution_level or 'medium'
        if pollution in ('high', 'severe') and any(
            f in opp.focus_areas for f in ['coal_transition', 'industrial', 'methane']
        ):
            parts.append('focus areas align with pollution reduction priorities')

    if not parts:
        parts.append('general eligibility based on instrument type and sector')

    return f'{tier.title().replace("_"," ")} match ({score:.0f}/100) — {"; ".join(parts)}.'


def _match_missing(profile, opportunity) -> list:
    missing = []
    # Bound with _known: an unknown input must not trip a threshold. Telling a
    # company it needs to 'raise transparency to 50+' when we have never
    # measured its transparency is a fabricated recommendation.
    trans = _known(profile.transparency_score_detail)
    ecoiq = _known(profile.ecoiq_total_score)
    revenue = profile.annual_revenue or 0

    if opportunity.instrument == 'loan' and revenue < 5_000_000:
        missing.append('Revenue documentation needed for loan sizing')
    if ecoiq is not None and ecoiq < 40:
        missing.append(f'EcoIQ score below minimum threshold ({ecoiq:.0f}/100 — target 40+)')
    if trans is not None and trans < 40 and opportunity.source_type in ('dfi', 'climate_fund'):
        missing.append(f'Transparency score {trans:.0f}/100 below DFI standard (target 50+)')
    if not profile.annual_report_url:
        missing.append('Annual report not on file')
    return missing


def _recommended_amount(profile, opportunity) -> int | None:
    """
    A recommended ticket size, or None when there is no capex estimate.

    A latent crash, surfaced by D3C-3d's tests. #242 correctly made
    _estimate_capex return (None, None, None) when annual_revenue is unknown —
    it had been inventing a $50m company — but this caller still did
    `(lo + hi) // 2` and raised TypeError.

    It went unnoticed because companies/views.py wraps the financing call in a
    bare `except: pass`, so the panel silently vanished instead of erroring.
    annual_revenue is NULL for every profile in the current dataset, so this
    fired on every company page that reached a financing match.

    Returning None is the honest answer and the one the signature already
    promised: without a capex estimate there is no ticket size to recommend.
    """
    lo, hi, _ = _estimate_capex(profile)
    if lo is None or hi is None:
        return None
    avg = (lo + hi) // 2
    mn, mx = opportunity.min_ticket_usd or 0, opportunity.max_ticket_usd or 0
    if mx:
        return min(avg, int(mx * 0.80))
    if mn:
        return max(avg, mn)
    return avg


# ── Full compute (no DB write) ─────────────────────────────────────────────────

def compute_financing_profile(profile) -> dict:
    """
    Compute the full financing intelligence profile without touching the DB.
    Returns a dict ready to be saved to CompanyFinancingProfile.
    """
    from transition.models import FinancingOpportunity

    readiness = compute_readiness(profile)
    cap_lo, cap_hi, impact = _estimate_capex(profile)
    tier    = _readiness_tier(readiness['financing_readiness'])
    urgency = _funding_urgency(profile)
    missing = generate_missing_requirements(profile)
    confidence = min(0.5 + (readiness['evidence_completeness'] / 200), 0.95)

    # Score all active opportunities
    opps    = list(FinancingOpportunity.objects.filter(is_active=True))
    matches = []
    for opp in opps:
        sc = _score_opportunity(profile, opp)
        mt = _tier_from_score(sc)
        if sc >= 25:  # Skip very poor matches
            matches.append({
                'opportunity':        opp,
                'match_score':        sc,
                'match_tier':         mt,
                'match_rationale':    _match_rationale(profile, opp, sc, mt),
                'missing_requirements': _match_missing(profile, opp),
                'recommended_amount_usd': _recommended_amount(profile, opp),
            })

    matches.sort(key=lambda x: -x['match_score'])
    next_actions = _generate_next_actions(profile, matches)

    return {
        'readiness':         readiness,
        'readiness_tier':    tier,
        'funding_urgency':   urgency,
        'capex_low':         cap_lo,
        'capex_high':        cap_hi,
        'impact':            impact,
        'missing':           missing,
        'next_actions':      next_actions,
        'confidence':        confidence,
        'matches':           matches,
    }


# ── DB write ──────────────────────────────────────────────────────────────────

# ── Derived provenance (D3C-3d) ───────────────────────────────────────────────

#: No methodology identifier existed here; these are the smallest stable,
#: code-owned constants. Not a git SHA, which changes on every unrelated
#: commit and so cannot answer 'did the formula change?'.
FINANCING_METHOD = 'ecoiq-financing-readiness'
FINANCING_VERSION = '1'

#: The ONE registered financing metric, and the only one this writer attests
#: to (STEP 3).
#:
#: CompanyFinancingProfile persists eleven values — five more readiness
#: dimensions, two capex bounds, an annual-impact estimate, a tier and an
#: urgency. They are semantically distinct outputs and only
#: financing.readiness is registered, so this row attests to that number
#: alone. It must NOT be read as covering the capex estimates: those were the
#: figures #242 found fabricated from an invented $50m revenue, and implying
#: provenance for them would quietly undo that finding.
#:
#: Registering the other ten is a registry decision, not a writer decision.
FINANCING_METRIC_KEY = 'financing.readiness'

#: What financing_readiness actually consumes:
#:
#:     _weighted((ecoiq, .25), (trans, .25), (gov, .20), (mod, .15), (ev, .15))
#:
#: Three of the four registered inputs are DERIVED, so this links to the
#: composite and two pillars rather than flattening back to raw material rows
#: (STEP 7). The graph should say what the formula does.
#:
#: KNOWN GAP: `ev` is _evidence_completeness(profile), computed inline from
#: profile completeness rather than read from a registered metric. It has no
#: provenance row and cannot be linked.
FINANCING_INPUTS = (
    'company.ecoiq_total',
    'transparency_score_detail',
    'company.transparency_governance',
    'company.modernization',
)


def compute_and_save(profile):
    """
    Compute and persist the financing profile, and record its lineage.

    The value and its provenance commit together or not at all. This function
    had no transaction boundary; one is added around the work it already did
    plus the provenance write. An inner atomic() joins an outer one as a
    savepoint, so the admin action and the detail view are unaffected.

    The returned profile carries a transient `provenance_status`.
    """
    from companies import provenance as prov

    with transaction.atomic():
        fp = _compute_and_save_inner(profile)
        fp.provenance_status = prov.record_calculated(
            profile, FINANCING_METRIC_KEY, fp.financing_readiness,
            FINANCING_INPUTS,
            writer='financing.matching.compute_and_save',
            methodology=FINANCING_METHOD,
            calculation_version=FINANCING_VERSION,
        )
    return fp


def _compute_and_save_inner(profile):
    """
    Compute and persist the CompanyFinancingProfile + DirectFinancingMatch records.
    Returns CompanyFinancingProfile.
    """
    from financing.models import CompanyFinancingProfile, DirectFinancingMatch

    data = compute_financing_profile(profile)
    r    = data['readiness']

    fp, _ = CompanyFinancingProfile.objects.update_or_create(
        profile=profile,
        defaults={
            'financing_readiness':      r['financing_readiness'],
            'modernization_readiness':  r['modernization_readiness'],
            'transparency_readiness':   r['transparency_readiness'],
            'climate_readiness':        r['climate_readiness'],
            'governance_readiness':     r['governance_readiness'],
            'evidence_completeness':    r['evidence_completeness'],
            'readiness_tier':           data['readiness_tier'],
            'funding_urgency':          data['funding_urgency'],
            'estimated_capex_low_usd':  data['capex_low'],
            'estimated_capex_high_usd': data['capex_high'],
            'estimated_annual_impact_usd': data['impact'],
            'missing_requirements':     data['missing'],
            'next_actions':             data['next_actions'],
            'confidence':               data['confidence'],
        },
    )

    # Rebuild DirectFinancingMatch records — delete old, create new
    DirectFinancingMatch.objects.filter(profile=profile).delete()
    to_create = []
    for m in data['matches']:
        to_create.append(DirectFinancingMatch(
            profile=profile,
            opportunity=m['opportunity'],
            match_score=m['match_score'],
            match_tier=m['match_tier'],
            match_rationale=m['match_rationale'],
            missing_requirements=m['missing_requirements'],
            recommended_amount_usd=m['recommended_amount_usd'],
        ))
    if to_create:
        DirectFinancingMatch.objects.bulk_create(to_create, ignore_conflicts=True)

    return fp


def get_or_compute(profile):
    """
    Return existing CompanyFinancingProfile or compute a fresh one.
    Returns None on any error (never breaks company pages).
    """
    try:
        from financing.models import CompanyFinancingProfile
        try:
            return CompanyFinancingProfile.objects.get(profile=profile)
        except CompanyFinancingProfile.DoesNotExist:
            return compute_and_save(profile)
    except Exception as exc:
        log.warning('Financing get_or_compute failed for %s: %s', profile, exc)
        return None
