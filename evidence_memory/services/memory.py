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


_HIKMA_REVIEW_TIER = {
    'verified': 'independently_verified',
    'analyst-reviewed': 'human_reviewed',
    'ai-seeded': 'system_checked',
    'model-estimate': 'system_checked',
}


def _hikma_verification_state(evidence):
    """
    Maps hikma's own confidence_tier + scholar_review_required onto
    EvidenceMemory's verification workflow without ever claiming a stronger
    tier than hikma itself asserts. scholar_review_required is True on every
    row the current ingest pipeline creates (hikma/ingest.py), so today this
    always resolves to 'requires_review' — that will change honestly, on its
    own, once a real scholar-review workflow starts clearing the flag.
    """
    review_tier = _HIKMA_REVIEW_TIER.get(evidence.confidence_tier, 'system_checked')
    if evidence.scholar_review_required:
        return 'requires_review', review_tier
    if evidence.confidence_tier in ('verified', 'analyst-reviewed'):
        return 'verified', review_tier
    return 'pending', review_tier


def create_memory_from_hikma_evidence(evidence):
    """
    evidence: a hikma.models.Evidence instance — a normalised SAY/DO/SHOW
    statement about a company (or, in future, another subject type). This is
    additive alongside create_memory_from_evidence(), not a replacement —
    hikma.Evidence has its own identity/dedup scheme (subject_type/subject_ref
    + content_hash, see hikma/ingest.py) distinct from harvester.Evidence's,
    and remains its own normalised evidence store; this only projects it into
    the shared semantic index, same as the harvester sync does.
    Idempotent on (source_type, source_reference).
    """
    text_chunk = evidence.statement
    source_type = 'company_report' if evidence.subject_type == 'company' else 'other'
    source_reference = f'hikma.Evidence:{evidence.pk}'

    memory, _ = EvidenceMemory.objects.get_or_create(
        source_type=source_type, source_reference=source_reference,
        defaults={'text_chunk': text_chunk},
    )
    memory.text_chunk = text_chunk
    memory.source_url = evidence.source_url or ''
    memory.company_id = evidence.company_id  # hikma.Evidence.company is a real FK to companies.CompanyProfile
    memory.confidence = evidence.confidence_score
    memory.date_collected = evidence.published_at or evidence.created_at.date()
    memory.verification_status, memory.review_tier = _hikma_verification_state(evidence)
    memory.is_demo = False  # hikma ingestion is derived from real CompanyProfile data, never demo
    _embed_and_save(memory)
    return memory


def create_memory_from_league_evidence(evidence):
    """
    evidence: a league.models.Evidence instance — a real project-verification
    document (permit, audit report, invoice, ...) attached to a league.Company
    and/or league.EnvironmentalProject. league.Company is a wholly separate
    model from companies.CompanyProfile (different app, different schema) —
    no `company` FK is set on the memory here, since setting company_id to a
    league.Company's pk would silently point at the wrong table's row.
    Provenance is carried entirely through source_reference instead.
    Idempotent on (source_type, source_reference).
    """
    text_chunk = evidence.notes or evidence.title
    source_reference = f'league.Evidence:{evidence.pk}'

    memory, _ = EvidenceMemory.objects.get_or_create(
        source_type='company_report', source_reference=source_reference,
        defaults={'text_chunk': text_chunk},
    )
    memory.text_chunk = text_chunk
    memory.source_url = evidence.url or ''
    memory.date_collected = evidence.date_issued or evidence.created_at.date()
    # league.Evidence.verification_status choices (pending/verified/rejected) are
    # a strict subset of EvidenceMemory's, so this is a direct, honest mapping.
    memory.verification_status = evidence.verification_status
    memory.review_tier = 'human_reviewed' if evidence.verification_status == 'verified' else 'uploaded'
    memory.is_demo = False  # only wired into league's real, non-seed write paths — see callers
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
