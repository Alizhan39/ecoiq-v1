"""
decision_studio/services/query_understanding.py — deterministic intent
classification, entity resolution and scope extraction over a free-text
decision question.

Deliberately NOT an LLM call, and NOT a trained classifier — a keyword rule
table over the question text, in the exact same style already proven at
ai_agent_workbench.services.recommender.recommend_agent_for_task() and
harvester.adapters.classify_text(): transparent, inspectable, zero cost,
zero prompt-injection surface for this step (the question text never
reaches an LLM prompt here). The heavier, optional agent-execution step
further down the pipeline is where a real LLM call may happen — gated by
execution_mode exactly as everywhere else in the platform.
"""
import re

# Ordered: first matching rule wins (mirrors recommender.py's own convention).
INTENT_RULES = [
    ('COMPARE', ['compare', ' versus ', ' vs ', 'difference between', 'differences between']),
    ('ASSESS', ['too weak', 'evidence weak', 'insufficient evidence', 'evidence quality', 'evidence coverage']),
    ('PRIORITISE', ['prioriti', 'should be prioriti', 'deserve', 'go first', 'which should']),
    ('RANK', ['rank', 'strongest combination', 'order by', 'top ', 'which companies have the']),
    ('FIND_RISK', ['risk', 'exposure', 'vulnerab', 'unusual risk', 'danger']),
    ('FIND_OPPORTUNITY', ['opportunit', 'attractive', 'invest in', 'worth investing']),
    ('EXPLAIN', ['why ', 'explain', 'reason for', 'reason why']),
    ('RECOMMEND', ['recommend', 'should we', 'advice', 'suggest', 'what should']),
    ('INVESTIGATE', ['investigate', 'look into', 'dig into', 'anomal', 'unusual pattern']),
    ('ASSESS', ['assess', 'evaluate', 'how strong is', 'how good is', 'how reliable']),
]

# "UK" -> the exact countries.CountryProfile.name it should match.
COUNTRY_SYNONYMS = {
    'uk': 'United Kingdom', 'u.k.': 'United Kingdom', 'britain': 'United Kingdom', 'great britain': 'United Kingdom',
    'usa': 'United States', 'u.s.': 'United States', 'us': 'United States', 'america': 'United States',
    'saudi': 'Saudi Arabia', 'ksa': 'Saudi Arabia',
    'uae': 'United Arab Emirates', 'emirates': 'United Arab Emirates',
    'turkey': 'Türkiye', 'kazakhstan': 'Kazakhstan',
}

# league.Company.SECTOR_CHOICES label text -> the stored code.
_SECTOR_KEYWORDS = {
    'energy': 'energy', 'power': 'energy', 'oil': 'oil_gas', 'gas': 'oil_gas',
    'mining': 'mining', 'chemical': 'chemical', 'metallurg': 'metallurgy', 'steel': 'metallurgy',
    'transport': 'transport', 'agricultur': 'agriculture', 'farm': 'agriculture',
}

TIME_HORIZON_PATTERN = re.compile(r'(\d+)\s*[- ]?\s*(year|month|yr)', re.IGNORECASE)

DECISION_CONTEXT_KEYWORDS = [
    'sovereign wealth fund', 'pension fund', 'institutional investor', 'private equity',
    'government', 'regulator', 'lender', 'insurer', 'asset manager',
]

MAX_ENTITY_MATCHES = 20  # cost control — never resolve an unbounded entity list


def classify_intent(question_text):
    text = (question_text or '').lower()
    for intent, keywords in INTENT_RULES:
        if any(kw in text for kw in keywords):
            return intent
    return 'UNKNOWN'


def extract_scope(question_text):
    text = (question_text or '').lower()

    country = None
    from countries.models import CountryProfile
    for name in CountryProfile.objects.values_list('name', flat=True):
        if name.lower() in text:
            country = name
            break
    if country is None:
        for synonym, canonical in COUNTRY_SYNONYMS.items():
            if synonym in text:
                country = canonical
                break

    sector = None
    for keyword, code in _SECTOR_KEYWORDS.items():
        if keyword in text:
            sector = code
            break

    time_match = TIME_HORIZON_PATTERN.search(text)
    time_horizon = f'{time_match.group(1)} {time_match.group(2)}s' if time_match else None

    decision_context = next((kw for kw in DECISION_CONTEXT_KEYWORDS if kw in text), None)

    requested_dimensions = []
    dimension_keywords = {
        'investment opportunity': 'investment_opportunity', 'modernisation potential': 'modernisation_priority',
        'modernization potential': 'modernisation_priority', 'climate risk': 'climate_risk',
        'governance': 'governance_esg', 'evidence quality': 'evidence_quality',
    }
    for phrase, dimension in dimension_keywords.items():
        if phrase in text:
            requested_dimensions.append(dimension)

    return {
        'country': country, 'sector': sector, 'time_horizon': time_horizon,
        'decision_context': decision_context, 'requested_dimensions': requested_dimensions,
    }


def resolve_entities(question_text, scope):
    """
    Returns a list of {'type', 'id', 'name', 'match_type'} dicts.
    match_type is one of: 'exact', 'partial', 'multiple', 'none' — never
    silently assumed. Company name mentions are matched by substring against
    real league.Company rows; country/sector are taken from the already-
    extracted scope (exact lookups, not fuzzy).
    """
    from companies.models import CompanyProfile
    from countries.models import CountryProfile
    from league.models import Company

    entities = []
    text = (question_text or '').lower()

    if scope.get('country'):
        country_profile = CountryProfile.objects.filter(name=scope['country']).first()
        entities.append({
            'type': 'country', 'id': country_profile.pk if country_profile else None,
            'name': scope['country'], 'match_type': 'exact' if country_profile else 'none',
        })

    if scope.get('sector'):
        entities.append({'type': 'sector', 'id': None, 'name': scope['sector'], 'match_type': 'exact'})

    # Explicit company-name mentions: only companies with at least 4 real
    # characters in their name are checked as substrings, to avoid a short
    # name like "BP" matching almost every sentence.
    candidate_names = list(Company.objects.values_list('name', flat=True))
    for name in candidate_names:
        if len(name) >= 4 and name.lower() in text:
            profile = CompanyProfile.objects.filter(company__name=name).first()
            entities.append({
                'type': 'company', 'id': profile.pk if profile else None,
                'name': name, 'match_type': 'exact' if profile else 'partial',
            })
            if len(entities) >= MAX_ENTITY_MATCHES:
                break

    return entities
