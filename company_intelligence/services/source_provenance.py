"""
company_intelligence/services/source_provenance.py — the full provenance of one
evidence record, assembled from the rows that already hold it.

WHY THIS EXISTS
---------------
The first real production ingestion exposed the gap. An evidence item served by
the API carried a URL, a retrieval date, a review state and the matcher's
reasoning — and then, where its source title should be, the string
`harvester.Evidence:41`.

That is not a lost title. It is `EvidenceMemory.source_reference`, the
idempotency key `create_memory_from_evidence()` writes and production
deduplication depends on, being rendered as a display name because no other
field carried one.

RESOLVED, NOT COPIED
--------------------
The metadata was never missing. `harvester.SourceDocument` records the title,
publisher, publication date, retrieval time, content hash and source tier;
`harvester.Evidence` records the chunk's own title, page reference and hash.
Promotion into `EvidenceMemory` simply did not carry them across.

So this module resolves provenance through the lineage rather than copying it
forward. Copying would denormalise a fact that already has an owner, and the
copy would drift the first time a document was re-fetched. The lookup
convention is the one `evidence_quality._harvester_evidence_for_memory()`
already uses — the same `source_reference` contract, read rather than
reinvented.

AUTHORITY IS DERIVED FROM SOURCE IDENTITY, NEVER FROM TONE
----------------------------------------------------------
`authority` comes from `harvester.verification.SOURCE_TIER_BY_TYPE`, the tier
table this codebase already treats as canonical and which
`evidence_provenance.py` explicitly forbids competing with. It maps a source
TYPE to a tier: sec_edgar and companies_house are Tier 1 because of what they
are, not because their prose reads officially. Unmapped types fall to Tier 4
conservatively, never a middle tier.

No text is inspected. Nothing here can promote a blog post by finding it
well-written.

ABSENT IS ABSENT
----------------
Every field is None when the source genuinely does not provide it. There is no
path that substitutes an empty string for an unknown publisher or today's date
for an unknown publication date — the same rule the rest of the evidence layer
runs on, applied to provenance.
"""
from __future__ import annotations

from harvester.verification import DEFAULT_TIER, SOURCE_TIER_BY_TYPE

#: Prefix of the `source_reference` contract written by
#: `evidence_memory.services.memory.create_memory_from_evidence`.
HARVESTER_SOURCE_PREFIX = 'harvester.Evidence:'

#: Tier -> the class of source it represents. Names describe WHAT the source is,
#: which is the only thing the tier table actually knows.
AUTHORITY_CLASS = {
    1: 'REGULATOR_OR_STATUTORY_FILING',
    2: 'COMPANY_REPORTED',
    3: 'STANDARDS_BODY_OR_ESTABLISHED_SECONDARY',
    4: 'COMPANY_SELF_PUBLISHED_OR_UNCLASSIFIED',
}

AUTHORITY_LABEL = {
    1: 'Regulator or statutory filing',
    2: 'Company-reported document',
    3: 'Standards body or established secondary source',
    4: 'Company self-published, or source type not classified',
}


def harvester_evidence_for_memory(memory):
    """
    The `harvester.Evidence` row an `EvidenceMemory` was promoted from, or None.

    Same contract as `evidence_quality._harvester_evidence_for_memory`. A memory
    from another path (an agent run, a manual fixture) has no harvester lineage
    and honestly returns None rather than a partially-filled shell.
    """
    reference = getattr(memory, 'source_reference', '') or ''
    if not reference.startswith(HARVESTER_SOURCE_PREFIX):
        return None
    try:
        pk = int(reference.split(':', 1)[1])
    except (IndexError, ValueError):
        return None
    from harvester.models import Evidence
    return (Evidence.objects
            .filter(pk=pk)
            .select_related('document', 'source')
            .first())


def _authority(source_type: str | None) -> dict:
    """
    Tier and class for a source TYPE. Unknown type -> the conservative default,
    labelled as unclassified rather than as a judgement.
    """
    if not source_type:
        return {'tier': None, 'class': 'UNKNOWN', 'label': 'Source type not recorded'}
    tier = SOURCE_TIER_BY_TYPE.get(source_type, DEFAULT_TIER)
    return {
        'tier': tier,
        'class': AUTHORITY_CLASS.get(tier, AUTHORITY_CLASS[DEFAULT_TIER]),
        'label': AUTHORITY_LABEL.get(tier, AUTHORITY_LABEL[DEFAULT_TIER]),
        # True only when the type was actually in the table. A Tier 4 that was
        # mapped and a Tier 4 that fell through are different facts.
        'classified': source_type in SOURCE_TIER_BY_TYPE,
    }


def provenance_for_memory(memory) -> dict:
    """
    Everything known about where one evidence record came from.

    Shape is stable whether or not a harvester lineage exists: the keys are
    always present and their values are None when unknown, so a caller never
    has to distinguish "field missing" from "value unknown".
    """
    evidence = harvester_evidence_for_memory(memory)
    document = getattr(evidence, 'document', None) if evidence else None
    source = getattr(evidence, 'source', None) if evidence else None

    # Prefer the chunk's own title, then the document's. Both are real titles
    # recorded at fetch time; neither is the idempotency key.
    title = (getattr(evidence, 'title', '') or getattr(document, 'title', '') or '')
    publisher = (getattr(document, 'publisher', '')
                 or getattr(source, 'source_owner', '') or '')
    source_type = (getattr(evidence, 'document_type', '')
                   or getattr(document, 'document_type', '')
                   or getattr(source, 'source_type', '') or '')
    published = getattr(evidence, 'publication_date', None) or getattr(
        document, 'publication_date', None)
    retrieved = getattr(evidence, 'retrieved_at', None) or getattr(
        document, 'retrieved_at', None)
    content_hash = (getattr(evidence, 'content_hash', '')
                    or getattr(document, 'content_hash', '') or '')

    return {
        'has_source_record': evidence is not None,
        # The identity key, exposed as what it is rather than as a title.
        'record_reference': getattr(memory, 'source_reference', '') or None,
        'title': title or None,
        'publisher': publisher or None,
        'source_type': source_type or None,
        'url': (getattr(evidence, 'url', '') or getattr(document, 'url', '')
                or getattr(memory, 'source_url', '') or None),
        'publication_date': published.isoformat() if published else None,
        'retrieved_at': retrieved.isoformat() if retrieved else None,
        # Which page or section the chunk came from — what makes a citation
        # checkable rather than merely attributed to a whole report.
        'location': getattr(evidence, 'source_location', '') or None,
        # Enough to establish "reviewed against this version of this source".
        'content_hash': content_hash or None,
        # SHA-256 of the stored text itself, written by EvidenceMemory on save.
        'text_integrity_reference': getattr(memory, 'integrity_reference', '') or None,
        'authority': _authority(source_type),
        'ingestion_method': ('harvester_document' if evidence is not None
                             else (getattr(memory, 'source_type', '') or None)),
        'ingested_at': (memory.created_at.isoformat()
                        if getattr(memory, 'created_at', None) else None),
        'is_demo': bool(getattr(memory, 'is_demo', False)),
    }


def display_title(memory) -> str | None:
    """
    A human-readable name for one evidence record, or None.

    None rather than a fallback: `source_reference` is an idempotency key, and
    showing it was the defect this module was written for. A record whose source
    recorded no title has no title, and the interface should say so in its own
    words rather than printing a primary key at a reader.
    """
    return provenance_for_memory(memory)['title']
