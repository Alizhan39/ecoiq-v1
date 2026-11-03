"""Mandatory review inventory for the grounded investigation service.

Walking a registry is NOT assessing compliance. No verified observation,
applicability decision or reviewer receipt is available here. Every operational
item therefore stays NOT_ASSESSED; draft religious definitions reuse the
existing knowledge gate. This module cannot authorise a recommendation.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from core.esg_principles_data import PRINCIPLES
from ecoiq_os.formula_registry import PROVISIONAL_KPI_FORMULAS
from intelligence_analytics_engine.reform_capabilities import REFORM_CAPABILITIES
from intelligence_analytics_engine.reform_kpi_crosswalk import proposed_kpi_context
from islamic_knowledge.contracts import assess_definition
from islamic_knowledge.environmental_principles import stewardship_drafts
from islamic_knowledge.governance_domains import GOVERNANCE_DOMAINS
from islamic_knowledge.governance_kpi_crosswalk import candidate_kpis_for_domain
from islamic_knowledge.principles import DRAFT_PRINCIPLES

REVIEW_VERSION = "grounded_principle_review_v1"
_RESULT_FIELDS = frozenset({
    "status", "model_called", "evidence_count", "source_manifest", "questions",
    "project_id", "process_analysis_id", "period",
})


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def build_principle_review(*, case_id: str, subject: dict[str, Any]) -> dict[str, Any]:
    """Bind explicit review gaps to one service result and current registries.

    Counts describe inventory coverage, never assessed/approved coverage.
    No source text, Quran locators, divine names or client approval flags enter
    the report. Hashes are reproducibility identifiers, NOT signed receipts.
    """
    if not isinstance(case_id, str) or not case_id.strip() or len(case_id) > 128:
        raise ValueError("A bounded case identifier is required.")

    principles = [{
        "principle_id": row["id"], "title": row["title"],
        "question": row["question"], "status": "NOT_ASSESSED",
        "applicability": "REVIEW_REQUIRED",
    } for row in PRINCIPLES]
    if len({row["principle_id"] for row in principles}) != len(principles):
        raise ValueError("Duplicate operational principle identifier.")

    # Shared concepts retain their canonical definition, not a second copy.
    definitions = {}
    for definition in (*DRAFT_PRINCIPLES, *stewardship_drafts()):
        previous = definitions.get(definition.id)
        if previous is not None and previous != definition:
            raise ValueError("Conflicting canonical knowledge definition.")
        definitions[definition.id] = definition
    knowledge = []
    for definition in definitions.values():
        gate = assess_definition(definition, {})
        knowledge.append({
            "definition_id": definition.id, "version": definition.version,
            "definition_sha256": _digest(asdict(definition)),
            "status": "REVIEW_REQUIRED", "reasons": list(gate.reasons),
        })

    formulas = [{
        "formula_key": spec.key, "expression": spec.expression,
        "output_unit": spec.output_unit,
        "inputs": [{"key": item.key, "unit": item.unit} for item in spec.inputs],
        "validation_status": spec.validation_status, "status": "NOT_ASSESSED",
    } for spec in PROVISIONAL_KPI_FORMULAS]
    domains = [{
        "domain_code": domain.code, "title": domain.operational_title,
        "questions": list(domain.audit_questions),
        "kpi_links": list(candidate_kpis_for_domain(domain.code)),
        "status": "NOT_ASSESSED",
    } for domain in GOVERNANCE_DOMAINS]
    capabilities = [{
        **proposed_kpi_context(capability.slug),
        "required_inputs": list(capability.required_inputs),
        "safeguards": list(capability.safeguards),
        "status": "RESEARCH_PLAN_ONLY",
    } for capability in REFORM_CAPABILITIES]

    inventory = {
        "operational_principles": principles,
        "knowledge_definitions": knowledge,
        "kpi_candidates": formulas,
        "governance_domains": domains,
        "reform_capabilities": capabilities,
    }
    return {
        "version": REVIEW_VERSION,
        "scope": "ecoiq_os.prepare_grounded_draft",
        "case_id": case_id,
        "subject_sha256": _digest({"case_id": case_id, "result": subject}),
        "inventory_sha256": _digest(inventory),
        "status": "REVIEW_REQUIRED",
        "inventory_counts": {key: len(rows) for key, rows in inventory.items()},
        "assessed_operational_principles": 0,
        "all_operational_principles_assessed": False,
        "decision_ready": False,
        "publication_permitted": False,
        "implementation_permitted": False,
        "missing_requirements": [
            "reviewed_applicability_per_principle",
            "source_bound_measurements_and_claims",
            "qualified_domain_and_knowledge_review",
        ],
        **inventory,
    }


def require_principle_review(result: dict[str, Any], *, case_id: str) -> dict[str, Any]:
    """Final server-owned envelope; caller/model flags cannot approve a draft.

    Citation validation and access checks must run BEFORE this function. This
    coverage gate is not a semantic judge of an LLM's prose. It never replaces
    the company publication policy, the OS kernel or expert review receipts.
    """
    safe = {
        **{key: value for key, value in result.items() if key in _RESULT_FIELDS},
        "decision_ready": False,
        "production_approved": False,
        "independently_verified_causality": False,
        "publication_permitted": False,
        "implementation_permitted": False,
        "approval_recorded": False,
        "requires_human_review": True,
        "causal_conclusion": None,
        "savings_forecast": None,
        "mizan_score": None,
    }
    # The closed output shape excludes reports and approvals from other layers.
    return {**safe, "principle_review": build_principle_review(case_id=case_id, subject=safe)}
