"""
companies/confidence.py — how much to trust the evidence we do hold.

D5. Confidence is NOT coverage, and conflating them is the mistake this module
exists to prevent.

    COVERAGE   how much of what the assessment needs is supported at all
    CONFIDENCE how good that support is

A company can have 100% coverage built entirely on unverified press releases
from 2019 — complete, and weak. Another can have 40% coverage from two
independently verified audits — incomplete, and strong. A single number cannot
say both, and averaging them would produce a figure that is true of neither.

NO INVENTED PRECISION
---------------------
This returns one of four labels, not a percentage. The inputs are categorical —
a review tier, a verification state, an origin — and combining categories into
"0.72 confidence" would manufacture a precision the underlying data cannot
support. That is the same fabrication the programme has spent eleven phases
removing, and it would be no better for arriving through arithmetic.

The vocabulary is decision_studio.DecisionQuery's, deliberately: HIGH /
MEDIUM / LOW / INSUFFICIENT_EVIDENCE. Two layers that answer the same question
should not need a translation table between them.

WHAT IS NOT HERE
----------------
Contradiction detection. EvidenceMemory has no contradiction field today, and
inferring disagreement from text would be a research problem wearing a
confidence label. The hook is documented at `_contradiction_penalty` and is a
no-op until something real records it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from companies.evidence import (
    PROVENANCE_ESTIMATED, PROVENANCE_INFERRED, PROVENANCE_MEASURED,
    _weight_by_field, coverage_for,
)

CONFIDENCE_HIGH = 'HIGH'
CONFIDENCE_MEDIUM = 'MEDIUM'
CONFIDENCE_LOW = 'LOW'
CONFIDENCE_INSUFFICIENT = 'INSUFFICIENT_EVIDENCE'

#: Ordered weakest-to-strongest, so a caller can compare two assessments
#: without hard-coding the order.
CONFIDENCE_ORDER = (CONFIDENCE_INSUFFICIENT, CONFIDENCE_LOW,
                    CONFIDENCE_MEDIUM, CONFIDENCE_HIGH)

#: How directly an origin ties a value to a source. MEASURED is a reading;
#: INFERRED is EcoIQ's assessment derived from one; ESTIMATED is an assumption
#: someone stated. All three count as evidence for coverage; they do not carry
#: equal weight for confidence.
_ORIGIN_STRENGTH = {
    PROVENANCE_MEASURED: 3,
    PROVENANCE_INFERRED: 2,
    PROVENANCE_ESTIMATED: 1,
}

#: Review tiers from evidence_memory that count as independent corroboration.
#: 'uploaded' and 'system_checked' do not: a file being present, or passing an
#: automated check, is not a person having verified it.
_CORROBORATING_TIERS = frozenset({'human_reviewed', 'independently_verified'})


@dataclass
class ConfidenceReport:
    """
    A confidence label and the reasons behind it.

    `reasons` is not decoration. A label with no stated basis is an assertion,
    and the whole point of this programme is that assertions carry their
    grounds with them.
    """
    label: str = CONFIDENCE_INSUFFICIENT
    reasons: list = field(default_factory=list)
    #: Counts that produced the label, for a surface that wants to show its work.
    evidenced_rows: int = 0
    measured_rows: int = 0
    reviewed_rows: int = 0
    verified_sources: int = 0
    stale_sources: int = 0

    def __str__(self) -> str:
        return self.label

    @property
    def is_publishable_quality(self) -> bool:
        """
        MEDIUM or better. Advisory — the publication gate decides, not this.
        """
        return CONFIDENCE_ORDER.index(self.label) >= CONFIDENCE_ORDER.index(
            CONFIDENCE_MEDIUM)


def _contradiction_penalty(profile) -> int:
    """
    Reserved. Nothing records contradictions between sources today.

    EvidenceMemory has verification_status and review_tier but no field saying
    "this source disagrees with that one", and deriving disagreement from text
    would be a research problem dressed as a confidence signal. Returns 0 until
    something real records it, and is called anyway so the wiring exists and
    the gap is visible rather than forgotten.
    """
    return 0


def confidence_for(profile) -> ConfidenceReport:
    """
    Confidence in the evidence behind one profile's assessment.

    Independent of coverage. The only thing coverage decides here is whether
    the question is answerable at all: with nothing evidenced there is no
    evidence to be confident about, and the answer is INSUFFICIENT_EVIDENCE
    rather than LOW. "We looked and it is weak" and "we have not looked" are
    different statements.
    """
    from companies import provenance as prov

    report = ConfidenceReport()
    if profile is None:
        report.reasons.append('No profile.')
        return report

    coverage = coverage_for(profile)
    if coverage.covered_inputs <= 0:
        report.reasons.append(
            'No material input has evidenced provenance, so there is no '
            'evidence to assess the quality of.')
        return report

    material_keys = set(_weight_by_field())
    rows = [row for key, row in prov.current_map(profile).items()
            if key in material_keys and row.origin in _ORIGIN_STRENGTH]

    report.evidenced_rows = len(rows)
    report.measured_rows = sum(
        1 for r in rows if r.origin == PROVENANCE_MEASURED)
    report.reviewed_rows = sum(
        1 for r in rows if r.review_status == 'confirmed')

    evidence_rows = [r for r in rows if r.evidence_id is not None]
    for row in evidence_rows:
        memory = row.evidence
        if memory is None:
            continue
        if (getattr(memory, 'verification_status', '') == 'verified'
                or getattr(memory, 'review_tier', '') in _CORROBORATING_TIERS):
            report.verified_sources += 1
        if getattr(memory, 'is_expired', False):
            report.stale_sources += 1

    # ── Grading ──────────────────────────────────────────────────────────────
    #
    # Deliberately coarse. Three ordered bands over categorical inputs, each
    # requiring something a person can point at, rather than a weighted sum
    # whose threshold nobody could defend.
    measured_share = report.measured_rows / len(rows)
    reviewed_share = report.reviewed_rows / len(rows)

    if report.stale_sources:
        report.reasons.append(
            f'{report.stale_sources} linked source(s) are past their expiry '
            'date.')

    if report.reviewed_rows and measured_share >= 0.5:
        report.label = CONFIDENCE_HIGH
        report.reasons.append(
            f'{report.measured_rows} of {len(rows)} evidenced inputs are '
            'MEASURED, and a reviewer has confirmed at least one.')
    elif measured_share >= 0.5 or report.verified_sources:
        report.label = CONFIDENCE_MEDIUM
        report.reasons.append(
            'Evidence is mostly direct, but no reviewer has confirmed it.'
            if measured_share >= 0.5 else
            f'{report.verified_sources} linked source(s) are independently '
            'verified.')
    else:
        report.label = CONFIDENCE_LOW
        report.reasons.append(
            'Evidence is mostly inferred or estimated, with no verified '
            'source and no reviewer confirmation.')

    # Staleness and contradiction can only ever LOWER a label, never raise one.
    if report.stale_sources and report.label == CONFIDENCE_HIGH:
        report.label = CONFIDENCE_MEDIUM
        report.reasons.append('Downgraded: some supporting sources are stale.')

    penalty = _contradiction_penalty(profile)
    if penalty:                                   # pragma: no cover - reserved
        index = max(0, CONFIDENCE_ORDER.index(report.label) - penalty)
        report.label = CONFIDENCE_ORDER[index]

    if reviewed_share == 0 and report.label == CONFIDENCE_HIGH:  # pragma: no cover
        report.label = CONFIDENCE_MEDIUM

    return report
