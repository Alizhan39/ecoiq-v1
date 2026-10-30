"""Read-only, permission-scoped Decision & Islah evidence brief API."""
from django.shortcuts import get_object_or_404
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes,
)
from rest_framework.permissions import IsAuthenticated

from api.models import ProcessAnalysisRun
from api.v2_process_analyses import _private, _resolve_project
from ecoiq_os.decision_islah import build_preliminary_brief
from gold_intelligence import access


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def process_decision_brief(request, project_slug, run_id):
    """Never infer project ownership from process names or case IDs.

    Source CSVs and evidence references are not in ProcessAnalysisRun; no
    authenticated causal finding, Islah execution approval or model call is
    possible through this endpoint.
    """
    project = _resolve_project(request, project_slug, access.READ)
    run = get_object_or_404(ProcessAnalysisRun, pk=run_id, project=project)
    try:
        kpi = run.summary["kpi"]
        brief = build_preliminary_brief(
            case_id=run.case_id,
            domain=run.domain,
            process_name=run.process_name,
            resource_type=run.resource_type,
            period=run.period,
            unit=run.unit,
            reported_input=kpi["denominator"],
            reported_loss=kpi["numerator"],
        )
    except (KeyError, ValueError, TypeError):
        # Legacy, malformed or migrated data cannot be silently upgraded.
        # No internals or commercial amounts are returned in the error.
        return _private({
            "detail": "This analysis is incomplete and cannot support a decision brief.",
        }, 422)
    return _private({
        "analysis_id": run.pk,
        "project_slug": project.slug,
        "brief": brief,
    })
