"""
api/commercial_views.py — the new PART 4 endpoints added on top of the
pre-existing /api/v1/ surface (api/views.py). Kept in a separate module so
the diff against the existing 1000+ line views.py stays reviewable.

Every endpoint here:
  - accepts EITHER a B2B api.authentication.APIKeyAuthentication credential
    OR a first-party mobile_auth.authentication.MobileTokenAuthentication
    session (added when the EcoIQ mobile/desktop app was built) — the same
    data, gated the same way, regardless of which caller it is
  - reuses api.permissions (IsPublicOrAPIKey / RequiresFeature) for gating;
    RequiresFeature resolves entitlement from an APIKey's plan OR, for a
    logged-in app user, that user's own entitlement (has_entitlement) —
    see api/permissions.py
  - only ever reads PUBLISHED data (InvestmentRelevanceReport.status='published',
    CompanyProfile.status in public/verified) — draft/unpublished intelligence
    is never reachable through the API, regardless of caller entitlement
  - returns a `_meta` block (generated/updated time, methodology version,
    confidence, source status, delay indicator) per PART 4
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import APIKeyAuthentication
from api.logging_mixin import APIRequestLoggingMixin
from api.models import APIKey
from api.permissions import IsAPIKeyAuthenticated, IsPublicOrAPIKey, RequiresFeature
from mobile_auth.authentication import MobileTokenAuthentication
from companies.investment_report import EVIDENCE_TYPE_CHOICES
from companies.models import CompanyProfile, InvestmentRelevanceReport
from companies.screening import compute_ethical_screening
from league.models import SECTOR_CHOICES, Company

STALE_AFTER_HOURS = 48


def _build_meta(*, generated_at=None, methodology_version='v1', confidence='medium',
                 source_status='ok', is_delayed=False):
    return {
        'generated_at': (generated_at or timezone.now()).isoformat(),
        'methodology_version': methodology_version,
        'confidence': confidence,
        'source_status': source_status,
        'possible_delay': is_delayed,
    }


def _get_public_profile_or_404(slug):
    company = get_object_or_404(Company, slug=slug)
    profile = get_object_or_404(CompanyProfile, company=company, status__in=('public', 'verified'))
    return company, profile


def _latest_published_report(profile):
    return profile.investment_reports.filter(status='published').order_by('-version').first()


# ── Risks (top environmental risks + positive signals) ─────────────────────

class CompanyRisksView(APIRequestLoggingMixin, APIView):
    """
    GET /api/v1/companies/<slug>/risks/

    Top environmental risks + positive stewardship signals from the latest
    PUBLISHED Investment Relevance Report. Falls back to an empty, clearly
    labelled result when no published report exists — never fabricated.
    """
    authentication_classes = [MobileTokenAuthentication, APIKeyAuthentication]
    permission_classes = [IsPublicOrAPIKey]

    def get(self, request, slug):
        company, profile = _get_public_profile_or_404(slug)
        report = _latest_published_report(profile)

        if not report:
            return Response({
                'company': slug,
                'name': company.name,
                'key_risks': [],
                'positive_signals': [],
                'note': 'No published EcoIQ Investment Relevance Report exists for this company yet.',
                '_meta': _build_meta(confidence='low', source_status='no_report'),
            })

        return Response({
            'company': slug,
            'name': company.name,
            'classification': report.classification,
            'key_risks': report.content.get('key_risks', []),
            'positive_signals': report.content.get('positive_signals', []),
            '_meta': _build_meta(
                generated_at=report.published_at or report.generated_at,
                methodology_version=report.methodology_version,
                confidence='high' if report.prohibited_language_flags == [] else 'medium',
                is_delayed=(timezone.now() - (report.published_at or report.generated_at)).total_seconds() / 3600 > STALE_AFTER_HOURS,
            ),
        })


# ── Evidence (entitlement-gated) ────────────────────────────────────────────

class CompanyEvidenceView(APIRequestLoggingMixin, APIView):
    """
    GET /api/v1/companies/<slug>/evidence/

    Cited sources + evidence-type breakdown from the latest published
    report. Requires the 'api_evidence_access' entitlement — a customer on
    the free Explorer API tier does not see this (per PART 4: "Respect
    ... evidence-access rights").
    """
    authentication_classes = [MobileTokenAuthentication, APIKeyAuthentication]
    permission_classes = [RequiresFeature('api_evidence_access')]

    def get(self, request, slug):
        company, profile = _get_public_profile_or_404(slug)
        sources = list(profile.cited_sources.all()[:20])
        report = _latest_published_report(profile)

        evidence_entries = []
        if report:
            for entry in (report.content.get('key_risks', []) + report.content.get('positive_signals', [])):
                evidence_entries.append({
                    'evidence_type': entry.get('evidence_type'),
                    'evidence_detail': entry.get('evidence_detail'),
                    'confidence': entry.get('confidence'),
                })

        return Response({
            'company': slug,
            'name': company.name,
            'cited_sources': [
                {'title': s.title, 'url': s.url, 'source_type': s.source_type,
                 'date_accessed': s.date_accessed.isoformat() if s.date_accessed else None}
                for s in sources
            ],
            'evidence_entries': evidence_entries,
            'evidence_type_legend': dict(EVIDENCE_TYPE_CHOICES),
            '_meta': _build_meta(
                generated_at=report.published_at if report else None,
                confidence='high' if sources else 'low',
            ),
        })


# ── Ethical screening ────────────────────────────────────────────────────────

class CompanyEthicalScreeningView(APIRequestLoggingMixin, APIView):
    """GET /api/v1/companies/<slug>/ethical-screening/ — passed | review_required | failed | insufficient_evidence."""
    authentication_classes = [MobileTokenAuthentication, APIKeyAuthentication]
    permission_classes = [IsPublicOrAPIKey]

    def get(self, request, slug):
        company, profile = _get_public_profile_or_404(slug)
        result = compute_ethical_screening(profile)
        return Response({
            'company': slug,
            'name': company.name,
            **result,
            '_meta': _build_meta(
                generated_at=profile.updated_at,
                methodology_version=result['methodology_version'],
                confidence=result['confidence'],
            ),
        })


# ── Islamic screening ────────────────────────────────────────────────────────

class CompanyIslamicScreeningView(APIRequestLoggingMixin, APIView):
    """
    GET /api/v1/companies/<slug>/islamic-screening/

    Reuses the existing QDF (Quranic Decision Filter) engine — NOT a new
    Islamic-finance screening model. QDF's own output already carries the
    "not a fatwa" disclaimer; this endpoint forwards it verbatim rather than
    softening or removing it.
    """
    authentication_classes = [MobileTokenAuthentication, APIKeyAuthentication]
    permission_classes = [IsPublicOrAPIKey]

    def get(self, request, slug):
        company, profile = _get_public_profile_or_404(slug)
        from qdf.scoring import get_or_compute
        assessment = get_or_compute(profile)  # a qdf.models.DecisionAssessment instance, or None on error

        if assessment is None:
            return Response({
                'company': slug, 'name': company.name,
                'status': 'insufficient_evidence',
                'note': 'The Qur\'anic Decision Filter could not be computed for this company.',
                '_meta': _build_meta(confidence='low', source_status='error'),
            })

        return Response({
            'company': slug,
            'name': company.name,
            'decision_integrity_score': assessment.decision_integrity_score,
            'risk_level': assessment.risk_level,
            'verdict': assessment.verdict,
            'evidence_status': assessment.evidence_status,
            'confidence_pct': round(assessment.confidence * 100, 1),
            'red_line_triggered': assessment.red_line_breached,
            'summary': assessment.rizq_without_zulm_summary,
            'disclaimer': (
                'This is EcoIQ\'s own AI-assisted Qur\'anic Decision Filter methodology, inspired by Qur\'anic '
                'decision principles. It is NOT a fatwa, tafsir, formal Shariah ruling, or output of an '
                'authorised religious governance process. Religious framing is non-authoritative pending '
                'qualified scholarly review.'
            ),
            '_meta': _build_meta(
                generated_at=assessment.last_computed,
                confidence='low' if assessment.confidence < 0.5 else 'medium',
                source_status='indicative',
            ),
        })


# ── Investment relevance ─────────────────────────────────────────────────────

class CompanyInvestmentRelevanceView(APIRequestLoggingMixin, APIView):
    """
    GET /api/v1/companies/<slug>/investment-relevance/

    Classification + executive summary are public. The full risk/signal
    breakdown requires any valid API key (not just an anonymous caller) —
    a lighter gate than /evidence/, matching PART 1's "latest investment-
    relevance classification" as a baseline Data API feature.
    """
    authentication_classes = [MobileTokenAuthentication, APIKeyAuthentication]
    permission_classes = [IsPublicOrAPIKey]

    def get(self, request, slug):
        company, profile = _get_public_profile_or_404(slug)
        report = _latest_published_report(profile)

        if not report:
            return Response({
                'company': slug, 'name': company.name,
                'classification': 'insufficient_evidence',
                'note': 'No published EcoIQ Investment Relevance Report exists for this company yet.',
                '_meta': _build_meta(confidence='low', source_status='no_report'),
            })

        payload = {
            'company': slug,
            'name': company.name,
            'classification': report.classification,
            'executive_assessment': report.content.get('executive_assessment'),
            'data_confidence': report.content.get('data_confidence'),
            'report_version': report.version,
            '_meta': _build_meta(
                generated_at=report.published_at or report.generated_at,
                methodology_version=report.methodology_version,
                is_delayed=(timezone.now() - (report.published_at or report.generated_at)).total_seconds() / 3600 > STALE_AFTER_HOURS,
            ),
        }

        has_key = isinstance(request.auth, APIKey)
        if has_key:
            payload['key_risks'] = report.content.get('key_risks', [])
            payload['positive_signals'] = report.content.get('positive_signals', [])
            payload['sector_relative_context'] = report.content.get('sector_relative_context')
            payload['due_diligence_questions'] = report.content.get('due_diligence_questions', [])
        else:
            payload['note'] = 'Full risk/signal breakdown requires an API key. Get one at /products/.'

        return Response(payload)


# ── Sector benchmark ─────────────────────────────────────────────────────────

class SectorBenchmarkView(APIRequestLoggingMixin, APIView):
    """GET /api/v1/sectors/<slug>/benchmark/ — average scores + exposure distribution for a sector."""
    authentication_classes = [MobileTokenAuthentication, APIKeyAuthentication]
    permission_classes = [IsPublicOrAPIKey]

    def get(self, request, slug):
        valid_sectors = dict(SECTOR_CHOICES)
        if slug not in valid_sectors:
            return Response({'error': f'Unknown sector "{slug}". Valid: {list(valid_sectors)}'},
                             status=status.HTTP_404_NOT_FOUND)

        from django.db.models import Avg
        companies = Company.objects.filter(sector=slug)
        agg = companies.aggregate(avg_score=Avg('ecoiq_score'))

        profiles = CompanyProfile.objects.filter(
            company__sector=slug, status__in=('public', 'verified'),
        ).select_related('company')

        distribution = {'lower_exposure': 0, 'moderate_exposure': 0, 'elevated_exposure': 0,
                         'high_exposure': 0, 'insufficient_evidence': 0}
        for profile in profiles:
            report = _latest_published_report(profile)
            bucket = report.classification if report else 'insufficient_evidence'
            distribution[bucket] = distribution.get(bucket, 0) + 1

        return Response({
            'sector': slug,
            'sector_name': valid_sectors[slug],
            'company_count': companies.count(),
            'average_ecoiq_score': round(agg['avg_score'], 1) if agg['avg_score'] is not None else None,
            'investment_relevance_distribution': distribution,
            '_meta': _build_meta(confidence='medium' if companies.count() >= 3 else 'low'),
        })


# ── Methodologies ─────────────────────────────────────────────────────────────

class MethodologiesView(APIRequestLoggingMixin, APIView):
    """GET /api/v1/methodologies/ — versioned info on every deterministic methodology EcoIQ uses."""
    authentication_classes = [MobileTokenAuthentication, APIKeyAuthentication]
    permission_classes = [IsPublicOrAPIKey]

    def get(self, request):
        from companies.screening import METHODOLOGY_VERSION as ETHICAL_SCREENING_VERSION
        from investor_portfolio.methodology import METHODOLOGY_VERSION as PORTFOLIO_METHODOLOGY_VERSION

        return Response({
            'methodologies': [
                {
                    'key': 'ecoiq_score', 'name': 'EcoIQ Company Score', 'version': 'v1',
                    'summary': 'Weighted composite: Pollution 35%, Reduction 25%, Investment 20%, '
                               'Transparency 10%, Community 10%.',
                },
                {
                    'key': 'investment_relevance', 'name': 'EcoIQ Investment Relevance Report', 'version': 'v1',
                    'summary': 'AI-generated report grounded strictly in stored EcoIQ evidence; classification is '
                               'one of lower/moderate/elevated/high identified exposure, or insufficient evidence. '
                               'Not investment advice.',
                },
                {
                    'key': 'ethical_screening', 'name': 'EcoIQ Ethical Screening', 'version': ETHICAL_SCREENING_VERSION,
                    'summary': 'Deterministic rule table over harm penalty, controversy risk, and pollution level. '
                               'passed / review_required / failed / insufficient_evidence.',
                },
                {
                    'key': 'islamic_screening', 'name': 'EcoIQ Qur\'anic Decision Filter', 'version': 'v1',
                    'summary': 'AI-assisted governance lens inspired by Qur\'anic decision principles. '
                               'NOT a fatwa or formal Shariah ruling.',
                },
                {
                    'key': 'portfolio_exposure', 'name': 'EcoIQ Portfolio Exposure', 'version': PORTFOLIO_METHODOLOGY_VERSION,
                    'summary': 'Deterministic weighted average of classification risk scores across '
                               'analytics-included holdings with a published report.',
                },
            ],
            '_meta': _build_meta(confidence='high', source_status='static'),
        })


# ── Controversies ─────────────────────────────────────────────────────────────

class ControversiesPagination(PageNumberPagination):
    page_size = 25
    max_page_size = 100


class ControversiesView(APIRequestLoggingMixin, APIView):
    """GET /api/v1/controversies/ — companies with elevated recorded controversy/harm signals."""
    authentication_classes = [MobileTokenAuthentication, APIKeyAuthentication]
    permission_classes = [IsPublicOrAPIKey]

    def get(self, request):
        profiles = (CompanyProfile.objects
                    .filter(status__in=('public', 'verified'))
                    .filter(controversy_risk_score__gte=55)
                    .select_related('company')
                    .order_by('-controversy_risk_score'))

        paginator = ControversiesPagination()
        page = paginator.paginate_queryset(profiles, request)
        results = [
            {
                'company': p.company.slug,
                'name': p.company.name,
                'controversy_risk_score': p.controversy_risk_score,
                'harm_penalty': p.harm_penalty,
                'pollution_level': p.pollution_level,
            }
            for p in page
        ]
        response = paginator.get_paginated_response(results)
        response.data['_meta'] = _build_meta(confidence='medium')
        return response
