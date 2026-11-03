"""Twelve proposed reform-analysis capabilities: a plan, NOT twelve deployed engines.

Internal, dependency-free catalogue. Existing component paths indicate potential
reuse, not operational coverage or validation. Inputs supplied to a plan builder
are claims of availability, NOT authenticated evidence. No public endpoints,
legal findings, allegations, forecasts or religious rulings are generated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ReformCapability:
    code: str
    slug: str
    title: str
    title_ru: str
    objective: str
    required_inputs: tuple[str, ...]
    candidate_outputs: tuple[str, ...]
    reuse_candidates: tuple[str, ...]
    safeguards: tuple[str, ...]
    governance_domain_codes: tuple[str, ...]
    maturity: str = "RESEARCH_SPEC_ONLY"

    def __post_init__(self) -> None:
        fields = (self.code, self.slug, self.title, self.title_ru, self.objective)
        if any(not value or not value.strip() for value in fields):
            raise ValueError("Capability identifiers and descriptions are required.")
        if self.maturity != "RESEARCH_SPEC_ONLY":
            raise ValueError("A catalogue entry cannot claim implementation readiness.")
        if not self.required_inputs or not self.candidate_outputs or not self.safeguards:
            raise ValueError("Data requirements, proposed outputs and safeguards are mandatory.")
        for items in (self.required_inputs, self.candidate_outputs, self.reuse_candidates,
                      self.safeguards, self.governance_domain_codes):
            if not isinstance(items, tuple) or any(not isinstance(x, str) or not x.strip() for x in items):
                raise ValueError("Capability fields must be nonempty text tuples.")
            if len(set(items)) != len(items):
                raise ValueError("Duplicate capability metadata item.")
        if any(code not in {f"{n:02d}" for n in range(1, 13)}
               for code in self.governance_domain_codes):
            raise ValueError("Governance references must use planned IDs 01–12.")


def _c(code, slug, title, ru, objective, required, outputs, reuse, safeguards, domain_ids):
    return ReformCapability(code, slug, title, ru, objective, required, outputs,
                            reuse, safeguards, domain_ids)


REFORM_CAPABILITIES: tuple[ReformCapability, ...] = (
    _c("01", "root_cause", "Root Cause Intelligence", "Анализ первопричин",
       "Document competing explanations and tests before asserting causality.",
       ("problem_definition", "observations_with_dates", "alternative_explanations",
        "confounder_assessment"),
       ("hypothesis_register", "falsification_plan"),
       ("poverty_justice/contracts.py", "ecoiq_os/evidence.py"),
       ("Association alone does not establish causality.",
        "No policy intervention without authorised review."), ("07", "11", "12")),
    _c("02", "regulatory_conflict", "Regulatory Conflict Graph", "Граф правовых противоречий",
       "Flag candidate conflicts between dated legal provisions for expert resolution.",
       ("jurisdiction", "effective_date", "official_legal_text_versions",
        "legal_hierarchy_and_scope"),
       ("candidate_conflict_edges", "lawyer_review_queue"),
       ("ai_agents/regulatory_agent/README.md",),
       ("Do not classify a law as invalid from text similarity alone.",
        "Legal applicability and conflict require jurisdiction-specific counsel."), ("01", "06", "11")),
    _c("03", "economic_digital_twin", "Economic Digital Twin", "Экономический цифровой двойник",
       "Compare hypothetical economic scenarios with stated uncertainty.",
       ("baseline_period", "scenario_assumptions", "economic_inputs",
        "units_and_deflators"),
       ("scenario_comparison", "sensitivity_requirements"),
       ("digital_twin/services/scenario_simulation.py",),
       ("Existing digital twin addresses industrial assets, not macroeconomics.",
        "Simulated outcomes must not be presented as observed or causal."), ("02", "08", "11")),
    _c("04", "anti_corruption", "Anti-Corruption Intelligence", "Риски коррупции",
       "Identify procurement and conflict-of-interest risk indicators, not guilt.",
       ("procurement_records", "decision_authorities", "procurement_rules",
        "independent_review_process"),
       ("risk_flags", "human_investigation_queue"),
       ("evidence_memory/services/retrieval_policy.py",),
       ("An anomaly is not proof of corruption or personal wrongdoing.",
        "Protect identities and procedural rights; no public accusations."), ("01", "06", "12")),
    _c("05", "wealth_distribution", "Wealth Distribution Analysis", "Распределение благ",
       "Measure how costs and benefits affect defined groups over time.",
       ("population_definition", "benefit_and_cost_data", "distribution_weights",
        "observation_period"),
       ("distributional_breakdown", "uncertainty_and_missing_data"),
       ("poverty_justice/contracts.py",),
       ("No individual-level conclusions from aggregated data.",
        "Protect personal data and disclose coverage bias."), ("02", "05")),
    _c("06", "public_budget", "Public Budget Intelligence", "Результативность бюджета",
       "Link public spending to independently measured service outcomes.",
       ("budget_actuals", "approved_programme_goals", "outcome_measurements",
        "accounting_period_and_currency"),
       ("spend_to_outcome_crosswalk", "unattributed_spend_flags"),
       ("companies/provenance.py",),
       ("Spending and outcomes are not proof of causal impact.",
        "Budget efficiency needs scope-adjusted comparison and audit."), ("01", "05", "11")),
    _c("07", "legal_access", "Legal Access Intelligence", "Доступ к правовой помощи",
       "Identify barriers to timely, affordable and fair legal assistance.",
       ("jurisdiction", "service_access_data", "case_type_and_complexity",
        "privacy_and_consent_basis"),
       ("barrier_register", "service_gap_summary"),
       (),
       ("Avoid legal advice or automated legal eligibility decisions.",
        "Never expose identifiable litigant or client records."), ("05", "06")),
    _c("08", "islamic_finance", "Islamic Finance Research", "Исследование исламских финансов",
       "Prepare financing-structure questions for qualified legal and scholarly review.",
       ("contract_terms", "asset_and_cashflow_details", "applicable_legal_framework",
        "scholar_review_scope"),
       ("contract_structure_questions", "qualified_review_requirements"),
       ("ml/finance/islamic_finance_fit.py", "islamic_knowledge/contracts.py"),
       ("Indicative research is not Shariah compliance certification or fatwa.",
        "Different schools or standards must not be merged into a fake consensus."), ("02", "03")),
    _c("09", "future_generations", "Future Generations Impact", "Влияние на будущие поколения",
       "Identify long-horizon harms, benefits, uncertainties and irreversible effects.",
       ("time_horizon", "intergenerational_population_assumptions",
        "environmental_and_social_baselines", "discount_and_uncertainty_policy"),
       ("long_horizon_risk_register", "irreversibility_questions"),
       ("digital_twin/services/scenario_simulation.py",),
       ("Future forecasts are scenario-dependent, not factual predictions.",
        "Never net away non-compensable rights or serious harms."), ("08", "09", "11")),
    _c("10", "ai_accountability", "AI Accountability Engine", "Подотчётность искусственного интеллекта",
       "Specify verifiable checks on model outputs, source attribution and appeals.",
       ("model_version", "input_and_output_record", "ground_truth_or_review_basis",
        "reviewer_and_appeal_process"),
       ("failure_taxonomy", "audit_test_plan"),
       ("islamic_knowledge/contracts.py", "evidence_memory/services/retrieval_policy.py"),
       ("A model cannot certify its own reliability by self-assessment.",
        "No self-approval, fabricated citations or automated irreversible decisions."), ("10", "12")),
    _c("11", "reform_experiments", "Reform Experiment Lab", "Эксперименты с реформами",
       "Plan ethical evaluations of pilot reform effectiveness.",
       ("intervention_definition", "outcome_definition", "comparison_strategy",
        "consent_ethics_and_safeguards"),
       ("preanalysis_plan", "evaluation_bias_checklist"),
       ("poverty_justice/contracts.py", "poverty_justice/falsification.py"),
       ("Avoid causal conclusions without an identified, defended design.",
        "No arbitrary withholding of essential rights or services."), ("07", "11")),
    _c("12", "institutional_memory", "Institutional Memory", "Институциональная память",
       "Retain decision rationale, revisions, lessons and accountability trails.",
       ("decision_id_and_scope", "dated_rationale", "responsible_actor",
        "evidence_and_version_references"),
       ("decision_history_schema", "retention_and_access_requirements"),
       ("companies/provenance.py", "evidence_memory/models.py"),
       ("Provenance logs do not by themselves constitute a decision history.",
        "Respect access controls, retention limits and lawful correction."), ("01", "07", "12")),
)

if tuple(c.code for c in REFORM_CAPABILITIES) != tuple(f"{n:02d}" for n in range(1, 13)):
    raise ValueError("Reform catalogue must contain unique codes 01–12 in order.")
if len({c.slug for c in REFORM_CAPABILITIES}) != 12:
    raise ValueError("Reform capability slugs must be unique.")


def capability_by_slug(slug: str) -> ReformCapability:
    """Read-only metadata lookup, not a workflow or permission boundary."""
    for capability in REFORM_CAPABILITIES:
        if capability.slug == slug:
            return capability
    raise KeyError(slug)


def build_research_plan(slug: str, input_presence: Mapping[str, bool]) -> dict:
    """Report missing declared inputs; never verify evidence or approve decisions.

    input_presence describes only the CALLER'S claimed availability, not proof
    of source quality, jurisdiction, permissions, correctness or audit.
    """
    cap = capability_by_slug(slug)
    if not isinstance(input_presence, Mapping):
        raise TypeError("Expected a mapping of required input keys to booleans.")
    unknown = set(input_presence) - set(cap.required_inputs)
    if unknown:
        raise ValueError("Unexpected input keys.")
    if any(type(value) is not bool for value in input_presence.values()):
        raise ValueError("Input availability must be explicitly boolean.")
    return {
        "code": cap.code,
        "slug": cap.slug,
        "status": "RESEARCH_PLAN_ONLY",
        "present_claimed_inputs": tuple(
            key for key in cap.required_inputs if input_presence.get(key) is True
        ),
        "missing_inputs": tuple(
            key for key in cap.required_inputs if input_presence.get(key) is not True
        ),
        "proposed_outputs": cap.candidate_outputs,
        "review_constraints": cap.safeguards,
        "evidence_authentication": "NOT_PERFORMED",
        "expert_review": "NOT_PERFORMED",
        "decision_ready": False,
    }
