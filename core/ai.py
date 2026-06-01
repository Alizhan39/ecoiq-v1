"""
EcoIQ AI service — calls Claude to score an assessment across five pillars
and return structured findings.
"""

import json
import re
from django.conf import settings
# anthropic is imported lazily inside run_ecoiq_analysis() so it does NOT
# load the SDK (and its ~40 MB of dependencies) at Django startup —
# only when an actual ESG assessment is run.


SYSTEM_PROMPT = """You are an EcoIQ Analyst — an expert in corporate sustainability,
ESG reporting, and ethical business practice. You evaluate organisations fairly and
evidence-based across five pillars: Environment, Social, Governance, Ethics, Innovation.
You always return valid JSON and nothing else."""

SCORE_GUIDE = """
Scoring guide (0–100 per pillar):
  0–20  : No evidence or actively harmful practices
 21–40  : Minimal effort, significant gaps
 41–60  : Some initiatives but inconsistent or unverified
 61–80  : Good performance with clear, demonstrated commitment
 81–100 : Exemplary, sector-leading practices with verified outcomes
"""


def _build_user_prompt(assessment, responses) -> str:
    doc_block = ""
    if assessment.extracted_text.strip():
        doc_block = (
            f"\n## Uploaded Document (excerpt)\n"
            f"{assessment.extracted_text[:8000]}\n"
        )

    qa_lines = []
    for r in responses:
        answer = r.answer.strip() if r.answer.strip() else "(not answered)"
        qa_lines.append(f"**{r.question_text}**\n{answer}")
    qa_block = "\n\n".join(qa_lines) if qa_lines else "(no questionnaire answers provided)"

    return f"""## Company under assessment: {assessment.company_name}
{doc_block}
## Questionnaire responses
{qa_block}

{SCORE_GUIDE}

Evaluate the company and respond with ONLY a JSON object in this exact shape:

{{
  "scores": {{
    "environment": <integer 0-100>,
    "social":      <integer 0-100>,
    "governance":  <integer 0-100>,
    "ethics":      <integer 0-100>,
    "innovation":  <integer 0-100>
  }},
  "summary": "<2–3 paragraphs: overall strengths, weaknesses, and key recommendations>",
  "pillar_notes": {{
    "environment": "<1–2 sentences on environment performance>",
    "social":      "<1–2 sentences on social performance>",
    "governance":  "<1–2 sentences on governance performance>",
    "ethics":      "<1–2 sentences on ethics performance>",
    "innovation":  "<1–2 sentences on innovation performance>"
  }}
}}

Return ONLY the JSON object. No markdown fences, no preamble, no commentary."""


def _extract_json(text: str) -> dict:
    """Parse JSON from Claude's response, stripping any accidental markdown fences."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ``` wrappers if present
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return json.loads(text)


def _clamp(value, lo=0, hi=100) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return 0


def run_ecoiq_analysis(assessment) -> dict:
    """
    Call Claude, parse the response, and return a dict ready to save into Finding:
    {
      score_environment, score_social, score_governance,
      score_ethics, score_innovation, score_overall,
      summary, pillar_notes, raw_ai_response
    }
    Raises ValueError if the API key is missing.
    Raises anthropic.APIError (or subclasses) on API failures.
    """
    import anthropic  # lazy — keeps the SDK out of startup memory

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file and restart the server."
        )

    client = anthropic.Anthropic(api_key=api_key)
    responses = list(assessment.responses.all())
    user_prompt = _build_user_prompt(assessment, responses)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text
    data = _extract_json(raw)

    scores = data.get("scores", {})
    env   = _clamp(scores.get("environment", 0))
    soc   = _clamp(scores.get("social", 0))
    gov   = _clamp(scores.get("governance", 0))
    eth   = _clamp(scores.get("ethics", 0))
    inn   = _clamp(scores.get("innovation", 0))
    overall = _clamp(round((env + soc + gov + eth + inn) / 5))

    return {
        "score_environment": env,
        "score_social":      soc,
        "score_governance":  gov,
        "score_ethics":      eth,
        "score_innovation":  inn,
        "score_overall":     overall,
        "summary":           data.get("summary", ""),
        "pillar_notes":      data.get("pillar_notes", {}),
        "raw_ai_response":   raw,
    }
