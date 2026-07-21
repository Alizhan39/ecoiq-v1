"""
company_intelligence/services/change_timeline.py — feat/stewardship-
monitor (PR 14): "What changed in EcoIQ's understanding of this company,
and why?" (Section 11). A read-only merge of already-stored records —
DiscoveredSource, SourceDocument, StewardshipChangeEvent,
CompanyKPIEvidenceLink, EvidenceReviewAction, CompanyRefreshRun — never a
second, duplicated history table. Every entry carries real provenance
(the underlying row's own pk) so a reviewer can click through to it.
"""


def company_change_timeline(company_profile, limit=50):
    from company_intelligence.models import CompanyKPIEvidenceLink, CompanyRefreshRun, EvidenceReviewAction, StewardshipChangeEvent
    from harvester.models import SourceDocument

    entries = []

    for ds in company_profile.discovered_sources.all():
        entries.append({
            'timestamp': ds.discovered_at, 'kind': 'source_discovered',
            'label': 'Source Discovered', 'detail': f'{ds.url} ({ds.get_discovery_method_display()})',
        })

    for doc in SourceDocument.objects.filter(company=company_profile):
        entries.append({
            'timestamp': doc.retrieved_at, 'kind': 'document_fetched',
            'label': 'Document Fetched', 'detail': f'{doc.title} ({doc.get_document_type_display()})',
        })

    for event in StewardshipChangeEvent.objects.filter(company=company_profile):
        entries.append({
            'timestamp': event.detected_at, 'kind': event.event_type,
            'label': event.get_event_type_display(), 'detail': event.summary,
        })

    for link in CompanyKPIEvidenceLink.objects.filter(assessment__company=company_profile):
        entries.append({
            'timestamp': link.added_at, 'kind': 'kpi_candidate_proposed',
            'label': 'KPI Candidate Proposed', 'detail': f'KPI #{link.assessment.kpi_id} — {link.get_relationship_display()}',
        })

    for action in EvidenceReviewAction.objects.filter(kpi_evidence_link__assessment__company=company_profile):
        entries.append({
            'timestamp': action.created_at, 'kind': 'review_decision',
            'label': action.get_action_display(),
            'detail': f'{action.previous_review_state} → {action.new_review_state} by {action.reviewer}',
        })

    for run in CompanyRefreshRun.objects.filter(company=company_profile):
        entries.append({
            'timestamp': run.started_at, 'kind': 'refresh_run',
            'label': f'Refresh — {run.get_status_display()}', 'run_id': run.pk,
            'detail': f'{run.sources_checked} source(s) checked, {run.sources_failed} failed, {run.get_triggered_by_display()}',
        })

    entries.sort(key=lambda e: e['timestamp'], reverse=True)
    return entries[:limit]
