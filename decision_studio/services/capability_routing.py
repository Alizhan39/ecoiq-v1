"""
decision_studio/services/capability_routing.py — decides WHICH existing
EcoIQ capabilities a question actually needs, and skips the rest. This is
the explicit cost-control mechanism the spec requires ("do not run every
module for every question") — a plain ordered list of (capability, reason)
tuples, never a black box.

Capabilities map directly onto existing modules — nothing here executes
anything itself:
  EVIDENCE_MEMORY      -> evidence_memory.services.memory
  GEO_INTELLIGENCE     -> geo_intelligence.services / pandas_scoring_engine's
                          country-level components
  SCORING              -> pandas_scoring_engine.services.scoring
  ANALYTICS            -> intelligence_analytics_engine.services.*
  AI_AGENTS            -> agent_runtime_model_router (via langgraph_orchestration)
  COUNCIL              -> ai_agent_council (via langgraph_orchestration)
  VISUAL_INTELLIGENCE  -> plotly_visual_intelligence.services.charts
"""
EVIDENCE_QUALITY_KEYWORDS = ['evidence is too weak', 'evidence too weak', 'weak evidence', 'insufficient evidence', 'evidence quality', 'evidence coverage']

# Cost control: AI_AGENTS/COUNCIL (the only capabilities that can invoke a
# real LLM call) only ever run for a bounded number of top entities.
MAX_ENTITIES_FOR_AGENT_ANALYSIS = 3


def build_capability_plan(question_text, intent, scope, entities):
    text = (question_text or '').lower()
    has_company = any(e['type'] == 'company' for e in entities)
    has_country = any(e['type'] == 'country' for e in entities)
    has_sector = any(e['type'] == 'sector' for e in entities)
    is_evidence_quality_question = any(kw in text for kw in EVIDENCE_QUALITY_KEYWORDS)

    plan = [
        {'capability': 'EVIDENCE_MEMORY', 'reason': 'Every decision question needs grounding evidence, retrieved first.', 'executed': False},
    ]

    if is_evidence_quality_question:
        # A meta-question about data quality itself — the cheapest possible
        # path: evidence + its distribution, nothing else.
        plan.append({
            'capability': 'ANALYTICS', 'executed': False,
            'reason': 'Question is about evidence quality/coverage itself — evidence_distribution analytics answers it directly.',
        })
        return plan

    if has_country and not has_company:
        plan.append({
            'capability': 'GEO_INTELLIGENCE', 'executed': False,
            'reason': 'A country/region was resolved without a specific company — Geo Intelligence provides the geographic risk/opportunity context.',
        })

    # Unconditional for these intents — _resolve_company_queryset() already
    # falls back to a bounded "all available companies" scope when no
    # specific company/sector/country was resolved (e.g. "compare available
    # companies" has zero named entities but is still a real comparison).
    needs_comparison = intent in ('COMPARE', 'RANK', 'PRIORITISE', 'ASSESS', 'RECOMMEND')
    if needs_comparison:
        plan.append({
            'capability': 'SCORING', 'executed': False,
            'reason': f'Intent "{intent}" requires explainable, comparable scores across the resolved scope.',
        })
        plan.append({
            'capability': 'ANALYTICS', 'executed': False,
            'reason': 'Similarity/ranking/outlier analysis over the scored entities.',
        })
    elif intent in ('FIND_RISK', 'FIND_OPPORTUNITY'):
        plan.append({
            'capability': 'ANALYTICS', 'executed': False,
            'reason': f'Intent "{intent}" is answered directly by the existing risk/opportunity analytics, without needing a full scoring pass.',
        })
    elif intent == 'INVESTIGATE':
        plan.append({
            'capability': 'ANALYTICS', 'executed': False,
            'reason': 'Outlier detection is the analytics capability suited to "investigate" questions.',
        })

    # Scoped to a real entity/sector/country — cost control keeps the
    # expensive agent+Council path off a totally unscoped "compare available
    # companies" question, but on for e.g. "UK energy companies..." even
    # with no single company named.
    if needs_comparison and (has_company or has_sector or has_country):
        plan.append({
            'capability': 'AI_AGENTS', 'executed': False,
            'reason': f'A specialised agent deep-dive on the top {MAX_ENTITIES_FOR_AGENT_ANALYSIS} ranked company/ies adds analysis scoring/analytics alone cannot.',
        })
        plan.append({
            'capability': 'COUNCIL', 'executed': False,
            'reason': 'Multi-agent Council synthesis governs the final recommendation for a comparison/prioritisation decision.',
        })

    has_chartable_capability = any(step['capability'] in ('SCORING', 'ANALYTICS', 'GEO_INTELLIGENCE') for step in plan)
    if has_chartable_capability:
        plan.append({
            'capability': 'VISUAL_INTELLIGENCE', 'executed': False,
            'reason': 'A chart makes the comparison/ranking/risk-opportunity signal easier to understand than text alone.',
        })

    return plan
