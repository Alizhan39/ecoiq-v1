"""Commercial Situation Intelligence: evidence-first calculation + Quran locator hints.

Sits on the EXISTING EcoIQ Decision & Islah kernel. It does not train on
religious text, quote unlicensed passages, issue a fatwa, infer moral guilt,
approve operations or call an external LLM. Scripture links are DRAFT editorial
research locators from islamic_knowledge.principles, NOT expert-reviewed tafsir.
"""
from __future__ import annotations

from math import isfinite
from typing import Any

from ecoiq_os.decision_islah import build_preliminary_brief
from islamic_knowledge.principles import DRAFT_PRINCIPLES

DRAFT_LENSES = {item.concept: item for item in DRAFT_PRINCIPLES}

# Fixed, explainable triage rule. Does NOT claim a theological relationship is
# proved. More sensitive concepts (fasad/justice allegations) are not triggered
# merely from a numerical loss ratio.
KNOWN_LOSS_LENSES = ("amanah", "mizan", "israf", "islah", "adl")
UNKNOWN_LENSES = ("amanah", "mizan")
ZERO_LOSS_LENSES = ("amanah", "mizan", "islah")


def _measured(value: Any) -> float | None:
    if value is None:
        return None
    if type(value) not in (float, int) or not isfinite(value) or value < 0:
        raise ValueError("Measured values must be finite non-negative numbers or None.")
    return float(value)


def _calculation_rows(*, reported_input: float | None,
                      reported_loss: float | None, unit: str) -> list[dict[str, Any]]:
    """Reported quantities, never financial forecasts or independently proven yield."""
    total = _measured(reported_input)
    loss = _measured(reported_loss)
    if total is not None and loss is not None and loss > total:
        raise ValueError("Loss cannot exceed input in the stated boundary.")
    value = (round(loss / total * 100, 4)
             if total is not None and total > 0 and loss is not None else None)
    remainder = (round(total - loss, 4)
                 if total is not None and loss is not None else None)
    return [
        {
            "key": "reported_loss_rate",
            "label": "Recorded loss relative to reported input",
            "formula": "reported_loss / reported_input * 100",
            "value": value,
            "unit": "%",
            "status": "REPORTED_ONLY" if value is not None else "INSUFFICIENT_DATA",
            "required_inputs": ["reported_input", "reported_loss"],
            "interpretation_limit": (
                "This is an arithmetic ratio. It is not evidence of avoidable waste, "
                "a causal mechanism or a religious judgement."
            ),
        },
        {
            "key": "reported_arithmetic_difference",
            "label": "Reported input minus recorded loss (arithmetic only)",
            "formula": "reported_input - reported_loss",
            "value": remainder,
            "unit": unit,
            "status": "REPORTED_ONLY" if remainder is not None else "INSUFFICIENT_DATA",
            "required_inputs": ["reported_input", "reported_loss"],
            "interpretation_limit": (
                "The difference is not independently verified physical output, "
                "product yield or financial saving."
            ),
        },
        {
            "key": "recoverable_savings",
            "label": "Savings attributable to a tested intervention",
            "formula": "verified_avoidable_quantity * verified_unit_economic_value - verified_intervention_cost",
            "value": None,
            "unit": "currency/period",
            "status": "REQUIRES_CAUSAL_EVIDENCE_AND_COSTS",
            "required_inputs": [
                "verified_avoidable_quantity", "verified_unit_economic_value",
                "verified_intervention_cost",
            ],
            "interpretation_limit": "No avoidability, price, cost or causal impact is established.",
        },
    ]


def _locator_hints(lenses: tuple[str, ...]) -> list[dict[str, Any]]:
    references = []
    for concept in lenses:
        definition = DRAFT_LENSES[concept]
        locators = [
            {"locator": reference.locator,
             "url": f"https://quran.com/{reference.surah}/{reference.ayah_start}"
                    + (f"-{reference.ayah_end}" if reference.ayah_end else "")}
            for reference in definition.quran_references
        ]
        references.append({
            "concept": concept,
            "research_question": definition.statement,
            "source_type": "EDITORIAL_RESEARCH_LOCATOR_ONLY",
            "review_state": "SCHOLAR_REVIEW_REQUIRED",
            "verse_text_provided": False,
            "tafsir_provided": False,
            "shariah_verdict": None,
            "references": locators,
        })
    return references


def assemble_situation_guidance(brief: dict[str, Any]) -> dict[str, Any]:
    """Compose a safe guided investigation from a *validated* canonical brief."""
    if brief.get("engine") != "DETERMINISTIC_DECISION_BRIEF_V1":
        raise ValueError("Only a canonical validated decision brief is accepted.")
    if brief.get("implementation_permitted") is not False:
        raise ValueError("Untrusted implementation approval must never enter guidance.")
    # Reconstruct from raw aggregates to avoid trusting a mutable stored
    # 'verified', 'loss_rate', 'savings', 'causal' or model-generated field.
    canonical = build_preliminary_brief(
        case_id=brief["case_id"], domain=brief["domain"],
        process_name=brief["process_name"],
        resource_type=brief["resource_type"], period=brief["period"],
        unit=brief["unit"], reported_input=brief["observed_input"],
        reported_loss=brief["observed_loss"],
    )
    calculations = _calculation_rows(
        reported_input=canonical["observed_input"],
        reported_loss=canonical["observed_loss"], unit=canonical["unit"],
    )
    observed = calculations[0]["value"]
    if observed is None:
        assessment = "INSUFFICIENT_REPORTED_DATA"
        lenses = UNKNOWN_LENSES
    elif observed == 0:
        assessment = "NO_REPORTED_LOSS_IN_THIS_BOUNDARY"
        lenses = ZERO_LOSS_LENSES
    else:
        assessment = "REPORTED_LOSS_REQUIRES_INVESTIGATION"
        lenses = KNOWN_LOSS_LENSES
    return {
        "engine": "ECOIQ_SITUATION_GUIDANCE_V1",
        "mode": "DETERMINISTIC_EVIDENCE_TRIAGE",
        "ai_model_called": False,
        "ai_questions_available_only_via_reviewed_evidence_gateway": True,
        "situation": assessment,
        "formulas": calculations,
        "guidance_lenses": _locator_hints(lenses),
        "next_step": canonical["next_stage"],
        "investigation_questions": [
            item["question"] for item in canonical["hypotheses"]
        ],
        "missing_evidence": canonical["missing_evidence"],
        "safety_constraints": {
            "independently_verified": False,
            "causal_conclusion": None,
            "religious_approval": None,
            "shariah_verdict": None,
            "savings_forecast": None,
            "implementation_permitted": False,
            "human_review_required_before_consequential_action": True,
            "religious_interpretation_requires_qualified_scholar": True,
        },
        "guidance_notice": (
            "Qur'anic references are draft research pointers, not quoted Scripture, "
            "tafsir, a fatwa, or proof that a company complies with Islam. "
            "Check original verses, translation, context and recognised scholarly "
            "views with qualified experts before any normative religious guidance."
        ),
    }
