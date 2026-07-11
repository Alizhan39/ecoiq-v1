"""
capital_guardian/services/resource_purpose_review.py — vertical-slice PR 3:
the first "is this resource being used for the most reasonable, beneficial,
safe, and responsible purpose?" review, and the human-reviewed bridge from
a ProjectAnalysisResult into a real Waste-to-Value OperationalLoss.

Deterministic, structured-data-only, no live AI:
- Resource identity (primary_resource/current_use/intended_service) and the
  alternative-pathway/safety-constraint content below come from a small,
  explicit, hand-reviewed profile table keyed on the project's own `slug`
  (a controlled, declared identifier — never a keyword/NLP guess over
  free-text evidence content). Projects with no reviewed profile get an
  honest "not yet reviewed" fallback rather than a fabricated one.
- Every evidence-derived field (evidence_used, evidence_gaps,
  review_confidence) comes from real EvidenceMemory rows via the same
  capital_guardian.services.evidence.evidence_for_project() already used by
  PR 1/PR 2 — never fabricated, never upgraded past what verification_status
  actually says.
- The six stewardship questions (Amanah, Mizan, Adl, Israf, Prevention of
  Harm, Maslaha, Hisab) are presented as REVIEW QUESTIONS with no attached
  score and no halal/haram calculation — never a ruling, never framed as
  "Quranically approved". This module does not expose mizan/scoring.py's
  internal Maqasid-to-dimension mapping (see that module's own docstring:
  "Do NOT expose Maqasid terminology in any output field") — these are a
  separate, explicitly-labelled, non-scored reflection layer, not a
  restatement of that internal mapping.
"""
from dataclasses import dataclass, field
from typing import Optional

from capital_guardian.services.evidence import evidence_for_project

STEWARDSHIP_DISCLAIMER = (
    'These are stewardship review questions for human decision-makers — not a religious ruling, '
    'Shariah determination, fatwa, or certification of any kind. Qualified scholars are required for '
    'religious rulings; qualified engineers, scientists, regulators, and other domain experts are '
    'required for technical and safety decisions.'
)

STEWARDSHIP_QUESTIONS = [
    {
        'name': 'Amanah',
        'question': 'Is the resource being managed responsibly, as something held in trust rather than owned outright?',
    },
    {
        'name': 'Mizan',
        'question': 'Are the benefits, harms, costs, and risks of the current use being measured and weighed fairly against the alternatives?',
    },
    {
        'name': 'Adl',
        'question': 'Who receives the benefit of the current use, and who carries the harm or cost?',
    },
    {
        'name': 'Israf',
        'question': 'Is useful value being wasted or destroyed unnecessarily by the current use?',
    },
    {
        'name': 'Prevention of Harm',
        'question': 'Could the current or a proposed use harm people, air, soil, water, ecosystems, or future generations?',
    },
    {
        'name': 'Maslaha',
        'question': 'Does the option under review create durable public benefit, or only a narrow or short-term one?',
    },
    {
        'name': 'Hisab',
        'question': 'Can the decision and its outcome actually be measured and accounted for, so it can be reviewed later?',
    },
]

# One reviewed profile for the known clean-heating pilot. Keyed on slug (a
# controlled identifier), not on any free-text guess. Extend this table only
# by adding a new, explicitly reviewed entry — never by pattern-matching
# evidence text.
_RESOURCE_PROFILES = {
    'almaty-clean-heating-pilot-200-homes': {
        'primary_resource': 'Coal',
        'current_use': 'Household space heating (individual coal stoves)',
        'intended_service': 'Safe and affordable warmth for the household',
        'necessity_of_current_use': (
            'Space heating itself is a genuine, necessary human need in this climate. The reviewable '
            'question is not whether heating is needed, but whether coal combustion is the most '
            'reasonable, safe, and beneficial way to deliver it, or whether demand reduction and a '
            'cleaner pathway would serve the same need with less harm.'
        ),
        'lifecycle_concerns': (
            'Household coal combustion is associated with indoor and ambient air pollution, ash '
            'disposal, and ongoing fuel-supply cost exposure. A full lifecycle comparison against '
            'alternatives has not been carried out for this pilot.'
        ),
        'alternative_pathways': [
            {'name': 'Insulation and demand reduction', 'status': 'open',
             'notes': 'Reduces the amount of heat (and therefore fuel of any kind) required — a reasonable first step regardless of which heating technology is ultimately used.'},
            {'name': 'Heat pumps', 'status': 'open',
             'notes': 'A credible substitute for coal-based heating where grid capacity and household budgets allow; requires a real feasibility and cost assessment for this pilot before recommending it.'},
            {'name': 'District heating connection', 'status': 'open',
             'notes': 'Viable where existing district heating infrastructure can be extended to these homes; requires confirmation of actual network proximity and capacity.'},
            {'name': 'Electric heating', 'status': 'open',
             'notes': 'Depends on real local grid capacity and electricity cost/emissions profile, which have not been evidenced for this pilot yet.'},
            {'name': 'Renewable integration / grid improvement', 'status': 'open',
             'notes': 'A longer-term pathway that would need real feasibility and investment review.'},
            {'name': 'Hybrid systems', 'status': 'open',
             'notes': 'Combining insulation with a partial electrification/renewable pathway; requires the same feasibility review as the individual pathways above.'},
            {'name': 'Safe non-combustion applications of coal', 'status': 'conditional',
             'notes': 'Only where specific technical and environmental review supports a specific processed product and use case — not assumed safe by default.'},
            {'name': 'Raw coal as fertiliser', 'status': 'blocked',
             'notes': 'Blocked: raw coal is not a fertiliser. Never recommended unless a specific processed product were scientifically validated for a specific agronomic use — no such validation exists here.'},
            {'name': 'Coal ash in construction materials', 'status': 'conditional',
             'notes': 'Conditional on chemical characterisation, heavy-metal testing, leaching testing, compliance with applicable technical standards, a lifecycle assessment, and regulatory approval. Not assumed safe, and never a reason to burn more coal in order to produce ash.'},
            {'name': 'Agricultural reuse of combustion by-products', 'status': 'conditional',
             'notes': 'Conditional on agronomic and toxicity review by qualified specialists. No blanket claim of safety.'},
            {'name': 'Reuse of other industrial by-products', 'status': 'conditional',
             'notes': 'Conditional on provenance, composition, safety, logistics, and legal status review — never assumed to be a usable product by default.'},
        ],
        'expected_evidence_categories': ['technical_report', 'inspection_report'],
    },
}

_FALLBACK_PROFILE = {
    'primary_resource': None,
    'current_use': None,
    'intended_service': None,
    'necessity_of_current_use': 'No reviewed resource-purpose profile exists yet for this project — nothing is assumed.',
    'lifecycle_concerns': '',
    'alternative_pathways': [],
    'expected_evidence_categories': [],
}


@dataclass
class ResourcePurposeReviewResult:
    project_name: str
    project_slug: str
    has_reviewed_profile: bool

    primary_resource: Optional[str]
    current_use: Optional[str]
    intended_service: Optional[str]
    necessity_of_current_use: str
    avoidability: str
    lifecycle_concerns: str

    alternative_pathways: list = field(default_factory=list)
    safety_constraints: list = field(default_factory=list)

    evidence_used: list = field(default_factory=list)
    evidence_gaps: list = field(default_factory=list)
    review_confidence: str = 'low'

    misuse_or_value_loss_condition_exists: bool = False
    recommended_next_action: str = ''

    stewardship_questions: list = field(default_factory=list)
    stewardship_disclaimer: str = STEWARDSHIP_DISCLAIMER


def _avoidability_from_score(harm_reduction_score):
    """
    Reuses PR 2's real, already-computed harm_reduction_score — never a new
    calculation. A low score means the sector/renewable-share inputs
    currently on record indicate high harm relative to what's achievable,
    which is itself a signal (not proof) that an avoidable pathway may exist.
    """
    if harm_reduction_score is None:
        return 'Unknown — no analysis score available.'
    if harm_reduction_score < 40:
        return 'High — current declared inputs indicate significant, potentially avoidable harm.'
    if harm_reduction_score < 70:
        return 'Moderate — some avoidable harm indicated; a full review is still warranted.'
    return 'Lower — current declared inputs do not indicate high avoidable harm, but this is not independently verified.'


def _review_confidence(evidence_list):
    if not evidence_list:
        return 'low'
    verified = [e for e in evidence_list if e.verification_status == 'verified' and not e.is_demo]
    if not verified:
        return 'low'
    if len(verified) < len(evidence_list):
        return 'medium'
    return 'medium' if len(verified) < 3 else 'high'


def review_resource_purpose(project, analysis_result):
    """
    project: a gold_intelligence.models.GoldProject.
    analysis_result: the real capital_guardian.services.project_analysis.
    ProjectAnalysisResult already computed for this project (PR 2) — its
    harm_reduction_score is reused directly, never recomputed here.
    """
    profile = _RESOURCE_PROFILES.get(project.slug, _FALLBACK_PROFILE)
    has_reviewed_profile = project.slug in _RESOURCE_PROFILES

    evidence_list = list(evidence_for_project(project))
    evidence_used = [e.source_reference for e in evidence_list]

    evidence_gaps = []
    present_categories = {e.document_category for e in evidence_list if e.verification_status == 'verified' and not e.is_demo}
    for expected in profile.get('expected_evidence_categories', []):
        if expected not in present_categories:
            evidence_gaps.append(f'No real, verified {expected.replace("_", " ")} evidence found for this project.')
    if not evidence_list:
        evidence_gaps.append('No project-scoped evidence exists yet.')

    review_confidence = _review_confidence(evidence_list)
    avoidability = _avoidability_from_score(getattr(analysis_result, 'harm_reduction_score', None))

    # A reviewed profile existing at all IS the human judgement that this
    # resource-use pattern is worth stewardship review (that's why someone
    # authored the profile) — the harm_reduction_score above adds narrative
    # context (how avoidable current declared inputs suggest it is) but does
    # not gate whether the concern is shown at all. A project with no
    # reviewed profile never shows a misuse condition, since nothing has
    # actually been reviewed for it yet.
    misuse_condition_exists = has_reviewed_profile

    if not has_reviewed_profile:
        recommended_next_action = (
            'No reviewed resource-purpose profile exists for this project yet — a domain expert should '
            'author one before any value-loss condition can be assessed.'
        )
    elif misuse_condition_exists and review_confidence == 'low':
        recommended_next_action = (
            'A potential resource-misuse / value-loss condition is indicated by the reviewed profile, but '
            'evidence confidence is currently low — gather real, verified evidence (technical/engineering '
            'review, energy/cost data) before or alongside human confirmation of any value-loss record.'
        )
    elif misuse_condition_exists:
        recommended_next_action = (
            'A potential resource-misuse / value-loss condition is indicated. A qualified reviewer should '
            'confirm the finding and, if confirmed, a human reviewer may create a value-loss record for '
            'further capital-allocation consideration.'
        )
    else:
        recommended_next_action = (
            'No clear misuse/value-loss condition is indicated by the current evidence and analysis. '
            'Continue gathering evidence before revisiting.'
        )

    return ResourcePurposeReviewResult(
        project_name=project.name,
        project_slug=project.slug,
        has_reviewed_profile=has_reviewed_profile,
        primary_resource=profile['primary_resource'],
        current_use=profile['current_use'],
        intended_service=profile['intended_service'],
        necessity_of_current_use=profile['necessity_of_current_use'],
        avoidability=avoidability,
        lifecycle_concerns=profile['lifecycle_concerns'],
        alternative_pathways=profile['alternative_pathways'],
        safety_constraints=[
            f"{p['name']}: {p['notes']}" for p in profile['alternative_pathways'] if p['status'] in ('conditional', 'blocked')
        ],
        evidence_used=evidence_used,
        evidence_gaps=evidence_gaps,
        review_confidence=review_confidence,
        misuse_or_value_loss_condition_exists=misuse_condition_exists,
        recommended_next_action=recommended_next_action,
        stewardship_questions=STEWARDSHIP_QUESTIONS,
    )
