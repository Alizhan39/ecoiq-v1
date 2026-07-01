"""
LegacySafe AI — modernisation planner.

MVP: a structured mock response built only from chunks retrieval already
cleared for this user. No LLM call yet — this is the seam where an
Anthropic/OpenAI call plugs in later. When it does, the allowed chunk text
must still be treated as inert evidence, never as instructions: retrieval
has already filtered it, but content (e.g. the seeded prompt-injection demo
document) can still contain text that *looks* like an instruction. The
system prompt for the real model must say so explicitly.
"""
from legacy_safe.models import MemoryChunk
from legacy_safe.services.retrieval import retrieve_allowed_chunks

_INSIGHTS = {
    'esg_report': {
        'systems': ['ESG Reporting'],
        'risks': ['Reputational exposure if reported emissions targets are missed'],
        'actions': ['Publish quarterly progress against the stated ESG targets'],
    },
    'maintenance_notes': {
        'systems': ['Legacy Coal Boiler', 'Heat Network'],
        'risks': ['Unplanned downtime from ageing components', 'Heat network reliability risk'],
        'actions': ['Schedule phased boiler replacement', 'Add condition-monitoring sensors to critical assets'],
    },
    'budget': {
        'systems': ['Capital Planning'],
        'risks': ['Underfunded transition if CAPEX is not staged correctly'],
        'actions': ['Stage capital expenditure across boiler replacement, grid upgrades, and heat pump integration'],
    },
    'strategy_memo': {
        'systems': ['Board Governance'],
        'risks': ['Regulatory and reputational exposure from a delayed coal-to-clean-heat decision'],
        'actions': ['Bring a phased transition proposal to the board for formal sign-off'],
    },
    'other': {
        'systems': [],
        'risks': [],
        'actions': [],
    },
}


def generate_modernisation_plan(user, project, question):
    """Return a structured plan built only from evidence this user is allowed to see."""
    retrieval = retrieve_allowed_chunks(user, project, question)
    allowed = retrieval['allowed']
    blocked = retrieval['blocked']

    affected_systems, risks, recommended_actions = [], [], []
    seen_doc_types = set()
    for entry in allowed:
        chunk = MemoryChunk.objects.select_related('source_document').get(id=entry['chunk_id'])
        doc_type = chunk.source_document.document_type
        if doc_type in seen_doc_types:
            continue
        seen_doc_types.add(doc_type)
        insight = _INSIGHTS.get(doc_type, _INSIGHTS['other'])
        affected_systems.extend(s for s in insight['systems'] if s not in affected_systems)
        risks.extend(r for r in insight['risks'] if r not in risks)
        recommended_actions.extend(a for a in insight['actions'] if a not in recommended_actions)

    if allowed:
        answer = (
            f'Based on {len(allowed)} allowed evidence item(s), the modernisation plan for '
            f'"{project.name}" covers: ' + '; '.join(affected_systems or ['no specific systems identified']) + '.'
        )
    else:
        answer = 'No evidence was accessible for this role — no plan could be generated.'

    if blocked:
        answer += f' {len(blocked)} additional source(s) exist but were excluded due to insufficient permissions.'

    return {
        'answer': answer,
        'affected_systems': affected_systems,
        'risks': risks,
        'recommended_actions': recommended_actions,
        'evidence_used': [
            {'source_title': e['source_title'], 'access_level': e['access_level'], 'text': e['text']}
            for e in allowed
        ],
        'restricted_evidence_excluded': [
            {'source_title': e['source_title'], 'access_level': e['access_level'], 'reason': e['reason']}
            for e in blocked
        ],
        'audit_log': retrieval['audit_log'],
    }
