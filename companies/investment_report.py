"""
EcoIQ Investment Relevance Report — generation + language safety.

generate_investment_relevance_report(profile, user=None) -> InvestmentRelevanceReport
    Builds a grounded prompt from data ALREADY stored in EcoIQ for the
    company (CompanyProfile scores, CompanySource citations, CompanyScoreSnapshot
    history, sector peer averages computed live from the DB), calls the
    Anthropic client using the same client/model/JSON-parsing helpers as
    companies.ai_helpers (the existing AI generation pattern in this repo),
    and persists a new, versioned, draft-status InvestmentRelevanceReport.
    Never overwrites a prior version.

check_prohibited_language(text) -> list[finding]
    Deterministic regex rule engine, styled after
    agent_runtime_model_router.services.safety_assertions — no LLM judge.
    Flags buy/sell/hold-style recommendation language. A report with any
    finding here can never be marked published (see
    InvestmentRelevanceReport.is_publishable).

This module is sustainability-risk intelligence generation, not a second
AI subsystem: model access is the same Anthropic client already wired in
companies/ai_helpers.py, and the *decision* of which provider/model to use
is delegated to agent_runtime_model_router.services.model_router — the
existing model router — purely for the routing explanation recorded on the
report. It intentionally does NOT pull in the full AgentRun/Council
pipeline (training packs, golden tests, cross-examination), which is a
heavier system built for multi-agent deliberation, not a single grounded
company report.
"""
from core.unknown import format_known as fmt, known
import logging
import re

from django.utils import timezone

from companies.ai_helpers import _get_client, _get_model, _parse_json

logger = logging.getLogger(__name__)

# ── Evidence typing (for citations inside report content) ──────────────────────

EVIDENCE_TYPE_CHOICES = [
    ('verified_evidence',     'Verified Evidence'),
    ('company_reported',      'Company-Reported Information'),
    ('external_allegation',   'External Allegation'),
    ('ai_interpretation',     'AI Interpretation'),
    ('insufficient_evidence', 'Insufficient Evidence'),
]

REPORT_JSON_SCHEMA_HINT = """{
  "classification": "lower_exposure | moderate_exposure | elevated_exposure | high_exposure | insufficient_evidence",
  "executive_assessment": "2-4 sentence neutral summary of sustainability-related investment relevance",
  "key_risks": [
    {
      "title": "short risk title",
      "detail": "1-3 sentences",
      "evidence_type": "EXACTLY one of these 5 literal strings: verified_evidence | company_reported | external_allegation | ai_interpretation | insufficient_evidence",
      "evidence_detail": "free text: which EcoIQ score/KPI, cited source, or score-history fact this is grounded in",
      "confidence": "low | medium | high"
    }
  ],
  "positive_signals": [
    {
      "title": "short signal title",
      "detail": "1-3 sentences",
      "evidence_type": "EXACTLY one of these 5 literal strings: verified_evidence | company_reported | external_allegation | ai_interpretation | insufficient_evidence",
      "evidence_detail": "free text: which EcoIQ score/KPI, cited source, or score-history fact this is grounded in",
      "confidence": "low | medium | high"
    }
  ],
  "transition_regulatory_exposure": "2-4 sentences on transition risk + regulatory exposure, grounded only in provided data",
  "controversies_evidence_concerns": "2-4 sentences on controversy/evidence-quality concerns, or a clear statement that none are recorded in EcoIQ",
  "sector_relative_context": "1-3 sentences comparing to sector peers ONLY using the sector peer averages provided below; if fewer than 3 peers were provided, say comparison is not possible",
  "data_confidence": "1-3 sentences on how complete/verified the underlying EcoIQ data is for this company",
  "due_diligence_questions": ["question 1", "question 2", "question 3"]
}

`evidence_type` values explained — use company data reported directly by EcoIQ's own scoring/verification as
"verified_evidence" only when profile.is_verified is true, "company_reported" for unverified self-disclosed
figures, "external_allegation" for third-party claims not confirmed by EcoIQ, "ai_interpretation" when you are
drawing an inference rather than citing a stored fact, and "insufficient_evidence" when you cannot ground the
point at all (in which case omit it from key_risks/positive_signals instead, or use it in data_confidence)."""

PROHIBITED_TERMS_REMINDER = """
STRICT LANGUAGE RULES:
- This is sustainability-risk intelligence, NOT investment advice. Never write a buy, sell or hold
  recommendation, and never use: buy, sell, hold, strong investment, guaranteed return, undervalued,
  overvalued, price target, "the stock will rise", "the stock will fall".
- Never invent: financial statements, stock prices, controversies, fines, emissions figures, company
  commitments, peer rankings, or future stock performance. Use ONLY the data given below.
- If evidence for a section is missing or too thin, say so plainly (e.g. "EcoIQ does not have
  evidence on X") instead of filling the gap with plausible-sounding text.
- classification must be "insufficient_evidence" whenever the underlying profile has very little
  verified data (e.g. no cited sources, no score history, unverified profile) — do not guess a risk
  tier just to avoid this classification.
"""


#: Unambiguous — these phrases are never legitimate in a sustainability-risk
#: report, so a bare word-boundary match is safe (low false-positive risk).
_UNAMBIGUOUS_PATTERNS = [
    (r'\bstrong investment\b', 'strong investment'),
    (r'\bguaranteed return\b', 'guaranteed return'),
    (r'\bundervalued\b', 'undervalued'),
    (r'\bovervalued\b', 'overvalued'),
    (r'\bprice target\b', 'price target'),
    (r'\bthe stock will rise\b', 'the stock will rise'),
    (r'\bthe stock will fall\b', 'the stock will fall'),
]

#: "buy"/"sell"/"hold" are also ordinary English words ("does not hold
#: evidence", "the company will sell products to..."), so a bare match would
#: be too noisy for real prose. These only count as prohibited when they
#: appear in a recommendation-shaped construction — e.g. "hold rating",
#: "we recommend a buy", "buy/sell/hold this stock" — mirroring the
#: negation/context-aware style already used in
#: agent_runtime_model_router.services.safety_assertions.
_RECOMMENDATION_SHAPED_PATTERNS = [
    (r'\b(?:buy|sell|hold)\s+(?:rating|recommendation)\b', 'recommendation rating'),
    (r'\brating\s+of\s+(?:buy|sell|hold)\b', 'recommendation rating'),
    (r'\brecommend(?:ed|s|ing)?\s+(?:a\s+|to\s+)?(?:buy|sell|hold)\b', 'recommend buy/sell/hold'),
    (r'\b(?:buy|sell|hold)\s+(?:this|the)\s+stock\b', 'buy/sell/hold this stock'),
    (r'\binvestors?\s+should\s+(?:buy|sell|hold)\b', 'investors should buy/sell/hold'),
]


#: How many characters before a match to look for a negation ("not", "n't",
#: "never", "does not constitute"...) before treating it as a legitimate
#: disclaimer rather than a live recommendation. Mirrors
#: agent_runtime_model_router.services.safety_assertions._negated_nearby.
_NEGATION_WINDOW = 40


def _negated_nearby(text: str, match_start: int) -> bool:
    preceding = text[max(0, match_start - _NEGATION_WINDOW):match_start].lower()
    return bool(re.search(r"\bnot\b|\bn't\b|\bnever\b|\bno\s+\w+\s+is\b", preceding))


def check_prohibited_language(text: str) -> list:
    """
    Deterministic scan for buy/sell/hold-style recommendation language.
    Returns a list of {pattern_id, severity, term, detail} findings —
    empty list means clean. No LLM judge, mirrors
    agent_runtime_model_router.services.safety_assertions style.

    A match with a negation ("does NOT constitute a buy/sell/hold
    recommendation") shortly before it is treated as compliant disclaimer
    language, not a live recommendation — otherwise EcoIQ's own required
    compliance disclaimer would trip this exact check.
    """
    if not text:
        return []
    findings = []
    for pattern, term in _UNAMBIGUOUS_PATTERNS + _RECOMMENDATION_SHAPED_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if _negated_nearby(text, match.start()):
                continue
            findings.append({
                'pattern_id': 'prohibited_investment_term',
                'severity': 'blocking',
                'term': term,
                'detail': f'Prohibited recommendation-style language ("{term}") found in generated content.',
                'context': text[max(0, match.start() - 40):match.end() + 40].strip(),
            })
    return findings


def _scan_report_content(content: dict) -> list:
    """Runs check_prohibited_language over every string value in the parsed report content."""
    findings = []
    for key, value in content.items():
        if isinstance(value, str):
            findings += check_prohibited_language(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    findings += check_prohibited_language(item)
                elif isinstance(item, dict):
                    for v in item.values():
                        if isinstance(v, str):
                            findings += check_prohibited_language(v)
    return findings


# ── Grounding context ────────────────────────────────────────────────────────

def _sector_peer_context(profile) -> tuple:
    """
    Live-computed sector peer averages (real DB data, never fabricated).
    Returns (context_lines, peer_count). Peer comparison is only offered
    to the model when peer_count >= 3.
    """
    from companies.models import CompanyProfile

    peers = CompanyProfile.objects.filter(
        company__sector=profile.company.sector,
        status__in=('public', 'verified'),
    ).exclude(pk=profile.pk)
    peer_count = peers.count()
    if peer_count < 3:
        return (
            [f'Sector peers with published profiles: {peer_count} (fewer than 3 — '
             'not enough for a sector comparison).'],
            peer_count,
        )
    from django.db.models import Avg
    agg = peers.aggregate(
        avg_score=Avg('ecoiq_total_score'),
        avg_env=Avg('environmental_responsibility_score'),
        avg_transparency=Avg('transparency_anti_corruption_score'),
        avg_controversy=Avg('controversy_risk_score'),
    )
    lines = [
        f'Sector peers with published profiles: {peer_count}',
        f"Sector peer average EcoIQ score: {agg['avg_score']:.1f}" if agg['avg_score'] is not None else '',
        f"Sector peer average environmental score: {agg['avg_env']:.1f}" if agg['avg_env'] is not None else '',
        f"Sector peer average transparency score: {agg['avg_transparency']:.1f}" if agg['avg_transparency'] is not None else '',
        f"Sector peer average controversy risk: {agg['avg_controversy']:.1f}" if agg['avg_controversy'] is not None else '',
    ]
    return ([l for l in lines if l], peer_count)


def _direction_of_change_context(profile) -> str:
    snapshots = list(profile.score_snapshots.order_by('date')[:12])
    if len(snapshots) < 2:
        return 'Score history: fewer than 2 snapshots recorded — direction of change cannot be established.'
    first, last = snapshots[0], snapshots[-1]
    delta = last.total_score - first.total_score
    direction = 'improving' if delta > 1 else ('declining' if delta < -1 else 'broadly stable')
    return (
        f'Score history: {len(snapshots)} snapshots from {first.date} ({first.total_score:.1f}) '
        f'to {last.date} ({last.total_score:.1f}) — trend is {direction} ({delta:+.1f} pts).'
    )


def _evidence_context(profile) -> str:
    sources = list(profile.cited_sources.all()[:10])
    if not sources:
        return 'Cited sources: none recorded in EcoIQ for this company.'
    lines = [f'Cited sources: {len(sources)} recorded —']
    for s in sources:
        lines.append(f'  - [{s.get_source_type_display()}] {s.title}'
                      f'{" (" + str(s.date_accessed) + ")" if s.date_accessed else ""}')
    return '\n'.join(lines)


def build_grounding_context(profile) -> str:
    """
    Full grounding context block for the prompt: reuses
    companies.ai_helpers._profile_context (the same context builder used for
    the existing AI company profile) and extends it with the additional data
    this report specifically needs: evidence citations, score-history
    direction of change, and live sector peer averages.
    """
    from companies.ai_helpers import _profile_context

    base = _profile_context(profile)
    peer_lines, peer_count = _sector_peer_context(profile)

    parts = [
        base,
        '',
        # D4A. 'not assessed', never a substituted number: this text is a
        # model prompt, and a fabricated 50 would be reasoned about as a real
        # measurement. The harm-penalty line drops its minus sign when there is
        # nothing to subtract, so it cannot read as "-not assessed pts".
        f'Controversy Risk Score: {fmt(profile.controversy_risk_score)}/100 (higher = more risk)',
        (f'Harm Penalty Applied: -{profile.harm_penalty:.1f} pts'
         if profile.harm_penalty is not None
         else 'Harm Penalty Applied: not assessed'),
        f'Emissions Reduction Target: {profile.emissions_reduction_target}% vs baseline' if profile.emissions_reduction_target else 'Emissions Reduction Target: Not disclosed',
        f'Profile Verified: {"Yes" if profile.is_verified else "No"}',
        f'Profile Status: {profile.get_status_display()}',
        '',
        _evidence_context(profile),
        '',
        _direction_of_change_context(profile),
        '',
        *peer_lines,
    ]
    return '\n'.join(str(p) for p in parts if p is not None)


# ── Report generation ────────────────────────────────────────────────────────

_VALID_EVIDENCE_TYPES = {key for key, _ in EVIDENCE_TYPE_CHOICES}


def _normalize_evidence_entries(entries) -> list:
    """
    Defensive normalization: if the model didn't return an exact
    evidence_type enum value, fall back to 'ai_interpretation' rather than
    let an arbitrary string reach the template's evidence-type badge.
    """
    if not isinstance(entries, list):
        return []
    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry = dict(entry)
        if entry.get('evidence_type') not in _VALID_EVIDENCE_TYPES:
            entry['evidence_type'] = 'ai_interpretation'
        normalized.append(entry)
    return normalized


def _next_version(profile) -> int:
    from companies.models import InvestmentRelevanceReport
    last = InvestmentRelevanceReport.objects.filter(company=profile).order_by('-version').first()
    return (last.version + 1) if last else 1


def generate_investment_relevance_report(profile, user=None):
    """
    Generates and persists a new draft InvestmentRelevanceReport version for
    `profile`. Does not touch any existing version. Raises RuntimeError if
    the Anthropic client isn't configured (no API key) — callers should
    surface this to the user rather than silently failing.
    """
    from companies.models import InvestmentRelevanceReport
    from agent_runtime_model_router.services.model_router import select_model_route

    route = select_model_route(
        agent_name='EcoIQ Investment Relevance Analyst',
        task_type='investment_relevance_report',
        execution_mode='live',
        sensitivity_level='standard',
        requires_reasoning=True,
    )

    client = _get_client()
    model = _get_model()
    context = build_grounding_context(profile)

    prompt = f"""You are EcoIQ's sustainability-risk analyst. Produce an Investment Relevance Report
that analyses how this company's environmental and stewardship profile MAY be relevant to long-term
investment risk. This is explicitly NOT investment advice and must never read as one.
{PROHIBITED_TERMS_REMINDER}

COMPANY DATA (the ONLY facts you may use):
{context}

Return ONLY valid JSON with exactly this structure:
{REPORT_JSON_SCHEMA_HINT}

Every entry in key_risks and positive_signals must cite which EcoIQ score, KPI, cited source, or
score-history fact it is grounded in via "evidence_detail". If you cannot ground a risk or signal in
the data above, do not include it.
"""

    logger.info('Generating investment relevance report for %s (v%s)', profile.company.name, _next_version(profile))
    response = client.messages.create(
        model=model,
        max_tokens=3072,
        messages=[{'role': 'user', 'content': prompt}],
    )
    raw = response.content[0].text
    data = _parse_json(raw)

    content = {key: data.get(key) for key in (
        'executive_assessment', 'key_risks', 'positive_signals',
        'transition_regulatory_exposure', 'controversies_evidence_concerns',
        'sector_relative_context', 'data_confidence', 'due_diligence_questions',
    )}
    content['key_risks'] = _normalize_evidence_entries(content.get('key_risks'))
    content['positive_signals'] = _normalize_evidence_entries(content.get('positive_signals'))

    classification = data.get('classification', 'insufficient_evidence')
    valid_classifications = {c for c, _ in InvestmentRelevanceReport._meta.get_field('classification').choices}
    if classification not in valid_classifications:
        classification = 'insufficient_evidence'

    flags = _scan_report_content(content)
    if flags:
        logger.warning(
            'Investment relevance report for %s flagged %d prohibited-language finding(s); '
            'report saved as draft and cannot be published until regenerated clean.',
            profile.company.name, len(flags),
        )

    report = InvestmentRelevanceReport.objects.create(
        company=profile,
        version=_next_version(profile),
        status='draft',
        classification=classification,
        content=content,
        # A snapshot records what was true when the report was written. An
        # unknown must stay null in it: a substituted number would be
        # indistinguishable from a real reading forever after, and this is the
        # record a future reader would use to check the report's claims.
        source_snapshot={
            'ecoiq_total_score': known(profile.ecoiq_total_score),
            'public_benefit_score': known(profile.public_benefit_score),
            'environmental_responsibility_score': known(profile.environmental_responsibility_score),
            'modernization_score': known(profile.modernization_score),
            'transparency_anti_corruption_score': known(profile.transparency_anti_corruption_score),
            'controversy_risk_score': known(profile.controversy_risk_score),
            'harm_penalty': known(profile.harm_penalty),
            'pollution_level': profile.pollution_level,
            'is_verified': profile.is_verified,
            'cited_sources_count': profile.cited_sources.count(),
            'score_snapshots_count': profile.score_snapshots.count(),
            'captured_at': timezone.now().isoformat(),
        },
        model_name=model,
        model_provider=route['selected_provider'],
        routing_reason=route['reason'],
        prompt_version='v1',
        methodology_version='v1',
        prohibited_language_flags=flags,
        generated_by=user if (user and getattr(user, 'is_authenticated', False)) else None,
    )
    logger.info('Investment relevance report v%s saved for %s (status=draft, flags=%d)',
                report.version, profile.company.name, len(flags))
    return report
