"""
Two-call AI orchestration for industrial facility audits.

Call 1 — Diagnostic:
    Input:  extracted document text + facility profile
    Output: detailed findings JSON (8 fields per finding)

Call 2 — Recommendations:
    Input:  findings + questionnaire answers
    Output: ranked recommendations + ROI + roadmap + before/after + projected improvements
"""

import json
import re
import anthropic
from django.conf import settings

MODEL = "claude-sonnet-4-6"


def _client():
    key = settings.ANTHROPIC_API_KEY
    if not key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file and restart the server."
        )
    return anthropic.Anthropic(api_key=key)


def _parse_json(text: str) -> dict:
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    # Extract first complete JSON object if there's extra text
    brace = text.find('{')
    if brace > 0:
        text = text[brace:]
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        # Surface a clear message — most common cause is token truncation
        raise ValueError(
            f"AI response was incomplete (JSON cut off at char {exc.pos}). "
            "This usually means the response was too long. "
            "Try reducing the number of questionnaire answers or contact support."
        ) from exc


def _clamp(v, lo=0, hi=100):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return lo


# ── Call 1: Diagnostic ────────────────────────────────────────────────────────

DIAGNOSTIC_SYSTEM = """You are a senior industrial efficiency consultant and process engineer
with 25 years of experience auditing heavy manufacturing facilities. You identify operational
inefficiencies, energy waste, maintenance failures, and modernisation opportunities.
You provide concrete, evidence-based analysis with realistic financial estimates.
You always return valid JSON — no markdown fences, no preamble, no trailing text."""

DIAGNOSTIC_PROMPT = """Analyse the following manufacturing facility based on available documents
and profile information. Produce a detailed diagnostic with specific, actionable findings.

## Facility Profile
{profile}

## Uploaded Documents (excerpt)
{doc_text}

Return ONLY a JSON object with this exact structure:
{{
  "overall_efficiency_score": <integer 0-100, honest assessment of current operational efficiency>,
  "current_state_summary": "<2 paragraphs: overall operational condition, key problem areas, and how inefficiencies compound each other>",
  "findings": [
    {{
      "area": "<energy|production|maintenance|safety|infrastructure|quality|workforce>",
      "severity": "<critical|high|medium|low>",
      "title": "<concise issue title, 5-10 words>",
      "description": "<2-3 sentences: what the problem is and its operational impact. Be specific with numbers where possible.>",
      "root_cause": "<1-2 sentences: why this problem exists — systemic cause, not symptoms>",
      "recommended_action": "<1-2 sentences: the specific modernisation action that would resolve this>",
      "loss_usd": <estimated annual financial loss as integer, 0 if unknown — be realistic>,
      "efficiency_gain_pct": <integer 0-40: estimated % efficiency improvement in this area if addressed>,
      "sustainability_impact": "<1 sentence: carbon, energy, or waste impact of this issue>"
    }}
  ],
  "critical_areas": ["<area1>", "<area2>"]
}}

List findings in descending order of loss_usd. Include 6-10 findings. Be specific and evidence-based.
Only return the JSON object."""


def run_diagnostic(session) -> dict:
    profile = _build_profile(session)
    doc_text = (session.extracted_text or 'No document provided.')[:8000]
    prompt = DIAGNOSTIC_PROMPT.format(profile=profile, doc_text=doc_text)

    try:
        msg = _client().messages.create(
            model=MODEL, max_tokens=4000,
            system=DIAGNOSTIC_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.RateLimitError:
        raise ValueError("API rate limit reached. Please wait a minute and try again.")
    except anthropic.APIConnectionError:
        raise ValueError("Could not connect to the AI service. Check your internet connection and try again.")
    except anthropic.APIStatusError as exc:
        raise ValueError(f"AI service error ({exc.status_code}). Please try again in a few minutes.")

    if msg.stop_reason == 'max_tokens':
        # Still try to parse — might be complete enough
        try:
            return _parse_json(msg.content[0].text)
        except ValueError:
            raise ValueError("Diagnostic response was truncated. Please try again.")

    return _parse_json(msg.content[0].text)


# ── Call 2: Recommendations + Roadmap ────────────────────────────────────────

RECS_SYSTEM = """You are a senior industrial modernisation advisor specialising in
ROI-driven facility transformation. Given diagnostic findings and operational data,
you produce prioritised, concrete recommendations with realistic financial modelling,
phased implementation roadmaps, and measurable projected improvements.
You always return valid JSON — no markdown fences, no preamble, no trailing text."""

RECS_PROMPT = """Based on the diagnostic findings and questionnaire responses below,
generate a full modernisation plan with ranked recommendations, ROI analysis, and projections.

## Diagnostic Findings
{findings_json}

## Questionnaire Responses
{qa_text}

## Facility Profile
{profile}

Return ONLY a JSON object with this exact structure:
{{
  "executive_summary": "<3 paragraphs: overall assessment of modernisation opportunity, top 3 priorities with expected impact, and the strategic case for investment>",
  "modernization_score": <integer 0-100, realistic projected efficiency after implementing all recommendations>,
  "total_savings_usd": <integer, total annual savings across all recommendations>,
  "total_investment_usd": <integer, total one-time investment across all recommendations>,
  "projected_improvements": {{
    "energy_reduction_pct": <integer 0-60: overall facility energy reduction %>,
    "downtime_reduction_pct": <integer 0-80: unplanned downtime reduction %>,
    "production_efficiency_pct": <integer 0-40: OEE / throughput improvement %>,
    "emissions_reduction_pct": <integer 0-60: CO2/emissions reduction %>
  }},
  "recommendations": [
    {{
      "priority": "<critical|high|medium|low>",
      "category": "<energy|production|maintenance|safety|infrastructure|quality|workforce>",
      "title": "<concise title, 5-10 words>",
      "problem": "<1-2 sentences: specific problem this addresses, with numbers>",
      "solution": "<2-3 sentences: what to implement, how it works, and why this approach>",
      "implementation": "<4-5 concrete steps as a single string, steps separated by ' | '>",
      "savings_usd": <annual savings as integer>,
      "cost_usd": <one-time implementation cost as integer>,
      "roi_months": <payback period in months as integer>,
      "complexity": "<low|medium|high>",
      "is_quick_win": <true if roi_months <= 12 and complexity != high>,
      "priority_score": <integer 0-100: composite score based on ROI speed, operational impact, risk reduction, implementation ease, and energy savings>
    }}
  ],
  "roadmap": {{
    "phase_1": {{
      "label": "Phase 1: Quick Wins (0–6 months)",
      "items": ["<specific action with expected outcome>", "<action 2>", "<action 3>"],
      "investment": <integer USD>,
      "savings": <integer USD annual>
    }},
    "phase_2": {{
      "label": "Phase 2: Operational Optimisation (6–18 months)",
      "items": ["<specific action>", "<action 2>", "<action 3>"],
      "investment": <integer USD>,
      "savings": <integer USD annual>
    }},
    "phase_3": {{
      "label": "Phase 3: Infrastructure Modernisation (18–36 months)",
      "items": ["<specific action>", "<action 2>", "<action 3>"],
      "investment": <integer USD>,
      "savings": <integer USD annual>
    }}
  }},
  "before_after": {{
    "energy":         {{"current": "<specific description with numbers>", "future": "<specific description with numbers>", "improvement_pct": <integer>}},
    "production":     {{"current": "<specific description>", "future": "<specific description>", "improvement_pct": <integer>}},
    "maintenance":    {{"current": "<specific description>", "future": "<specific description>", "improvement_pct": <integer>}},
    "safety":         {{"current": "<specific description>", "future": "<specific description>", "improvement_pct": <integer>}},
    "infrastructure": {{"current": "<specific description>", "future": "<specific description>", "improvement_pct": <integer>}}
  }},
  "future_state_summary": "<2 paragraphs: what the facility will look like operationally after full implementation — specific metrics, not vague promises>"
}}

Order recommendations by priority_score descending (highest priority first).
Include 6–10 recommendations maximum — quality over quantity.
Only return the JSON object."""


def run_recommendations(session, diagnostic: dict) -> dict:
    responses = list(session.responses.all())
    qa_text = '\n\n'.join(
        f"**{r.question_text}**\n{r.answer or '(not answered)'}"
        for r in responses
    )
    profile  = _build_profile(session)
    findings = json.dumps(diagnostic.get('findings', []), indent=2)

    prompt = RECS_PROMPT.format(
        findings_json=findings,
        qa_text=qa_text or '(no questionnaire answers)',
        profile=profile,
    )
    try:
        msg = _client().messages.create(
            model=MODEL, max_tokens=16000,
            system=RECS_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.RateLimitError:
        raise ValueError("API rate limit reached. Please wait a minute and try again.")
    except anthropic.APIConnectionError:
        raise ValueError("Could not connect to the AI service. Check your internet connection and try again.")
    except anthropic.APIStatusError as exc:
        raise ValueError(f"AI service error ({exc.status_code}). Please try again in a few minutes.")

    if msg.stop_reason == 'max_tokens':
        try:
            return _parse_json(msg.content[0].text)
        except ValueError:
            raise ValueError(
                "Recommendations response was truncated. "
                "Try again — if this persists, shorten some questionnaire answers."
            )

    return _parse_json(msg.content[0].text)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_profile(session) -> str:
    lines = [
        f"Facility: {session.facility_name}",
        f"Sector: {session.get_sector_display()}",
    ]
    if session.location:
        lines.append(f"Location: {session.location}")
    if session.facility_age:
        lines.append(f"Facility age: {session.facility_age} years")
    if session.headcount:
        lines.append(f"Headcount: {session.headcount}")
    if session.annual_revenue:
        lines.append(f"Annual revenue: ${session.annual_revenue:,}")
    if session.notes:
        lines.append(f"Additional context: {session.notes}")
    return '\n'.join(lines)


# ── Orchestrator: save everything to DB ──────────────────────────────────────

def run_full_analysis(session):
    """
    Run both AI calls and persist all results.
    Returns the AuditReport instance.
    Raises ValueError (missing key) or anthropic.APIError on failure.
    """
    from .models import Finding, Recommendation, ActionPlan, AuditReport

    # ── Call 1: Diagnostic
    diagnostic = run_diagnostic(session)

    # Persist findings with all new fields
    session.findings.all().delete()
    for f in diagnostic.get('findings', []):
        Finding.objects.create(
            session               = session,
            area                  = f.get('area', 'production'),
            severity              = f.get('severity', 'medium'),
            title                 = f.get('title', '')[:255],
            description           = f.get('description', ''),
            root_cause            = f.get('root_cause', ''),
            recommended_action    = f.get('recommended_action', ''),
            loss_usd              = max(0, int(f.get('loss_usd', 0))),
            efficiency_gain_pct   = _clamp(f.get('efficiency_gain_pct', 0), 0, 40),
            sustainability_impact = f.get('sustainability_impact', ''),
        )

    # ── Call 2: Recommendations + Roadmap
    recs_data = run_recommendations(session, diagnostic)

    # Persist recommendations
    session.recommendations.all().delete()
    for i, r in enumerate(recs_data.get('recommendations', [])):
        Recommendation.objects.create(
            session        = session,
            priority       = r.get('priority', 'medium'),
            category       = r.get('category', 'production'),
            title          = r.get('title', '')[:255],
            problem        = r.get('problem', ''),
            solution       = r.get('solution', ''),
            implementation = r.get('implementation', ''),
            savings_usd    = max(0, int(r.get('savings_usd', 0))),
            cost_usd       = max(0, int(r.get('cost_usd', 0))),
            roi_months     = max(0, int(r.get('roi_months', 0))),
            complexity     = r.get('complexity', 'medium'),
            is_quick_win   = bool(r.get('is_quick_win', False)),
            order          = i,
        )

    # Persist roadmap
    session.action_phases.all().delete()
    roadmap = recs_data.get('roadmap', {})
    for phase_num, key in enumerate(['phase_1', 'phase_2', 'phase_3'], start=1):
        ph = roadmap.get(key, {})
        if ph:
            ActionPlan.objects.create(
                session    = session,
                phase      = phase_num,
                label      = ph.get('label', f'Phase {phase_num}'),
                items      = ph.get('items', []),
                investment = max(0, int(ph.get('investment', 0))),
                savings    = max(0, int(ph.get('savings', 0))),
            )

    # Extract projected improvements
    proj = recs_data.get('projected_improvements', {})
    total_savings = max(0, int(recs_data.get('total_savings_usd', 0)))
    total_invest  = max(0, int(recs_data.get('total_investment_usd', 0)))
    blended_roi   = round((total_invest / total_savings * 12) if total_savings > 0 else 0)

    report, _ = AuditReport.objects.update_or_create(
        session=session,
        defaults=dict(
            overall_efficiency_score  = _clamp(diagnostic.get('overall_efficiency_score', 0)),
            modernization_score       = _clamp(recs_data.get('modernization_score', 0)),
            total_savings_potential   = total_savings,
            total_investment_required = total_invest,
            blended_roi_months        = blended_roi,
            executive_summary         = recs_data.get('executive_summary', ''),
            current_state_summary     = diagnostic.get('current_state_summary', ''),
            future_state_summary      = recs_data.get('future_state_summary', ''),
            before_after              = recs_data.get('before_after', {}),
            energy_reduction_pct      = _clamp(proj.get('energy_reduction_pct', 0), 0, 60),
            downtime_reduction_pct    = _clamp(proj.get('downtime_reduction_pct', 0), 0, 80),
            production_efficiency_pct = _clamp(proj.get('production_efficiency_pct', 0), 0, 40),
            emissions_reduction_pct   = _clamp(proj.get('emissions_reduction_pct', 0), 0, 60),
            raw_ai_response           = json.dumps({'diagnostic': diagnostic, 'recommendations': recs_data}),
        )
    )
    return report
