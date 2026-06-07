"""
EcoIQ Projects — Phase 1 views.

Lightweight, static-data-backed list + detail. No database access. When the
section is promoted to a model (Phase 2), only the data source changes — the
URLs, view names and templates stay the same.
"""
from django.http import Http404
from django.shortcuts import render

from .data import PROJECTS, PROJECTS_BY_SLUG, status_label


def project_index(request):
    """
    GET /projects/ — Portfolio overview of all EcoIQ real-world projects.
    Public, no auth.
    """
    projects = [
        {**p, 'status': status_label(p['status_key'])}
        for p in PROJECTS
    ]
    return render(request, 'projects/index.html', {'projects': projects})


def project_detail(request, slug):
    """
    GET /projects/<slug>/ — Individual project page.
    404 if the slug is unknown. Public, no auth.
    """
    project = PROJECTS_BY_SLUG.get(slug)
    if project is None:
        raise Http404('Project not found')

    project = {**project, 'status': status_label(project['status_key'])}
    return render(request, 'projects/detail.html', {'project': project})
