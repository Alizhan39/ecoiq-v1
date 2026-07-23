"""
good_agents/services/human_review.py — the one write path for
HumanReviewDecision (PR4 Phase 12). Append-only: a new review is always a
new row, never an edit of a prior one — the full history is what
`prioritisation.py`'s deterministic feedback adjustment reads.
"""
from good_agents.models import HumanReviewDecision


def submit_review(opportunity, decision, *, rationale='', reviewer=None):
    if decision not in dict(HumanReviewDecision.DECISION_CHOICES):
        raise ValueError(f'Unknown HumanReviewDecision.decision: {decision!r}')
    return HumanReviewDecision.objects.create(
        opportunity=opportunity, decision=decision, rationale=rationale, reviewer=reviewer,
    )
