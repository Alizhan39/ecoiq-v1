"""
WHY Engine — views: JSON API, Boardroom web report, Decision Defense Pack PDF.
Read-only; all data from core.why (evidence-derived). No new models, no AI.
"""
from __future__ import annotations

from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import render

from .why import why_company, why_country


def _resolve(subject, slug):
    d = why_country(slug) if subject == "country" else why_company(slug)
    if d is None:
        raise Http404("subject not found")
    return d


# ── WHY API (sellable, read-only) ──
def api_why_country(request, slug):
    return JsonResponse(_resolve("country", slug))


def api_why_company(request, slug):
    return JsonResponse(_resolve("company", slug))


# ── Boardroom Mode web report ──
def why_country_page(request, slug):
    return render(request, "why/report.html", {"d": _resolve("country", slug)})


def why_company_page(request, slug):
    return render(request, "why/report.html", {"d": _resolve("company", slug)})


# ── Decision Defense Pack (PDF) ──
def _pack(request, subject, slug):
    import weasyprint
    from django.template.loader import render_to_string
    from datetime import datetime, timezone

    d = _resolve(subject, slug)
    d["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    d["base_url"] = request.build_absolute_uri("/")
    html = render_to_string("why/defense_pack.html", {"d": d})
    pdf = weasyprint.HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = 'inline; filename="ecoiq-decision-defense-%s-%s.pdf"' % (subject, slug)
    return resp


def defense_pack_country(request, slug):
    return _pack(request, "country", slug)


def defense_pack_company(request, slug):
    return _pack(request, "company", slug)
