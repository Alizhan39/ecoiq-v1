"""
company_intelligence/services/review_recommendation.py — what the deterministic
pipeline can defensibly suggest to a reviewer, and what it must refuse to.

WHAT THIS IS FOR
----------------
The review queue asks a person to classify each proposed evidence link. That is
faster and safer when the system says what it already knows. It becomes
dangerous the moment the system says something it does not know, because a
recommendation sitting beside a decision field is an anchor whether or not
anyone intends it as one.

THE LINE THIS DRAWS
-------------------
`kpi_candidate_matching` proposes links on keyword overlap, and it already
records `relationship='context'` for every one of them — never `supports`, never
`conflicts`. That is correct: the words "reduction" and "waste" appearing in a
document tell you the document is ABOUT the topic. They tell you nothing about
whether it supports the organisation's position or damns it.

So this module never recommends a valence. Everything it returns is a statement
about the EVIDENCE'S CHARACTERISTICS — how it was matched, what kind of source
it came from, what is missing — and the valence question is left entirely to the
person, which is where it belongs. Production's first nine candidates all match
on keyword overlap alone, and a system that offered "supports" for those would
be manufacturing exactly the certainty this platform exists to refuse.

NOT BINDING, STRUCTURALLY
-------------------------
Nothing here writes. `is_binding` is False on every return and there is no code
path that sets it True; `apply_review_decision()` remains the only writer, and
it still requires a named reviewer. A recommendation cannot become a standing by
being ignored, timing out, or being the only thing on screen.
"""
from __future__ import annotations

from company_intelligence.services.source_provenance import provenance_for_memory

#: The label every surface must show beside a recommendation. Kept here so a
#: template cannot quietly soften it.
RECOMMENDATION_LABEL = 'Recommendation — not reviewed, counts toward nothing'

#: Recommendable standings. Deliberately EXCLUDES 'supports' and 'conflicts':
#: no deterministic signal available here can establish a valence, so neither is
#: offerable. A reviewer can still choose them; the machine cannot suggest them.
CONTEXT = 'CONTEXT'
INSUFFICIENT = 'INSUFFICIENT_TO_CONCLUDE'
NEEDS_STRONGER_SOURCE = 'NEEDS_STRONGER_SOURCE'
NOT_RELEVANT = 'NOT_RELEVANT'

#: Tiers at which a source is worth a reviewer's time on its own merits.
AUTHORITATIVE_TIERS = {1, 2}


def _keyword_terms(match_basis: str) -> list[str]:
    """The terms a keyword match fired on, or an empty list."""
    if not match_basis or ':' not in match_basis:
        return []
    return [t.strip() for t in match_basis.split(':', 1)[1].split(',') if t.strip()]


def recommendation_for_link(link) -> dict:
    """
    A non-binding suggestion for one proposed evidence link.

    Never returns a valence. `standing` is None when even a characteristic-level
    suggestion would overstate what is known.
    """
    provenance = provenance_for_memory(link.evidence)
    authority = provenance['authority']
    tier = authority['tier']
    terms = _keyword_terms(link.match_basis or '')

    must_decide = [
        'Whether this source actually addresses the principle, or merely shares '
        'vocabulary with it.',
        'If it does address it: whether it supports, conflicts with, or only '
        'provides context for the organisation\'s position.',
    ]

    # Matched on keywords alone — the case every production candidate is in.
    if terms:
        reason = (
            f'Matched on keyword overlap alone ({", ".join(terms)}). Shared '
            'vocabulary shows the document discusses the topic; it cannot show '
            'whether the document supports or contradicts the organisation on '
            'it, so no valence is suggested here.'
        )
        if tier is not None and tier not in AUTHORITATIVE_TIERS:
            return {
                'standing': NEEDS_STRONGER_SOURCE,
                'reason': (
                    f'{reason} The source is {authority["label"].lower()}, which '
                    'is a weak basis for a finding even if the match is sound.'),
                'must_decide': must_decide,
                'is_binding': False,
                'label': RECOMMENDATION_LABEL,
                'basis': 'keyword_overlap_low_tier',
            }
        return {
            'standing': CONTEXT,
            'reason': (
                f'{reason} The source is {authority["label"].lower()}, so it is '
                'worth reading before deciding.'),
            'must_decide': must_decide,
            'is_binding': False,
            'label': RECOMMENDATION_LABEL,
            'basis': 'keyword_overlap',
        }

    # No recorded basis at all — a link created outside the matcher.
    if not link.match_basis:
        return {
            'standing': None,
            'reason': (
                'No matcher reasoning was recorded for this link, so there is '
                'nothing for a recommendation to rest on. It was created outside '
                'the automated candidate path.'),
            'must_decide': must_decide,
            'is_binding': False,
            'label': RECOMMENDATION_LABEL,
            'basis': 'no_recorded_basis',
        }

    return {
        'standing': INSUFFICIENT,
        'reason': (
            f'The recorded basis ({link.match_basis}) does not correspond to a '
            'signal this module knows how to weigh, so it defers rather than '
            'guessing.'),
        'must_decide': must_decide,
        'is_binding': False,
        'label': RECOMMENDATION_LABEL,
        'basis': 'unrecognised_basis',
    }


def review_packet(links) -> list[dict]:
    """
    Everything a reviewer needs for a set of proposed links, in one structure.

    Informational only — assembling this applies nothing. It exists so a person
    can work a queue without opening database rows, and so the same structure
    can later seed an evaluation case once a real decision has been recorded
    against it.
    """
    from core.esg_principles_data import PRINCIPLES

    by_id = {p['id']: p for p in PRINCIPLES}
    packet = []
    for link in links:
        principle = by_id.get(link.assessment.kpi_id, {})
        provenance = provenance_for_memory(link.evidence)
        recommendation = recommendation_for_link(link)
        packet.append({
            'link_id': link.pk,
            'entity': {
                'slug': link.assessment.company.company.slug,
                'name': link.assessment.company.company.name,
            },
            'principle': {
                'kpi_id': link.assessment.kpi_id,
                'title': principle.get('title', ''),
                'question': principle.get('question', ''),
                'indicators': principle.get('metrics', []),
            },
            'source': {
                'title': provenance['title'],
                'publisher': provenance['publisher'],
                'source_type': provenance['source_type'],
                'url': provenance['url'],
                'publication_date': provenance['publication_date'],
                'retrieved_at': provenance['retrieved_at'],
                'location': provenance['location'],
                'content_hash': provenance['content_hash'],
                'authority': provenance['authority'],
                'record_reference': provenance['record_reference'],
            },
            'excerpt': (link.evidence.text_chunk or '')[:600],
            'proposed': {
                'relationship': link.relationship,
                'review_state': link.review_state,
                'match_basis': link.match_basis or None,
                'counts_toward_assessment': link.review_state == 'confirmed',
            },
            'recommendation': recommendation,
            'uncertainty': _uncertainty(provenance, link),
        })
    return packet


def _uncertainty(provenance: dict, link) -> list[str]:
    """
    What remains genuinely unknown about this candidate. Stated plainly so a
    reviewer sees the gaps rather than inferring their absence.
    """
    gaps = []
    if not provenance['publication_date']:
        gaps.append('The source carries no publication date, so its age — and '
                    'therefore its current relevance — is unknown.')
    if not provenance['title']:
        gaps.append('The source recorded no title.')
    if not provenance['publisher']:
        gaps.append('No publisher was recorded for the source.')
    if not provenance['authority']['classified']:
        gaps.append('The source type is not in the classification table, so its '
                    'authority defaulted to the most conservative tier rather '
                    'than being assessed.')
    if not provenance['content_hash']:
        gaps.append('No content hash was recorded, so a later reviewer cannot '
                    'confirm which version of the source this was.')
    if link.relationship == 'context':
        gaps.append('The matcher proposed this as context only. Whether it bears '
                    'on the principle either way is exactly what is undecided.')
    return gaps
