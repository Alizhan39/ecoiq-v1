"""
waste_to_value_capital_allocation_engine/services/capital_guardian_handoff.py
— Phase 1A: the first real connection from a human-approved
CapitalAllocationDecision to capital_guardian's post-decision monitoring.

VALUE LOSS -> RECOMMENDATION -> CAPITAL ALLOCATION DECISION -> HUMAN APPROVAL
-> CAPITAL GUARDIAN is the flow this module completes the last hop of.

Never automatic: nothing else in this app calls promote_to_capital_guardian()
— it is not wired into ranking.py, capital_allocation_scoring.py, or either
agent bridge. An AI system may rank and recommend (that's what ranking.py
already does); only an explicit call to this function, on a decision a human
has already approved, starts real Capital Guardian monitoring.

On the approval check: CapitalAllocationDecision does NOT have a
`human_approved` boolean field (only CapitalRouteMatch does) — its real,
persisted approval state is `approval_status`
('approved'/'approved_with_conditions'/'rejected'/'pending'), set entirely
by governance.py's create_governed_investment_case() from a real Council
process. This module gates on that existing field directly rather than
routing through human_approval_gate.py's require_human_approval(), which
was built around a `.human_approved` boolean this model doesn't actually
persist — using it here would mean either fabricating a second, parallel
approval flag or having the gate always fail. approval_status already IS
the real human-approval mechanism for this model; this is not a new one.
"""
from dataclasses import dataclass
from typing import Optional

APPROVED_STATUSES = {'approved', 'approved_with_conditions'}


class DecisionNotApprovedError(Exception):
    """Raised when promotion is attempted on a CapitalAllocationDecision with
    no real human/Council approval recorded (approval_status not in
    APPROVED_STATUSES). Capital tracking must never start silently for an
    unapproved decision."""


@dataclass
class PromotionResult:
    status: str  # 'promoted' | 'already_promoted' | 'no_matching_project' | 'ambiguous_project_match'
    project: Optional[object] = None
    governance: Optional[object] = None
    message: str = ''


class _AmbiguousMatch(Exception):
    """Internal signal only — more than one GoldProject shares this name."""


def _find_matching_gold_project(decision):
    """
    Matches on CapitalAllocationDecision.project — a plain text field (see
    waste_to_value's models.py docstring: no trustworthy Project model
    existed to FK to when this app was built). Exact, case-insensitive name
    match only, never fuzzy — a wrong match would start real capital
    monitoring against the wrong asset.

    GoldProject.name has no uniqueness constraint (only .slug does), so more
    than one row can share a name. Silently taking the first match (e.g.
    .first()) could route capital monitoring to the wrong physical asset —
    an ambiguous match is treated the same as no match at all, never guessed.
    """
    from gold_intelligence.models import GoldProject

    project_name = (decision.project or '').strip()
    if not project_name:
        return None
    matches = list(GoldProject.objects.filter(name__iexact=project_name)[:2])
    if len(matches) > 1:
        raise _AmbiguousMatch(project_name)
    return matches[0] if matches else None


def promote_to_capital_guardian(decision, actor=None):
    """
    decision: a waste_to_value_capital_allocation_engine.models.CapitalAllocationDecision.
    actor: the real Django User performing the promotion, for audit
    attribution (capital_guardian's ProjectGovernance signal already logs
    `changed_by` when `_cg_changed_by` is set before save — same convention
    used by capital_guardian/admin.py). Left None when genuinely unknown;
    never guessed.

    Raises DecisionNotApprovedError if the decision has not been approved —
    this is the one case that must stop the caller, since proceeding would
    start capital tracking for a decision no human ever approved.

    Otherwise never raises for an expected outcome: a missing matching
    GoldProject is an honest, reportable result (status='no_matching_project'),
    not an error, and no fake GoldProject is ever created to force a match.

    Idempotent: calling this twice on the same decision returns
    status='already_promoted' the second time and does not create a second
    ProjectGovernance row (ProjectGovernance is a real OneToOneField to
    GoldProject, so at most one can ever exist per project).
    """
    if decision.approval_status not in APPROVED_STATUSES:
        raise DecisionNotApprovedError(
            f"CapitalAllocationDecision {decision.pk} has approval_status="
            f"{decision.approval_status!r} — capital tracking cannot start "
            f"without explicit human/Council approval."
        )

    try:
        project = _find_matching_gold_project(decision)
    except _AmbiguousMatch:
        return PromotionResult(
            status='ambiguous_project_match',
            message=(
                f'More than one GoldProject is named {decision.project!r} — '
                f'refusing to guess which one this decision belongs to. Nothing '
                f'was created; disambiguate the GoldProject names before promoting.'
            ),
        )
    if project is None:
        return PromotionResult(
            status='no_matching_project',
            message=(
                f'No GoldProject named {decision.project!r} was found — nothing was '
                f'created. Add or rename the matching GoldProject before promoting '
                f'this decision into Capital Guardian monitoring.'
            ),
        )

    from capital_guardian.models import ProjectGovernance

    existing = ProjectGovernance.objects.filter(project=project).first()
    if existing is not None:
        return PromotionResult(
            status='already_promoted', project=project, governance=existing,
            message=f'{project.name} is already under Capital Guardian monitoring.',
        )

    governance = ProjectGovernance(project=project, is_demo=False)
    if actor is not None:
        # Set before save so capital_guardian/signals.py's post_save handler
        # (which reads this attribute at save time) attributes the creation
        # AuditLogEntry to the real approving user, not changed_by=None.
        governance._cg_changed_by = actor
    governance.save()

    return PromotionResult(
        status='promoted', project=project, governance=governance,
        message=f'Capital Guardian monitoring started for {project.name}.',
    )
