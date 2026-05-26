"""
EcoIQ Industrial Transition Engine.

Generates AI-powered transition roadmaps and matches financing opportunities
for industrial companies. Designed to be called synchronously from views
or async management commands.

Entry points:
    generate_roadmap(company, roadmap_type)  → TransitionRoadmap
    match_financing(roadmap)                 → list[FinancingMatch]
    recommend_technologies(company, roadmap) → list[TechnologyRecommendation]
"""
import json
import logging
import re
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_client():
    import anthropic
    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '') or ''
    if not api_key:
        raise RuntimeError('ANTHROPIC_API_KEY not configured')
    return anthropic.Anthropic(api_key=api_key)


def _get_model():
    return getattr(settings, 'ECOIQ_AI_MODEL', 'claude-opus-4-5')


def _parse_json_block(text: str) -> dict | list:
    """Extract the outermost JSON object or array from text."""
    # Strip markdown fences
    text = re.sub(r'```(?:json)?\s*', '', text).strip()
    # Find outermost { … } or [ … ]
    for opener, closer in [('{', '}'), ('[', ']')]:
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:i + 1])
    raise ValueError('No JSON block found in response')


def _fmt_usd(v):
    """Format integer USD value for prompt context."""
    if v is None:
        return 'unknown'
    if v >= 1_000_000_000:
        return f'${v / 1_000_000_000:.1f}B'
    if v >= 1_000_000:
        return f'${v / 1_000_000:.0f}M'
    return f'${v / 1_000:.0f}K'


# ── Company context builder ────────────────────────────────────────────────────

def _build_company_context(company) -> str:
    """Build a rich text summary of a company for AI prompts."""
    from league.models import Company
    score = float(company.ecoiq_score)
    projects = list(company.projects.all()[:10])
    findings = list(company.ai_findings.filter(
        status='approved'
    ).select_related()[:15]) if hasattr(company, 'ai_findings') else []

    lines = [
        f'Company: {company.name}',
        f'Sector: {company.get_sector_display()}',
        f'Country: {company.country}',
        f'EcoIQ Score: {score}/100 ({company.status_label})',
        f'Total CO₂ reduced: {company.total_co2_reduced:,} tonnes/yr',
        f'Total ESG investment: {_fmt_usd(company.total_investment_usd)}',
        f'Pollution control score: {company.pollution_control_score}/100',
        f'Emission reduction score: {company.emission_reduction_score}/100',
        f'ESG investment score: {company.esg_investment_score}/100',
        f'Transparency score: {company.transparency_score}/100',
        f'Community impact score: {company.community_impact_score}/100',
    ]
    if projects:
        lines.append('Active environmental projects:')
        for p in projects:
            lines.append(f'  - {p.name} ({p.get_project_type_display()}, '
                         f'{p.co2_reduced_tonnes:,} tCO₂/yr, ${p.investment_usd:,} invested)')
    if findings:
        lines.append('Key AI findings (approved):')
        for f in findings[:8]:
            lines.append(f'  - [{f.get_finding_type_display()}] {f.title} '
                         f'(confidence {f.confidence_score:.0%})')
    return '\n'.join(lines)


# ── Roadmap Generation ─────────────────────────────────────────────────────────

ROADMAP_PROMPTS = {
    'coal_gas': (
        'Design a coal-to-gas fuel switching transition roadmap. '
        'Focus on: boiler/turbine replacement, gas infrastructure build-out, '
        'workforce retraining, regulatory approvals, and interim emission reduction.'
    ),
    'methane': (
        'Design a methane reduction strategy roadmap. '
        'Focus on: LDAR (leak detection and repair), vapour recovery units, '
        'flare elimination, methane-to-energy capture, monitoring systems.'
    ),
    'electrification': (
        'Design an industrial electrification roadmap. '
        'Focus on: electric motors, heat pumps, electric arc furnaces (if relevant), '
        'renewable PPA, on-site solar/wind, grid integration, battery storage.'
    ),
    'district_heat': (
        'Design a district heating modernisation roadmap. '
        'Focus on: network upgrades, heat pump integration, waste heat recovery, '
        'biomass co-firing, metering and demand management.'
    ),
    'water': (
        'Design a water restoration and efficiency roadmap. '
        'Focus on: closed-loop water systems, treatment plant upgrades, '
        'discharge compliance, watershed restoration, water intensity KPIs.'
    ),
    'waste_heat': (
        'Design a waste heat recovery roadmap. '
        'Focus on: heat exchangers, ORC (organic Rankine cycle), steam generation, '
        'process integration, heat-to-power, payback optimisation.'
    ),
    'flare': (
        'Design a flare reduction programme roadmap. '
        'Focus on: gas routing, vapour recovery, flare gas recovery units, '
        'regulatory compliance, World Bank Zero Routine Flaring alignment.'
    ),
    'renewable': (
        'Design a renewable energy integration roadmap. '
        'Focus on: solar PV, wind, PPAs, green hydrogen readiness, '
        'storage, grid connection, corporate RE targets.'
    ),
    'circular': (
        'Design a circular economy and waste reduction roadmap. '
        'Focus on: waste-to-energy, industrial symbiosis, recycling rates, '
        'packaging reduction, supplier engagement, landfill diversion.'
    ),
    'full': (
        'Design a comprehensive industrial transition operating plan — '
        'a full decarbonisation and modernisation roadmap covering all relevant '
        'emission sources, efficiency opportunities, and ESG improvement areas.'
    ),
}


def generate_roadmap(company, roadmap_type: str = 'full') -> 'TransitionRoadmap':
    """
    Generate an AI-powered transition roadmap for a company.
    Creates and saves the roadmap + phases to the database.
    Returns the TransitionRoadmap instance.
    """
    from transition.models import TransitionRoadmap, TransitionPhase

    client = _get_client()
    model  = _get_model()
    focus  = ROADMAP_PROMPTS.get(roadmap_type, ROADMAP_PROMPTS['full'])
    ctx    = _build_company_context(company)

    prompt = f"""You are EcoIQ's Industrial Transition Engine — a world-class industrial
decarbonisation advisor specialising in Central Asia, Eastern Europe, and emerging
market industrial companies.

COMPANY DATA:
{ctx}

ROADMAP FOCUS:
{focus}

Generate a detailed, realistic, financially-grounded transition roadmap for this company.

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "title": "string — concise roadmap title",
  "executive_summary": "string — 3-5 sentence institutional-grade summary of the plan",
  "current_state": {{
    "key_inefficiencies": ["string"],
    "baseline_emissions_tco2": number_or_null,
    "primary_risks": ["string"],
    "data_gaps": ["string"]
  }},
  "target_state": {{
    "headline_outcome": "string",
    "co2_reduction_pct": number,
    "ecoiq_score_gain": number,
    "timeframe_years": number
  }},
  "financials": {{
    "total_capex_usd": number_or_null,
    "annual_opex_savings_usd": number_or_null,
    "payback_years": number_or_null,
    "irr_pct": number_or_null,
    "npv_usd": number_or_null
  }},
  "environmental": {{
    "co2_reduction_tonnes_annual": number_or_null,
    "co2_reduction_pct": number_or_null,
    "methane_reduction_pct": number_or_null,
    "energy_efficiency_gain_pct": number_or_null
  }},
  "phases": [
    {{
      "number": 1,
      "name": "string",
      "duration_months": number,
      "description": "string",
      "activities": ["string"],
      "milestones": ["string"],
      "capex_usd": number_or_null,
      "opex_change_usd": number_or_null,
      "co2_reduction_tonnes": number_or_null
    }}
  ],
  "recommended_financing_structures": ["string"],
  "key_risks": ["string"],
  "technology_options": ["string"],
  "confidence": 0.0_to_1.0,
  "data_quality": "high|medium|low"
}}

Rules:
- phases: 3-5 phases minimum (Quick Wins, Foundation, Scale, Optimise, Sustain as appropriate)
- All USD figures must be realistic for the company's country and sector
- capex_usd total across phases should roughly equal financials.total_capex_usd
- If data is insufficient for a field, use null — never invent implausible numbers
- confidence reflects how much real data backed the analysis (0.3-0.9 range)
"""

    logger.info('Generating %s roadmap for %s', roadmap_type, company.name)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw_text = response.content[0].text
        token_count = response.usage.input_tokens + response.usage.output_tokens
        data = _parse_json_block(raw_text)
    except Exception as exc:
        logger.error('Roadmap generation failed for %s: %s', company.name, exc)
        raise

    financials = data.get('financials', {})
    environmental = data.get('environmental', {})
    target = data.get('target_state', {})

    with transaction.atomic():
        roadmap = TransitionRoadmap.objects.create(
            company=company,
            roadmap_type=roadmap_type,
            status='draft',
            title=data.get('title', f'{company.name} Transition Roadmap'),
            executive_summary=data.get('executive_summary', ''),
            current_state_json=data.get('current_state', {}),
            target_state_json=data.get('target_state', {}),
            # Financials
            total_capex_usd=_safe_int(financials.get('total_capex_usd')),
            annual_opex_savings_usd=_safe_int(financials.get('annual_opex_savings_usd')),
            payback_years=_safe_float(financials.get('payback_years')),
            irr_pct=_safe_float(financials.get('irr_pct')),
            npv_usd=_safe_int(financials.get('npv_usd')),
            # Environmental
            co2_reduction_tonnes=_safe_int(environmental.get('co2_reduction_tonnes_annual')),
            co2_reduction_pct=_safe_float(environmental.get('co2_reduction_pct')),
            methane_reduction_pct=_safe_float(environmental.get('methane_reduction_pct')),
            energy_efficiency_gain_pct=_safe_float(environmental.get('energy_efficiency_gain_pct')),
            # EcoIQ
            projected_ecoiq_delta=_safe_float(target.get('ecoiq_score_gain')),
            projected_ecoiq=_clamp(
                float(company.ecoiq_score) + (_safe_float(target.get('ecoiq_score_gain')) or 0),
                0, 100
            ),
            # Duration
            total_duration_months=sum(
                p.get('duration_months', 6) for p in data.get('phases', [])
            ) or None,
            # JSON fields
            recommended_structures_json=data.get('recommended_financing_structures', []),
            risks_json=data.get('key_risks', []),
            technology_options_json=data.get('technology_options', []),
            # Meta
            confidence=_safe_float(data.get('confidence')) or 0.5,
            data_quality=data.get('data_quality', 'medium'),
            model_used=model,
            token_count=token_count,
        )

        for phase_data in data.get('phases', []):
            TransitionPhase.objects.create(
                roadmap=roadmap,
                number=phase_data.get('number', 1),
                name=phase_data.get('name', 'Phase'),
                duration_months=phase_data.get('duration_months', 6),
                description=phase_data.get('description', ''),
                activities=phase_data.get('activities', []),
                milestones=phase_data.get('milestones', []),
                capex_usd=_safe_int(phase_data.get('capex_usd')),
                opex_change_usd=_safe_int(phase_data.get('opex_change_usd')),
                co2_reduction_tonnes=_safe_int(phase_data.get('co2_reduction_tonnes')),
            )

    logger.info('Created roadmap pk=%d for %s', roadmap.pk, company.name)
    return roadmap


# ── Financing Matching ─────────────────────────────────────────────────────────

def match_financing(roadmap) -> list:
    """
    Match a TransitionRoadmap against the FinancingOpportunity registry.
    Uses rule-based pre-filtering + AI scoring for top candidates.
    Returns list of created FinancingMatch objects.
    """
    from transition.models import FinancingOpportunity, FinancingMatch

    company = roadmap.company
    sector  = company.sector
    country = company.country

    # 1. Pull active opportunities from registry
    opportunities = list(FinancingOpportunity.objects.filter(is_active=True))
    if not opportunities:
        logger.warning('No FinancingOpportunity records in database — run seed_financing first')
        return []

    # 2. Rule-based pre-filter: sector + country eligibility
    candidates = []
    for opp in opportunities:
        # Sector filter
        if opp.eligible_sectors and sector not in opp.eligible_sectors:
            # allow if sector list empty (all sectors)
            continue
        # Country filter (fuzzy: substring match)
        if opp.eligible_countries:
            country_match = any(
                country.lower() in c.lower() or c.lower() in country.lower()
                for c in opp.eligible_countries
            )
            if not country_match:
                # Also try region match
                region_match = False
                if opp.eligible_regions:
                    region_keywords = ' '.join(opp.eligible_regions).lower()
                    # rough region heuristics
                    region_match = _country_in_regions(country, opp.eligible_regions)
                if not region_match:
                    continue
        candidates.append(opp)

    if not candidates:
        # Fallback: global instruments (no country/sector restriction)
        candidates = [o for o in opportunities
                      if not o.eligible_countries and not o.eligible_sectors][:10]

    # 3. Score each candidate
    matches_created = []
    capex = roadmap.total_capex_usd or 0

    existing_ids = set(
        roadmap.financing_matches.values_list('opportunity_id', flat=True)
    )

    for opp in candidates:
        if opp.pk in existing_ids:
            continue

        score = _score_opportunity(roadmap, opp)
        if score < 0.15:
            continue

        suggested_amount = None
        suggested_pct = None
        if capex and opp.max_ticket_usd:
            # suggest min(max_ticket, capex * co_financing %)
            pct = (100 - (opp.co_financing_pct or 30)) / 100
            suggested_amount = min(int(capex * pct), opp.max_ticket_usd)
            if opp.min_ticket_usd and suggested_amount < opp.min_ticket_usd:
                suggested_amount = opp.min_ticket_usd
            suggested_pct = round((suggested_amount / capex) * 100, 1) if capex else None

        rationale = _build_rationale(roadmap, opp, score)
        fm = FinancingMatch.objects.create(
            roadmap=roadmap,
            opportunity=opp,
            match_score=round(score, 3),
            match_rationale=rationale,
            suggested_amount_usd=suggested_amount,
            suggested_pct_of_capex=suggested_pct,
        )
        matches_created.append(fm)

    matches_created.sort(key=lambda m: m.match_score, reverse=True)
    logger.info('Created %d financing matches for roadmap pk=%d',
                len(matches_created), roadmap.pk)
    return matches_created[:12]  # cap at 12


def _score_opportunity(roadmap, opp) -> float:
    """Rule-based match score 0-1."""
    score = 0.4  # base for passing pre-filter

    # Roadmap type ↔ focus area alignment
    focus_map = {
        'coal_gas':       ['coal_transition', 'energy_transition', 'coal'],
        'methane':        ['methane', 'gas', 'fugitive_emissions'],
        'electrification':['electrification', 'renewable', 'clean_energy'],
        'district_heat':  ['district_heating', 'energy_efficiency', 'heat'],
        'water':          ['water', 'water_restoration'],
        'waste_heat':     ['energy_efficiency', 'industrial'],
        'flare':          ['flare', 'methane', 'gas'],
        'renewable':      ['renewable', 'solar', 'wind', 'clean_energy'],
        'circular':       ['circular', 'waste', 'industrial'],
        'full':           [],
    }
    focus_areas = [f.lower() for f in (opp.focus_areas or [])]
    roadmap_keywords = focus_map.get(roadmap.roadmap_type, [])
    if any(kw in fa for kw in roadmap_keywords for fa in focus_areas):
        score += 0.25

    # Ticket size fit
    capex = roadmap.total_capex_usd
    if capex:
        if opp.min_ticket_usd and capex < opp.min_ticket_usd * 0.5:
            score -= 0.15  # too small for this funder
        elif opp.max_ticket_usd and capex > opp.max_ticket_usd * 3:
            score -= 0.1   # likely too large
        else:
            score += 0.1

    # Instrument preference: grants and concessional loans score higher
    if opp.instrument in ('grant', 'loan'):
        score += 0.1
    elif opp.instrument == 'carbon_credit':
        score += 0.05

    # DFIs and climate funds preferred over commercial
    if opp.source_type in ('dfi', 'climate_fund', 'blended'):
        score += 0.1

    return min(max(score, 0.0), 1.0)


def _build_rationale(roadmap, opp, score: float) -> str:
    company = roadmap.company
    parts = [
        f'{opp.institution_name} is a strong match for {company.name}\'s '
        f'{roadmap.get_roadmap_type_display()} programme.'
    ]
    if opp.focus_areas:
        parts.append(f'Focus areas include {", ".join(opp.focus_areas[:3])}.')
    if opp.typical_interest_rate is not None:
        rate = opp.typical_interest_rate
        if rate == 0:
            parts.append('Grant funding — no repayment required.')
        else:
            parts.append(f'Typical rate: {rate:.1f}% p.a. with '
                         f'{opp.grace_period_years or 0:.0f}-year grace period.')
    if opp.typical_tenor_years:
        parts.append(f'Tenor up to {opp.typical_tenor_years:.0f} years.')
    parts.append(f'Match score: {score:.0%}.')
    return ' '.join(parts)


def _country_in_regions(country: str, regions: list) -> bool:
    """Rough country→region mapping for pre-filter."""
    country_l = country.lower()
    region_str = ' '.join(regions).lower()
    CA = ['kazakhstan', 'uzbekistan', 'kyrgyzstan', 'tajikistan', 'turkmenistan']
    EE = ['ukraine', 'poland', 'romania', 'bulgaria', 'hungary', 'moldova',
          'serbia', 'albania', 'georgia', 'armenia', 'azerbaijan', 'belarus']
    SA = ['india', 'pakistan', 'bangladesh', 'nepal', 'sri lanka']
    SEA = ['vietnam', 'indonesia', 'thailand', 'philippines', 'myanmar']
    SSA = ['nigeria', 'kenya', 'ghana', 'ethiopia', 'tanzania', 'south africa']
    MENA = ['egypt', 'morocco', 'jordan', 'algeria', 'tunisia', 'iraq', 'iran']

    checks = [
        ('central asia', CA),
        ('eastern europe', EE),
        ('south asia', SA),
        ('southeast asia', SEA),
        ('sub-saharan africa', SSA),
        ('africa', SSA),
        ('mena', MENA),
        ('middle east', MENA),
    ]
    for region_kw, country_list in checks:
        if region_kw in region_str and country_l in country_list:
            return True
    # Global / All countries
    if 'global' in region_str or 'all' in region_str or 'worldwide' in region_str:
        return True
    return False


# ── Technology Recommendations ─────────────────────────────────────────────────

def recommend_technologies(company, roadmap=None) -> list:
    """
    Generate technology recommendations for a company.
    Optionally scoped to a specific roadmap type.
    Returns list of created TechnologyRecommendation objects.
    """
    from transition.models import TechnologyRecommendation

    client = _get_client()
    model  = _get_model()
    ctx    = _build_company_context(company)
    rtype  = roadmap.roadmap_type if roadmap else 'full'

    prompt = f"""You are EcoIQ's technology advisor. Based on this company's data, recommend
the most impactful clean technologies they should deploy.

COMPANY DATA:
{ctx}

ROADMAP TYPE: {rtype}

Return ONLY a JSON array of technology recommendations:
[
  {{
    "category": "one of: cems|filters|heat_recovery|gas_turbine|solar_pv|wind|methane_capture|ccs|electrification|district_heat|water_treatment|energy_storage|process_opt|hydrogen",
    "priority": 1,
    "provider_name": "string or empty",
    "technology_name": "string",
    "description": "2-3 sentence description and fit rationale",
    "provider_origin": "country or empty",
    "capex_low_usd": number_or_null,
    "capex_high_usd": number_or_null,
    "co2_reduction_pct": number_or_null,
    "energy_saving_pct": number_or_null,
    "payback_years": number_or_null,
    "maturity": "proven|commercial|emerging|pilot",
    "url": "string or empty"
  }}
]

Rules:
- Return 4-8 technology recommendations ranked by priority (1=highest impact)
- Focus on technologies appropriate for the company's sector and country
- Use realistic capex ranges for the region (emerging markets, not US prices)
- Only recommend technologies with clear decarbonisation benefit
"""

    logger.info('Generating tech recommendations for %s', company.name)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw_text = response.content[0].text
        data = _parse_json_block(raw_text)
        if not isinstance(data, list):
            data = [data]
    except Exception as exc:
        logger.error('Tech recs failed for %s: %s', company.name, exc)
        raise

    VALID_CATEGORIES = {
        'cems', 'filters', 'heat_recovery', 'gas_turbine', 'solar_pv', 'wind',
        'methane_capture', 'ccs', 'electrification', 'district_heat',
        'water_treatment', 'energy_storage', 'process_opt', 'hydrogen',
    }
    VALID_MATURITY = {'proven', 'commercial', 'emerging', 'pilot'}

    recs = []
    with transaction.atomic():
        for i, item in enumerate(data, 1):
            cat = item.get('category', 'process_opt')
            if cat not in VALID_CATEGORIES:
                cat = 'process_opt'
            maturity = item.get('maturity', 'proven')
            if maturity not in VALID_MATURITY:
                maturity = 'proven'
            rec = TechnologyRecommendation.objects.create(
                roadmap=roadmap,
                company=company,
                category=cat,
                priority=item.get('priority', i),
                provider_name=str(item.get('provider_name', ''))[:255],
                technology_name=str(item.get('technology_name', ''))[:255],
                description=str(item.get('description', '')),
                provider_origin=str(item.get('provider_origin', ''))[:100],
                capex_low_usd=_safe_int(item.get('capex_low_usd')),
                capex_high_usd=_safe_int(item.get('capex_high_usd')),
                co2_reduction_pct=_safe_float(item.get('co2_reduction_pct')),
                energy_saving_pct=_safe_float(item.get('energy_saving_pct')),
                payback_years=_safe_float(item.get('payback_years')),
                maturity=maturity,
                url=str(item.get('url', ''))[:200],
                applicable_sectors=[company.sector],
            )
            recs.append(rec)

    logger.info('Created %d tech recommendations for %s', len(recs), company.name)
    return recs


# ── Utility helpers ────────────────────────────────────────────────────────────

def _safe_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))
