"""
API v2 views — truthful evidence semantics.

Additive. Nothing here imports from or mutates the v1 views, so shipping v2
cannot change a single v1 response. See docs/product/API_EVIDENCE_MIGRATION.md.

Permissions match v1 exactly (`IsPublicOrAPIKey`): v2 is not a privilege change,
it is a truthfulness change. The same audience gets the same data, described
honestly.
"""
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from api.authentication import APIKeyAuthentication
from api.permissions import IsPublicOrAPIKey
# StandardPagination lives in api/views.py. Imported, not duplicated: v2 should
# paginate identically to v1, and a second copy would be free to drift.
from api.views import StandardPagination
from api.v2_serializers import CompanyProfileV2Serializer, CompanyV2Serializer
from companies.models import CompanyProfile
from league.models import Company


class CompanyListV2View(ListAPIView):
    """
    GET /api/v2/companies/

    Every company, each with an explicit score status. Companies without
    publishable evidence are listed with `ecoiq_score: null` rather than
    omitted — the caller asked for the companies, and hiding them would be its
    own distortion.

    Query params: q, sector, country, page, page_size.

    Deliberately no min_score/max_score: filtering on a value that is null for
    most rows would silently drop them, which is a comparative claim made by
    omission.
    """
    serializer_class = CompanyV2Serializer
    pagination_class = StandardPagination
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsPublicOrAPIKey]

    def get_queryset(self):
        qs = Company.objects.select_related('profile').order_by('name')

        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(name__icontains=q)
        sector = self.request.query_params.get('sector')
        if sector:
            qs = qs.filter(sector__iexact=sector)
        country = self.request.query_params.get('country')
        if country:
            qs = qs.filter(country__iexact=country)
        return qs


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def company_detail_v2(request, slug):
    """GET /api/v2/companies/<slug>/ — one company, with its evidence state."""
    company = get_object_or_404(Company, slug=slug)
    profile = get_object_or_404(
        CompanyProfile, company=company, status__in=('public', 'verified', 'draft'))
    return Response(CompanyProfileV2Serializer(profile, context={'request': request}).data)


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def leaderboard_v2(request):
    """
    GET /api/v2/leaderboard/

    Only companies whose score is publishable are ranked — the same rule the web
    league table follows since #239. A leaderboard is a comparative statement
    about every row in it, so an unevidenced company is withheld rather than
    placed somewhere in the order.

    `withheld` reports how many were held back, so a caller receiving an empty
    list can tell "nothing qualifies" from "nothing exists".
    """
    top = min(int(request.query_params.get('top', 100)), 500)
    qs = Company.objects.select_related('profile').order_by('rank', '-ecoiq_score')

    sector = request.query_params.get('sector')
    if sector:
        qs = qs.filter(sector__iexact=sector)

    from companies.evidence import public_score_state_for_company

    eligible, withheld = [], 0
    for company in qs:
        if public_score_state_for_company(company).available:
            eligible.append(company)
            if len(eligible) >= top:
                break
        else:
            withheld += 1

    return Response({
        'count': len(eligible),
        'withheld_insufficient_evidence': withheld,
        'leaderboard': CompanyV2Serializer(
            eligible, many=True, context={'request': request}).data,
    })


@api_view(['GET'])
@permission_classes([])
def api_root_v2(request):
    """GET /api/v2/ — what this version is and how it differs from v1."""
    return Response({
        'version': 'v2',
        'status': 'canonical',
        'description': (
            'EcoIQ public API with explicit evidence semantics. A score is '
            'null when EcoIQ cannot support it with evidence; score_status and '
            'evidence_coverage say so explicitly. Unknown is never reported as '
            '0, 50 or any other stand-in value.'
        ),
        'score_status_values': ['PUBLISHED', 'INSUFFICIENT_EVIDENCE'],
        'endpoints': {
            'companies': '/api/v2/companies/',
            'company_detail': '/api/v2/companies/<slug>/',
            'leaderboard': '/api/v2/leaderboard/',
        },
        'v1': {
            'path': '/api/v1/',
            'status': 'legacy-compatibility',
            'note': (
                'v1 still returns a numeric score for every company regardless '
                'of evidence. It is retained for existing integrators and is '
                'not the canonical contract. New integrations should use v2.'
            ),
        },
    })
