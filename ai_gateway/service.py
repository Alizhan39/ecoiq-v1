"""
ai_gateway/service.py — `AIService`, the only thing an EcoIQ view calls.

Responsibilities, in order:
  1. validate everything the browser sent (nothing downstream re-validates);
  2. resolve the opaque `model_key` through the registry;
  3. assemble the message list with the EcoIQ system prompt pinned at index 0;
  4. hand off to the router;
  5. return a public-safe dict — friendly model names, no provider slugs, no
     hidden reasoning, no raw upstream fields.

Views never construct a provider client, never see a `provider_model_id`, and
never see an API key.
"""
from __future__ import annotations

import logging
import uuid

from django.conf import settings

from ai_gateway.exceptions import FreeModelsUnavailable, InvalidAIRequest, InvalidModelSelection
from ai_gateway.prompts import build_system_prompt, normalise_language
from ai_gateway.registry import registry
from ai_gateway.router import router
from ai_gateway.types import CAPABILITY_CHAT

logger = logging.getLogger('ecoiq.ai_gateway')

# ── Input limits ──────────────────────────────────────────────────────────────
MAX_MESSAGE_CHARS = 8_000
MAX_HISTORY_TURNS = 20
MAX_HISTORY_CHARS = 24_000
MAX_TOTAL_REQUEST_CHARS = 32_000
ALLOWED_HISTORY_ROLES = frozenset({'user', 'assistant'})

# `context` is a fixed, closed shape — an arbitrary user-supplied JSON blob is
# never forwarded into a prompt.
ALLOWED_CONTEXT_KEYS = frozenset({'company_id', 'country_id', 'module'})
MAX_MODULE_LENGTH = 64

DEFAULT_TEMPERATURE = 0.2


def _validate_message(raw) -> str:
    if not isinstance(raw, str):
        raise InvalidAIRequest('A message is required.')
    message = raw.strip()
    if not message:
        raise InvalidAIRequest('A message is required.')
    if len(message) > MAX_MESSAGE_CHARS:
        raise InvalidAIRequest(
            f'Your message is too long (limit {MAX_MESSAGE_CHARS:,} characters).'
        )
    return message


def _validate_history(raw) -> list[dict]:
    """
    Accept only `user`/`assistant` turns. A `system` role from a client is
    rejected outright rather than silently dropped — a caller trying to inject
    a system message is making a request EcoIQ will not serve, and telling
    them so is more honest than pretending it worked.
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise InvalidAIRequest('Conversation history must be a list.')
    if len(raw) > MAX_HISTORY_TURNS:
        raise InvalidAIRequest(f'Conversation history is too long (limit {MAX_HISTORY_TURNS} turns).')

    history: list[dict] = []
    total_chars = 0
    for turn in raw:
        if not isinstance(turn, dict):
            raise InvalidAIRequest('Each history turn must be an object.')
        role = turn.get('role')
        content = turn.get('content')
        if role == 'system':
            raise InvalidAIRequest('History may not contain system messages.')
        if role not in ALLOWED_HISTORY_ROLES:
            raise InvalidAIRequest('History turns must have a role of "user" or "assistant".')
        if not isinstance(content, str):
            raise InvalidAIRequest('History turn content must be text.')
        content = content.strip()
        if not content:
            continue
        total_chars += len(content)
        if total_chars > MAX_HISTORY_CHARS:
            raise InvalidAIRequest('Conversation history is too large.')
        history.append({'role': role, 'content': content})
    return history


def _validate_context(raw) -> dict:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise InvalidAIRequest('Context must be an object.')
    unknown = set(raw) - ALLOWED_CONTEXT_KEYS
    if unknown:
        raise InvalidAIRequest('Unsupported context fields.')

    context: dict = {}
    for key in ('company_id', 'country_id'):
        if key in raw and raw[key] is not None:
            try:
                context[key] = int(raw[key])
            except (TypeError, ValueError) as exc:
                raise InvalidAIRequest(f'Context "{key}" must be an integer.') from exc
    module = raw.get('module')
    if module is not None:
        if not isinstance(module, str) or len(module) > MAX_MODULE_LENGTH:
            raise InvalidAIRequest('Context "module" must be a short text label.')
        # Closed character set — this value reaches the system prompt.
        cleaned = module.strip()
        if cleaned and not all(c.isalnum() or c in '-_ ./' for c in cleaned):
            raise InvalidAIRequest('Context "module" contains unsupported characters.')
        if cleaned:
            context['module'] = cleaned
    return context


class AIService:
    """Provider-neutral. Knows about the registry and the router, nothing else."""

    def chat(
        self,
        *,
        user,
        message: str,
        model_key: str | None = None,
        language: str | None = None,
        history=None,
        context=None,
    ) -> dict:
        request_id = uuid.uuid4().hex[:16]

        message = _validate_message(message)
        history = _validate_history(history)
        context = _validate_context(context)
        language = normalise_language(language)

        total_chars = len(message) + sum(len(t['content']) for t in history)
        if total_chars > MAX_TOTAL_REQUEST_CHARS:
            raise InvalidAIRequest('This conversation is too large to send. Start a new chat.')

        definition = self._resolve_model(model_key, user)

        messages = self._build_messages(
            message=message, history=history, language=language, context=context,
        )

        max_tokens = int(getattr(settings, 'AI_MAX_OUTPUT_TOKENS', 1600))
        response = router.run(
            selected=definition,
            messages=messages,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=max_tokens,
            request_id=request_id,
            user=user,
        )

        return self._public_payload(definition, response, request_id)

    # ── Steps ─────────────────────────────────────────────────────────────────

    def _resolve_model(self, model_key: str | None, user):
        """
        In `AI_MODEL_SELECTION_MODE=user` the caller picks. In any other mode
        the submitted key is ignored entirely and the server default is used —
        a per-request selector that the operator has turned off must not be
        bypassable by simply posting a key anyway.
        """
        selection_mode = getattr(settings, 'AI_MODEL_SELECTION_MODE', 'user')

        if selection_mode == 'user' and model_key:
            return registry.resolve(model_key, user, required_capability=CAPABILITY_CHAT)

        default = registry.default_model(user)
        if default is None:
            raise FreeModelsUnavailable()
        return default

    def _build_messages(self, *, message: str, history: list[dict], language: str,
                        context: dict) -> list[dict]:
        # Index 0 is always the EcoIQ system prompt. Client history has already
        # been stripped of system messages, so this position cannot be taken.
        return [
            {'role': 'system', 'content': build_system_prompt(language=language, context=context)},
            *history,
            {'role': 'user', 'content': message},
        ]

    def _public_payload(self, definition, response, request_id: str) -> dict:
        """
        The public response. Friendly names only; `provider_model_id` and the
        raw upstream body stay server-side. `resolved_model_name` is included
        only when the upstream actually reported a concrete model that differs
        from what we asked for — which is how `openrouter/free` reports its
        pick.
        """
        served_key = response.metadata.get('served_model_key', definition.key)
        served_name = response.metadata.get('served_model_name', definition.display_name)

        resolved_name = None
        if response.resolved_model and response.resolved_model != definition.provider_model_id:
            resolved_name = response.resolved_model

        payload = {
            'success': True,
            'answer': response.content,
            'model': {'key': served_key, 'name': served_name},
            'resolved_model_name': resolved_name,
            'fallback_used': response.fallback_used,
            'request_id': request_id,
        }
        if response.fallback_used:
            payload['notice'] = (
                'The selected free model was unavailable, so EcoIQ used another free model.'
            )
            payload['selected_model'] = {'key': definition.key, 'name': definition.display_name}
        return payload

    # ── Catalogue ─────────────────────────────────────────────────────────────

    def list_models(self, user) -> dict:
        snapshot = registry.get_snapshot()
        models = registry.visible_models(user, snapshot=snapshot)
        default = registry.default_model(user)

        return {
            'models': [self.serialise_model(m) for m in models],
            'default_model_key': default.key if default else None,
            'free_only': bool(settings.AI_FREE_ONLY),
            'selection_mode': getattr(settings, 'AI_MODEL_SELECTION_MODE', 'user'),
            'refreshed_at': snapshot.refreshed_at,
            'stale': snapshot.stale,
        }

    @staticmethod
    def serialise_model(model) -> dict:
        """
        Everything the browser is allowed to know about a model. Note what is
        absent: `provider_model_id`, base URLs, credentials, pricing, account
        balances and the free-policy internals.
        """
        return {
            'key': model.key,
            'name': model.display_name,
            'provider': model.provider_display_name,
            'description': model.description,
            'capabilities': sorted(model.capabilities),
            'context_length': model.context_length,
            'availability': model.availability,
            'free': model.free_eligible,
            'free_label': model.free_label,
            'preview': model.development_only,
        }


service = AIService()
