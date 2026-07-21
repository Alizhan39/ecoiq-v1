"""
company_intelligence/services/review_trace.py — feat/evidence-review-
workbench (PR 12): "Explain Review Decision" — traces one
CompanyKPIEvidenceLink from its original source document all the way
through to its effect (or lack of one) on the company's KPI assessment and
Discovery results. Reuses capital_guardian.services.decision_trace.TraceNode
verbatim (same convention as company_trace.py/match_trace.py). Computes
nothing new — every value comes from already-stored records via
services/evidence_review.py.
"""
from dataclasses import dataclass, field

from capital_guardian.services.decision_trace import NOT_AVAILABLE, TraceNode

from company_intelligence.services import evidence_review


@dataclass
class ReviewDecisionTrace:
    link: object
    nodes: list = field(default_factory=list)


def explain_review_decision(link):
    """
    Nodes: Source -> Document -> Evidence Chunk -> Candidate Matcher ->
    Proposed KPI -> Human Reviewer -> Decision -> Company KPI Assessment
    Impact -> Discovery Impact. Every value read from stored records —
    no invented prose.
    """
    provenance = evidence_review.source_provenance(link)
    history = evidence_review.review_history(link)
    kpi_ctx = evidence_review.kpi_context(link)
    nodes = []

    # ---- 1. Source ------------------------------------------------------------
    if provenance.get('has_harvester_record'):
        nodes.append(TraceNode(
            stage='source', title='Source', status=provenance['publisher'] or 'Unknown publisher',
            status_kind='measured',
            summary=f"{provenance['document_type'] or 'Unclassified source type'} — tier "
                    f"{provenance['source_tier'] if provenance['source_tier'] is not None else 'unknown'}.",
            source_url=provenance['source_url'] or None, source_label='View original source →' if provenance['source_url'] else '',
            data_quality=['measured'],
        ))
    else:
        nodes.append(TraceNode(
            stage='source', title='Source', status='Not Harvester-Backed',
            status_kind='missing', summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 2. Document ------------------------------------------------------------
    if provenance.get('has_harvester_record'):
        nodes.append(TraceNode(
            stage='document', title='Document', status=provenance['document_title'] or 'Untitled',
            status_kind='measured',
            summary=(
                f"Published {provenance['publication_date'] or 'date unknown'}. "
                f"Retrieved {provenance['retrieved_at'].date() if provenance['retrieved_at'] else 'unknown'}. "
                f"Location: {provenance['source_location'] or 'not recorded'}. "
                f"Content hash: {provenance['content_hash'][:12] + '…' if provenance['content_hash'] else 'none'}."
            ),
            data_quality=['demo'] if provenance.get('is_stale') else ['measured'],
            extra={'provenance': provenance},
        ))
    else:
        nodes.append(TraceNode(
            stage='document', title='Document', status='Not Available',
            status_kind='missing', summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 3. Evidence Chunk --------------------------------------------------------
    nodes.append(TraceNode(
        stage='evidence_chunk', title='Evidence Chunk', status=link.evidence.get_verification_status_display(),
        status_kind='verified' if link.evidence.verification_status == 'verified' else 'measured',
        summary=link.evidence.text_chunk[:300] + ('…' if len(link.evidence.text_chunk) > 300 else ''),
        data_quality=['demo'] if link.evidence.is_demo else ['measured'],
    ))

    # ---- 4. Candidate Matcher --------------------------------------------------------
    nodes.append(TraceNode(
        stage='candidate_matcher', title='Candidate Matcher', status=evidence_review._proposed_by(link),
        status_kind='deterministic',
        summary=(
            f"Match basis: {link.match_basis}" if link.match_basis
            else 'This link was created directly by a human reviewer, not proposed by the matcher.'
        ),
        data_quality=['deterministic'],
    ))

    # ---- 5. Proposed KPI --------------------------------------------------------
    principle = kpi_ctx['principle']
    nodes.append(TraceNode(
        stage='proposed_kpi', title='Proposed KPI', status=f"#{link.assessment.kpi_id} {principle.get('title', '')}",
        status_kind='measured',
        summary=f"Proposed relationship: {link.get_relationship_display()}. {principle.get('tagline', '')}",
        data_quality=['measured'],
    ))

    # ---- 6. Human Reviewer / 7. Decision (one node per history entry, oldest first) ---
    if history:
        for action in history:
            nodes.append(TraceNode(
                stage='review_decision', title='Human Reviewer Decision',
                status=action.get_action_display(),
                status_kind=(
                    'blocked' if action.new_review_state == 'rejected' else
                    'disputed' if action.new_review_state == 'disputed' else
                    'verified' if action.new_review_state == 'confirmed' else 'estimated'
                ),
                summary=(
                    f"{action.reviewer} moved this link from '{action.previous_review_state or 'none'}' to "
                    f"'{action.new_review_state}'"
                    + (f" (relationship: {action.relationship_decision})" if action.relationship_decision else '')
                    + f". Reason: {action.reason or 'No reason recorded.'}"
                ),
                timestamp=action.created_at,
                data_quality=['human_approved'],
            ))
    else:
        nodes.append(TraceNode(
            stage='review_decision', title='Human Reviewer Decision', status='Awaiting First Review',
            status_kind='missing', summary='No review action has been recorded for this link yet.', available=False,
        ))

    # ---- 8. Company KPI Assessment Impact --------------------------------------------
    counts_toward_status = link.review_state == 'confirmed'
    nodes.append(TraceNode(
        stage='assessment_impact', title='Company KPI Assessment Impact',
        status=kpi_ctx['current_status_display'],
        status_kind='verified' if counts_toward_status else 'missing',
        summary=(
            f"This link is currently '{link.get_review_state_display()}' — "
            + ('it DOES count toward the assessment above.' if counts_toward_status
               else 'it does NOT count toward the assessment above (only confirmed links do).')
        ),
        data_quality=['deterministic'],
    ))

    # ---- 9. Discovery Impact --------------------------------------------------------
    nodes.append(TraceNode(
        stage='discovery_impact', title='Discovery Impact',
        status='Included in ranking' if counts_toward_status else 'Excluded from ranking',
        status_kind='verified' if counts_toward_status else 'missing',
        summary=(
            "Confirmed evidence like this contributes to this company's kpi_alignment ranking component in "
            "Discover Companies and Explain Match." if counts_toward_status else
            "Only confirmed evidence contributes to Discover Companies' ranking — this link, in its current "
            "state, has no effect on the company's discovery ranking or KPI coverage counts."
        ),
        data_quality=['deterministic'],
    ))

    return ReviewDecisionTrace(link=link, nodes=nodes)
