"""Versioned, exact quotations. Retrieval similarity is never claim support."""
import hashlib
import json
from urllib.parse import urlsplit

from django.core.exceptions import PermissionDenied

from evidence_memory.models import EvidenceCitationSnapshot
from evidence_memory.services.retrieval_policy import is_record_accessible


INSUFFICIENT = 'Insufficient evidence: this conclusion has no verified document-level support.'


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def payload_digest(payload):
    return digest(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')))


def safe_source_url(url):
    try:
        parsed = urlsplit(url or '')
        return url if parsed.scheme in ('https', 'http') and parsed.hostname and parsed.username is None else ''
    except ValueError:
        return ''


def _source_payload(memory):
    payload = {
        'text': memory.text_chunk,
        'text_sha256': digest(memory.text_chunk),
        'source_reference': memory.source_reference,
        'document_title': memory.source_reference or f'Evidence record #{memory.pk}',
        'source_url': safe_source_url(memory.source_url),
        'source_location': 'Stored evidence chunk',
        'document_reference': '',
        'document_version': digest(memory.text_chunk),
        'version_kind': 'Stored chunk SHA-256 (original document version unavailable)',
        'verification_status': memory.verification_status,
        'review_tier': memory.review_tier,
        'is_demo': memory.is_demo,
    }
    prefix = 'harvester.Evidence:'
    if memory.source_reference.startswith(prefix):
        from harvester.models import Evidence
        try:
            evidence = Evidence.objects.select_related('document').filter(pk=int(memory.source_reference[len(prefix):])).first()
        except (ValueError, OverflowError):
            evidence = None
        # Never borrow a new document version for an old, unsynchronised chunk.
        if evidence and memory.text_chunk == (evidence.excerpt or evidence.full_text or evidence.title):
            payload['document_title'] = evidence.title or payload['document_title']
            payload['source_location'] = evidence.source_location or 'Stored evidence chunk'
            if evidence.document_id:
                document = evidence.document
                payload.update(document_title=document.title, document_reference=f'harvester.SourceDocument:{document.pk}',
                               source_url=safe_source_url(document.url))
                if document.content_hash:
                    payload.update(document_version=document.content_hash, version_kind='Recorded source-document content hash')
    return payload


def capture_citation(memory, *, start=0, end=None):
    """Internal: callers must first retrieve memory through the access policy."""
    end = min(len(memory.text_chunk), start + 400) if end is None else end
    if not (type(start) is int and type(end) is int and 0 <= start < end <= len(memory.text_chunk)):
        raise ValueError('Citation must identify a non-empty exact text range.')
    payload = _source_payload(memory)
    snapshot, _ = EvidenceCitationSnapshot.objects.get_or_create(
        memory=memory, digest=payload_digest(payload), defaults={'payload': payload},
    )
    quote = payload['text'][start:end]
    return {
        'citation_id': f'ev-{snapshot.pk}-{start}-{end}', 'snapshot_id': snapshot.pk,
        'memory_id': memory.pk, 'snapshot_sha256': snapshot.digest,
        'quote': quote, 'quote_sha256': digest(quote), 'start': start, 'end': end,
        **{k: v for k, v in payload.items() if k != 'text'},
    }


def resolve_citation(citation, *, user, project, include_snapshot=False):
    """Recheck access and stored bytes at read time, including historical quotes."""
    try:
        snapshot = EvidenceCitationSnapshot.objects.select_related('memory').get(pk=citation['snapshot_id'])
        start, end = citation['start'], citation['end']
        payload = snapshot.payload
        valid = (type(start) is int and type(end) is int and 0 <= start < end <= len(payload['text'])
                 and snapshot.digest == payload_digest(payload) == citation['snapshot_sha256']
                 and digest(payload['text']) == payload['text_sha256']
                 and snapshot.memory_id == citation['memory_id']
                 and citation['citation_id'] == f'ev-{snapshot.pk}-{start}-{end}'
                 and payload['text'][start:end] == citation['quote']
                 and digest(citation['quote']) == citation['quote_sha256'])
    except (KeyError, TypeError, ValueError, OverflowError, EvidenceCitationSnapshot.DoesNotExist):
        raise PermissionDenied('Citation is unavailable or its integrity check failed.') from None
    if not valid or not is_record_accessible(snapshot.memory, project, user):
        raise PermissionDenied('Citation is unavailable or its integrity check failed.')
    # Display trusted snapshot fields, never metadata supplied by a saved claim.
    return {
        **{k: v for k, v in payload.items() if k != 'text'},
        **{k: citation[k] for k in ('citation_id', 'snapshot_id', 'memory_id', 'snapshot_sha256', 'quote', 'quote_sha256', 'start', 'end')},
        'source_changed': payload_digest(_source_payload(snapshot.memory)) != snapshot.digest,
        'current_verification_status': snapshot.memory.verification_status,
        'expired': snapshot.memory.is_expired or snapshot.memory.verification_status == 'expired',
        **({'stored_snapshot': payload} if include_snapshot else {}),
    }


def assess_claim(claim, citations):
    """Only an exact attributed quotation is mechanically supported.

    An inferred recommendation cannot become supported just by naming nearby
    search results. Entailment / substantive human review is a separate gate.
    """
    ids = claim.get('citation_ids', [])
    if claim.get('kind') == 'source_quote' and len(ids) == 1:
        citation = citations.get(ids[0])
        if citation and claim.get('text') == citation['quote']:
            return {**claim, 'support_status': 'attributed_quote',
                    'support_note': 'Exact source quotation; its truth is not independently established by this check.'}
    return {**claim, 'citation_ids': [], 'support_status': 'insufficient_evidence', 'support_note': INSUFFICIENT}
