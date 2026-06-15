"""
EcoIQ Evidence Harvester — read-only Company Evidence Dashboard (Slice 5).

Standalone, additive, read-only views over harvested data. They never write,
score, or interpret — they only summarise what the harvester has stored:
coverage, verification, missing categories, sources, evidence, datapoints, and
contradictions. No scoring / Moral Compass / Planetary Balance / Executive Brief.

Existing company-profile pages are NOT touched — these live at separate routes.
"""
from __future__ import annotations

from collections import Counter

from django.http import JsonResponse
from django.shortcuts import render

from .constants import EVIDENCE_CATEGORIES


def _company_name(slug: str) -> str:
    try:
        from league.models import Company
        c = Company.objects.filter(slug=slug).only("name").first()
        return c.name if c else slug
    except Exception:  # noqa: BLE001 — never let lookup break a read-only view
        return slug


def build_dashboard_data(slug: str) -> dict:
    """Assemble the read-only dashboard payload for a company slug.

    Pure read: queries Evidence / Datapoint / EvidenceSourceRef and derives
    coverage, verification, and missing-category summaries. No mutation.
    """
    from .models import Evidence, Datapoint, EvidenceSourceRef

    cat_labels = dict(EVIDENCE_CATEGORIES)
    all_categories = [c[0] for c in EVIDENCE_CATEGORIES]

    evidence = list(
        Evidence.objects.filter(company_slug=slug).order_by("category", "-confidence")
    )
    datapoints = list(
        Datapoint.objects.filter(company_slug=slug).order_by("category", "metric")
    )
    refs = (EvidenceSourceRef.objects
            .filter(canonical_evidence__company_slug=slug)
            .order_by("-source_quality_score"))

    present = sorted({e.category for e in evidence})
    missing = [c for c in all_categories if c not in present]

    total_ev = len(evidence)
    status_counts = Counter(e.verification_status for e in evidence)
    verified = status_counts.get("VERIFIED", 0)

    coverage_pct = round(len(present) / len(all_categories) * 100, 1)
    verification_pct = round(verified / total_ev * 100, 1) if total_ev else 0.0

    # distinct contributing sources (by type + url)
    sources, seen = [], set()
    for r in refs:
        key = (r.source_type, r.url)
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "source_type": r.source_type,
            "source_owner": r.source_owner or "",
            "url": r.url or "",
            "publication_date": r.publication_date.isoformat() if r.publication_date else None,
            "quality": round(r.source_quality_score, 3),
        })

    def ev_dict(e):
        return {
            "id": e.id,
            "category": e.category,
            "category_label": cat_labels.get(e.category, e.category),
            "title": e.title or (e.excerpt[:120] if e.excerpt else ""),
            "url": e.url or "",
            "publication_date": e.publication_date.isoformat() if e.publication_date else None,
            "verification_status": e.verification_status,
            "confidence": round(e.confidence, 3),
            "corroboration_count": e.corroboration_count,
            "source_count": e.source_refs.count(),
        }

    def dp_dict(d):
        return {
            "metric": d.metric,
            "value": d.value,
            "value_text": d.value_text or "",
            "unit": d.unit or "",
            "period": d.period or "",
            "period_year": d.period_year,
            "category": d.category,
            "category_label": cat_labels.get(d.category, d.category),
            "status": d.status,
            "confidence": round(d.confidence, 3),
        }

    contradictions = [ev_dict(e) for e in evidence
                      if e.verification_status == "CONTRADICTED"]

    return {
        "company_slug": slug,
        "company_name": _company_name(slug),
        "coverage_pct": coverage_pct,
        "verification_pct": verification_pct,
        "categories_present": len(present),
        "categories_total": len(all_categories),
        "missing_categories": [{"key": c, "label": cat_labels[c]} for c in missing],
        "status_breakdown": dict(status_counts),
        "counts": {
            "sources": len(sources),
            "evidence": total_ev,
            "datapoints": len(datapoints),
            "contradictions": len(contradictions),
        },
        "sources": sources,
        "evidence": [ev_dict(e) for e in evidence],
        "datapoints": [dp_dict(d) for d in datapoints],
        "contradictions": contradictions,
        "read_only": True,
        "disclaimer": (
            "Read-only Evidence Harvester summary. Collected, verified, and "
            "normalized evidence only — no scoring, rating, or interpretation."
        ),
    }


def evidence_dashboard(request, slug):
    """GET /evidence/<slug>/ — standalone read-only Company Evidence Dashboard."""
    data = build_dashboard_data(slug)
    return render(request, "harvester/evidence_dashboard.html", {"d": data})


def evidence_dashboard_data(request, slug):
    """GET /evidence/<slug>/data/ — same payload as JSON (read-only)."""
    return JsonResponse(build_dashboard_data(slug))
