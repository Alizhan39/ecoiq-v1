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


def investigation_chain(assessment, links=None) -> dict:
    """
    The full chain for one organisation against one principle.

    `assessment` may be None — an organisation that has never been looked at
    against this principle gets the chain with every node NOT_INVESTIGATED,
    rather than no chain at all.
    """
    from api.v2_kpi import VERDICT_LABELS

    links = list(links if links is not None
                 else (assessment.evidence_links.all() if assessment else []))
    confirmed = [l for l in links if l.review_state == 'confirmed']
    awaiting = [l for l in links if l.review_state == 'proposed']

    verdict = assessment.status if assessment else 'not_assessed'
    conflict = _conflict(confirmed)
    remediation = _remediation(assessment, confirmed)

    return {
        'investigation_started': bool(confirmed),
        'evidence_requirements': _requirement_states(confirmed),
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
        'standing': _standing(confirmed),
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
        'decision_implication': _decision_implication(verdict, confirmed, conflict),
    }
