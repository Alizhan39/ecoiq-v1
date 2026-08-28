"""
company_intelligence/services/investigation_chain.py — one organisation against
one principle, as an explicit chain from question to decision.

THE RULE THIS MODULE EXISTS TO ENFORCE
--------------------------------------
Every node has a state. None is ever silently omitted, because an omitted node
reads as "nothing to say" when the truth is usually "nobody looked", and those
are opposite claims about EcoIQ rather than about the organisation.

The distinction runs through everything here:

    NOT_INVESTIGATED   nobody has looked yet
    NONE_FOUND         someone looked and found nothing

"No verified remediation found" is a finding. "Remediation not investigated" is
an admission. A chain that rendered both as an empty section would let the
second borrow the credibility of the first.

WHEN DOES AN INVESTIGATION BEGIN?
---------------------------------
When a named reviewer confirms at least one evidence item. Before that,
everything downstream is NOT_INVESTIGATED — not because the data is missing but
because nothing has been established to reason from. Proposed evidence sitting
in a queue is not an investigation in progress; it is a queue.

That single rule is what keeps the chain honest for the nine candidates now in
production: real evidence, none reviewed, so every downstream node correctly
reports that nobody has looked rather than implying a clean result.

EVIDENCE REQUIREMENTS, NOT A CHECKLIST PER PRINCIPLE
----------------------------------------------------
The brief warns against manufacturing 114 arbitrary checklists, and it is right
to: an invented requirement list would be a fabricated standard presented as
methodology.

`stewardship_principle.metrics` is already the canonical per-principle material,
and it holds INDICATORS — "circularity rate %", "single-point-of-failure count".
Those are measurable quantities that bear on the question. They are not
requirements: no rule says a conclusion needs four of the five.

So requirements are modelled as the STRUCTURAL conditions that were already
implicit in `api.v2_kpi._confidence` — corroboration, authority, independence,
and whether both sides were considered. Those apply to every principle because
they are properties of evidence rather than of subject matter, and naming them
turns INSUFFICIENT EVIDENCE from a status into an explanation: not merely
"insufficient", but which condition is unmet.

NOTHING HERE DECIDES ANYTHING
-----------------------------
Read-only. The verdict still comes from `kpi_engine`, confirmation still
requires `apply_review_decision` and a named reviewer, and publication
eligibility is still decided where it always was. This module assembles what
those systems already determined and states the gaps between them.
"""
from __future__ import annotations

from company_intelligence.services.kpi_engine import STRONG_EVIDENCE_TIERS

#: A node nobody has reached yet.
NOT_INVESTIGATED = 'NOT_INVESTIGATED'
#: A node that was reached, where the answer is genuinely nothing.
NONE_FOUND = 'NONE_FOUND'

#: Legal statuses strong enough to make a conflict material. Mirrors
#: api.v2_kpi.MATERIAL_STATUSES — a preliminary finding is a regulator's opening
#: position, not its conclusion.
MATERIAL_STATUSES = {'final_regulatory_finding', 'court_finding'}

#: The four structural evidence requirements. Properties of evidence, not of
#: subject matter, which is why they apply to all 114 without inventing a
#: checklist for any of them.
REQUIREMENTS = (
    ('corroboration',
     'More than one independent item speaks to the question',
     'A single item can be wrong, out of date, or unrepresentative without '
     'anything in the record showing it.'),
    ('authority',
     'At least one item carries evidentiary standing beyond assertion',
     'A claim about an organisation, made by that organisation, is a starting '
     'point rather than a finding.'),
    ('independence',
     'At least one item was reviewed beyond automated ingestion',
     'A keyword match establishes that a document mentions the topic, never '
     'what it concludes.'),
    ('both_sides',
     'Evidence pointing both ways was considered',
     'A conclusion that only ever saw agreeing evidence has not been tested.'),
)


def _requirement_states(confirmed) -> list[dict]:
    """Which structural conditions the confirmed evidence meets."""
    statuses = {l.evidence.legal_status for l in confirmed}
    tiers = {l.evidence.review_tier for l in confirmed}
    relations = {l.relationship for l in confirmed}

    met = {
        'corroboration': len(confirmed) >= 2,
        'authority': bool(statuses & MATERIAL_STATUSES) or bool(
            statuses & {'preliminary_regulatory_finding'}),
        'independence': bool(tiers & STRONG_EVIDENCE_TIERS),
        'both_sides': {'supports', 'conflicts'} <= relations,
    }
    return [
        {
            'key': key,
            'requirement': requirement,
            'why': why,
            # NOT_INVESTIGATED rather than NOT_MET when there is nothing to
            # assess: an unmet requirement is a judgement about evidence that
            # exists, and none does.
            'state': ('MET' if met[key] else
                      ('NOT_MET' if confirmed else NOT_INVESTIGATED)),
        }
        for key, requirement, why in REQUIREMENTS
    ]


def _standing(confirmed) -> dict:
    """The strongest evidentiary standing present."""
    if not confirmed:
        return {'state': NOT_INVESTIGATED,
                'detail': 'No evidence has been confirmed, so nothing has an '
                          'evidentiary standing yet.'}
    statuses = {l.evidence.legal_status for l in confirmed}
    if statuses & MATERIAL_STATUSES:
        return {'state': 'FINAL_REGULATORY_OR_COURT_FINDING',
                'detail': 'A concluded regulatory or court finding is among the '
                          'confirmed evidence.'}
    if 'preliminary_regulatory_finding' in statuses:
        return {'state': 'PRELIMINARY_REGULATORY_FINDING',
                'detail': "A regulator has opened a position but has not "
                          'concluded it.'}
    if statuses - {'unclassified', ''}:
        return {'state': 'CLASSIFIED_NON_REGULATORY',
                'detail': 'The confirmed evidence carries a recorded standing, '
                          'none of it regulatory.'}
    return {'state': 'UNCLASSIFIED',
            'detail': 'Evidence is confirmed but none of it has been given an '
                      'evidentiary standing.'}


def _conflict(confirmed) -> dict:
    if not confirmed:
        return {'state': NOT_INVESTIGATED,
                'detail': 'Nothing has been confirmed, so no conflict has been '
                          'looked for.'}
    conflicting = [l for l in confirmed if l.relationship == 'conflicts']
    if not conflicting:
        return {'state': NONE_FOUND,
                'detail': f'{len(confirmed)} confirmed item(s) were considered '
                          'and none conflicts with the others.'}
    material = [l for l in conflicting
                if l.evidence.legal_status in MATERIAL_STATUSES]
    if material:
        return {'state': 'MATERIAL_CONFLICT',
                'detail': 'A conflict rests on a concluded regulatory or court '
                          'finding.'}
    return {'state': 'CONFLICT',
            'detail': f'{len(conflicting)} confirmed item(s) conflict, none '
                      'resting on a concluded regulatory finding.'}


def _remediation(assessment, confirmed) -> dict:
    steps = list(assessment.remediation_steps.all()) if assessment else []
    if steps:
        verified = [s for s in steps if s.verification == 'independently_verified']
        return {
            'state': 'RECORDED',
            'step_count': len(steps),
            'independently_verified_count': len(verified),
            'detail': (f'{len(steps)} step(s) recorded, {len(verified)} '
                       'independently verified. Remediation is reported '
                       'alongside the finding and never replaces it.'),
        }
    if not confirmed:
        return {'state': NOT_INVESTIGATED, 'step_count': 0,
                'independently_verified_count': 0,
                'detail': 'Nothing has been confirmed, so no remediation has '
                          'been looked for.'}
    return {'state': NONE_FOUND, 'step_count': 0,
            'independently_verified_count': 0,
            'detail': 'Evidence was reviewed and no verified remediation was '
                      'found. That is a finding, not an absence of enquiry.'}


def _residual_concern(conflict: dict, remediation: dict) -> dict:
    """
    What remains after remediation is taken into account.

    Never resolves a concern on the strength of the organisation's own account:
    remediation reduces residual concern only where it was independently
    verified.
    """
    if conflict['state'] == NOT_INVESTIGATED:
        return {'state': NOT_INVESTIGATED,
                'detail': 'No finding has been established, so there is nothing '
                          'for a residual concern to be about.'}
    if conflict['state'] == NONE_FOUND:
        return {'state': NONE_FOUND,
                'detail': 'No conflict was found, so no residual concern arises '
                          'from one.'}
    if remediation['independently_verified_count'] > 0:
        return {'state': 'REDUCED_BY_VERIFIED_REMEDIATION',
                'detail': 'A conflict stands historically; independently '
                          'verified remediation reduces its current standing '
                          'without erasing the original finding.'}
    if remediation['state'] == 'RECORDED':
        return {'state': 'REMEDIATION_CLAIMED_NOT_VERIFIED',
                'detail': 'Remediation is recorded but none of it was '
                          'independently verified, so the concern is unchanged.'}
    return {'state': 'UNMITIGATED',
            'detail': 'A conflict stands and no remediation has been recorded '
                      'against it.'}


def _decision_implication(verdict: str, confirmed, conflict: dict) -> dict:
    """
    What a reader can defensibly do with this. Never advice, and never a
    recommendation to buy, sell or hold anything.
    """
    if not confirmed:
        return {'state': NOT_INVESTIGATED,
                'detail': 'Nothing has been established, so this principle '
                          'supports no decision either way. That is not a point '
                          'in the organisation\'s favour or against it.'}
    if conflict['state'] == 'MATERIAL_CONFLICT':
        return {'state': 'MATERIAL_CONCERN_ON_RECORD',
                'detail': 'A concluded regulatory or court finding conflicts on '
                          'this principle. It is on the record whatever else is '
                          'true of the organisation.'}
    if verdict in ('strong_support', 'support'):
        return {'state': 'SUPPORTED_ON_THE_EVIDENCE_SEEN',
                'detail': 'The confirmed evidence supports the organisation on '
                          'this principle. It bounds what was looked at, not '
                          'what is true.'}
    if verdict in ('mixed', 'mixed_material_conflict', 'conflict'):
        return {'state': 'UNRESOLVED',
                'detail': 'Confirmed evidence points both ways and has not been '
                          'reconciled.'}
    return {'state': 'INSUFFICIENT_TO_ACT',
            'detail': 'Evidence exists but does not carry a conclusion.'}


def _primary_source(confirmed) -> dict:
    """
    The strongest source behind the confirmed evidence.

    Strongest by AUTHORITY TIER, which says what the source IS. It is not a
    claim that this source carries the argument — a Tier 1 regulator filing and
    a Tier 2 company report can sit on opposite sides of the same principle.
    """
    from company_intelligence.services.source_provenance import provenance_for_memory

    if not confirmed:
        return {'state': NOT_INVESTIGATED,
                'detail': 'No evidence is confirmed, so no source stands behind '
                          'anything yet.'}
    resolved = [(provenance_for_memory(l.evidence), l) for l in confirmed]
    ranked = sorted(
        resolved,
        key=lambda pair: (pair[0]['authority']['tier']
                          if pair[0]['authority']['tier'] is not None else 99))
    provenance, _ = ranked[0]
    return {
        'state': 'IDENTIFIED',
        'title': provenance['title'],
        'publisher': provenance['publisher'],
        'url': provenance['url'],
        'authority': provenance['authority'],
        'detail': (f'{provenance["title"] or "An untitled source"} — '
                   f'{provenance["authority"]["label"].lower()}. Strongest by '
                   'source type among the confirmed evidence; that is what the '
                   'source is, not which way it points.'),
    }


def _provenance_completeness(confirmed) -> dict:
    """
    Whether the confirmed evidence can be traced and re-checked.

    A finding nobody can verify against its source is an assertion. This reports
    which of the checkable fields are actually present rather than assuming a
    citation is complete because it exists.
    """
    from company_intelligence.services.source_provenance import provenance_for_memory

    if not confirmed:
        return {'state': NOT_INVESTIGATED, 'complete': 0, 'total': 0,
                'missing': [], 'detail': 'Nothing is confirmed, so there is no '
                                         'provenance to check.'}
    fields = ('title', 'publisher', 'url', 'publication_date', 'content_hash')
    missing: dict[str, int] = {}
    complete = 0
    for link in confirmed:
        provenance = provenance_for_memory(link.evidence)
        absent = [f for f in fields if not provenance.get(f)]
        if not absent:
            complete += 1
        for f in absent:
            missing[f] = missing.get(f, 0) + 1
    return {
        'state': 'COMPLETE' if complete == len(confirmed) else 'PARTIAL',
        'complete': complete,
        'total': len(confirmed),
        'missing': sorted(missing),
        'detail': (f'{complete} of {len(confirmed)} confirmed item(s) carry a '
                   'full citation.'
                   + (f' Missing across the rest: {", ".join(sorted(missing))}.'
                      if missing else '')),
    }


def _human_standing(assessment, confirmed) -> dict:
    """
    WHO decided this, and when — as distinct from what the evidence is.

    `standing` above is evidentiary: what kind of source the claim rests on.
    This is procedural: whether a named person classified it. A finding that
    looks strong on evidence and has never been reviewed is a different object
    from one a reviewer signed, and collapsing them would let automated
    matching inherit a human's credibility.
    """
    from company_intelligence.models import EvidenceReviewAction

    if assessment is None or not confirmed:
        return {'state': NOT_INVESTIGATED, 'reviewers': [], 'review_count': 0,
                'detail': 'No evidence has been confirmed, so nobody has ruled '
                          'on this principle.'}
    actions = list(EvidenceReviewAction.objects
                   .filter(kpi_evidence_link__assessment=assessment)
                   .select_related('reviewer')
                   .order_by('created_at'))
    if not actions:
        return {'state': 'CONFIRMED_WITHOUT_RECORDED_REVIEW',
                'reviewers': [], 'review_count': 0,
                'detail': 'Evidence is confirmed but no review action is on '
                          'record — it predates the review workbench or was '
                          'seeded as a fixture.'}
    reviewers = sorted({a.reviewer.username for a in actions if a.reviewer})
    latest = actions[-1]
    return {
        'state': 'REVIEWED_BY_NAMED_HUMAN',
        'reviewers': reviewers,
        'review_count': len(actions),
        'last_reviewed_at': latest.created_at.isoformat() if latest.created_at else None,
        'last_action': latest.action,
        'rationale': latest.reason or None,
        'evidence_version': latest.evidence_version or None,
        'detail': (f'{len(actions)} review action(s) by '
                   f'{", ".join(reviewers) or "an unnamed reviewer"}. The '
                   'classification is a human act, recorded immutably.'),
    }


def _confidence(confirmed, requirements) -> dict:
    """
    Categorical, never a percentage — the inputs are categorical too, and a
    number would manufacture precision the evidence cannot support.

    Derived from how many structural requirements the evidence meets, so the
    level and the reason are the same fact rather than two.
    """
    if not confirmed:
        return {'state': 'INSUFFICIENT_EVIDENCE', 'met': 0, 'of': len(requirements),
                'detail': 'No confirmed evidence, so nothing to be confident '
                          'about either way.'}
    met = [r for r in requirements if r['state'] == 'MET']
    unmet = [r['requirement'] for r in requirements if r['state'] == 'NOT_MET']
    level = ('VERY_HIGH' if len(met) == 4 else
             'HIGH' if len(met) == 3 else
             'MEDIUM' if len(met) == 2 else
             'LOW' if len(met) == 1 else 'VERY_LOW')
    return {
        'state': level,
        'met': len(met),
        'of': len(requirements),
        'unmet': unmet,
        'detail': (f'{len(met)} of {len(requirements)} evidence requirements '
                   'met.' + (f' Not met: {"; ".join(unmet)}.' if unmet else '')),
    }


def _publication_eligibility(profile, confirmed) -> dict:
    """
    Whether a composite score may be published — decided where it always was.

    `companies.eligibility.decide()` reads coverage, confidence and score, and
    never reads visibility. Reported here so the chain ends where a reader
    expects, not recomputed: a second publication rule is how two answers to one
    question start.
    """
    from companies import eligibility

    decision = eligibility.decide(profile)
    return {
        'state': 'PUBLISHED' if decision.is_published else decision.status,
        'is_published': decision.is_published,
        'reasons': list(decision.reasons),
        'detail': ('A composite score is publishable.' if decision.is_published
                   else 'No composite score is publishable for this '
                        'organisation. That is decided from coverage and '
                        'confidence across all inputs, not from this principle '
                        'alone.'),
    }


def investigation_chain(assessment, links=None, *, profile=None,
                       principle=None) -> dict:
    """
    The full chain for one organisation against one principle.

    `assessment` may be None — an organisation that has never been looked at
    against this principle gets the chain with every node NOT_INVESTIGATED,
    rather than no chain at all.

    Every node in the sequence the brief names is present:

        entity → principle → question → evidence requirement → evidence →
        primary source → provenance → human standing → finding →
        conflict status → remediation status → residual concern →
        confidence → publication eligibility → decision implication

    No value is invented to fill one. Where a node has no answer it says which
    KIND of nothing it is: NOT_INVESTIGATED when nobody looked, NONE_FOUND when
    somebody did.
    """
    from api.v2_kpi import VERDICT_LABELS

    links = list(links if links is not None
                 else (assessment.evidence_links.all() if assessment else []))
    confirmed = [l for l in links if l.review_state == 'confirmed']
    awaiting = [l for l in links if l.review_state == 'proposed']

    verdict = assessment.status if assessment else 'not_assessed'
    conflict = _conflict(confirmed)
    remediation = _remediation(assessment, confirmed)
    requirements = _requirement_states(confirmed)

    if profile is None and assessment is not None:
        profile = assessment.company
    if principle is None and assessment is not None:
        from core.esg_principles_data import PRINCIPLES
        principle = next(
            (p for p in PRINCIPLES if p['id'] == assessment.kpi_id), None)

    return {
        'investigation_started': bool(confirmed),
        # The chain opens with what is being asked of whom, so a reader never
        # has to hold the question in their head while reading the answer.
        'entity': {
            'state': 'IDENTIFIED' if profile is not None else NOT_INVESTIGATED,
            'slug': getattr(getattr(profile, 'company', None), 'slug', None),
            'name': getattr(getattr(profile, 'company', None), 'name', None),
        },
        'principle': {
            'state': 'IDENTIFIED' if principle else NOT_INVESTIGATED,
            'kpi_id': (principle or {}).get('id'),
            'title': (principle or {}).get('title'),
        },
        'question': {
            'state': 'STATED' if principle else NOT_INVESTIGATED,
            'text': (principle or {}).get('question'),
        },
        'evidence_requirements': requirements,
        'evidence': {
            'total': len(links),
            'confirmed': len(confirmed),
            'awaiting_review': len(awaiting),
            'state': ('REVIEWED' if confirmed else
                      ('AWAITING_REVIEW' if awaiting else NOT_INVESTIGATED)),
            'detail': (
                f'{len(awaiting)} item(s) recorded and awaiting review. They '
                'count toward nothing until a named reviewer classifies them.'
                if awaiting and not confirmed else
                f'{len(confirmed)} item(s) confirmed and counted.'
                if confirmed else
                'No evidence is linked to this principle.'),
        },
        'primary_source': _primary_source(confirmed),
        'provenance': _provenance_completeness(confirmed),
        # Evidentiary standing: what KIND of source the claim rests on.
        'standing': _standing(confirmed),
        # Procedural standing: WHO ruled on it. Distinct on purpose — a finding
        # nobody reviewed must not inherit a reviewer's credibility.
        'human_standing': _human_standing(assessment, confirmed),
        'finding': {
            'state': verdict.upper() if confirmed else NOT_INVESTIGATED,
            'label': (VERDICT_LABELS.get(verdict, verdict.upper()) if confirmed
                      else 'Not investigated'),
            'detail': ('Derived by rule from the confirmed evidence.' if confirmed
                       else 'No confirmed evidence, so no finding has been made.'),
        },
        'conflict': conflict,
        'remediation': remediation,
        'residual_concern': _residual_concern(conflict, remediation),
        'confidence': _confidence(confirmed, requirements),
        'publication_eligibility': _publication_eligibility(profile, confirmed),
        'decision_implication': _decision_implication(verdict, confirmed, conflict),
    }
