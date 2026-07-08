"""
evidence_memory/services/memory.py — create and search EvidenceMemory rows.

Search branches on `connection.vendor`:
- PostgreSQL: real, SQL-side pgvector CosineDistance — fast, scales with an
  index (see EvidenceMemory's HnswIndex note below for a Phase 2 addition).
- Anything else (SQLite, used by local dev and the test suite): a genuine,
  correct Python-side cosine-similarity fallback over the candidate rows —
  slower, but never fabricated, and exercised by every test in this app.
"""
import numpy as np
from django.db import connection

from evidence_memory.models import EvidenceMemory
from evidence_memory.services.embeddings import compute_embedding

DEFAULT_TOP_K = 5


def create_memory_from_evidence(evidence):
    """
    evidence: a harvester.models.Evidence instance — the canonical,
    deduplicated evidence store (see module docstring in models.py for why
    league.Evidence / hikma.Evidence aren't wired up in Phase 1).
    Idempotent on (source_type='harvester_evidence', source_reference).
    """
    text_chunk = evidence.excerpt or evidence.full_text or evidence.title
    source_reference = f'harvester.Evidence:{evidence.pk}'

    memory, _ = EvidenceMemory.objects.get_or_create(
        source_type='harvester_evidence', source_reference=source_reference,
        defaults={'text_chunk': text_chunk},
    )
    memory.text_chunk = text_chunk
    memory.source_url = evidence.url or ''
    memory.company_id = evidence.company_id
    memory.confidence = evidence.confidence or None
    memory.date_collected = evidence.publication_date or evidence.retrieved_at.date()
    memory.is_demo = False  # real harvested evidence, never demo
    _embed_and_save(memory)
    return memory


def create_memory_from_agent_run(agent_run, company=None, country=None):
    """
    agent_run: an agent_runtime_model_router.models.AgentRun instance.
    company/country: optional explicit scope — AgentRun itself has no direct
    company/country FK, so the caller (e.g. the run_ai_analysis Celery task,
    which knows which demo case/company it was analysing) supplies it.
    Idempotent on (source_type='agent_output', source_reference).
    """
    output = agent_run.parsed_output or {}
    text_chunk = output.get('output_summary') or agent_run.input_summary or ''
    source_reference = f'agent_runtime_model_router.AgentRun:{agent_run.pk}'

    memory, _ = EvidenceMemory.objects.get_or_create(
        source_type='agent_output', source_reference=source_reference,
        defaults={'text_chunk': text_chunk},
    )
    memory.text_chunk = text_chunk
    memory.company = company
    memory.country = country
    memory.agent_name = agent_run.agent.agent_name
    memory.confidence = agent_run.calibrated_confidence if agent_run.calibrated_confidence is not None else agent_run.raw_confidence
    memory.date_collected = agent_run.created_at.date()
    memory.is_demo = agent_run.execution_mode_used in ('simulated_demo', 'deterministic_test')
    _embed_and_save(memory)
    return memory


def _embed_and_save(memory):
    try:
        embedding = compute_embedding(memory.text_chunk)
        memory.embedding = embedding
        memory.embedding_status = 'embedded' if embedding is not None else 'failed'
    except Exception:
        memory.embedding_status = 'failed'
    memory.save()


def _cosine_similarity(a, b):
    a, b = np.asarray(a), np.asarray(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1e-9
    return float(np.dot(a, b) / denom)


def search_similar(query_text, top_k=DEFAULT_TOP_K, company=None, country=None):
    """
    Returns up to top_k EvidenceMemory rows most similar to query_text,
    optionally scoped to a company and/or country. Rows without a real
    embedding yet (embedding_status != 'embedded') are never returned — an
    un-embedded row has nothing meaningful to compare against.
    """
    query_vector = compute_embedding(query_text)
    if query_vector is None:
        return EvidenceMemory.objects.none()

    candidates = EvidenceMemory.objects.filter(embedding_status='embedded')
    if company is not None:
        candidates = candidates.filter(company=company)
    if country is not None:
        candidates = candidates.filter(country=country)

    if connection.vendor == 'postgresql':
        from pgvector.django import CosineDistance
        return list(candidates.annotate(distance=CosineDistance('embedding', query_vector)).order_by('distance')[:top_k])

    scored = [(_cosine_similarity(m.embedding, query_vector), m) for m in candidates if m.embedding]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [memory for _, memory in scored[:top_k]]


def search_company_memory(company, query_text, top_k=DEFAULT_TOP_K):
    return search_similar(query_text, top_k=top_k, company=company)


def search_country_memory(country, query_text, top_k=DEFAULT_TOP_K):
    return search_similar(query_text, top_k=top_k, country=country)
