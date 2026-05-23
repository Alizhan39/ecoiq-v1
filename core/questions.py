"""
Central definition of the EcoIQ questionnaire.
Two questions per pillar = 10 total.
Each entry: (key, pillar_label, pillar_color, question_text, placeholder)
"""

QUESTIONS = [
    # ── Environment ─────────────────────────────────────────────────────────
    (
        'env_1', 'Environment', '#d8f3dc',
        'Describe your company\'s approach to reducing carbon emissions and environmental footprint.',
        'e.g. We have committed to net-zero by 2030, use renewable energy for 60 % of operations…',
    ),
    (
        'env_2', 'Environment', '#d8f3dc',
        'What environmental certifications, targets, or reporting standards does your company follow?',
        'e.g. ISO 14001, GRI Standards, Science Based Targets initiative…',
    ),

    # ── Social ───────────────────────────────────────────────────────────────
    (
        'soc_1', 'Social', '#dde5f4',
        'How does your company support employee wellbeing, diversity, and inclusion?',
        'e.g. Flexible working, pay-equity audits, ERGs, mental health programmes…',
    ),
    (
        'soc_2', 'Social', '#dde5f4',
        'Describe your community engagement and broader social impact initiatives.',
        'e.g. Local supplier preference, pro-bono work, charity partnerships…',
    ),

    # ── Governance ───────────────────────────────────────────────────────────
    (
        'gov_1', 'Governance', '#fef9c3',
        'How is ethical decision-making embedded in your leadership and governance structure?',
        'e.g. Independent board members, ethics committee, ESG KPIs tied to exec pay…',
    ),
    (
        'gov_2', 'Governance', '#fef9c3',
        'What transparency and stakeholder reporting mechanisms does your company have?',
        'e.g. Annual sustainability report, third-party audits, public ESG dashboard…',
    ),

    # ── Ethics ───────────────────────────────────────────────────────────────
    (
        'eth_1', 'Ethics', '#fce7f3',
        'How does your company handle conflicts of interest, whistleblowing, and ethical breaches?',
        'e.g. Anonymous reporting hotline, zero-tolerance policy, published case outcomes…',
    ),
    (
        'eth_2', 'Ethics', '#fce7f3',
        'Describe your supply chain ethics and responsible sourcing practices.',
        'e.g. Supplier code of conduct, living-wage requirements, conflict-mineral audits…',
    ),

    # ── Innovation ───────────────────────────────────────────────────────────
    (
        'inn_1', 'Innovation', '#ede9fe',
        'What sustainable or ethical innovations has your company introduced in the last two years?',
        'e.g. Circular-economy product line, AI bias auditing tool, green logistics…',
    ),
    (
        'inn_2', 'Innovation', '#ede9fe',
        'How does your company invest in future-focused, responsible technology or processes?',
        'e.g. R&D budget allocation, responsible AI policy, green-tech partnerships…',
    ),
]

# Group questions by pillar for template rendering
def grouped():
    groups = {}
    for key, pillar, color, text, placeholder in QUESTIONS:
        if pillar not in groups:
            groups[pillar] = {'color': color, 'questions': []}
        groups[pillar]['questions'].append((key, text, placeholder))
    return groups
