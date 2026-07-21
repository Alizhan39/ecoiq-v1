"""
company_intelligence/review_views.py — feat/evidence-review-workbench
(PR 12): the Evidence Review Workbench. Staff-only throughout — this is a
governance/verification layer, never a public page. Every view here
ORCHESTRATES only; all state mutation and queue/trace logic lives in
services/evidence_review.py and services/review_trace.py.
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from company_intelligence.models import CompanyKPIEvidenceLink, EvidenceReviewAction
from company_intelligence.services import evidence_review
from company_intelligence.services.review_trace import explain_review_decision
from core.esg_principles_data import PRINCIPLE_CATEGORIES


def _criteria_from_request(request):
    kpi_raw = request.GET.get('kpi', '')
    tier_raw = request.GET.get('tier', '')
    states_raw = request.GET.getlist('state')
    valid_states = {s for s, _ in CompanyKPIEvidenceLink.REVIEW_STATE_CHOICES}
    return {
        'review_states': [s for s in states_raw if s in valid_states] or None,
        'company_slug': request.GET.get('company', '').strip(),
        'kpi_id': int(kpi_raw) if kpi_raw.isdigit() else None,
        'kpi_category': request.GET.get('category', '').strip(),
        'relationship': request.GET.get('relationship', '').strip(),
        'min_source_tier': int(tier_raw) if tier_raw.isdigit() else None,
        'date_from': request.GET.get('date_from', '').strip() or None,
        'date_to': request.GET.get('date_to', '').strip() or None,
    }


@staff_member_required(login_url='/login/')
def review_queue_view(request):
    """
    /companies/review/ — the primary Evidence Review Workbench queue.
    Default shows proposed/needs_more_evidence/disputed items; a reviewer
    can widen the state filter to also see recently confirmed/rejected
    items for context. Sorted by transparent, documented priority
    components — never an opaque score.
    """
    from ai_observatory.services import recorder

    criteria = _criteria_from_request(request)

    session = recorder.start_session(kind='evidence_review_workbench', user=request.user)
    with recorder.record_stage(session, 'queue_opened', 'Review Queue Opened', category='deterministic') as info:
        rows = evidence_review.pending_review_queue(criteria)
        info['items_processed'] = len(rows)
        info['metadata'] = {'criteria': {k: v for k, v in criteria.items() if v}}
    recorder.finish_session(session, evidence_retrieved=len(rows), final_recommendation_status='recorded')

    analytics = evidence_review.review_analytics()

    return render(request, 'company_intelligence/review_queue.html', {
        'rows': rows,
        'analytics': analytics,
        'criteria': criteria,
        'review_state_choices': CompanyKPIEvidenceLink.REVIEW_STATE_CHOICES,
        'relationship_choices': CompanyKPIEvidenceLink.RELATIONSHIP_CHOICES,
        'kpi_categories': PRINCIPLE_CATEGORIES,
    })


@staff_member_required(login_url='/login/')
def review_detail_view(request, link_id):
    """
    /companies/review/<link_id>/ — the dedicated review page. GET shows
    full evidence + context + source provenance + KPI context + history;
    POST records exactly one explicit reviewer decision. No action ever
    auto-confirms — `action` must be one of evidence_review.ACTION_TRANSITIONS'
    keys, all typed in by a human via the decision form.
    """
    from ai_observatory.services import recorder

    link = get_object_or_404(CompanyKPIEvidenceLink.objects.select_related(
        'assessment', 'assessment__company', 'assessment__company__company', 'evidence',
    ), pk=link_id)

    if request.method == 'POST':
        action = request.POST.get('action', '')
        reason = request.POST.get('reason', '').strip()
        if action not in evidence_review.ACTION_TRANSITIONS:
            messages.error(request, 'Invalid review action.')
            return redirect('companies:review_detail', link_id=link_id)

        session = recorder.start_session(kind='evidence_review_workbench', company=link.assessment.company, user=request.user)
        with recorder.record_stage(session, 'review_decision', f'Review Decision: {action}', category='governance') as info:
            evidence_review.apply_review_decision(link, action, request.user, reason=reason)
            info['metadata'] = {'action': action, 'kpi_id': link.assessment.kpi_id}
        recorder.finish_session(session, final_recommendation_status='recorded', human_review_completed=True)

        messages.success(request, f'Recorded "{dict(EvidenceReviewAction.ACTION_CHOICES)[action]}" for this evidence link.')
        return redirect('companies:review_detail', link_id=link_id)

    context = {
        'link': link,
        'company': link.assessment.company,
        'evidence_context': evidence_review.evidence_context(link),
        'source_provenance': evidence_review.source_provenance(link),
        'kpi_context': evidence_review.kpi_context(link),
        'evidence_quality': evidence_review.evidence_quality.evidence_quality_for_memory(link.evidence),
        'evidence_freshness': evidence_review.evidence_freshness_info(link),
        'duplicates': evidence_review.duplicate_links_for(link),
        'history': evidence_review.review_history(link),
        'proposed_by': evidence_review._proposed_by(link),
        'appearance': evidence_review.appearance_context(link),
        'action_choices': EvidenceReviewAction.ACTION_CHOICES,
    }
    return render(request, 'company_intelligence/review_detail.html', context)


@staff_member_required(login_url='/login/')
def explain_review_decision_view(request, link_id):
    """/companies/review/<link_id>/explain/ — deterministic Source ->
    Document -> Evidence Chunk -> Candidate Matcher -> Proposed KPI ->
    Human Reviewer -> Decision -> Assessment Impact -> Discovery Impact
    trace."""
    link = get_object_or_404(CompanyKPIEvidenceLink.objects.select_related(
        'assessment', 'assessment__company', 'assessment__company__company', 'evidence',
    ), pk=link_id)
    trace = explain_review_decision(link)
    return render(request, 'company_intelligence/review_explain.html', {'link': link, 'trace': trace})


@staff_member_required(login_url='/login/')
def review_bulk_action_view(request):
    """
    POST-only, staff-only. Deliberately conservative per the brief: the
    ONLY bulk action offered is marking selected items NEEDS_MORE_EVIDENCE
    — never bulk-confirm (supports or conflicts), which would make human
    governance meaningless at scale. Each affected link still gets its own
    real, attributed EvidenceReviewAction row — a bulk action is a batch of
    individual decisions, not one anonymous mass mutation.
    """
    if request.method != 'POST':
        raise Http404()

    link_ids = request.POST.getlist('link_id')
    reason = request.POST.get('reason', '').strip()
    links = CompanyKPIEvidenceLink.objects.filter(pk__in=link_ids)

    count = 0
    for link in links:
        evidence_review.apply_review_decision(link, 'needs_more_evidence', request.user, reason=reason or 'Bulk-marked for additional evidence.')
        count += 1

    messages.success(request, f'Marked {count} item(s) as Needs More Evidence.')
    return redirect('companies:review_queue')
