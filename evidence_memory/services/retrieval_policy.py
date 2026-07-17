"""
evidence_memory/services/retrieval_policy.py — feat/evidence-memory-hardening:
the ONE place that decides whether a project (and the user acting on its
behalf) may retrieve an EvidenceMemory row, and how retrieved rows are
ranked and explained. Views never make their own access decisions about
evidence retrieval — they call this module.

ACCESS DECISIONS (is_record_accessible):
- restricted_unresolved      → never retrievable cross-project (its own
                               project link is by definition unknown, so it
                               is not retrievable same-project either).
- project_private            → only when the record's project IS the
                               requesting project.
- organisation_shared        → when both the record and the requesting
                               project declare the same non-blank
                               organisation (trimmed, case-insensitive).
                               Blank never matches blank — "no organisation"
                               is not an organisation.
- platform_learning_demo     → any project, but only if the record is
                               honestly demo (is_demo=True); always
                               labelled DEMO by the caller.
- platform_learning_verified → any project, but only if the record still
                               genuinely qualifies: independently verified,
                               verification_status='verified', not demo.
                               A record whose state has since degraded
                               (e.g. re-synced after a dispute) fails this
                               check even if its visibility field was never
                               downgraded — visibility grants at most what
                               the record's own state can honestly support.

Rejected records are excluded from retrieval entirely, in every scope —
a rejected outcome is never "relevant historical evidence".

USER GATE: retrieval is currently exposed only on staff-only pages
(run_project_analysis / Command Centre). is_record_accessible still takes
the user so the policy is enforced in one place when non-staff project
access arrives: anonymous/None users are refused outright, non-staff users
are refused (no non-staff project-membership model exists yet — see PR3
report's known limitations).

RANKING (rank_for_project): semantic similarity remains the base signal
(the same _rank_candidates engine used everywhere else — never a second
vector-search implementation). A transparent, additive quality weighting
then adjusts ordering, and every returned item carries a human-readable
`explanation` listing exactly the factors that ranked it — nothing hidden,
and never a claim of causal transferability.
"""
from dataclasses import dataclass, field
from typing import Optional

from django.utils import timezone

# Additive score bonuses — deliberately small relative to the 0..1 cosine
# similarity base so semantic relevance stays primary, and deliberately
# transparent: every non-zero factor below also appears in the explanation.
_WEIGHT_SAME_PROJECT = 0.15
_WEIGHT_VERIFIED_STATUS = 0.10
_WEIGHT_TIER = {'independently_verified': 0.08, 'human_reviewed': 0.05, 'system_checked': 0.02, 'uploaded': 0.0}
_WEIGHT_SAME_SECTOR = 0.05
_WEIGHT_SAME_COUNTRY = 0.04
_WEIGHT_RECENT = 0.03          # created within the last ~2 years
_PENALTY_DEMO = 0.05
_RECENT_DAYS = 730


@dataclass
class RetrievedEvidence:
    """One policy-approved, ranked retrieval result. `memory` is the real
    EvidenceMemory row; everything else is derived, explainable context —
    no field here is ever fabricated."""
    memory: object
    scope: str                    # 'same_project' | 'organisation_shared' | 'platform_learning'
    similarity: Optional[float]   # raw cosine similarity when available (SQLite path); None on the PG path
    similarity_band: str          # 'high' | 'moderate' | 'low' | 'unknown'
    quality_score: float          # the additive bonus applied on top of similarity
    explanation: str              # e.g. "Same sector · independently verified · high semantic similarity"
    is_disputed: bool
    factors: list = field(default_factory=list)


def _norm_org(value):
    return (value or '').strip().casefold()


def is_record_accessible(memory, project, user=None):
    """May `project` (viewed by `user`) use this EvidenceMemory record?
    Pure policy — no queries beyond the passed objects' own fields."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if not getattr(user, 'is_staff', False):
        # No non-staff project-membership model exists in this codebase yet;
        # until one does, non-staff users get nothing rather than everything.
        return False
    if project is None:
        return False
    if memory.verification_status == 'rejected':
        return False

    visibility = memory.visibility
    if visibility == 'restricted_unresolved':
        return False
    if visibility == 'project_private':
        return memory.project_id is not None and memory.project_id == project.pk
    if visibility == 'organisation_shared':
        if memory.project_id == project.pk:
            return True
        record_org = _norm_org(memory.organisation)
        project_org = _norm_org(getattr(project, 'organisation', ''))
        return bool(record_org) and record_org == project_org
    if visibility == 'platform_learning_demo':
        return bool(memory.is_demo)
    if visibility == 'platform_learning_verified':
        return (
            not memory.is_demo
            and memory.verification_status == 'verified'
            and memory.review_tier == 'independently_verified'
        )
    return False  # unknown visibility value — fail closed, never open


def _scope_for(memory, project):
    if memory.project_id is not None and memory.project_id == project.pk:
        return 'same_project'
    if memory.visibility == 'organisation_shared':
        return 'organisation_shared'
    return 'platform_learning'


def is_disputed(memory):
    """True when the originating outcome's own MRV state is 'disputed' —
    read from the structured provenance link, never inferred from the
    verification_status it happens to map to."""
    outcome = memory.originating_outcome
    return outcome is not None and outcome.mrv_status == 'disputed'


_SCOPE_LABEL = {
    'same_project': 'Same project',
    'organisation_shared': 'Organisation shared',
    'platform_learning': 'Platform learning evidence',
}
_TIER_LABEL = {
    'independently_verified': 'independently verified',
    'human_reviewed': 'human reviewed',
    'system_checked': 'system checked',
    'uploaded': 'uploaded only',
}
_BAND_LABEL = {
    'high': 'high semantic similarity',
    'moderate': 'moderate semantic similarity',
    'low': 'low semantic similarity',
    'unknown': 'semantic similarity match',
}


def _similarity_band(similarity):
    if similarity is None:
        return 'unknown'
    if similarity >= 0.55:
        return 'high'
    if similarity >= 0.3:
        return 'moderate'
    return 'low'


def score_and_explain(memory, project, similarity=None):
    """Builds the transparent quality weighting + explanation for one
    accessible record. Returns a RetrievedEvidence (without asserting
    accessibility — callers go through retrieve_for_project below, which
    checks the policy first)."""
    factors = []
    bonus = 0.0
    scope = _scope_for(memory, project)
    factors.append(_SCOPE_LABEL[scope])
    if scope == 'same_project':
        bonus += _WEIGHT_SAME_PROJECT

    record_project = memory.project
    if record_project is not None and memory.project_id != project.pk:
        if record_project.commodity and record_project.commodity == project.commodity:
            bonus += _WEIGHT_SAME_SECTOR
            factors.append('same sector')
        if record_project.country_id and record_project.country_id == project.country_id:
            bonus += _WEIGHT_SAME_COUNTRY
            factors.append('same country')

    if memory.verification_status == 'verified':
        bonus += _WEIGHT_VERIFIED_STATUS
    tier_bonus = _WEIGHT_TIER.get(memory.review_tier, 0.0)
    bonus += tier_bonus
    factors.append(_TIER_LABEL.get(memory.review_tier, memory.review_tier))

    disputed = is_disputed(memory)
    if disputed:
        factors.append('DISPUTED — under review')
    if memory.is_demo:
        bonus -= _PENALTY_DEMO
        factors.append('demo evidence')

    if memory.created_at and (timezone.now() - memory.created_at).days <= _RECENT_DAYS:
        bonus += _WEIGHT_RECENT

    band = _similarity_band(similarity)
    factors.append(_BAND_LABEL[band])

    return RetrievedEvidence(
        memory=memory, scope=scope, similarity=similarity, similarity_band=band,
        quality_score=round(bonus, 4), explanation=' · '.join(factors),
        is_disputed=disputed, factors=factors,
    )


def retrieve_for_project(project, user, query_text, *, limit=5):
    """
    The ONE cross-project retrieval path for outcome-derived learning
    evidence. Applies the access policy first (DB-side where expressible,
    then re-checked per-record in Python so a queryset mistake can never
    widen access), then semantic-ranks the accessible candidates, then
    applies the transparent quality weighting.

    Returns a list of RetrievedEvidence, best first. Never raises for an
    unauthorised user — returns [] (the caller shows an honest empty state).
    """
    from django.db.models import Q

    from evidence_memory.models import EvidenceMemory
    from evidence_memory.services.memory import OUTCOME_SOURCE_PREFIX, _rank_candidates, _similarities_for

    if user is None or not getattr(user, 'is_authenticated', False) or not getattr(user, 'is_staff', False):
        return []
    if project is None or not query_text:
        return []

    project_org = _norm_org(getattr(project, 'organisation', ''))
    access_q = Q(project=project)
    if project_org:
        access_q |= Q(visibility='organisation_shared', organisation__iexact=(project.organisation or '').strip())
    access_q |= Q(visibility='platform_learning_demo', is_demo=True)
    access_q |= Q(
        visibility='platform_learning_verified', is_demo=False,
        verification_status='verified', review_tier='independently_verified',
    )

    candidates = (
        EvidenceMemory.objects
        .filter(source_reference__startswith=OUTCOME_SOURCE_PREFIX)
        .filter(access_q)
        .exclude(visibility='restricted_unresolved')
        .exclude(verification_status='rejected')
        .select_related('project', 'originating_outcome', 'originating_decision')
    )

    # Over-fetch on pure similarity so quality re-weighting has real
    # similarity-ranked material to reorder — never invents candidates.
    ranked = _rank_candidates(query_text, candidates, top_k=max(limit * 3, limit))
    similarities = _similarities_for(query_text, ranked)

    results = []
    for memory in ranked:
        # Defence in depth: the queryset above should already be correct,
        # but the per-record policy check is authoritative.
        if not is_record_accessible(memory, project, user=user):
            continue
        results.append(score_and_explain(memory, project, similarity=similarities.get(memory.pk)))

    results.sort(key=lambda r: ((r.similarity or 0.0) + r.quality_score), reverse=True)
    return results[:limit]


class VisibilityNotAllowedError(Exception):
    """Raised when a record's own state cannot honestly support the
    requested visibility."""


def set_visibility(memory, visibility, actor=None):
    """
    The one sanctioned way to change a record's visibility — an explicit
    human action, never automatic. Validates that the record's own state can
    honestly support the target state:

    - platform_learning_verified requires verification_status='verified',
      review_tier='independently_verified', and is_demo=False;
    - platform_learning_demo requires is_demo=True (real private evidence is
      never shared under a demo label);
    - organisation_shared requires a non-blank organisation on the record
      (set from its project when missing);
    - rejected records can never be shared beyond project_private.
    """
    valid = {choice for choice, _ in memory.VISIBILITY_CHOICES}
    if visibility not in valid:
        raise VisibilityNotAllowedError(f'Unknown visibility {visibility!r}.')

    if memory.verification_status == 'rejected' and visibility not in ('project_private', 'restricted_unresolved'):
        raise VisibilityNotAllowedError('A rejected record cannot be shared for learning.')
    if visibility == 'platform_learning_verified':
        if memory.is_demo:
            raise VisibilityNotAllowedError('Demo evidence cannot be shared as verified platform learning.')
        if memory.verification_status != 'verified' or memory.review_tier != 'independently_verified':
            raise VisibilityNotAllowedError(
                'Only independently verified records can be shared as verified platform learning.'
            )
    if visibility == 'platform_learning_demo' and not memory.is_demo:
        raise VisibilityNotAllowedError('Only demo evidence can be shared under the demo learning label.')
    if visibility == 'organisation_shared':
        if not (memory.organisation or '').strip():
            project_org = (getattr(memory.project, 'organisation', '') or '').strip()
            if not project_org:
                raise VisibilityNotAllowedError(
                    'Organisation sharing requires an organisation on the record or its project.'
                )
            memory.organisation = project_org

    memory.visibility = visibility
    if actor is not None:
        memory._cg_changed_by = actor
    memory.save(update_fields=['visibility', 'organisation'])
    return memory
