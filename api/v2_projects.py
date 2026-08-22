"""
api/v2_projects.py — projects, and their verification state.

The estate currently holds ZERO projects. That is not a reason to omit the
endpoint: the frontend needs a real shape to render an honest empty state
against, and inventing demo rows to make a page look populated is the exact
failure this programme exists to remove.

`verified` is carried separately from `status` on purpose. A project can be
complete and unverified, and collapsing the two would let "we finished it"
read as "someone checked".

TWO LISTS, NEVER ONE
--------------------
`results` holds projects RECORDED in the database — zero of them today.
`concepts` holds the five programme concepts in projects/data.py: real
intentions, at concept or design stage, with indicative budgets and no
implementation behind them.

They are returned as separate keys and are never summed. Merging them would
turn five ideas into "five projects", which is the same substitution as a
score standing in for evidence — and the more tempting one, because the
merged page looks finished. `count` counts recorded projects only.
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
        # Separate key, never merged into `count` or `results`. See the module
        # docstring for why that separation is the whole point.
        'concepts': project_concepts(),
    })


# ── Programme concepts ───────────────────────────────────────────────────────

class ProjectConceptSerializer(serializers.Serializer):
    """
    A programme concept: an intention, not an implementation.

    Every field here is editorial content from projects/data.py. Nothing is a
    measurement, and the serializer deliberately exposes no field that could be
    read as one — `funding_amount` travels with `funding_label` and
    `funding_note`, which carry the word "indicative" the figure depends on.
    """
    slug = serializers.CharField()
    name = serializers.CharField()
    tagline = serializers.CharField()
    #: 'concept' | 'scoping' | 'design' | 'pilot' | 'scaling'. Never 'complete'.
    status_key = serializers.CharField()
    status = serializers.SerializerMethodField()
    location = serializers.CharField()
    sector = serializers.CharField()
    timeline_label = serializers.CharField()
    overview = serializers.CharField()
    problem = serializers.CharField()
    solution = serializers.CharField()
    expected_impact = serializers.ListField()
    kpis = serializers.ListField()
    timeline_phases = serializers.ListField()
    partnership_opportunities = serializers.ListField()
    funding_amount = serializers.CharField()
    funding_label = serializers.CharField()
    funding_note = serializers.CharField()

    def get_status(self, obj) -> str:
        from projects.data import status_label
        return status_label(obj['status_key'])


def project_concepts() -> list:
    """
    The five programme concepts, serialised.

    Read from projects/data.py — the same module the server-rendered pages used
    — so there is one source of truth for them and migrating the frontend did
    not fork the content.
    """
    from projects.data import PROJECTS

    return ProjectConceptSerializer(PROJECTS, many=True).data
