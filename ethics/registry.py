"""
EcoIQ Formula Registry — 33 sub-formulas + 3 master formulas.

This module defines the canonical list of all EcoIQ ethical intelligence formulas.
Used by the data migration (0002) to populate FormulaDefinition records.

Each entry: (code, name, category, master_formula, description, maqasid, weight, is_public, order)

Internal mapping to universal preservation principles (Maqasid layer) is included
but only surfaced in the advanced methodology view and internal analyst tools —
not in the main public UI.
"""

# ── Master formulas (3) ────────────────────────────────────────────────────────

MASTER_FORMULAS = [
    {
        'code': 'NEI',
        'name': 'Net Ethical Impact',
        'category': '',
        'master_formula': 'NEI',
        'description': (
            'Measures whether a company creates more long-term benefit than harm. '
            'Computed as: Total Benefit (weighted average of 6 EcoIQ pillars) '
            'minus Harm Burden (pollution severity + controversy risk + opacity). '
            'The definitive answer to: "Is this company a net positive or net negative?"'
        ),
        'maqasid_principle': '',
        'weight': 0.40,
        'is_public': True,
        'order': 1,
    },
    {
        'code': 'TSS',
        'name': 'Transition Stewardship Score',
        'category': '',
        'master_formula': 'TSS',
        'description': (
            'Measures whether a company is responsibly modernising and reducing harm '
            'over time. Computed as: (Restoration + Modernisation + Efficiency + '
            'Transparency) / 4, adjusted for harm burden and modernisation momentum. '
            'Rewards genuine transition progress even from high-impact baselines.'
        ),
        'maqasid_principle': '',
        'weight': 0.35,
        'is_public': True,
        'order': 2,
    },
    {
        'code': 'RVI',
        'name': 'Regenerative Value Index',
        'category': '',
        'master_formula': 'RVI',
        'description': (
            'Measures long-term societal and environmental value created relative to '
            'resources consumed. Forward-looking metric — rewards companies building '
            'lasting employment quality, community resilience, ecosystem health, '
            'and future-generation benefit.'
        ),
        'maqasid_principle': '',
        'weight': 0.25,
        'is_public': True,
        'order': 3,
    },
]


# ── Sub-formulas (33) — 8 categories × ~4 each ────────────────────────────────

SUB_FORMULAS = [

    # ── Environmental Balance (EB) ── 4 formulas ──────────────────────────────
    {
        'code': 'EB_01',
        'name': 'Carbon Footprint Intensity',
        'category': 'environmental_balance',
        'master_formula': 'NEI',
        'description': 'Measures GHG emissions relative to revenue or output, benchmarked against sector norms.',
        'maqasid_principle': 'life',
        'weight': 0.35,
        'is_public': False,
        'order': 10,
    },
    {
        'code': 'EB_02',
        'name': 'Ecosystem Preservation Score',
        'category': 'environmental_balance',
        'master_formula': 'RVI',
        'description': 'Evaluates protection of biodiversity, land use practices, and nature-positive commitments.',
        'maqasid_principle': 'life',
        'weight': 0.25,
        'is_public': False,
        'order': 11,
    },
    {
        'code': 'EB_03',
        'name': 'Waste-to-Resource Ratio',
        'category': 'environmental_balance',
        'master_formula': 'NEI',
        'description': 'Percentage of operational waste recovered, recycled, or converted to energy vs. landfill.',
        'maqasid_principle': 'wealth',
        'weight': 0.20,
        'is_public': False,
        'order': 12,
    },
    {
        'code': 'EB_04',
        'name': 'Water Stewardship Quality',
        'category': 'environmental_balance',
        'master_formula': 'NEI',
        'description': 'Assesses water withdrawal intensity, recycling rates, and basin-level water risk management.',
        'maqasid_principle': 'life',
        'weight': 0.20,
        'is_public': False,
        'order': 13,
    },

    # ── Industrial Efficiency (IE) ── 4 formulas ─────────────────────────────
    {
        'code': 'IE_01',
        'name': 'Energy Efficiency Index',
        'category': 'industrial_efficiency',
        'master_formula': 'TSS',
        'description': 'Energy consumed per unit of output, indexed to sector benchmarks and trend direction.',
        'maqasid_principle': 'wealth',
        'weight': 0.30,
        'is_public': False,
        'order': 20,
    },
    {
        'code': 'IE_02',
        'name': 'Process Innovation Rate',
        'category': 'industrial_efficiency',
        'master_formula': 'TSS',
        'description': 'Rate of adoption of cleaner production methods, process patents, and operational improvements.',
        'maqasid_principle': 'intellect',
        'weight': 0.25,
        'is_public': False,
        'order': 21,
    },
    {
        'code': 'IE_03',
        'name': 'Technology Modernisation Index',
        'category': 'industrial_efficiency',
        'master_formula': 'TSS',
        'description': 'Assesses equipment age, technology adoption rate, and capex directed at modernisation.',
        'maqasid_principle': 'wealth',
        'weight': 0.25,
        'is_public': False,
        'order': 22,
    },
    {
        'code': 'IE_04',
        'name': 'Supply Chain Responsibility Score',
        'category': 'industrial_efficiency',
        'master_formula': 'TSS',
        'description': 'Measures supplier ESG screening, local sourcing ratios, and supply chain emissions disclosure.',
        'maqasid_principle': 'trust',
        'weight': 0.20,
        'is_public': False,
        'order': 23,
    },

    # ── Transparency & Governance (TG) ── 4 formulas ──────────────────────────
    {
        'code': 'TG_01',
        'name': 'Reporting Depth Score',
        'category': 'transparency_governance',
        'master_formula': 'NEI',
        'description': 'Quality and completeness of public ESG/sustainability reporting aligned to GRI, CDP, or TCFD.',
        'maqasid_principle': 'intellect',
        'weight': 0.35,
        'is_public': True,
        'order': 30,
    },
    {
        'code': 'TG_02',
        'name': 'Audit Independence Quality',
        'category': 'transparency_governance',
        'master_formula': 'NEI',
        'description': 'Independence and rigour of financial, environmental, and social audits.',
        'maqasid_principle': 'trust',
        'weight': 0.30,
        'is_public': False,
        'order': 31,
    },
    {
        'code': 'TG_03',
        'name': 'Procurement Transparency Index',
        'category': 'transparency_governance',
        'master_formula': 'TSS',
        'description': 'Openness of supplier selection, contract disclosure, and procurement governance.',
        'maqasid_principle': 'trust',
        'weight': 0.20,
        'is_public': False,
        'order': 32,
    },
    {
        'code': 'TG_04',
        'name': 'Stakeholder Engagement Score',
        'category': 'transparency_governance',
        'master_formula': 'RVI',
        'description': 'Quality and breadth of community, investor, and regulator engagement processes.',
        'maqasid_principle': 'society',
        'weight': 0.15,
        'is_public': False,
        'order': 33,
    },

    # ── Public Benefit (PB) ── 4 formulas ────────────────────────────────────
    {
        'code': 'PB_01',
        'name': 'Employment Quality Index',
        'category': 'public_benefit',
        'master_formula': 'RVI',
        'description': 'Wage quality, skills development investment, job stability, and gender pay equity.',
        'maqasid_principle': 'society',
        'weight': 0.30,
        'is_public': True,
        'order': 40,
    },
    {
        'code': 'PB_02',
        'name': 'Regional Development Contribution',
        'category': 'public_benefit',
        'master_formula': 'RVI',
        'description': 'Local procurement ratios, regional infrastructure contributions, and SME development support.',
        'maqasid_principle': 'society',
        'weight': 0.25,
        'is_public': False,
        'order': 41,
    },
    {
        'code': 'PB_03',
        'name': 'Community Investment Ratio',
        'category': 'public_benefit',
        'master_formula': 'NEI',
        'description': 'Social investment as a ratio of revenue — community health, education, and infrastructure.',
        'maqasid_principle': 'society',
        'weight': 0.25,
        'is_public': False,
        'order': 42,
    },
    {
        'code': 'PB_04',
        'name': 'National Value Creation Score',
        'category': 'public_benefit',
        'master_formula': 'RVI',
        'description': 'Long-term contribution to national economic resilience, tax compliance, and strategic sectors.',
        'maqasid_principle': 'wealth',
        'weight': 0.20,
        'is_public': False,
        'order': 43,
    },

    # ── Restoration & Regeneration (RR) ── 4 formulas ─────────────────────────
    {
        'code': 'RR_01',
        'name': 'Ecosystem Restoration Investment',
        'category': 'restoration_regeneration',
        'master_formula': 'RVI',
        'description': 'Investment in ecosystem restoration, reforestation, or habitat rehabilitation.',
        'maqasid_principle': 'life',
        'weight': 0.30,
        'is_public': False,
        'order': 50,
    },
    {
        'code': 'RR_02',
        'name': 'Biodiversity Net Gain Score',
        'category': 'restoration_regeneration',
        'master_formula': 'RVI',
        'description': 'Whether operations result in net-positive biodiversity outcomes relative to baseline.',
        'maqasid_principle': 'life',
        'weight': 0.25,
        'is_public': False,
        'order': 51,
    },
    {
        'code': 'RR_03',
        'name': 'Pollution Remediation Progress',
        'category': 'restoration_regeneration',
        'master_formula': 'TSS',
        'description': 'Rate of cleanup of legacy pollution sites, contaminated land, and industrial waste.',
        'maqasid_principle': 'life',
        'weight': 0.25,
        'is_public': False,
        'order': 52,
    },
    {
        'code': 'RR_04',
        'name': 'Environmental Liability Management',
        'category': 'restoration_regeneration',
        'master_formula': 'NEI',
        'description': 'Adequacy of provisions and controls for environmental liabilities and remediation obligations.',
        'maqasid_principle': 'wealth',
        'weight': 0.20,
        'is_public': False,
        'order': 53,
    },

    # ── Long-Term Sustainability (LS) ── 4 formulas ────────────────────────────
    {
        'code': 'LS_01',
        'name': 'Future Readiness Assessment',
        'category': 'long_term_sustainability',
        'master_formula': 'RVI',
        'description': 'Strategic preparedness for energy transition, regulatory shifts, and market evolution.',
        'maqasid_principle': 'intellect',
        'weight': 0.30,
        'is_public': False,
        'order': 60,
    },
    {
        'code': 'LS_02',
        'name': 'Climate Resilience Score',
        'category': 'long_term_sustainability',
        'master_formula': 'RVI',
        'description': 'Physical climate risk exposure (floods, drought, heat) and adaptation measures in place.',
        'maqasid_principle': 'life',
        'weight': 0.25,
        'is_public': False,
        'order': 61,
    },
    {
        'code': 'LS_03',
        'name': 'Digital Transformation Maturity',
        'category': 'long_term_sustainability',
        'master_formula': 'TSS',
        'description': 'Adoption of digital tools, data infrastructure, and automated monitoring for efficiency gains.',
        'maqasid_principle': 'intellect',
        'weight': 0.25,
        'is_public': False,
        'order': 62,
    },
    {
        'code': 'LS_04',
        'name': 'Long-Term Value Creation Index',
        'category': 'long_term_sustainability',
        'master_formula': 'RVI',
        'description': 'Composite of R&D investment, knowledge asset creation, and multi-decade value horizon.',
        'maqasid_principle': 'intellect',
        'weight': 0.20,
        'is_public': False,
        'order': 63,
    },

    # ── Ethical Capital Allocation (EC) ── 4 formulas ─────────────────────────
    {
        'code': 'EC_01',
        'name': 'Profit Distribution Equity',
        'category': 'ethical_capital',
        'master_formula': 'NEI',
        'description': 'Ratio of profit retained in operations, returned to employees, and distributed to shareholders.',
        'maqasid_principle': 'wealth',
        'weight': 0.30,
        'is_public': False,
        'order': 70,
    },
    {
        'code': 'EC_02',
        'name': 'Social Return on Investment',
        'category': 'ethical_capital',
        'master_formula': 'RVI',
        'description': 'Estimated societal value generated per unit of capital deployed (SROI methodology).',
        'maqasid_principle': 'wealth',
        'weight': 0.30,
        'is_public': False,
        'order': 71,
    },
    {
        'code': 'EC_03',
        'name': 'Responsible Investment Ratio',
        'category': 'ethical_capital',
        'master_formula': 'TSS',
        'description': 'Share of capex directed at environmental, social, and governance improvements.',
        'maqasid_principle': 'wealth',
        'weight': 0.25,
        'is_public': False,
        'order': 72,
    },
    {
        'code': 'EC_04',
        'name': 'Human Capital Investment Score',
        'category': 'ethical_capital',
        'master_formula': 'RVI',
        'description': 'Training spend per employee, leadership development, and retention programmes.',
        'maqasid_principle': 'intellect',
        'weight': 0.15,
        'is_public': False,
        'order': 73,
    },

    # ── Anti-Corruption & Accountability (AC) ── 5 formulas ───────────────────
    {
        'code': 'AC_01',
        'name': 'Anti-Bribery Controls Quality',
        'category': 'anti_corruption',
        'master_formula': 'NEI',
        'description': 'Implementation and certification of anti-bribery management systems (ISO 37001 / FCPA compliance).',
        'maqasid_principle': 'trust',
        'weight': 0.25,
        'is_public': True,
        'order': 80,
    },
    {
        'code': 'AC_02',
        'name': 'Conflicts of Interest Management',
        'category': 'anti_corruption',
        'master_formula': 'NEI',
        'description': 'Policies and controls managing conflicts of interest at board and management level.',
        'maqasid_principle': 'trust',
        'weight': 0.20,
        'is_public': False,
        'order': 81,
    },
    {
        'code': 'AC_03',
        'name': 'Whistleblower Protection Score',
        'category': 'anti_corruption',
        'master_formula': 'NEI',
        'description': 'Availability, independence, and confidentiality of whistleblower channels.',
        'maqasid_principle': 'trust',
        'weight': 0.20,
        'is_public': False,
        'order': 82,
    },
    {
        'code': 'AC_04',
        'name': 'Regulatory Compliance History',
        'category': 'anti_corruption',
        'master_formula': 'NEI',
        'description': 'Track record of regulatory compliance, sanctions history, and remediation quality.',
        'maqasid_principle': 'trust',
        'weight': 0.20,
        'is_public': False,
        'order': 83,
    },
    {
        'code': 'AC_05',
        'name': 'Ethical Leadership Assessment',
        'category': 'anti_corruption',
        'master_formula': 'NEI',
        'description': 'Board diversity, executive accountability, and ethics tone-from-the-top indicators.',
        'maqasid_principle': 'trust',
        'weight': 0.15,
        'is_public': False,
        'order': 84,
    },
]


def all_formulas():
    """Return the combined list of master + sub formulas."""
    return MASTER_FORMULAS + SUB_FORMULAS
