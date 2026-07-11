"""
capital_guardian/services/better_way.py — vertical-slice PR 4: human-
reviewed scenario comparison across real InterventionOption rows for one
OperationalLoss, reusing the existing, unmodified
capital_allocation_scoring.score_intervention_option() and
ranking.rank_capital_allocation_options() directly — no scoring logic is
duplicated here.

Baseline-gaming guard (documented, not a change to the shared engine): the
shared scorer's `payback` sub-score defaults to 65 when
estimated_payback_months is None, which reflects a same-cycle tactical-
action assumption that's appropriate for the Meat Cold-Chain golden case
this scorer was built for, but wrong for a genuine 'do_nothing' baseline,
which realises no payback at all because no capital was deployed. This
module overrides ONLY that one sub-score, ONLY for intervention_type ==
'do_nothing', on the dict returned by the real scorer — capital_allocation_
scoring.py and ranking.py themselves are never touched, so the existing
Meat Cold-Chain golden-case regression test is unaffected. As a second,
independent safeguard (not a substitute for the above), if the baseline
still ranks first despite this, the result is flagged with an explicit
warning rather than presented as a recommendation — the true composite
score is never hidden or fudged, only never silently presented as "the
answer" when it's the do-nothing option.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

from waste_to_value_capital_allocation_engine.services.capital_allocation_scoring import score_intervention_option
from waste_to_value_capital_allocation_engine.services.ranking import rank_capital_allocation_options

from capital_guardian.services.intervention_safety_gate import classify_intervention_safety

# The shared engine's own golden-case constant (capital_allocation_bridge.py).
# recoverable_value scoring is calibrated for inventory-recovery use cases
# and is not materially meaningful for a heating retrofit — included only
# because it's part of the shared engine's fixed 13-dimension output.
DEFAULT_INVENTORY_VALUE_CEILING = 80000

_CLASSIFICATION_TAG_RE = re.compile(r'\[intervention_classification:\s*(real|estimated|illustrative)\]', re.IGNORECASE)


def tag_classification(description, classification):
    """Appends a machine-parseable classification tag to a human-entered
    description — the only place InterventionOption can honestly carry this,
    since the model has no is_demo/classification field (documented
    limitation, same as OperationalLoss in PR 3)."""
    description = (description or '').strip()
    tag = f'[intervention_classification: {classification}]'
    return f'{description}\n\n{tag}' if description else tag


def extract_classification(description):
    match = _CLASSIFICATION_TAG_RE.search(description or '')
    return match.group(1).lower() if match else 'estimated'


@dataclass
class BetterWayResult:
    loss: object
    project_name: str
    ranked: list = field(default_factory=list)
    blocked: list = field(default_factory=list)
    capital_at_risk_ceiling: float = 0
    baseline_ranked_first: bool = False
    baseline_warning: str = ''
    why_top_ranked: str = ''
    trade_offs: dict = field(default_factory=dict)
    limitations: list = field(default_factory=list)


def _capital_at_risk_ceiling(loss):
    """
    Prefers the loss's explicit projected_future_loss; falls back to the
    already-incurred financial_loss_amount as the best available real proxy
    when no forward projection was entered — never a fabricated number,
    always one of the two real fields the human reviewer actually entered.
    """
    return loss.projected_future_loss or loss.financial_loss_amount or 0


def compare_interventions(project, loss):
    """
    project: the gold_intelligence.GoldProject this loss's evidence/analysis
    is scoped to (needed only to look up the reviewed safety pathways).
    loss: a real waste_to_value_capital_allocation_engine.models.OperationalLoss
    with its real, already-persisted InterventionOption children.
    """
    options = list(loss.interventions.all())
    ceiling = _capital_at_risk_ceiling(loss)

    ranked_candidates = []
    blocked = []
    for option in options:
        classification = extract_classification(option.description)
        safety = classify_intervention_safety(project, option, classification=classification)

        if safety['status'] == 'blocked':
            blocked.append({'option': option, 'reason': safety['reason']})
            continue

        scores = score_intervention_option(option, ceiling, DEFAULT_INVENTORY_VALUE_CEILING)
        if option.intervention_type == 'do_nothing':
            scores['payback'] = 0  # see module docstring — no capital deployed, no payback realised
        ranked_candidates.append({
            'option': option, 'safety_status': safety['status'], 'safety_reason': safety['reason'],
            **scores,
        })

    ranked = rank_capital_allocation_options(ranked_candidates)

    baseline_ranked_first = bool(ranked) and ranked[0]['option'].intervention_type == 'do_nothing'
    baseline_warning = ''
    if baseline_ranked_first:
        baseline_warning = (
            'The current baseline (continuing as-is) currently ranks highest under the entered '
            'assumptions. This does not mean continuing is recommended — it means the alternative '
            'options need more complete or favourable assumptions entered, or a human reviewer should '
            'examine the ranking before treating it as a recommendation.'
        )

    why_top_ranked = ''
    if ranked and not baseline_ranked_first:
        top = ranked[0]
        why_top_ranked = (
            f"Based on the currently entered evidence and assumptions, \"{top['option'].title}\" scores "
            f"highest on the weighted composite ranking ({top['composite_score']}) among the "
            f"{len(ranked)} compared option(s). This is a recommendation for human review, never an "
            f"autonomous capital decision."
        )

    trade_offs = {}
    if ranked:
        with_payback = [c for c in ranked if c['option'].estimated_payback_months is not None]
        if with_payback:
            trade_offs['fastest_payback'] = min(with_payback, key=lambda c: c['option'].estimated_payback_months)
        trade_offs['highest_capital_efficiency'] = max(ranked, key=lambda c: c['capital_efficiency'])
        trade_offs['lowest_capex'] = min(ranked, key=lambda c: c['option'].capex_estimate)

    limitations = [
        'Scores are derived entirely from human-entered assumptions (CAPEX, savings, readiness, risk) — '
        'none of them are independently verified.',
        'recoverable_value scoring is calibrated for inventory-recovery use cases (the shared engine\'s '
        'original design) and is not materially meaningful for a heating retrofit; it is included only '
        'because it is part of the shared 13-dimension scoring output.',
        'The capital-at-risk ceiling used to scale financial_return/loss_avoided comes from the loss\'s '
        'projected_future_loss field if set, otherwise its already-incurred financial_loss_amount — not '
        'a separately verified capital-at-risk study.',
    ]

    return BetterWayResult(
        loss=loss, project_name=project.name, ranked=ranked, blocked=blocked,
        capital_at_risk_ceiling=ceiling, baseline_ranked_first=baseline_ranked_first,
        baseline_warning=baseline_warning, why_top_ranked=why_top_ranked, trade_offs=trade_offs,
        limitations=limitations,
    )
