"""Private server-rendered Stage 7 review console.

No browser endpoint accepts a claimed AI result, triggers a model, or grants
external transfer permission. Django's CSRF middleware protects both forms.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from api.models import ProcessAIReviewCase
from ecoiq_os.human_review import (
    ReviewBlocked, decide_grounded_review, inspect_review_case,
    record_processing_readiness,
)
from gold_intelligence import access


def _private(response):
    response["Cache-Control"] = "private, no-store, max-age=0"
    response["Pragma"] = "no-cache"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


@login_required(login_url="/login/")
@never_cache
def review_queue(request):
    if request.method not in ("GET", "HEAD"):
        return _private(HttpResponseNotAllowed(["GET", "HEAD"]))
    projects = list(
        access.projects_for(request.user, access.APPROVE)
        .order_by("name", "pk")[:101]
    )
    visible = projects[:100]
    cases = (
        ProcessAIReviewCase.objects
        .filter(project_id__in=[p.pk for p in visible])
        .select_related("project", "analysis", "submitted_by")
        .order_by("-created_at", "-pk")[:50]
    )
    return _private(render(request, "core/ai_review_queue.html", {
        "cases": cases,
        "projects": visible,
        "project_list_truncated": len(projects) > 100,
        "suppress_analytics": True,
    }))


@login_required(login_url="/login/")
@never_cache
def review_detail(request, project_slug, review_id):
    if request.method not in ("GET", "HEAD", "POST"):
        return _private(HttpResponseNotAllowed(["GET", "HEAD", "POST"]))
    project = get_object_or_404(
        access.projects_for(request.user, access.APPROVE), slug=project_slug,
    )
    case = get_object_or_404(
        ProcessAIReviewCase.objects.select_related("analysis", "submitted_by", "reviewed_by"),
        pk=review_id, project=project,
    )

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "decision":
                if set(request.POST.keys()) != {
                    "csrfmiddlewaretoken", "action", "decision", "reason_code",
                }:
                    raise ReviewBlocked("Unsupported form fields.")
                decide_grounded_review(
                    project=project, actor=request.user, case_id=case.pk,
                    decision=request.POST.get("decision"),
                    reason_code=request.POST.get("reason_code"),
                )
            elif action == "readiness":
                if not inspect_review_case(project=project, actor=request.user, case=case)["is_current"]:
                    raise ReviewBlocked("Source content or verification has changed.")
                if set(request.POST.keys()) != {
                    "csrfmiddlewaretoken", "action", "source_rights",
                    "privacy", "provider_terms",
                }:
                    raise ReviewBlocked("Unsupported form fields.")
                record_processing_readiness(
                    project=project, analysis=case.analysis, actor=request.user,
                    checks={
                        "source_rights": request.POST.get("source_rights") == "on",
                        "privacy": request.POST.get("privacy") == "on",
                        "provider_terms": request.POST.get("provider_terms") == "on",
                    },
                )
            else:
                raise ReviewBlocked("Unknown review action.")
        except ReviewBlocked as exc:
            return _private(render(request, "core/ai_review_detail.html", {
                "review": case,
                "snapshot": inspect_review_case(project=project, actor=request.user, case=case),
                "events": list(case.events.select_related("actor")[:20]),
                "readiness": list(case.analysis.ai_processing_readiness.filter(project=project)[:10]),
                "error": str(exc),
                "suppress_analytics": True,
            }, status=409))
        # Redirect-after-POST: do not accidentally submit review actions twice.
        return redirect("ai_review_detail", project_slug=project.slug, review_id=case.pk)

    snapshot = inspect_review_case(project=project, actor=request.user, case=case)
    return _private(render(request, "core/ai_review_detail.html", {
        "review": case, "snapshot": snapshot,
        "events": list(case.events.select_related("actor")[:20]),
        "readiness": list(case.analysis.ai_processing_readiness.filter(project=project)[:10]),
        "suppress_analytics": True,
    }))
