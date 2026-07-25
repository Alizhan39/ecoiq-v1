"""
outreach_readiness/views.py — PR12: every mutation staff-only + POST-only.
No view in this file can perform a real external send — that transport
call does not exist anywhere in this app (see services/dry_run.py's own
docstring).
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render

from capability_graph.models import ROUTE_TYPE_CHOICES
from good_agents.models import GoodOpportunity
from outreach_readiness.models import (
    RECIPIENT_ROLE_CHOICES, SENSITIVITY_CATEGORY_CHOICES, SUITABILITY_STATE_CHOICES, OutreachMessageVersion,
)
from outreach_readiness.services import (
    assessment as assessment_service, dry_run as dry_run_service, founder_review as founder_review_service,
    message as message_service, risk as risk_service, route as route_service,
)
from outreach_readiness.services.candidate_review import candidate_review_list as build_candidate_review_list
from outreach_readiness.services.duplicate_check import prior_outreach_history
from outreach_readiness.services.readiness import READINESS_LABELS, compute_readiness_state
from outreach_readiness.services.roles import role_summary

SUITABILITY_QUESTIONS = [
    ('evidence_credible', 'Is the underlying problem supported by credible evidence?'),
    ('response_genuinely_useful', 'Is a specific external response genuinely useful?'),
    ('within_recipient_remit', "Is the requested action within the organisation's real remit?"),
    ('route_available', 'Is a correct public contact route available?'),
    ('ask_small_and_proportionate', 'Is the ask small and proportionate?'),
    ('plausibly_answerable', 'Could the organisation reasonably answer?'),
    ('plausible_next_governed_step', 'Is there a plausible next governed step?'),
    ('risk_of_appearing_inappropriate', 'Risk of appearing spammy, irrelevant, misleading, exploitative, or insensitive?'),
    ('more_value_than_public_info_alone', 'Would contacting them create more value than simply using their published information?'),
]

RISK_CHECKLIST_LABELS = [
    ('correct_organisation', 'Correct organisation?'), ('correct_institutional_role', 'Correct institutional role?'),
    ('correct_public_route', 'Correct public route?'), ('evidence_current', 'Evidence current?'),
    ('request_answerable', 'Request answerable?'), ('request_proportionate', 'Request proportionate?'),
    ('no_sensitive_personal_data', 'No sensitive personal data?'), ('no_unsupported_urgency', 'No unsupported urgency?'),
    ('no_implied_partnership', 'No implied partnership?'), ('no_implied_authority', 'No implied authority?'),
    ('no_financial_promise', 'No financial promise?'), ('no_legal_or_religious_claim', 'No legal/religious claim?'),
    ('no_exploitative_framing', 'No exploitative framing?'), ('no_duplicate_prior_outreach', 'No duplicate prior outreach?'),
    ('no_do_not_contact_status', 'No do-not-contact status?'),
]


@staff_member_required(login_url='/login/')
def candidate_review_list(request):
    """Phase 1 — compares a bounded set of real opportunities side by side. Never a mysterious aggregate score."""
    opportunities = GoodOpportunity.objects.exclude(title__startswith='[CONTROLLED TEST]').order_by('-urgency')[:30]
    return render(request, 'outreach_readiness/candidate_review_list.html', {
        'candidates': build_candidate_review_list(opportunities),
    })


@staff_member_required(login_url='/login/')
def assessment_detail(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    a = assessment_service.get_or_create_assessment(opportunity)
    latest_version = a.message_versions.order_by('-version_number').first()
    latest_dry_run = latest_version.dry_runs.order_by('-run_at').first() if latest_version else None
    latest_risk_review = getattr(latest_version, 'risk_review', None) if latest_version else None

    suitability_questions = [
        {'field': field, 'label': label, 'value': getattr(a, field)} for field, label in SUITABILITY_QUESTIONS
    ]
    risk_checklist_items = [
        {'field': field, 'label': label, 'checked': getattr(latest_risk_review, field) if latest_risk_review else False}
        for field, label in RISK_CHECKLIST_LABELS
    ]

    return render(request, 'outreach_readiness/assessment_detail.html', {
        'opportunity': opportunity,
        'assessment': a,
        'suitability_questions': suitability_questions,
        'suitability_state_choices': SUITABILITY_STATE_CHOICES,
        'recipient_role_choices': RECIPIENT_ROLE_CHOICES,
        'sensitivity_category_choices': SENSITIVITY_CATEGORY_CHOICES,
        'route_type_choices': ROUTE_TYPE_CHOICES,
        'active_route': route_service.active_route(a),
        'routes': a.routes.all(),
        'message_versions': a.message_versions.all(),
        'latest_version': latest_version,
        'latest_dry_run': latest_dry_run,
        'latest_risk_review': latest_risk_review,
        'risk_checklist_items': risk_checklist_items,
        'readiness_state': compute_readiness_state(a),
        'readiness_label': READINESS_LABELS[compute_readiness_state(a)],
        'role_summary': role_summary(a),
        'prior_history': prior_outreach_history(a),
    })


@staff_member_required(login_url='/login/')
def record_suitability_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        a = assessment_service.get_or_create_assessment(opportunity)
        bool_fields = [
            'evidence_credible', 'response_genuinely_useful', 'within_recipient_remit', 'route_available',
            'ask_small_and_proportionate', 'plausibly_answerable', 'plausible_next_governed_step',
            'risk_of_appearing_inappropriate', 'more_value_than_public_info_alone',
        ]
        answers = {}
        for field in bool_fields:
            raw = request.POST.get(field, '')
            answers[field] = {'true': True, 'false': False}.get(raw, None)
        assessment_service.record_suitability_review(a, actor=request.user, answers=answers, notes=request.POST.get('notes', ''))
        new_state = request.POST.get('suitability_state', '')
        if new_state:
            assessment_service.set_suitability_state(a, new_state, actor=request.user, rationale=request.POST.get('state_rationale', ''))
    return redirect('outreach_readiness:assessment_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def recipient_responsibility_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        a = assessment_service.get_or_create_assessment(opportunity)
        assessment_service.record_recipient_responsibility_test(
            a, actor=request.user, recipient_role=request.POST.get('recipient_role', ''),
            jurisdiction=request.POST.get('jurisdiction', ''),
            remit_confirmed=request.POST.get('remit_confirmed') == 'true',
            remit_rationale=request.POST.get('remit_rationale', ''),
            geographic_relevance_confirmed=request.POST.get('geographic_relevance_confirmed') == 'true',
            capability_evidence_reference=request.POST.get('capability_evidence_reference', ''),
            limitations=request.POST.get('limitations', ''),
            identity_confirmed=request.POST.get('identity_confirmed') == 'true',
        )
    return redirect('outreach_readiness:assessment_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def sensitivity_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        a = assessment_service.get_or_create_assessment(opportunity)
        categories = request.POST.getlist('categories')
        assessment_service.record_sensitivity_review(
            a, actor=request.user, categories=categories, notes=request.POST.get('notes', ''),
            outreach_inappropriate=request.POST.get('outreach_inappropriate') == 'true',
        )
    return redirect('outreach_readiness:assessment_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def minimum_viable_ask_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        a = assessment_service.get_or_create_assessment(opportunity)
        assessment_service.record_minimum_viable_ask(
            a, actor=request.user, ask=request.POST.get('ask', ''), value_offered=request.POST.get('value_offered', ''),
        )
    return redirect('outreach_readiness:assessment_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def add_route_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        a = assessment_service.get_or_create_assessment(opportunity)
        try:
            route_service.record_route(
                a, actor=request.user,
                contact_page_or_institutional_email=request.POST.get('contact_page_or_institutional_email', ''),
                route_type=request.POST.get('route_type', 'other'), source_reference=request.POST.get('source_reference', ''),
                official_website=request.POST.get('official_website', ''), route_purpose=request.POST.get('route_purpose', ''),
                jurisdiction=request.POST.get('jurisdiction', ''),
                accepts_this_request_type=request.POST.get('accepts_this_request_type') == 'true',
                published_restrictions=request.POST.get('published_restrictions', ''),
            )
        except route_service.RouteNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('outreach_readiness:assessment_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def create_message_version_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        a = assessment_service.get_or_create_assessment(opportunity)
        fact_points = [line.strip() for line in request.POST.get('fact_points', '').splitlines() if line.strip()]
        inference_points = [line.strip() for line in request.POST.get('inference_points', '').splitlines() if line.strip()]
        unknowns = [line.strip() for line in request.POST.get('unknowns', '').splitlines() if line.strip()]
        try:
            message_service.create_message_version(
                a, actor=request.user, subject=request.POST.get('subject', ''), fact_points=fact_points,
                inference_points=inference_points, the_request=request.POST.get('the_request', ''), unknowns=unknowns,
                body_text=request.POST.get('body_text', ''), sender_name=request.POST.get('sender_name', ''),
                sender_role=request.POST.get('sender_role', ''), sender_organisation=request.POST.get('sender_organisation', ''),
                reply_to=request.POST.get('reply_to', ''), value_offered=request.POST.get('value_offered', ''),
                sender_website=request.POST.get('sender_website', ''), signature_block=request.POST.get('signature_block', ''),
                change_summary=request.POST.get('change_summary', ''),
            )
        except message_service.MessageNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('outreach_readiness:assessment_detail', opportunity_pk=opportunity_pk)


@staff_member_required(login_url='/login/')
def mark_reviewed_view(request, version_pk):
    version = get_object_or_404(OutreachMessageVersion, pk=version_pk)
    if request.method == 'POST':
        try:
            message_service.mark_reviewed(version, actor=request.user)
        except message_service.MessageNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('outreach_readiness:assessment_detail', opportunity_pk=version.assessment.opportunity_id)


@staff_member_required(login_url='/login/')
def founder_approve_message_view(request, version_pk):
    version = get_object_or_404(OutreachMessageVersion, pk=version_pk)
    if request.method == 'POST':
        try:
            message_service.founder_approve(version, actor=request.user)
        except message_service.MessageNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('outreach_readiness:assessment_detail', opportunity_pk=version.assessment.opportunity_id)


@staff_member_required(login_url='/login/')
def record_risk_review_view(request, version_pk):
    version = get_object_or_404(OutreachMessageVersion, pk=version_pk)
    if request.method == 'POST':
        from outreach_readiness.models import OutreachRiskReview
        answers = {field: (request.POST.get(field) == 'true') for field in OutreachRiskReview.CHECKLIST_FIELDS}
        risk_service.record_risk_review(version, actor=request.user, answers=answers, notes=request.POST.get('notes', ''))
    return redirect('outreach_readiness:assessment_detail', opportunity_pk=version.assessment.opportunity_id)


@staff_member_required(login_url='/login/')
def run_dry_run_view(request, version_pk):
    version = get_object_or_404(OutreachMessageVersion, pk=version_pk)
    if request.method == 'POST':
        dry_run_service.run_dry_run(version, actor=request.user)
    return redirect('outreach_readiness:assessment_detail', opportunity_pk=version.assessment.opportunity_id)


@staff_member_required(login_url='/login/')
def founder_send_review(request, opportunity_pk):
    """Phase 24 — the one final review surface. Read-only; the decision is recorded via record_founder_decision_view."""
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    a = assessment_service.get_or_create_assessment(opportunity)
    latest_version = a.message_versions.order_by('-version_number').first()
    latest_dry_run = latest_version.dry_runs.order_by('-run_at').first() if latest_version else None
    recommendation, reasons = founder_review_service.compute_recommendation(a)
    return render(request, 'outreach_readiness/founder_send_review.html', {
        'opportunity': opportunity,
        'assessment': a,
        'latest_version': latest_version,
        'latest_dry_run': latest_dry_run,
        'risk_review': getattr(latest_version, 'risk_review', None) if latest_version else None,
        'recommendation': recommendation,
        'recommendation_reasons': reasons,
        'readiness_state': compute_readiness_state(a),
        'role_summary': role_summary(a),
        'prior_history': prior_outreach_history(a),
        'existing_decision': getattr(a, 'founder_decision', None),
    })


@staff_member_required(login_url='/login/')
def record_founder_decision_view(request, opportunity_pk):
    opportunity = get_object_or_404(GoodOpportunity, pk=opportunity_pk)
    if request.method == 'POST':
        a = assessment_service.get_or_create_assessment(opportunity)
        latest_version = a.message_versions.order_by('-version_number').first()
        try:
            founder_review_service.record_decision(
                a, request.POST.get('decision', ''), actor=request.user, message_version=latest_version,
                rationale=request.POST.get('rationale', ''),
            )
        except founder_review_service.FounderReviewNotAllowedError as exc:
            messages.error(request, str(exc))
    return redirect('outreach_readiness:founder_send_review', opportunity_pk=opportunity_pk)
