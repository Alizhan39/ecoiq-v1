"""Internal crosswalk: 12 governance research domains → 20 existing KPI candidates.

These are CONTEXT INDICATORS, not theological scores, legal compliance tests
or certified evidence. Reuse the *actual* versioned formula registry; do not
recreate expressions, thresholds, input units or a competing KPI catalogue.

No HTTP view calls this module. The public API's sacred-source boundary stays
unchanged. A metric becomes 'measured' only via its authorised measurement
and evidence workflow; a link in this table is not evidence of anything.
"""
from __future__ import annotations

from types import MappingProxyType

from ecoiq_os.formula_registry import FORMULAS_BY_KEY
from islamic_knowledge.governance_domains import GOVERNANCE_DOMAINS, domain_by_code


_CANDIDATE_LINKS = MappingProxyType({
    "01": ("fair_procurement", "evidence_coverage", "independent_verification", "decision_review_coverage"),
    "02": ("revenue", "gross_margin", "operating_cash_flow", "liquidity_ratio",
           "asset_utilisation", "benefit_distribution"),
    "03": ("operating_cash_flow", "liquidity_ratio", "evidence_coverage", "independent_verification"),
    "04": ("worker_incident_rate", "training_hours", "living_wage_coverage", "adjusted_pay_gap"),
    "05": ("benefit_distribution", "living_wage_coverage"),
    "06": ("evidence_coverage", "independent_verification", "decision_review_coverage"),
    "07": ("training_hours", "evidence_coverage", "independent_verification"),
    "08": ("material_loss_rate", "energy_intensity", "water_intensity", "ghg_intensity",
           "waste_recovery", "freshwater_stress"),
    "09": ("living_wage_coverage", "worker_incident_rate", "benefit_distribution", "ghg_intensity"),
    "10": ("evidence_coverage", "independent_verification", "decision_review_coverage"),
    "11": ("benefit_distribution", "decision_review_coverage", "operating_cash_flow", "evidence_coverage"),
    "12": ("evidence_coverage", "independent_verification", "decision_review_coverage"),
})

if set(_CANDIDATE_LINKS) != {domain.code for domain in GOVERNANCE_DOMAINS}:
    raise AssertionError("Exactly one KPI crosswalk entry per governance research domain.")
if any(len(keys) != len(set(keys)) or not keys for keys in _CANDIDATE_LINKS.values()):
    raise AssertionError("A domain cannot have empty or repeated KPI candidate links.")
if not set().union(*map(set, _CANDIDATE_LINKS.values())) <= set(FORMULAS_BY_KEY):
    raise AssertionError("Governance crosswalk points to a missing formula definition.")


def candidate_kpis_for_domain(code: str) -> tuple[dict[str, object], ...]:
    """Neutral operational metadata; never exposes research Arabic/Quran tags."""
    domain_by_code(code)  # reject unknown codes and retain domain registry authority
    return tuple({
        "formula_key": key,
        "formula_title": FORMULAS_BY_KEY[key].title,
        "formula_validation_status": FORMULAS_BY_KEY[key].validation_status,
        "link_type": "CONTEXT_INDICATOR_ONLY",
        "evidence_status": "NOT_ASSESSED",
        "legal_compliance_verdict": None,
        "shariah_verdict": None,
        "approved_for_implementation": False,
    } for key in _CANDIDATE_LINKS[code])


def governance_crosswalk_coverage() -> dict[str, object]:
    """Inventory of CANDIDATE links, never a measured company assessment."""
    linked = set().union(*map(set, _CANDIDATE_LINKS.values()))
    return {
        "domain_count": len(GOVERNANCE_DOMAINS),
        "registry_kpi_count": len(FORMULAS_BY_KEY),
        "linked_formula_keys": tuple(sorted(linked)),
        "unlinked_formula_keys": tuple(sorted(set(FORMULAS_BY_KEY) - linked)),
        "link_status": "RESEARCH_ONLY",
        "evidence_verified": False,
    }
