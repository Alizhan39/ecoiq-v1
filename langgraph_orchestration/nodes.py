"""
langgraph_orchestration/nodes.py — every node function used by graph.py.

Every node calls into an EXISTING service — none of these implement new
scoring, evidence, geo or agent logic of their own. Each node's docstring
names exactly which existing module it reuses.
"""
import datetime

import numpy as np
from django.utils import timezone

from langgraph_orchestration.state import record_node

DEFAULT_EXECUTION_MODE = 'deterministic_test'


def classify_intent(state):
    """
    Resolves target_type from the caller-supplied target_id/type hint and
    location — deliberately NOT a free-text NLU classifier (there is no new
    ML/LLM classification here, matching ai_agent_workbench.recommender's
    own precedent of a transparent, inspectable rule rather than a black box).
    """
    record_node(state, 'classify_intent')

    if state.get('location'):
        state['target_type'] = 'location'
        return state

    target_id = state.get('target_id')
    hint = state.get('target_type')

    if target_id and hint == 'company':
        from companies.models import CompanyProfile
        profile = CompanyProfile.objects.filter(pk=target_id).select_related('company').first()
        if profile:
            state['company'] = {
                'id': profile.pk,
                'name': profile.company.name if profile.company_id else f'Profile #{profile.pk}',
                'country': profile.company.country if profile.company_id else '',
            }
            state['target_type'] = 'company'
            return state

    if target_id and hint == 'country':
        from countries.models import CountryProfile
        country = CountryProfile.objects.filter(pk=target_id).first()
        if country:
            state['country'] = {'id': country.pk, 'name': country.name}
            state['target_type'] = 'country'
            return state

    state['target_type'] = 'unknown'
    return state


def handle_unresolved_target(state):
    """
    Reached only when classify_intent could not resolve a company, country
    or location. A real node (not a conditional-edge callback) — LangGraph
    conditional-edge router functions are read-only routing decisions; any
    state mutation made inside one is silently discarded from the final
    result, confirmed empirically before this was split out as its own node.
    """
    record_node(state, 'handle_unresolved_target')
    state['status'] = 'failed'
    state['failed_node'] = 'classify_intent'
    state.setdefault('verification_notes', []).append(
        'Could not resolve a company, country or location target from the given input.',
    )
    return state


def retrieve_evidence_memory(state):
    """Reuses evidence_memory.services.memory.search_similar/search_company_memory/search_country_memory."""
    record_node(state, 'retrieve_evidence_memory')
    from evidence_memory.services import memory as memory_service

    company_obj = None
    if state.get('company'):
        from companies.models import CompanyProfile
        company_obj = CompanyProfile.objects.filter(pk=state['company']['id']).first()
    country_obj = None
    if state.get('country'):
        from countries.models import CountryProfile
        country_obj = CountryProfile.objects.filter(pk=state['country']['id']).first()

    query = state.get('user_request') or (state.get('company') or state.get('country') or {}).get('name', '')
    results = memory_service.search_similar(query, top_k=5, company=company_obj, country=country_obj) if query else []
    memories = [
        {'id': m.pk, 'text': m.text_chunk[:200], 'confidence': m.confidence, 'source_type': m.source_type}
        for m in results
    ]
    known_confidences = [m['confidence'] for m in memories if m['confidence'] is not None]
    avg_confidence = float(np.mean(known_confidences)) if known_confidences else None
    weak = (len(memories) == 0) or (avg_confidence is not None and avg_confidence < 50)

    state['evidence_context'] = {
        'available': bool(memories), 'count': len(memories), 'memories': memories,
        'avg_confidence': round(avg_confidence, 1) if avg_confidence is not None else None, 'weak': weak,
    }
    if weak:
        state.setdefault('verification_notes', []).append(
            'Evidence Memory is weak or empty for this target — findings should be treated cautiously.',
        )
    return state


def gather_geo_intelligence(state):
    """
    Reuses pandas_scoring_engine.services.scoring.compute_country_geo_components
    (itself built on geo_intelligence data) for a resolved company/country,
    and geo_intelligence.services.weather.get_city_climate_summary for an
    explicit lat/lng location.
    """
    record_node(state, 'gather_geo_intelligence')
    from pandas_scoring_engine.services.scoring import compute_country_geo_components

    country_obj = None
    if state.get('country'):
        from countries.models import CountryProfile
        country_obj = CountryProfile.objects.filter(pk=state['country']['id']).first()
    elif state.get('company') and state['company'].get('country'):
        from countries.models import CountryProfile
        country_obj = CountryProfile.objects.filter(name__iexact=state['company']['country']).first()

    geo_context = {'available': False}
    if country_obj:
        components = compute_country_geo_components(country_obj)
        geo_context = {
            'available': any(v is not None for v in components.values()),
            'country': country_obj.name, **components,
        }

    if state.get('location'):
        from geo_intelligence.services.weather import get_city_climate_summary
        loc = state['location']
        summary = get_city_climate_summary('Requested location', loc['latitude'], loc['longitude'])
        geo_context['location_climate'] = summary
        geo_context['available'] = geo_context['available'] or bool(summary.get('available'))

    state['geo_context'] = geo_context
    return state


def run_agent_analysis(state):
    """
    Reuses ai_agent_workbench.services.recommender.recommend_agent_for_task
    to pick an agent, then the EXACT SAME create_agent_run -> execute_agent
    pipeline agent_runtime_model_router/backend_intelligence_engine already
    use — no second execution path. execution_mode defaults to
    'deterministic_test' (never silently claims 'live' — see
    execution_mode_used in the recorded output, which is always the real,
    honest value execute_agent returned).
    """
    record_node(state, 'run_agent_analysis')
    from ai_agent_workbench.services.recommender import recommend_agent_for_task
    from agent_runtime_model_router.services.execution import create_agent_run, execute_agent

    question = state.get('user_request') or f'Analyse this {state.get("target_type", "target")}'
    recommendation = recommend_agent_for_task(question)
    agent_name = recommendation['agent_name']

    target_label = (state.get('company') or state.get('country') or {}).get('name', state.get('target_type', 'unknown'))
    execution_mode = state.get('execution_mode', DEFAULT_EXECUTION_MODE)

    agent_run = create_agent_run(
        agent_name, 'langgraph_orchestration_analysis', execution_mode=execution_mode,
        input_summary=f'{question} (target: {target_label})',
    )
    agent_run = execute_agent(agent_run)

    output = agent_run.parsed_output or {}
    state['agent_outputs'] = [{
        'agent_run_id': agent_run.pk, 'agent_name': agent_name,
        'status': agent_run.status,
        'execution_mode_requested': agent_run.execution_mode_requested,
        'execution_mode_used': agent_run.execution_mode_used,
        'confidence': agent_run.calibrated_confidence if agent_run.calibrated_confidence is not None else agent_run.raw_confidence,
        'output_summary': output.get('output_summary', ''),
        'recommendation_reason': recommendation['why'],
    }]
    return state


def recalculate_score_if_needed(state):
    """
    Reuses pandas_scoring_engine.services.scoring.compute_company_intelligence_score
    — this graph node runs it synchronously and labels it as such (this node
    itself typically already runs inside a Celery task via
    run_langgraph_intelligence_workflow, so a further synchronous call here
    is consistent with, not a bypass of, the background-task architecture).
    """
    record_node(state, 'recalculate_score_if_needed')

    if state.get('target_type') != 'company' or not state.get('company'):
        state['scoring_context'] = {'available': False, 'reason': 'Scoring only applies to a company target.'}
        return state

    from companies.models import CompanyProfile
    from pandas_scoring_engine.services.scoring import compute_company_intelligence_score

    profile = CompanyProfile.objects.filter(pk=state['company']['id']).first()
    if not profile:
        state['scoring_context'] = {'available': False, 'reason': 'Company profile not found.'}
        return state

    latest_snapshot = profile.score_snapshots.filter(intelligence_score__isnull=False).order_by('-date').first()
    is_stale = (latest_snapshot is None) or (
        timezone.now().date() - latest_snapshot.date > datetime.timedelta(days=30)
    )

    if is_stale:
        scores = compute_company_intelligence_score(profile)
        state['scoring_context'] = {'available': True, 'source': 'recalculated_synchronously', **scores}
    else:
        state['scoring_context'] = {
            'available': True, 'source': 'existing_snapshot', 'snapshot_date': str(latest_snapshot.date),
            'intelligence_score': latest_snapshot.intelligence_score,
            'confidence': latest_snapshot.intelligence_confidence,
        }
    return state


def run_intelligence_analytics(state):
    """Reuses intelligence_analytics_engine.services (similarity, clustering, outliers, recommendations)."""
    record_node(state, 'run_intelligence_analytics')
    analytics_context = {'available': False}

    if state.get('target_type') == 'company' and state.get('company'):
        from intelligence_analytics_engine.services import outliers, recommendations, similarity

        company_id = state['company']['id']
        similar = similarity.find_similar_companies(company_id, top_n=3)
        outlier_result = outliers.detect_company_outliers()
        own_outlier = None
        if outlier_result['available']:
            own_outlier = next((o for o in outlier_result['outliers'] if o['id'] == company_id), None)
        recs = recommendations.recommend_for_company(company_id)

        analytics_context = {
            'available': True,
            'similar_companies': similar['results'] if similar['available'] else [],
            'is_outlier': own_outlier is not None,
            'outlier_detail': own_outlier,
            'recommendations': recs['recommendations'] if recs['available'] else [],
        }

    elif state.get('target_type') == 'country' and state.get('country'):
        from intelligence_analytics_engine.services import clustering, similarity

        country_id = state['country']['id']
        similar = similarity.find_similar_countries(country_id, top_n=3)
        clusters = clustering.climate_risk_clusters(n_clusters=3)
        own_cluster = None
        if clusters['available']:
            own_cluster = next(
                (c for c in clusters['clusters'] if any(x['id'] == country_id for x in c['countries'])), None,
            )
        analytics_context = {
            'available': True,
            'similar_countries': similar['results'] if similar['available'] else [],
            'climate_risk_cluster': own_cluster,
        }

    state['analytics_context'] = analytics_context
    return state


def verify_output(state):
    """
    The lightweight verification node: checks evidence exists, confidence is
    numeric, recommendations have a stated reason, and marks low/absent
    confidence for human review rather than presenting it as trustworthy.
    """
    record_node(state, 'verify_output')
    notes = state.setdefault('verification_notes', [])

    if not state.get('evidence_context', {}).get('available'):
        notes.append('No Evidence Memory available for this target.')

    confidences = []
    for output in state.get('agent_outputs', []):
        if isinstance(output.get('confidence'), (int, float)):
            confidences.append(output['confidence'])
    if isinstance(state.get('scoring_context', {}).get('confidence'), (int, float)):
        confidences.append(state['scoring_context']['confidence'])
    if isinstance(state.get('evidence_context', {}).get('avg_confidence'), (int, float)):
        confidences.append(state['evidence_context']['avg_confidence'])

    overall_confidence = float(np.mean(confidences)) if confidences else None
    state['confidence'] = round(overall_confidence, 1) if overall_confidence is not None else None

    if overall_confidence is None:
        notes.append('No numeric confidence signal was available from any node.')
        state['human_review_required'] = True
    elif overall_confidence < 50:
        notes.append(f'Overall confidence ({overall_confidence:.1f}) is low — marked for human review.')
        state['human_review_required'] = True

    for rec in state.get('analytics_context', {}).get('recommendations', []):
        if not rec.get('basis'):
            notes.append(f'Recommendation "{rec.get("summary", "")}" has no stated basis — flagged.')

    return state


def finalize(state):
    """Assembles final_recommendations/next_actions — never a dead end."""
    record_node(state, 'finalize')
    recommendations_out = []

    for output in state.get('agent_outputs', []):
        if output.get('output_summary'):
            recommendations_out.append({
                'type': 'agent_finding', 'summary': output['output_summary'], 'source': output['agent_name'],
                'basis': output.get('recommendation_reason', ''),
            })

    recommendations_out.extend(state.get('analytics_context', {}).get('recommendations', []))

    scoring = state.get('scoring_context', {})
    if scoring.get('available') and scoring.get('intelligence_score') is not None:
        recommendations_out.append({
            'type': 'intelligence_score',
            'summary': f'EcoIQ Intelligence Score: {scoring["intelligence_score"]}/100 ({scoring["source"]}).',
            'basis': 'pandas_scoring_engine.compute_company_intelligence_score',
            'source': 'pandas_scoring_engine',
        })

    next_actions = []
    if state.get('evidence_context', {}).get('weak'):
        next_actions.append('Gather more evidence for this target before relying on these findings.')
    if state.get('human_review_required'):
        next_actions.append('Route to human review before acting on this analysis.')
    if not next_actions:
        next_actions.append('Send to AI Agent Council for full governed review.')

    state['final_recommendations'] = recommendations_out
    state['next_actions'] = next_actions
    if state.get('status') == 'running':
        state['status'] = 'needs_human_review' if state.get('human_review_required') else 'completed'
    return state
