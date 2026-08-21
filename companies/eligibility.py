"""
companies/eligibility.py — the one place that decides whether a score is published.

D5. Four inputs, one answer:

    1. provenance defensibility  can we stand behind the lineage we recorded?
    2. evidence coverage         did we record enough of it?
    3. confidence                how good is what we recorded?
    4. the score itself          is there a number at all?

ONE SERVICE, NOT A RULE REPEATED IN TEMPLATES
---------------------------------------------
The company detail page renders the composite in seventeen places. Gating each
one would be seventeen chances to miss one, and a number left in JSON-LD is
still published even when the visible one is hidden. So the decision is made
here, once, and every surface asks.

THE THRESHOLD, AND WHY IT IS WHERE IT IS
----------------------------------------
The brief asked for candidate thresholds (20/40/60/80%) simulated against the
real dataset before choosing. That simulation was run. Its result:

    467 of 467 production companies sit at 0% coverage.

Every company in the estate carries LEGACY_UNKNOWN_PROVENANCE from the D3B
backfill, and no ingestion or analyst write has run against production. So
every candidate threshold produces exactly the same answer -- 0 eligible, 0
provisional, 467 unavailable -- and the distribution contains no information to
choose between them.

Picking 40% over 60% on that basis would be inventing a justification. So the
rule is deliberately the most conservative one available, and the reason is
recorded rather than the number being presented as considered:

    PUBLISHED requires FULL coverage.

Tightening a threshold later is a policy change. Publishing something that
should not have been published is not recoverable, and an evidence-integrity
system gets exactly one reputation. When real coverage exists in production the
distribution will mean something, and THAT is the moment to choose a threshold
with evidence behind it.

PROVISIONAL is defined and reachable, but no coverage level currently maps to
it. It is not dead: the state exists so the surfaces, the API contract and the
tests are all built for a three-state world before the threshold that produces
the third state is chosen. Adding a state later is a schema and contract
change; leaving room for one is free.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from companies.confidence import (
    CONFIDENCE_INSUFFICIENT, ConfidenceReport, confidence_for,
)
from companies.evidence import (
    AVAILABILITY_AVAILABLE, CoverageReport, coverage_for,
)

#: Sentinel for "the caller did not supply a score".
#:
#: `score=None` cannot mean that, because None is a VALID and meaningful value
#: here -- it is precisely how "this score is unknown" is expressed everywhere
#: else in the system. Using None as the not-supplied marker made
#: decide_for_company() fall back to the PROFILE composite whenever a
#: league.Company had no score of its own, publishing one number under
#: another's name.
_NOT_SUPPLIED = object()

STATUS_PUBLISHED = 'PUBLISHED'
STATUS_PROVISIONAL = 'PROVISIONAL'
STATUS_INSUFFICIENT = 'INSUFFICIENT_EVIDENCE'

#: Coverage required to publish, as a ratio. See the module docstring for why
#: this is 1.0 and not one of the candidate thresholds.
PUBLISH_COVERAGE = 1.0

#: Coverage that would qualify as PROVISIONAL. Set equal to PUBLISH_COVERAGE so
#: nothing currently lands in the provisional band -- a deliberate no-op, not an
#: oversight. Lowering PUBLISH_COVERAGE below this is the single edit that turns
#: the third state on.
PROVISIONAL_COVERAGE = 1.0


@dataclass
class EligibilityDecision:
    """
    Whether a score may be published, and everything the answer rested on.

    Carries the coverage and confidence reports rather than just their
    summaries, so a caller never has to recompute them to explain the verdict —
    and so the verdict and its stated grounds cannot drift apart.
    """
    status: str = STATUS_INSUFFICIENT
    score: float | None = None
    coverage: CoverageReport = field(default_factory=CoverageReport)
    confidence: ConfidenceReport = field(default_factory=ConfidenceReport)
    reasons: list = field(default_factory=list)

    @property
    def is_published(self) -> bool:
        return self.status == STATUS_PUBLISHED

    @property
    def public_score(self) -> float | None:
        """
        The score a public surface may show, or None.

        The only correct way to read a score off this object. Reading `.score`
        directly would hand out the number regardless of the verdict.
        """
        return self.score if self.is_published else None

    @property
    def coverage_percent(self) -> int:
        return self.coverage.coverage_percent

    @property
    def confidence_label(self) -> str:
        return self.confidence.label

    def __bool__(self) -> bool:
        return self.is_published


def decide(profile, score=_NOT_SUPPLIED) -> EligibilityDecision:
    """
    The canonical publication decision for one profile's composite score.

    `score` defaults to the profile's stored composite; callers gating a
    different number (the league table reads league.Company.ecoiq_score, a
    separate field derived from the same inputs) pass it explicitly.

    Fails closed at every step: a missing profile, a missing score, no
    coverage, or insufficient confidence all produce INSUFFICIENT_EVIDENCE.
    """
    decision = EligibilityDecision()
    if profile is None:
        decision.reasons.append('No profile, so no evidence by definition.')
        return decision

    decision.coverage = coverage_for(profile)
    decision.confidence = confidence_for(profile)
    decision.score = (getattr(profile, 'ecoiq_total_score', None)
                      if score is _NOT_SUPPLIED else score)

    if decision.score is None:
        decision.reasons.append(
            'No composite score has been computed for this organisation.')
        return decision

    if decision.coverage.covered_inputs <= 0:
        decision.reasons.append(
            'No material input has evidenced provenance. Seeded and legacy '
            'values can never satisfy public evidence eligibility.')
        _note_unevidenced(decision)
        return decision

    if decision.confidence.label == CONFIDENCE_INSUFFICIENT:
        decision.reasons.append(
            'Evidence quality could not be assessed.')
        return decision

    # Coverage is the deciding threshold. Confidence has already had its say
    # above by ruling out the unassessable case; it does not get a second vote,
    # because a high-confidence assessment of a quarter of the inputs is still
    # an assessment of a quarter of the inputs.
    if decision.coverage.coverage >= PUBLISH_COVERAGE:
        decision.status = STATUS_PUBLISHED
        decision.reasons.append(
            f'All {decision.coverage.denominator} material inputs are '
            f'supported by evidenced provenance; confidence '
            f'{decision.confidence.label}.')
    elif decision.coverage.coverage >= PROVISIONAL_COVERAGE:  # pragma: no cover
        decision.status = STATUS_PROVISIONAL
        decision.reasons.append(
            f'Partial evidence: {decision.coverage.numerator} of '
            f'{decision.coverage.denominator} material inputs supported.')
    else:
        decision.reasons.append(
            f'Only {decision.coverage.numerator} of '
            f'{decision.coverage.denominator} material inputs are supported by '
            f'evidenced provenance ({decision.coverage.coverage_percent}%).')

    _note_unevidenced(decision)
    return decision


def _note_unevidenced(decision) -> None:
    """
    Say how many inputs hold a value we cannot use.

    Reported on every path, including the early returns. "We hold nothing" and
    "we hold sixteen numbers we cannot stand behind" are different situations
    needing different work, and a caller told only the first would go looking
    for data that is already there.
    """
    if decision.coverage.unevidenced:
        decision.reasons.append(
            f'{len(decision.coverage.unevidenced)} input(s) hold a value with '
            'seeded or legacy provenance, which does not count as evidence.')


def decide_for_company(company) -> EligibilityDecision:
    """
    Same decision for a league.Company.

    The league table renders `Company.ecoiq_score`, a different field from
    `CompanyProfile.ecoiq_total_score` but derived from the same inputs, so it
    is gated on the linked profile's evidence. A company with no profile has no
    evidence by definition.
    """
    profile = getattr(company, 'profile', None)
    # Passed explicitly, including when it is None: a company with no league
    # score of its own must NOT inherit the profile's composite. They are
    # different numbers over different inputs, and publishing one under the
    # other's name is exactly the substitution this system exists to prevent.
    return decide(profile, score=getattr(company, 'ecoiq_score', None))


def simulate_thresholds(profiles, candidates=(0.2, 0.4, 0.6, 0.8, 1.0)) -> dict:
    """
    How many profiles each candidate threshold would publish.

    Provided so the threshold decision can be re-taken against real data when
    production has some, rather than being argued from first principles a
    second time. Returns {threshold: {eligible, provisional, unavailable}}.
    """
    reports = [coverage_for(p) for p in profiles]
    results = {}
    for threshold in candidates:
        eligible = sum(1 for r in reports if r.coverage >= threshold)
        partial = sum(1 for r in reports
                      if 0 < r.coverage < threshold)
        results[threshold] = {
            'eligible': eligible,
            'provisional': partial,
            'unavailable': len(reports) - eligible - partial,
        }
    return results


def publishable_company_ids(companies) -> set:
    """
    The subset of `companies` whose scores may be shown publicly.

    Exists because charts need the SAME gate as tables, and the obvious
    implementation -- calling decide_for_company() in a loop -- is around two
    queries per company. On a 467-row leaderboard that is a thousand queries on
    a public page, which is why the charts ended up ungated in the first place:
    the correct check looked too expensive to run.

    So the expensive decision is bounded first. A company with no evidenced
    provenance row cannot be publishable under any threshold, and that question
    is answerable in ONE query against the provenance table.

    Returns league.Company primary keys.
    """
    from companies.evidence import EVIDENCED_MATERIAL_ORIGINS
    from companies.models import CompanyMetricProvenance, CompanyProfile

    companies = list(companies)
    if not companies:
        return set()

    company_ids = [c.pk for c in companies]

    # One query: which profiles hold any evidenced provenance at all?
    evidenced_profiles = set(
        CompanyMetricProvenance.objects
        .filter(is_current=True, origin__in=EVIDENCED_MATERIAL_ORIGINS)
        .values_list('company_id', flat=True)
        .distinct()
    )
    if not evidenced_profiles:
        return set()

    # One query: map those profiles back to the companies in scope.
    candidates = {
        profile.company_id: profile
        for profile in CompanyProfile.objects
        .filter(pk__in=evidenced_profiles, company_id__in=company_ids)
        .select_related('company')
    }
    if not candidates:
        return set()

    return {
        company.pk for company in companies
        if company.pk in candidates
        and decide(candidates[company.pk],
                   score=getattr(company, 'ecoiq_score', None)).is_published
    }
