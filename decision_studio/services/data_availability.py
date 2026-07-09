"""
decision_studio/services/data_availability.py — the up-front honesty gate.
Checked BEFORE any analysis runs, so EcoIQ can say "insufficient evidence"
instead of generating a confident-sounding but unsupported answer. Reads
only existing data (CompanyScoreSnapshot, EvidenceMemory) — computes
nothing new itself.
"""
from evidence_memory.models import EvidenceMemory


def _company_data_summary(profile):
    from plotly_visual_intelligence.services.dashboard_data import latest_intelligence_snapshot

    snapshot = latest_intelligence_snapshot(profile)
    evidence_count = EvidenceMemory.objects.filter(company=profile).count()
    name = profile.company.name if profile.company_id else f'Profile #{profile.pk}'
    gaps = []
    if snapshot is None:
        gaps.append(f'{name}: no EcoIQ Intelligence Score has been computed yet.')
    if evidence_count == 0:
        gaps.append(f'{name}: no evidence memory records exist yet.')
    return {
        'name': name, 'profile_id': profile.pk, 'has_score': snapshot is not None,
        'has_evidence': evidence_count > 0, 'evidence_count': evidence_count, 'gaps': gaps,
    }


def check_data_availability(profiles):
    """
    Returns {'status': 'AVAILABLE'|'PARTIAL'|'INSUFFICIENT'|'UNKNOWN',
    'entity_summaries': [...], 'missing_data': [str, ...]}.
    status is computed from the real fraction of the ACTUALLY-RESOLVED
    company scope (profiles) that has a score + evidence — never assumed,
    and never judged only against explicitly-named entities: a general
    "compare available companies" question resolves a real (bounded)
    company scope with no named entities, and deserves a real availability
    verdict too, not an UNKNOWN default.
    """
    if not profiles:
        # A pure country/sector-only or fully-unscoped question with no
        # company scope at all — company-level availability doesn't apply.
        return {'status': 'UNKNOWN', 'entity_summaries': [], 'missing_data': []}

    summaries = [_company_data_summary(profile) for profile in profiles]
    ready_count = sum(1 for s in summaries if s['has_score'] and s['has_evidence'])
    total = len(summaries)

    if ready_count == total:
        status = 'AVAILABLE'
    elif ready_count == 0:
        status = 'INSUFFICIENT'
    else:
        status = 'PARTIAL'

    missing_data = [gap for s in summaries for gap in s['gaps']]
    return {'status': status, 'entity_summaries': summaries, 'missing_data': missing_data}
