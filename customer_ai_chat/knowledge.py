"""
customer_ai_chat/knowledge.py — Authoritative Knowledge Registry for Ask EcoIQ.

Curated from approved repository documentation:
  - docs/platform-overview.md
  - docs/islamic-ethical-finance-fit.md
  - docs/project-readiness-score.md
  - docs/capital-integrity-score.md
  - PLATFORM_MATURITY.md

This registry serves as the verified single source of truth for the customer
assistant. It is structured into searchable domains and explicitly declares what
is verified vs what must trigger a disclaimer or refusal.
"""
from __future__ import annotations

# ── Core Platform Summary ───────────────────────────────────────────────────

PLATFORM_SUMMARY = """
EcoIQ is an investor-facing ethical climate intelligence and modernization platform.
It consolidates industrial asset intelligence, country transition data, and ethical
governance screening into a single system for responsible investors, development finance
institutions (DFIs), sovereign wealth funds, and industrial operators.

Core Geographic Focus:
- United Kingdom (Home market; FCA SDR, mandatory TCFD alignment)
- Kazakhstan (High transition exposure; industrial modernization, JETP signatory, active DFI pipeline)
- Saudi Arabia (Vision 2030 diversification, Net-Zero 2060, large sovereign capital deployment)
- Türkiye (EU Green Deal supply-chain pressure, active EBRD / IFC industrial transition engagement)

Key Principles:
- All outputs are AI-assisted, evidence-backed, and indicative.
- EcoIQ does not invent numbers: missing data is treated as unknown, not assumed to be compliant.
- Decision-support only: EcoIQ never provides legal, religious (fatwa), or regulated investment advice.
"""

# ── Five Intelligence Modules ───────────────────────────────────────────────

INTELLIGENCE_MODULES = {
    "country_transition": {
        "title": "Country Transition Intelligence",
        "url": "/countries/",
        "purpose": "National-level transition risk and opportunity mapping assessing the industrial and regulatory environment relative to low-carbon economic demands.",
        "dimensions": [
            "Policy Environment (climate and industrial policy clarity)",
            "Energy Infrastructure (renewable capacity, grid modernisation, fossil dependency)",
            "Industrial Composition (sector mix, emissions intensity, transition employment)",
            "Climate Commitments (NDC ambition, JETP eligibility)",
            "Regulatory Trajectory (environmental and financial regulation pace)",
        ],
        "output": "Country transition score (0–100), risk tier (low/medium/high), sector exposure breakdown, JETP eligibility indicators, narrative intelligence brief.",
    },
    "company_assessment": {
        "title": "Company EcoIQ Assessment",
        "url": "/companies/",
        "purpose": "Six-pillar evidence-based scoring for industrial companies, producing an EcoIQ Score (0–100) with moral classification labels and harm penalties.",
        "pillars": [
            "Public Benefit (25%): employment quality, regional development, community investment",
            "Environmental Stewardship (25%): emissions, pollution intensity, waste, water, biodiversity",
            "Responsible Modernisation (20%): energy transition, digitalization, clean infrastructure",
            "Transparent Governance (15%): reporting quality, audit rigor, procurement transparency",
            "Anti-Corruption (10%): governance integrity, anti-bribery controls, fair procurement",
            "Ethical Alignment (5%): long-term value creation, controversy management",
        ],
        "harm_penalty": "Up to -30 points deducted for severe pollution, unmanaged controversies, or excessive profit extraction without proportionate public benefit.",
        "moral_labels": [
            "Regenerative Leader (score >= 75)",
            "Responsible Builder (score >= 55)",
            "Public Benefit Oriented (score >= 42)",
            "Transitional Company (score >= 28)",
            "Profit-First Operator (score >= 15)",
            "Extractive Core (score < 15)",
        ],
        "evidence_rule": "Scores are grounded in verified public evidence. If data for a dimension is unobserved, EcoIQ reports it as unknown rather than fabricating a default.",
    },
    "project_readiness": {
        "title": "Project Readiness Review",
        "url": "/request-access/review/?type=project_readiness",
        "purpose": "Ten-dimension assessment of how prepared a climate, industrial transition, or clean infrastructure project is for review by DFIs, banks, and climate funds.",
        "dimensions": [
            "Problem Clarity (12%)",
            "Emissions Baseline (12%)",
            "Technical Feasibility (12%)",
            "CAPEX / OPEX Clarity (12%)",
            "Revenue Model (12%)",
            "Governance & Procurement (10%)",
            "Risk Mitigation (10%)",
            "Public Benefit (8%)",
            "Evidence Confidence (7%)",
            "Finance Structure (5%)",
        ],
        "readiness_tiers": "Investment-ready (>=75), Advanced (>=58), Developing (>=40), Early-stage (<40).",
        "finance_routes": "Maps projects to 11 international finance routes including IFC blended finance, EBRD Early Transition Country window, Green Bond issuance, and ADB co-financing.",
    },
    "capital_integrity": {
        "title": "Capital Integrity Score",
        "url": "/platform/#capital-integrity",
        "purpose": "Assesses whether the financial structure of a company, fund, or SPV aligns with responsible investment principles and DFI standards.",
        "dimensions": [
            "Ownership Transparency (beneficial ownership clarity, related-party scrutiny)",
            "Debt Structure (covenants, leverage health, responsible finance norms)",
            "Profit Reinvestment (ratio of profit reinvested into durable assets vs extracted)",
            "Shareholder Accountability (board independence, minority protection)",
            "Long-Term Orientation (transition-aligned capital expenditure)",
            "DFI Compatibility (alignment with IFC Performance Standards, EBRD, ADB criteria)",
        ],
    },
    "ethical_finance_fit": {
        "title": "Islamic & Ethical Finance Fit",
        "url": "/platform/#ethical-finance-fit",
        "purpose": "Assesses compatibility with responsible capital frameworks emphasizing ethical stewardship, public benefit, tangible asset backing, and equitable value distribution.",
        "dimensions": [
            "Asset Structure Alignment (tangible vs speculative asset composition, leverage profile)",
            "Revenue Stream Composition (proportion of revenue from ethically aligned vs excluded sectors)",
            "Prohibited Activity Exposure (rigorous screening against harmful activities)",
            "Governance Stewardship (board accountability, ethical procurement)",
            "Social Impact Orientation (fair employment, regional community benefit)",
            "Long-Term Resilience (balance-sheet durability, sustainability commitments)",
        ],
        "terminology_policy": {
            "approved": [
                "ethical finance fit",
                "ethical stewardship",
                "responsible capital",
                "potentially suitable for Sharia review",
                "requires qualified review",
                "ethical compatibility",
                "Islamic finance fit",
            ],
            "prohibited": [
                "Shariah-compliant (use 'ethical finance fit' or 'suitable for Sharia review')",
                "halal / haram",
                "fatwa (EcoIQ never issues religious rulings)",
                "religiously permissible",
                "faith-based scoring",
                "Shariah score",
            ],
        },
    },
}

# ── Deep Industrial Engines ─────────────────────────────────────────────────

DEEP_ENGINES = {
    "digital_twin": {
        "title": "Industrial Digital Twin & Loss Detection",
        "description": "Simulates complex industrial assets (e.g. mining facilities, metallurgical plants, chemical refineries), maps component graphs, detects energy/material losses, and evaluates intervention options against Khalifah stewardship KPIs.",
    },
    "capital_guardian": {
        "title": "Capital Guardian & SPV Governance",
        "description": "Deterministic governance and capital traceability engine for high-CAPEX transition projects. Tracks capital allocation against physical milestones and triggers deterministic red flags on cost overruns or governance breaches.",
    },
    "good_agents": {
        "title": "114 Good Deeds Agents & Opportunity Discovery",
        "description": "A multi-agent network representing ethical stewardship principles that scans global industrial signals, matches funding gaps with bankable transition interventions, and performs adversarial red-teaming.",
    },
}

# ── Commercial Pricing & Tiers ──────────────────────────────────────────────

PRICING_TIERS = [
    {
        "name": "Starter Plan",
        "price": "£199 / month",
        "audience": "SMEs, emerging developers, and research analysts",
        "features": [
            "Company EcoIQ assessment access",
            "Basic Country Transition profiles",
            "Standard exportable summary reports",
            "Email support",
        ],
    },
    {
        "name": "Professional Plan",
        "price": "£599 / month",
        "audience": "Asset managers, ESG consultants, and corporate sustainability officers",
        "features": [
            "Full 6-pillar score breakdowns & evidence lineage",
            "Ethical & Islamic finance screening overlays",
            "Project Readiness evaluation tool",
            "Portfolio batch screening & watchlist alerts",
            "Priority analytical support",
        ],
    },
    {
        "name": "Enterprise Plan",
        "price": "£2,500 / month",
        "audience": "Development finance institutions, commercial banks, and institutional funds",
        "features": [
            "Full REST API access (v1 & v2)",
            "Digital Twin asset loss analysis & intervention modeling",
            "Capital Guardian SPV tracking integration",
            "Custom DFI & Green Bond compliance mapping",
            "Dedicated analyst briefing & SLA guarantee",
        ],
    },
    {
        "name": "Custom Institutional / Sovereign",
        "price": "Custom quote",
        "audience": "Sovereign wealth funds, national ministries, and multilateral development banks",
        "features": [
            "Bespoke national transition roadmaps",
            "On-premise / private cloud deployment options",
            "Custom methodology calibrations & dedicated advisory board",
        ],
    },
]

# ── Onboarding & Engagement Pathways ────────────────────────────────────────

ACTION_ROUTES = {
    "request_review": {
        "label": "Request an EcoIQ Review",
        "url": "/request-access/review/",
        "description": "Submit a company, project, or portfolio for an official AI-assisted assessment.",
    },
    "request_demo": {
        "label": "Request an Institutional Demo",
        "url": "/request-access/enterprise/",
        "description": "Schedule a personalized demonstration of EcoIQ's institutional intelligence suite.",
    },
    "explore_intelligence": {
        "label": "Explore Platform Intelligence",
        "url": "/intelligence/",
        "description": "Browse live company scores, country transition profiles, and rankings.",
    },
    "contact_team": {
        "label": "Contact the Team",
        "url": "/contact/",
        "description": "Direct communication with the EcoIQ leadership team (alizhan@ecoiq.uk).",
    },
}

# ── Starter Questions ───────────────────────────────────────────────────────

STARTER_QUESTIONS = [
    "What does EcoIQ do?",
    "How does EcoIQ assess industrial companies?",
    "How can EcoIQ help financial institutions & DFIs?",
    "What is EcoIQ's Islamic & ethical finance capability?",
    "How can I arrange a demo or trial?",
]


def get_relevant_knowledge_context(query: str) -> str:
    """
    Assemble relevant grounded knowledge snippets based on the user's query.
    Returns structured markdown text for injection into the system prompt.
    """
    q = query.lower()
    snippets = [PLATFORM_SUMMARY.strip()]

    # Match modules
    if any(k in q for k in ("module", "what do you do", "product", "capability", "overview", "ecoiq")):
        for mod in INTELLIGENCE_MODULES.values():
            snippets.append(f"### {mod['title']}\nPurpose: {mod['purpose']}\nURL: {mod['url']}")

    if any(k in q for k in ("company", "score", "pillar", "rating", "moral", "harm", "penalty", "public benefit")):
        m = INTELLIGENCE_MODULES["company_assessment"]
        snippets.append(
            f"### Company Assessment Methodology\n"
            f"Pillars:\n" + "\n".join(f"- {p}" for p in m["pillars"]) + "\n"
            f"Harm Penalty: {m['harm_penalty']}\n"
            f"Moral Labels:\n" + "\n".join(f"- {l}" for l in m["moral_labels"]) + "\n"
            f"Evidence Rule: {m['evidence_rule']}"
        )

    if any(k in q for k in ("islamic", "sharia", "shariah", "halal", "ethical finance", "mizan", "stewardship", "khalifa")):
        m = INTELLIGENCE_MODULES["ethical_finance_fit"]
        snippets.append(
            f"### Ethical & Islamic Finance Fit\n"
            f"Purpose: {m['purpose']}\n"
            f"Dimensions:\n" + "\n".join(f"- {d}" for d in m["dimensions"]) + "\n"
            f"Approved Vocabulary: {', '.join(m['terminology_policy']['approved'])}\n"
            f"Prohibited Terms: {', '.join(m['terminology_policy']['prohibited'])}\n"
            f"Note: EcoIQ provides decision-support compatibility screening only; never religious rulings or fatwas."
        )

    if any(k in q for k in ("project", "readiness", "dfi", "ifc", "ebrd", "adb", "green bond", "capex")):
        m = INTELLIGENCE_MODULES["project_readiness"]
        snippets.append(
            f"### Project Readiness Review\n"
            f"Purpose: {m['purpose']}\n"
            f"Tiers: {m['readiness_tiers']}\n"
            f"Finance Routes: {m['finance_routes']}"
        )

    if any(k in q for k in ("country", "transition", "kazakhstan", "saudi", "turkey", "uk", "jetp", "national")):
        m = INTELLIGENCE_MODULES["country_transition"]
        snippets.append(
            f"### Country Transition Intelligence\n"
            f"Purpose: {m['purpose']}\n"
            f"Dimensions: {', '.join(m['dimensions'])}\n"
            f"Output: {m['output']}"
        )

    if any(k in q for k in ("digital twin", "asset", "loss", "mining", "industrial", "modernization")):
        snippets.append(
            f"### Digital Twin & Asset Intelligence\n"
            f"{DEEP_ENGINES['digital_twin']['description']}\n"
            f"{DEEP_ENGINES['capital_guardian']['description']}"
        )

    if any(k in q for k in ("price", "pricing", "cost", "subscription", "plan", "tier", "how much", "buy", "starter", "enterprise")):
        tiers_text = "\n".join(
            f"- **{t['name']}** ({t['price']}): {t['audience']}. Key features: {', '.join(t['features'][:3])}."
            for t in PRICING_TIERS
        )
        snippets.append(f"### Approved Pricing & Subscription Plans\n{tiers_text}")

    if any(k in q for k in ("demo", "contact", "talk", "sales", "onboard", "trial", "start", "book", "meeting")):
        routes_text = "\n".join(
            f"- **{r['label']}**: {r['url']} — {r['description']}"
            for r in ACTION_ROUTES.values()
        )
        snippets.append(f"### Onboarding & Engagement Routes\n{routes_text}\nEmail: alizhan@ecoiq.uk")

    return "\n\n---\n\n".join(snippets)
