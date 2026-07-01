"""
LegacySafe AI — permission-aware retrieval.

MVP retrieval is simple keyword overlap. What matters for the Conduct/BasedAI
demo is not retrieval sophistication — it's that permission filtering happens
BEFORE anything is scored or handed to the planner, and that every call is
audited. Blocked chunks are never inspected for relevance; they are excluded
outright based on access_level alone.
"""
import re

from legacy_safe.models import MemoryChunk
from legacy_safe.services import audit
from legacy_safe.services.permissions import can_access, get_user_roles

_STOPWORDS = {
    'a', 'an', 'the', 'is', 'are', 'of', 'what', 'full', 'to', 'for', 'and',
    'in', 'on', 'with', 'do', 'we', 'i', 'it', 'this', 'that', 'plan',
}


def _keywords(text):
    return {w for w in re.findall(r'[a-z0-9]+', text.lower()) if w not in _STOPWORDS}


def _score(chunk_text, question_keywords):
    return len(_keywords(chunk_text) & question_keywords)


def retrieve_allowed_chunks_for_roles(roles, project, question):
    """Pure retrieval against an explicit role set — no user/DB-session assumptions.

    Used both by retrieve_allowed_chunks() (real logged-in user) and by the
    permission demo page (which simulates four personas without four logins).
    """
    question_keywords = _keywords(question)
    chunks = (
        MemoryChunk.objects
        .filter(source_document__project=project)
        .select_related('source_document')
        .order_by('source_document__created_at', 'chunk_index')
    )

    allowed, blocked = [], []
    for chunk in chunks:
        revoked = chunk.is_revoked or chunk.source_document.is_revoked
        entry = {
            'chunk_id': chunk.id,
            'source_title': chunk.source_document.title,
            'access_level': chunk.access_level,
            'text': chunk.text,
            'is_revoked': revoked,
            'relevance': _score(chunk.text, question_keywords),
        }
        if can_access(chunk.access_level, roles, is_revoked=revoked):
            allowed.append(entry)
        else:
            entry['reason'] = 'revoked' if revoked else 'insufficient_role'
            blocked.append(entry)

    allowed.sort(key=lambda e: e['relevance'], reverse=True)
    return {'allowed': allowed, 'blocked': blocked}


def retrieve_allowed_chunks(user, project, question):
    """Retrieve for a real request user, and write the AuditLog entry."""
    roles = get_user_roles(user)
    result = retrieve_allowed_chunks_for_roles(roles, project, question)

    log = audit.log_event(
        user=user,
        action='ask',
        question=question,
        decision='allowed' if result['allowed'] else 'blocked',
        allowed_sources=[e['source_title'] for e in result['allowed']],
        blocked_sources=[e['source_title'] for e in result['blocked']],
        reason=f'roles={sorted(roles)}',
    )
    result['audit_log'] = log
    result['roles'] = roles
    return result
