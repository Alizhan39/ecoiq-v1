"""
api/v2_projects.py — projects, and their verification state.

The estate currently holds ZERO projects. That is not a reason to omit the
endpoint: the frontend needs a real shape to render an honest empty state
against, and inventing demo rows to make a page look populated is the exact
failure this programme exists to remove.

`verified` is carried separately from `status` on purpose. A project can be
complete and unverified, and collapsing the two would let "we finished it"
read as "someone checked".
"""
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.unknown import known


class ProjectV2Serializer(serializers.Serializer):
    """
    One project.

    Every quantity is nullable. A project with no recorded CO2 figure has no
    recorded CO2 figure — it did not reduce zero tonnes, and the difference is
    the whole point.
    """
    slug = serializers.SerializerMethodField()
    name = serializers.CharField()
    project_type = serializers.CharField()
    status = serializers.CharField()
    location = serializers.CharField()
    description = serializers.CharField()
    company = serializers.SerializerMethodField()
    verified = serializers.BooleanField()
    investment_usd = serializers.SerializerMethodField()
    co2_reduction_tonnes = serializers.SerializerMethodField()
    households_helped = serializers.SerializerMethodField()

    def get_slug(self, obj) -> str:
        return str(obj.pk)

    def get_company(self, obj) -> str:
        company = getattr(obj, 'company', None)
        return company.name if company else ''

    def get_investment_usd(self, obj):
        return known(obj.investment_usd)

    def get_co2_reduction_tonnes(self, obj):
        return known(obj.co2_reduction_tonnes)

    def get_households_helped(self, obj):
        return known(obj.households_helped)


@api_view(['GET'])
@permission_classes([AllowAny])
def projects(request):
    """
    GET /api/v2/projects/

    Returns `{count, verified_count, results}`. `verified_count` is exposed
    beside the total because "12 projects" and "12 projects, 0 independently
    verified" are very different statements, and a frontend that has to compute
    the second from the first will eventually forget to.
    """
    from league.models import EnvironmentalProject

    queryset = (EnvironmentalProject.objects
                .select_related('company')
                .order_by('-start_date', 'name'))

    return Response({
        'count': queryset.count(),
        'verified_count': queryset.filter(verified=True).count(),
        'results': ProjectV2Serializer(queryset[:100], many=True).data,
    })
