"""Internal mapping: proposed reform research capabilities → existing candidate KPIs.

Links are descriptive context signals ONLY. They cannot prove a root cause,
regulatory conflict, corruption, Shariah compliance, public value or policy
impact. Never infer a missing legal/social/economic indicator from an unrelated
metric; gaps are declared explicitly.
"""
from __future__ import annotations

from types import MappingProxyType

from ecoiq_os.formula_registry import FORMULAS_BY_KEY
from intelligence_analytics_engine.reform_capabilities import (
    REFORM_CAPABILITIES, capability_by_slug,
)


# These are contextual indicators. Zero links is honest if no existing KPI
# can defensibly measure the proposed capability's outcome.
_REFORM_LINKS = MappingProxyType({
    "root_cause": ("evidence_coverage", "independent_verification", "decision_review_coverage"),
    "regulatory_conflict": ("evidence_coverage", "decision_review_coverage"),
    "economic_digital_twin": ("revenue", "gross_margin", "operating_cash_flow",
                              "liquidity_ratio", "energy_intensity"),
    "anti_corruption": ("fair_procurement", "independent_verification", "decision_review_coverage"),
    "wealth_distribution": ("benefit_distribution", "adjusted_pay_gap", "living_wage_coverage"),
    "public_budget": ("benefit_distribution", "operating_cash_flow", "fair_procurement"),
    "legal_access": (),  # No legal-access KPI in the existing 20; do not pretend.
    "islamic_finance": ("operating_cash_flow", "liquidity_ratio", "evidence_coverage"),
    "future_generations": ("ghg_intensity", "freshwater_stress", "waste_recovery",
                           "worker_incident_rate"),
    "ai_accountability": ("evidence_coverage", "independent_verification", "decision_review_coverage"),
    "reform_experiments": ("evidence_coverage", "independent_verification", "decision_review_coverage"),
    "institutional_memory": ("evidence_coverage", "decision_review_coverage", "independent_verification"),
})


if set(_REFORM_LINKS) != {item.slug for item in REFORM_CAPABILITIES}:
    raise AssertionError("Every reform capability must explicitly declare its KPI crosswalk.")
if any(len(keys) != len(set(keys)) for keys in _REFORM_LINKS.values()):
    raise AssertionError("Duplicate crosswalk KPI key.")
if any(key not in FORMULAS_BY_KEY for keys in _REFORM_LINKS.values() for key in keys):
    raise AssertionError("Reform crosswalk references an unknown canonical KPI key.")


def proposed_kpi_context(slug: str) -> dict[str, object]:
    """No observed inputs, reviewed source binding, score or policy conclusion."""
    capability = capability_by_slug(slug)
    keys = _REFORM_LINKS[slug]
    return {
        "capability": capability.slug,
        "kpi_relation": "CONTEXT_ONLY_NOT_OUTCOME_MEASURE",
        "formula_links": tuple({
            "formula_key": key,
            "formula_title": FORMULAS_BY_KEY[key].title,
            "validation_status": FORMULAS_BY_KEY[key].validation_status,
            "measured": False,
        } for key in keys),
        "missing_direct_kpi": not bool(keys),
        "source_authentication": "NOT_PERFORMED",
        "professional_review": "NOT_PERFORMED",
        "decision_ready": False,
    }
