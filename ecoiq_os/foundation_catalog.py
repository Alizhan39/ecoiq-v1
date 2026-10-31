"""Versioned *candidate* Business Plan 2.0 KPI catalogue for foundation research.

33 operational questions, 20 v1-priority questions. These are neither the
existing public EcoIQ score nor religious interpretations. Units/formulas need
external sector validation. Training data uses SYNTHETIC risk signals, never
reported performance of companies or actual verse links.
"""
from __future__ import annotations

from dataclasses import dataclass

from islamic_knowledge.catalog import divine_names, surahs

CATEGORIES = ("financial", "resource", "environmental", "social", "justice", "accountability")


@dataclass(frozen=True)
class CandidateKPI:
    key: str
    title: str
    category: str
    unit_hint: str
    priority_v1: bool
    principle_lenses: tuple[str, ...]

    def __post_init__(self):
        if not self.key or not self.title or not self.unit_hint:
            raise ValueError("Candidate KPI needs an identifier, title and unit hint.")
        if self.category not in CATEGORIES:
            raise ValueError("Unknown KPI category.")
        if not self.principle_lenses or set(self.principle_lenses) - {
            "mizan", "amanah", "adl", "islah", "israf", "fasad",
        }:
            raise ValueError("Unknown analytic principle lens.")
        if type(self.priority_v1) is not bool:
            raise ValueError("KPI priority must be boolean.")


def _k(key, title, category, unit, priority, *lenses):
    return CandidateKPI(key, title, category, unit, priority, tuple(lenses))


KPI_CATALOG = (
    # Financial (6; 4 initial).
    _k("revenue", "Reported revenue", "financial", "currency/period", True, "mizan", "amanah"),
    _k("gross_margin", "Reported gross margin", "financial", "%", True, "mizan"),
    _k("operating_cash_flow", "Reported operating cash flow", "financial", "currency/period", True, "amanah"),
    _k("liquidity_ratio", "Liquidity coverage", "financial", "ratio", True, "mizan"),
    _k("debt_service_coverage", "Debt service coverage", "financial", "ratio", False, "amanah"),
    _k("reinvestment_rate", "Reinvestment rate", "financial", "%", False, "islah"),
    # Resource and operations (6; 4 initial).
    _k("material_loss_rate", "Recorded material loss", "resource", "%", True, "israf"),
    _k("energy_intensity", "Energy intensity", "resource", "kWh/unit", True, "israf", "mizan"),
    _k("water_intensity", "Water intensity", "resource", "m3/unit", True, "mizan", "israf"),
    _k("asset_utilisation", "Asset utilisation", "resource", "%", True, "islah"),
    _k("process_cycle_time", "Process cycle time", "resource", "hours/unit", False, "islah"),
    _k("rework_rate", "Rework rate", "resource", "%", False, "israf"),
    # Environment (6; 3 initial).
    _k("ghg_intensity", "Reported GHG intensity", "environmental", "tCO2e/unit", True, "mizan", "fasad"),
    _k("waste_recovery", "Waste recovery", "environmental", "%", True, "islah", "israf"),
    _k("freshwater_stress", "Freshwater stress exposure", "environmental", "site risk index", True, "mizan"),
    _k("effluent_breaches", "Regulated effluent breaches", "environmental", "count/period", False, "fasad"),
    _k("habitat_impact", "Affected habitat", "environmental", "hectares", False, "fasad"),
    _k("remediation_completion", "Verified remediation completion", "environmental", "%", False, "islah"),
    # Social (5; 3 initial).
    _k("worker_incident_rate", "Worker incident rate", "social", "incidents/hours", True, "amanah", "mizan"),
    _k("training_hours", "Training per worker", "social", "hours/person", True, "islah"),
    _k("living_wage_coverage", "Living-wage coverage", "social", "%", True, "adl"),
    _k("grievance_resolution", "Community grievance resolution", "social", "%", False, "adl"),
    _k("service_access", "Accessible service coverage", "social", "%", False, "adl", "mizan"),
    # Distributional justice (5; 3 initial).
    _k("adjusted_pay_gap", "Explained pay gap", "justice", "%", True, "adl"),
    _k("fair_procurement", "Fair procurement process coverage", "justice", "%", True, "adl", "amanah"),
    _k("benefit_distribution", "Documented beneficiary distribution", "justice", "share by group", True, "adl", "mizan"),
    _k("appeal_access", "Stakeholder appeal access", "justice", "%", False, "adl"),
    _k("case_resolution", "Fair-treatment case resolution", "justice", "%", False, "adl"),
    # Responsibility and auditability (5; 3 initial).
    _k("evidence_coverage", "KPI evidence coverage", "accountability", "%", True, "amanah"),
    _k("independent_verification", "Independently verified KPI share", "accountability", "%", True, "amanah"),
    _k("decision_review_coverage", "Human-reviewed consequential decisions", "accountability", "%", True, "amanah", "islah"),
    _k("audit_issues_closed", "Closed audit findings", "accountability", "%", False, "islah"),
    _k("corrective_actions_closed", "Closed corrective actions", "accountability", "%", False, "islah"),
)

KPI_KEYS = tuple(item.key for item in KPI_CATALOG)
INITIAL_KPI_KEYS = tuple(item.key for item in KPI_CATALOG if item.priority_v1)


def catalogue_summary() -> dict[str, object]:
    """Describe coverage, not evaluate people/companies or religious compliance."""
    if len(KPI_CATALOG) != 33 or len(set(KPI_KEYS)) != 33:
        raise AssertionError("The v1 draft catalogue must have 33 unique operational KPI definitions.")
    if len(INITIAL_KPI_KEYS) != 20:
        raise AssertionError("Business Plan 2.0 draft must select 20 of those KPI questions.")
    chapters = surahs()
    names = divine_names()
    return {
        "catalogue_version": "candidate_kpi_33_v1",
        "initial_kpi_count": len(INITIAL_KPI_KEYS),
        "candidate_kpi_count": len(KPI_KEYS),
        "surah_metadata_count": len(chapters),
        "divine_name_inventory_count": len(names),
        "potential_review_cells": len(KPI_CATALOG) * len(chapters),
        "reviewed_kpi_surah_links": 0,
        "verified_religious_scores": 0,
        "scholarly_review_status": "NOT_REVIEWED",
        "model_training_permission_from_religious_text": False,
        "principle_lenses_are_analyst_questions_not_rulings": True,
    }


def review_queue_page(*, start: int = 0, limit: int = 50) -> dict[str, object]:
    """Generate bounded review WORK items; no verse interpretation is implied.

    33 x 114 = 3762 unreviewed possible pairs. An item is a request for an
    external scholar/domain reviewer, not a cited mapping or training label.
    """
    if type(start) is not int or start < 0 or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Bad review-page bounds.")
    chapter_numbers = tuple(surahs())
    total = len(KPI_KEYS) * len(chapter_numbers)
    tasks = []
    for index in range(start, min(total, start + limit)):
        kpi_key = KPI_KEYS[index // len(chapter_numbers)]
        chapter = chapter_numbers[index % len(chapter_numbers)]
        tasks.append({
            "candidate_kpi": kpi_key, "surah": chapter,
            "status": "UNREVIEWED",
            "verse_locator": None, "interpretation": None,
            "source_record_id": None, "scholarly_receipt": None,
            "approved_for_training": False,
        })
    return {"total": total, "start": start, "tasks": tasks}
