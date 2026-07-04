"""
agent_runtime_model_router/services/safety_assertions.py — the Safety
Assertion Engine.

Deterministic pattern-matching only — no LLM judge. Every rule below is a
direct transcription of a "must never do" line already authored in the
relevant agent's own `ai_agents/<folder>/safety_rules.md` (e.g. Finance
Modelling Agent's own rules forbid "guaranteed savings" and unsupported
Shariah-compliance assertions almost verbatim), not an invented policy.

Severity: 'warning' | 'needs_review' | 'blocking'. `run_safety_assertions`
returns only the findings that actually matched (an empty list means a
clean run).
"""
import re

TIMING_NEGATION_WINDOW = 60


def _combined_text(parsed_output):
    texts = [str(v) for v in parsed_output.values() if isinstance(v, str)]
    return ' '.join(texts)


def _negated_nearby(text, match_start, window=TIMING_NEGATION_WINDOW):
    """Mirrors the negation-context-check pattern already used in ai_agent_council/tests.py."""
    preceding = text[max(0, match_start - window):match_start]
    return 'not' in preceding.lower()


def _rule_invented_missing_data(parsed_output, agent_name, text):
    missing_data = parsed_output.get('missing_data') or []
    trigger_phrases = ['assuming', 'estimated based on typical', 'in the absence of data']
    if not missing_data and any(phrase in text.lower() for phrase in trigger_phrases):
        return {
            'pattern_id': 'invented_missing_data', 'severity': 'blocking',
            'detail': 'Output implies missing data was filled in without any missing_data entry recorded.',
        }
    return None


def _rule_estimated_as_verified(parsed_output, agent_name, text):
    evidence_used = parsed_output.get('evidence_used') or []
    if re.search(r'\bverified\b', text, re.IGNORECASE) and not evidence_used:
        return {
            'pattern_id': 'estimated_as_verified', 'severity': 'blocking',
            'detail': 'Output claims "verified" with no supporting evidence reference.',
        }
    return None


def _rule_guaranteed_savings(parsed_output, agent_name, text):
    if re.search(r'\bguarantee(d)?\b', text, re.IGNORECASE) and re.search(
        r'saving|%|payback', text, re.IGNORECASE,
    ):
        return {
            'pattern_id': 'guaranteed_savings', 'severity': 'blocking',
            'detail': 'Output uses "guaranteed" language about savings, payback or percentage figures.',
        }
    return None


def _rule_funding_secured_without_evidence(parsed_output, agent_name, text):
    evidence_used = parsed_output.get('evidence_used') or []
    trigger = re.search(r'secured funding|funding is secured|committed capital', text, re.IGNORECASE)
    has_funding_evidence = any('funding' in str(e).lower() for e in evidence_used)
    if trigger and not has_funding_evidence:
        return {
            'pattern_id': 'funding_secured_without_evidence', 'severity': 'blocking',
            'detail': 'Output claims funding is secured with no funding-confirmation evidence reference.',
        }
    return None


def _rule_supplier_endorsement_from_quote_only(parsed_output, agent_name, text):
    evidence_used = parsed_output.get('evidence_used') or []
    trigger = re.search(r'recommend', text, re.IGNORECASE) and 'supplier' in text.lower()
    only_quote_evidence = bool(evidence_used) and all('quote' in str(e).lower() for e in evidence_used)
    if trigger and only_quote_evidence:
        return {
            'pattern_id': 'supplier_endorsement_from_quote_only', 'severity': 'needs_review',
            'detail': 'Supplier is recommended based only on a supplier quote, with no independent verification.',
        }
    return None


def _rule_mrv_verified_without_evidence(parsed_output, agent_name, text):
    missing_data = parsed_output.get('missing_data') or []
    if re.search(r'mrv verified', text, re.IGNORECASE) and missing_data:
        return {
            'pattern_id': 'mrv_verified_without_evidence', 'severity': 'blocking',
            'detail': 'Output claims MRV Verified status while missing_data is still non-empty.',
        }
    return None


def _rule_visual_hypothesis_as_fact(parsed_output, agent_name, text):
    if agent_name != 'Photo / Visual Evidence Agent':
        return None
    risk_flags = parsed_output.get('risk_flags') or []
    asserts_fact = re.search(r'\bconfirmed\b', text, re.IGNORECASE) is not None
    hedged = re.search(r'hypothesis|appears to|suggests', text, re.IGNORECASE) is not None
    if asserts_fact and not hedged and 'unverified_visual_hypothesis' not in risk_flags:
        return {
            'pattern_id': 'visual_hypothesis_as_fact', 'severity': 'needs_review',
            'detail': 'Visual finding is asserted as confirmed fact rather than a flagged hypothesis.',
        }
    return None


def _rule_external_action_without_permission(parsed_output, agent_name, text):
    next_action = str(parsed_output.get('next_action', ''))
    human_approval_required = parsed_output.get('human_approval_required')
    trigger = re.search(
        r'\b(send|publish|notify|email)\b.*\b(supplier|investor|funder|public)\b',
        next_action or text, re.IGNORECASE,
    )
    if trigger and human_approval_required is False:
        return {
            'pattern_id': 'external_action_without_permission', 'severity': 'blocking',
            'detail': 'Output proposes an external action without requiring human approval.',
        }
    return None


def _rule_public_impact_claim_without_approval(parsed_output, agent_name, text):
    human_approval_required = parsed_output.get('human_approval_required')
    trigger = 'public' in text.lower() and re.search(r'impact|press release', text, re.IGNORECASE)
    if trigger and human_approval_required is False:
        return {
            'pattern_id': 'public_impact_claim_without_approval', 'severity': 'blocking',
            'detail': 'Output makes a public impact claim without requiring human approval.',
        }
    return None


def _rule_unsupported_microsoft_claim(parsed_output, agent_name, text):
    match = re.search(r'Microsoft certif|Microsoft partner|official Microsoft', text, re.IGNORECASE)
    if match and not _negated_nearby(text, match.start()):
        return {
            'pattern_id': 'unsupported_microsoft_claim', 'severity': 'blocking',
            'detail': 'Output asserts a Microsoft certification/partnership claim without negation context.',
        }
    return None


def _rule_unsupported_shariah_fatwa_claim(parsed_output, agent_name, text):
    match = re.search(
        r'Shariah[- ]compliant|Shariah certif|is a fatwa|fatwa-style', text, re.IGNORECASE,
    )
    if match and not _negated_nearby(text, match.start()):
        return {
            'pattern_id': 'unsupported_shariah_fatwa_claim', 'severity': 'blocking',
            'detail': 'Output asserts a Shariah-compliance or fatwa-style claim without negation context.',
        }
    return None


RULES = [
    _rule_invented_missing_data,
    _rule_estimated_as_verified,
    _rule_guaranteed_savings,
    _rule_funding_secured_without_evidence,
    _rule_supplier_endorsement_from_quote_only,
    _rule_mrv_verified_without_evidence,
    _rule_visual_hypothesis_as_fact,
    _rule_external_action_without_permission,
    _rule_public_impact_claim_without_approval,
    _rule_unsupported_microsoft_claim,
    _rule_unsupported_shariah_fatwa_claim,
]


def run_safety_assertions(parsed_output, agent_name, context=None):
    """Returns only the findings that matched — an empty list means a clean run."""
    text = _combined_text(parsed_output)
    findings = []
    for rule in RULES:
        finding = rule(parsed_output, agent_name, text)
        if finding:
            findings.append(finding)
    return findings


def aggregate_safety_status(findings):
    """Worst severity wins: blocking > needs_review > warning > pass."""
    severities = {f['severity'] for f in findings}
    if 'blocking' in severities:
        return 'blocking'
    if 'needs_review' in severities:
        return 'needs_review'
    if 'warning' in severities:
        return 'warning'
    return 'pass'
