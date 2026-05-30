"""
api/views.py — EcoIQ REST API v1 endpoints.

All endpoints require a valid API key unless marked as public.
Public endpoints return a subset of data.

Endpoints:
    GET  /api/v1/                            API info + rate limit status
    GET  /api/v1/companies/                  Paginated list with search + filters
    GET  /api/v1/companies/<slug>/           Full company profile
    GET  /api/v1/companies/<slug>/scores/    Scores only (lightweight)
    GET  /api/v1/companies/<slug>/harm-signals/
    GET  /api/v1/leaderboard/               Top-N ranked companies
    GET  /api/v1/countries/                  Country list
    GET  /api/v1/countries/<slug>/           Country detail
    GET  /api/v1/search/                     Cross-entity search
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Avg
from django.shortcuts import get_object_or_404

from api.authentication import APIKeyAuthentication
from api.permissions import IsAPIKeyAuthenticated, IsPublicOrAPIKey
from api.serializers import (
    CompanyListSerializer,
    CompanyDetailSerializer,
    CompanyScoresSerializer,
    HarmSignalSerializer,
    LeaderboardSerializer,
    CountryListSerializer,
    CountryDetailSerializer,
)
from league.models import Company


# ── Pagination ────────────────────────────────────────────────────────────────

class StandardPagination(PageNumberPagination):
    page_size             = 50
    page_size_query_param = 'page_size'
    max_page_size         = 200


# ── API Root ──────────────────────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([])  # public
def api_root(request):
    """API info and rate-limit status for the authenticated key."""
    rate_info = {}
    if request.auth:
        key = request.auth
        rate_info = {
            'key_prefix': key.prefix,
            'tier':       key.tier,
            'total_requests_used': key.total_requests,
        }

    return Response({
        'api':     'EcoIQ Intelligence API',
        'version': 'v1',
        'docs':    request.build_absolute_uri('/api/'),
        'auth':    'Include your key via X-API-Key header or Authorization: Bearer <key>',
        'endpoints': {
            'companies':  request.build_absolute_uri('/api/v1/companies/'),
            'leaderboard': request.build_absolute_uri('/api/v1/leaderboard/'),
            'countries':  request.build_absolute_uri('/api/v1/countries/'),
            'search':     request.build_absolute_uri('/api/v1/search/'),
        },
        'rate_limit': rate_info or 'Unauthenticated — 20 requests/day. Get a key at ecoiq.uk/pricing/',
    })


# ── Companies ─────────────────────────────────────────────────────────────────

class CompanyListView(ListAPIView):
    """
    GET /api/v1/companies/

    Query params:
        q          — name search
        sector     — filter by sector slug
        country    — filter by country name
        min_score  — minimum ecoiq_score
        max_score  — maximum ecoiq_score
        cluster    — filter by ml_cluster_label
        anomaly    — 'true' to show only anomalies
        page       — pagination
        page_size  — items per page (max 200)
    """
    serializer_class   = CompanyListSerializer
    pagination_class   = StandardPagination
    authentication_classes = [APIKeyAuthentication]
    permission_classes     = [IsPublicOrAPIKey]

    def get_queryset(self):
        qs = Company.objects.select_related('profile').order_by('rank', '-ecoiq_score')

        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

        sector = self.request.query_params.get('sector')
        if sector:
            qs = qs.filter(sector__iexact=sector)

        country = self.request.query_params.get('country')
        if country:
            qs = qs.filter(country__icontains=country)

        min_score = self.request.query_params.get('min_score')
        if min_score:
            try:
                qs = qs.filter(ecoiq_score__gte=float(min_score))
            except ValueError:
                pass

        max_score = self.request.query_params.get('max_score')
        if max_score:
            try:
                qs = qs.filter(ecoiq_score__lte=float(max_score))
            except ValueError:
                pass

        cluster = self.request.query_params.get('cluster')
        if cluster:
            qs = qs.filter(ml_cluster_label__icontains=cluster)

        if self.request.query_params.get('anomaly', '').lower() == 'true':
            qs = qs.filter(is_anomaly=True)

        return qs


class CompanyDetailView(RetrieveAPIView):
    """GET /api/v1/companies/<slug>/"""
    serializer_class   = CompanyDetailSerializer
    lookup_field       = 'slug'
    authentication_classes = [APIKeyAuthentication]
    permission_classes     = [IsPublicOrAPIKey]

    def get_queryset(self):
        return Company.objects.select_related('profile').prefetch_related('history')


class CompanyScoresView(RetrieveAPIView):
    """GET /api/v1/companies/<slug>/scores/"""
    serializer_class   = CompanyScoresSerializer
    lookup_field       = 'slug'
    authentication_classes = [APIKeyAuthentication]
    permission_classes     = [IsPublicOrAPIKey]

    def get_queryset(self):
        return Company.objects.select_related('profile')


class CompanyHarmSignalsView(APIView):
    """GET /api/v1/companies/<slug>/harm-signals/"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes     = [IsPublicOrAPIKey]

    def get(self, request, slug):
        company = get_object_or_404(
            Company.objects.select_related('profile'), slug=slug
        )
        try:
            from companies.views import _get_harm_signals
            signals = _get_harm_signals(company.profile)
        except Exception:
            signals = []

        return Response({
            'company':    company.name,
            'slug':       slug,
            'harm_signals': signals,
            'harm_penalty': getattr(company.profile, 'harm_penalty', 0) if hasattr(company, 'profile') else 0,
        })


# ── Leaderboard ───────────────────────────────────────────────────────────────

class LeaderboardView(ListAPIView):
    """
    GET /api/v1/leaderboard/

    Query params:
        top     — number of companies (default 100, max 500)
        sector  — filter by sector
    """
    serializer_class   = LeaderboardSerializer
    authentication_classes = [APIKeyAuthentication]
    permission_classes     = [IsPublicOrAPIKey]

    def get_queryset(self):
        top = min(int(self.request.query_params.get('top', 100)), 500)
        qs  = Company.objects.filter(ecoiq_score__gt=0).order_by('rank', '-ecoiq_score')

        sector = self.request.query_params.get('sector')
        if sector:
            qs = qs.filter(sector__iexact=sector)

        return qs[:top]

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response({
            'count':       len(serializer.data),
            'leaderboard': serializer.data,
        })


# ── Countries ─────────────────────────────────────────────────────────────────

class CountryListView(APIView):
    """GET /api/v1/countries/"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes     = [IsPublicOrAPIKey]

    def get(self, request):
        try:
            from countries.models import CountryProfile
            profiles = CountryProfile.objects.all().order_by('name')
            results  = []
            for p in profiles:
                companies = Company.objects.filter(
                    country__icontains=p.name
                ).filter(ecoiq_score__gt=0)
                avg_score = companies.aggregate(a=Avg('ecoiq_score'))['a']
                results.append({
                    'slug':    p.slug,
                    'name':    p.name,
                    'region':  getattr(p, 'region', ''),
                    'company_count':   companies.count(),
                    'avg_ecoiq_score': round(float(avg_score), 1) if avg_score else None,
                })
            return Response({'count': len(results), 'countries': results})
        except Exception as exc:
            return Response({'error': str(exc)}, status=500)


class CountryDetailView(APIView):
    """GET /api/v1/countries/<slug>/"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes     = [IsPublicOrAPIKey]

    def get(self, request, slug):
        try:
            from countries.models import CountryProfile
            profile = get_object_or_404(CountryProfile, slug=slug)
        except Exception:
            return Response({'error': 'Countries not configured.'}, status=404)

        companies = Company.objects.filter(
            country__icontains=profile.name,
            ecoiq_score__gt=0,
        ).order_by('rank', '-ecoiq_score')[:10]

        avg_score = Company.objects.filter(
            country__icontains=profile.name, ecoiq_score__gt=0
        ).aggregate(a=Avg('ecoiq_score'))['a']

        top_cos_data = CompanyListSerializer(companies, many=True, context={'request': request}).data

        return Response({
            'slug':          profile.slug,
            'name':          profile.name,
            'region':        getattr(profile, 'region', ''),
            'ai_summary':    getattr(profile, 'ai_summary', ''),
            'ai_risk_notes': getattr(profile, 'ai_risk_notes', ''),
            'ecoiq_national_index': round(float(avg_score), 1) if avg_score else None,
            'company_count': companies.count(),
            'top_companies': top_cos_data,
        })


# ── Search ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def search(request):
    """
    GET /api/v1/search/?q=<query>

    Searches companies by name, description, sector, country.
    Returns top 20 results.
    """
    q = request.query_params.get('q', '').strip()
    if not q:
        return Response({'error': 'q parameter required'}, status=400)

    companies = Company.objects.filter(
        Q(name__icontains=q)
        | Q(slug__icontains=q)
        | Q(description__icontains=q)
        | Q(sector__icontains=q)
        | Q(country__icontains=q)
    ).select_related('profile').order_by('rank', '-ecoiq_score')[:20]

    serializer = CompanyListSerializer(companies, many=True, context={'request': request})
    return Response({
        'query':   q,
        'count':   len(serializer.data),
        'results': serializer.data,
    })
