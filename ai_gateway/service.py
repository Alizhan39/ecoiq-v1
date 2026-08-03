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

from ai_gateway import safety
from ai_gateway.exceptions import FreeModelsUnavailable, InvalidAIRequest
from ai_gateway.prompts import build_system_prompt, normalise_language
from ai_gateway.registry import registry
from ai_gateway.router import router
from ai_gateway.routing import build_profile
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

#: Fields that would steer routing if they were trusted. None of them is ever
#: legitimate from a browser: EcoIQ picks the model, and the provider, base URL
#: and free-only policy are server-side decisions. Submitting one is either a
#: stale client or an attempt to escape the free pool, and both deserve a clear,
#: consistent 400 rather than a silent shrug.
REJECTED_ROUTING_FIELDS = ('provider', 'base_url', 'model', 'free_only',
                           'provider_preferences', 'route', 'api_key')


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


def reject_untrusted_routing_fields(data: dict) -> None:
    """
    Refuse any request that tries to steer routing directly. Consistent with
    how `context` already treats unknown keys: an unsupported field is a 400,
    not something quietly dropped.
    """
    present = [f for f in REJECTED_ROUTING_FIELDS if f in data]
    if present:
        # The field NAMES are safe to log; their values are not, and are not.
        logger.warning('ai_gateway.untrusted_routing_fields fields=%s', ','.join(present))
        raise InvalidAIRequest(
            'This request contains fields EcoIQ does not accept. '
            'EcoIQ selects the AI model automatically.'
        )


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
        mode=None,
        images=None,
        attachments=None,
    ) -> dict:
        request_id = uuid.uuid4().hex[:16]

        message = _validate_message(message)
        history = _validate_history(history)
        context = _validate_context(context)
        language = normalise_language(language)

        total_chars = len(message) + sum(len(t['content']) for t in history)
        if total_chars > MAX_TOTAL_REQUEST_CHARS:
            raise InvalidAIRequest('This conversation is too large to send. Start a new chat.')

        has_images = bool(images)
        has_attachments = bool(attachments) or has_images

        profile = build_profile(
            user=user,
            mode=mode,
            module=context.get('module', ''),
            language=language,
            estimated_input_chars=total_chars,
            # Drives the capability filter: with images present, only
            # vision-capable models survive `routing.is_eligible()`.
            needs_vision=has_images,
        )

        # Selective safety screening — see ai_gateway/safety.py. A harmless
        # text question meets no trigger and costs nothing extra.
        found = safety.triggers(
            message=message,
            has_attachments=has_attachments,
            has_images=has_images,
            module=context.get('module', ''),
        )
        if safety.should_screen(found):
            verdict = safety.screen(message=message, found=found, request_id=request_id)
            if verdict.blocked:
                # A stable, generic refusal. The classifier's category, its
                # reasoning and the provider behind it are never disclosed.
                raise InvalidAIRequest(
                    'EcoIQ cannot help with this request.',
                    code='CONTENT_NOT_SUPPORTED',
                )

        chain, pinned = self._build_chain(model_key, user, profile)

        messages = self._build_messages(
            message=message, history=history, language=language, context=context,
        )

        response = router.run(
            chain=chain,
            messages=messages,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=profile.max_output_tokens,
            request_id=request_id,
        )

        return self._public_payload(response, profile, request_id, pinned=pinned)

    # ── Steps ─────────────────────────────────────────────────────────────────

    def _build_chain(self, model_key, user, profile):
        """
        Decide what to try, in order.

        Public callers get automatic routing — a submitted `model_key` is
        ignored rather than rejected, so a stale client that still remembers a
        selection keeps working instead of erroring. Ignoring is safe precisely
        because the value is never read: it cannot widen the free pool.

        Staff may pin a model for benchmarking. That still goes through
        `registry.resolve()`, so it accepts only registered keys, cannot reach a
        paid model, and cannot name a provider, base URL or raw slug.
        """
        selection_mode = getattr(settings, 'AI_MODEL_SELECTION_MODE', 'automatic')
        staff_override = (
            getattr(settings, 'AI_STAFF_MODEL_OVERRIDE_ENABLED', True)
            and registry.user_may_use_development_models(user)
        )
        may_pin = staff_override or selection_mode == 'user'

        if model_key and may_pin:
            pinned = registry.resolve(model_key, user, required_capability=CAPABILITY_CHAT)
            chain = registry.fallback_chain(pinned, user)
            return chain, pinned

        if model_key:
            # Ignored, but recorded — a public client still sending one is worth
            # knowing about. The key itself is not logged.
            logger.info('ai_gateway.model_key_ignored mode=%s audience=%s',
                        selection_mode, profile.audience)

        chain = registry.select_route(profile, user)
        if not chain:
            raise FreeModelsUnavailable()
        return chain, None

    def _build_messages(self, *, message: str, history: list[dict], language: str,
                        context: dict) -> list[dict]:
        # Index 0 is always the EcoIQ system prompt. Client history has already
        # been stripped of system messages, so this position cannot be taken.
        return [
            {'role': 'system', 'content': build_system_prompt(language=language, context=context)},
            *history,
            {'role': 'user', 'content': message},
        ]

    def _public_payload(self, response, profile, request_id: str, *, pinned=None) -> dict:
        """
        The public response carries the answer and nothing about how it was
        produced. A normal user never sees a model name, a provider name, a
        resolved slug or a fallback notice — under automatic routing those are
        implementation detail, and surfacing them would reintroduce exactly the
        model-awareness this change removes.

        Staff get the routing detail back, because they are the ones
        benchmarking and comparing.
        """
        payload = {
            'success': True,
            'answer': response.content,
            'mode': profile.mode,
            'request_id': request_id,
        }

        if profile.audience != 'staff':
            return payload

        served_key = response.metadata.get('served_model_key')
        served_name = response.metadata.get('served_model_name')
        payload['routing'] = {
            'automatic': pinned is None,
            'model': {'key': served_key, 'name': served_name},
            # The concrete model behind a router pick (openrouter/free reports
            # what it actually ran) — staff-only, for benchmark attribution.
            'resolved_model_name': response.resolved_model,
            'attempts': response.provider_attempts,
            'fallback_used': response.fallback_used,
            'task': profile.task,
        }
        if pinned is not None:
            payload['routing']['pinned_model'] = {'key': pinned.key, 'name': pinned.display_name}
        return payload

    # ── Catalogue ─────────────────────────────────────────────────────────────

    def list_models(self, user) -> dict:
        """
        Under automatic routing this endpoint is a staff tool, not a public
        selector. A normal caller gets `selection_available: false` and an
        empty list — the endpoint keeps its contract, but there is nothing to
        pick from, so the frontend cannot build a selector even if it tried.
        """
        snapshot = registry.get_snapshot()
        selection_mode = getattr(settings, 'AI_MODEL_SELECTION_MODE', 'automatic')
        may_select = (
            selection_mode == 'user'
            or (getattr(settings, 'AI_STAFF_MODEL_OVERRIDE_ENABLED', True)
                and registry.user_may_use_development_models(user))
        )

        payload = {
            'models': [],
            'selection_available': bool(may_select),
            'selection_mode': selection_mode,
            'routing_mode': getattr(settings, 'AI_ROUTING_MODE', 'automatic'),
            'modes': sorted((getattr(settings, 'AI_ROUTING_MODES', {}) or {}).keys()),
            'default_mode': getattr(settings, 'AI_DEFAULT_ROUTING_MODE', 'auto'),
            'free_only': bool(settings.AI_FREE_ONLY),
            'refreshed_at': snapshot.refreshed_at,
            'stale': snapshot.stale,
        }
        if may_select:
            payload['models'] = [
                self.serialise_model(m)
                for m in registry.visible_models(user, snapshot=snapshot)
            ]
        return payload

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
