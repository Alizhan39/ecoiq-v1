"""
digital_twin/views.py — minimal UI + API views for the 13 required screens.

Every page here is explicit about what it's showing: OBSERVED data (a
stored field value), CALCULATED data (a deterministic service's output),
an ASSUMPTION (an explicit input the simulator was given), an AI-GENERATED
SUGGESTION (a LossDetection candidate, a council position, or a scenario
before human approval), MISSING DATA (a TwinDataGap), or an APPROVED
HUMAN DECISION (a HumanDecision row). Templates render these as visually
distinct classes; no template here ever renders a suggestion with the same
styling as an approved decision.
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from digital_twin import models as m
from digital_twin.services import baseline as baseline_service
from digital_twin.services import scenario_simulation


def asset_list(request):
    assets = m.IndustrialAsset.objects.select_related('asset_type', 'company').order_by('name')
    return render(request, 'digital_twin/asset_list.html', {'assets': assets})


def asset_detail(request, asset_id):
    asset = get_object_or_404(m.IndustrialAsset, pk=asset_id)
    twins = asset.twins.order_by('-version')
    return render(request, 'digital_twin/asset_detail.html', {'asset': asset, 'twins': twins})


def twin_baseline(request, twin_id):
    twin = get_object_or_404(m.DigitalTwin, pk=twin_id)
    result = baseline_service.compute_baseline(twin)
    return render(request, 'digital_twin/twin_baseline.html', {'twin': twin, 'result': result})


def twin_process_map(request, twin_id):
    twin = get_object_or_404(m.DigitalTwin, pk=twin_id)
    nodes = twin.process_nodes.select_related('component').order_by('sequence_order')
    edges = twin.process_edges.select_related('source_node', 'target_node')
    components = twin.components.filter(parent_component__isnull=True).order_by('name')
    return render(request, 'digital_twin/twin_process_map.html', {
        'twin': twin, 'nodes': nodes, 'edges': edges, 'components': components,
    })


def twin_data_gaps(request, twin_id):
    twin = get_object_or_404(m.DigitalTwin, pk=twin_id)
    gaps = twin.data_gaps.order_by('-severity', 'affected_area')
    return render(request, 'digital_twin/twin_data_gaps.html', {'twin': twin, 'gaps': gaps})


def twin_losses(request, twin_id):
    twin = get_object_or_404(m.DigitalTwin, pk=twin_id)
    losses = twin.loss_detections.order_by('-estimated_annual_impact')
    return render(request, 'digital_twin/twin_losses.html', {'twin': twin, 'losses': losses})


def twin_scenarios(request, twin_id):
    twin = get_object_or_404(m.DigitalTwin, pk=twin_id)
    scenarios = twin.scenarios.select_related('intervention').order_by('scenario_type')
    return render(request, 'digital_twin/twin_scenarios.html', {'twin': twin, 'scenarios': scenarios})


def scenario_compare(request):
    scenario_ids = request.GET.getlist('scenario')
    scenarios = m.ModernisationScenario.objects.select_related('intervention').filter(pk__in=scenario_ids)
    comparisons = [scenario_simulation.simulate_scenario(s) for s in scenarios]
    return render(request, 'digital_twin/scenario_compare.html', {'scenarios': scenarios, 'comparisons': comparisons})


def scenario_detail(request, scenario_id):
    scenario = get_object_or_404(m.ModernisationScenario, pk=scenario_id)
    simulation = scenario_simulation.simulate_scenario(scenario)
    return render(request, 'digital_twin/scenario_detail.html', {'scenario': scenario, 'simulation': simulation})


def scenario_stewardship(request, scenario_id):
    scenario = get_object_or_404(m.ModernisationScenario, pk=scenario_id)
    assessments = scenario.stewardship_assessments.select_related('kpi', 'kpi__principle')
    return render(request, 'digital_twin/scenario_stewardship.html', {'scenario': scenario, 'assessments': assessments})


def scenario_council(request, scenario_id):
    from digital_twin.services import council as council_service

    scenario = get_object_or_404(m.ModernisationScenario, pk=scenario_id)
    council_run = council_service.get_council_run(scenario)
    tasks = council_run.tasks.all() if council_run else []
    decision_record = getattr(council_run, 'decision', None) if council_run else None
    return render(request, 'digital_twin/scenario_council.html', {
        'scenario': scenario, 'council_run': council_run, 'tasks': tasks, 'decision_record': decision_record,
    })


@login_required
def scenario_approve(request, scenario_id):
    scenario = get_object_or_404(m.ModernisationScenario, pk=scenario_id)
    decisions = scenario.human_decisions.order_by('-decided_at')
    return render(request, 'digital_twin/scenario_approve.html', {'scenario': scenario, 'decisions': decisions})


@login_required
def scenario_promote(request, scenario_id):
    scenario = get_object_or_404(m.ModernisationScenario, pk=scenario_id)
    decision = scenario.human_decisions.filter(human_approved=True).order_by('-decided_at').first()
    return render(request, 'digital_twin/scenario_promote.html', {'scenario': scenario, 'decision': decision})


def scenario_implementation(request, scenario_id):
    scenario = get_object_or_404(m.ModernisationScenario, pk=scenario_id)
    actions = scenario.implementation_actions.prefetch_related('measured_outcomes')
    return render(request, 'digital_twin/scenario_implementation.html', {'scenario': scenario, 'actions': actions})


# ── API ────────────────────────────────────────────────────────────────────

def api_asset_list(request):
    assets = m.IndustrialAsset.objects.select_related('asset_type').order_by('name')
    return JsonResponse({'assets': [
        {'id': a.pk, 'name': a.name, 'asset_type': a.asset_type.code, 'country': a.country,
         'lifecycle_stage': a.lifecycle_stage, 'operational_status': a.operational_status}
        for a in assets
    ]})


def api_twin_baseline(request, twin_id):
    twin = get_object_or_404(m.DigitalTwin, pk=twin_id)
    return JsonResponse(baseline_service.compute_baseline(twin))


def api_scenario_simulation(request, scenario_id):
    scenario = get_object_or_404(m.ModernisationScenario, pk=scenario_id)
    return JsonResponse(scenario_simulation.simulate_scenario(scenario))
