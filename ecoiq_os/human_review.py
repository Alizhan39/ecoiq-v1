"""Stage 7: restricted human review of AI investigation questions.

This workflow can accept *questions for study* only. It never upgrades an
evidence record, authorises external provider transfer, changes a KPI, or
authorises an Islah action. Queue creation is internal, NOT an HTTP upload.
"""
from __future__ import annotations

import hashlib
import json
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from api.models import (
    ProcessAIProcessingReadiness, ProcessAIReviewCase,
    ProcessAIReviewEvent, ProcessAnalysisRun,
)
from ecoiq_os.grounded_ai import (
    MAX_SOURCE_CHARS, GroundedSource, collect_reviewed_sources,
    validate_grounded_questions,
)
from gold_intelligence import access


class ReviewBlocked(ValueError):
    """User-visible, no document text in exception payloads."""


DECISIONS = {
    "accept": ProcessAIReviewCase.Status.ACCEPTED,
    "reject": ProcessAIReviewCase.Status.REJECTED,
    "revise": ProcessAIReviewCase.Status.REVISION,
}
REASON_CODES = frozenset({
    "citations_checked", "needs_more_evidence", "misleading_interpretation",
    "confidentiality_concern", "out_of_scope",
})


def _digest(questions, manifest) -> str:
    content = json.dumps(
        {"questions": questions, "manifest": manifest},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _review_sources(project, user, manifest):
    """Re-read source rows, not a cached prompt or submitted source claim."""
    from evidence_memory.models import EvidenceMemory
    from evidence_memory.services.retrieval_policy import (
        is_disputed, is_record_accessible,
    )

    if not access.can(user, project, access.READ):
        return None
    if not isinstance(manifest, list) or not 1 <= len(manifest) <= 4:
        return None
    sources = []
    used = set()
    for index, item in enumerate(manifest, start=1):
        if not isinstance(item, dict) or set(item) != {
            "key", "memory_id", "review_tier", "sha256",
        }:
            return None
        memory_id = item["memory_id"]
        if (type(memory_id) is not int or memory_id in used
                or item["key"] != f"S{index}"
                or item["review_tier"] != "independently_verified"):
            return None
        used.add(memory_id)
        memory = (EvidenceMemory.objects.filter(pk=memory_id, project=project)
                  .select_related("originating_outcome").first())
        if (memory is None or not is_record_accessible(memory, project, user=user)
                or memory.visibility != "project_private"
                or memory.verification_status != "verified"
                or memory.review_tier != "independently_verified"
                or memory.reviewer_id is None
                or memory.is_demo or memory.is_expired or is_disputed(memory)
                or memory.source_type == "agent_output"
                or memory.legal_status in ("disputed", "superseded")
                or not memory.source_reference.strip()
                or not memory.text_chunk.strip()):
            return None
        digest = hashlib.sha256(memory.text_chunk.encode("utf-8")).hexdigest()
        if item["sha256"] != digest or memory.integrity_reference != digest:
            return None
        sources.append(GroundedSource(
            key=item["key"], memory_id=memory.pk,
            excerpt=memory.text_chunk[:MAX_SOURCE_CHARS],
            review_tier=memory.review_tier, content_sha256=digest,
        ))
    return tuple(sources)


def _check_questions(questions, sources) -> list[dict] | None:
    if not isinstance(questions, list) or not 1 <= len(questions) <= 3:
        return None
    sanitized = []
    for question in questions:
        if (not isinstance(question, dict) or set(question) != {
            "question", "citations", "status", "implementation_permitted",
        } or question["status"] != "UNTESTED"
                or question["implementation_permitted"] is not False):
            return None
        citations = question["citations"]
        if not isinstance(citations, list):
            return None
        cleaned = []
        for citation in citations:
            if not isinstance(citation, dict) or set(citation) != {
                "key", "memory_id", "quote",
            }:
                return None
            key = citation["key"]
            if not any(src.key == key and src.memory_id == citation["memory_id"]
                       for src in sources):
                return None
            cleaned.append({"key": key, "quote": citation["quote"]})
        sanitized.append({"question": question["question"], "citations": cleaned})

    validation = validate_grounded_questions(
        json.dumps({"questions": sanitized}), sources,
    )
    if validation["status"] != "REVIEW_REQUIRED":
        return None
    return validation["questions"]


def queue_grounded_review(*, project, user, run, model_result) -> ProcessAIReviewCase:
    """Internal trusted code only; client-supplied model output is not admitted."""
    if not access.can(user, project, access.ANALYSE) or run.project_id != project.pk:
        raise PermissionDenied("Project analysis permission required.")
    if (not isinstance(model_result, dict)
            or model_result.get("status") != "REVIEW_REQUIRED"
            or model_result.get("model_called") is not True
            or model_result.get("approval_recorded") is not False
            or model_result.get("implementation_permitted") is not False):
        raise ReviewBlocked("Only validated, unapproved AI question drafts can be queued.")

    sources = collect_reviewed_sources(project=project, user=user)
    manifest = model_result.get("source_manifest")
    expected = [
        {"key": src.key, "memory_id": src.memory_id,
         "review_tier": src.review_tier, "sha256": src.content_sha256}
        for src in sources
    ]
    if not sources or manifest != expected:
        raise ReviewBlocked("The source evidence changed; request a new draft.")
    validated = _check_questions(model_result.get("questions"), sources)
    if validated is None or validated != model_result["questions"]:
        raise ReviewBlocked("Question citations did not pass independent validation.")

    questions = validated
    with transaction.atomic():
        if not access.can(user, project, access.ANALYSE):
            raise PermissionDenied("Analysis grant was revoked.")
        if _review_sources(project, user, manifest) != sources:
            raise ReviewBlocked("The source evidence changed; request a new draft.")
        digest = _digest(questions, manifest)
        case = ProcessAIReviewCase.objects.create(
            project=project, analysis=run, submitted_by=user,
            questions=questions, source_manifest=manifest, content_sha256=digest,
        )
        ProcessAIReviewEvent.objects.create(
            case=case, actor=user, action="submitted", content_sha256=digest,
        )
        return case


def inspect_review_case(*, project, actor, case):
    """Return source previews only to an active reviewer for the same project."""
    if not access.can(actor, project, access.APPROVE) or case.project_id != project.pk:
        raise PermissionDenied("Review permission required.")
    sources = _review_sources(project, actor, case.source_manifest)
    valid = (sources is not None
             and _digest(case.questions, case.source_manifest) == case.content_sha256
             and _check_questions(case.questions, sources) == case.questions)
    return {
        "is_current": valid,
        "questions": case.questions if valid else [],
        "sources": ([{"key": src.key, "memory_id": src.memory_id,
                      "excerpt": src.excerpt} for src in sources] if valid else []),
    }


def decide_grounded_review(*, project, actor, case_id, decision, reason_code):
    """One decision per queued draft, with append-only-by-service audit event."""
    if decision not in DECISIONS or reason_code not in REASON_CODES:
        raise ReviewBlocked("Choose an allowed decision and reason.")
    if decision == "accept" and reason_code != "citations_checked":
        raise ReviewBlocked("Accepting study questions requires the citations_checked reason.")
    with transaction.atomic():
        if not access.can(actor, project, access.APPROVE):
            raise PermissionDenied("Review permission required.")
        case = (ProcessAIReviewCase.objects.select_for_update()
                .filter(pk=case_id, project=project).first())
        if case is None:
            raise ReviewBlocked("Review not available.")
        if actor.pk == case.submitted_by_id:
            raise ReviewBlocked("A person cannot approve their own draft.")
        if case.status != ProcessAIReviewCase.Status.PENDING:
            raise ReviewBlocked("The review has already been decided.")
        if case.analysis.project_id != project.pk:
            raise ReviewBlocked("Review ownership changed.")

        snapshot = inspect_review_case(project=project, actor=actor, case=case)
        if not snapshot["is_current"]:
            raise ReviewBlocked("Source content or verification has changed.")
        case.status = DECISIONS[decision]
        case.reviewed_by = actor
        case.reviewed_at = timezone.now()
        case.reason_code = reason_code
        case.save(update_fields=["status", "reviewed_by", "reviewed_at", "reason_code"])
        ProcessAIReviewEvent.objects.create(
            case=case, actor=actor, action=decision, reason_code=reason_code,
            content_sha256=case.content_sha256,
        )
    return case


def record_processing_readiness(*, project, analysis, actor, checks):
    """A checklist/audit record only, NOT authorisation for external AI calls."""
    if not access.can(actor, project, access.APPROVE):
        raise PermissionDenied("Review permission required.")
    if not isinstance(analysis, ProcessAnalysisRun) or analysis.project_id != project.pk:
        raise ReviewBlocked("Invalid analysis scope.")
    if checks != {
        "source_rights": True, "privacy": True, "provider_terms": True,
    }:
        raise ReviewBlocked("All three checks must be explicitly completed.")

    with transaction.atomic():
        if not access.can(actor, project, access.APPROVE):
            raise PermissionDenied("Review grant was revoked.")
        now = timezone.now()
        return ProcessAIProcessingReadiness.objects.create(
            project=project, analysis=analysis, recorded_by=actor,
            source_rights_reviewed=True, privacy_reviewed=True,
            provider_terms_reviewed=True,
            authorises_external_transfer=False,
            expires_at=now + timedelta(days=7),
        )
