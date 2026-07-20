"""
company_intelligence/services/kpi_candidate_matching.py — feat/company-
evidence-ingestion (PR 10): deterministic (never LLM-based) matching of one
real, already-stored evidence_memory.EvidenceMemory row against candidate
principles in the 114-KPI framework (core.esg_principles_data.PRINCIPLES).

CRITICAL RULE (from the brief): "DO NOT ask an LLM: does company X support
KPI Y? and store the answer as fact." This module never does that — it
proposes CompanyKPIEvidenceLink rows with review_state='proposed', which
kpi_engine.derive_status_from_evidence() explicitly ignores until a human
reviewer confirms them (see EvidenceReviewAction / views.py). A proposal
that is never reviewed can never move a company's KPI status.

Matching happens in two conservative stages, both keyword/category based:
1. harvester's real EVIDENCE_CATEGORIES narrows to a small set of candidate
   PRINCIPLES categories (CATEGORY_MAP below) — an evidence item never gets
   matched against all 114 principles blindly.
2. Within that narrowed set, a plain word-overlap check between the
   evidence text and each principle's own title/metrics text decides
   whether to propose a link at all, and whether to propose it as
   'supports' (only when the evidence also contains a real positive-
   outcome signal word) or the more conservative 'context'. Never proposes
   'conflicts' automatically — asserting a conflict is left to explicit
   human/reviewer action, matching this module's evidence-first discipline.
"""
import re

from core.esg_principles_data import PRINCIPLES

# harvester.constants.EVIDENCE_CATEGORIES -> candidate core.esg_principles_data
# principle categories. Deliberately conservative/coarse — narrows the
# search space, never asserts a fact by itself.
CATEGORY_MAP = {
    'financial': {'economy'},
    'governance': {'governance'},
    'board': {'governance'},
    'ownership': {'governance'},
    'executive_compensation': {'governance', 'justice'},
    'strategy': {'longterm', 'governance'},
    'risk': {'risk'},
    'climate': {'earth', 'risk'},
    'emissions': {'earth', 'risk'},
    'energy': {'earth'},
    'water': {'earth'},
    'waste': {'earth'},
    'air_pollution': {'earth'},
    'biodiversity': {'earth'},
    'land_use': {'earth'},
    'supply_chain': {'justice', 'economy'},
    'human_rights': {'social', 'justice'},
    'workforce': {'social', 'human'},
    'health_safety': {'social', 'human'},
    'cybersecurity': {'risk', 'governance'},
    'innovation': {'longterm', 'knowledge'},
    'capital_projects': {'economy', 'longterm'},
    'regulatory_compliance': {'justice', 'risk'},
    'future_commitments': {'longterm'},
    'contradictions': set(),  # never a positive-match source category
}

_STOPWORDS = {
    'that', 'this', 'with', 'from', 'have', 'been', 'were', 'their', 'which',
    'about', 'across', 'under', 'over', 'into', 'than', 'also', 'such', 'each',
    'these', 'those', 'will', 'would', 'could', 'should', 'company', 'companies',
}
_WORD_RE = re.compile(r'[a-z]{5,}')

# Conservative positive-outcome signal words — presence alongside a matched
# principle upgrades a proposal from 'context' to 'supports'. Never used to
# assert 'conflicts' automatically.
_POSITIVE_SIGNAL_WORDS = {
    'reduced', 'achieved', 'published', 'implemented', 'verified', 'audited',
    'certified', 'disclosed', 'established', 'adopted', 'committed', 'invested',
}


def _significant_words(text):
    return {w for w in _WORD_RE.findall((text or '').lower()) if w not in _STOPWORDS}


PRINCIPLE_KEYWORDS = {
    p['id']: _significant_words(p['title'] + ' ' + ' '.join(p['metrics']))
    for p in PRINCIPLES
}
PRINCIPLES_BY_CATEGORY = {}
for _p in PRINCIPLES:
    PRINCIPLES_BY_CATEGORY.setdefault(_p['category'], []).append(_p)

MIN_WORD_OVERLAP = 2


def candidate_principles_for_evidence(evidence_category, evidence_text):
    """
    Returns a list of {'kpi_id', 'title', 'overlap_words', 'relationship'}
    dicts — real, inspectable matches, never a black-box relevance score.
    `relationship` is always 'supports' or 'context' (see module docstring
    for why 'conflicts' is never auto-proposed).
    """
    principle_categories = CATEGORY_MAP.get(evidence_category, set())
    if not principle_categories:
        return []

    text_words = _significant_words(evidence_text)
    if not text_words:
        return []

    has_positive_signal = bool(text_words & _POSITIVE_SIGNAL_WORDS)

    matches = []
    for category in principle_categories:
        for principle in PRINCIPLES_BY_CATEGORY.get(category, []):
            overlap = text_words & PRINCIPLE_KEYWORDS[principle['id']]
            if len(overlap) >= MIN_WORD_OVERLAP:
                matches.append({
                    'kpi_id': principle['id'],
                    'title': principle['title'],
                    'overlap_words': sorted(overlap),
                    'relationship': 'supports' if has_positive_signal else 'context',
                })
    return matches


def propose_kpi_links_for_evidence(company_profile, evidence, harvester_category):
    """
    Creates (or leaves alone, idempotent) CompanyKPIEvidenceLink rows with
    review_state='proposed' for every candidate match found for one real
    evidence_memory.EvidenceMemory row. Never confirms anything itself.
    Returns the list of created CompanyKPIEvidenceLink rows (empty if none
    matched or all already existed).
    """
    from company_intelligence.models import CompanyKPIAssessment, CompanyKPIEvidenceLink

    text = f'{evidence.text_chunk}'
    matches = candidate_principles_for_evidence(harvester_category, text)
    created = []
    for match in matches:
        assessment, _ = CompanyKPIAssessment.objects.get_or_create(
            company=company_profile, kpi_id=match['kpi_id'],
        )
        link, was_created = CompanyKPIEvidenceLink.objects.get_or_create(
            assessment=assessment, evidence=evidence,
            defaults={
                'relationship': match['relationship'],
                'review_state': 'proposed',
                'match_basis': f"Keyword overlap: {', '.join(match['overlap_words'])}",
            },
        )
        if was_created:
            created.append(link)
    return created
