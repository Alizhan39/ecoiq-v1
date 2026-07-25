"""
public_need_discovery/services/sensitivity.py — Phase 13: the sensitivity
gate applied at the actionability layer, one stage earlier than
outreach_readiness's own identical gate (Phase 13 there). Evidence
importance is never confused with permission to progress: a sensitive
case can be `evidence_valid_but_outreach_inappropriate` even when every
other actionability criterion passes.
"""
from django.utils import timezone

from public_need_discovery.models import PilotCandidateAssessment


class SensitivityReviewNotAllowedError(Exception):
    pass


def record_sensitivity_review(candidate, *, actor, categories, notes='', outreach_inappropriate=False):
    if actor is None:
        raise SensitivityReviewNotAllowedError('Sensitivity review requires a real actor.')
    candidate.is_sensitive = bool(categories)
    candidate.sensitivity_categories = categories
    candidate.sensitivity_notes = notes
    candidate.evidence_valid_but_outreach_inappropriate = outreach_inappropriate
    candidate.assessed_by = actor
    candidate.assessed_at = timezone.now()
    candidate.save(update_fields=[
        'is_sensitive', 'sensitivity_categories', 'sensitivity_notes', 'evidence_valid_but_outreach_inappropriate',
        'assessed_by', 'assessed_at', 'updated_at',
    ])
    if outreach_inappropriate:
        from public_need_discovery.services.actionability import set_actionability_state
        set_actionability_state(
            candidate, 'sensitive_review_required', actor=actor,
            rationale=f'Evidence remains valid; outreach itself is inappropriate. Categories: {", ".join(categories)}.',
        )
    return candidate


# Same category vocabulary that trips a stricter review, applied at
# discovery time via free-text signal fields — deterministic keyword
# match only, never a black-box classifier (Phase 13's own discipline).
_SENSITIVITY_KEYWORDS = {
    'disaster': ['earthquake', 'flood', 'wildfire', 'hurricane', 'tsunami', 'disaster'],
    'death_or_injury': ['death', 'fatalit', 'killed', 'injur', 'casualt'],
    'children': ['child', 'children', 'school', 'infant', 'minor'],
    'health': ['hospital', 'disease', 'outbreak', 'epidemic', 'pandemic', 'health emergency'],
    'war_or_conflict': ['war', 'conflict', 'attack', 'military', 'refugee'],
    'vulnerable_communities': ['refugee', 'homeless', 'displaced', 'vulnerable'],
    'emergency_response': ['emergency', 'evacuation', 'rescue', 'significant earthquake'],
}


def suggest_sensitivity_categories(opportunity):
    """
    A deterministic keyword pass over the opportunity's own real
    title/problem_statement/summary text — a starting point for a human
    reviewer, never itself a decision (mirrors outreach_readiness's own
    sensitivity suggestion discipline: suggestion, not verdict).
    """
    haystack = ' '.join(filter(None, [
        opportunity.title, opportunity.problem_statement, opportunity.unmet_need_or_waste,
    ])).lower()
    return sorted({
        category for category, keywords in _SENSITIVITY_KEYWORDS.items()
        if any(keyword in haystack for keyword in keywords)
    })
