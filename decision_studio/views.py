"""
decision_studio/views.py — the Decision Studio's three views.

Security/cost controls enforced here, not left to the caller:
- execution_mode is ALWAYS 'deterministic_test' for this public form — a
  user-supplied question can never reach a real, billed LLM call. Live
  analysis stays exactly where it already lives (the AI Agent Workbench,
  behind existing controls) — this view is not a new path to it.
- question length is capped (MAX_QUESTION_LENGTH) before anything touches it.
- a simple per-session rate limit (cache-based) bounds how often one visitor
  can submit — there is no existing rate-limit precedent for plain Django
  views in this codebase (only the DRF JSON API has one), so this is a new,
  minimal safeguard rather than a reused one.
- a question belongs to whoever asked it. Every read of a DecisionQuery goes
  through decision_studio/visibility.py, so the list and the detail view
  cannot disagree about who may see what.
"""
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from decision_studio.models import DecisionQuery
from decision_studio.services.decision_engine import answer_question
from decision_studio.visibility import queries_visible_to
from gold_intelligence.access import ANALYSE, projects_for

MAX_QUESTION_LENGTH = 500
RATE_LIMIT_MAX_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 600  # 10 minutes

SUGGESTED_QUESTIONS = [
    'Which companies have the strongest investment opportunity and modernisation potential?',
    'Compare available companies by EcoIQ Intelligence Score.',
    'Where is EcoIQ\'s evidence too weak to support a confident decision?',
    'Which portfolio companies show unusual risk patterns?',
]


def _rate_limit_key(request):
    if not request.session.session_key:
        request.session.save()
    return f'decision_studio_rate:{request.session.session_key}'


def _is_rate_limited(request):
    key = _rate_limit_key(request)
    count = cache.get(key, 0)
    if count >= RATE_LIMIT_MAX_REQUESTS:
        return True
    cache.set(key, count + 1, timeout=RATE_LIMIT_WINDOW_SECONDS)
    return False


def studio(request):
    if not request.session.session_key:
        request.session.save()
    recent_queries = queries_visible_to(request)[:10]
    # Optional prefill only — e.g. from the globe's "Ask EcoIQ about the
    # world" action. Never auto-submits; the user still presses Ask, so the
    # existing rate-limit/cost-control path in ask() is untouched.
    prefill_question = request.GET.get('q', '').strip()[:MAX_QUESTION_LENGTH]
    available_projects = projects_for(request.user, ANALYSE)
    project_id = request.GET.get('project_id')
    selected_project = _selected_project(available_projects, project_id) if project_id else None
    return render(request, 'decision_studio/studio.html', {
        'suggested_questions': SUGGESTED_QUESTIONS, 'recent_queries': recent_queries,
        'prefill_question': prefill_question,
        'available_projects': available_projects, 'selected_project': selected_project,
    })


def _selected_project(queryset, project_id):
    from django.http import Http404
    try:
        return get_object_or_404(queryset, pk=int(project_id))
    except (ValueError, TypeError, OverflowError):
        raise Http404('Unknown project.') from None


def ask(request):
    if request.method != 'POST':
        return redirect('decision_studio:studio')

    question_text = (request.POST.get('suggested_question') or request.POST.get('question', '')).strip()[:MAX_QUESTION_LENGTH]
    if not question_text:
        return redirect('decision_studio:studio')

    if _is_rate_limited(request):
        return render(request, 'decision_studio/rate_limited.html', {
            'window_minutes': RATE_LIMIT_WINDOW_SECONDS // 60, 'max_requests': RATE_LIMIT_MAX_REQUESTS,
        })

    if not request.session.session_key:
        request.session.save()

    # Scoped like everything else: a follow-up may only continue a question
    # this requester actually asked. Unscoped, any id could be named as the
    # parent, threading one visitor's question onto another's.
    parent_id = request.POST.get('parent_query_id')
    from django.http import Http404
    try:
        parent_query = (get_object_or_404(queries_visible_to(request), pk=int(parent_id)) if parent_id else None)
    except (ValueError, TypeError, OverflowError):
        raise Http404('Unknown prior question.') from None

    project_id = request.POST.get('project_id')
    if parent_query and parent_query.project_id is not None:
        if project_id and str(parent_query.project_id) != project_id:
            raise Http404('Follow-up project does not match the original question.')
        project_id = parent_query.project_id
    project = _selected_project(projects_for(request.user, ANALYSE), project_id) if project_id else None
    outcome = answer_question(question_text, execution_mode='deterministic_test', user=request.user, project=project)

    query = DecisionQuery.objects.create(
        question_text=question_text, session_key=request.session.session_key,
        user=request.user if request.user.is_authenticated else None,
        intent=outcome['intent'], resolved_entities=outcome['entities'], scope=outcome['scope'],
        capability_plan=outcome['capability_plan'], data_availability_status=outcome['data_availability'],
        confidence_label=outcome['confidence_label'], confidence_score=outcome['confidence_score'],
        result=outcome['result'], parent_query=parent_query, project=project,
    )
    return redirect(reverse('decision_studio:result_detail', args=[query.pk]))


def result_detail(request, query_id):
    """
    One question's result — only for the visitor who asked it.

    404 rather than 403: whether a given id has ever been asked is itself not
    public, and a 403 would confirm it. Same reasoning as
    companies/visibility.py.
    """
    query = get_object_or_404(queries_visible_to(request), pk=query_id)
    return render(request, 'decision_studio/result.html', {'query': query, 'result': query.result})
