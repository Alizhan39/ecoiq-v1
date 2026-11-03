"""Persist source-*linked*, not source-*verified*, 20-KPI input claims.

This non-public service enforces project permissions and the exact formula
input/unit contract. No claims that an independently reviewed source chunk
has been proven to contain, support or uniquely determine the reported value.
No public API, formula approval, automatic publishing or LLM calls.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404

from api.models import ProcessAnalysisRun, ProcessKPIMeasurementClaim
from api.process_kpi_evidence_readiness import inspect_candidate_source
from ecoiq_os.formula_registry import FORMULAS_BY_KEY, Observation
from evidence_memory.models import EvidenceMemory
from gold_intelligence import access


def _spec_digest(spec) -> str:
    """Bind the claim to a specific registry definition, not a floating key."""
    data = {
        "key": spec.key,
        "expression": spec.expression,
        "output_unit": spec.output_unit,
        "inputs": [(i.key, i.unit) for i in spec.inputs],
        "validation_status": spec.validation_status,
    }
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@transaction.atomic
def create_process_kpi_measurement_claim(*, user, project, run_id: int,
                                         formula_key: str, input_key: str,
                                         evidence_memory_id: int,
                                         reported_value: str | int | Decimal) -> ProcessKPIMeasurementClaim:
    """Append a reported input; independent numeric verification is NOT done.

    Source metadata is rechecked under the DB transaction before insertion.
    Historical claims may be superseded by new claims, never silently
    rewritten by this service.
    """
    if not access.can(user, project, access.ANALYSE):
        raise PermissionDenied("An active project analyse grant is required.")
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("Invalid analysis id.")
    if type(evidence_memory_id) is not int or evidence_memory_id <= 0:
        raise ValueError("Invalid source id.")

    analysis = ProcessAnalysisRun.objects.select_for_update().filter(
        pk=run_id, project=project,
    ).first()
    if analysis is None:
        raise Http404

    spec = FORMULAS_BY_KEY.get(formula_key) if isinstance(formula_key, str) else None
    if spec is None:
        raise ValueError("Unknown KPI formula.")
    canonical_inputs = {i.key: i.unit for i in spec.inputs}
    if not isinstance(input_key, str) or input_key not in canonical_inputs:
        raise ValueError("Input is not declared for this KPI.")
    unit = canonical_inputs[input_key]

    # Validate through the very same bounded Decimal/period/unit contract as
    # the 20 candidate formula engine. Caller cannot supply a different unit
    # or period; these come from the registry and the saved process run.
    observation = Observation(
        value=reported_value, unit=unit, period=analysis.period,
        source_ref=f"evidence_memory:{evidence_memory_id}",
    )
    value = Decimal(observation.value)
    # DecimalField must not coerce or round an overprecise caller input.
    # Limit reported precision in this first storage schema to 18 places.
    if value.as_tuple().exponent < -18 or len(value.as_tuple().digits) > 44:
        raise ValueError("Unsupported measurement precision.")

    source = EvidenceMemory.objects.select_for_update().filter(
        pk=evidence_memory_id, project=project,
    ).first()
    if source is None:
        raise ValueError("Source is not accessible or not suitable.")

    status = inspect_candidate_source(
        user=user, project=project, run_id=analysis.pk, formula_key=spec.key,
        input_key=input_key, evidence_memory_id=evidence_memory_id,
    )
    if status["source_record_status"] != "REVIEW_METADATA_PRESENT":
        raise ValueError("Source is not accessible or does not pass preliminary review.")

    # Store the source CHUNK's current content digest. This is a snapshot of
    # indexed text, not a signature of the original full document.
    return ProcessKPIMeasurementClaim.objects.create(
        project=project, analysis=analysis, evidence=source, created_by=user,
        formula_key=spec.key, input_key=input_key, value_decimal=value,
        unit=unit, period=analysis.period,
        source_chunk_sha256=source.integrity_reference,
        formula_spec_sha256=_spec_digest(spec),
        review_status=ProcessKPIMeasurementClaim.ReviewStatus.REPORTED_NOT_VERIFIED,
    )


def claims_for_process(*, user, project, run_id: int):
    """Private queryset; the caller must still gate serialization/output."""
    if not access.can(user, project, access.READ):
        raise PermissionDenied("An active project read grant is required.")
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("Invalid analysis id.")
    if not ProcessAnalysisRun.objects.filter(pk=run_id, project=project).exists():
        raise Http404
    return ProcessKPIMeasurementClaim.objects.filter(
        project=project, analysis_id=run_id,
    ).order_by("-created_at", "-pk")
