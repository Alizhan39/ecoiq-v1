from django.db.models import Sum
from django.shortcuts import get_object_or_404, render

from waste_to_value_capital_allocation_engine.models import (
    CapitalAllocationDecision, FundingGap, InterventionOption, OperationalLoss,
    VerifiedCapitalOutcome,
)

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

    return render(request, 'waste_to_value_capital_allocation_engine/decision_detail.html', {
        'decision': decision,
        'funding_gap': funding_gap,
        'route_matches': route_matches,
        'verified_outcome': verified_outcome,
    })
