"""
customer_ai_chat/views.py — REST API endpoints for Ask EcoIQ.

Endpoints:
  POST /api/customer-chat/chat/      — public chat generation endpoint with IP throttling
  GET  /api/customer-chat/starters/  — public endpoint returning curated starter questions
"""
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from customer_ai_chat.knowledge import STARTER_QUESTIONS
from customer_ai_chat.services import (
    InvalidChatInputError,
    customer_chat_service,
)
from customer_ai_chat.throttles import CustomerChatIPThrottle

logger = logging.getLogger('ecoiq.customer_ai_chat')


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([CustomerChatIPThrottle])
def customer_chat_view(request):
    """
    POST /api/customer-chat/chat/

    Public customer-facing chat endpoint for prospective clients, investors, and visitors.
    Accepts:
      {
        "message": "What does EcoIQ do?",
        "conversation_id": "optional-uuid-string",
        "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
      }
    Returns:
      {
        "answer": "...",
        "conversation_id": "...",
        "suggested_actions": [{"label": "...", "url": "..."}]
      }
    """
    data = request.data
    if not isinstance(data, dict):
        return Response(
            {"error": "invalid_request", "detail": "Request body must be a JSON object."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    message = data.get('message')
    conversation_id = data.get('conversation_id')
    history = data.get('history')

    try:
        payload = customer_chat_service.process_chat(
            message=message,
            conversation_id=conversation_id,
            history=history,
        )
        return Response(payload, status=status.HTTP_200_OK)

    except InvalidChatInputError as exc:
        return Response(
            {"error": "invalid_input", "detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        logger.exception("customer_chat_view.unexpected_error")
        return Response(
            {
                "error": "server_error",
                "detail": "An unexpected error occurred while processing your request.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def customer_starters_view(request):
    """
    GET /api/customer-chat/starters/

    Returns curated starter prompt pills to help new visitors begin a conversation.
    """
    return Response({"starters": STARTER_QUESTIONS}, status=status.HTTP_200_OK)
