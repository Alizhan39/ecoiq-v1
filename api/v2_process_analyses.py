"""Authenticated, project-scoped process CSV inspection and private history.

Uses the existing GoldProject permission registry (generic portfolio project
identity) and Process Diagnostic kernel. It deliberately stores NO CSV bytes,
raw observations, or evidence identifiers, and issues no operational writes.
"""
from __future__ import annotations

import hashlib
import hmac

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view, authentication_classes, parser_classes, permission_classes,
    throttle_classes,
)
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from api.models import ProcessAnalysisRun
from ecoiq_os.process_csv import MAX_CSV_BYTES, diagnose_csv
from gold_intelligence import access


class ProcessCSVUploadThrottle(SimpleRateThrottle):
    """Authenticated per-user cap; never use a claimed client/IP identity."""

    scope = "os_process_upload"
    rate = "20/hour"

    def get_cache_key(self, request, view):
        if request.method != "POST" or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


def _private(payload, status=200):
    response = Response(payload, status=status)
    response["Cache-Control"] = "private, no-store, max-age=0"
    response["Pragma"] = "no-cache"
    return response


def _resolve_project(request, slug, permission):
    # Projects are searched *inside* the authorised queryset, so an attacker
    # cannot distinguish nonexistent project slugs from inaccessible ones.
    return get_object_or_404(access.projects_for(request.user, permission), slug=slug)


def _view_run(run):
    """Fixed, minimal projection: never include actor email or fingerprint."""
    return {
        "id": run.pk,
        "case_id": run.case_id,
        "domain": run.domain,
        "process_name": run.process_name,
        "resource_type": run.resource_type,
        "unit": run.unit,
        "period": run.period,
        "created_at": run.created_at.isoformat(),
        "read_only": True,
        "independently_verified": False,
        "result": run.summary,
    }


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
@throttle_classes([ProcessCSVUploadThrottle])
def process_analyses(request, project_slug):
    """GET history or POST a single <=512 KiB UTF-8 multipart CSV.

    GET grants READ, POST grants ANALYSE. User ID/project permission/evidence
    truth is NEVER accepted from POST payload. Django's session authenticator
    enforces CSRF on authenticated unsafe requests.
    """
    permission = access.ANALYSE if request.method == "POST" else access.READ
    project = _resolve_project(request, project_slug, permission)

    if request.method == "GET":
        runs = ProcessAnalysisRun.objects.filter(project=project).order_by("-created_at", "-pk")
        return _private({
            "project_slug": project.slug,
            "count": runs.count(),
            "results": [_view_run(run) for run in runs[:50]],
            "has_more": runs.count() > 50,
        })

    # Narrow multipart contract: only 'file' is accepted; no actor, approval
    # state, organisation, cause or arbitrary claimed permission parameters.
    # Bound the entire HTTP entity before multipart parsing; reverse proxies
    # should enforce a matching server-level request-body ceiling as well.
    declared = request.META.get("CONTENT_LENGTH")
    try:
        size = int(declared) if declared else 0
    except (ValueError, TypeError):
        return _private({"detail": "Invalid content length."}, 400)
    if size > MAX_CSV_BYTES + 8192:
        return _private({"detail": "Request exceeds size limit."}, 413)
    if set(request.data.keys()) != {"file"} or len(request.FILES) != 1:
        return _private({"detail": "Upload exactly one CSV field named file."}, 400)
    upload = request.FILES.get("file")
    if upload is None or upload.size > MAX_CSV_BYTES:
        return _private({"detail": "CSV missing or exceeds size limit."}, 400)

    raw = upload.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        return _private({"detail": "CSV exceeds size limit."}, 400)

    try:
        parsed = raw.decode("utf-8-sig")
        diagnostic = diagnose_csv(parsed)
    except (ValueError, UnicodeError) as exc:
        # Never echo submitted CSV content; validation errors only name fields
        # and line numbers.
        return _private({"detail": str(exc)}, 400)

    # Recheck the grant immediately before the protected DB write to avoid
    # honouring a role revoked while a file was being parsed.
    if not access.can(request.user, project, access.ANALYSE):
        raise Http404

    # Project membership and owner come from server-side context, not CSV.
    # A repeated import is idempotent within one project.
    digest = hmac.new(
        settings.SECRET_KEY.encode("utf-8"), raw, hashlib.sha256
    ).hexdigest()
    snapshot = diagnostic
    kpi = snapshot["kpi"]
    report = {
        "kpi": {
            "key": kpi["key"],
            "value": kpi["value"],
            "status": kpi["status"],
            "unit": kpi["unit"],
            "numerator": kpi["numerator"],
            "denominator": kpi["denominator"],
            "source_unit": kpi["source_unit"],
            "period": kpi["period"],
            "independently_verified": False,
        },
        "next_stage": snapshot["next_step"]["next_stage"],
        "requires_human_review": snapshot["next_step"]["requires_human_review"],
        "import": {
            "rows": snapshot["import"]["rows"],
            "unknown_inputs": snapshot["import"]["unknown_inputs"],
            "unknown_losses": snapshot["import"]["unknown_losses"],
            "source_authentication": "NOT_VERIFIED",
            "raw_csv_stored": False,
        },
    }
    try:
        with transaction.atomic():
            run, created = ProcessAnalysisRun.objects.get_or_create(
                project=project, file_fingerprint=digest,
                defaults={
                    "created_by": request.user,
                    "case_id": snapshot["case_id"],
                    "domain": snapshot["domain"],
                    "process_name": snapshot["process_name"],
                    "resource_type": snapshot["flow_graph"]["edges"][0]["resource_type"],
                    "period": kpi["period"],
                    "unit": kpi["source_unit"],
                    "summary": report,
                },
            )
    except IntegrityError:
        # Never leak a database exception (the duplicate is already safe).
        run = ProcessAnalysisRun.objects.filter(project=project, file_fingerprint=digest).first()
        if run is None:
            raise
        created = False

    return _private({
        "created": created,
        "analysis": _view_run(run),
    }, 201 if created else 200)


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def process_analysis_detail(request, project_slug, run_id):
    project = _resolve_project(request, project_slug, access.READ)
    run = get_object_or_404(ProcessAnalysisRun, project=project, pk=run_id)
    return _private({"analysis": _view_run(run)})
