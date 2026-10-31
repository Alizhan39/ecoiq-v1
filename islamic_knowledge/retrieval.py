"""Bounded hybrid retrieval of published source text; never generated answers.

Reciprocal rank fusion combines ranks rather than incomparable cosine/word
scores. The existing neural-only API retains its strict availability contract.
"""
from dataclasses import dataclass, field
from heapq import nlargest
import re
import unicodedata

from django.conf import settings

from .models import KnowledgePassage
from .neural import MODEL_VERSION, NeuralUnavailable, semantic_search, validate_search

MAX_LEXICAL_PASSAGES = 10000
CANDIDATE_LIMIT = 20
RRF_K = 60


class RetrievalUnavailable(RuntimeError):
    pass


def tokens(text):
    # NFKC handles presentation forms/full-width characters; stripping marks
    # permits Arabic queries with/without harakat. No stemming/translation is
    # claimed. Preserve letters such as Kazakh ә, қ, ұ, ү and ң.
    normal = unicodedata.normalize('NFKC', text).casefold()
    normal = ''.join(char for char in normal if unicodedata.category(char) != 'Mn')
    return set(re.findall(r'[^\W_]+', normal, flags=re.UNICODE))


def lexical_search(query, *, limit=5, provider=None, language=None):
    validate_search(query, limit)
    terms = tokens(query)
    if not terms or len(terms) > 32:
        raise ValueError('Query must contain 1–32 distinct searchable words.')
    candidates = KnowledgePassage.published()
    if provider:
        candidates = candidates.filter(provider=provider)
    if language:
        candidates = candidates.filter(language=language)
    if candidates.count() > MAX_LEXICAL_PASSAGES:
        raise RetrievalUnavailable('Corpus exceeds the lexical-search capacity; configure a text index.')

    def scores():
        # Lexical search must not transfer every stored vector from the DB.
        for row in candidates.defer('embedding').iterator(chunk_size=128):
            overlap = terms & tokens(row.passage)
            if overlap:
                yield len(overlap) / len(terms), row

    return nlargest(limit, scores(), key=lambda pair: pair[0])


@dataclass
class HybridHit:
    row: KnowledgePassage
    fusion_score: float = 0.0
    matched_by: list[str] = field(default_factory=list)
    similarity: float | None = None
    lexical_match: float | None = None


@dataclass
class HybridResult:
    results: list[HybridHit]
    method: str
    neural_status: str


def hybrid_search(query, *, limit=5, provider=None, language=None):
    validate_search(query, limit)
    lexical = lexical_search(query, limit=CANDIDATE_LIMIT, provider=provider, language=language)
    semantic = []
    if not settings.ISLAMIC_NEURAL_SEARCH_ENABLED:
        status = 'disabled'
    else:
        try:
            semantic = semantic_search(query, limit=CANDIDATE_LIMIT, provider=provider, language=language)
            status = 'used' if semantic else 'no_results'
        except NeuralUnavailable:
            # Explicit degradation, not a claim that lexical results are neural.
            status = 'unavailable'

    hits = {}
    for method, ranked in (('lexical', lexical), ('neural', semantic)):
        for rank, (score, row) in enumerate(ranked, start=1):
            # A concurrent edit can put two versions of one PK into the lists.
            key = (row.pk, row.digest)
            hit = hits.setdefault(key, HybridHit(row=row))
            hit.fusion_score += 1 / (RRF_K + rank)
            hit.matched_by.append(method)
            if method == 'neural':
                hit.similarity = score
            else:
                hit.lexical_match = score

    # Recheck publication/digests after both searches. Neural-only hits must
    # also retain the current embedding; never return a withdrawn source.
    current = {row.pk: row for row in KnowledgePassage.published().filter(
        pk__in=[key[0] for key in hits]).defer('embedding')}
    valid = []
    for (pk, digest), hit in hits.items():
        row = current.get(pk)
        if row is None or row.digest != digest:
            continue
        if 'neural' in hit.matched_by and (
                row.embedding_model != MODEL_VERSION or row.embedding_digest != row.digest):
            # Discard the stale neural contribution; a lexical match can live on.
            rank = next(i for i, (_, old) in enumerate(semantic, 1) if old.pk == pk and old.digest == digest)
            hit.fusion_score -= 1 / (RRF_K + rank)
            hit.matched_by.remove('neural')
            hit.similarity = None
        if hit.matched_by:
            hit.row = row
            valid.append(hit)
    valid.sort(key=lambda hit: (-hit.fusion_score, hit.row.provider, hit.row.external_id))
    used_neural = any('neural' in hit.matched_by for hit in valid)
    method = 'hybrid_rrf' if used_neural else 'lexical_overlap'
    return HybridResult(valid[:limit], method, status)
