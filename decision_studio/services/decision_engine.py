"""
decision_studio/services/decision_engine.py — the one orchestrating
function, answer_question(). Calls existing services directly; the only
"second orchestrator" concept here is capability SELECTION (which of the
existing engines to call), never a duplicate implementation of any of them.

Cost controls (spec section 18), all enforced here in one place:
  MAX_ENTITIES              — company/country rows considered at all
  MAX_ENTITIES_FOR_SCORING  — how many get a synchronous score computed
  MAX_EVIDENCE_PER_ENTITY   — evidence_memory retrieval top_k per entity
  MAX_ENTITIES_FOR_AGENTS   — how many get a full agent+Council run
"""
from companies.models import CompanyProfile, CompanyScoreSnapshot
from countries.models import CountryProfile
from decision_studio.services import capability_routing, data_availability, query_understanding

MAX_ENTITIES = 20
MAX_ENTITIES_FOR_SCORING = 20
MAX_EVIDENCE_PER_ENTITY = 5
MAX_ENTITIES_FOR_AGENTS = capability_routing.MAX_ENTITIES_FOR_AGENT_ANALYSIS

DIMENSION_TO_SNAPSHOT_FIELD = {
    'investment_opportunity': 'investment_opportunity_score',
    'modernisation_priority': 'modernisation_priority_score',
    'climate_risk': 'climate_risk_score',
    'governance_esg': 'total_score',
    'evidence_quality': 'evidence_quality_score',
}


def _resolve_company_queryset(entities, scope):
    company_entities = [e for e in entities if e['type'] == 'company' and e.get('id')]
    if company_entities:
        return list(CompanyProfile.objects.filter(pk__in=[e['id'] for e in company_entities]).select_related('company'))

    queryset = CompanyProfile.objects.filter(status__in=('public', 'verified')).select_related('company')
    if scope.get('sector'):
        queryset = queryset.filter(company__sector=scope['sector'])
    if scope.get('country'):
        queryset = queryset.filter(company__country__iexact=scope['country'])
    return list(queryset[:MAX_ENTITIES])


def _latest_snapshot(profile):
    from plotly_visual_intelligence.services.dashboard_data import latest_intelligence_snapshot
    return latest_intelligence_snapshot(profile)


def _ensure_scored(profiles):
    """Computes a snapshot only for profiles that don't already have one — never recomputes needlessly."""
    from pandas_scoring_engine.services.scoring import compute_company_intelligence_score

    for profile in profiles[:MAX_ENTITIES_FOR_SCORING]:
        if _latest_snapshot(profile) is None:
            scores = compute_company_intelligence_score(profile)
            CompanyScoreSnapshot.create_from_profile(
                profile, trigger='intelligence_score_recalc',
                notes='Computed on demand by the Decision Studio.', intelligence_scores=scores,
            )


def _evidence_to_dict(memory):
    return {
        'excerpt': memory.text_chunk[:400], 'source_type': memory.get_source_type_display(),
        'entity': memory.company.company.name if memory.company_id and memory.company.company_id else (memory.country.name if memory.country_id else ''),
        'confidence': memory.confidence, 'date': memory.date_collected.isoformat() if memory.date_collected else None,
        'is_demo': memory.is_demo,
    }


def _retrieve_evidence(question_text, profiles, countries):
    from evidence_memory.services.memory import search_company_memory, search_country_memory, search_similar

    items = []
    for profile in profiles:
        for memory in search_company_memory(profile, question_text, top_k=MAX_EVIDENCE_PER_ENTITY):
            items.append(_evidence_to_dict(memory))
    for country in countries:
        for memory in search_country_memory(country, question_text, top_k=MAX_EVIDENCE_PER_ENTITY):
            items.append(_evidence_to_dict(memory))
    if not profiles and not countries:
        for memory in search_similar(question_text, top_k=MAX_EVIDENCE_PER_ENTITY):
            items.append(_evidence_to_dict(memory))
    # Deduplicate on excerpt text — the same finding retrieved via two paths should appear once.
    seen, deduped = set(), []
    for item in items:
        if item['excerpt'] in seen:
            continue
        seen.add(item['excerpt'])
        deduped.append(item)
    return deduped


def _build_ranking(profiles, scope):
    dimensions = scope.get('requested_dimensions') or []
    field = DIMENSION_TO_SNAPSHOT_FIELD.get(dimensions[0]) if dimensions else 'intelligence_score'

    rows = []
    for profile in profiles:
        snapshot = _latest_snapshot(profile)
        value = getattr(snapshot, field, None) if snapshot else None
        rows.append({
            'company_id': profile.pk, 'name': profile.company.name if profile.company_id else f'Profile #{profile.pk}',
            'value': value, 'dimension': field, 'intelligence_score': snapshot.intelligence_score if snapshot else None,
            'confidence': snapshot.intelligence_confidence if snapshot else None,
        })
    ranked = sorted([r for r in rows if r['value'] is not None], key=lambda r: r['value'], reverse=True)
    unranked = [r for r in rows if r['value'] is None]
    for i, row in enumerate(ranked, start=1):
        row['rank'] = i
    return ranked + unranked


def _run_agent_analysis(profiles, execution_mode):
    from langgraph_orchestration.graph import run_orchestration

    agent_runs = []
    for profile in profiles[:MAX_ENTITIES_FOR_AGENTS]:
        final_state = run_orchestration(
            user_request=f'Decision Studio analysis for {profile.company.name if profile.company_id else profile.pk}',
            target_id=profile.pk, target_type='company', execution_mode=execution_mode,
        )
        agent_runs.append({
            'company_id': profile.pk, 'name': profile.company.name if profile.company_id else f'Profile #{profile.pk}',
            'status': final_state.get('status'), 'confidence': final_state.get('confidence'),
            'agent_outputs': final_state.get('agent_outputs', []),
            'final_recommendations': final_state.get('final_recommendations', []),
            'nodes_executed': final_state.get('nodes_executed', []),
        })
    return agent_runs


def _compute_confidence(availability_status, evidence_count, agent_runs):
    if availability_status == 'INSUFFICIENT':
        return 'INSUFFICIENT_EVIDENCE', None
    score = 70.0
    if availability_status == 'PARTIAL':
        score -= 25
    if evidence_count == 0:
        score -= 25
    elif evidence_count < 3:
        score -= 10
    low_confidence_agents = [r for r in agent_runs if r.get('confidence') is not None and r['confidence'] < 50]
    if agent_runs and low_confidence_agents:
        score -= 10
    score = max(5.0, min(95.0, score))
    label = 'HIGH' if score >= 70 else 'MEDIUM' if score >= 45 else 'LOW'
    return label, round(score, 1)


def _build_executive_answer(intent, ranking, availability_status):
    if availability_status == 'INSUFFICIENT':
        return "EcoIQ currently has insufficient evidence to make this recommendation reliably."
    ranked = [r for r in ranking if r.get('rank')]
    if not ranked:
        return "EcoIQ resolved the question's scope, but no company currently has enough scoring data to answer with confidence."
    top = ranked[0]
    sentence = f'Based on available EcoIQ evidence, {top["name"]} currently shows the strongest signal among the {len(ranked)} compan{"y" if len(ranked)==1 else "ies"} considered'
    if len(ranked) > 1:
        sentence += f', followed by {ranked[1]["name"]}.'
    else:
        sentence += '.'
    return sentence


def _build_follow_up_questions(ranking, intent):
    ranked = [r for r in ranking if r.get('rank')]
    questions = []
    if len(ranked) >= 2:
        questions.append(f'Why is {ranked[0]["name"]} ranked above {ranked[1]["name"]}?')
    if ranked:
        questions.append(f'What are the main risks for {ranked[0]["name"]}?')
    questions.append('What data is missing?')
    questions.append('Show only companies with strong evidence quality.')
    return questions


def answer_question(question_text, execution_mode='deterministic_test'):
    """
    Returns {'intent', 'scope', 'entities', 'capability_plan',
    'data_availability', 'result': {...Decision Result...}}. Never raises
    for a normal "no data" case — that's an honest INSUFFICIENT result, not
    an exception.
    """
    intent = query_understanding.classify_intent(question_text)
    scope = query_understanding.extract_scope(question_text)
    entities = query_understanding.resolve_entities(question_text, scope)
    plan = capability_routing.build_capability_plan(question_text, intent, scope, entities)

    modules_used, agents_used, visualizations = [], [], []
    ranking, evidence_items, agent_runs = [], [], []
    uncertainty_notes, risks, opportunities = [], [], []

    profiles = _resolve_company_queryset(entities, scope)
    countries = [CountryProfile.objects.get(pk=e['id']) for e in entities if e['type'] == 'country' and e.get('id')]

    # Judged against the REAL resolved scope (profiles), not just explicitly
    # named entities — a general "compare available companies" question
    # resolves a real bounded scope with zero named entities and deserves a
    # genuine availability verdict, not a default UNKNOWN.
    availability = data_availability.check_data_availability(profiles)

    for step in plan:
        cap = step['capability']

        if cap == 'EVIDENCE_MEMORY':
            evidence_items = _retrieve_evidence(question_text, profiles, countries)
            step['executed'] = True
            modules_used.append('Evidence Memory')

        elif cap == 'GEO_INTELLIGENCE':
            step['executed'] = True
            modules_used.append('Geo Intelligence')

        elif cap == 'SCORING':
            _ensure_scored(profiles)
            step['executed'] = True
            modules_used.append('Pandas Scoring Engine')

        elif cap == 'ANALYTICS':
            if step['reason'].startswith('Question is about evidence quality'):
                from intelligence_analytics_engine.services.evidence_distribution import evidence_quality_distribution
                distribution = evidence_quality_distribution()
                if not distribution['available']:
                    uncertainty_notes.append('No evidence records exist yet to assess evidence quality distribution.')
                else:
                    uncertainty_notes.append(f"Platform-wide evidence confidence averages {distribution['mean']}% across {distribution['count']} record(s).")
            else:
                ranking = _build_ranking(profiles, scope)
                if intent == 'INVESTIGATE':
                    from intelligence_analytics_engine.services.outliers import detect_company_outliers
                    outlier_result = detect_company_outliers()
                    if outlier_result['available']:
                        scoped_ids = {p.pk for p in profiles}
                        matched = [o for o in outlier_result['outliers'] if not scoped_ids or o['id'] in scoped_ids]
                        for o in matched:
                            uncertainty_notes.append(f"{o['name']} is a statistical outlier: {o.get('reason', '')}")
            step['executed'] = True
            modules_used.append('Intelligence Analytics Engine')

        elif cap == 'AI_AGENTS':
            top_profiles = [p for p in profiles if p.pk in {r['company_id'] for r in ranking[:MAX_ENTITIES_FOR_AGENTS]}] or profiles[:MAX_ENTITIES_FOR_AGENTS]
            agent_runs = _run_agent_analysis(top_profiles, execution_mode)
            step['executed'] = True
            modules_used.append('Agent Runtime & Model Router')
            agents_used.extend({name for run in agent_runs for o in run['agent_outputs'] for name in [o.get('agent_name')] if name})

        elif cap == 'COUNCIL':
            step['executed'] = any(run.get('nodes_executed') and 'finalize' in run['nodes_executed'] for run in agent_runs)
            modules_used.append('AI Agent Council')

        elif cap == 'VISUAL_INTELLIGENCE':
            from decision_studio.services import visualization
            visualizations = visualization.build_visualizations(intent, profiles, ranking)
            step['executed'] = True
            modules_used.append('Plotly Visual Intelligence')

    for run in agent_runs:
        for note in run.get('final_recommendations', []) or []:
            if isinstance(note, str):
                risks.append(note) if 'risk' in note.lower() else opportunities.append(note)

    confidence_label, confidence_score = _compute_confidence(availability['status'], len(evidence_items), agent_runs)
    executive_answer = _build_executive_answer(intent, ranking, availability['status'])

    if availability['status'] == 'PARTIAL':
        uncertainty_notes.append('Some resolved companies do not yet have a full EcoIQ Intelligence Score or evidence coverage — see data gaps below.')
    if not evidence_items:
        uncertainty_notes.append('No supporting evidence records were retrieved for this question.')

    result = {
        'executive_answer': executive_answer,
        'key_findings': [f"{r['name']}: {r.get('dimension', 'intelligence_score')} = {r['value']}" for r in ranking if r.get('rank')][:5],
        'ranking': ranking,
        'recommendation': executive_answer if intent in ('RECOMMEND', 'PRIORITISE') else '',
        'rationale': ' '.join(uncertainty_notes) if uncertainty_notes else 'See supporting evidence and analysis modules used below.',
        'supporting_evidence': evidence_items,
        'counter_evidence': [],
        'risks': risks,
        'opportunities': opportunities,
        'confidence_label': confidence_label,
        'confidence_score': confidence_score,
        'uncertainty_notes': uncertainty_notes,
        'data_gaps': availability['missing_data'],
        'sources': sorted({item['source_type'] for item in evidence_items}),
        'modules_used': modules_used,
        'agents_used': sorted(agents_used),
        'visualizations': visualizations,
        'follow_up_questions': _build_follow_up_questions(ranking, intent),
    }

    return {
        'intent': intent, 'scope': scope, 'entities': entities, 'capability_plan': plan,
        'data_availability': availability['status'], 'data_availability_detail': availability,
        'confidence_label': confidence_label, 'confidence_score': confidence_score,
        'result': result,
    }
