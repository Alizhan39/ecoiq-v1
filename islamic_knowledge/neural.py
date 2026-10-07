"""Optional, pinned multilingual neural encoder, isolated from lexical memory.

Weights must be prepared before request serving. Requests never download models,
and no vector is treated as religious evidence or a calibrated confidence score.
"""
from functools import lru_cache
from heapq import nlargest
from threading import Lock

import numpy as np
from django.conf import settings
from django.db.models import F

from .models import KnowledgePassage

MODEL_ID = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
MODEL_REVISION = 'bf3bf13ab40c3157080a7ab344c831b9ad18b5eb'
MODEL_VERSION = f'{MODEL_ID}@{MODEL_REVISION}'
DIMENSIONS = 384
MAX_INDEXED_PASSAGES = 10000
_lock = Lock()


class NeuralUnavailable(RuntimeError):
    pass


def load_encoder(*, allow_download=False):
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(MODEL_ID, revision=MODEL_REVISION, device='cpu',
            cache_folder=settings.ISLAMIC_NEURAL_CACHE_DIR,
            trust_remote_code=False, local_files_only=not allow_download,
            model_kwargs={'use_safetensors': True})
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        raise NeuralUnavailable('Neural encoder dependencies or pinned cached weights are unavailable.') from exc


@lru_cache(maxsize=2)
def _encoder(cache_dir):
    # The key follows settings changes; weights and model version stay pinned.
    return load_encoder()


def encode(texts):
    if not settings.ISLAMIC_NEURAL_SEARCH_ENABLED:
        raise NeuralUnavailable('Neural semantic search is disabled.')
    if not texts or any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError('Embedding input must contain non-empty text.')
    with _lock:
        model = _encoder(settings.ISLAMIC_NEURAL_CACHE_DIR)
        # Refuse silent truncation of passages or queries. Import smaller exact
        # source passages instead of indexing text the encoder never saw.
        tokens = model.tokenizer(texts, truncation=False, padding=False)['input_ids']
        if any(len(row) > model.max_seq_length for row in tokens):
            raise ValueError('Text exceeds the pinned encoder token limit; use shorter passages or query.')
        vectors = np.asarray(model.encode(texts, batch_size=16, normalize_embeddings=True,
            show_progress_bar=False, convert_to_numpy=True), dtype=float)
    if vectors.shape != (len(texts), DIMENSIONS) or not np.isfinite(vectors).all():
        raise NeuralUnavailable('Encoder returned invalid vectors.')
    norms = np.linalg.norm(vectors, axis=1)
    if (norms == 0).any():
        raise NeuralUnavailable('Encoder returned a zero vector.')
    return (vectors / norms[:, None]).tolist()


def index_passages():
    indexed = 0
    candidates = KnowledgePassage.published().exclude(
        embedding_model=MODEL_VERSION, embedding_digest=F('digest'))
    batch = []

    def write(rows):
        nonlocal indexed
        vectors = encode([row.passage for row in rows])
        for row, vector in zip(rows, vectors):
            # Reject a concurrent content edit/revocation rather than attaching
            # an old vector to a new or withdrawn source.
            indexed += KnowledgePassage.published().filter(pk=row.pk, digest=row.digest).update(
                embedding=vector, embedding_model=MODEL_VERSION, embedding_digest=row.digest)

    for row in candidates.iterator(chunk_size=64):
        batch.append(row)
        if len(batch) == 16:
            write(batch)
            batch = []
    if batch:
        write(batch)
    return indexed


def semantic_search(query, *, limit=5, provider=None, language=None):
    if not isinstance(query, str) or not query.strip() or len(query) > 1000:
        raise ValueError('Query must contain 1–1000 characters.')
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError('Limit must be between 1 and 20.')
    if not settings.ISLAMIC_NEURAL_SEARCH_ENABLED:
        raise NeuralUnavailable('Neural semantic search is disabled.')
    candidates = KnowledgePassage.published().filter(
        embedding_model=MODEL_VERSION, embedding_digest=F('digest')).exclude(embedding=[])
    if provider:
        candidates = candidates.filter(provider=provider)
    if language:
        candidates = candidates.filter(language=language)
    # Phase 1 is exact cosine over a bounded corpus. Never silently truncate
    # the corpus or claim approximate results; graduate to pgvector when needed.
    count = candidates.count()
    if count > MAX_INDEXED_PASSAGES:
        raise NeuralUnavailable('Corpus exceeds the exact-search capacity; configure a vector index.')
    if not count:
        return []
    query_vector = np.asarray(encode([query])[0])

    def scores():
        for row in candidates.iterator(chunk_size=128):
            vector = np.asarray(row.embedding, dtype=float)
            if vector.shape != (DIMENSIONS,) or not np.isfinite(vector).all():
                continue
            norm = np.linalg.norm(vector)
            if norm:
                yield float(np.clip(np.dot(vector, query_vector) / norm, -1, 1)), row

    ranked = nlargest(limit, scores(), key=lambda pair: pair[0])
    # A source withdrawn while ranking must not be returned from an old cursor.
    valid = set(KnowledgePassage.published().filter(
        pk__in=[row.pk for _, row in ranked], embedding_model=MODEL_VERSION,
        embedding_digest=F('digest')).values_list('pk', 'digest'))
    return [(similarity, row) for similarity, row in ranked if (row.pk, row.digest) in valid]
