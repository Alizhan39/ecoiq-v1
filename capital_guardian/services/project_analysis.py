"""
capital_guardian/services/project_analysis.py — vertical-slice PR 2: turns a
GoldProject's real project-scoped evidence into a Mizan project analysis.

Uses the existing mizan.project.score_project() directly — this module is
an ADAPTER (GoldProject + real EvidenceMemory rows -> mizan.project.
ProjectInput) plus a small structured result wrapper. It is not a second
scoring engine and does not duplicate any of score_project()'s logic.

Honesty rules enforced here:
- Every ProjectInput field is either a direct, real GoldProject field, or
  is left at the dataclass's own conservative default — never guessed from
  free-text evidence content. The one exception (environmental_assessment)
  only flips to True when a real, non-demo, VERIFIED technical_report
  EvidenceMemory row exists for this project; pending/estimated/demo
  evidence never counts (see _has_real_verified_technical_report below).
- mizan.project.score_project()'s own `confidence` field is always
  'model-estimate' by construction (see mizan/project.py:249) — it reflects
  how many ProjectInput declarations were made, not real EvidenceMemory
  verification status. This module computes its OWN, separate evidence-
  quality summary from the real EvidenceMemory rows and never conflates
  the two, or upgrades one using the other.
- Public-facing language only: 'Mizan', 'ethical balance', 'stewardship',
  'harm reduction', 'justice', 'transparency', 'evidence confidence' (see
  mizan/scoring.py's own docstring, which explicitly forbids exposing its
  internal Maqasid mapping in any output). This module and everything that
  renders its output must never use Quranic/Shariah-ruling/Maqasid terms —
  mizan/project.py's islamic_finance_fit output already enforces the same
  rule for itself (explicit "not a Shariah ruling" disclaimers throughout).

Real dimensions score_project() actually produces (nothing is invented here
that isn't one of these): public_benefit_score, harm_reduction_score,
justice_distribution_score, transparency_accountability_score,
stewardship_score, evidence_confidence_score, final_mizan_score. There is
no separate "readiness", "impact", or "risk" score — those concepts map
loosely onto the above (public_benefit/stewardship are impact-adjacent,
harm_reduction is risk-adjacent) but are not computed as distinct fields,
and this module does not invent a new weighted combination to produce one.
"""
from dataclasses import dataclass, field
from typing import Optional

from django.utils import timezone

from capital_guardian.services.evidence import evidence_for_project
from mizan.project import ProjectInput, score_project

# ProjectInput fields this adapter does not attempt to derive from evidence
# today — left at the dataclass's own conservative defaults. Listed here so
# callers can render this as an explicit, honest limitation rather than
# silently presenting a full-looking input.
_FIELDS_NOT_DERIVED_FROM_EVIDENCE = (
    'duration_years', 'direct_jobs', 'local_procurement_pct',
    'renewable_energy_share', 'governance_framework',
    'gender_inclusion_plan', 'climate_risk_disclosure', 'community_benefit',
)


def _has_real_verified_technical_report(evidence_list):
    """
    True only when a real (non-demo), independently VERIFIED
    technical_report row exists — never for pending/estimated/rejected/
    requires_review/demo evidence. This is the one place evidence is
    allowed to flip a ProjectInput declaration, and only because
    document_category='technical_report' is a real, structurally-specific
    EvidenceMemory field (not a free-text guess).
    """
    return any(
        e.document_category == 'technical_report' and e.verification_status == 'verified' and not e.is_demo
        for e in evidence_list
    )


@dataclass
class ProjectInputBuildMeta:
    evidence_references: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    missing_project_fields: list = field(default_factory=list)
    fields_not_evidence_derived: tuple = _FIELDS_NOT_DERIVED_FROM_EVIDENCE
    has_real_verified_technical_report: bool = False


def build_project_input_from_evidence(project):
    """
    Returns (ProjectInput, ProjectInputBuildMeta).

    Never fabricates a value: a null/missing real GoldProject field is
    reported in `missing_project_fields` and left at ProjectInput's own
    default rather than backfilled with a plausible-looking number.
    """
    evidence_list = list(evidence_for_project(project))

    warnings = []
    missing_project_fields = []

    sector = project.commodity or 'other'

    country_name = ''
    if project.country_id:
        country_name = project.country.name
    else:
        warnings.append('Project has no linked country — country-level governance context cannot be applied.')

    budget_usd = project.total_capex_usd
    if budget_usd is None:
        missing_project_fields.append('total_capex_usd')

    if not evidence_list:
        warnings.append('No project-scoped evidence exists yet — analysis is based on declared project fields only.')

    has_real_eia = _has_real_verified_technical_report(evidence_list)

    project_input = ProjectInput(
        name=project.name,
        sector=sector,
        country=country_name,
        description=project.description or '',
        budget_usd=budget_usd,
        environmental_assessment=has_real_eia,
    )

    meta = ProjectInputBuildMeta(
        evidence_references=[e.source_reference for e in evidence_list],
        warnings=warnings,
        missing_project_fields=missing_project_fields,
        has_real_verified_technical_report=has_real_eia,
    )
    return project_input, meta


@dataclass
class ProjectAnalysisResult:
    """
    Structured wrapper around one real score_project() run. Every field
    here traces back either to the real GoldProject/EvidenceMemory rows
    (via build_project_input_from_evidence) or to score_project()'s own
    real output — nothing is computed by this class itself beyond simple
    counting/labelling.
    """
    project_name: str
    project_slug: str
    analysed_at: object

    evidence_count: int
    verified_evidence_count: int
    pending_evidence_count: int
    rejected_or_expired_evidence_count: int
    demo_evidence_count: int
    evidence_quality_summary: str

    # The six real dimensions + aggregate, taken directly from MizanResult.
    public_benefit_score: float
    harm_reduction_score: float
    justice_distribution_score: float
    transparency_accountability_score: float
    stewardship_score: float
    evidence_confidence_score: float
    final_mizan_score: float
    mizan_label: str

    risk_flags: list
    recommended_next_actions: list
    methodology: str
    scorer_confidence: str  # score_project()'s own always-'model-estimate' field — kept separate from evidence_quality_summary above

    missing_project_fields: list
    fields_not_evidence_derived: tuple
    warnings: list
    evidence_references: list

    limitations: list = field(default_factory=list)


def analyse_project(project):
    """
    The one real entry point for vertical-slice PR 2: builds a ProjectInput
    from the project's real data + real evidence, runs the existing
    mizan.project.score_project() unmodified, and returns a
    ProjectAnalysisResult describing both the score and exactly what
    evidence did (and did not) support it.
    """
    project_input, build_meta = build_project_input_from_evidence(project)
    result = score_project(project_input)

    evidence_list = list(evidence_for_project(project))
    verified = sum(1 for e in evidence_list if e.verification_status == 'verified')
    pending = sum(1 for e in evidence_list if e.verification_status == 'pending')
    rejected_or_expired = sum(1 for e in evidence_list if e.verification_status in ('rejected', 'expired'))
    demo = sum(1 for e in evidence_list if e.is_demo)

    if evidence_list:
        quality_summary = (
            f'{verified} of {len(evidence_list)} evidence record(s) verified, '
            f'{pending} pending, {demo} illustrative/demo.'
        )
    else:
        quality_summary = 'No evidence recorded for this project yet.'

    limitations = [
        'This analysis reuses the existing mizan.project.score_project() rule-based scorer — '
        'it is not a live AI call and does not train or update any model.',
        "score_project()'s own confidence field is always 'model-estimate' by design — it reflects "
        'how many declared inputs were provided, not the verification status of real evidence.',
        'Most ProjectInput fields (' + ', '.join(build_meta.fields_not_evidence_derived) + ') are not yet '
        'derived from evidence content — they remain at conservative defaults until a future PR adds '
        'a reviewed way to derive them without guessing from free text.',
        "The evidence intake form (PR 1) accepts a real/estimated/illustrative classification, but only "
        "'illustrative' (is_demo) is currently a distinct stored field — 'estimated' evidence is not yet "
        'separately trackable from real, unreviewed (pending) evidence.',
        'Mizan scoring is indicative project-readiness/ethical-balance scoring, not a religious ruling, '
        'Shariah determination, or certification of any kind.',
    ]
    if build_meta.warnings:
        limitations.extend(build_meta.warnings)
    if build_meta.missing_project_fields:
        limitations.append(
            'Missing real project fields (left at conservative defaults): ' + ', '.join(build_meta.missing_project_fields)
        )

    return ProjectAnalysisResult(
        project_name=project.name,
        project_slug=project.slug,
        analysed_at=timezone.now(),
        evidence_count=len(evidence_list),
        verified_evidence_count=verified,
        pending_evidence_count=pending,
        rejected_or_expired_evidence_count=rejected_or_expired,
        demo_evidence_count=demo,
        evidence_quality_summary=quality_summary,
        public_benefit_score=result.public_benefit_score,
        harm_reduction_score=result.harm_reduction_score,
        justice_distribution_score=result.justice_distribution_score,
        transparency_accountability_score=result.transparency_accountability_score,
        stewardship_score=result.stewardship_score,
        evidence_confidence_score=result.evidence_confidence_score,
        final_mizan_score=result.final_mizan_score,
        mizan_label=result.mizan_label,
        risk_flags=result.risk_flags,
        recommended_next_actions=result.recommended_next_actions,
        methodology=result.methodology,
        scorer_confidence=result.confidence,
        missing_project_fields=build_meta.missing_project_fields,
        fields_not_evidence_derived=build_meta.fields_not_evidence_derived,
        warnings=build_meta.warnings,
        evidence_references=build_meta.evidence_references,
        limitations=limitations,
    )
