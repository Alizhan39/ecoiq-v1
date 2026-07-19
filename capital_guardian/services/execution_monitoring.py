"""
capital_guardian/services/execution_monitoring.py — vertical-slice PR 6:
CAPITAL GUARDIAN -> HUMAN-ENTERED IMPLEMENTATION MONITORING -> EXPECTED VS
ACTUAL -> HUMAN-REVIEWED VERIFIED CAPITAL OUTCOME.

Reuses, never duplicates:
- capital_guardian.CapitalTraceEntry for capital committed/deployed (real,
  already-existing model; this module only aggregates it).
- gold_intelligence.MineTimelineMilestone for implementation milestones.
- waste_to_value_capital_allocation_engine.services.mrv_outcomes.
  record_verified_outcome() for all VerifiedCapitalOutcome persistence — this
  module never writes actual_* fields to that model directly.

A CapitalAllocationDecision has no FK to gold_intelligence.GoldProject (see
waste_to_value's own models.py docstring — `project` is a plain CharField,
matched by name elsewhere in capital_guardian_handoff.find_matching_gold_
project()). capital_decisions_for_project() below does the same honest
name-match rather than inventing an FK.

Safety gate (Task 9): record_verified_outcome() defaults mrv_status to
'verified' and derives verified_status='verified' directly from it — calling
it blind from an ordinary staff data-entry form would auto-verify on first
submission, which the founder's brief explicitly forbids ("the same user
entering a result does not automatically make it independently verified").
MONITORING_MRV_STATUS_CHOICES below excludes 'verified' entirely, and
record_monitoring_outcome() raises if a caller tries to pass it anyway. The
only path to mrv_status='verified' is the existing, already-staff-gated
Django admin change form for VerifiedCapitalOutcome (no readonly_fields there
— same precedent as CapitalAllocationDecision.approval_status in PR 5).
"""
from waste_to_value_capital_allocation_engine.models import (
    MRV_STATUS_CHOICES, CapitalAllocationDecision,
)
from waste_to_value_capital_allocation_engine.services.mrv_outcomes import record_verified_outcome

# Every real MRV status a human can honestly report at data-entry time,
# short of independent verification itself.
MONITORING_MRV_STATUS_CHOICES = [c for c in MRV_STATUS_CHOICES if c[0] != 'verified']


class VerificationNotAllowedHereError(Exception):
    """Raised if a caller tries to mark an outcome 'verified' through the
    ordinary monitoring form. Verification only ever happens through the
    existing Django admin change form for VerifiedCapitalOutcome."""


def capital_decisions_for_project(project):
    """Every real CapitalAllocationDecision whose free-text `project` name
    matches this GoldProject — the same honest exact-match convention as
    capital_guardian_handoff.find_matching_gold_project(), just reversed."""
    return (
        CapitalAllocationDecision.objects
        .filter(project=project.name)
        .select_related('intervention', 'intervention__operational_loss', 'verified_outcome')
        .order_by('ranking', '-created_at')
    )


def capital_summary(project):
    """Capital committed (internally approved spend) / deployed (actually
    paid) / remaining (committed not yet paid) — all real sums over
    CapitalTraceEntry, never a fabricated budget total. Negative "remaining"
    is shown honestly (it means more has been paid than was ever approved),
    never clamped to zero."""
    entries = list(project.capital_trace_entries.all())
    committed = sum(e.amount_usd for e in entries if e.approval_status == 'approved')
    deployed = sum(e.amount_usd for e in entries if e.payment_status == 'paid')
    return {
        'capital_committed_usd': round(committed, 2),
        'capital_deployed_usd': round(deployed, 2),
        'capital_remaining_usd': round(committed - deployed, 2),
        'entry_count': len(entries),
    }


NOT_YET_REPORTED = 'NOT YET REPORTED'


def _variance(expected, actual):
    if expected is None or actual is None:
        return None
    return round(actual - expected, 2)


def expected_vs_actual(decision):
    """
    Compares the selected InterventionOption's estimated_* assumptions
    against the linked VerifiedCapitalOutcome's actual_* fields (if any),
    for one CapitalAllocationDecision. Never fabricates a value: every
    "actual" field is either a real stored number or the literal string
    NOT_YET_REPORTED, and every variance is None unless both sides are real.
    """
    option = decision.intervention
    outcome = getattr(decision, 'verified_outcome', None)

    def actual_or_stub(value):
        return value if (outcome is not None and value is not None) else NOT_YET_REPORTED

    capex_actual = outcome.capex_actual if outcome else None
    opex_actual = outcome.opex_actual if outcome else None
    savings_actual = outcome.savings_actual if outcome else None
    loss_avoided_actual = outcome.loss_avoided_actual if outcome else None
    payback_actual = outcome.payback_actual if outcome else None

    return {
        'expected_capex': option.capex_estimate,
        'actual_capex': actual_or_stub(capex_actual),
        'capex_variance': _variance(option.capex_estimate, capex_actual),

        'expected_opex_change': option.opex_change,
        'actual_opex_change': actual_or_stub(opex_actual),
        'opex_variance': _variance(option.opex_change, opex_actual),

        'expected_savings': option.estimated_annual_savings,
        'actual_savings': actual_or_stub(savings_actual),
        'savings_variance': _variance(option.estimated_annual_savings, savings_actual),

        'expected_loss_avoided': option.estimated_loss_avoided,
        'actual_loss_avoided': actual_or_stub(loss_avoided_actual),
        'loss_avoided_variance': _variance(option.estimated_loss_avoided, loss_avoided_actual),

        'expected_payback_months': option.estimated_payback_months,
        'actual_payback_months': actual_or_stub(payback_actual),
        'payback_variance': _variance(option.estimated_payback_months, payback_actual),

        # No field on either model honestly captures an "actual" implementation
        # timeline yet (see module docstring / PR6 audit) — reported plainly
        # rather than inferred from unrelated milestone dates.
        'expected_timeline': option.implementation_time or NOT_YET_REPORTED,
        'actual_timeline': 'Not yet tracked at the decision level — see Milestones below.',

        'outcome': outcome,
        'verified_status': outcome.get_verified_status_display() if outcome else 'Not yet reported',
        'mrv_status': outcome.get_mrv_status_display() if outcome else 'Not started',
        'evidence_quality': outcome.get_evidence_quality_display() if outcome else None,
    }


RESULT_ACHIEVED = 'achieved'
RESULT_PARTIALLY_ACHIEVED = 'partially_achieved'
RESULT_NOT_ACHIEVED = 'not_achieved'
RESULT_DISPUTED = 'disputed'
RESULT_INSUFFICIENT_EVIDENCE = 'insufficient_evidence'

RESULT_LABELS = {
    RESULT_ACHIEVED: 'Achieved',
    RESULT_PARTIALLY_ACHIEVED: 'Partially Achieved',
    RESULT_NOT_ACHIEVED: 'Not Achieved',
    RESULT_DISPUTED: 'Disputed',
    RESULT_INSUFFICIENT_EVIDENCE: 'Insufficient Evidence',
}


def outcome_result_label(ctx):
    """
    Classifies one expected_vs_actual() dict as achieved / partially
    achieved / not achieved / disputed / insufficient evidence — reusing
    the exact real expected/actual loss-avoided figures that dict already
    carries, never a second independent computation of them. Disputed and
    insufficient-evidence are checked first and always take precedence
    over the numeric comparison: a disputed or evidence-poor outcome is
    never labelled achieved/not achieved regardless of the raw numbers, and
    "no outcome recorded yet" is honestly insufficient evidence, not a
    silent default to any other state.
    """
    outcome = ctx['outcome']
    if outcome is None:
        return RESULT_INSUFFICIENT_EVIDENCE
    if outcome.mrv_status == 'disputed':
        return RESULT_DISPUTED
    if outcome.evidence_quality == 'missing':
        return RESULT_INSUFFICIENT_EVIDENCE

    actual = ctx['actual_loss_avoided']
    expected = ctx['expected_loss_avoided']
    if actual == NOT_YET_REPORTED or not expected:
        return RESULT_INSUFFICIENT_EVIDENCE

    ratio = actual / expected
    if ratio >= 0.9:
        return RESULT_ACHIEVED
    if ratio > 0:
        return RESULT_PARTIALLY_ACHIEVED
    return RESULT_NOT_ACHIEVED


def record_monitoring_outcome(decision, *, mrv_status, evidence_quality='medium', capex_actual=None,
                               opex_actual=0, loss_avoided_actual=None, savings_actual=0, reviewer_note=''):
    """
    The ONLY entry point the Capital Guardian monitoring UI uses to persist
    a VerifiedCapitalOutcome. Delegates all real computation (value_
    recovered_actual, payback_actual, verified_status) to the existing
    record_verified_outcome() — this function adds exactly one thing:
    refusing to let a plain monitoring submission claim mrv_status='verified'.

    reviewer_note is appended to the existing next_capital_allocation_signal
    free-text field (VerifiedCapitalOutcome has no dedicated reviewer-notes
    field — see PR6 audit) rather than inventing a new schema field.
    """
    if mrv_status == 'verified':
        raise VerificationNotAllowedHereError(
            "mrv_status='verified' cannot be set from the monitoring form. Independent verification "
            "is recorded only through the existing VerifiedCapitalOutcome admin change form."
        )
    if loss_avoided_actual is None or capex_actual is None:
        raise ValueError('loss_avoided_actual and capex_actual are required to record an outcome.')

    outcome = record_verified_outcome(
        decision, decision.intervention,
        loss_avoided_actual=loss_avoided_actual, capex_actual=capex_actual, opex_actual=opex_actual,
        savings_actual=savings_actual, mrv_status=mrv_status, evidence_quality=evidence_quality,
        public_reporting_ready=False,
    )
    if reviewer_note:
        stamp = f'[Reviewer note] {reviewer_note.strip()}'
        outcome.next_capital_allocation_signal = (
            f'{outcome.next_capital_allocation_signal}\n{stamp}'.strip()
            if outcome.next_capital_allocation_signal else stamp
        )
        outcome.save(update_fields=['next_capital_allocation_signal'])
    return outcome
