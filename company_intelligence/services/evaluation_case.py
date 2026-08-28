"""
company_intelligence/services/evaluation_case.py — turning real review work into
material a benchmark could one day be built from.

WHY THIS SHAPE
--------------
`platform_registry/evaluation.py` argues, correctly, that a harness filled with
generated examples produces impressive numbers measuring nothing. The way out of
that is not a better generator. It is a labelled set that came from people doing
the work anyway.

Every confirmed evidence link is already a human judgement about a specific piece
of text, made by a named person, with a recorded rationale. That is the shape of
an evaluation case. This module reads those records and presents them as one —
without inventing a label, and without deciding that any of them belongs in a
benchmark.

CANDIDATE, NOT CASE
-------------------
Nothing here publishes anything. `is_benchmark_ready` reports whether a review
carries what a case needs; it never promotes. Curating "EcoIQ Evidence Evaluation
Set v1" is a human act for the same reason confirming evidence is: a set assembled
by whatever passed a filter is a set nobody vouched for.

The counterpart to that discipline is `platform_registry.evaluation.NOT_MEASURED`.
A metric with no measurement says NOT YET MEASURED; a review with no usable case
says so too, rather than being quietly dropped from a count.

THE VERSION IS THE POINT
------------------------
A case is (input, label, provenance), and the input is a specific text. If the
source is re-fetched and changes, a case built from the review would pair a
human's judgement with text they never read — a labelled example that is quietly
wrong, which is worse in a benchmark than a missing one.

`EvidenceReviewAction.evidence_version` pins the hash at review time.
`version_status` compares it to the text now, so a stale case is detectable
rather than silently mislabelled.
"""
from __future__ import annotations

from company_intelligence.services.source_provenance import provenance_for_memory

#: A review made before evidence_version existed. Honestly unknown — never
#: backfilled with a hash computed today, which would assert something about the
#: past that nobody recorded.
VERSION_UNKNOWN = 'UNKNOWN'
#: The text is byte-identical to what the reviewer saw.
VERSION_MATCHES = 'MATCHES'
#: The text has changed since. The label may no longer describe it.
VERSION_DRIFTED = 'DRIFTED'

#: Review actions that record a positive classification. Rejection and the
#: holding states are real decisions but they are not labels ABOUT the evidence's
#: relationship to the principle, which is what a case needs.
LABELLING_ACTIONS = {
    'confirm_supports': 'supports',
    'confirm_conflicts': 'conflicts',
    'confirm_context': 'context',
    'confirm_insufficient': 'insufficient_to_conclude',
}


def version_status(action) -> str:
    """Does the evidence still say what it said when this review was made?"""
    recorded = (action.evidence_version or '').strip()
    if not recorded:
        return VERSION_UNKNOWN
    current = (getattr(action.evidence, 'integrity_reference', '') or '').strip()
    if not current:
        return VERSION_UNKNOWN
    return VERSION_MATCHES if recorded == current else VERSION_DRIFTED


def case_from_review(action) -> dict:
    """
    One review action, expressed as an evaluation case candidate.

    Returns the three parts a case needs — input, human ground truth, and
    provenance — plus an explicit statement of whether it is usable. Never
    fabricates a label: a review that did not classify the evidence produces a
    candidate with `label=None` and a reason, not a guess.
    """
    from core.esg_principles_data import PRINCIPLES

    link = action.kpi_evidence_link
    principle = {}
    if link is not None:
        principle = next(
            (p for p in PRINCIPLES if p['id'] == link.assessment.kpi_id), {})

    provenance = provenance_for_memory(action.evidence)
    label = LABELLING_ACTIONS.get(action.action)
    status = version_status(action)

    blockers = []
    if label is None:
        blockers.append(
            f'The action recorded was {action.action!r}, which is a decision '
            'about the link rather than a classification of the evidence.')
    if status == VERSION_DRIFTED:
        blockers.append(
            'The evidence text has changed since this review, so the label may '
            'no longer describe what it labels.')
    if status == VERSION_UNKNOWN:
        blockers.append(
            'No evidence version was recorded, so it cannot be shown that the '
            'text is the one the reviewer read.')
    if not (action.reason or '').strip():
        blockers.append(
            'No rationale was recorded, so the case carries a label without the '
            'reasoning that would let anyone check it.')

    return {
        'review_action_id': action.pk,
        'input': {
            'principle_id': principle.get('id'),
            'principle_title': principle.get('title'),
            'question': principle.get('question'),
            'entity': (link.assessment.company.company.slug
                       if link is not None else None),
            'evidence_text': action.evidence.text_chunk,
            'source': {
                'title': provenance['title'],
                'publisher': provenance['publisher'],
                'url': provenance['url'],
                'authority': provenance['authority'],
                'publication_date': provenance['publication_date'],
            },
        },
        'ground_truth': {
            'label': label,
            'action': action.action,
            'rationale': action.reason or None,
        },
        'provenance': {
            'reviewer': getattr(action.reviewer, 'username', None),
            'reviewed_at': action.created_at.isoformat() if action.created_at else None,
            'previous_review_state': action.previous_review_state or None,
            'new_review_state': action.new_review_state or None,
            'evidence_version': action.evidence_version or None,
            'version_status': status,
        },
        # Reports readiness. Never promotes: curating a set is a human act.
        'is_benchmark_ready': not blockers,
        'blockers': blockers,
    }


def candidates(actions) -> list[dict]:
    """Every review action as a case candidate, usable or not."""
    return [case_from_review(action) for action in actions]


def corpus_summary(actions) -> dict:
    """
    What a labelled set built from this review work would currently amount to.

    Reports zero as zero. A corpus of nothing is a real measurement and the
    honest answer while the review queue is untouched — it is not the same as
    NOT YET MEASURED, which is what a metric nobody has run says.
    """
    cases = candidates(actions)
    ready = [c for c in cases if c['is_benchmark_ready']]
    by_label: dict[str, int] = {}
    for case in ready:
        label = case['ground_truth']['label']
        by_label[label] = by_label.get(label, 0) + 1
    return {
        'reviews_examined': len(cases),
        'benchmark_ready': len(ready),
        'not_ready': len(cases) - len(ready),
        'labels': by_label,
        'reviewers': sorted({c['provenance']['reviewer'] for c in ready
                             if c['provenance']['reviewer']}),
        'drifted': sum(1 for c in cases
                       if c['provenance']['version_status'] == VERSION_DRIFTED),
        'version_unknown': sum(1 for c in cases
                               if c['provenance']['version_status'] == VERSION_UNKNOWN),
        # Stated rather than implied. Nothing in this repository turns these
        # candidates into a published benchmark.
        'published_as_benchmark': False,
        'note': ('Candidates only. Curating a labelled set is a human act, for '
                 'the same reason confirming evidence is.'),
    }
