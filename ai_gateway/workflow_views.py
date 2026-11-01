"""Staff-only read-only schema preview for the future React Flow editor."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ai_gateway.permissions import IsEcoIQStaff
from ai_gateway.workflow_contracts import preview_decision_flow


@api_view(["GET"])
@permission_classes([IsEcoIQStaff])
def decision_flow_preview(request):
    """Return no private project data and execute no AI or database writes."""
    return Response(preview_decision_flow())
