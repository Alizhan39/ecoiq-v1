"""
EcoIQ Evidence Harvester — read-only presentation rollups.

Pure read helpers for the investor-facing presentation layer. They query
Evidence / Datapoint only and never write, score, harvest, or normalize. Used by
the company-page evidence panel (and, later, the ranking page / explorer).
"""
from __future__ import annotations


def _evidence_dict(e):
    return {
        "title": e.title or (e.excerpt[:120] if e.excerpt else ""),
        "category": e.category,
        "verification_status": e.verification_status,
        "confidence": round(e.confidence, 2),
        "url": e.url or "",
    }


def _datapoint_dict(d):
    return {
        "metric": d.metric,
        "value": d.value,
        "value_text": d.value_text or "",
        "unit": d.unit or "",
        "period": d.period or "",
        "status": d.status,
    }


def company_rollup(slug: str, *, n: int = 5) -> dict:
    """Read-only summary of harvested evidence for a company slug.

    Returns counts, last-updated timestamp, and the n most recent evidence rows
    and datapoints. No mutation.
    """
    from .models import Evidence, Datapoint

    ev_qs = Evidence.objects.filter(company_slug=slug)
    dp_qs = Datapoint.objects.filter(company_slug=slug)

    evidence_count = ev_qs.count()
    datapoint_count = dp_qs.count()

    latest_evidence = list(ev_qs.order_by("-retrieved_at")[:n])
    latest_datapoints = list(
        dp_qs.order_by("-normalized_at", "-created_at")[:n]
    )

    # last updated = most recent evidence retrieval or datapoint normalization
    stamps = []
    if latest_evidence:
        stamps.append(latest_evidence[0].retrieved_at)
    newest_dp = dp_qs.exclude(normalized_at=None).order_by("-normalized_at").first()
    if newest_dp:
        stamps.append(newest_dp.normalized_at)
    last_updated = max(stamps) if stamps else None

    return {
        "slug": slug,
        "evidence_count": evidence_count,
        "datapoint_count": datapoint_count,
        "last_updated": last_updated,
        "latest_evidence": [_evidence_dict(e) for e in latest_evidence],
        "latest_datapoints": [_datapoint_dict(d) for d in latest_datapoints],
        "has_data": bool(evidence_count or datapoint_count),
        "dashboard_url": f"/evidence/{slug}/",
    }
