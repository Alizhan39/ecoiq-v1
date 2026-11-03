"""Read-only, project-scoped coverage review of *all* 20 candidate KPI formulas.

A ProcessAnalysisRun stores only an aggregate CSV diagnostic, not its original
observations. Never pretend its summary is source data or transform a CSV
aggregate into twenty independently supported KPI measurements.

Caller explicitly supplies a bounded set of reported measurements; common
variables are shared across formulas with the same declared unit. No implicit
mapping from one calculated KPI into another and no AI-model execution.
"""
from __future__ import annotations

import re
from typing import Mapping

from django.shortcuts import get_object_or_404
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import ProcessAnalysisRun
from api.v2_formula_flow import FormulaPreviewThrottle, _private
from ecoiq_os.formula_registry import (
    FormulaRejected, Observation, PROVISIONAL_KPI_FORMULAS,
    calculate_formula, formula_catalogue_view,
)
from gold_intelligence import access

MAX_REQUEST_BYTES = 48 * 1024
SOURCE_MAX = 120
PARAMETER_KEY = re.compile(r"^[a-z][a-z0-9_]{0,49}$")


def parameter_contract() -> tuple[dict[str, str], list[dict[str, object]]]:
    """Registry-derived canonical variable/unit map; fail closed on collisions."""
    units: dict[str, str] = {}
    used_by: dict[str, list[str]] = {}
    for spec in PROVISIONAL_KPI_FORMULAS:
        for item in spec.inputs:
            if item.key in units and units[item.key] != item.unit:
                raise AssertionError("Conflicting units for a shared process parameter.")
            units[item.key] = item.unit
            used_by.setdefault(item.key, []).append(spec.key)
    contract = [
        {"key": key, "unit": unit, "used_by": used_by[key]}
        for key, unit in units.items()
    ]
    return units, contract


def _parse_measurements(raw: object, period: str) -> dict[str, Observation]:
    units, _ = parameter_contract()
    if not isinstance(raw, dict) or len(raw) > len(units):
        raise FormulaRejected("Invalid process measurements.")
    if not set(raw).issubset(units):
        raise FormulaRejected("Unknown process parameter.")
    parsed = {}
    for key, item in raw.items():
        if not isinstance(key, str) or not PARAMETER_KEY.fullmatch(key):
            raise FormulaRejected("Invalid parameter name.")
        if not isinstance(item, dict) or set(item) != {"value", "unit", "source_ref"}:
            raise FormulaRejected("Expected value, unit and source_ref.")
        if item["unit"] != units[key]:
            raise FormulaRejected("Parameter has a conflicting unit.")
        ref = item["source_ref"]
        if (
            not isinstance(ref, str)
            or not 1 <= len(ref.strip()) <= SOURCE_MAX
            or any(ord(char) < 32 or ord(char) == 127 for char in ref)
        ):
            raise FormulaRejected("Invalid source identifier.")
        parsed[key] = Observation(
            value=item["value"], unit=units[key], period=period, source_ref=ref.strip(),
        )
    return parsed


def evaluate_all_formulas(
    measurements: Mapping[str, Observation],
) -> dict[str, object]:
    """Visit each registry item exactly once; preserve absent vs undefined.

    Input is already fully parsed. No external process or evidence service is
    invoked, no writes and no automatic formula/expert approvals are possible.
    """
    results: list[dict[str, object]] = []
    counts = {"reported_not_verified": 0, "needs_measurements": 0, "blocked": 0}
    for sequence, spec in enumerate(PROVISIONAL_KPI_FORMULAS, start=1):
        expected = [item.key for item in spec.inputs]
        missing = [key for key in expected if key not in measurements]
        if missing:
            counts["needs_measurements"] += 1
            result = {
                "sequence": sequence,
                "formula_key": spec.key,
                "formula_version": "candidate_formula_registry_v1",
                "status": "NEEDS_MEASUREMENTS",
                "value_decimal": None,
                "unit": spec.output_unit,
                "missing_inputs": missing,
                "review_status": spec.validation_status,
                "approved_for_implementation": False,
                "verified_evidence": False,
                "shariah_verdict": None,
            }
        else:
            scoped = {key: measurements[key] for key in expected}
            response = calculate_formula(spec, scoped)
            result = {"sequence": sequence, **response, "missing_inputs": []}
            if response["status"] == "REPORTED_NOT_VERIFIED":
                counts["reported_not_verified"] += 1
            else:
                counts["blocked"] += 1
        results.append(result)
    return {
        "formula_count": len(PROVISIONAL_KPI_FORMULAS),
        "counts": counts,
        "results": results,
        "automated_publication": False,
        "review_required": True,
        "source_identifiers_verified": False,
        "model_called": False,
        "all_formulas_visited": True,
    }


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@throttle_classes([FormulaPreviewThrottle])
def process_formula_review(request, project_slug: str, run_id: int):
    """Preview coverage for one real, permission-checked ProcessAnalysisRun.

    GET: project READ, show registry and required shared parameters, no private
    observations. POST: project ANALYSE, validate before calculating 20 steps.
    Both modes bind project and period to a saved DB run, never client claims.
    """
    permission = access.ANALYSE if request.method == "POST" else access.READ
    project = get_object_or_404(access.projects_for(request.user, permission), slug=project_slug)
    analysis = get_object_or_404(
        ProcessAnalysisRun.objects.only(
            "id", "project_id", "case_id", "domain", "process_name", "period",
        ),
        project=project, pk=run_id,
    )
    context = {
        "project_slug": project.slug,
        "process_analysis_id": analysis.pk,
        "case_id": analysis.case_id,
        "domain": analysis.domain,
        "process_name": analysis.process_name,
        "period": analysis.period,
        "mode": "process_formula_review",
        "production_approved": False,
    }
    if request.method == "GET":
        _, parameters = parameter_contract()
        return _private({
            **context,
            "formulas": formula_catalogue_view(),
            "parameters": parameters,
            "can_preview_calculate": access.can(request.user, project, access.ANALYSE),
            "source_measurements_stored_in_process_analysis": False,
        })

    declared = request.META.get("CONTENT_LENGTH", "")
    if declared:
        if not declared.isdigit():
            return _private({"detail": "Invalid request size."}, 400)
        if int(declared) > MAX_REQUEST_BYTES:
            return _private({"detail": "Request exceeds size limit."}, 413)

    if not isinstance(request.data, dict) or set(request.data) != {"measurements"}:
        return _private({"detail": "Expected measurements only."}, 400)
    try:
        measurements = _parse_measurements(request.data["measurements"], analysis.period)
        evaluated = evaluate_all_formulas(measurements)
    except (FormulaRejected, TypeError, ValueError):
        return _private({"detail": "Invalid process measurements."}, 400)

    return _private({**context, **evaluated})
