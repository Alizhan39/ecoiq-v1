"""
plotly_visual_intelligence/services/dashboard_data.py — the aggregation
layer between the dashboard view and every existing intelligence module.
Contains no scoring/evidence/geo/clustering logic of its own — every
number here was already computed by pandas_scoring_engine,
intelligence_analytics_engine, evidence_memory, geo_intelligence or
langgraph_orchestration.

Server-side aggregation, bounded queries (RISK_OPPORTUNITY_LIMIT), no
massive dataset handed to the template — matches the platform-wide cost-
control convention already established in backend_intelligence_engine.
"""
from companies.models import CompanyProfile, CompanyScoreSnapshot

RISK_OPPORTUNITY_LIMIT = 200


def latest_intelligence_snapshot(profile):
    return profile.score_snapshots.filter(intelligence_score__isnull=False).order_by('-date', '-created_at').first()


def resolve_focus_company(company_id=None):
    """
    Explicit company_id, or the most recently intelligence-scored company —
    so the dashboard is never blankly empty on first load, but never
    fabricates a "default" company either (falls back to None honestly if
    literally no company has ever been scored).
    """
    if company_id:
        profile = CompanyProfile.objects.filter(pk=company_id).select_related('company').first()
        if profile:
            return profile
    latest_snapshot = CompanyScoreSnapshot.objects.filter(intelligence_score__isnull=False).order_by('-date', '-created_at').first()
    return latest_snapshot.profile if latest_snapshot else None


def resolve_focus_orchestration_run(run_id=None):
    from langgraph_orchestration.models import OrchestrationRun

    if run_id:
        run = OrchestrationRun.objects.filter(pk=run_id).first()
        if run:
            return run
    return OrchestrationRun.objects.exclude(status='running').order_by('-created_at').first()


def build_kpi_cards(focus_profile):
    """
    Section 1 — Intelligence Overview KPI cards. Every value is either a
    real number from the focus company's latest snapshot, or None — the
    template renders "Not yet measured" for None, never a fabricated 0/50.
    """
    from backend_intelligence_engine.models import BackgroundTaskRun

    snapshot = latest_intelligence_snapshot(focus_profile) if focus_profile else None
    active_tasks = BackgroundTaskRun.objects.filter(status__in=('queued', 'running')).count()

    def _card(label, value, unit, link=None):
        return {'label': label, 'value': value, 'unit': unit, 'available': value is not None, 'link': link}

    return [
        _card('EcoIQ Intelligence Score', snapshot.intelligence_score if snapshot else None, '/100'),
        _card('Climate Risk', snapshot.climate_risk_score if snapshot else None, '/100'),
        _card('Investment Opportunity', snapshot.investment_opportunity_score if snapshot else None, '/100'),
        _card('Modernisation Priority', snapshot.modernisation_priority_score if snapshot else None, '/100'),
        _card('Evidence Confidence', snapshot.intelligence_confidence if snapshot else None, '%'),
        _card('Active Intelligence Tasks', active_tasks, '', '/admin/backend_intelligence_engine/backgroundtaskrun/'),
    ]


def build_risk_opportunity_rows():
    """
    Section 3 data. One row per company using its LATEST intelligence
    snapshot — a single bounded query (RISK_OPPORTUNITY_LIMIT), not a
    per-company round trip.
    """
    from intelligence_analytics_engine.services.outliers import detect_company_outliers

    snapshots = list(
        CompanyScoreSnapshot.objects.filter(intelligence_score__isnull=False)
        .select_related('profile__company').order_by('profile_id', '-date', '-created_at'),
    )
    seen_profiles, latest_per_company = set(), []
    for snap in snapshots:
        if snap.profile_id in seen_profiles:
            continue
        seen_profiles.add(snap.profile_id)
        latest_per_company.append(snap)
        if len(latest_per_company) >= RISK_OPPORTUNITY_LIMIT:
            break

    outlier_result = detect_company_outliers()
    outlier_ids = {o['id'] for o in outlier_result['outliers']} if outlier_result['available'] else set()

    return [
        {
            'company_id': snap.profile_id,
            'name': snap.profile.company.name if snap.profile.company_id else f'Profile #{snap.profile_id}',
            'climate_risk_score': snap.climate_risk_score,
            'investment_opportunity_score': snap.investment_opportunity_score,
            'modernisation_priority_score': snap.modernisation_priority_score,
            'intelligence_confidence': snap.intelligence_confidence,
            'is_outlier': snap.profile_id in outlier_ids,
        }
        for snap in latest_per_company
    ]


def build_similarity_context(focus_profile):
    if not focus_profile:
        return None
    from intelligence_analytics_engine.services.similarity import find_similar_companies

    return find_similar_companies(focus_profile.pk, top_n=5)


def build_cluster_context():
    from intelligence_analytics_engine.services.clustering import climate_risk_clusters

    return climate_risk_clusters(n_clusters=3)


def build_evidence_context(focus_profile):
    from intelligence_analytics_engine.services.evidence_distribution import evidence_quality_distribution
    from evidence_memory.models import EvidenceMemory

    scoped = evidence_quality_distribution(company=focus_profile) if focus_profile else None
    platform_wide = evidence_quality_distribution()
    total_memory_rows = EvidenceMemory.objects.count()
    companies_with_memory = EvidenceMemory.objects.exclude(company__isnull=True).values('company_id').distinct().count()
    total_companies = CompanyProfile.objects.filter(status__in=('public', 'verified')).count()

    return {
        'scoped': scoped, 'platform_wide': platform_wide,
        'total_memory_rows': total_memory_rows,
        'coverage_pct': round(100 * companies_with_memory / total_companies, 1) if total_companies else None,
        'companies_with_memory': companies_with_memory, 'total_companies': total_companies,
    }


def build_recommendations_context(focus_profile):
    if not focus_profile:
        return None
    from intelligence_analytics_engine.services.recommendations import recommend_for_company

    return recommend_for_company(focus_profile.pk)
