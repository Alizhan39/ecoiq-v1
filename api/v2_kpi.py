"""
api/v2_kpi.py — one company against one of the 114 stewardship principles.

WHAT THIS ENDPOINT IS FOR
-------------------------
`/api/v2/companies/<slug>/assessment/` answers "what is this organisation's
overall standing?". This answers a different and narrower question: "what did
we observe about this organisation against ONE principle, what evidence says
so, and how sure are we?"

It is deliberately a separate endpoint rather than a fatter assessment payload.
An investigation view needs the full evidence chain for one KPI; a company page
needs a one-line summary of many. Serving both from one shape would make the
common case pay for the rare one.

SACRED-SOURCE GOVERNANCE, ENFORCED HERE
---------------------------------------
`docs/governance-principles-surah-map.md` is unambiguous: no Surah names,
Arabic terminology, ayah text or translations appear in public-facing code or
API responses. The mapping is internal.

That rule is enforced at THIS boundary rather than left to the frontend,
because a template that forgets is a leak and a serializer that never emits the
field cannot forget. `stewardship_principle` below carries the operational
principle only — the plain-language statement of what is being tested.

There is a second, independent reason. `SacredSourceReference.review_status`
defaults to `requires_scholarly_review`. Publishing an unreviewed sacred
reference would violate EcoIQ's own evidence-integrity rule — the same rule
that keeps an unevidenced score unpublished — quite apart from the language
policy.

EVIDENCE THAT DOES NOT COUNT IS STILL SHOWN
-------------------------------------------
Links that are not `confirmed` are returned, flagged, and excluded from the
assessment — `kpi_engine.derive_status_from_evidence` already counts only
confirmed links. Hiding them would make the assessment look better evidenced
than it is; counting them would let unreviewed material move a verdict. The
payload does both honestly: `counts_toward_assessment` is on every item.
"""
from __future__ import annotations

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from companies.models import CompanyProfile
from companies.visibility import profile_for
from company_intelligence.models import CompanyKPIAssessment
from company_intelligence.services.kpi_engine import derive_status_from_evidence
from company_intelligence.services.investigation_chain import investigation_chain
from company_intelligence.services.source_provenance import provenance_for_memory
from core.esg_principles_data import PRINCIPLES

#: Verdict vocabulary the UI renders. Mirrors KPI_STATUS_CHOICES, with the
#: distinction §16 asks for: a mixed picture that contains a FINAL regulatory
#: finding is not the same as a mixed picture that does not, and flattening
#: them loses the thing a reader most needs to know.
VERDICT_LABELS = {
    'strong_support': 'STRONGLY SUPPORTS',
    'support': 'SUPPORTS',
    'mixed': 'MIXED',
    'mixed_material_conflict': 'MIXED — MATERIAL CONFLICT',
    'conflict': 'CONFLICTS',
    'neutral_or_no_material_link': 'NO MATERIAL LINK',
    'insufficient_evidence': 'INSUFFICIENT EVIDENCE',
    'not_assessed': 'NOT ASSESSED',
}

#: Legal statuses strong enough to make a conflict "material". A preliminary
#: finding is deliberately NOT in this set: it is a regulator's opening
#: position, not its conclusion.
MATERIAL_STATUSES = {'final_regulatory_finding', 'court_finding'}

#: Confidence is categorical, never a percentage. The inputs are categorical
#: too, and a number would manufacture precision the evidence cannot support —
#: the same reason `types/evidence.ts` refuses a numeric confidence.
CONFIDENCE_ORDER = ['INSUFFICIENT_EVIDENCE', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']


def _principle(kpi_id: int) -> dict:
    for entry in PRINCIPLES:
        if entry['id'] == kpi_id:
            return entry
    raise Http404(f'No stewardship principle with id {kpi_id}.')


def _evidence_payload(link) -> dict:
    """
    One evidence item. Never includes the raw source text unless the record is
    a demo fixture: a third-party excerpt is a licensing question, and this
    endpoint answers anonymously.

    `title` used to fall back to `source_reference`, which is the idempotency
    key `create_memory_from_evidence()` writes — so the first real production
    ingestion served an evidence item titled `harvester.Evidence:41`. The title
    now comes from the source record, and is null when the source recorded
    none. `record_reference` carries the key, labelled as the key.
    """
    evidence = link.evidence
    provenance = provenance_for_memory(evidence)
    return {
        'id': evidence.pk,
        'title': provenance['title'],
        'provenance': provenance,
        'relation': link.relationship,
        'legal_status': evidence.legal_status or 'unclassified',
        'legal_status_strength': evidence.LEGAL_STATUS_STRENGTH.get(evidence.legal_status, 0),
        # Kept for callers that already read it. `provenance.authority` is the
        # structured form, derived from source type via the canonical tier
        # table rather than from how the text reads.
        'source_authority': evidence.source_authority or '',
        'source_url': evidence.source_url or '',
        'source_type': evidence.source_type,
        'date_collected': evidence.date_collected.isoformat() if evidence.date_collected else None,
        'review_tier': evidence.review_tier,
        'verification_status': evidence.verification_status,
        'review_state': link.review_state,
        # The honest flag. A reader can see unconfirmed material AND see that
        # it changed nothing.
        'counts_toward_assessment': link.review_state == 'confirmed',
        'match_basis': link.match_basis or '',
        'is_demo': evidence.is_demo,
        'excerpt': evidence.text_chunk if evidence.is_demo else '',
    }


def _confidence(confirmed_links) -> dict:
    """
    Derived from evidence characteristics, never hardcoded.

    Four inputs, each independently defensible: how many confirmed items there
    are (corroboration), the strongest evidentiary standing present
    (authority), whether anything was reviewed beyond ingestion (independence),
    and whether both sides of the principle are represented (coverage).
    """
    if not confirmed_links:
        return {
            'level': 'INSUFFICIENT_EVIDENCE',
            'reasons': ['No confirmed evidence is linked to this principle.'],
        }

    statuses = {l.evidence.legal_status for l in confirmed_links}
    tiers = {l.evidence.review_tier for l in confirmed_links}
    relations = {l.relationship for l in confirmed_links}

    reasons = []
    score = 0

    if statuses & MATERIAL_STATUSES:
        score += 2
        reasons.append('A final regulatory or court finding is among the evidence.')
    elif 'preliminary_regulatory_finding' in statuses:
        score += 1
        reasons.append('A regulatory finding is present but remains preliminary.')

    if tiers & {'human_reviewed', 'independently_verified'}:
        score += 1
        reasons.append('At least one item was reviewed beyond automated ingestion.')

    if len(confirmed_links) >= 3:
        score += 1
        reasons.append(f'{len(confirmed_links)} independent items corroborate the picture.')

    if {'supports', 'conflicts'} <= relations:
        score += 1
        reasons.append('Both supporting and conflicting evidence were considered.')

    level = ['LOW', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH', 'VERY_HIGH'][min(score, 5)]
    return {'level': level, 'reasons': reasons}


def _verdict(links) -> str:
    """
    The engine's deterministic verdict, with one refinement it does not make.

    `derive_status_from_evidence` returns 'mixed' whenever supports and
    conflicts coexist. That is correct but under-informative: a mixed picture
    whose conflict rests on a FINAL regulatory finding is materially different
    from one resting on a blog post, and a reader who cannot tell them apart
    has been told very little.
    """
    base = derive_status_from_evidence(links)
    if base != 'mixed':
        return base
    confirmed = [l for l in links if l.review_state == 'confirmed']
    conflicting = [l for l in confirmed if l.relationship == 'conflicts']
    if any(l.evidence.legal_status in MATERIAL_STATUSES for l in conflicting):
        return 'mixed_material_conflict'
    return 'mixed'


@require_GET
def company_kpi(request, slug: str, kpi_id: int):
    """One organisation against one principle. Anonymous, read-only."""
    principle = _principle(int(kpi_id))
    # Archived profiles answer 404 to the public and resolve for staff — see
    # companies/visibility.py. Previously this had no status filter at all,
    # so an archived organisation's evidence chain was served anonymously
    # while the page built on it 404'd for everyone.
    profile = profile_for(
        slug, request.user,
        queryset=CompanyProfile.objects.select_related('company'))

    assessment = (CompanyKPIAssessment.objects
                  .filter(company=profile, kpi_id=kpi_id)
                  .prefetch_related('evidence_links__evidence', 'remediation_steps__evidence')
                  .first())

    links = list(assessment.evidence_links.all()) if assessment else []
    confirmed = [l for l in links if l.review_state == 'confirmed']
    verdict = _verdict(links) if links else 'insufficient_evidence'
    confidence = _confidence(confirmed)

    remediation = [
        {
            'position': step.position,
            'kind': step.kind,
            'kind_label': step.get_kind_display(),
            'summary': step.summary,
            'detail': step.detail,
            'occurred_on': step.occurred_on.isoformat() if step.occurred_on else None,
            'verification': step.verification,
            'verification_label': step.get_verification_display(),
            'evidence_id': step.evidence_id,
        }
        for step in (assessment.remediation_steps.all() if assessment else [])
    ]

    return JsonResponse({
        'company': {
            'slug': profile.company.slug,
            'name': profile.company.name,
            'sector': profile.company.sector,
        },
        # The operational principle ONLY. No surah number, name, Arabic term,
        # ayah text or translation — see the module docstring.
        'stewardship_principle': {
            'kpi_id': principle['id'],
            'title': principle['title'],
            'tagline': principle['tagline'],
            'question': principle['question'],
            'category': principle['category'],
            'principle_statement': principle.get('signal', ''),
            'metrics': principle.get('metrics', []),
        },
        'assessment': {
            'verdict': verdict,
            'verdict_label': VERDICT_LABELS.get(verdict, verdict.upper()),
            'confidence': confidence['level'],
            'confidence_reasons': confidence['reasons'],
            'rationale': assessment.rationale if assessment else '',
            'is_demo': bool(assessment and assessment.is_demo),
            'last_assessed_at': (
                assessment.last_assessed_at.isoformat() if assessment else None),
        },
        'counts': {
            'total': len(links),
            'confirmed': len(confirmed),
            'supports': sum(1 for l in confirmed if l.relationship == 'supports'),
            'conflicts': sum(1 for l in confirmed if l.relationship == 'conflicts'),
            'context': sum(1 for l in confirmed if l.relationship == 'context'),
            'excluded_from_assessment': len(links) - len(confirmed),
            'remediation_steps': len(remediation),
        },
        'evidence': [_evidence_payload(l) for l in links],
        'remediation': remediation,
        # The full chain from requirement to decision, every node carrying an
        # explicit state. NOT_INVESTIGATED and NONE_FOUND are different claims
        # and are never collapsed into an empty section.
        'chain': investigation_chain(assessment, links),
    })
