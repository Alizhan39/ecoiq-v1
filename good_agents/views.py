"""
good_agents/views.py — minimal read views over the Good Agents pipeline.
No dead ends: every opportunity links through to its real activations,
red-team review, opportunity-cost assessment, actions, capital decision and
impact receipt, all of which are real rows created by the pipeline in
services/pipeline.py — nothing here is a static mockup.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from good_agents.models import AvailableResource, GoodDiscoveryRun, GoodOpportunity, Need, SignalProvider
from good_agents.services import morning_brief as morning_brief_service


def opportunity_list(request):
    opportunities = GoodOpportunity.objects.select_related('project', 'geography').order_by('-created_at')
    status = request.GET.get('status', '')
    if status:
        opportunities = opportunities.filter(status=status)
    return render(request, 'good_agents/opportunity_list.html', {
        'opportunities': opportunities,
        'status_choices': GoodOpportunity.STATUS_CHOICES,
        'active_status': status,
    })


def opportunity_detail(request, pk):
    opportunity = get_object_or_404(
        GoodOpportunity.objects.select_related('project', 'geography', 'operational_loss', 'discovery_run'),
        pk=pk,
    )
    activations = opportunity.agent_activations.select_related('agent').all()
    actions = opportunity.actions.all()
    cost_assessment = getattr(opportunity, 'opportunity_cost_assessment', None)
    red_team_review = getattr(opportunity, 'red_team_review', None)
    impact_receipt = getattr(opportunity, 'impact_receipt', None)
    decisions = []
    if opportunity.operational_loss_id:
        decisions = [
            d for loss_option in opportunity.operational_loss.interventions.all()
            for d in loss_option.allocation_decisions.all()
        ]
    return render(request, 'good_agents/opportunity_detail.html', {
        'opportunity': opportunity,
        'activations': activations,
        'actions': actions,
        'cost_assessment': cost_assessment,
        'red_team_review': red_team_review,
        'impact_receipt': impact_receipt,
        'decisions': decisions,
    })


def morning_brief(request):
    """PR2 Phase 13 + PR3 Phase 16-18 — assembled entirely from stored run/opportunity data, never fabricated numbers."""
    latest_run = GoodDiscoveryRun.objects.filter(status='completed').order_by('-created_at').first()
    top_opportunities = []
    awaiting_review = []
    top_3_actions = []
    if latest_run is not None:
        top_opportunities = list(
            latest_run.opportunities.order_by('-urgency', '-confidence')[:5]
        )
        awaiting_review = list(
            GoodOpportunity.objects.filter(status__in=['potential', 'qualified']).order_by('-urgency')[:10]
        )
        top_3_actions = morning_brief_service.top_3_actions(list(latest_run.opportunities.all()))
    return render(request, 'good_agents/morning_brief.html', {
        'latest_run': latest_run,
        'top_opportunities': top_opportunities,
        'awaiting_review': awaiting_review,
        'top_3_actions': top_3_actions,
    })


def good_map_api(request):
    """
    PR3 Phase 21 — backend/data support for a future /good/map. Read-only
    JSON; the map UI itself is explicitly out of scope for this PR. Never
    exposes precise coordinates or individual identifiers — only the
    region-level fields already on each model.
    """
    theme = request.GET.get('theme', '')
    status = request.GET.get('status', '')
    zero_capital = request.GET.get('zero_capital', '')
    min_confidence = request.GET.get('min_confidence', '')

    opportunities = GoodOpportunity.objects.select_related('geography')
    if theme:
        opportunities = opportunities.filter(theme=theme)
    if status:
        opportunities = opportunities.filter(status=status)
    if zero_capital:
        opportunities = opportunities.filter(zero_capital_possible=(zero_capital == 'true'))
    if min_confidence:
        opportunities = opportunities.filter(confidence__gte=float(min_confidence))

    needs = Need.objects.select_related('geography').filter(status='open')
    resources = AvailableResource.objects.select_related('geography').filter(status='active')

    return JsonResponse({
        'opportunities': [
            {
                'id': o.pk, 'title': o.title, 'theme': o.theme, 'status': o.status,
                'region': o.region, 'country': o.geography.name if o.geography_id else '',
                'urgency': o.urgency, 'confidence': o.confidence,
                'zero_capital_possible': o.zero_capital_possible, 'capital_required_usd': o.capital_required_usd,
            }
            for o in opportunities[:200]
        ],
        'needs': [
            {
                'id': n.pk, 'title': n.title, 'need_type': n.need_type, 'status': n.status,
                'region': n.region, 'country': n.geography.name if n.geography_id else '', 'urgency': n.urgency,
            }
            for n in needs[:200]
        ],
        'resources': [
            {
                'id': r.pk, 'title': r.title, 'resource_type': r.resource_type, 'availability': r.availability,
                'region': r.region, 'country': r.geography.name if r.geography_id else '', 'confidence': r.confidence,
            }
            for r in resources[:200]
        ],
    })


def observatory_health_api(request):
    """PR3 Phase 31 — operational visibility over SignalProvider health. No silent ingestion failures."""
    providers = SignalProvider.objects.all()
    return JsonResponse({
        'providers': [
            {
                'slug': p.slug, 'name': p.name, 'status': p.status, 'trust_tier': p.trust_tier,
                'last_refresh_at': p.last_refresh_at.isoformat() if p.last_refresh_at else None,
                'last_failure_reason': p.last_failure_reason, 'is_stale': p.is_stale(),
            }
            for p in providers
        ],
        'active_count': providers.filter(status='active').count(),
        'failed_count': providers.filter(status='failed').count(),
        'stale_count': sum(1 for p in providers if p.is_stale()),
    })
