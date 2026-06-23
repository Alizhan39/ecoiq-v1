"""
EcoIQ Quranic Decision Filter — REST API v1.

Mounted at /api/qdf/ from the root URLconf.

    GET  /api/qdf/questions/                 The 10 decision questions (framework)
    GET  /api/qdf/companies/<slug>/          Auto QDF assessment for a company
    POST /api/qdf/evaluate/                  Roll up explicit per-question scores
                                             for an ad-hoc subject (policy/investment/…)

GET endpoints are public. POST requires a valid API key.
"""
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes)
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from api.authentication import APIKeyAuthentication
from api.permissions import IsPublicOrAPIKey, IsAPIKeyAuthenticated

DISCLAIMER = (
    'EcoIQ Quranic Decision Filter is an AI-assisted governance lens inspired by '
    'Qur’anic decision principles. It is NOT fatwa, tafsir, a Shariah ruling, '
    'or investment advice. Scores are indicative and evidence-gated; religious '
    'framing is pending qualified scholarly review.'
)


def _question_payload(q):
    return {
        'key': q.key, 'order': q.order, 'arabic_term': q.arabic_term,
        'title': q.title_en, 'core_question': q.core_question,
        'weight': q.weight, 'is_red_line': q.is_red_line,
        'definition': q.definition, 'plain_english': q.plain_english,
        'evidence_required': q.evidence_required, 'red_flags': q.red_flags,
        'scoring_rubric': q.scoring_rubric, 'ai_prompt': q.ai_prompt,
        'low_score_actions': q.low_score_actions,
        'examples': {
            'company': q.example_company,
            'policy': q.example_policy,
            'investment': q.example_investment,
        },
    }


def _assessment_payload(assessment):
    return {
        'subject': {
            'type': assessment.subject_type,
            'name': assessment.subject_name,
            'ref': assessment.subject_ref,
        },
        'decision_integrity_score': round(assessment.decision_integrity_score, 1),
        'integrity_band': assessment.integrity_band,
        'risk_level': assessment.risk_level,
        'verdict': assessment.verdict,
        'verdict_display': assessment.verdict_display,
        'evidence_status': assessment.evidence_status,
        'confidence': assessment.confidence,
        'red_line_breached': assessment.red_line_breached,
        'rizq_without_zulm': assessment.rizq_without_zulm_summary,
        'questions': [
            {
                'key': qs.question.key,
                'arabic_term': qs.question.arabic_term,
                'title': qs.question.title_en,
                'core_question': qs.question.core_question,
                'score': round(qs.score, 1),
                'evidence_status': qs.evidence_status,
                'rationale': qs.rationale,
                'red_flags_triggered': qs.red_flags_triggered,
                'recommended_actions': qs.recommended_actions,
            }
            for qs in assessment.ordered_scores
        ],
    }


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def qdf_questions(request):
    """GET /api/qdf/questions/ — the 10 Quranic Decision Filter questions."""
    from qdf.scoring import ensure_questions
    questions = ensure_questions()
    return Response({
        'thesis': 'Create rizq without zulm.',
        'count': questions.count(),
        'questions': [_question_payload(q) for q in questions],
        '_note': DISCLAIMER,
    })


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def qdf_company(request, slug):
    """GET /api/qdf/companies/<slug>/ — auto QDF assessment for a company."""
    from league.models import Company
    from qdf.scoring import get_or_compute

    company = get_object_or_404(Company.objects.select_related('profile'), slug=slug)
    try:
        profile = company.profile
    except Exception:
        return Response({'error': 'No profile found for this company.'},
                        status=status.HTTP_404_NOT_FOUND)

    assessment = get_or_compute(profile)
    if assessment is None:
        return Response({'error': 'QDF assessment unavailable.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    payload = _assessment_payload(assessment)
    payload['company'] = {'slug': slug, 'name': company.name,
                          'country': company.country, 'sector': company.sector}
    payload['_note'] = DISCLAIMER
    return Response(payload)


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def qdf_decision_engine(request, slug):
    """
    GET /api/qdf/companies/<slug>/engine/ — full Decision Engine output:
    ranked action queue (decision cards) + roadmap trajectory.
    """
    from league.models import Company
    from qdf.scoring import get_or_compute
    from qdf import engine

    company = get_object_or_404(Company.objects.select_related('profile'), slug=slug)
    try:
        profile = company.profile
    except Exception:
        return Response({'error': 'No profile found for this company.'},
                        status=status.HTTP_404_NOT_FOUND)
    assessment = get_or_compute(profile)
    if assessment is None:
        return Response({'error': 'QDF assessment unavailable.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    roadmap = engine.generate_roadmap(assessment)
    return Response({
        'company': {'slug': slug, 'name': company.name},
        'decision_integrity_score': round(assessment.decision_integrity_score, 1),
        'verdict': assessment.verdict,
        'rizq_without_zulm': assessment.rizq_without_zulm_summary,
        'action_queue': engine.build_action_queue(assessment),
        'roadmap': {
            'baseline_integrity': roadmap['baseline_integrity'],
            'target_integrity':   roadmap['target_integrity'],
            'total_uplift':       roadmap['total_uplift'],
            'card_count':         roadmap['card_count'],
            'trajectory': [
                {k: t[k] for k in ('horizon', 'horizon_label', 'card_count',
                                   'projected_integrity', 'projected_verdict',
                                   'projected_risk')}
                for t in roadmap['trajectory']
            ],
        },
        '_note': DISCLAIMER,
    })


@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def qdf_scenario(request, slug):
    """
    POST /api/qdf/companies/<slug>/scenario/ — re-score a company under
    hypothetical per-question overrides. Body: {"overrides": {"adl": 2, ...}}.
    """
    from league.models import Company
    from qdf.scoring import get_or_compute
    from qdf import engine

    company = get_object_or_404(Company.objects.select_related('profile'), slug=slug)
    try:
        profile = company.profile
    except Exception:
        return Response({'error': 'No profile found for this company.'},
                        status=status.HTTP_404_NOT_FOUND)
    assessment = get_or_compute(profile)
    if assessment is None:
        return Response({'error': 'QDF assessment unavailable.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    overrides = (request.data or {}).get('overrides') or {}
    if not isinstance(overrides, dict):
        return Response({'error': '"overrides" must be an object of key→0–10.'},
                        status=status.HTTP_400_BAD_REQUEST)
    projected = engine.simulate_scenario(assessment, overrides)
    return Response({
        'company': {'slug': slug, 'name': company.name},
        'baseline_integrity': projected['baseline'],
        'projected_integrity': projected['overall'],
        'delta': projected['delta'],
        'verdict': projected['verdict'],
        'risk_level': projected['risk'],
        'red_line_breached': projected['red_line'],
        'rizq_without_zulm': projected['summary'],
        '_note': DISCLAIMER,
    })


@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAPIKeyAuthenticated])
def qdf_evaluate(request):
    """
    POST /api/qdf/evaluate/ — roll up explicit per-question scores for an ad-hoc
    subject (policy / investment / infrastructure / government decision).

    Body: {
        "subject_type": "policy",
        "subject_name": "Carbon Tax Bill 2026",
        "scores": { "niyyah": 8, "halal": 9, "adl": 4, ... },   # 0–10, missing → 5
        "evidence_status": "partial",     # optional
        "confidence": 0.6                 # optional
    }
    """
    from qdf.scoring import compute_from_scores
    from qdf.models import SUBJECT_TYPE_CHOICES, EVIDENCE_STATUS_CHOICES

    data = request.data or {}
    scores = data.get('scores') or {}
    if not isinstance(scores, dict):
        return Response({'error': '"scores" must be an object of key→0–10.'},
                        status=status.HTTP_400_BAD_REQUEST)

    # Validate ranges
    clean = {}
    for k, v in scores.items():
        try:
            clean[str(k)] = float(v)
        except (TypeError, ValueError):
            return Response({'error': f'Score for "{k}" must be numeric.'},
                            status=status.HTTP_400_BAD_REQUEST)

    subject_type = data.get('subject_type', 'policy')
    if subject_type not in dict(SUBJECT_TYPE_CHOICES):
        return Response({'error': f'subject_type must be one of '
                                  f'{list(dict(SUBJECT_TYPE_CHOICES))}.'},
                        status=status.HTTP_400_BAD_REQUEST)
    evidence_status = data.get('evidence_status', 'unverified')
    if evidence_status not in dict(EVIDENCE_STATUS_CHOICES):
        evidence_status = 'unverified'
    subject_name = str(data.get('subject_name', 'Decision'))[:200]
    try:
        confidence = max(0.0, min(1.0, float(data.get('confidence', 0.5))))
    except (TypeError, ValueError):
        confidence = 0.5

    result = compute_from_scores(clean, subject_name=subject_name,
                                 evidence_status=evidence_status, confidence=confidence)
    return Response({
        'subject': {'type': subject_type, 'name': subject_name},
        'decision_integrity_score': result['overall'],
        'risk_level': result['risk'],
        'verdict': result['verdict'],
        'evidence_status': result['evidence_status'],
        'confidence': result['confidence'],
        'red_line_breached': result['red_line'],
        'rizq_without_zulm': result['summary'],
        'questions': result['questions'],
        '_note': DISCLAIMER,
    })
