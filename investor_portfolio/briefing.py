"""
EcoIQ Portfolio Briefing generation — reuses the exact same AI-call pattern
as companies/investment_report.py (which itself reuses companies/ai_helpers.py):
same client bootstrap, same JSON parsing, same agent_runtime_model_router
routing-decision reuse, same prohibited-language safety filter. No second AI
subsystem.

The briefing NEVER calculates anything — it is handed the already-persisted
PortfolioSnapshot fields (calculations.py) and the deterministic diff against
the prior snapshot (changes.py), and may only narrate those numbers.
"""
import logging

from companies.ai_helpers import _get_client, _get_model, _parse_json
from companies.investment_report import check_prohibited_language

logger = logging.getLogger(__name__)

REPORT_JSON_SCHEMA_HINT = """{
  "summary": "2-4 sentence neutral overview of this portfolio's sustainability-risk exposure, using ONLY the numbers given below",
  "largest_exposure_concentrations": "1-3 sentences on where identified exposure concentrates (sector/company/classification), citing the actual percentages given",
  "top_contributors": "1-3 sentences naming the companies contributing most to identified exposure, from the contributors list given",
  "insufficient_evidence_areas": "1-3 sentences on what fraction of the portfolio lacks sufficient EcoIQ evidence and roughly which holdings",
  "changes_since_prior_snapshot": "1-3 sentences summarizing the changes given below — or a clear statement that this is the first snapshot",
  "due_diligence_questions": ["question 1", "question 2", "question 3"]
}"""

PROHIBITED_TERMS_REMINDER = """
STRICT RULES:
- This is a summary of ALREADY-CALCULATED sustainability-risk numbers, not investment advice. Never write a
  buy, sell or hold recommendation, and never use: buy, sell, hold, strong investment, guaranteed return,
  undervalued, overvalued, price target, "the stock will rise", "the stock will fall".
- Do not recommend buying or selling anything. Do not optimise returns, propose trades, predict market
  movement, create price targets, invent diversification benefits, or claim a lower EcoIQ score means
  higher financial returns.
- Use ONLY the numbers given below. Do not invent percentages, company names, or classifications not
  present in the data.
- If a section's underlying data is thin (e.g. very few holdings, or a portfolio that is entirely
  insufficient-evidence), say so plainly rather than padding with generic text.
"""


def _format_pct(value):
    return f'{value:.1f}%' if value is not None else 'unknown'


def build_grounding_context(snapshot, diff: dict) -> str:
    lines = [
        f'Portfolio value: {snapshot.total_market_value} {snapshot.total_value_currency}'
        if snapshot.total_market_value is not None else
        f'Portfolio value: incomplete — multiple currencies without FX conversion '
        f'({snapshot.currency_subtotals})',
        f'Methodology version: {snapshot.methodology_version}',
        f'Overall exposure score (0-100, higher = more identified exposure): {snapshot.exposure_score}',
        f'Known exposure (has a usable EcoIQ classification): {_format_pct(snapshot.known_exposure_pct)} of value',
        f'Unknown/unassessed exposure (no report or insufficient evidence): {_format_pct(snapshot.unknown_exposure_pct)} of value',
        f'Evidence coverage (weighted average evidence strength): {_format_pct(snapshot.evidence_coverage_pct)}',
        f'Stale analysis (reports older than 90 days): {_format_pct(snapshot.stale_analysis_pct)} of value',
        '',
        f'Exposure distribution by value: {snapshot.distribution}',
        f'Concentration: top holdings = {snapshot.concentration.get("top_holdings")}',
        f'Concentration: HHI = {snapshot.concentration.get("hhi")} (flagged high: {snapshot.concentration.get("hhi_flag")})',
        f'Concentration: by sector = {snapshot.concentration.get("by_sector")}',
        f'Concentration: high-exposure classification concentration = {snapshot.concentration.get("high_exposure_concentration_pct")}%',
        '',
        'Largest contributors to identified exposure (company, exposure_contribution points):',
    ]
    contributors = sorted(
        [r for r in snapshot.holding_snapshots if r.get('exposure_contribution')],
        key=lambda r: r['exposure_contribution'], reverse=True,
    )[:5]
    for r in contributors:
        lines.append(f'  - {r["company_name"]} ({r["ticker"]}): contribution={r["exposure_contribution"]}, '
                      f'classification={r["classification"]}, weight={r["weight_pct"]}%')

    lines.append('')
    if not diff.get('has_prior'):
        lines.append('This is the first snapshot for this portfolio — no prior snapshot to compare against.')
    else:
        lines.append(f'Change since prior snapshot ({diff.get("prior_calculated_at")}):')
        lines.append(f'  Exposure score change: {diff.get("exposure_score_delta")}')
        lines.append(f'  Unknown-exposure % change: {diff.get("unknown_exposure_pct_delta")}')
        lines.append(f'  Companies added: {diff.get("added_companies")}')
        lines.append(f'  Companies removed: {diff.get("removed_companies")}')
        lines.append(f'  Company-analysis changes (classification/evidence, NOT price-driven): {diff.get("company_analysis_changes")}')
        lines.append(f'  Market-weight changes (price-driven, no share count change): {diff.get("market_weight_changes")}')
        lines.append(f'  User holding changes (share count changed by the user): {diff.get("user_holding_changes")}')

    return '\n'.join(lines)


def generate_portfolio_briefing(portfolio, snapshot, diff: dict, user=None):
    """
    Generates and persists a new draft PortfolioBriefing version for
    `snapshot`. Never touches a prior version.
    """
    from investor_portfolio.models import PortfolioBriefing
    from agent_runtime_model_router.services.model_router import select_model_route

    route = select_model_route(
        agent_name='EcoIQ Portfolio Briefing Analyst',
        task_type='portfolio_briefing',
        execution_mode='live',
        sensitivity_level='standard',
        requires_reasoning=True,
    )

    client = _get_client()
    model = _get_model()
    context = build_grounding_context(snapshot, diff)

    prompt = f"""You are EcoIQ's portfolio sustainability-risk analyst. Summarise this portfolio's ALREADY-CALCULATED
EcoIQ exposure numbers in plain, neutral language. You are explaining numbers a deterministic calculation
already produced — you never calculate or estimate a score yourself.
{PROHIBITED_TERMS_REMINDER}

PORTFOLIO ANALYTICS (the ONLY facts you may use):
{context}

Return ONLY valid JSON with exactly this structure:
{REPORT_JSON_SCHEMA_HINT}
"""

    last_version = PortfolioBriefing.objects.filter(portfolio=portfolio).order_by('-version').first()
    next_version = (last_version.version + 1) if last_version else 1

    logger.info('Generating portfolio briefing for %s (v%s)', portfolio.name, next_version)
    response = client.messages.create(
        model=model, max_tokens=2048,
        messages=[{'role': 'user', 'content': prompt}],
    )
    raw = response.content[0].text
    data = _parse_json(raw)

    content = {key: data.get(key) for key in (
        'summary', 'largest_exposure_concentrations', 'top_contributors',
        'insufficient_evidence_areas', 'changes_since_prior_snapshot', 'due_diligence_questions',
    )}

    flags = []
    for value in content.values():
        if isinstance(value, str):
            flags += check_prohibited_language(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    flags += check_prohibited_language(item)

    briefing = PortfolioBriefing.objects.create(
        portfolio=portfolio, snapshot=snapshot, version=next_version, status='draft',
        content=content,
        model_name=model, model_provider=route['selected_provider'], routing_reason=route['reason'],
        prompt_version='v1', methodology_version=snapshot.methodology_version,
        prohibited_language_flags=flags,
        generated_by=user if (user and getattr(user, 'is_authenticated', False)) else None,
    )
    logger.info('Portfolio briefing v%s saved for %s (flags=%d)', briefing.version, portfolio.name, len(flags))
    return briefing
