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


# ── Semantic Search ───────────────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def semantic_search(request):
    """
    GET /api/v1/semantic-search/?q=<natural language query>&limit=10

    With pgvector + sentence-transformers installed:
      Performs true semantic vector search using all-MiniLM-L6-v2 embeddings.

    Without (free-tier / no ML dependencies):
      Falls back to keyword search across name, sector, country, search_text.

    Returns ranked company list with similarity score.
    """
    query = request.query_params.get('q', '').strip()
    limit = min(int(request.query_params.get('limit', 10)), 50)

    if not query or len(query) < 2:
        return Response({'error': 'q parameter required (min 2 chars)'}, status=400)

    method = 'text'
    companies = None

    # ── Try semantic vector search ────────────────────────────────────────────
    try:
        from sentence_transformers import SentenceTransformer
        from pgvector.django import L2Distance

        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = model.encode(query).tolist()

        companies = Company.objects.filter(
            embedding__isnull=False
        ).order_by(
            L2Distance('embedding', query_embedding)
        ).select_related('profile')[:limit]
        method = 'semantic'

    except Exception:
        pass

    # ── Keyword fallback ──────────────────────────────────────────────────────
    if companies is None:
        words = query.lower().split()[:6]
        q_filter = Q()
        for word in words:
            q_filter |= Q(name__icontains=word)
            q_filter |= Q(sector__icontains=word)
            q_filter |= Q(country__icontains=word)
            q_filter |= Q(description__icontains=word)
            q_filter |= Q(search_text__icontains=word)
        companies = (
            Company.objects
            .filter(q_filter)
            .select_related('profile')
            .order_by('rank', '-ecoiq_score')[:limit]
        )
        method = 'text'

    results = []
    for c in companies:
        profile = getattr(c, 'profile', None)
        results.append({
            'name':        c.name,
            'slug':        c.slug,
            'sector':      c.sector,
            'country':     c.country,
            'ecoiq_score': float(c.ecoiq_score),
            'tier':        profile.moral_label_display if profile else '',
            'url':         f'/companies/{c.slug}/',
        })

    return Response({
        'query':  query,
        'method': method,
        'count':  len(results),
        'results': results,
    })


# ── Responsible Finance Score ─────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def responsible_finance_detail(request, slug):
    """
    GET /api/v1/companies/<slug>/responsible-finance/

    Returns Responsible Finance alignment score and dimension breakdown.
    Based on five stewardship dimensions mapped to EcoIQ pillar scores.

    All scores are indicative. Not investment advice.
    """
    from django.shortcuts import get_object_or_404
    from companies.models import CompanyProfile
    from ml.responsible_finance import compute_responsible_finance_score

    company = get_object_or_404(Company, slug=slug)
    try:
        profile = company.profile
    except Exception:
        return Response({'error': 'No profile found for this company.'}, status=404)

    result = compute_responsible_finance_score(profile)

    return Response({
        'company':  slug,
        'name':     company.name,
        'ecoiq_total_score': float(profile.ecoiq_total_score or 0),
        **result,
        '_note': (
            'Responsible Finance scores are indicative. '
            'Based on EcoIQ pillar scores mapped to five stewardship dimensions. '
            'Not investment advice. Requires independent due diligence.'
        ),
    })


# ── Ethical Intelligence ──────────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def ethical_intelligence_score(request):
    """
    GET /api/v1/intelligence/ethical-score/?company=<slug>

    Returns a multi-dimensional ethical intelligence payload for a company.
    Combines public benefit, harm reduction, justice balance, stewardship,
    and evidence confidence into a single weighted score.

    All scores are AI-assisted and indicative. Not investment advice.
    """
    from companies.models import CompanyProfile
    from ml.ethics import compute_ethical_intelligence

    slug = request.query_params.get('company', '').strip()
    if not slug:
        return Response(
            {'error': 'company parameter required (company slug)'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    company = get_object_or_404(Company, slug=slug)
    try:
        profile = company.profile
    except Exception:
        return Response({'error': 'No profile found for this company.'}, status=404)

    result = compute_ethical_intelligence(profile)

    return Response({
        'company': slug,
        'name':    company.name,
        'country': company.country,
        'sector':  company.sector,
        **result,
    })


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def company_ethical_intelligence(request, slug):
    """
    GET /api/v1/companies/<slug>/ethical-intelligence/

    Full ethical intelligence breakdown for a specific company.
    Includes public benefit composite, harm reduction assessment,
    justice balance, stewardship score, and evidence confidence tier.
    """
    from companies.models import CompanyProfile
    from ml.ethics import compute_ethical_intelligence

    company = get_object_or_404(Company.objects.select_related('profile'), slug=slug)
    try:
        profile = company.profile
    except Exception:
        return Response({'error': 'No profile found for this company.'}, status=404)

    result = compute_ethical_intelligence(profile)

    return Response({
        'company': slug,
        'name':    company.name,
        'country': company.country,
        'sector':  company.sector,
        'ecoiq_total_score': float(getattr(profile, 'ecoiq_total_score', 0) or 0),
        'ethical_intelligence': result,
        '_note': (
            'EcoIQ Ethical Intelligence is AI-assisted and derived from public or seeded data. '
            'Not investment advice. Independent verification required for investment use.'
        ),
    })


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def country_ethical_intelligence(request, slug):
    """
    GET /api/v1/countries/<slug>/ethical-intelligence/

    Aggregate ethical intelligence for all public companies in a country.
    Returns sector breakdown and average sub-scores.
    """
    from companies.models import CompanyProfile
    from ml.ethics import compute_ethical_intelligence
    from django.db.models import Avg as DjAvg

    try:
        from countries.models import CountryProfile
        country_profile = get_object_or_404(CountryProfile, slug=slug)
        country_name    = country_profile.name
    except Exception:
        return Response({'error': 'Country not found.'}, status=404)

    profiles = (
        CompanyProfile.objects
        .filter(company__country__iexact=country_name, status__in=('public', 'verified'))
        .select_related('company')
    )

    if not profiles.exists():
        return Response({
            'country': slug,
            'name':    country_name,
            'message': 'No public profiles found for this country.',
            'company_count': 0,
        })

    all_results = [compute_ethical_intelligence(p) for p in profiles]

    avg_overall    = round(sum(r['overall_score']                for r in all_results) / len(all_results), 2)
    avg_pb         = round(sum(r['public_benefit']['score']      for r in all_results) / len(all_results), 2)
    avg_harm       = round(sum(r['harm_reduction']['harm_score'] for r in all_results) / len(all_results), 2)
    avg_stewardship= round(sum(r['stewardship']['score']         for r in all_results) / len(all_results), 2)
    avg_justice    = round(sum(r['justice_balance']['score']     for r in all_results) / len(all_results), 2)

    # Label distribution
    from collections import Counter
    label_dist = Counter(r['label'] for r in all_results)

    return Response({
        'country':       slug,
        'name':          country_name,
        'company_count': len(all_results),
        'aggregate': {
            'avg_ethical_intelligence_score': avg_overall,
            'avg_public_benefit':             avg_pb,
            'avg_harm_score':                 avg_harm,
            'avg_stewardship':                avg_stewardship,
            'avg_justice_balance':            avg_justice,
        },
        'label_distribution': dict(label_dist),
        '_note': (
            'Country aggregate is based on all public EcoIQ company profiles for this country. '
            'AI-assisted profiles are included; treat aggregate as indicative.'
        ),
    })


# ── Capital Integrity Score ───────────────────────────────────────────────────

@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def capital_integrity_score(request):
    """
    POST /api/v1/capital-integrity/

    Evaluate a financing instrument or transaction against the
    EcoIQ Capital Integrity Score (CIS).

    Returns: capital_integrity_score, label, dimension_scores,
             red_flags, positive_indicators, investor_note,
             islamic_finance_note, due_diligence_required,
             recommended_next_actions, confidence, methodology.

    Request body (JSON):
    {
        "name":                        "Green Bond 2026",        // optional
        "instrument_type":             "green_bond",             // REQUIRED
        "sector":                      "renewables",             // REQUIRED
        "country":                     "Kazakhstan",             // optional
        "use_of_proceeds_specificity": "specific",               // specific|general|vague|none
        "proceeds_amount_usd":         500000000,                // optional float
        "third_party_verified":        true,                     // bool
        "reporting_commitment":        "annual",                 // annual|bi-annual|none
        "community_consultation":      "standard",               // fpic_aligned|standard|minimal|none
        "ownership_disclosed":         true,                     // bool
        "procurement_framework":       "IFC",                    // IFC|EBRD|ADB|GBP|national|none
        "emission_reduction_target":   true,                     // bool
        "impact_measurement_plan":     true,                     // bool
        "baseline_data_available":     true,                     // bool
        "independent_verification_plan": true,                   // bool
        "additionality_demonstrated":  false,                    // bool
        "label_matches_project":       true,                     // bool
        "sector_excluded":             false,                    // bool
        "issuer_track_record":         "moderate",               // strong|moderate|weak|unknown
        "gender_inclusion":            false,                    // bool
        "local_employment_commitment": false,                    // bool
        "existing_ecoiq_profile":      "company-slug"           // optional slug
    }
    """
    body = request.data
    if not body:
        return Response(
            {
                'error': 'Request body required.',
                'hint':  (
                    'Send JSON with at minimum {"instrument_type": "green_bond", "sector": "renewables"} '
                    'to receive a baseline Capital Integrity assessment.'
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    instrument_type = str(body.get('instrument_type', '')).strip()
    sector          = str(body.get('sector', '')).strip()

    if not instrument_type:
        return Response(
            {
                'error': '"instrument_type" is required.',
                'hint':  'Accepted values: green_bond, sustainability_linked_loan, transition_bond, sukuk, blended_finance, project_finance, other.',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not sector:
        return Response(
            {'error': '"sector" is required. Provide a sector slug (e.g. "renewables", "energy", "oil_gas").'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from ml.ethics.capital_integrity import CapitalIntegrityInput, score_capital_integrity
        ci_input = CapitalIntegrityInput.from_dict(dict(body))
        result   = score_capital_integrity(ci_input)
    except (TypeError, ValueError) as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'instrument':  ci_input.name,
        'instrument_type': ci_input.instrument_type,
        'sector':      ci_input.sector,
        'country':     ci_input.country,
        **result.to_dict(),
        '_meta': {
            'engine':   'EcoIQ Capital Integrity Score v1',
            'endpoint': request.build_absolute_uri(),
            'note': (
                'Capital Integrity Score is a model estimate based on declared instrument parameters. '
                'Independent legal, financial, and environmental due diligence is required '
                'before any capital commitment or responsible finance labelling decision.'
            ),
        },
    })


# ── Islamic & Ethical Finance Fit ─────────────────────────────────────────────

@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def islamic_finance_fit(request):
    """
    POST /api/v1/finance/islamic-fit/

    Assess whether a transition project may be structurally suitable for
    Islamic finance instruments (sukuk, murabaha, musharakah), ethical
    finance frameworks, or development-bank blended finance.

    ⚠ This assessment is indicative only. It does not constitute a
    religious ruling, Shariah determination, or compliance certification.
    All Islamic finance suitability conclusions require review by a
    qualified Shariah scholar or accredited Shariah advisory board.

    Returns: finance_fit_score, label, dimension_scores,
             suitable_instruments, sukuk_potential, blended_finance_potential,
             required_evidence, structuring_notes, investor_note,
             sharia_review_note, confidence_note, methodology.

    Request body (JSON) — all fields optional except sector:
    {
        "name":                          "Solar Park Phase 2",
        "sector":                        "renewables",            // REQUIRED
        "country":                       "Kazakhstan",
        "project_type":                  "renewable_energy",
        "budget_usd":                    50000000,
        "duration_years":                20,
        "tangible_asset_linked":         true,
        "asset_ownership_transferable":  true,
        "asset_generates_income":        true,
        "community_benefit":             "high",
        "direct_jobs":                   400,
        "local_procurement_pct":         60,
        "additionality_demonstrated":    true,
        "use_of_proceeds_specificity":   "specific",
        "third_party_verified":          false,
        "reporting_commitment":          "annual",
        "ring_fenced_account":           false,
        "sector_excluded":               false,
        "sector_cautionary":             false,
        "environmental_assessment":      true,
        "pollution_mitigation_plan":     false,
        "project_stage":                 "development",
        "contractual_clarity":           "high",
        "performance_guarantees":        false,
        "profit_loss_sharing":           false,
        "investor_equity_participation": false,
        "fixed_return_only":             false,
        "community_benefit_sharing":     false,
        "governance_framework":          "IFC",
        "ownership_disclosed":           true,
        "independent_board_oversight":   false,
        "shariah_advisory_engaged":      false,
        "renewable_energy_share":        100,
        "nature_positive":               false,
        "climate_risk_disclosure":       true,
        "biodiversity_plan":             false,
        "emission_reduction_target":     true,
        "impact_measurement_plan":       true,
        "baseline_data_available":       false,
        "independent_verification_plan": false
    }
    """
    body = request.data
    if not body:
        return Response(
            {
                'error': 'Request body required.',
                'hint':  (
                    'Send JSON with at minimum {"sector": "renewables"} to receive '
                    'a baseline Islamic & Ethical Finance Fit assessment.'
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    sector = str(body.get('sector', '')).strip()
    if not sector:
        return Response(
            {
                'error': '"sector" is required.',
                'hint':  (
                    'Accepted values: renewables, energy, infrastructure, transport, '
                    'agriculture, water, mining, metallurgy, other — and excluded sectors '
                    'such as tobacco, alcohol, gambling.'
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from ml.finance.islamic_finance_fit import IslamicFinanceFitInput, assess_islamic_finance_fit
        if_input  = IslamicFinanceFitInput.from_dict(dict(body))
        if_result = assess_islamic_finance_fit(if_input)
    except (TypeError, ValueError) as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'project':      if_input.name,
        'sector':       if_input.sector,
        'country':      if_input.country,
        'project_type': if_input.project_type,
        **if_result.to_dict(),
        '_meta': {
            'engine':   'EcoIQ Islamic & Ethical Finance Fit v1',
            'endpoint': request.build_absolute_uri(),
            'note': (
                'This assessment is indicative only and based on declared project parameters. '
                'It does not constitute a religious ruling, Shariah determination, or '
                'certification of any kind. Formal Islamic finance suitability requires '
                'review by a qualified Shariah scholar or accredited Shariah advisory board. '
                'Not investment advice.'
            ),
        },
    })


# ── Project Readiness Score ───────────────────────────────────────────────────

@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def project_readiness_score(request):
    """
    POST /api/projects/readiness/

    Assess how ready a transition project is for investor, development bank,
    or climate finance review across ten structured dimensions.

    Returns:
      project_readiness_score      float 0–100
      readiness_label              investment-ready | advanced | developing | early-stage
      dimension_scores             dict — all 10 raw scores
      missing_documents            list — documents absent from the project file
      main_blockers                list — highest-priority structural gaps
      investor_note                str — investor-facing narrative
      next_steps                   list — ordered, actionable preparation steps
      recommended_finance_route    str — most appropriate financing pathway

    Request body (JSON):
    {
        "project_name":                     "Solar Farm Kazakhstan",   // optional
        "sector":                           "renewables",              // REQUIRED
        "country":                          "Kazakhstan",              // optional
        "project_type":                     "energy",                  // optional
        "budget_usd":                       120000000,                 // optional float
        "duration_years":                   20,                        // optional

        // Problem clarity
        "problem_statement":                "clear",                   // detailed|clear|partial|vague|none
        "quantified_impact_target":         true,
        "baseline_problem_data":            true,

        // Emissions baseline
        "emissions_baseline_documented":    true,
        "baseline_independently_verified":  false,
        "emissions_measurement_methodology": "ghg_protocol",          // iso_14064|ghg_protocol|sector_specific|internal|none

        // Technical feasibility
        "technology_readiness":             "proven",                  // operational|proven|pilot|prototype|concept
        "feasibility_study":                "standard",                // bankable|standard|preliminary|none
        "technical_advisor_engaged":        true,
        "technology_local_availability":    true,

        // CAPEX / OPEX
        "capex_estimate_quality":           "order_of_magnitude",      // detailed|order_of_magnitude|preliminary|none
        "opex_estimate_quality":            "preliminary",
        "independent_cost_review":          false,
        "contingency_provision":            true,

        // Revenue model
        "revenue_model":                    "contracted",              // contracted|market|grant|hybrid|none
        "offtake_agreement":                true,
        "subsidy_or_grant_confirmed":       false,
        "revenue_projections_available":    true,

        // Governance
        "governance_framework":             "IFC",                     // IFC|EBRD|ADB|World Bank|EU Taxonomy|GBP|TCFD|national|none
        "procurement_plan_documented":      true,
        "ownership_structure_disclosed":    true,
        "shareholder_agreement":            false,

        // Public benefit
        "community_benefit":                "medium",                  // high|medium|low|none
        "direct_jobs":                      250,
        "public_benefit_metrics_defined":   true,
        "gender_inclusion_plan":            false,

        // Risk mitigation
        "risk_register_documented":         true,
        "environmental_assessment":         true,
        "social_risk_assessment":           false,
        "insurance_plan":                   false,
        "force_majeure_coverage":           false,

        // Evidence
        "evidence_type":                    "analyst-reviewed",        // verified|analyst-reviewed|ai-seeded|model-estimate
        "key_documents_available":          ["feasibility_study", "eia", "financial_model"],
        "legal_land_rights_confirmed":      true,
        "permits_in_progress":              true,

        // Finance structure
        "finance_instrument":               "project_finance",         // green_bond|sukuk|project_finance|blended_finance|grant|equity|other
        "financial_model_available":        true,
        "legal_structure_defined":          false,
        "co_financing_identified":          false,
        "development_bank_engaged":         true
    }
    """
    body = request.data
    if not body:
        return Response(
            {
                'error': 'Request body required.',
                'hint': (
                    'Send JSON with at minimum {"sector": "renewables"} to receive '
                    'a baseline Project Readiness assessment. All other fields are optional '
                    'and default conservatively.'
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    sector = str(body.get('sector', '')).strip()
    if not sector:
        return Response(
            {
                'error': '"sector" is required.',
                'hint': (
                    'Provide a sector slug, e.g. "renewables", "energy", "infrastructure", '
                    '"transport", "water", "agriculture", "forestry", "waste", "other".'
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from ml.projects.project_readiness import ProjectReadinessInput, assess_project_readiness
        pr_input  = ProjectReadinessInput.from_dict(dict(body))
        pr_result = assess_project_readiness(pr_input)
    except (TypeError, ValueError) as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'project':       pr_input.project_name,
        'sector':        pr_input.sector,
        'country':       pr_input.country,
        'project_type':  pr_input.project_type,
        'budget_usd':    pr_input.budget_usd,
        **pr_result.to_dict(),
        '_meta': {
            'engine':   'EcoIQ Project Readiness Score v1',
            'endpoint': request.build_absolute_uri(),
            'note': (
                'Project Readiness Score is based on declared project parameters. '
                'It does not constitute investment advice, legal opinion, or a '
                'guarantee of finance eligibility. Independent technical, legal, '
                'and financial due diligence is required before any capital commitment.'
            ),
        },
    })


# ── Hikma assessment (read-only) ──────────────────────────────────────────────
@api_view(["GET"])
@permission_classes([IsPublicOrAPIKey])
def hikma_latest_assessment(request, slug):
    """GET /api/v1/assess/<slug>/latest

    Returns the latest stored Hikma AssessmentRun result for a company slug.
    Read-only: does NOT trigger scoring and does NOT mutate the database.
    404 if no completed run exists.
    """
    from hikma.models import AssessmentRun

    run = (AssessmentRun.objects
           .filter(subject_ref=slug, status="done", result__isnull=False)
           .order_by("-created_at")
           .first())
    if run is None:
        return Response(
            {"error": f'No Hikma assessment found for "{slug}". Run is generated offline.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response({
        "assessment_run_id": run.id,
        "generated_at": run.created_at.isoformat(),
        "engine_version": run.engine_version,
        **run.result,
        "_meta": {
            "endpoint": request.build_absolute_uri(),
            "read_only": True,
            "note": "Stored assessment; not regenerated on request. AI-assisted, indicative, not a ruling.",
        },
    })
