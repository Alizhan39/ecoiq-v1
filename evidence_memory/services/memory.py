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


# Vertical-slice PR 7 — closes the loop: VERIFIED CAPITAL OUTCOME -> EVIDENCE
# MEMORY -> RETRIEVAL FOR FUTURE DECISIONS. "Learning" here means retrieval of
# real historical evidence, never automatic model retraining or weight
# updates — see create_memory_from_verified_outcome()'s docstring.
#
# Deterministic eligibility tier -> (verification_status, review_tier).
# Never upgraded automatically; a demo/illustrative source project can never
# reach 'verified' regardless of its own MRV status (see the is_demo check
# inside create_memory_from_verified_outcome()).
_OUTCOME_TIER_MAPPING = {
    'rejected':       ('rejected', 'uploaded'),
    'disputed':       ('requires_review', 'system_checked'),
    'verified':       ('verified', 'independently_verified'),
    'human_reviewed': ('requires_review', 'human_reviewed'),
    'reported':       ('pending', 'system_checked'),
    'estimated':      ('pending', 'uploaded'),
}


def _outcome_eligibility_tier(outcome):
    """
    decision.approval_status == 'rejected' -> never positive learning evidence.
    mrv_status == 'disputed' -> a genuine MRV discrepancy, flagged for review,
    never silently treated as either verified or safe to discard.
    verified_status == 'verified' (and evidence isn't 'missing') -> the
    outcome's own MRV process already asserts this; evidence_quality=='missing'
    can never support 'verified', by definition.
    A real, human-typed reviewer note (see execution_monitoring.
    record_monitoring_outcome()'s reviewer_note -> next_capital_allocation_
    signal convention) is the only honest "a human reviewed this specific
    outcome" signal available on this model — used to distinguish REPORTED
    (real after-data, no reviewer commentary yet) from HUMAN-REVIEWED.
    """
    decision = outcome.decision
    if decision.approval_status == 'rejected':
        return 'rejected'
    if outcome.mrv_status == 'disputed':
        return 'disputed'
    if outcome.verified_status == 'verified' and outcome.evidence_quality != 'missing':
        return 'verified'
    if '[Reviewer note]' in (outcome.next_capital_allocation_signal or ''):
        return 'human_reviewed'
    if outcome.mrv_status == 'after_data_pending':
        return 'reported'
    return 'estimated'


def _fmt_amount(value, currency='£'):
    return f'{currency}{value:,.0f}' if value is not None else 'NOT YET REPORTED'


def create_memory_from_verified_outcome(outcome, actor=None):
    """
    outcome: a waste_to_value_capital_allocation_engine.models.
    VerifiedCapitalOutcome instance. Idempotent on (source_type='other',
    source_reference) — the same one-row-per-source-object pattern as
    create_memory_from_evidence()/hikma/league above, NOT the content-hash
    pattern used by create_memory_from_manual_project_evidence(): there is
    exactly one VerifiedCapitalOutcome per CapitalAllocationDecision (a real
    OneToOneField), so a repeated sync must update the SAME memory row as the
    outcome's real state changes over time, never accumulate stale duplicate
    versions of it.

    Never claims machine learning: this stores a real, human-readable summary
    of a real outcome as retrievable evidence. It never retrains a model,
    updates a scoring weight, or runs automatically for every outcome — see
    the staff-only sync_outcome_to_evidence_memory() view, the only caller.

    source_type='other': none of EvidenceMemory's existing SOURCE_TYPE_CHOICES
    honestly describe a verified capital outcome record (see PR7 audit) —
    'other' is the safest existing choice; source_reference disambiguates.
    document_category='technical_report' — the closest existing choice for a
    structured monitoring/outcome summary.

    is_demo propagates from the matched GoldProject (via the same public
    find_matching_gold_project() used by capital_guardian_handoff/PR5) — a
    demo/illustrative project's outcome can never be stored as 'verified'
    evidence, however strong its own recorded MRV status looks in isolation.
    Ambiguous or missing project matches are treated as real (not demo) but
    with no country scoping, never guessed.
    """
    decision = outcome.decision
    intervention = decision.intervention
    loss = intervention.operational_loss

    tier = _outcome_eligibility_tier(outcome)
    verification_status, review_tier = _OUTCOME_TIER_MAPPING[tier]

    from waste_to_value_capital_allocation_engine.services.capital_guardian_handoff import (
        AmbiguousProjectMatchError, find_matching_gold_project,
    )
    try:
        matched_project = find_matching_gold_project(decision)
    except AmbiguousProjectMatchError:
        matched_project = None

    is_demo = bool(matched_project.is_demo) if matched_project is not None else False
    if is_demo and tier == 'verified':
        verification_status, review_tier = _OUTCOME_TIER_MAPPING['human_reviewed']

    reviewer_note = ''
    signal_text = outcome.next_capital_allocation_signal or ''
    if '[Reviewer note]' in signal_text:
        reviewer_note = signal_text.split('[Reviewer note]', 1)[1].strip(' ]').strip()

    text_chunk = '\n'.join([
        f'PROJECT: {decision.project or "Not recorded"}',
        f'ORIGINAL VALUE LOSS: {loss.title} ({loss.get_loss_type_display()}) — financial loss {_fmt_amount(loss.financial_loss_amount)}',
        f'SELECTED INTERVENTION: {intervention.title} ({intervention.get_intervention_type_display()})',
        f'EXPECTED CAPEX: {_fmt_amount(intervention.capex_estimate)}',
        f'ACTUAL CAPEX: {_fmt_amount(outcome.capex_actual)}',
        f'EXPECTED SAVINGS: {_fmt_amount(intervention.estimated_annual_savings)}',
        f'ACTUAL SAVINGS: {_fmt_amount(outcome.savings_actual)}',
        f'EXPECTED LOSS AVOIDED: {_fmt_amount(intervention.estimated_loss_avoided)}',
        f'ACTUAL LOSS AVOIDED: {_fmt_amount(outcome.loss_avoided_actual)}',
        f'EXPECTED PAYBACK: {intervention.estimated_payback_months} months' if intervention.estimated_payback_months is not None else 'EXPECTED PAYBACK: NOT YET REPORTED',
        f'ACTUAL PAYBACK: {outcome.payback_actual} months' if outcome.payback_actual is not None else 'ACTUAL PAYBACK: NOT YET REPORTED',
        f'IMPLEMENTATION STATUS: {outcome.get_mrv_status_display()}',
        f'VERIFICATION STATUS: {outcome.get_verified_status_display()} (evidence quality: {outcome.get_evidence_quality_display()})',
        'EVIDENCE LIMITATIONS: Figures are human-entered monitoring data, not an independent third-party '
        'audit unless explicitly reviewer-confirmed; a single pilot result does not guarantee outcomes elsewhere.',
        f'REVIEW NOTES: {reviewer_note}' if reviewer_note else 'REVIEW NOTES: None recorded.',
    ])

    source_reference = f'waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome:{outcome.pk}'
    # Not get_or_create(): that helper's own internal .save() would fire
    # before `actor` could be attached to the instance for a brand-new row,
    # silently losing the "who triggered this" audit attribution for every
    # first-time sync. Constructing (or fetching) the instance first lets
    # _cg_changed_by be set before the ONE save() call that actually persists it.
    memory = EvidenceMemory.objects.filter(source_type='other', source_reference=source_reference).first()
    if memory is None:
        memory = EvidenceMemory(source_type='other', source_reference=source_reference)
    memory.text_chunk = text_chunk
    memory.verification_status = verification_status
    memory.review_tier = review_tier
    memory.document_category = 'technical_report'
    memory.is_demo = is_demo
    memory.country = matched_project.country if matched_project is not None else None
    if actor is not None:
        memory._cg_changed_by = actor
    _embed_and_save(memory)
    return memory


# Review tiers that can honestly back a 'verified' status — a row whose
# strongest recorded scrutiny is 'uploaded'/'system_checked' has not been
# verified by anyone, and this service refuses to store that contradiction.
_TIERS_SUPPORTING_VERIFIED = {'human_reviewed', 'independently_verified'}


def create_memory_from_manual_project_evidence(
    project, *, title, text, source_url='', source_type='manual',
    document_category='other', verification_status='pending',
    review_tier='uploaded', is_demo=False, date_collected=None, reviewer=None,
):
    """
    Manual/document-assisted evidence intake for a project anchored on a
    gold_intelligence.GoldProject row (the temporary generic project anchor
    per docs/adr-0001). Vertical-slice PR 1.

    Unlike the harvester/hikma/league syncs above, MANY manual evidence rows
    legitimately share one project, so (source_type, source_reference) can't
    be the idempotency key here. Instead the key is
    (source_reference, sha256(text_chunk)) — submitting the exact same text
    for the same project updates the existing row's metadata rather than
    duplicating it, while genuinely different text always creates a new row.
    The hash is the same computation EvidenceMemory.save() stores as
    integrity_reference, so the dedup key and the stored integrity value can
    never disagree.

    No company FK is ever set — a project is not a companies.CompanyProfile,
    and league-style pk-confusion is exactly what the soft-reference
    convention exists to avoid. `country` IS set from project.country when
    present: GoldProject.country and EvidenceMemory.country are the same
    real model (countries.CountryProfile), and evidence about a project in
    Kazakhstan genuinely is Kazakhstan-scoped evidence.
    """
    import hashlib

    if verification_status == 'verified' and review_tier not in _TIERS_SUPPORTING_VERIFIED:
        raise ValueError(
            f"verification_status='verified' requires review_tier in "
            f"{sorted(_TIERS_SUPPORTING_VERIFIED)} — got {review_tier!r}. A row nobody "
            f"has reviewed cannot honestly be stored as verified."
        )

    title = (title or '').strip()
    text = (text or '').strip()
    if not text:
        raise ValueError('Evidence text is required — an empty evidence record has no value to store.')
    text_chunk = f'{title} — {text}' if title else text

    source_reference = f'gold_intelligence.GoldProject:{project.pk}'
    content_hash = hashlib.sha256(text_chunk.encode('utf-8')).hexdigest()

    memory, _ = EvidenceMemory.objects.get_or_create(
        source_reference=source_reference, integrity_reference=content_hash,
        defaults={'text_chunk': text_chunk, 'source_type': source_type},
    )
    memory.text_chunk = text_chunk
    memory.source_type = source_type
    memory.source_url = source_url or ''
    memory.document_category = document_category
    memory.verification_status = verification_status
    memory.review_tier = review_tier
    memory.is_demo = is_demo
    memory.country = project.country
    memory.date_collected = date_collected
    memory.reviewer = reviewer
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


def _rank_candidates(query_text, candidates, top_k):
    """The one real ranking engine — Postgres pgvector CosineDistance, or a
    genuine Python-side cosine-similarity fallback on SQLite. Shared by
    search_similar() and retrieve_relevant_verified_outcomes() below so the
    latter is a different candidate queryset over the SAME ranking logic,
    never a second vector-search engine."""
    query_vector = compute_embedding(query_text)
    if query_vector is None:
        return EvidenceMemory.objects.none()

    candidates = candidates.filter(embedding_status='embedded')

    if connection.vendor == 'postgresql':
        from pgvector.django import CosineDistance
        return list(candidates.annotate(distance=CosineDistance('embedding', query_vector)).order_by('distance')[:top_k])

    scored = [(_cosine_similarity(m.embedding, query_vector), m) for m in candidates if m.embedding]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [memory for _, memory in scored[:top_k]]


def search_similar(query_text, top_k=DEFAULT_TOP_K, company=None, country=None):
    """
    Returns up to top_k EvidenceMemory rows most similar to query_text,
    optionally scoped to a company and/or country. Rows without a real
    embedding yet (embedding_status != 'embedded') are never returned — an
    un-embedded row has nothing meaningful to compare against.
    """
    candidates = EvidenceMemory.objects.all()
    if company is not None:
        candidates = candidates.filter(company=company)
    if country is not None:
        candidates = candidates.filter(country=country)
    return _rank_candidates(query_text, candidates, top_k)


def search_company_memory(company, query_text, top_k=DEFAULT_TOP_K):
    return search_similar(query_text, top_k=top_k, company=company)


def search_country_memory(country, query_text, top_k=DEFAULT_TOP_K):
    return search_similar(query_text, top_k=top_k, country=country)


# Vertical-slice PR 7 — RETRIEVAL FOR FUTURE DECISIONS. "Learning" here means
# retrieving real historical evidence, never automatic model retraining.
OUTCOME_SOURCE_PREFIX = 'waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome:'

# Priority order for presentation — verified/human-reviewed evidence is
# surfaced ahead of merely estimated/reported evidence at equal similarity
# rank; rejected rows are excluded from the candidate queryset entirely
# (never returned as "relevant historical evidence" at all).
_RETRIEVAL_STATUS_PRIORITY = {'verified': 0, 'requires_review': 1, 'pending': 2}


def default_outcome_query_for_project(project):
    """
    A deterministic, non-AI-generated query string built from real,
    already-stored project attributes — no live/uncontrolled AI query
    generation (see PR7 brief). Sector/resource/intervention terms are drawn
    directly from the project's own declared fields; nothing is invented.
    """
    parts = [
        project.get_commodity_display() if project.commodity else '',
        project.region or '',
        project.country.name if project.country_id else '',
        project.description or '',
    ]
    return ' '.join(p for p in parts if p).strip()


def retrieve_relevant_verified_outcomes(project, query=None, limit=DEFAULT_TOP_K):
    """
    Retrieves up to `limit` EvidenceMemory rows created from a
    VerifiedCapitalOutcome (see create_memory_from_verified_outcome()) that
    are relevant to `project` — real historical outcomes a human can consult
    while reviewing a NEW project's analysis, never a guaranteed predictor
    and never proof that EcoIQ "learned" anything automatically.

    Rejected outcomes are excluded from the candidate set entirely — they
    never surface as "relevant historical evidence". Among the remainder,
    verified/human-reviewed rows are prioritised ahead of merely estimated/
    reported ones at comparable similarity rank; demo/illustrative rows are
    never excluded outright (a demo pilot's evidence can still be
    instructive) but remain honestly labelled via is_demo on the returned
    row — the caller/template must never present one as guaranteed.

    query: an optional caller-supplied search string; if omitted, a
    deterministic query is built from the project's own real declared
    attributes (see default_outcome_query_for_project()) — never an
    uncontrolled live-AI-generated query.
    """
    query_text = query or default_outcome_query_for_project(project)
    if not query_text:
        return []

    candidates = (
        EvidenceMemory.objects
        .filter(source_reference__startswith=OUTCOME_SOURCE_PREFIX)
        .exclude(verification_status='rejected')
    )
    # Over-fetch so the priority re-sort below has real similarity-ranked
    # material to reorder within, without ever inventing extra candidates.
    ranked = _rank_candidates(query_text, candidates, top_k=max(limit * 3, limit))
    ranked = sorted(
        ranked,
        key=lambda m: _RETRIEVAL_STATUS_PRIORITY.get(m.verification_status, 3),
    )
    return ranked[:limit]
