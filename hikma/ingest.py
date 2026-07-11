"""
Hikma evidence ingestion (real, deterministic, no runtime web-scraping).

Extracts SAY / DO / SHOW evidence from the company data EcoIQ already holds on
the CompanyProfile (its real public_sources, reports, disclosures and measured
metrics) rather than fetching external URLs at runtime — which keeps the slice
safe, deterministic, idempotent, and offline-testable.

  SAY  — stated intent / commitments  (ai_summary, emissions targets, reports)
  DO   — actions / investments        (modernization & community investment,
                                       renewable share, modernization projects)
  SHOW — independent metrics/outcomes (estimated emissions, pollution level,
                                       controversy & transparency scores, EcoIQ
                                       score, cited public_sources)

Idempotent: each record carries a content_hash (sha1 of subject|kind|statement);
re-running creates zero duplicates.
"""
from __future__ import annotations

import hashlib

# confidence by source character
TIER_SCORE = {"verified": 0.95, "analyst-reviewed": 0.8, "ai-seeded": 0.5, "model-estimate": 0.3}


def _hash(subject_ref, kind, statement):
    return hashlib.sha1(f"{subject_ref}|{kind}|{statement}".encode("utf-8")).hexdigest()


def _rec(kind, statement, *, tier, source_type, source_url="",
         metric_name="", metric_value=None, metric_unit=""):
    return {
        "kind": kind, "statement": statement, "confidence_tier": tier,
        "confidence_score": TIER_SCORE.get(tier, 0.5),
        "source_type": source_type, "source_url": source_url,
        "metric_name": metric_name, "metric_value": metric_value, "metric_unit": metric_unit,
    }


def extract_evidence(profile) -> dict:
    """Return {'records': [...], 'sources_seen': int}. Pure function — no DB writes."""
    p = profile
    recs = []
    sources = set()

    def src(url):
        if url:
            sources.add(url)
        return url or ""

    # ── SAY: stated intent / commitments ─────────────────────────────────────
    if getattr(p, "ai_summary", ""):
        recs.append(_rec("say", p.ai_summary.strip()[:600],
                         tier="ai-seeded", source_type="company_disclosure",
                         source_url=src(p.annual_report_url)))
    tgt = getattr(p, "emissions_reduction_target", None)
    if tgt is not None:
        recs.append(_rec("say", f"Stated emissions-reduction target of {tgt:.0f}%.",
                         tier="analyst-reviewed", source_type="sustainability_report",
                         source_url=src(p.sustainability_report_url),
                         metric_name="emissions_reduction_target", metric_value=float(tgt), metric_unit="%"))
    if getattr(p, "ai_modernization_report", ""):
        recs.append(_rec("say", p.ai_modernization_report.strip()[:600],
                         tier="ai-seeded", source_type="company_disclosure"))
    if getattr(p, "sustainability_report_url", ""):
        recs.append(_rec("say", "Publishes a public sustainability report.",
                         tier="analyst-reviewed", source_type="sustainability_report",
                         source_url=src(p.sustainability_report_url)))

    # ── DO: actions / capital allocation ─────────────────────────────────────
    mi = getattr(p, "modernization_investment", None)
    if mi:
        recs.append(_rec("do", "Reported modernization investment.",
                         tier="analyst-reviewed", source_type="company_disclosure",
                         metric_name="modernization_investment", metric_value=float(mi), metric_unit="currency"))
    ci = getattr(p, "community_investment", None)
    if ci:
        recs.append(_rec("do", "Reported community investment.",
                         tier="analyst-reviewed", source_type="company_disclosure",
                         metric_name="community_investment", metric_value=float(ci), metric_unit="currency"))
    ren = getattr(p, "renewable_energy_share", None)
    if ren is not None:
        recs.append(_rec("do", f"Renewable energy share at {ren:.0f}%.",
                         tier="analyst-reviewed", source_type="company_disclosure",
                         metric_name="renewable_energy_share", metric_value=float(ren), metric_unit="%"))
    for proj in (getattr(p, "modernization_projects", []) or [])[:5]:
        label = proj if isinstance(proj, str) else (proj.get("name") or proj.get("title") or str(proj))[:200]
        recs.append(_rec("do", f"Modernization project: {label}.",
                         tier="ai-seeded", source_type="company_disclosure"))

    # ── SHOW: independent metrics / measured outcomes ────────────────────────
    em = getattr(p, "estimated_emissions", None)
    if em is not None:
        recs.append(_rec("show", "Estimated emissions (independent estimate).",
                         tier="model-estimate", source_type="dataset",
                         metric_name="estimated_emissions", metric_value=float(em), metric_unit="tCO2e"))
    if getattr(p, "pollution_level", ""):
        recs.append(_rec("show", f"Pollution classification: {p.get_pollution_level_display()}.",
                         tier="analyst-reviewed", source_type="ecoiq_assessment"))
    cr = getattr(p, "controversy_risk_score", None)
    if cr is not None:
        recs.append(_rec("show", f"Controversy-risk indicator at {cr:.0f}/100.",
                         tier="analyst-reviewed", source_type="ecoiq_assessment",
                         metric_name="controversy_risk_score", metric_value=float(cr), metric_unit="/100"))
    tr = getattr(p, "transparency_score_detail", None)
    if tr is not None:
        recs.append(_rec("show", f"Disclosure transparency scored {tr:.0f}/100.",
                         tier="analyst-reviewed", source_type="ecoiq_assessment",
                         metric_name="transparency_score_detail", metric_value=float(tr), metric_unit="/100"))
    ecoiq = getattr(p, "ecoiq_total_score", None)
    if ecoiq:
        recs.append(_rec("show", f"EcoIQ composite score {ecoiq:.1f}/100.",
                         tier="analyst-reviewed", source_type="ecoiq_assessment",
                         metric_name="ecoiq_total_score", metric_value=float(ecoiq), metric_unit="/100"))
    for s in (getattr(p, "public_sources", []) or [])[:8]:
        url = s if isinstance(s, str) else (s.get("url") if isinstance(s, dict) else "")
        title = s.get("title") if isinstance(s, dict) else url
        if url:
            recs.append(_rec("show", f"Cited public source: {title}.",
                             tier="analyst-reviewed", source_type="public_source", source_url=src(url)))

    return {"records": recs, "sources_seen": len(sources)}


def ingest_for_profile(profile) -> dict:
    """Persist extracted evidence (deduped) and return {created, skipped, sources_seen}."""
    from hikma.models import Evidence

    company = profile.company
    out = extract_evidence(profile)
    created = skipped = 0
    for r in out["records"]:
        h = _hash(company.slug, r["kind"], r["statement"])
        if Evidence.objects.filter(content_hash=h).exists():
            skipped += 1
            continue
        ev = Evidence.objects.create(
            company=profile, subject_type="company", subject_ref=company.slug,
            kind=r["kind"], statement=r["statement"],
            metric_name=r["metric_name"], metric_value=r["metric_value"], metric_unit=r["metric_unit"],
            source_type=r["source_type"], source_url=r["source_url"],
            confidence_tier=r["confidence_tier"], confidence_score=r["confidence_score"],
            content_hash=h, scholar_review_required=True,
        )
        from evidence_memory.services.memory import create_memory_from_hikma_evidence
        create_memory_from_hikma_evidence(ev)
        created += 1
    return {"created": created, "skipped": skipped, "sources_seen": out["sources_seen"]}
