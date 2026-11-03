"""Project-scoped evidence *readiness* for candidate 20-KPI process inputs.

An EvidenceMemory record is an indexed source CHUNK, never a raw verified
measurement. This service reuses the canonical project permission policy and
existing EvidenceMemory verification/retrieval gates; it makes no writes.

Even if the source record has independent-review metadata, the observed
number/unit/period remain UNVERIFIED until linked to a specific source passage
and checked by a qualified reviewer. This is a mandatory safety boundary.
"""
from __future__ import annotations

import hashlib

from django.core.exceptions import PermissionDenied
from django.http import Http404

from api.models import ProcessAnalysisRun
from ecoiq_os.formula_registry import FORMULAS_BY_KEY
from evidence_memory.models import EvidenceMemory
from evidence_memory.services.retrieval_policy import is_disputed, is_record_accessible
from gold_intelligence import access


def inspect_candidate_source(*, user, project, run_id: int,
                             formula_key: str, input_key: str,
                             evidence_memory_id: int) -> dict[str, object]:
    """Non-public source-readiness gate, without leaking inaccessible evidence.

    This can inform a later measurement-binding workflow. It does not bind a
    quantity, assert that quoted document contents match a submitted value,
    or produce an externally valid certificate.
    """
    if not access.can(user, project, access.ANALYSE):
        raise PermissionDenied("An active analyse grant is required.")

    if (type(run_id) is not int or run_id <= 0 or
            type(evidence_memory_id) is not int or evidence_memory_id <= 0):
        raise ValueError("Expected valid persisted IDs.")
    if not ProcessAnalysisRun.objects.filter(pk=run_id, project=project).exists():
        raise Http404

    spec = FORMULAS_BY_KEY.get(formula_key) if isinstance(formula_key, str) else None
    if spec is None:
        raise ValueError("Unknown candidate KPI formula.")
    contract = {item.key: item.unit for item in spec.inputs}
    if not isinstance(input_key, str) or input_key not in contract:
        raise ValueError("Unknown input for the selected formula.")

    # Lookup is bound to THIS project even when the retrieval system would
    # allow cross-project learning. A shared report is not evidence that this
    # process produced the same numeric measurement.
    memory = EvidenceMemory.objects.filter(
        pk=evidence_memory_id, project=project,
    ).select_related("originating_outcome").first()

    summary = {
        "process_analysis_id": run_id,
        "formula_key": spec.key,
        "input_key": input_key,
        "expected_unit": contract[input_key],
        "source_record_status": "NOT_ACCESSIBLE_OR_NOT_FOUND",
        "source_record_reviewed_metadata": False,
        "observed_measurement_verified": False,
        "formula_approved": False,
        "source_value_and_period_bound": False,
    }
    if memory is None or not is_record_accessible(memory, project, user):
        return summary

    reason = None
    if memory.is_demo:
        reason = "DEMONSTRATION_SOURCE"
    elif memory.verification_status in ("rejected", "expired") or is_disputed(memory):
        reason = "UNUSABLE_SOURCE"
    elif memory.is_expired:
        reason = "EXPIRED_SOURCE"
    elif not memory.source_reference.strip() and not memory.source_url.strip():
        reason = "MISSING_SOURCE_PROVENANCE"
    elif (not memory.integrity_reference or not memory.text_chunk or
          memory.integrity_reference != hashlib.sha256(memory.text_chunk.encode("utf-8")).hexdigest()):
        reason = "INTEGRITY_REFERENCE_MISMATCH"
    elif (memory.verification_status != "verified" or
          memory.review_tier != "independently_verified" or memory.reviewer_id is None):
        reason = "SOURCE_REVIEW_INCOMPLETE"

    return {
        **summary,
        "source_record_status": reason or "REVIEW_METADATA_PRESENT",
        # This flag means a *record's metadata* passes preliminary checks, not
        # independently verified business truth or approved numeric observation.
        "source_record_reviewed_metadata": reason is None,
    }
