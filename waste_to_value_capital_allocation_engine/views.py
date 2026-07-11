import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from waste_to_value_capital_allocation_engine.models import (
    CapitalAllocationDecision, FundingGap, InterventionOption, OperationalLoss,
    VerifiedCapitalOutcome,
)
from waste_to_value_capital_allocation_engine.services.capital_guardian_handoff import (
    APPROVED_STATUSES, AmbiguousProjectMatchError, DecisionNotApprovedError,
    find_matching_gold_project, promote_to_capital_guardian,
)

log = logging.getLogger(__name__)

CORE_PURPOSE = (
    'Turns operational waste into finance-ready investment opportunities: quantifying the '
    'financial loss, comparing interventions, calculating investment requirements, identifying '
    'financing gaps, matching capital routes, supporting governed investment decisions, verifying '
    'outcomes through MRV, and feeding verified results into future capital allocation.'
)

LIFECYCLE_STEPS = [
    'Operational Waste', 'Capital at Risk', 'Recoverable Value', 'Intervention Options',
    'Investment Model', 'Funding Gap', 'Funding Match', 'Council Decision', 'Implementation',
    'MRV', 'Verified Value Recovered', 'Capital Reallocation',
]

PRESENTATION_HEADLINE = 'We make wasted value investable.'
PRESENTATION_SUBHEADLINE = (
    'EcoIQ detects hidden losses in the real economy and turns them into finance-ready '
    'investment opportunities.'
)
PRESENTATION_PIPELINE = [
    'Operational Waste', 'Financial Loss Quantified', 'Intervention', 'CAPEX / OPEX / Payback',
    'Funding Gap', 'Investor Match', 'Governed Decision', 'MRV', 'Verified Value', 'Capital Reallocated',
]
SECOND_HEADLINE = 'AI Capital Allocation for the Real Economy'
THIRD_HEADLINE = 'Before value is wasted, EcoIQ identifies where capital can recover it.'

NEXT_POUND_HEADLINE = 'Where should the next £1 of capital go?'

SAFETY_PRINCIPLES = [
    'EcoIQ provides decision-support, not financial advice.',
    'Estimated financial outcomes are not guaranteed.',
    'Funding routes are not funding commitments.',
    'Supplier matches are not endorsements.',
    'Predicted waste reduction is not verified impact.',
    'Public impact requires MRV and approval.',
    'Food redistribution requires food-safety and legal review.',
    'Islamic finance suitability requires qualified review.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Microsoft ecosystem-ready does not mean Microsoft certified or Microsoft partner.',
]

CTA_BUTTONS = [
    {'label': 'Open Waste-to-Value Engine', 'anchor': '#dashboard'},
    {'label': 'View Capital at Risk', 'anchor': '#dashboard'},
    {'label': 'Model Intervention', 'anchor': '#next-pound'},
    {'label': 'Compare Investment Options', 'anchor': '#next-pound'},
    {'label': 'Calculate Funding Gap', 'anchor': '#dashboard'},
    {'label': 'Match Capital Route', 'anchor': '#dashboard'},
    {'label': 'Open Governed Investment Case', 'anchor': '#next-pound'},
    {'label': 'View MRV Status', 'anchor': '#dashboard'},
    {'label': 'View Verified Value Recovered', 'anchor': '#dashboard'},
    {'label': 'Where Should the Next £1 Go?', 'anchor': '#next-pound'},
    {'label': 'Open Meat Cold-Chain Demo', 'url_name': 'ai_agent_council:run_detail', 'url_arg': 'meat-cold-chain-loss-prevention-demo'},
    {'label': 'View Capital Reallocation Signal', 'anchor': '#dashboard'},
]


def _dashboard_stats():
    return {
        'total_capital_at_risk': OperationalLoss.objects.aggregate(
            total=Sum('projected_future_loss'))['total'] or 0,
        'estimated_recoverable_value': InterventionOption.objects.aggregate(
            total=Sum('estimated_value_recovered'))['total'] or 0,
        'operational_losses_detected': OperationalLoss.objects.count(),
        'urgent_interventions': OperationalLoss.objects.filter(urgency_score__gte=70).count(),
        'investment_opportunities': InterventionOption.objects.filter(
            status__in=['recommended', 'approved']).count(),
        'estimated_capex_required': InterventionOption.objects.aggregate(
            total=Sum('capex_estimate'))['total'] or 0,
        'funding_gap': FundingGap.objects.aggregate(total=Sum('remaining_gap'))['total'] or 0,
        'finance_ready_opportunities': InterventionOption.objects.filter(finance_readiness='ready').count(),
        'mrv_verified_outcomes': VerifiedCapitalOutcome.objects.filter(verified_status='verified').count(),
        'verified_value_recovered': VerifiedCapitalOutcome.objects.filter(
            verified_status='verified').aggregate(total=Sum('value_recovered_actual'))['total'] or 0,
        'working_capital_released': 0,  # not yet tracked on a persisted field — honest zero, not fabricated
        'projects_awaiting_approval': CapitalAllocationDecision.objects.filter(approval_status='pending').count(),
    }


def overview(request):
    decisions = CapitalAllocationDecision.objects.select_related('intervention', 'council_case').order_by(
        'ranking', '-created_at',
    )

    return render(request, 'waste_to_value_capital_allocation_engine/overview.html', {
        'core_purpose': CORE_PURPOSE,
        'lifecycle_steps': LIFECYCLE_STEPS,
        'stats': _dashboard_stats(),
        'decisions': decisions,
        'presentation_headline': PRESENTATION_HEADLINE,
        'presentation_subheadline': PRESENTATION_SUBHEADLINE,
        'presentation_pipeline': PRESENTATION_PIPELINE,
        'second_headline': SECOND_HEADLINE,
        'third_headline': THIRD_HEADLINE,
        'next_pound_headline': NEXT_POUND_HEADLINE,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })


def decision_detail(request, decision_id):
    decision = get_object_or_404(
        CapitalAllocationDecision.objects.select_related('intervention', 'intervention__operational_loss', 'council_case'),
        pk=decision_id,
    )
    funding_gap = getattr(decision.intervention, 'funding_gap', None)
    route_matches = funding_gap.route_matches.all() if funding_gap else []
    verified_outcome = getattr(decision, 'verified_outcome', None)

    # Vertical-slice PR 5 — best-effort traceability link back to the real
    # GoldProject/OperationalLoss this decision came from, so the founder's
    # "one continuous workflow" journey can be followed both ways. Never
    # fabricated: silently omitted (not guessed) if no matching project
    # exists or the match is ambiguous — the decision page itself is
    # unaffected either way.
    originating_loss_url = None
    try:
        matched_project = find_matching_gold_project(decision)
        if matched_project is not None:
            originating_loss_url = reverse(
                'capital_guardian:operational_loss_detail',
                kwargs={'slug': matched_project.slug, 'loss_id': decision.intervention.operational_loss_id},
            )
    except AmbiguousProjectMatchError:
        originating_loss_url = None

    return render(request, 'waste_to_value_capital_allocation_engine/decision_detail.html', {
        'decision': decision,
        'funding_gap': funding_gap,
        'route_matches': route_matches,
        'verified_outcome': verified_outcome,
        'council_run': decision.council_case,
        # Human-approved Capital Guardian promotion — button only shown when
        # both true; the real authorization/eligibility check happens again,
        # independently, server-side in promote_confirm()/promote_execute().
        'eligible_for_promotion': decision.approval_status in APPROVED_STATUSES,
        'originating_loss_url': originating_loss_url,
    })


def _decision_or_404(decision_id):
    return get_object_or_404(
        CapitalAllocationDecision.objects.select_related('intervention', 'intervention__operational_loss', 'council_case'),
        pk=decision_id,
    )


@staff_member_required(login_url='/login/')
def promote_confirm(request, decision_id):
    """
    GET-only confirmation screen for promoting a CapitalAllocationDecision
    into Capital Guardian monitoring. Read-only preview — never mutates
    anything. This view's own eligibility/match preview is for display only;
    promote_execute() below independently re-checks everything from scratch
    and is the sole place a ProjectGovernance record can actually be created.
    """
    decision = _decision_or_404(decision_id)
    eligible = decision.approval_status in APPROVED_STATUSES

    matching_project = None
    match_state = 'not_eligible'
    already_governance = None

    if eligible:
        from capital_guardian.models import ProjectGovernance
        try:
            matching_project = find_matching_gold_project(decision)
        except AmbiguousProjectMatchError:
            match_state = 'ambiguous'
        else:
            match_state = 'found' if matching_project else 'none'
            if matching_project is not None:
                already_governance = ProjectGovernance.objects.filter(project=matching_project).first()

    return render(request, 'waste_to_value_capital_allocation_engine/promote_confirm.html', {
        'decision': decision,
        'eligible': eligible,
        'matching_project': matching_project,
        'match_state': match_state,
        'already_governance': already_governance,
    })


@staff_member_required(login_url='/login/')
def promote_execute(request, decision_id):
    """
    POST-only. Independently reloads the decision from the database (never
    trusts anything about eligibility/matching carried over from the
    confirmation page) and calls the existing, unmodified
    promote_to_capital_guardian() service — no promotion logic is
    duplicated here.
    """
    if request.method != 'POST':
        return redirect('waste_to_value_capital_allocation_engine:promote_confirm', decision_id=decision_id)

    decision = _decision_or_404(decision_id)

    try:
        result = promote_to_capital_guardian(decision, actor=request.user)
    except DecisionNotApprovedError:
        messages.error(
            request, 'This decision must receive human approval before it can enter Capital Guardian.',
        )
        return redirect('waste_to_value_capital_allocation_engine:decision_detail', decision_id=decision_id)
    except Exception:
        log.exception(
            'Unexpected failure promoting CapitalAllocationDecision %s to Capital Guardian', decision_id,
        )
        messages.error(
            request, 'Something went wrong starting Capital Guardian monitoring. No changes were made.',
        )
        return redirect('waste_to_value_capital_allocation_engine:decision_detail', decision_id=decision_id)

    if result.status == 'promoted':
        messages.success(request, 'Capital Guardian monitoring has been activated for this project.')
        return redirect('capital_guardian:governance', slug=result.project.slug)

    if result.status == 'already_promoted':
        messages.info(request, 'This decision is already monitored by Capital Guardian.')
        return redirect('capital_guardian:governance', slug=result.project.slug)

    if result.status == 'no_matching_project':
        messages.warning(
            request, 'No matching project record was found. No Capital Guardian record was created.',
        )
        return redirect('waste_to_value_capital_allocation_engine:decision_detail', decision_id=decision_id)

    if result.status == 'ambiguous_project_match':
        messages.warning(
            request,
            'Multiple matching project records were found. Promotion was stopped to prevent incorrect capital monitoring.',
        )
        return redirect('waste_to_value_capital_allocation_engine:decision_detail', decision_id=decision_id)

    # Unrecognised status — fail safe, log loudly, never expose internals to the user.
    log.error('promote_to_capital_guardian returned unrecognised status %r for decision %s', result.status, decision_id)
    messages.error(request, 'Something went wrong starting Capital Guardian monitoring. No changes were made.')
    return redirect('waste_to_value_capital_allocation_engine:decision_detail', decision_id=decision_id)
