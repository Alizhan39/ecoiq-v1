"""Domain profiles for EcoIQ OS.

Domains are adapters onto the same OS kernel, not separate top-level agents or
independent reasoning stacks.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainProfile:
    key: str
    name: str
    primary_resources: tuple[str, ...]
    typical_scopes: tuple[str, ...]
    core_questions: tuple[str, ...]


DOMAINS: tuple[DomainProfile, ...] = (
    DomainProfile(
        "mining",
        "Mining & Minerals",
        ("mineral", "energy", "water", "land", "labour", "money", "waste"),
        ("process", "facility", "company", "region", "ecosystem"),
        ("recovery", "energy_intensity", "water_intensity", "tailings", "local_value_capture", "restoration"),
    ),
    DomainProfile(
        "oil_gas",
        "Oil & Gas",
        ("material", "energy", "water", "land", "labour", "money", "emissions", "waste"),
        ("asset", "process", "facility", "company", "supply_chain", "region", "country", "ecosystem"),
        ("recovery", "methane_loss", "flaring", "energy_intensity", "water", "local_value_capture", "decommissioning"),
    ),
    DomainProfile(
        "processing",
        "Processing & Metallurgy",
        ("material", "energy", "water", "labour", "money", "emissions", "waste"),
        ("process", "facility", "company", "supply_chain", "region"),
        ("yield", "waste_heat", "scrap", "downtime", "water_reuse", "value_added"),
    ),
    DomainProfile(
        "manufacturing",
        "Manufacturing & Assembly",
        ("material", "energy", "water", "labour", "time", "money", "waste"),
        ("process", "facility", "company", "supply_chain"),
        ("throughput", "reject_rate", "rework", "idle_time", "supplier_risk", "repairability"),
    ),
    DomainProfile(
        "energy",
        "Energy & Power",
        ("energy", "money", "material", "water", "land", "emissions"),
        ("asset", "process", "facility", "company", "region", "country"),
        ("generation_efficiency", "grid_loss", "reliability", "waste_heat", "affordability", "resilience"),
    ),
    DomainProfile(
        "water",
        "Water Systems",
        ("water", "energy", "money", "land"),
        ("asset", "process", "facility", "city", "region", "ecosystem"),
        ("abstraction", "loss", "reuse", "quality", "allocation", "basin_resilience"),
    ),
    DomainProfile(
        "agriculture",
        "Agriculture & Food",
        ("water", "land", "energy", "material", "labour", "money", "waste"),
        ("process", "facility", "supply_chain", "region", "ecosystem"),
        ("yield", "soil_health", "water_productivity", "input_loss", "food_loss", "farmer_value_capture"),
    ),
    DomainProfile(
        "construction",
        "Construction & Built Environment",
        ("material", "energy", "water", "labour", "money", "land", "waste"),
        ("asset", "process", "facility", "city", "region"),
        ("whole_life_value", "embodied_energy", "operational_energy", "worker_safety", "repairability", "affordability"),
    ),
    DomainProfile(
        "transport",
        "Transport & Logistics",
        ("energy", "time", "money", "material", "labour", "emissions"),
        ("asset", "process", "company", "supply_chain", "city", "region"),
        ("load_factor", "idle_time", "energy_intensity", "access", "reliability", "external_cost"),
    ),
    DomainProfile(
        "finance",
        "Finance & Capital",
        ("money", "data", "time", "service"),
        ("organisation", "market", "region", "country"),
        ("capital_access", "risk_distribution", "cost_of_capital", "asset_creation", "transparency", "resilience"),
    ),
    DomainProfile(
        "government",
        "Government & Public Systems",
        ("money", "data", "labour", "time", "service", "land"),
        ("public_system", "city", "region", "country"),
        ("public_value", "service_access", "procurement", "fiscal_resilience", "accountability", "future_liability"),
    ),
    DomainProfile(
        "healthcare",
        "Healthcare Systems",
        ("money", "labour", "time", "data", "energy", "water", "material", "service"),
        ("facility", "organisation", "city", "region", "country"),
        ("access", "quality", "waiting_time", "capacity", "resource_use", "health_outcomes"),
    ),
    DomainProfile(
        "education",
        "Education Systems",
        ("money", "labour", "time", "data", "energy", "service"),
        ("facility", "organisation", "city", "region", "country"),
        ("access", "learning_outcomes", "teacher_capacity", "skills_match", "mobility", "future_productivity"),
    ),
    DomainProfile(
        "households",
        "Households & Poverty / Justice",
        ("money", "labour", "time", "service", "energy", "water"),
        ("household", "city", "region", "country"),
        ("income", "essential_burden", "dependency", "debt_service", "housing", "resilience"),
    ),
)

DOMAIN_REGISTRY = {domain.key: domain for domain in DOMAINS}


def get_domain(key: str) -> DomainProfile:
    try:
        return DOMAIN_REGISTRY[key]
    except KeyError as exc:
        raise ValueError(f"Unknown EcoIQ OS domain: {key}") from exc
