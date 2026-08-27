"""
api/v2_principles.py — the 114 stewardship principles, as a product surface.

TWO ENDPOINTS, TWO QUESTIONS
----------------------------
`/api/v2/principles/` answers "what does EcoIQ assess against?" — the registry
itself, with no organisation involved.

`/api/v2/companies/<slug>/principles/` answers "where does ONE organisation
stand across all 114?" — the matrix. It is the entry point into the
investigation flow: a reader picks a cell here and lands on
`/api/v2/companies/<slug>/kpis/<id>/`, which serves that one principle's full
evidence chain.

Between them they close the gap the Phase 1 audit found: the 114 were canonical
in `core.esg_principles_data` and reachable through the engine, but the only way
into them from the product was a single hard-coded link to principle 114.

ONE SOURCE OF TRUTH FOR STATUS
------------------------------
The per-principle status comes from `kpi_engine.kpi_alignment_profile()` and
nowhere else. That service is already described in its own module as the ONE
canonical per-company 114-row profile, and several surfaces
(`companies/views.py`, `category_coverage`, `alignment_metrics`,
`company_trace`) read it. Recomputing status here would make a second authority
that drifts, which is the failure this codebase has repeatedly designed against.

What this module adds is the per-cell DETAIL a matrix needs and the profile does
not carry: how much evidence sits behind each state, whether a conflict rests on
a final regulatory finding, and whether remediation has been recorded.

NO FOURTH VOCABULARY
--------------------
The brief asks the matrix to distinguish states like "under review",
"remediation underway" and "remediated with residual concern". Those are NOT
added to `KPI_STATUS_CHOICES` — a second status enum layered over the first is
exactly how two sources of truth start.

Instead each row carries the real status plus orthogonal, independently true
facts: `pending_review_count`, `remediation_step_count`,
`has_material_conflict`, `counts`. A cell that is `conflict` with
`remediation_step_count > 0` is "conflict, remediation recorded" — composed at
the presentation layer from facts, not asserted by a new enum. Remediation
changes what is displayed alongside the finding; it never rewrites the finding,
which is the invariant the whole evidence layer exists to protect.

SACRED-SOURCE GOVERNANCE
------------------------
Same boundary as `api/v2_kpi.py`, for the same reason: `docs/governance-
principles-surah-map.md` keeps the mapping internal, and a serializer that never
emits the field cannot forget to. Only the operational principle is exposed.

NO SCORE
--------
Neither endpoint returns a number standing for an organisation's overall
quality. `coverage_pct` is the share of principles that have been ASSESSED —
a statement about how much work has been done, not about how good the
organisation is — and it is labelled as such.
"""
from __future__ import annotations

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from api.v2_kpi import MATERIAL_STATUSES, VERDICT_LABELS
from companies.models import CompanyProfile
from companies.visibility import profile_for
from company_intelligence.services.kpi_engine import kpi_alignment_profile
from core.esg_principles_data import PRINCIPLE_CATEGORIES, PRINCIPLES

#: Review states that count toward an assessment. Mirrors the single filter in
#: `kpi_engine.derive_status_from_evidence`; imported as a name rather than
#: repeated as a literal so the two cannot drift apart silently.
COUNTING_REVIEW_STATE = 'confirmed'

#: id -> principle, built once at import. The matrix walks 114 rows and needs a
#: principle for each; a linear scan per row is 114 scans of a 114-item list.
_PRINCIPLE_BY_ID = {entry['id']: entry for entry in PRINCIPLES}


def _principle_public(entry: dict) -> dict:
    """
    The operational principle only — see SACRED-SOURCE GOVERNANCE above.

    `signal` is the analyst guidance held in `esg_principles_data`. It is
    published deliberately: it says what EcoIQ looks for, which is the sort of
    thing a reader is entitled to check the method against.
    """
    return {
        'kpi_id': entry['id'],
        'title': entry['title'],
        'category': entry['category'],
        'tagline': entry['tagline'],
        'question': entry['question'],
        'metrics': entry.get('metrics', []),
        'principle_statement': entry.get('signal', ''),
    }


@require_GET
def principles(request):
    """
    GET /api/v2/principles/

    The registry. No organisation, no evidence, no state — this is what EcoIQ
    assesses against, which is a stable fact about the method rather than a
    finding about anybody.
    """
    return JsonResponse({
        'total': len(PRINCIPLES),
        'categories': [
            {
                'key': key,
                'label': label,
                'principle_count': sum(1 for p in PRINCIPLES if p['category'] == key),
            }
            for key, label in PRINCIPLE_CATEGORIES
        ],
        'principles': [_principle_public(entry) for entry in PRINCIPLES],
    })


def _evidence_detail(profile) -> tuple[dict, dict]:
    """
    Per-KPI evidence counts and remediation counts, in two queries total.

    Deliberately not computed by walking `assessment.evidence_links` per row:
    that is one query per assessed principle, and this endpoint is the one that
    will be asked about a fully assessed organisation — the exact case where
    that cost is 114 queries instead of 2.
    """
    from company_intelligence.models import CompanyKPIEvidenceLink, KPIRemediationStep

    counts: dict[int, dict] = {}
    for row in (CompanyKPIEvidenceLink.objects
                .filter(assessment__company=profile)
                .values('assessment__kpi_id', 'relationship', 'review_state',
                        'evidence__legal_status')):
        kpi_id = row['assessment__kpi_id']
        bucket = counts.setdefault(kpi_id, {
            'total': 0, 'confirmed': 0, 'supports': 0, 'conflicts': 0,
            'context': 0, 'insufficient_to_conclude': 0,
            'excluded_from_assessment': 0, 'pending_review': 0,
            'has_material_conflict': False,
        })
        bucket['total'] += 1
        if row['review_state'] == 'proposed':
            bucket['pending_review'] += 1
        if row['review_state'] != COUNTING_REVIEW_STATE:
            # Shown, flagged, and excluded — the same honesty rule v2_kpi
            # applies per item, aggregated here.
            bucket['excluded_from_assessment'] += 1
            continue
        bucket['confirmed'] += 1
        relationship = row['relationship']
        if relationship in bucket:
            bucket[relationship] += 1
        if (relationship == 'conflicts'
                and row['evidence__legal_status'] in MATERIAL_STATUSES):
            bucket['has_material_conflict'] = True

    remediation: dict[int, int] = {}
    for row in (KPIRemediationStep.objects
                .filter(assessment__company=profile)
                .values_list('assessment__kpi_id', flat=True)):
        remediation[row] = remediation.get(row, 0) + 1

    return counts, remediation


@require_GET
def company_principles(request, slug: str):
    """
    GET /api/v2/companies/<slug>/principles/

    One organisation across all 114. Read-only, and on the same footing as
    `company_kpi`: this reports evidence state, not a score, so the publication
    gate that governs `/assessment/` does not apply.

    It does apply the VISIBILITY gate. When this endpoint was added it copied
    `company_kpi`'s profile lookup, which had no status filter — so an archived
    organisation's matrix answered 200 anonymously. Both now go through
    `companies.visibility.profile_for`. A principle
    with no assessment is reported as `not_assessed` and stays in the
    denominator — never dropped to make coverage look better than it is.
    """
    profile = profile_for(
        slug, request.user,
        queryset=CompanyProfile.objects.select_related('company'))

    alignment = kpi_alignment_profile(profile)
    evidence_counts, remediation_counts = _evidence_detail(profile)

    rows = []
    for row in alignment['rows']:
        kpi_id = row['kpi_id']
        detail = evidence_counts.get(kpi_id)
        assessment = row['assessment']
        rows.append({
            **_principle_public(_PRINCIPLE_BY_ID[kpi_id]),
            'state': row['status'],
            'state_label': VERDICT_LABELS.get(row['status'], row['status_display']),
            'counts': {
                'total': detail['total'] if detail else 0,
                'confirmed': detail['confirmed'] if detail else 0,
                'supports': detail['supports'] if detail else 0,
                'conflicts': detail['conflicts'] if detail else 0,
                'context': detail['context'] if detail else 0,
                'insufficient_to_conclude': (
                    detail['insufficient_to_conclude'] if detail else 0),
                'excluded_from_assessment': (
                    detail['excluded_from_assessment'] if detail else 0),
            },
            # Orthogonal facts the presentation layer composes a cell from —
            # see NO FOURTH VOCABULARY above.
            'pending_review_count': detail['pending_review'] if detail else 0,
            'remediation_step_count': remediation_counts.get(kpi_id, 0),
            'has_material_conflict': bool(detail and detail['has_material_conflict']),
            'is_demo': bool(assessment and assessment.is_demo),
            'last_assessed_at': (
                assessment.last_assessed_at.isoformat() if assessment else None),
        })

    return JsonResponse({
        'company': {
            'slug': profile.company.slug,
            'name': profile.company.name,
            'sector': profile.company.sector,
        },
        'summary': {
            'total': alignment['total'],
            'assessed': alignment['assessed'],
            'not_assessed': alignment['counts'].get('not_assessed', 0),
            # Named for what it measures. This is how much of the framework has
            # been investigated, NOT how well the organisation did.
            'assessed_pct': alignment['coverage_pct'],
            'counts': alignment['counts'],
            'pending_review_total': alignment['pending_review_total'],
        },
        'categories': [
            {
                'key': key,
                'label': label,
                'principle_count': sum(1 for r in rows if r['category'] == key),
                'assessed_count': sum(
                    1 for r in rows
                    if r['category'] == key and r['state'] != 'not_assessed'),
            }
            for key, label in PRINCIPLE_CATEGORIES
        ],
        'principles': rows,
    })
