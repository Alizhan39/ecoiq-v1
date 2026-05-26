"""
EcoIQ Company Intelligence — AI Helper Functions.

generate_ai_company_profile(profile)          → fills ai_summary, ai_modernization_report,
                                                 ai_investment_opportunity, ai_risk_notes,
                                                 ai_recommendations on CompanyProfile

generate_guidance_video_script(video)          → fills script, higgsfield_prompt,
                                                 recommended_actions, executive_summary
                                                 on CompanyGuidanceVideo

generate_company_guidance_video_script(company_id, video_type)
                                               → standalone function returning a dict
                                                 (for management command use)

All AI content uses strictly neutral EcoIQ language:
  ethical value creation, public benefit, responsible leadership,
  long-term trust, harm reduction, stewardship, modernization,
  transparency, anti-corruption, future generations, people and planet.
No religious language whatsoever.
"""
import json
import logging
import re
from django.conf import settings

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

NEUTRAL_LANGUAGE_REMINDER = """
LANGUAGE RULES (strict):
- Use ONLY: ethical value creation, public benefit, responsible leadership,
  long-term trust, harm reduction, stewardship, modernization, transparency,
  anti-corruption, future generations, people and planet, fair growth,
  investor readiness, responsible modernization.
- NEVER use: religious, faith-based, or culturally specific framing.
- Tone: premium, wise, investor-grade, constructive, not activist.
"""

VIDEO_TYPE_DESCRIPTIONS = {
    'path_to_100':            'Path from current EcoIQ score to 100',
    'profit_to_public':       'Transitioning profit-first mindset to public benefit',
    'hidden_harm_reduction':  'Identifying and reducing hidden operational harms',
    'modernization_roadmap':  'Concrete modernization pathway',
    'transparency_trust':     'Building transparency and stakeholder trust',
    'investor_readiness':     'Preparing for ethical investor engagement',
    'public_benefit_story':   'Telling the public benefit story of the company',
    'board_summary':          'Board-level strategic summary',
    'what_100_looks_like':    'Visualizing what a 100% EcoIQ score means',
}


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _get_client():
    import anthropic
    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not api_key:
        raise RuntimeError('ANTHROPIC_API_KEY not set')
    return anthropic.Anthropic(api_key=api_key)


def _get_model():
    return getattr(settings, 'ECOIQ_AI_MODEL', 'claude-opus-4-5')


def _parse_json(text: str):
    text = re.sub(r'```(?:json)?\s*', '', text).strip()
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
    raise ValueError('No JSON block found in AI response')


def _profile_context(profile) -> str:
    """Build a rich plain-text context block for the AI."""
    co = profile.company
    lines = [
        f'Company: {co.name}',
        f'Country: {co.country}',
        f'Sector: {co.get_sector_display()}',
        f'Description: {co.description or "Not provided"}',
        '',
        f'EcoIQ Total Score: {profile.ecoiq_total_score:.1f}/100 ({profile.moral_label_display})',
        f'Public Benefit Score:          {profile.public_benefit_score:.1f}',
        f'Environmental Score:           {profile.environmental_responsibility_score:.1f}',
        f'Modernization Score:           {profile.modernization_score:.1f}',
        f'Transparency Score:            {profile.transparency_anti_corruption_score:.1f}',
        f'Anti-Corruption Score:         {profile.anti_corruption_score:.1f}',
        f'Ethical Alignment Score:       {profile.ethical_alignment_score:.1f}',
        f'Profit Extraction Risk:        {profile.profit_extraction_risk_score:.1f}',
        '',
        f'Pollution Level: {profile.get_pollution_level_display()}',
        f'Estimated Emissions: {profile.estimated_emissions:,} tCO2/yr' if profile.estimated_emissions else 'Emissions: Not disclosed',
        f'Renewable Energy Share: {profile.renewable_energy_share:.0f}%' if profile.renewable_energy_share else 'Renewable: Not disclosed',
        f'Funding Status: {profile.get_funding_status_display()}',
        f'Ownership: {profile.get_ownership_type_display()}',
    ]
    if profile.annual_revenue:
        lines.append(f'Annual Revenue: ${profile.annual_revenue:,}')
    if profile.employees:
        lines.append(f'Employees: {profile.employees:,}')
    if profile.modernization_projects:
        lines.append(f'Modernization Projects: {", ".join(profile.modernization_projects[:4])}')
    if profile.ai_risk_notes:
        lines.append(f'Known Risk Notes: {profile.ai_risk_notes[:300]}')
    return '\n'.join(lines)


# ── AI Company Profile ─────────────────────────────────────────────────────────

def generate_ai_company_profile(profile) -> None:
    """
    Generate AI content for a CompanyProfile:
    - ai_summary
    - ai_modernization_report
    - ai_investment_opportunity
    - ai_risk_notes
    - ai_recommendations (JSON list)

    All saved to the profile (draft status maintained).
    """
    client = _get_client()
    model  = _get_model()
    ctx    = _profile_context(profile)

    prompt = f"""You are EcoIQ's senior intelligence analyst. Generate a structured intelligence
profile for this industrial company using ONLY publicly appropriate, neutral language.
{NEUTRAL_LANGUAGE_REMINDER}

COMPANY DATA:
{ctx}

Return ONLY valid JSON with this exact structure:
{{
  "ai_summary": "3-4 sentence neutral overview of the company's operations, scale, and EcoIQ standing. Professional and factual.",
  "ai_modernization_report": "3-4 sentence analysis of the company's modernization status, key opportunities, and what responsible modernization would look like for them.",
  "ai_investment_opportunity": "2-3 sentence description of why this company may attract ethical/ESG investors, and what funding or partnership opportunities exist.",
  "ai_risk_notes": "2-3 sentences identifying the most material transparency gaps, harm indicators, or governance risks visible in their profile.",
  "ai_recommendations": [
    "Specific recommendation 1 — actionable, constructive",
    "Specific recommendation 2",
    "Specific recommendation 3",
    "Specific recommendation 4",
    "Specific recommendation 5"
  ]
}}

Ensure language is:
- Investor-grade: precise, analytical, evidence-referenced
- Constructive: not accusatory, focuses on improvement pathways
- Neutral: no religious, cultural, or politically charged framing
"""
    logger.info('Generating AI profile for %s', profile.company.name)
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{'role': 'user', 'content': prompt}],
    )
    raw = response.content[0].text
    data = _parse_json(raw)

    profile.ai_summary                = data.get('ai_summary', '')[:2000]
    profile.ai_modernization_report   = data.get('ai_modernization_report', '')[:2000]
    profile.ai_investment_opportunity = data.get('ai_investment_opportunity', '')[:2000]
    profile.ai_risk_notes             = data.get('ai_risk_notes', '')[:2000]
    profile.ai_recommendations        = data.get('ai_recommendations', [])[:10]

    profile.save(update_fields=[
        'ai_summary', 'ai_modernization_report', 'ai_investment_opportunity',
        'ai_risk_notes', 'ai_recommendations', 'updated_at',
    ])
    logger.info('AI profile saved for %s', profile.company.name)


# ── Guidance Video Script ──────────────────────────────────────────────────────

def generate_guidance_video_script(video) -> None:
    """
    Generate script + Higgsfield prompt + recommended_actions + executive_summary
    for a CompanyGuidanceVideo. Saves directly to the video record.
    """
    profile = video.company
    result  = generate_company_guidance_video_script(
        profile_obj=profile,
        video_type=video.video_type,
    )

    video.script               = result.get('script', '')
    video.higgsfield_prompt    = result.get('higgsfield_prompt', '')
    video.recommended_actions  = result.get('recommended_actions', [])
    video.executive_summary    = result.get('executive_summary', '')
    video.current_score_snapshot = profile.ecoiq_total_score
    video.target_score         = result.get('target_score')
    video.target_score_improvement = result.get('target_score_improvement')
    video.status               = 'video_prompt_generated'

    video.save(update_fields=[
        'script', 'higgsfield_prompt', 'recommended_actions',
        'executive_summary', 'current_score_snapshot', 'target_score',
        'target_score_improvement', 'status', 'updated_at',
    ])
    logger.info('Video script generated for %s — %s', profile.company.name, video.video_type)


def generate_company_guidance_video_script(
    company_id: int = None,
    video_type: str = 'path_to_100',
    profile_obj=None,
) -> dict:
    """
    Standalone function to generate a complete guidance video package.

    Usage:
        result = generate_company_guidance_video_script(
            company_id=42, video_type='path_to_100'
        )
    or:
        result = generate_company_guidance_video_script(
            profile_obj=my_profile, video_type='modernization_roadmap'
        )

    Returns dict with:
        title, script, higgsfield_prompt, recommended_actions,
        target_score, target_score_improvement, executive_summary
    """
    if profile_obj is None:
        from companies.models import CompanyProfile
        profile_obj = CompanyProfile.objects.get(pk=company_id)

    profile = profile_obj
    co      = profile.company
    ctx     = _profile_context(profile)
    vtype_desc = VIDEO_TYPE_DESCRIPTIONS.get(video_type, 'EcoIQ Guidance')
    current_score = profile.ecoiq_total_score
    target_score  = min(100, current_score + 25)

    client = _get_client()
    model  = _get_model()

    prompt = f"""You are a world-class ESG documentary writer and visual strategist.
Create a personalized EcoIQ guidance video package for the company below.
{NEUTRAL_LANGUAGE_REMINDER}

COMPANY DATA:
{ctx}

VIDEO TYPE: {vtype_desc}
CURRENT ECOIQ SCORE: {current_score:.1f}
SUGGESTED TARGET SCORE: {target_score:.1f}

Return ONLY valid JSON:
{{
  "title": "Compelling, specific video title (e.g. 'How {co.name} Can Move from {current_score:.0f} to {target_score:.0f} EcoIQ')",
  "executive_summary": "2-3 sentence premium executive summary. What this video reveals and why it matters.",
  "script": "Complete 60-90 second narration script. Written in second person (addressing the company). Must: (1) open with the company's current position and what it means for stakeholders; (2) name the 2-3 most important improvement areas with specifics; (3) describe the tangible impact of reaching {target_score:.0f}; (4) close with an inspiring, grounded call to action. Must NOT contain any religious language.",
  "higgsfield_prompt": "Detailed cinematic visual prompt for Higgsfield AI video generation. Describe: setting (industrial/corporate/landscape), visual style (cinematic, premium, documentary), colour palette, camera movements, key visual metaphors. 100-150 words. No people's faces. Premium corporate aesthetic.",
  "recommended_actions": [
    "Specific, actionable improvement recommendation 1",
    "Recommendation 2",
    "Recommendation 3",
    "Recommendation 4",
    "Recommendation 5"
  ],
  "target_score": {target_score:.1f},
  "target_score_improvement": {target_score - current_score:.1f}
}}
"""

    response = client.messages.create(
        model=model,
        max_tokens=3000,
        messages=[{'role': 'user', 'content': prompt}],
    )
    raw  = response.content[0].text
    data = _parse_json(raw)
    return data
