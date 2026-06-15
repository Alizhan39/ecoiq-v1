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

    # mean evidence confidence (verification confidence, not a company score)
    from django.db.models import Avg
    avg_conf = ev_qs.aggregate(a=Avg("confidence"))["a"]
    avg_confidence = round(avg_conf, 2) if avg_conf is not None else None

    return {
        "slug": slug,
        "evidence_count": evidence_count,
        "datapoint_count": datapoint_count,
        "avg_confidence": avg_confidence,
        "last_updated": last_updated,
        "latest_evidence": [_evidence_dict(e) for e in latest_evidence],
        "latest_datapoints": [_datapoint_dict(d) for d in latest_datapoints],
        "has_data": bool(evidence_count or datapoint_count),
        "dashboard_url": f"/evidence/{slug}/",
    }


def platform_stats() -> dict:
    """Read-only platform totals for the homepage intelligence block."""
    from django.db.models import Max
    from .models import RegistryCompany, Evidence, Datapoint

    ev_last = Evidence.objects.aggregate(m=Max("retrieved_at"))["m"]
    dp_last = Datapoint.objects.exclude(normalized_at=None).aggregate(m=Max("normalized_at"))["m"]
    stamps = [s for s in (ev_last, dp_last) if s]
    return {
        "companies_tracked": RegistryCompany.objects.filter(is_active=True).count(),
        "evidence_count": Evidence.objects.count(),
        "datapoint_count": Datapoint.objects.count(),
        "last_updated": max(stamps) if stamps else None,
        "rankings_url": "/rankings/utilities/",
        "evidence_url": "/evidence/",
    }


def _latest_metric_value(slug, metric):
    from .models import Datapoint
    dp = (Datapoint.objects.filter(company_slug=slug, metric=metric, status="NORMALIZED")
          .exclude(value=None).order_by("-period_year", "-normalized_at").first())
    return (dp.value, dp.unit) if dp else (None, "")


def rankings_data() -> list:
    """Read-only per-company rollup for the rankings table — all active registry
    companies, sorted by operating profit descending (no-data companies last)."""
    from django.db.models import Max
    from .models import RegistryCompany, Evidence, Datapoint

    rows = []
    for rc in RegistryCompany.objects.filter(is_active=True):
        slug = rc.slug
        rev, rev_unit = _latest_metric_value(slug, "revenue")
        op, op_unit = _latest_metric_value(slug, "operating_profit")
        ev_count = Evidence.objects.filter(company_slug=slug).count()
        dp_count = Datapoint.objects.filter(company_slug=slug).count()
        ev_last = Evidence.objects.filter(company_slug=slug).aggregate(m=Max("retrieved_at"))["m"]
        rows.append({
            "slug": slug,
            "company_name": rc.company_name,
            "ticker": rc.ticker,
            "sector": rc.sector,
            "subsector": rc.subsector,
            "revenue": rev, "revenue_unit": rev_unit,
            "operating_profit": op, "operating_profit_unit": op_unit,
            "evidence_count": ev_count,
            "datapoint_count": dp_count,
            "last_updated": ev_last,
        })
    # operating profit desc; None sorts last; tie-break by evidence count
    rows.sort(key=lambda r: (r["operating_profit"] is not None,
                             r["operating_profit"] or 0,
                             r["evidence_count"]), reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows
