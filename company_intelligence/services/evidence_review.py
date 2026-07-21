"""
company_intelligence/services/evidence_review.py — feat/evidence-review-
workbench (PR 12): the ONE place a CompanyKPIEvidenceLink's review_state
and relationship are ever mutated. Both the pre-existing company-scoped
review view (companies/<slug>/evidence-review/, PR 10) and the new
Evidence Review Workbench call apply_review_decision() — no duplicated
state-mutation logic between them.

Governance rule (the brief's own words): "the system that proposes a KPI
match must never silently confirm its own proposal." Every mutation here
requires an explicit, named human action; there is no code path that moves
a link to 'confirmed' without a reviewer argument recording who did it.
"""
from company_intelligence.services import evidence_quality, kpi_engine
from company_intelligence.services.evidence_quality import _harvester_evidence_for_memory
from core.esg_principles_data import PRINCIPLES

PRINCIPLES_BY_ID = {p['id']: p for p in PRINCIPLES}

# action -> (new review_state, new relationship or None if unchanged).
# The four confirm_* actions are the ONLY ones that assert a relationship;
# reject/needs_more_evidence/mark_disputed only move review_state, keeping
# MATCH VALIDITY (should this link exist at all right now) separate from
# EVIDENCE RELATIONSHIP (what the evidence concludes, once confirmed).
ACTION_TRANSITIONS = {
    'confirm_supports': ('confirmed', 'supports'),
    'confirm_conflicts': ('confirmed', 'conflicts'),
    'confirm_context': ('confirmed', 'context'),
    'confirm_insufficient': ('confirmed', 'insufficient_to_conclude'),
    'reject': ('rejected', None),
    'needs_more_evidence': ('needs_more_evidence', None),
    'mark_disputed': ('disputed', None),
}

DEFAULT_QUEUE_STATES = {'proposed', 'needs_more_evidence', 'disputed'}


def apply_review_decision(link, action, reviewer, reason=''):
    """
    The one real state-mutation path for a CompanyKPIEvidenceLink review
    decision. Always creates an immutable EvidenceReviewAction row (never
    edited/overwritten) and always recomputes the affected
    CompanyKPIAssessment through the existing, unmodified kpi_engine — never
    a hardcoded status flip. Works identically whether this is a link's
    first review or a re-review of an already-confirmed/disputed link.
    """
    from company_intelligence.models import EvidenceReviewAction

    if action not in ACTION_TRANSITIONS:
        raise ValueError(f'Unknown review action: {action}')
    new_state, new_relationship = ACTION_TRANSITIONS[action]
    previous_state = link.review_state

    EvidenceReviewAction.objects.create(
        kpi_evidence_link=link, evidence=link.evidence, action=action, reviewer=reviewer, reason=reason,
        previous_review_state=previous_state, new_review_state=new_state,
        relationship_decision=new_relationship or '',
    )

    link.review_state = new_state
    update_fields = ['review_state']
    if new_relationship:
        link.relationship = new_relationship
        update_fields.append('relationship')
    link.save(update_fields=update_fields)

    kpi_engine.recompute_assessment_status(link.assessment)
    return link


def _source_tier_for_link(link):
    """Real tier (1 highest authority) from the harvester Evidence backing
    this link, or None when this link isn't harvester-backed (e.g. a PR9
    demo fixture) — never a guessed default."""
    from harvester.verification import source_tier as tier_for_type

    harvester_evidence = _harvester_evidence_for_memory(link.evidence)
    if harvester_evidence is None:
        return None
    if harvester_evidence.document_id:
        return harvester_evidence.document.source_tier
    if harvester_evidence.source_id:
        return tier_for_type(harvester_evidence.source.source_type)
    return None


def evidence_freshness_info(link):
    """
    Real, evidence-level freshness (distinct from company_intelligence.
    services.freshness's SCREENING freshness) — publication_date/
    freshness_score already computed by harvester.verification for any
    harvester-backed evidence. Honestly None for non-harvester-backed rows
    (e.g. PR9 demo fixtures), never a fabricated recency claim.
    """
    harvester_evidence = _harvester_evidence_for_memory(link.evidence)
    if harvester_evidence is None:
        return {'has_harvester_record': False, 'publication_date': None, 'freshness_score': None, 'retrieved_at': None}
    return {
        'has_harvester_record': True,
        'publication_date': harvester_evidence.publication_date,
        'freshness_score': harvester_evidence.freshness_score,
        'retrieved_at': harvester_evidence.retrieved_at,
    }


def _proposed_by(link):
    """Honest provenance: a manually-added link always has added_by set (a
    human created it directly); a matcher-proposed link has match_basis set
    and no added_by. Never invents a fabricated 'AI-assisted' provenance —
    this codebase's matcher is deterministic keyword-overlap, not an LLM
    (see kpi_candidate_matching.py's own docstring)."""
    if link.added_by_id:
        return f'Manual entry — {link.added_by}'
    if link.match_basis:
        return 'Deterministic candidate matcher'
    return 'Unknown / import'


def appearance_context(link):
    """
    feat/stewardship-monitor (PR 14) — "why did this appear?" Reuses the
    link's own `proposed_via_refresh_run` FK (set at creation time by
    kpi_candidate_matching.propose_kpi_links_for_evidence, never rewritten
    afterward) and any StewardshipChangeEvent flagging this exact link as
    a potential conflict — never a second, duplicated provenance record.
    """
    from company_intelligence.models import StewardshipChangeEvent

    run = link.proposed_via_refresh_run
    potential_conflict = StewardshipChangeEvent.objects.filter(
        kpi_evidence_link=link, event_type='potential_conflict',
    ).order_by('-detected_at').first()
    return {
        'proposed_via_refresh_run': run,
        'refresh_run_label': (
            f'Proposed during refresh run #{run.pk} ({run.get_triggered_by_display()}) on '
            f'{run.started_at:%Y-%m-%d}' if run else None
        ),
        'potential_conflict_event': potential_conflict,
    }


def duplicate_links_for(link):
    """
    Other CompanyKPIEvidenceLink rows a reviewer would otherwise waste time
    re-reviewing: same evidence chunk linked to the same KPI for a DIFFERENT
    assessment (shouldn't normally happen — assessment is per company+kpi,
    so this only fires if the same evidence somehow got linked twice), and
    — more commonly — other links for the SAME assessment backed by
    evidence from the same source document (a report often produces several
    chunks that all point at one KPI). Never merges them; only surfaces the
    relationship so a reviewer can see it before deciding.
    """
    from company_intelligence.models import CompanyKPIEvidenceLink

    same_evidence = CompanyKPIEvidenceLink.objects.filter(evidence=link.evidence).exclude(pk=link.pk)

    same_doc_same_kpi = CompanyKPIEvidenceLink.objects.none()
    harvester_evidence = _harvester_evidence_for_memory(link.evidence)
    if harvester_evidence is not None and harvester_evidence.document_id:
        from evidence_memory.models import EvidenceMemory
        from harvester.models import Evidence as HarvesterEvidence

        sibling_pks = HarvesterEvidence.objects.filter(
            document_id=harvester_evidence.document_id,
        ).exclude(pk=harvester_evidence.pk).values_list('pk', flat=True)
        sibling_memory_ids = EvidenceMemory.objects.filter(
            source_type='harvester_evidence',
            source_reference__in=[f'harvester.Evidence:{pk}' for pk in sibling_pks],
        ).values_list('pk', flat=True)
        same_doc_same_kpi = CompanyKPIEvidenceLink.objects.filter(
            assessment=link.assessment, evidence_id__in=sibling_memory_ids,
        ).exclude(pk=link.pk)

    return {
        'same_evidence_different_kpi': list(same_evidence.select_related('assessment')),
        'same_document_same_kpi': list(same_doc_same_kpi.select_related('evidence')),
    }


def _priority_components(link, watchlisted_company_ids):
    """
    Deterministic, documented priority indicators — never an opaque model
    score. Each is a real boolean fact about this link/company, shown
    alongside the total so nothing is hidden behind one number.
    """
    assessment = link.assessment
    company = assessment.company
    tier = _source_tier_for_link(link)
    quality = evidence_quality.evidence_quality_for_memory(link.evidence)

    conflicting_exists = company.kpi_assessments.filter(
        kpi_id=assessment.kpi_id, evidence_links__relationship='conflicts', evidence_links__review_state='confirmed',
    ).exists()
    corroborating_count = link.assessment.evidence_links.filter(
        evidence=link.evidence,
    ).count()

    components = {
        'conflict_present': bool(conflicting_exists),
        'high_authority_source': tier is not None and tier <= 2,
        'fresh_evidence': bool(quality.get('recency') and quality['recency'] >= 0.7),
        'kpi_currently_unresolved': assessment.status in ('not_assessed', 'insufficient_evidence'),
        'on_research_watchlist': company_id_in(company.pk, watchlisted_company_ids),
        'corroborated': corroborating_count > 1,
    }
    return components, sum(1 for v in components.values() if v)


def company_id_in(company_id, id_set):
    return company_id in id_set


def pending_review_queue(criteria=None):
    """
    Returns a list of dicts (one per CompanyKPIEvidenceLink row) — never a
    bare queryset, since every row needs its resolved harvester provenance,
    priority components, and duplicate-candidate flag computed once here
    rather than repeated ad hoc in a template. Sorted by priority
    (descending) then age (oldest first) — "oldest high-value unresolved
    items first," with every component shown, never an opaque score.
    """
    from company_intelligence.models import CompanyKPIEvidenceLink, ResearchWatchlistEntry

    criteria = criteria or {}
    review_states = set(criteria.get('review_states') or DEFAULT_QUEUE_STATES)
    qs = CompanyKPIEvidenceLink.objects.filter(review_state__in=review_states).select_related(
        'assessment', 'assessment__company', 'assessment__company__company', 'evidence',
    )

    company_slug = criteria.get('company_slug')
    if company_slug:
        qs = qs.filter(assessment__company__company__slug=company_slug)
    kpi_id = criteria.get('kpi_id')
    if kpi_id:
        qs = qs.filter(assessment__kpi_id=kpi_id)
    relationship = criteria.get('relationship')
    if relationship:
        qs = qs.filter(relationship=relationship)
    date_from = criteria.get('date_from')
    if date_from:
        qs = qs.filter(added_at__gte=date_from)
    date_to = criteria.get('date_to')
    if date_to:
        qs = qs.filter(added_at__lte=date_to)

    kpi_category = criteria.get('kpi_category')
    min_source_tier = criteria.get('min_source_tier')

    watchlisted_company_ids = set(
        ResearchWatchlistEntry.objects.values_list('company_id', flat=True).distinct()
    )

    rows = []
    for link in qs:
        principle = PRINCIPLES_BY_ID.get(link.assessment.kpi_id, {})
        if kpi_category and principle.get('category') != kpi_category:
            continue
        tier = _source_tier_for_link(link)
        if min_source_tier is not None and (tier is None or tier > min_source_tier):
            continue

        quality = evidence_quality.evidence_quality_for_memory(link.evidence)
        components, score = _priority_components(link, watchlisted_company_ids)

        rows.append({
            'link': link,
            'company': link.assessment.company,
            'kpi_id': link.assessment.kpi_id,
            'kpi_title': principle.get('title', f'KPI #{link.assessment.kpi_id}'),
            'kpi_category': principle.get('category', ''),
            'source_tier': tier,
            'evidence_quality': quality,
            'evidence_freshness': evidence_freshness_info(link),
            'proposed_by': _proposed_by(link),
            'priority_components': components,
            'priority_score': score,
            'on_watchlist': components['on_research_watchlist'],
            'appearance': appearance_context(link),
        })

    rows.sort(key=lambda r: (-r['priority_score'], r['link'].added_at))
    return rows


CONTEXT_CHARS = 300


def evidence_context(link):
    """
    Splits the harvester Evidence's full page/section text around the
    exact matched statement into MATCHED EVIDENCE / preceding / following
    context — never fabricated when unavailable (e.g. a single-fact SEC
    EDGAR statement has no natural surrounding prose, or the matched text
    couldn't be located inside the stored full_text).
    """
    harvester_evidence = _harvester_evidence_for_memory(link.evidence)
    matched_text = link.evidence.text_chunk
    if harvester_evidence is None or not harvester_evidence.full_text:
        return {'has_context': False, 'matched_text': matched_text, 'preceding': '', 'following': ''}

    full_text = harvester_evidence.full_text
    probe = matched_text[:120].strip()
    idx = full_text.find(probe) if probe else -1
    if idx == -1:
        return {'has_context': False, 'matched_text': matched_text, 'preceding': '', 'following': ''}

    preceding = full_text[max(0, idx - CONTEXT_CHARS):idx].strip()
    end_idx = idx + len(matched_text)
    following = full_text[end_idx:end_idx + CONTEXT_CHARS].strip()
    return {'has_context': bool(preceding or following), 'matched_text': matched_text, 'preceding': preceding, 'following': following}


def source_provenance(link):
    """
    Every field the brief's section 6 requires, honestly None for whichever
    aren't available for this evidence's actual source type — never
    silently treated as verified when inaccessible.
    """
    harvester_evidence = _harvester_evidence_for_memory(link.evidence)
    if harvester_evidence is None:
        return {'has_harvester_record': False}

    document = harvester_evidence.document
    source = harvester_evidence.source
    return {
        'has_harvester_record': True,
        'publisher': document.publisher if document else (source.source_owner if source else ''),
        'document_title': document.title if document else harvester_evidence.title,
        'document_type': document.get_document_type_display() if document else (source.get_source_type_display() if source else ''),
        'source_url': harvester_evidence.url,
        'source_tier': _source_tier_for_link(link),
        'publication_date': harvester_evidence.publication_date,
        'reporting_period': document.reporting_period if document else '',
        'retrieved_at': harvester_evidence.retrieved_at,
        'content_hash': harvester_evidence.content_hash,
        'source_location': harvester_evidence.source_location,
        'verification_state': harvester_evidence.get_verification_status_display(),
        'is_stale': (
            harvester_evidence.freshness_score is not None and harvester_evidence.freshness_score < 0.3
        ),
    }


def kpi_context(link):
    """Existing confirmed supporting/conflicting evidence for this same
    company+KPI, and the current assessment status — so a reviewer sees
    the full picture before deciding, never just the one candidate in
    isolation."""
    assessment = link.assessment
    existing_links = assessment.evidence_links.filter(review_state='confirmed').exclude(pk=link.pk).select_related('evidence')
    return {
        'principle': PRINCIPLES_BY_ID.get(assessment.kpi_id, {}),
        'current_status': assessment.status,
        'current_status_display': assessment.get_status_display(),
        'supporting': [l for l in existing_links if l.relationship == 'supports'],
        'conflicting': [l for l in existing_links if l.relationship == 'conflicts'],
        'other_confirmed': [l for l in existing_links if l.relationship not in ('supports', 'conflicts')],
    }


def review_history(link):
    """Full immutable audit trail for this link, oldest first (chronological
    reading order) — never edited or collapsed."""
    return list(link.review_actions.select_related('reviewer').order_by('created_at'))


def review_analytics():
    """
    Workflow analytics only — never a sustainability/investment score. Real
    counts by review_state, plus median/oldest unresolved age, by source
    tier and by KPI category, all computed live from stored rows.
    """
    import statistics

    from django.utils import timezone

    from company_intelligence.models import CompanyKPIEvidenceLink

    all_links = CompanyKPIEvidenceLink.objects.select_related('assessment', 'evidence').all()
    counts = {state: 0 for state, _ in CompanyKPIEvidenceLink.REVIEW_STATE_CHOICES}
    for link in all_links:
        counts[link.review_state] = counts.get(link.review_state, 0) + 1

    now = timezone.now()
    unresolved = [l for l in all_links if l.review_state in DEFAULT_QUEUE_STATES]
    ages_days = [(now - l.added_at).days for l in unresolved]

    reviewed_today = CompanyKPIEvidenceLink.objects.filter(
        review_state__in=('confirmed', 'rejected'), added_at__date=now.date(),
    ).count()

    by_tier = {}
    by_category = {}
    for link in unresolved:
        tier = _source_tier_for_link(link)
        by_tier[tier] = by_tier.get(tier, 0) + 1
        principle = PRINCIPLES_BY_ID.get(link.assessment.kpi_id, {})
        cat = principle.get('category', 'unknown')
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        'counts': counts,
        'reviewed_today': reviewed_today,
        'median_unresolved_age_days': round(statistics.median(ages_days), 1) if ages_days else None,
        'oldest_unresolved_age_days': max(ages_days) if ages_days else None,
        'unresolved_total': len(unresolved),
        'by_source_tier': by_tier,
        'by_kpi_category': by_category,
    }
