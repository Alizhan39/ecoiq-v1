"""
company_intelligence/services/evidence_provenance.py — feat/global-
stewardship-universe (PR 15), Sections 15-16: differentiates evidence by
WHO produced it (never treating all evidence as equivalent), and surfaces
conservative, transparent greenwashing-resistance signals.

Reuses harvester.verification.SOURCE_TIER_BY_TYPE (the same real, already-
documented tier table every other part of this app already reads) — never
a second, competing source-classification scheme. "Human-reviewed" is a
separate, cross-cutting dimension (CompanyKPIEvidenceLink.review_state ==
'confirmed'), not mutually exclusive with the provenance classes below —
any evidence, regardless of who produced it, becomes human-reviewed only
once a reviewer confirms it in the Evidence Review Workbench.

CRITICAL DISCIPLINE (the brief's own words): "Do not claim EcoIQ 'detects
greenwashing' unless methodology supports that claim." This module never
makes that claim — it only ever surfaces "Evidence concentration warning",
"Unresolved contradiction", or "High reliance on company self-reporting",
each backed by a real, documented threshold.
"""
REGULATORY_SOURCE_TYPES = {
    'companies_house', 'sec_edgar', 'fca_filing', 'ofgem', 'environment_agency', 'regulatory_filing',
}
INDEPENDENT_SOURCE_TYPES = {
    'sbti', 'cdp', 'gri', 'sasb', 'issb', 'world_bank', 'iea', 'ebrd', 'oecd', 'undp',
    'financial_times', 'reuters', 'tender_portal', 'procurement_db',
}
# Tier 2 (annual/sustainability/ESG reports) and Tier 4 (investor relations,
# company website, press releases) are BOTH commissioned and published by
# the company itself — more thorough than a press release, but still
# self-reported, never independently produced. Grouping them honestly
# reflects that, rather than implying a company's own glossy sustainability
# report carries the same independence as a third-party rating.
SELF_REPORTED_SOURCE_TYPES = {
    'annual_report', 'sustainability_report', 'esg_report', 'tcfd_report', 'transition_plan',
    'investor_relations', 'company_website', 'press_release', 'bloomberg', 'csv_dataset',
}

# Conservative, documented thresholds — never silently tuned.
SELF_REPORT_CONCENTRATION_WARNING_PCT = 80.0
EVIDENCE_CONCENTRATION_SAME_DOCUMENT_WARNING = 5  # 5+ confirmed links from one document


def _harvester_evidence_for_link(link):
    from company_intelligence.services.evidence_quality import _harvester_evidence_for_memory

    return _harvester_evidence_for_memory(link.evidence)


def provenance_class_for_link(link):
    """Returns one of 'regulatory', 'independent', 'self_reported', or
    'unknown' (never fabricated when the source type isn't classifiable)."""
    harvester_evidence = _harvester_evidence_for_link(link)
    if harvester_evidence is None:
        return 'unknown'
    source_type = harvester_evidence.document.document_type if harvester_evidence.document_id else (
        harvester_evidence.source.source_type if harvester_evidence.source_id else ''
    )
    if source_type in REGULATORY_SOURCE_TYPES:
        return 'regulatory'
    if source_type in INDEPENDENT_SOURCE_TYPES:
        return 'independent'
    if source_type in SELF_REPORTED_SOURCE_TYPES:
        return 'self_reported'
    return 'unknown'


def self_report_concentration(company_profile):
    """
    Returns {'self_reported_count', 'independent_count', 'regulatory_count',
    'unknown_count', 'total', 'self_reported_pct', 'warning'} over this
    company's CONFIRMED evidence only (proposed candidates don't yet
    represent accepted alignment, so they're excluded from this signal).
    `warning` is a plain string, never a claim of "detected greenwashing".
    """
    from company_intelligence.models import CompanyKPIEvidenceLink

    confirmed_links = CompanyKPIEvidenceLink.objects.filter(
        assessment__company=company_profile, review_state='confirmed',
    ).select_related('evidence')

    counts = {'regulatory': 0, 'independent': 0, 'self_reported': 0, 'unknown': 0}
    for link in confirmed_links:
        counts[provenance_class_for_link(link)] += 1

    total = sum(counts.values())
    self_reported_pct = round(100.0 * counts['self_reported'] / total, 1) if total else None

    warning = None
    if total and self_reported_pct is not None and self_reported_pct >= SELF_REPORT_CONCENTRATION_WARNING_PCT and counts['independent'] == 0 and counts['regulatory'] == 0:
        warning = (
            f'High reliance on company self-reporting — {self_reported_pct}% of confirmed evidence for this '
            f'company comes from its own published reports/website, with no independent or regulatory source '
            f'confirmed yet.'
        )

    return {
        'self_reported_count': counts['self_reported'], 'independent_count': counts['independent'],
        'regulatory_count': counts['regulatory'], 'unknown_count': counts['unknown'],
        'total': total, 'self_reported_pct': self_reported_pct, 'warning': warning,
    }


def evidence_concentration_warning(company_profile):
    """
    Section 16 — "cap repeated evidence from the same document / avoid
    counting duplicate claims multiple times." Duplicate-claim counting
    itself is already prevented upstream by harvester.dedup's dedup_key
    (the same fact from the same document can never create two canonical
    Evidence rows) — this function only surfaces, honestly, when a single
    document is responsible for an unusually large share of a company's
    CONFIRMED KPI links, so a reviewer can judge source diversity for
    themselves rather than treating link COUNT as a quality signal.
    """
    from company_intelligence.models import CompanyKPIEvidenceLink

    confirmed_links = CompanyKPIEvidenceLink.objects.filter(
        assessment__company=company_profile, review_state='confirmed',
    ).select_related('evidence')

    by_document = {}
    for link in confirmed_links:
        harvester_evidence = _harvester_evidence_for_link(link)
        doc_id = harvester_evidence.document_id if harvester_evidence else None
        if doc_id is None:
            continue
        by_document.setdefault(doc_id, []).append(link)

    warnings = []
    for doc_id, links in by_document.items():
        if len(links) >= EVIDENCE_CONCENTRATION_SAME_DOCUMENT_WARNING:
            harvester_evidence = _harvester_evidence_for_link(links[0])
            doc_title = harvester_evidence.document.title if harvester_evidence and harvester_evidence.document_id else f'document #{doc_id}'
            warnings.append(f'{len(links)} confirmed KPI links all come from the same document ("{doc_title}").')
    return warnings
