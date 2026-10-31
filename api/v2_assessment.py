"""
api/v2_assessment.py — the full organisation assessment, for the React company
page.

ONE GATE, APPLIED ONCE, AT THE TOP
----------------------------------
`companies.eligibility.decide` decides whether this organisation's assessment
may be published. If it may not, this endpoint returns identity and evidence
state and **nothing else** — no ethics profile, no financing readiness, no QDF
verdict, no Shariah result, no pillar values.

Not nulled out: absent. A payload with `"ethics": null` invites a client to
render an empty ethics panel, and an empty panel beside a real one is still a
statement about the organisation. The keys are simply not there, and
`score_status` says why.

That mirrors what the server-rendered page does — it fails closed to
detail_evidence_pending.html before it computes any panel — and it is the
reason this endpoint can exist at all.

WHAT IS DELIBERATELY NOT HERE
-----------------------------
Four panels from the server-rendered page were audited and moved behind
sign-in rather than ported (docs/product/COMPANY_PAGE_PANELS.md):

    matched financing pathways   readiness says an organisation COULD meet
                                 criteria; a matched pathway names an
                                 instrument, which is closer to advice
    data status / source library operational freshness, not a decision input
    watchlist                    user-scoped by definition
    stock strip                  removed outright: a share price beside an
                                 ethics assessment implies a relationship
                                 EcoIQ does not assert

DEMO ROWS NEVER LEAVE
---------------------
CompanyShariahScreen and CompanyControversy both carry `is_demo`. A demo row in
a public payload is fixture data presented as analysis — the exact confusion the
data-status panel was built to prevent. Filtered here, and asserted in tests.
"""
from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from companies.visibility import profile_for
from core.unknown import known


@api_view(['GET'])
@permission_classes([AllowAny])
def company_assessment(request, slug):
    """GET /api/v2/companies/<slug>/assessment/"""
    from companies.eligibility import decide
    from companies.evidence import PENDING_DETAIL, PENDING_HEADLINE

    # companies/visibility.py, like the sibling endpoints under this slug.
    # The literal here predated `public_demo`, so a demonstration organisation
    # 404'd on its assessment while /companies/<slug>/ served the page built on
    # it. This view takes DRF's default authentication chain, which includes
    # SessionAuthentication, so a staff reviewer is recognised.
    profile = profile_for(slug, request.user)
    company = profile.company

    decision = decide(profile)
    payload = {
        'slug': company.slug,
        'name': company.name,
        'sector': company.sector or '',
        'country': company.country or '',
        'score_status': decision.status,
        'ecoiq_score': decision.public_score,
        'evidence_coverage': decision.coverage_percent,
        'confidence': decision.confidence_label,
    }

    if not decision.is_published:
        # The whole payload, for 467 of 467 organisations today.
        payload['evidence_note'] = {
            'headline': PENDING_HEADLINE,
            'detail': PENDING_DETAIL,
        }
        payload['evidence_gaps'] = _gaps(decision)
        return Response(payload)

    payload['material_evidence'] = _material_evidence(profile)
    payload['decision_risks'] = _decision_risks(profile)
    payload['ethics'] = _ethics(profile)
    payload['financing_readiness'] = _financing(profile)
    payload['shariah'] = _shariah(profile)
    payload['evidence_gaps'] = _gaps(decision)
    return Response(payload)


def _gaps(decision) -> dict:
    """
    What is missing, and what would close it.

    Available whether or not the score publishes — for an organisation with no
    assessment this IS the useful content, and it is the one thing a reader can
    act on.
    """
    coverage = decision.coverage
    return {
        'covered': coverage.numerator,
        'required': coverage.denominator,
        'missing': sorted(coverage.missing),
        'unevidenced': sorted(coverage.unevidenced),
        'reasons': list(decision.reasons),
    }


def _material_evidence(profile) -> list:
    """
    The six pillars, each with the value the composite actually used.

    `known()` rather than a bare read: an unassessed pillar is None, and None
    must travel as null rather than as a zero the client would render as a bar
    at the floor.
    """
    return [
        {'key': key, 'label': label, 'value': known(getattr(profile, key, None))}
        for key, label in (
            ('public_benefit_score', 'Public benefit'),
            ('environmental_responsibility_score', 'Environmental stewardship'),
            ('modernization_score', 'Responsible modernisation'),
            ('transparency_anti_corruption_score', 'Transparency and anti-corruption'),
            ('ethical_alignment_score', 'Ethical alignment'),
            ('harm_penalty', 'Harm penalty'),
        )
    ]


def _decision_risks(profile) -> dict:
    """QDF decision integrity, plus recorded controversies."""
    from qdf.scoring import get_or_compute as qdf_compute

    assessment = qdf_compute(profile)
    controversies = [
        {
            'title': c.title,
            'category': c.category,
            'severity': c.severity,
            'status': c.status,
            'reported_date': c.reported_date.isoformat() if c.reported_date else None,
        }
        # Demo rows never leave. See the module docstring.
        for c in profile.controversies.filter(is_demo=False)
    ]

    if assessment is None:
        return {'integrity': None, 'controversies': controversies}

    return {
        'integrity': {
            'score': known(assessment.decision_integrity_score),
            'risk_level': assessment.risk_level,
            'verdict': assessment.verdict,
            'evidence_status': assessment.evidence_status,
            'red_line_breached': assessment.red_line_breached,
        },
        'controversies': controversies,
    }


def _ethics(profile) -> dict | None:
    """Ethics master scores. `ethics.scoring` is a PRODUCTION engine."""
    from ethics.scoring import get_or_compute

    ethics = get_or_compute(profile)
    if ethics is None:
        return None
    return {
        'net_ethical_impact': known(ethics.net_ethical_impact),
        'transition_stewardship': known(ethics.transition_stewardship),
        'regenerative_value': known(ethics.regenerative_value),
        'total_benefit_score': known(ethics.total_benefit_score),
        'total_harm_score': known(ethics.total_harm_score),
        'key_harms': list(ethics.key_harms or []),
        'key_benefits': list(ethics.key_benefits or []),
        'next_best_actions': list(ethics.next_best_actions or []),
        # Its own confidence notion, named so it cannot be mistaken for
        # companies.confidence — they measure different things.
        'engine_confidence': ethics.data_confidence,
        'analyst_reviewed': bool(ethics.analyst_reviewed),
        'formula_version': ethics.formula_version,
    }


def _financing(profile) -> dict | None:
    """
    Financing readiness — what an organisation could meet.

    NOT the matched-pathway shortlist, which names instruments and moved behind
    sign-in. See the module docstring.
    """
    from financing.matching import get_or_compute as fin_compute

    fin = fin_compute(profile)
    if fin is None:
        return None
    return {
        'readiness': known(fin.financing_readiness),
        'tier': fin.readiness_tier,
        'evidence_completeness': known(fin.evidence_completeness),
        'dimensions': {
            'modernisation': known(fin.modernization_readiness),
            'transparency': known(fin.transparency_readiness),
            'climate': known(fin.climate_readiness),
            'governance': known(fin.governance_readiness),
        },
        'missing_requirements': list(fin.missing_requirements or []),
        'next_actions': list(fin.next_actions or []),
        'engine_confidence': fin.confidence,
        'analyst_reviewed': bool(fin.analyst_reviewed),
    }


#: Travels WITH the result, in the same object, never as a page footnote.
#:
#: The panel this replaces carried the same words and the audit kept the screen
#: on that condition. A methodology result separated from the statement that it
#: is not a ruling becomes, to a reader, a ruling.
SHARIAH_DISCLAIMER = (
    'A named, versioned business-activity and financial-ratio eligibility '
    'screen. Not a religious ruling, a fatwa, or a certification.'
)


def _shariah(profile) -> dict | None:
    from company_intelligence.services.shariah_screening import latest_screen_for

    screen = latest_screen_for(profile)
    # Demo screens never leave.
    if screen is None or getattr(screen, 'is_demo', False):
        return None
    return {
        'disclaimer': SHARIAH_DISCLAIMER,
        'methodology': str(screen.methodology) if screen.methodology else '',
        'overall_result': screen.overall_result,
        'business_activity_result': screen.business_activity_result,
        'business_activity_reason': screen.business_activity_reason,
        'financial_ratio_result': screen.financial_ratio_result,
        'data_completeness_pct': known(screen.data_completeness_pct),
        'review_status': screen.review_status,
        'screened_at': screen.screened_at.isoformat() if screen.screened_at else None,
    }
