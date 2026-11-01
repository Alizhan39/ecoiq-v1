"""Project-scoped, deterministic sequential previews of the 20 provisional KPI formulas.

No LLM, arbitrary expression, publication, DB mutation, or inference of source
authenticity. The existing Decimal/AST registry is the sole evaluator.
"""
from __future__ import annotations

import re

from django.shortcuts import get_object_or_404
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from ecoiq_os.formula_registry import (
    FORMULAS_BY_KEY, PROVISIONAL_KPI_FORMULAS, FormulaRejected,
    Observation, calculate_formula, formula_catalogue_view,
)
from gold_intelligence import access

PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
MAX_SOURCE_CHARS = 120
MAX_REQUEST_BYTES = 48 * 1024


class FormulaPreviewThrottle(SimpleRateThrottle):
    scope = "formula_preview"
    rate = "30/hour"

    def get_cache_key(self, request, view):
        if request.method != "POST" or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


def _private(payload, status=200):
    result = Response(payload, status=status)
    result["Cache-Control"] = "private, no-store, max-age=0"
    result["Pragma"] = "no-cache"
    result["X-Robots-Tag"] = "noindex, nofollow"
    return result


def _graph():
    """Exactly the authoritative registry order; graph never executes client-side."""
    nodes = []
    edges = []
    for i, spec in enumerate(PROVISIONAL_KPI_FORMULAS):
        row, offset = divmod(i, 4)
        column = offset if row % 2 == 0 else 3 - offset
        nodes.append({
            "id": spec.key, "type": "default",
            "position": {"x": column * 290, "y": row * 155},
            "data": {
                "key": spec.key, "label": spec.title,
                "expression": spec.expression,
                "unit": spec.output_unit,
                "ordinal": i + 1,
                "validation_status": spec.validation_status,
            },
        })
        if i:
            edges.append({
                "id": f"step_{i}",
                "source": PROVISIONAL_KPI_FORMULAS[i - 1].key,
                "target": spec.key, "type": "smoothstep", "animated": False,
            })
    return {"nodes": nodes, "edges": edges}


def _validated_request(data):
    """Strictly validate the complete request *before* evaluating any step."""
    if not isinstance(data, dict) or set(data) != {"period", "observations"}:
        raise FormulaRejected("Expected period and observations only.")
    period = data["period"]
    if not isinstance(period, str) or not PERIOD_RE.fullmatch(period):
        raise FormulaRejected("Period must be YYYY-MM.")
    raw = data["observations"]
    if not isinstance(raw, dict) or len(raw) > len(PROVISIONAL_KPI_FORMULAS):
        raise FormulaRejected("Expected at most 20 formula observation groups.")
    if set(raw) - set(FORMULAS_BY_KEY):
        raise FormulaRejected("Unknown formula key.")

    parsed = {}
    for key, supplied in raw.items():
        spec = FORMULAS_BY_KEY[key]
        expected = {item.key: item.unit for item in spec.inputs}
        if not isinstance(supplied, dict) or set(supplied) != set(expected):
            raise FormulaRejected("Each supplied formula needs exactly its declared inputs.")
        observations = {}
        for variable, unit in expected.items():
            item = supplied[variable]
            if not isinstance(item, dict) or set(item) != {"value", "source_ref"}:
                raise FormulaRejected("Each observation needs value and source_ref only.")
            source_ref = item["source_ref"]
            if (not isinstance(source_ref, str) or not 1 <= len(source_ref.strip()) <= MAX_SOURCE_CHARS
                    or any(ord(char) < 32 for char in source_ref)):
                raise FormulaRejected("Provide a bounded source identifier for each input.")
            # Values are never coerced: raw JSON floats and booleans are rejected
            # by Observation's deterministic _decimal validator.
            observations[variable] = Observation(
                value=item["value"], unit=unit, period=period, source_ref=source_ref.strip(),
            )
        parsed[key] = observations
    return period, parsed


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@throttle_classes([FormulaPreviewThrottle])
def project_formula_flow(request, project_slug):
    """GET formula definitions/graph; POST sequential preview for supplied sources.

    READ permission for GET; ANALYSE for POST. The computation never executes
    arbitrary client expressions or calls an external AI provider.
    """
    permission = access.ANALYSE if request.method == "POST" else access.READ
    project = get_object_or_404(access.projects_for(request.user, permission), slug=project_slug)

    if request.method == "GET":
        return _private({
            "project_slug": project.slug, "mode": "candidate_preview",
            "execution_enabled": False,
            "formula_count": len(PROVISIONAL_KPI_FORMULAS),
            "formulas": formula_catalogue_view(),
            **_graph(),
        })

    if (request.META.get("CONTENT_LENGTH") and
            not request.META["CONTENT_LENGTH"].isdigit()):
        return _private({"detail": "Invalid request size."}, 400)
    if int(request.META.get("CONTENT_LENGTH") or "0") > MAX_REQUEST_BYTES:
        return _private({"detail": "Formula preview request too large."}, 413)
    try:
        period, parsed = _validated_request(request.data)
    except (FormulaRejected, TypeError, ValueError):
        return _private({"detail": "Invalid formula observations or source identifiers."}, 400)

    results = []
    for index, spec in enumerate(PROVISIONAL_KPI_FORMULAS, start=1):
        if spec.key not in parsed:
            results.append({
                "sequence": index, "formula_key": spec.key,
                "status": "NOT_SUPPLIED", "value_decimal": None,
                "unit": spec.output_unit,
            })
            continue
        try:
            result = calculate_formula(spec, parsed[spec.key])
        except FormulaRejected:
            # No partial success or side effects were committed. Defensive:
            # validation should already have caught every malformed input.
            return _private({"detail": "Formula evaluation rejected."}, 400)
        results.append({"sequence": index, **result})

    return _private({
        "project_slug": project.slug, "period": period,
        "mode": "candidate_preview", "execution_enabled": False,
        "automated_publication": False, "review_required": True,
        "source_ids_verified": False, "model_called": False,
        "results": results,
    })
