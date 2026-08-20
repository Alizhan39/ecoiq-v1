"""
customer_ai_chat/services.py — Core customer chat service for Ask EcoIQ.

Coordinates input validation, knowledge grounding, central AI provider routing,
response sanitization, and contextual lead-generation action recommendations.
"""
from __future__ import annotations

import logging
import uuid
import re

from django.conf import settings

from ai_gateway.exceptions import AIGatewayError, FreeModelsUnavailable, ProviderCallError
from ai_gateway.registry import registry
from ai_gateway.router import AIProviderRouter
from customer_ai_chat.knowledge import ACTION_ROUTES, STARTER_QUESTIONS
from customer_ai_chat.prompts import build_customer_chat_messages

logger = logging.getLogger('ecoiq.customer_ai_chat')

MAX_MESSAGE_LENGTH = 2000
MAX_HISTORY_ITEMS = 10


class InvalidChatInputError(ValueError):
    """Raised when user input violates validation bounds."""


class CustomerChatService:
    """Encapsulates customer-facing chat orchestration."""

    def __init__(self, router: AIProviderRouter | None = None):
        self.router = router or AIProviderRouter()

    def validate_input(self, message: str | None, history: list | None = None) -> tuple[str, list[dict]]:
        """Validate and sanitize user input message and history."""
        if not message or not isinstance(message, str):
            raise InvalidChatInputError("Message must be a non-empty text string.")

        clean_message = message.strip()
        if not clean_message:
            raise InvalidChatInputError("Message cannot be blank.")

        if len(clean_message) > MAX_MESSAGE_LENGTH:
            raise InvalidChatInputError(
                f"Message exceeds maximum allowed length of {MAX_MESSAGE_LENGTH} characters."
            )

        sanitized_history = []
        if history and isinstance(history, list):
            for item in history[-MAX_HISTORY_ITEMS:]:
                if isinstance(item, dict) and 'role' in item and 'content' in item:
                    role = str(item['role']).lower()
                    if role in ('user', 'assistant'):
                        content = str(item['content'])[:MAX_MESSAGE_LENGTH]
                        sanitized_history.append({'role': role, 'content': content})

        return clean_message, sanitized_history

    def get_suggested_actions(self, message: str, answer: str) -> list[dict[str, str]]:
        """Determine relevant call-to-action suggestions based on message and answer context."""
        text = (message + " " + answer).lower()
        actions = []

        if any(k in text for k in ("demo", "trial", "enterprise", "schedule", "pricing", "cost", "subscription")):
            actions.append({"label": ACTION_ROUTES["request_demo"]["label"], "url": ACTION_ROUTES["request_demo"]["url"]})
            actions.append({"label": ACTION_ROUTES["contact_team"]["label"], "url": ACTION_ROUTES["contact_team"]["url"]})

        elif any(k in text for k in ("review", "assess", "company score", "project readiness", "evaluate")):
            actions.append({"label": ACTION_ROUTES["request_review"]["label"], "url": ACTION_ROUTES["request_review"]["url"]})
            actions.append({"label": ACTION_ROUTES["explore_intelligence"]["label"], "url": ACTION_ROUTES["explore_intelligence"]["url"]})

        elif any(k in text for k in ("islamic", "sharia", "mizan", "ethical finance", "stewardship")):
            actions.append({"label": "Request Ethical Finance Review", "url": "/request-access/review/?type=islamic_finance"})
            actions.append({"label": ACTION_ROUTES["explore_intelligence"]["label"], "url": ACTION_ROUTES["explore_intelligence"]["url"]})

        else:
            actions.append({"label": ACTION_ROUTES["explore_intelligence"]["label"], "url": ACTION_ROUTES["explore_intelligence"]["url"]})
            actions.append({"label": ACTION_ROUTES["request_demo"]["label"], "url": ACTION_ROUTES["request_demo"]["url"]})

        # Return unique actions by URL, max 3
        seen_urls = set()
        unique_actions = []
        for a in actions:
            if a["url"] not in seen_urls:
                seen_urls.add(a["url"])
                unique_actions.append(a)
            if len(unique_actions) >= 3:
                break
        return unique_actions

    def sanitize_response(self, raw_text: str) -> str:
        """Strip dangerous system injection echoes, internal prompt headers, or raw tracebacks."""
        if not raw_text:
            return "I apologize, but I could not generate a response at this time. Please try asking your question again."

        # Remove any leaked internal header markers
        cleaned = re.sub(r'VERIFIED ECOIQ KNOWLEDGE CONTEXT.*?={3,}', '', raw_text, flags=re.DOTALL)
        cleaned = cleaned.replace('VERIFIED ECOIQ KNOWLEDGE CONTEXT', '')
        cleaned = re.sub(r'### HOW TO RESPOND.*?\n', '', cleaned)
        return cleaned.strip()

    def process_chat(
        self,
        message: str,
        conversation_id: str | None = None,
        history: list | None = None,
    ) -> dict:
        """
        Main entry point: validates input, retrieves grounded knowledge, routes to AI model,
        and returns structured response with conversation tracking and suggested actions.
        """
        clean_message, sanitized_history = self.validate_input(message, history)
        conv_id = conversation_id or str(uuid.uuid4())
        request_id = f"customer_chat_{uuid.uuid4().hex[:12]}"

        messages = build_customer_chat_messages(clean_message, sanitized_history)

        try:
            chain = registry.select_route(user=None, mode='auto')
            ai_response = self.router.run(
                chain=chain,
                messages=messages,
                temperature=0.2,
                max_tokens=900,
                request_id=request_id,
            )
            answer_text = self.sanitize_response(ai_response.content)

        except FreeModelsUnavailable:
            logger.warning("customer_ai_chat.free_models_unavailable: request_id=%s", request_id)
            answer_text = (
                "The EcoIQ Assistant is currently undergoing scheduled maintenance. "
                "You can explore live platform intelligence at `/intelligence/` or "
                "reach our team directly at alizhan@ecoiq.uk."
            )
        except ProviderCallError as exc:
            logger.error("customer_ai_chat.provider_error: request_id=%s exc=%s", request_id, exc)
            answer_text = (
                "We experienced a temporary issue connecting to our analytical models. "
                "Please try again in a moment, or visit `/request-access/` to speak with our team."
            )
        except AIGatewayError as exc:
            logger.error("customer_ai_chat.gateway_error: request_id=%s exc=%s", request_id, exc)
            answer_text = (
                "An unexpected service error occurred. Please refresh the page or try again shortly."
            )
        except Exception:
            logger.exception("customer_ai_chat.unhandled_exception: request_id=%s", request_id)
            answer_text = (
                "An unexpected error occurred. Please contact alizhan@ecoiq.uk if this issue persists."
            )

        suggested_actions = self.get_suggested_actions(clean_message, answer_text)

        return {
            "answer": answer_text,
            "conversation_id": conv_id,
            "suggested_actions": suggested_actions,
        }


# Singleton service instance for standard imports
customer_chat_service = CustomerChatService()
