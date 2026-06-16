"""
EcoIQ WHY Engine — explainability, read-only, evidence-derived (no new models,
no AI, no fabrication).

Produces a uniform WhyReport for any score/metric so a user can defend a decision
to a board / IC / regulator. Two honest modes:
  DERIVED  — a normalized company Datapoint: full lineage (source doc,
             verification, corroboration, timeline).
  SOURCED  — an external CountryProfile national indicator: EcoIQ did NOT compute
             it, so we expose provenance + evidence-coverage + confidence and say
             so plainly — never a fabricated "+X if fixed".

Every WhyReport answers Boardroom Mode's six questions.
"""
from __future__ import annotations

# expected company metrics (drives "evidence missing"); kept deliberately small
EXPECTED_METRICS = [
    ("revenue", "Revenue"), ("operating_profit", "Operating profit"),
    ("capex", "Capital investment"), ("scope1_emissions", "Scope 1 emissions"),
    ("scope2_emissions", "Scope 2 emissions"), ("scope3_emissions", "Scope 3 emissions"),
    ("employee_count", "Employees"),
]
METRIC_LABEL = dict(EXPECTED_METRICS)

# country indicator fields (SOURCED) → label
COUNTRY_SCORES = [
    ("national_ecoiq_index", "Overall (EcoIQ index)"),
    ("transition_readiness_score", "Transition readiness"),
    ("policy_environment_score", "Governance / policy"),
    ("investment_climate_score", "Investment climate"),
    ("transparency_score", "Transparency"),
    ("industrial_modernization_score", "Industrial modernisation"),
]


def _evidence_dict(e):
    ref = e.source_refs.first() if e.pk else None
    return {
        "title": e.title or (e.excerpt[:120] if e.excerpt else ""),
        "source_type": (e.source and e.source.source_type) or (ref and ref.source_type) or e.document_type or "",
        "source_owner": (e.source and e.source.source_owner) or (ref and ref.source_owner) or "",
        "url": e.url or (ref and ref.url) or "",
        "verification_status": e.verification_status,
        "confidence": round(e.confidence, 2),
        "publication_date": e.publication_date.isoformat() if e.publication_date else None,
    }


def _defendable(verification_status, has_value):
    if not has_value:
        return ("NOT_YET", "No — insufficient evidence on record to support this figure.")
    if verification_status == "VERIFIED":
        return ("YES", "Yes — independently corroborated and source-cited; defensible to an IC.")
    if verification_status == "PARTIAL":
        return ("WITH_CAVEATS", "With caveats — a single credible source, not yet independently corroborated; disclose that to the IC.")
    if verification_status == "CONTRADICTED":
        return ("NOT_YET", "No — sources disagree; resolve the contradiction before relying on it.")
    return ("NOT_YET", "Not yet — recorded but not independently verified.")


def _boardroom(value, unit, verification_status, confidence, evidence_used, evidence_missing, origin, defend_text):
    has = value is not None
    return {
        "1_trust": ("%.0f%% confidence, verification: %s" % ((confidence or 0) * 100, verification_status))
                   if has else "Insufficient evidence — do not rely on a value.",
        "2_origin": origin,
        "3_supports": ("%d source(s) on record" % len(evidence_used)) if evidence_used else "No supporting evidence on record.",
        "4_missing": ("%d gap(s): %s" % (len(evidence_missing), ", ".join(evidence_missing[:4]))) if evidence_missing else "No material gaps detected.",
        "5_improve": "Obtain independently-verified corroboration of the figure(s)." if verification_status != "VERIFIED" else "Maintain refresh cadence; figure is corroborated.",
        "6_defend": defend_text,
    }


# ── Company WHY (DERIVED — full lineage) ─────────────────────────────────────
def why_company(slug: str):
    from harvester.models import RegistryCompany, Evidence, Datapoint

    rc = RegistryCompany.objects.filter(slug=slug).first()
    name = rc.company_name if rc else slug.replace("-", " ").title()
    present = {}
    for d in Datapoint.objects.filter(company_slug=slug, status="NORMALIZED").order_by("metric", "period_year"):
        present.setdefault(d.metric, []).append(d)

    reports = []
    for metric, label in EXPECTED_METRICS:
        rows = present.get(metric, [])
        if rows:
            latest = rows[-1]
            ev = latest.evidence
            ev_used = [_evidence_dict(ev)] if ev else []
            vstatus = ev.verification_status if ev else "UNVERIFIED"
            conf = round(ev.confidence, 2) if ev else round(latest.confidence, 2)
            timeline = [{"period": r.period or (str(r.period_year) if r.period_year else ""), "value": r.value} for r in rows]
            verdict, defend = _defendable(vstatus, True)
            origin = "%s — %s" % (ev_used[0]["source_type"] or "company disclosure", ev_used[0]["source_owner"] or name) if ev_used else "company disclosure"
            reports.append({
                "metric_key": metric, "label": label, "value": latest.value, "unit": latest.unit,
                "period": latest.period, "score_type": "DERIVED",
                "confidence": conf, "confidence_basis": "source verification",
                "verification_status": vstatus,
                "evidence_used": ev_used, "evidence_missing": [],
                "timeline": timeline,
                "timeline_note": "" if len(timeline) > 1 else "single reported period",
                "methodology": "Deterministically normalized from the cited source document; verification by source quality, freshness and independent corroboration.",
                "improvement_path": ([] if vstatus == "VERIFIED" else ["Obtain an independent source (regulator/dataset) to corroborate and raise verification to VERIFIED."]),
                "boardroom": _boardroom(latest.value, latest.unit, vstatus, conf, ev_used, [], origin, defend),
                "defendable": verdict,
            })
        else:
            verdict, defend = _defendable("NOT_FOUND", False)
            reports.append({
                "metric_key": metric, "label": label, "value": None, "unit": "",
                "period": "", "score_type": "DERIVED",
                "confidence": None, "confidence_basis": "no evidence",
                "verification_status": "NOT_FOUND",
                "evidence_used": [], "evidence_missing": [label + " not disclosed / not yet harvested"],
                "timeline": [], "timeline_note": "no data",
                "methodology": "No source document with this metric is on record.",
                "improvement_path": ["Register and harvest a verified source disclosing " + label + "."],
                "boardroom": _boardroom(None, "", "NOT_FOUND", None, [], [label + " missing"], "no source on record", defend),
                "defendable": verdict,
            })

    covered = sum(1 for r in reports if r["value"] is not None)
    return {
        "subject_type": "company", "slug": slug, "name": name,
        "summary": {
            "metrics_total": len(reports), "metrics_covered": covered,
            "evidence": Evidence.objects.filter(company_slug=slug).count(),
            "verified_metrics": sum(1 for r in reports if r["verification_status"] == "VERIFIED"),
        },
        "reports": reports,
        "disclaimer": ("Read-only, evidence-derived. Each figure is normalized from a cited source "
                       "with a verification status. Metrics with no source show 'insufficient evidence' "
                       "— never an estimated value."),
    }


# ── Country WHY (SOURCED — provenance + coverage, no fabricated deltas) ───────
def why_country(slug: str):
    from countries.models import CountryProfile
    from countries.intelligence import country_intelligence
    from harvester.models import Evidence

    cp = CountryProfile.objects.filter(slug=slug).first()
    if cp is None:
        return None
    intel = country_intelligence(cp)
    slugs = [c["slug"] for c in intel["companies"]]
    total_ev = Evidence.objects.filter(company_slug__in=slugs).count() if slugs else 0
    verified_ev = Evidence.objects.filter(company_slug__in=slugs, verification_status="VERIFIED").count() if slugs else 0
    coverage_conf = round(verified_ev / total_ev, 2) if total_ev else 0.0

    cats = set(Evidence.objects.filter(company_slug__in=slugs).values_list("category", flat=True)) if slugs else set()
    coverage = [
        ("Financial reporting", "financial" in cats or "capital_projects" in cats),
        ("Emissions disclosure", "emissions" in cats),
        ("Governance / ownership", bool({"governance", "board", "ownership"} & cats)),
        ("Climate / transition", "climate" in cats),
        ("Independent verification", verified_ev > 0),
    ]
    missing = [lab for lab, ok in coverage if not ok]
    src = intel.get("data_sources") or "EcoIQ national indicators"

    reports = []
    for field, label in COUNTRY_SCORES:
        v = getattr(cp, field, None)
        if v in (None, 0, 0.0):
            v = None
        origin = "Externally-sourced national indicator (%s)" % src
        # SOURCED scores are not EcoIQ-computed → defensibility is about provenance + coverage
        if v is None:
            verdict, defend = "NOT_YET", "No — EcoIQ has no value for this indicator."
        elif coverage_conf >= 0.5:
            verdict, defend = "WITH_CAVEATS", "Defensible as a cited external indicator; EcoIQ-verified company evidence is partial — present both."
        else:
            verdict, defend = "WITH_CAVEATS", "Use as cited external context only — EcoIQ has thin verified company evidence for this market; disclose that to the IC."
        reports.append({
            "metric_key": field, "label": label, "value": v, "unit": "",
            "period": "", "score_type": "SOURCED",
            "confidence": coverage_conf, "confidence_basis": "EcoIQ company-evidence verification coverage (the indicator itself is external)",
            "verification_status": "VERIFIED" if coverage_conf >= 0.5 else ("PARTIAL" if total_ev else "INSUFFICIENT_EVIDENCE"),
            "evidence_used": [{"title": "National indicator (external)", "source_type": "national_dataset", "source_owner": src, "url": "", "verification_status": "EXTERNAL", "confidence": None, "publication_date": None}],
            "evidence_missing": [m + " (no verified company evidence yet)" for m in missing],
            "timeline": [], "timeline_note": "point-in-time national indicator — time series unavailable",
            "methodology": "Externally-sourced national indicator. EcoIQ does NOT recompute this value; confidence reflects how much verified company-level evidence EcoIQ holds for the market.",
            "improvement_path": (["Harvest verified company evidence to close gaps: " + ", ".join(missing[:4])] if missing else ["Maintain evidence refresh cadence."]),
            "boardroom": _boardroom(v, "", "VERIFIED" if coverage_conf >= 0.5 else "PARTIAL", coverage_conf,
                                    [1], missing, origin, defend),
            "defendable": verdict,
        })

    return {
        "subject_type": "country", "slug": slug, "name": cp.name,
        "summary": {
            "companies": intel["companies_count"], "evidence": total_ev,
            "verified_coverage_pct": round(coverage_conf * 100, 1),
            "indicators": len(reports),
        },
        "coverage": [{"label": lab, "ok": ok} for lab, ok in coverage],
        "reports": reports,
        "disclaimer": ("National indicators are externally sourced and cited; EcoIQ does not recompute "
                       "them. Company evidence is EcoIQ-derived and verification-graded. Where verified "
                       "evidence is thin, this is stated — nothing is fabricated."),
    }
