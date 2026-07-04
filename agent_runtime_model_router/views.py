from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404, render

from ai_agent_council.models import CouncilRun
from agent_runtime_model_router.models import AgentRegistryEntry, AgentRun

CORE_PURPOSE = (
    'Connects the 10 operational agent training packs and the governed AI Agent '
    'Council v2 runtime to a reusable execution layer, so a Council position is '
    'produced by a real, auditable pipeline rather than hand-authored fixture data.'
)

PIPELINE_STEPS = [
    'Council Case', 'Agent Selection', 'Training Pack Loader', 'Model Router',
    'Agent Execution', 'Structured Output Validation', 'Safety Assertions',
    'Council Position', 'Cross-Examination', 'Council Decision', 'Human Approval',
    'Institutional Memory',
]

PRESENTATION_HEADLINE = 'From trained agent to governed decision.'
PRESENTATION_PIPELINE = [
    'Training Pack', 'Model Router', 'Agent Run', 'Schema Validation', 'Safety Gate',
    'Council Position', 'Cross-Examination', 'Decision', 'Human Approval', 'Memory',
]

EXECUTION_MODE_NOTE = (
    'Every run explicitly declares its Execution Mode — live, deterministic_test, or '
    'simulated_demo — and a failed live run is never silently relabelled as simulated.'
)

SAFETY_ENGINE_NOTE = (
    'The Safety Assertion Engine blocks or flags output that invents missing data, '
    'presents estimated figures as verified, claims guaranteed savings, or makes '
    'unsupported certification/Shariah/fatwa claims — before it can reach the Council.'
)


def _dashboard_stats():
    return {
        'registered_agents': AgentRegistryEntry.objects.count(),
        'live_enabled_agents': AgentRegistryEntry.objects.filter(enabled=True).count(),
        'deterministic_test_runs': AgentRun.objects.filter(execution_mode_used='deterministic_test').count(),
        'simulated_demo_runs': AgentRun.objects.filter(execution_mode_used='simulated_demo').count(),
        'successful_runs': AgentRun.objects.filter(status='completed').count(),
        'schema_failures': AgentRun.objects.filter(schema_valid=False).count(),
        'safety_blocks': AgentRun.objects.filter(safety_status='blocking').count(),
        'human_reviews_required': AgentRun.objects.filter(
            human_approval_required=True, human_approved__isnull=True,
        ).count(),
        'average_calibrated_confidence': AgentRun.objects.filter(
            calibrated_confidence__isnull=False,
        ).aggregate(avg=Avg('calibrated_confidence'))['avg'],
        'fallback_events': AgentRun.objects.exclude(fallback_chain=[]).count(),
        'estimated_model_cost_usd': AgentRun.objects.filter(
            estimated_cost_usd__isnull=False,
        ).aggregate(total=Sum('estimated_cost_usd'))['total'],
    }


def overview(request):
    demo_case = CouncilRun.objects.filter(
        slug='boiler-house-3-modernisation-runtime-demo',
    ).first()
    recent_runs = AgentRun.objects.select_related('agent').order_by('-created_at')[:10]

    return render(request, 'agent_runtime_model_router/overview.html', {
        'core_purpose': CORE_PURPOSE,
        'pipeline_steps': PIPELINE_STEPS,
        'presentation_headline': PRESENTATION_HEADLINE,
        'presentation_pipeline': PRESENTATION_PIPELINE,
        'execution_mode_note': EXECUTION_MODE_NOTE,
        'safety_engine_note': SAFETY_ENGINE_NOTE,
        'stats': _dashboard_stats(),
        'demo_case': demo_case,
        'recent_runs': recent_runs,
    })


def run_detail(request, run_id):
    agent_run = get_object_or_404(AgentRun.objects.select_related('agent', 'council_case', 'council_position'), pk=run_id)
    return render(request, 'agent_runtime_model_router/run_detail.html', {
        'run': agent_run,
    })


def case_trace(request, case_slug):
    council_run = get_object_or_404(CouncilRun, slug=case_slug)
    decision = getattr(council_run, 'decision', None)
    memory_entry = getattr(decision, 'memory_entry', None) if decision else None

    return render(request, 'agent_runtime_model_router/case_trace.html', {
        'council_run': council_run,
        'agent_runs': council_run.agent_runs.select_related('agent').order_by('created_at'),
        'tasks': council_run.tasks.all(),
        'disagreements': council_run.disagreements.select_related('position_a', 'position_b').all(),
        'cross_examinations': council_run.cross_examinations.all(),
        'decision': decision,
        'memory_entry': memory_entry,
    })
