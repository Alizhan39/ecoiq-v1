"""
company_intelligence/services/conflict_detection.py — feat/stewardship-
monitor (PR 14): conservative, deterministic POTENTIAL_CONFLICT detection.

CRITICAL RULE (the brief's own words): "The system may create
POTENTIAL_CONFLICT but only human review may confirm CONFLICTS." This
module NEVER sets CompanyKPIEvidenceLink.relationship to 'conflicts' and
NEVER changes review_state — it only ever creates a StewardshipChangeEvent
flagging a link for a human reviewer's attention, exactly the same
discipline kpi_candidate_matching.py already established for why
'conflicts' is never auto-proposed as a relationship in the first place.

Two conservative, explainable signals — never naive keyword-opposite
matching treated as authoritative:

1. REVERSAL SIGNAL — the newly-proposed evidence's own matched text
   contains an explicit reversal/discontinuation phrase (a real word
   choice the source document itself used, not an inferred antonym) while
   an existing CONFIRMED link for the same company+KPI currently supports
   it. This is "a previously supported KPI now has newly extracted
   contradictory evidence" / "a previously current policy is explicitly
   replaced" from Section 5's own examples.
2. NEWER-DOCUMENT CONTEXT-ONLY — the newly-proposed link is a CONTEXT_ONLY
   match (never asserts support on its own) for a KPI that already has a
   CONFIRMED 'supports' link, AND the new evidence comes from a strictly
   newer document than the confirmed evidence's own source. A newer report
   discussing the same topic without repeating the positive claim is
   worth a human's attention, never an automatic downgrade.
"""
from company_intelligence.models import StewardshipChangeEvent
from company_intelligence.services.evidence_quality import _harvester_evidence_for_memory

REVERSAL_SIGNAL_PHRASES = (
    'no longer', 'discontinued', 'ceased', 'abandoned', 'ended', 'terminated',
    'withdrawn', 'reversed', 'suspended', 'has not', 'did not', 'failed to',
    'no longer supports', 'previously committed',
)


def _contains_reversal_signal(text):
    lowered = (text or '').lower()
    return any(phrase in lowered for phrase in REVERSAL_SIGNAL_PHRASES)


def _document_recency_key(link):
    harvester_evidence = _harvester_evidence_for_memory(link.evidence)
    if harvester_evidence is None:
        return None
    if harvester_evidence.document_id:
        return harvester_evidence.document.retrieved_at
    return harvester_evidence.retrieved_at


def detect_potential_conflicts_for_refresh(company_profile, newly_created_links, refresh_run=None):
    """
    Inspects only the links CREATED THIS REFRESH (never re-scans the whole
    history — a conflict is flagged once, at the moment new evidence
    arrives that might contradict something already confirmed). Returns
    the list of StewardshipChangeEvent rows created.
    """
    events = []
    for link in newly_created_links:
        assessment = link.assessment
        existing_confirmed = list(
            assessment.evidence_links.filter(review_state='confirmed').exclude(pk=link.pk)
        )
        confirmed_supports = [l for l in existing_confirmed if l.relationship == 'supports']
        if not confirmed_supports:
            continue

        matched_text = link.evidence.text_chunk or ''
        reversal = _contains_reversal_signal(matched_text)

        newer_context_only = False
        if link.relationship == 'context':
            new_recency = _document_recency_key(link)
            for existing in confirmed_supports:
                existing_recency = _document_recency_key(existing)
                if new_recency and existing_recency and new_recency > existing_recency:
                    newer_context_only = True
                    break

        if not (reversal or newer_context_only):
            continue

        basis = (
            'the new evidence text uses an explicit discontinuation/reversal phrase' if reversal
            else 'the new evidence comes from a newer document than the currently confirmed supporting evidence, '
                 'discussing the same KPI without repeating the supporting claim'
        )
        event = StewardshipChangeEvent.objects.create(
            company=company_profile, event_type='potential_conflict', severity='high', review_required=True,
            evidence=link.evidence, kpi_evidence_link=link, refresh_run=refresh_run,
            summary=(
                f'KPI #{assessment.kpi_id}: newly proposed evidence may conflict with existing confirmed '
                f'supporting evidence — {basis}. Not automatically decided; requires human review.'
            ),
            previous_state='confirmed: supports', new_state=f'proposed: {link.relationship}',
        )
        events.append(event)
    return events
