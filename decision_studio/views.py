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
"""
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from decision_studio.models import DecisionQuery
from decision_studio.services.decision_engine import answer_question

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
    recent_queries = DecisionQuery.objects.filter(session_key=request.session.session_key)[:10]
    # Optional prefill only — e.g. from the globe's "Ask EcoIQ about the
    # world" action. Never auto-submits; the user still presses Ask, so the
    # existing rate-limit/cost-control path in ask() is untouched.
    prefill_question = request.GET.get('q', '').strip()[:MAX_QUESTION_LENGTH]
    return render(request, 'decision_studio/studio.html', {
        'suggested_questions': SUGGESTED_QUESTIONS, 'recent_queries': recent_queries,
        'prefill_question': prefill_question,
    })


def ask(request):
    if request.method != 'POST':
        return redirect('decision_studio:studio')

    question_text = request.POST.get('question', '').strip()[:MAX_QUESTION_LENGTH]
    if not question_text:
        return redirect('decision_studio:studio')

    if _is_rate_limited(request):
        return render(request, 'decision_studio/rate_limited.html', {
            'window_minutes': RATE_LIMIT_WINDOW_SECONDS // 60, 'max_requests': RATE_LIMIT_MAX_REQUESTS,
        })

    if not request.session.session_key:
        request.session.save()

    parent_id = request.POST.get('parent_query_id')
    parent_query = DecisionQuery.objects.filter(pk=parent_id).first() if parent_id else None

    outcome = answer_question(question_text, execution_mode='deterministic_test')

    query = DecisionQuery.objects.create(
        question_text=question_text, session_key=request.session.session_key,
        user=request.user if request.user.is_authenticated else None,
        intent=outcome['intent'], resolved_entities=outcome['entities'], scope=outcome['scope'],
        capability_plan=outcome['capability_plan'], data_availability_status=outcome['data_availability'],
        confidence_label=outcome['confidence_label'], confidence_score=outcome['confidence_score'],
        result=outcome['result'], parent_query=parent_query,
    )
    return redirect(reverse('decision_studio:result_detail', args=[query.pk]))


def result_detail(request, query_id):
    query = get_object_or_404(DecisionQuery, pk=query_id)
    return render(request, 'decision_studio/result.html', {'query': query, 'result': query.result})
