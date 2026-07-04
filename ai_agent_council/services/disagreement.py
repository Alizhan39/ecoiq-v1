"""
ai_agent_council/services/disagreement.py — deterministic disagreement classification.

Classifies a disagreement between two AgentTask positions using only
structured fields already on those tasks (confidence, risk_flags,
evidence_refs) — never a random label, never an LLM call. Dissenting
opinions are never hidden: this function only decides how a disagreement is
described and how it should be resolved, not whether it gets shown.
"""

TIMING_KEYWORDS = {'timeline', 'schedule', 'delay', 'timing', 'deadline'}

# Confidence gap (points) above which two positions built on the same
# evidence are treated as an assumption disagreement rather than noise.
ASSUMPTION_CONFIDENCE_GAP = 15


def classify_conflict(position_a, position_b):
    """
    Returns (conflict_type, resolution_method) — both values drawn from the
    model's CONFLICT_TYPE_CHOICES / RESOLUTION_METHOD_CHOICES. Rule cascade,
    evaluated in order; the first matching rule wins.
    """
    evidence_a = set(position_a.evidence_refs or [])
    evidence_b = set(position_b.evidence_refs or [])
    risk_a = set(position_a.risk_flags or [])
    risk_b = set(position_b.risk_flags or [])
    confidence_a = position_a.confidence or 0
    confidence_b = position_b.confidence or 0
    confidence_delta = abs(confidence_a - confidence_b)
    shared_evidence = evidence_a & evidence_b

    # Rule 1: either side flags a timing/schedule risk — this is a timing
    # disagreement regardless of evidence/confidence, and is mechanical
    # enough (a date either fits the plan or it doesn't) to resolve on its own.
    if risk_a & TIMING_KEYWORDS or risk_b & TIMING_KEYWORDS:
        return 'timing', 'resolve_automatically'

    # Rule 2: the two positions cite no common evidence at all — they are
    # not disagreeing about interpretation, they are working from different
    # facts, so more evidence is needed before anything else can be resolved.
    if not shared_evidence and (evidence_a or evidence_b):
        return 'evidence', 'request_more_evidence'

    # Rule 3: risk flags differ (one sees a risk the other doesn't) even
    # though they share evidence — this is a difference in risk appetite,
    # not fact, so it needs a human to weigh in.
    if risk_a != risk_b and (risk_a or risk_b):
        return 'risk_tolerance', 'require_human_review'

    # Rule 4: same evidence, but confidence diverges sharply — the two
    # agents are making different assumptions on top of the same facts.
    # Asking a third agent to weigh in is cheaper than an immediate human
    # escalation.
    if shared_evidence and confidence_delta >= ASSUMPTION_CONFIDENCE_GAP:
        return 'assumption', 'ask_another_agent'

    # Rule 5: same evidence, similar confidence, but the two agents come
    # from different specialisms (e.g. Finance vs Governance) — a domain
    # conflict where both views are legitimate and the minority one must be
    # preserved rather than resolved away.
    if shared_evidence and position_a.agent_name != position_b.agent_name:
        return 'domain', 'preserve_minority_opinion'

    # Rule 6: fallback — a concrete factual disagreement that doesn't fit
    # any of the above (e.g. disjoint risk/evidence signals of similar
    # weight); always requires a human to adjudicate the fact itself.
    return 'factual', 'require_human_review'
