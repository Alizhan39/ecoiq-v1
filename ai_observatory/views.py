"""
ai_observatory/views.py — the AI Intelligence Observatory dashboard and
Methodology pages. Staff-only, project-scoped: a session is only ever
reachable through its own project's slug (cross-project session IDs 404),
mirroring capital_guardian's permission model. Read-only — telemetry is
written exclusively by services/recorder.py at real pipeline run time.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from gold_intelligence.models import GoldProject

from ai_observatory.models import AnalysisSession
from ai_observatory.services import comparison as comparison_service
from ai_observatory.services import metrics as metrics_service
from ai_observatory.services import proxies as proxies_service


def _project_or_404(slug):
    return get_object_or_404(GoldProject, slug=slug)


def _session_or_404_for_project(project, session_id):
    session = get_object_or_404(AnalysisSession.objects.select_related('user'), pk=session_id)
    if session.project_id != project.pk:
        raise Http404('No observatory session found for this project.')
    return session


def _dashboard_context(project, current_session=None):
    sessions = AnalysisSession.objects.filter(project=project).select_related('user')
    completed = [s for s in sessions if s.status == 'completed']
    current = current_session or (sessions.first() if sessions else None)

    # feat/e2e-project-pipeline — the same project workflow nav every other
    # stage renders, so Observatory is reachable and returnable-from as part
    # of the one connected journey, not a dead end.
    from capital_guardian.services.command_centre import build_project_workflow_nav

    context = {
        'project': project,
        'sessions': list(sessions[:25]),
        'session_total': sessions.count(),
        'current': current,
        'current_stages': list(current.stages.all()) if current is not None else [],
        'current_invocations': list(current.model_invocations.all()) if current is not None else [],
        'metrics': metrics_service.quality_metrics(project),
        'proxies': proxies_service.proxy_indices(completed),
        'comparison': comparison_service.compare(project, completed) if completed else None,
        'metric_definitions': metrics_service.METRIC_DEFINITIONS,
        'workflow_nav': build_project_workflow_nav(project, 'observatory'),
    }
    return context


@staff_member_required(login_url='/login/')
def observatory_view(request, slug):
    project = _project_or_404(slug)
    return render(request, 'ai_observatory/observatory.html', _dashboard_context(project))


@staff_member_required(login_url='/login/')
def session_detail_view(request, slug, session_id):
    project = _project_or_404(slug)
    session = _session_or_404_for_project(project, session_id)
    return render(request, 'ai_observatory/observatory.html', _dashboard_context(project, current_session=session))


@staff_member_required(login_url='/login/')
def methodology_view(request, slug):
    project = _project_or_404(slug)
    from ai_observatory.services.comparison import baseline_assumptions
    from ai_observatory.services.proxies import compute_weights, cost_weights

    cw, kw = compute_weights(), cost_weights()
    weight_rows = [{'key': key, 'compute': cw[key], 'cost': kw.get(key)} for key in cw]

    from capital_guardian.services.command_centre import build_project_workflow_nav

    return render(request, 'ai_observatory/methodology.html', {
        'project': project,
        'metric_definitions': metrics_service.METRIC_DEFINITIONS,
        'weight_rows': weight_rows,
        'baseline_assumptions': baseline_assumptions(),
        'proxies_doc': proxies_service.__doc__,
        'comparison_doc': comparison_service.__doc__,
        'workflow_nav': build_project_workflow_nav(project, 'observatory'),
    })
