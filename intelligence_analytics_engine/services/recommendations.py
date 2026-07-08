"""
intelligence_analytics_engine/services/recommendations.py — the
Recommendation Engine that ties every other capability in this app
together for one company, and connects the result to the AI Agent
Workbench, Evidence Memory and Pandas Scoring Engine.

Every recommendation names exactly which upstream analysis produced it
(similar-company match, percentile rank, outlier z-score, evidence
distribution) — never a bare suggestion with no traceable basis. This is
a synthesis layer, not a ninth model: it calls the other services in this
app, plus ai_agent_workbench.services.recommender.recommend_agent_for_task()
(reused exactly as the AI Agent Workbench's own natural-language box uses
it — no second agent-recommendation implementation).
"""
from intelligence_analytics_engine.services.evidence_distribution import evidence_quality_distribution
from intelligence_analytics_engine.services.outliers import detect_company_outliers
from intelligence_analytics_engine.services.ranking import modernisation_priority_ranking
from intelligence_analytics_engine.services.similarity import find_similar_companies


def recommend_for_company(company_profile_id, similar_top_n=3):
    from companies.models import CompanyProfile

    try:
        profile = CompanyProfile.objects.select_related('company').get(pk=company_profile_id)
    except CompanyProfile.DoesNotExist:
        return {'available': False, 'reason': f'CompanyProfile {company_profile_id} does not exist.'}

    recommendations = []

    similar = find_similar_companies(company_profile_id, top_n=similar_top_n)
    if similar['available'] and similar['results']:
        names = ', '.join(r['name'] for r in similar['results'])
        recommendations.append({
            'type': 'peer_comparison',
            'summary': f'Compare against similar companies: {names}.',
            'basis': f'{similar["method"]}, based on {similar["features_used"]}.',
            'source': 'intelligence_analytics_engine.similarity.find_similar_companies',
            'details': similar['results'],
        })

    ranking = modernisation_priority_ranking(scope='company', top_n=None)
    if ranking['available']:
        own_entry = next((r for r in ranking['results'] if r['id'] == company_profile_id), None)
        if own_entry:
            if own_entry['percentile'] >= 75:
                recommendations.append({
                    'type': 'modernisation_priority',
                    'summary': (
                        f'{own_entry["name"]} ranks in the top {100 - own_entry["percentile"]:.0f}% for modernisation '
                        f'priority (rank {own_entry["rank"]} of {ranking["total_ranked"]}) — worth a modernisation plan.'
                    ),
                    'basis': own_entry['explanation'],
                    'source': 'intelligence_analytics_engine.ranking.modernisation_priority_ranking',
                    'ai_agent_workbench_suggestion': _suggest_agent('Which modernisation pathway fits?'),
                })

    outliers = detect_company_outliers()
    if outliers['available']:
        own_outlier = next((o for o in outliers['outliers'] if o['id'] == company_profile_id), None)
        if own_outlier:
            recommendations.append({
                'type': 'outlier_flag',
                'summary': f'{own_outlier["name"]} deviates notably from the platform average.',
                'basis': own_outlier['explanation'],
                'source': 'intelligence_analytics_engine.outliers.detect_company_outliers',
            })

    evidence = evidence_quality_distribution(company=profile)
    if not evidence['available']:
        recommendations.append({
            'type': 'evidence_gap',
            'summary': f'No Evidence Memory records exist yet for {profile.company.name if profile.company_id else profile}.',
            'basis': 'evidence_memory.EvidenceMemory has zero rows scoped to this company.',
            'source': 'intelligence_analytics_engine.evidence_distribution.evidence_quality_distribution',
            'ai_agent_workbench_suggestion': _suggest_agent('What information is missing from these documents?'),
        })
    elif evidence['mean'] < 60:
        recommendations.append({
            'type': 'evidence_quality',
            'summary': f'Existing evidence for this company has below-average confidence ({evidence["mean"]:.0f}/100 mean).',
            'basis': f'{evidence["count"]} evidence record(s), mean confidence {evidence["mean"]:.1f}, std {evidence["std"]:.1f}.',
            'source': 'intelligence_analytics_engine.evidence_distribution.evidence_quality_distribution',
            'ai_agent_workbench_suggestion': _suggest_agent('What is actually verified?'),
        })

    return {
        'available': True,
        'company_id': company_profile_id,
        'company_name': profile.company.name if profile.company_id else str(profile),
        'recommendation_count': len(recommendations),
        'recommendations': recommendations,
    }


def _suggest_agent(question):
    """
    Reuses the AI Agent Workbench's own recommend_agent_for_task() exactly —
    no second, parallel agent-recommendation implementation. Never runs
    anything; matches the Workbench's own "recommend only, confirm before
    running" contract.
    """
    from ai_agent_workbench.services.recommender import recommend_agent_for_task

    result = recommend_agent_for_task(question)
    return {
        'suggested_question': question,
        'recommended_agent': result['agent_name'],
        'why': result['why'],
        'workbench_url': f'/ai-agents/workbench/?ask={question}',
    }
