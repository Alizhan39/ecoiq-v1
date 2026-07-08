from django.shortcuts import redirect, render
from django.urls import reverse

from agent_runtime_model_router.models import AgentRun
from ai_agent_workbench.services import agent_data, demo_cases, recommender

PIPELINE_STAGES = [
    'Evidence', 'Specialist Agents', 'Disagreement', 'AI Agent Council',
    'Human Approval', 'Verified Outcome',
]

# Council runs seeded elsewhere in the platform, available for /ai-agents/council-demo/
COUNCIL_DEMO_CASES = [
    {'slug': 'boiler-house-3-modernisation-runtime-demo', 'title': 'Boiler House #3 Modernisation'},
    {'slug': 'meat-cold-chain-loss-prevention-demo', 'title': 'Meat Cold-Chain Loss Prevention'},
    {'slug': 'kazakhstan-clean-heat-stewardship-demo', 'title': 'Kazakhstan Clean Heat Stewardship Tour'},
    {'slug': 'freshbridge-foods-advisory-demo', 'title': 'FreshBridge Foods Advisory Opportunity'},
]


def directory(request):
    rows = agent_data.agent_directory_rows()
    return render(request, 'ai_agent_workbench/directory.html', {
        'agent_rows': rows,
        'pipeline_stages': PIPELINE_STAGES,
    })


def agent_profile(request, slug):
    context = agent_data.agent_profile_context(slug)
    if context is None:
        return render(request, 'ai_agent_workbench/agent_not_found.html', {'slug': slug}, status=404)
    return render(request, 'ai_agent_workbench/agent_profile.html', {'agent': context})


def _run_context_for_agent(council_run, agent_name):
    if not council_run:
        return None
    agent_run = (
        AgentRun.objects
        .filter(council_case=council_run, agent__agent_name=agent_name)
        .select_related('agent', 'council_position')
        .order_by('-created_at')
        .first()
    )
    task = council_run.tasks.filter(agent_name=agent_name).first()
    handoffs_in = council_run.handoffs.filter(receiver_agent=agent_name)
    handoffs_out = council_run.handoffs.filter(sender_agent=agent_name)
    return {
        'agent_run': agent_run, 'task': task,
        'handoffs_in': handoffs_in, 'handoffs_out': handoffs_out,
    }


def workbench(request):
    case_slug = request.GET.get('case', '')
    agent_slug = request.GET.get('agent', '')
    ask_text = request.GET.get('ask', '').strip()

    demo_case = demo_cases.get_demo_case(case_slug) if case_slug else None
    agent_rows = agent_data.agent_directory_rows()
    selected_agent_row = next((r for r in agent_rows if r['slug'] == agent_slug), None)

    recommendation = None
    if ask_text:
        recommendation = recommender.recommend_agent_for_task(ask_text)

    council_run = demo_cases.council_run_for_case(demo_case) if demo_case else None
    run_context = None
    ranked_options = None

    if demo_case and demo_case['slug'] == demo_cases.INVESTMENT_PORTFOLIO:
        ranked_options = demo_cases.ranked_investment_options(demo_case)
    elif demo_case and selected_agent_row:
        run_context = _run_context_for_agent(council_run, selected_agent_row['name'])

    agent_available_for_case = (
        demo_case is not None and selected_agent_row is not None
        and selected_agent_row['name'] in demo_case.get('agents_involved', [])
    )

    return render(request, 'ai_agent_workbench/workbench.html', {
        'demo_cases': list(demo_cases.DEMO_CASES.values()),
        'demo_case': demo_case,
        'agent_rows': agent_rows,
        'selected_agent_row': selected_agent_row,
        'council_run': council_run,
        'run_context': run_context,
        'ranked_options': ranked_options,
        'agent_available_for_case': agent_available_for_case,
        'ask_text': ask_text,
        'recommendation': recommendation,
    })


def council_demo(request):
    from ai_agent_council.models import CouncilRun
    cases = []
    for entry in COUNCIL_DEMO_CASES:
        run = CouncilRun.objects.filter(slug=entry['slug']).first()
        cases.append({**entry, 'run': run})
    return render(request, 'ai_agent_workbench/council_demo.html', {'cases': cases})


def performance(request):
    agent_data.ensure_registry_synced()
    rows = agent_data.agent_directory_rows()
    return render(request, 'ai_agent_workbench/performance.html', {'agent_rows': rows})


def presentation(request):
    from ai_agent_council.models import CouncilRun
    walkthrough_case = CouncilRun.objects.filter(slug='meat-cold-chain-loss-prevention-demo').first()
    return render(request, 'ai_agent_workbench/presentation.html', {
        'pipeline_stages': [
            'Question', 'Specialist Agents', 'Disagreement', 'Cross-Examination',
            'Conditions', 'Human Approval', 'Verified Outcome',
        ],
        'walkthrough_case': walkthrough_case,
    })


def run_alias(request, run_id):
    return redirect(reverse('agent_runtime_model_router:run_detail', args=[run_id]))


def orchestration_detail(request, run_id):
    """
    Lets the Workbench open a LangGraph-powered analysis result — reads the
    existing langgraph_orchestration.OrchestrationRun directly, no new
    orchestration model or duplicate result storage here.
    """
    from django.shortcuts import get_object_or_404

    from langgraph_orchestration.models import OrchestrationRun

    run = get_object_or_404(OrchestrationRun, pk=run_id)
    return render(request, 'ai_agent_workbench/orchestration_detail.html', {'run': run})
