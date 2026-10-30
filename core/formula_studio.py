"""Private, read-only Formula Studio; business proposal metadata only."""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache

from ecoiq_os.formula_designer import EXTRA_SITUATION_FORMULAS
from ecoiq_os.formula_registry import formula_catalogue_view
from gold_intelligence import access


@login_required(login_url="/login/")
@never_cache
def formula_studio(request, project_slug):
    if request.method not in ("GET", "HEAD"):
        response = HttpResponseNotAllowed(["GET", "HEAD"])
    else:
        project = get_object_or_404(
            access.projects_for(request.user, access.READ),
            slug=project_slug,
        )
        additional = [{
            "key": row.key,
            "title": row.title, "expression": row.expression,
            "output_unit": row.output_unit,
            "required_inputs": [
                {"key": x.key, "unit": x.unit} for x in row.inputs
            ],
            "limitation": row.interpretation_limit,
        } for row in EXTRA_SITUATION_FORMULAS.values()]
        response = render(request, "core/formula_studio.html", {
            "project": project,
            "initial_formulas": formula_catalogue_view(),
            "situation_formulas": additional,
            "suppress_analytics": True,
        })
    response["Cache-Control"] = "private, no-store, max-age=0"
    response["Pragma"] = "no-cache"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response
