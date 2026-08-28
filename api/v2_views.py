"""
API v2 views — truthful evidence semantics.

Additive. Nothing here imports from or mutates the v1 views, so shipping v2
cannot change a single v1 response. See docs/product/API_EVIDENCE_MIGRATION.md.

Permissions match v1 exactly (`IsPublicOrAPIKey`): v2 is not a privilege change,
it is a truthfulness change. The same audience gets the same data, described
honestly.
"""
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from api.authentication import APIKeyAuthentication
from api.permissions import IsPublicOrAPIKey
# StandardPagination lives in api/views.py. Imported, not duplicated: v2 should
# paginate identically to v1, and a second copy would be free to drift.
from api.views import StandardPagination
from api.v2_serializers import CompanyProfileV2Serializer, CompanyV2Serializer
from companies.visibility import profile_for, profiles_visible_to
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
    #: SessionAuthentication alongside the API key, so a signed-in staff
    #: session is recognised here as it already is on the sub-resources.
    #:
    #: `[APIKeyAuthentication]` alone was a pure SUBTRACTION from DRF's default
    #: chain — the default already contains APIKeyAuthentication, so overriding
    #: with just it added nothing and only removed session auth. The cost was
    #: measured by the authorization pass: /api/v2/companies/<slug>/kpis/<id>/
    #: is a plain Django view and lets a staff reviewer open an archived
    #: organisation, while its own parent resource answered 404 to the same
    #: person in the same browser. GET-only, so restoring session auth carries
    #: no CSRF surface.
    authentication_classes = [APIKeyAuthentication, SessionAuthentication]
    permission_classes = [IsPublicOrAPIKey]

    def get_queryset(self):
        # Through companies.visibility, not Company.objects. Starting from the
        # company table listed every organisation the DETAIL endpoint and the
        # page both withhold: archived ones, and ones carrying no profile at
        # all. A directory that lists what its own entries refuse to open is
        # the index to the thing it is withholding.
        qs = (Company.objects
              .filter(profile__in=profiles_visible_to(self.request.user))
              .select_related('profile').order_by('name'))

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
@authentication_classes([APIKeyAuthentication, SessionAuthentication])
@permission_classes([IsPublicOrAPIKey])
def company_detail_v2(request, slug):
    """GET /api/v2/companies/<slug>/ — one company, with its evidence state."""
    # The literal this replaced was written before `public_demo` existed, so a
    # demonstration profile 404'd here while /companies/<slug>/ served it — the
    # page and its own API disagreeing about whether the organisation is
    # reachable. companies/visibility.py is the one list, and it is not copied.
    profile = profile_for(slug, request.user)
    return Response(CompanyProfileV2Serializer(profile, context={'request': request}).data)


@api_view(['GET'])
# Not given SessionAuthentication with the two above: the leaderboard ranks
# only publishable organisations, so who is asking cannot change its contents.
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

    from companies.evidence import PENDING_HEADLINE

    return Response({
        'count': len(eligible),
        'withheld_insufficient_evidence': withheld,
        'leaderboard': CompanyV2Serializer(
            eligible, many=True, context={'request': request}).data,
        # The BACKEND owns the wording for an absent ranking, in the same
        # constants every other surface uses.
        #
        # The league page used to be server-rendered and carried this text in
        # its HTML; it is React now, and if the page wrote its own sentence the
        # explanation would drift from the one the company pages give. An
        # evidence system that explains itself differently depending on which
        # page you are on has two explanations, which is one too many.
        #
        # The HEADLINE is the shared constant — that is the claim which must
        # not drift between surfaces. The DETAIL is written for this one:
        # PENDING_DETAIL says "for this organisation", which is right on a
        # company page and wrong on a leaderboard, and a sentence that does not
        # fit the page it is on reads as boilerplate rather than as an
        # explanation.
        #
        # Null when something IS ranked: there is then nothing to explain.
        'evidence_note': None if eligible else {
            'headline': PENDING_HEADLINE,
            'detail': (
                'No organisation currently has the evidence coverage a '
                'published score requires, so none can be ranked. A rank is a '
                'comparative claim, and publishing one would assert exactly '
                'what the score is withholding.'),
        },
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
