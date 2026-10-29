"""Session-protected Business OS workspace over the existing process CSV API.

Only server-authorised GoldProject roles may be rendered in the project picker.
This page does not parse CSV or calculate KPI; that remains exclusively in
api.v2_process_analyses and the existing EcoIQ OS diagnostic kernel.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from gold_intelligence import access


@login_required(login_url="/login/")
@never_cache
def process_workspace(request):
    """GET the responsive workspace. All actual reads/writes recheck API roles."""
    if request.method not in ("GET", "HEAD"):
        response = HttpResponseNotAllowed(["GET", "HEAD"])
    else:
        permitted = list(access.projects_for(request.user, access.READ)
                         .order_by("name", "pk")[:101])
        truncated = len(permitted) > 100
        visible = permitted[:100]
        writable_ids = set(
            access.projects_for(request.user, access.ANALYSE)
            .filter(pk__in=[project.pk for project in visible])
            .values_list("pk", flat=True)
        )
        projects = [
            {"slug": project.slug, "name": project.name,
             "can_upload": project.pk in writable_ids}
            for project in visible
        ]
        response = render(request, "core/process_workspace.html", {
            "projects": projects,
            "project_list_truncated": truncated,
        })
    response["Cache-Control"] = "private, no-store, max-age=0"
    response["Pragma"] = "no-cache"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response
