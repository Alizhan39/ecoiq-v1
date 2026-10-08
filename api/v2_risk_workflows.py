"""Authenticated, CSRF-protected API for the bounded internal evidence workflow."""
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ai_observatory.models import AnalysisSession
from ai_observatory.services.governance import session_trace
from capital_guardian.models import RiskFollowUp
from capital_guardian.services import risk_workflow as workflow
from gold_intelligence.access import projects_for, ANALYSE


class StartInput(serializers.Serializer):
    rule_key = serializers.CharField(max_length=60)


class ActionInput(serializers.Serializer):
    action = serializers.ChoiceField(choices=('document', 'resume', 'recalculate', 'review'))
    memory_id = serializers.IntegerField(min_value=1, required=False)
    decision = serializers.ChoiceField(choices=('approved', 'rejected'), required=False)
    assessment_digest = serializers.RegexField(r'^[a-f0-9]{64}$', required=False)
    notes = serializers.CharField(max_length=4000, required=False)

    def validate(self, attrs):
        required = {'document': ('memory_id',), 'review': ('decision', 'assessment_digest', 'notes')}.get(attrs['action'], ())
        for name in required:
            if name not in attrs:
                raise serializers.ValidationError({name: 'Required for this action.'})
        return attrs


def _response(task, user):
    response = Response(workflow.task_detail(task, user))
    response['Cache-Control'] = 'private, no-store'
    return response


@api_view(['GET', 'POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def workflows(request, slug):
    project = get_object_or_404(projects_for(request.user, ANALYSE) if request.method == 'POST' else projects_for(request.user), slug=slug)
    if request.method == 'GET':
        return Response({'results': list(RiskFollowUp.objects.filter(project=project).order_by('-pk').values(
            'id', 'rule_key', 'state', 'created_at')[:100])})
    data = StartInput(data=request.data)
    data.is_valid(raise_exception=True)
    try:
        task = workflow.start_followup(project, request.user, data.validated_data['rule_key'])
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=409)
    return _response(task, request.user)


@api_view(['GET', 'POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def detail(request, slug, task_id):
    project = get_object_or_404(projects_for(request.user), slug=slug)
    task = get_object_or_404(RiskFollowUp.objects.select_related('project', 'session'), pk=task_id, project=project)
    if request.method == 'POST':
        data = ActionInput(data=request.data)
        data.is_valid(raise_exception=True)
        params = data.validated_data
        try:
            if params['action'] == 'document':
                workflow.submit_document(task.pk, project, request.user, params['memory_id'])
                task = workflow.advance(task.pk, project, request.user)
            elif params['action'] == 'review':
                task = workflow.review(task.pk, project, request.user, params['decision'], params['assessment_digest'], params['notes'])
            elif params['action'] == 'recalculate':
                task = workflow.recalculate(task.pk, project, request.user)
            else:
                task = workflow.advance(task.pk, project, request.user)
        except ObjectDoesNotExist:
            return Response({'detail': 'Requested project record unavailable.'}, status=404)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=409)
    return _response(task, request.user)


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def audit_trace(request, slug, session_id):
    project = get_object_or_404(projects_for(request.user), slug=slug)
    session = get_object_or_404(AnalysisSession, pk=session_id, project=project)
    task = RiskFollowUp.objects.filter(session=session).select_related('project', 'session').first()
    trace = workflow.task_detail(task, request.user)['trace'] if task else session_trace(session)
    response = Response({'trace': trace})
    response['Cache-Control'] = 'private, no-store'
    return response
