"""
public_action_preparation/views.py — PR14: every mutation staff-only +
POST-only. No view here can perform a real external action — the
furthest this app reaches is a founder-recorded PROCEED decision, never
a real submission, referral, application, or contact.
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render

from capability_graph.models import ROUTE_TYPE_CHOICES
from capability_graph.services.organisations import get_or_create_organisation
from good_agents.models import GoodOpportunity
from public_action_preparation.models import (
    ACTION_TYPE_CHOICES, CONTENT_TYPE_CHOICES, EthicsReview, PROCESS_STATUS_CHOICES,
)
from public_action_preparation.services import (
    action_type as action_type_service, content_draft as content_draft_service, ethics_review as ethics_review_service,
    evidence_pack as evidence_pack_service, founder_review as founder_review_service,
    process_verification as process_verification_service, roles as roles_service,
)
from public_action_preparation.services.readiness import READINESS_LABELS, compute_action_readiness

ETHICS_QUESTIONS = [
    ('vulnerability_considered', 'Vulnerability considered?'),
    ('health_or_financial_hardship_considered', 'Health/financial hardship considered?'),
    ('personal_data_risk_checked', 'Personal data risk checked?'),
    ('representation_risk_checked', 'Representation risk checked (no claimed consensus/mandate)?'),
    ('consent_addressed', 'Consent addressed?'),
    ('misrouting_risk_checked', 'Risk of misrouting checked?'),
    ('wasted_public_resources_risk_checked', 'Risk of wasting public resources checked?'),
    ('implied_authority_risk_checked', 'Risk of implied authority checked?'),
]


@staff_member_required(login_url='/login/')
def candidate_comparison(request):
    """Phase 1 — compares real actionable candidates from public_need_discovery side by side."""
    opportunities = GoodOpportunity.objects.filter(
        pilot_candidate_assessment__actionability_state__in=['actionable', 'actionable_needs_review'],
    ).exclude(title__startswith='[CONTROLLED TEST]').select_related('pilot_candidate_assessment').order_by('-urgency')
    rows = []
    for o in opportunities:
        candidate = o.pilot_candidate_assessment
        rows.append({
            'opportunity': o,
            'candidate': candidate,
            'readiness': READINESS_LABELS[compute_action_readiness(o)],
            'action_type': getattr(getattr(o, 'action_type_decision', None), 'action_type', ''),
        })
    return render(request, 'public_action_preparation/candidate_comparison.html', {'rows': rows})


@staff_member_required(login_url='/login/')
def action_prep_detail(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    decision = action_type_service.get_or_create_decision(opportunity)
    process = process_verification_service.get_or_create_process(opportunity)
    ethics = ethics_review_service.get_or_create_review(opportunity)
    recommended_type, recommended_reasons = action_type_service.recommend_action_type(opportunity)
    latest_draft = decision.content_drafts.order_by('-version_number').first()

    return render(request, 'public_action_preparation/action_prep_detail.html', {
        'opportunity': opportunity,
        'candidate': getattr(opportunity, 'pilot_candidate_assessment', None),
        'evidence_pack': evidence_pack_service.build_evidence_pack(opportunity),
        'decision': decision,
        'process': process,
        'ethics': ethics,
        'ethics_questions': [{'field': f, 'label': l, 'value': getattr(ethics, f)} for f, l in ETHICS_QUESTIONS],
        'recommended_type': recommended_type,
        'recommended_reasons': recommended_reasons,
        'action_type_choices': ACTION_TYPE_CHOICES,
        'process_status_choices': PROCESS_STATUS_CHOICES,
        'route_type_choices': ROUTE_TYPE_CHOICES,
        'content_type_choices': CONTENT_TYPE_CHOICES,
        'content_drafts': decision.content_drafts.all(),
        'latest_draft': latest_draft,
        'preview': content_draft_service.render_preview(latest_draft) if latest_draft else None,
        'readiness': compute_action_readiness(opportunity),
        'readiness_label': READINESS_LABELS[compute_action_readiness(opportunity)],
        'role_summary': roles_service.role_summary(opportunity),
    })


@staff_member_required(login_url='/login/')
def record_action_type_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        try:
            action_type_service.record_action_type_decision(
                opportunity, request.POST.get('action_type', ''), actor=request.user,
                rationale=request.POST.get('rationale', ''),
                has_real_beneficiary=request.POST.get('has_real_beneficiary') == 'true',
                beneficiary_basis_notes=request.POST.get('beneficiary_basis_notes', ''),
            )
        except action_type_service.ActionTypeNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('public_action_preparation:action_prep_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def record_process_verification_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        organisation = None
        org_name = request.POST.get('owning_organisation_name', '').strip()
        if org_name:
            organisation = get_or_create_organisation(org_name, jurisdiction=request.POST.get('owning_organisation_jurisdiction', ''))

        def _parse_date(value):
            from datetime import date
            if not value:
                return None
            return date.fromisoformat(value)

        try:
            process_verification_service.record_process_verification(
                opportunity, actor=request.user, process_name=request.POST.get('process_name', ''),
                owning_organisation=organisation, official_url=request.POST.get('official_url', ''),
                route_type=request.POST.get('route_type', ''), opening_date=_parse_date(request.POST.get('opening_date', '')),
                closing_date=_parse_date(request.POST.get('closing_date', '')), eligibility=request.POST.get('eligibility', ''),
                required_information=request.POST.get('required_information', ''),
                submission_format=request.POST.get('submission_format', ''), evidence_allowed=request.POST.get('evidence_allowed', ''),
                acknowledgement_semantics=request.POST.get('acknowledgement_semantics', ''),
                status=request.POST.get('status', 'unknown'), checked_notes=request.POST.get('checked_notes', ''),
            )
        except process_verification_service.ProcessVerificationNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('public_action_preparation:action_prep_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def record_ethics_review_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        answers = {field: (request.POST.get(field) == 'true') for field, _ in ETHICS_QUESTIONS}
        ethics_review_service.record_ethics_review(opportunity, actor=request.user, answers=answers, notes=request.POST.get('notes', ''))
    return redirect('public_action_preparation:action_prep_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def create_content_draft_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        decision = action_type_service.get_or_create_decision(opportunity)
        fact_points = [line.strip() for line in request.POST.get('fact_points', '').splitlines() if line.strip()]
        inference_points = [line.strip() for line in request.POST.get('inference_points', '').splitlines() if line.strip()]
        source_links = [line.strip() for line in request.POST.get('source_links', '').splitlines() if line.strip()]
        required_fields_missing = [line.strip() for line in request.POST.get('required_fields_missing', '').splitlines() if line.strip()]
        try:
            content_draft_service.create_content_draft(
                decision, actor=request.user, content_type=request.POST.get('content_type', ''),
                subject=request.POST.get('subject', ''), fact_points=fact_points, inference_points=inference_points,
                specific_recommendation=request.POST.get('specific_recommendation', ''),
                limitations=request.POST.get('limitations', ''), source_links=source_links,
                body_text=request.POST.get('body_text', ''), required_fields_missing=required_fields_missing,
                change_summary=request.POST.get('change_summary', ''),
            )
        except content_draft_service.ContentDraftNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('public_action_preparation:action_prep_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def mark_draft_reviewed_view(request, draft_pk):
    from public_action_preparation.models import ActionContentDraft
    draft = get_object_or_404(ActionContentDraft, pk=draft_pk)
    if request.method == 'POST':
        try:
            content_draft_service.mark_reviewed(draft, actor=request.user)
        except content_draft_service.ContentDraftNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('public_action_preparation:action_prep_detail', opportunity_pk=draft.decision.opportunity_id)


@staff_member_required(login_url='/login/')
def founder_approve_draft_view(request, draft_pk):
    from public_action_preparation.models import ActionContentDraft
    draft = get_object_or_404(ActionContentDraft, pk=draft_pk)
    if request.method == 'POST':
        try:
            content_draft_service.founder_approve(draft, actor=request.user)
        except content_draft_service.ContentDraftNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('public_action_preparation:action_prep_detail', opportunity_pk=draft.decision.opportunity_id)


@staff_member_required(login_url='/login/')
def add_review_role_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        roles_service.record_role(opportunity, request.user, request.POST.get('role', 'reviewer'), actor=request.user)
    return redirect('public_action_preparation:action_prep_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def founder_action_review(request, opportunity_pk):
    """Phase 17 — the one final review surface. Read-only; the decision is recorded via record_founder_action_decision_view."""
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    decision = action_type_service.get_or_create_decision(opportunity)
    latest_draft = decision.content_drafts.order_by('-version_number').first()
    recommendation, reasons = founder_review_service.compute_recommendation(opportunity)
    return render(request, 'public_action_preparation/founder_action_review.html', {
        'opportunity': opportunity,
        'evidence_pack': evidence_pack_service.build_evidence_pack(opportunity),
        'decision': decision,
        'process': getattr(opportunity, 'verified_official_process', None),
        'ethics': getattr(opportunity, 'ethics_review', None),
        'latest_draft': latest_draft,
        'preview': content_draft_service.render_preview(latest_draft) if latest_draft else None,
        'recommendation': recommendation,
        'recommendation_reasons': reasons,
        'readiness_label': READINESS_LABELS[compute_action_readiness(opportunity)],
        'role_summary': roles_service.role_summary(opportunity),
        'existing_decision': getattr(opportunity, 'founder_action_decision', None),
    })


@staff_member_required(login_url='/login/')
def record_founder_action_decision_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        decision = action_type_service.get_or_create_decision(opportunity)
        latest_draft = decision.content_drafts.order_by('-version_number').first()
        try:
            founder_review_service.record_decision(
                opportunity, request.POST.get('decision', ''), actor=request.user, content_draft=latest_draft,
                rationale=request.POST.get('rationale', ''),
            )
        except founder_review_service.FounderActionReviewNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('public_action_preparation:founder_action_review', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def dossier_view(request, opportunity_pk):
    from public_action_preparation.services.dossier import build_founder_action_dossier
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    return render(request, 'public_action_preparation/dossier.html', {'dossier': build_founder_action_dossier(opportunity)})
