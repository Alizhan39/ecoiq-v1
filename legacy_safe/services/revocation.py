"""
LegacySafe AI — revocation propagation.

BasedAI alignment: revoking a source document must cascade. Its chunks go
dark immediately, and any DerivedMemory whose lineage names that document
also goes dark — a derived summary can never outlive the source it was
built from.
"""
from legacy_safe.models import DerivedMemory, MemoryChunk
from legacy_safe.services import audit


def revoke_source_document(source_document, user=None, reason='Manual revocation'):
    source_document.is_revoked = True
    source_document.save(update_fields=['is_revoked', 'updated_at'])

    revoked_chunk_ids = list(
        MemoryChunk.objects.filter(source_document=source_document, is_revoked=False)
        .values_list('id', flat=True)
    )
    MemoryChunk.objects.filter(id__in=revoked_chunk_ids).update(is_revoked=True)

    revoked_derived_titles = []
    for derived in DerivedMemory.objects.filter(project=source_document.project, is_revoked=False):
        if source_document.id in derived.lineage_source_ids:
            derived.is_revoked = True
            derived.save(update_fields=['is_revoked'])
            revoked_derived_titles.append(derived.title)

    audit.log_event(
        user=user,
        action='revoke',
        question='',
        decision='revoked',
        allowed_sources=[],
        blocked_sources=[source_document.title, *revoked_derived_titles],
        reason=reason,
    )

    return {
        'source_document': source_document.title,
        'chunks_revoked': len(revoked_chunk_ids),
        'derived_memories_revoked': revoked_derived_titles,
    }
