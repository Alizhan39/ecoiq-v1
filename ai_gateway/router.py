"""
ai_gateway/router.py — `AIProviderRouter`: run one request against the free
pool, with bounded fallback.

    Selected free model
            ↓ unavailable
    Same provider's approved free fallback
            ↓ unavailable
    Another provider's approved free fallback
            ↓ unavailable
    FREE_MODELS_UNAVAILABLE

Three invariants, all enforced structurally rather than by convention:

  * **Never leaves the free pool.** The attempt chain is built by the registry
    from already-approved, already-free-eligible models. There is no code path
    that constructs a model id from anywhere else, so "fall back to a paid
    model" is not a thing this router can express.
  * **Never loops.** Each model key is attempted at most once (`attempted`
    set), and the loop is additionally capped by `AI_MAX_PROVIDER_ATTEMPTS`.
  * **Never falls back on a terminal error.** An invalid request, unsupported
    modality or broken configuration stops immediately — trying a second model
    would only hide the fault.
"""
from __future__ import annotations

import logging

from django.conf import settings

from ai_gateway.exceptions import (
    CATEGORY_TO_PUBLIC_ERROR, AIGatewayError, FreeModelsUnavailable, ProviderCallError,
)
from ai_gateway.providers import get_provider
from ai_gateway.registry import mark_model_unavailable, registry
from ai_gateway.types import AIModelDefinition, AIResponse

logger = logging.getLogger('ecoiq.ai_gateway')


class AIProviderRouter:
    """Stateless. One `run()` call == one user request."""

    def run(
        self,
        *,
        selected: AIModelDefinition,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        request_id: str,
        user=None,
    ) -> AIResponse:
        chain = registry.fallback_chain(selected, user)
        max_attempts = max(1, int(settings.AI_MAX_PROVIDER_ATTEMPTS))

        attempted: set[str] = set()
        attempts = 0
        last_error: ProviderCallError | None = None

        for candidate in chain:
            if attempts >= max_attempts:
                break
            if candidate.key in attempted:
                continue          # structural loop guard
            attempted.add(candidate.key)
            attempts += 1

            provider = get_provider(candidate.provider)
            try:
                response = provider.generate(
                    model_id=candidate.provider_model_id,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_id=request_id,
                )
            except ProviderCallError as exc:
                last_error = exc
                self._log_failure(candidate, exc, attempts, request_id)

                if not exc.retryable:
                    # Terminal: invalid request, unsupported modality,
                    # unauthorised, broken configuration. Stop.
                    raise self._public_error(exc) from exc

                mark_model_unavailable(candidate.provider, candidate.provider_model_id,
                                       exc.category)
                continue

            fallback_used = candidate.key != selected.key
            logger.info(
                'ai_gateway.request_ok model_key=%s provider=%s resolved=%s attempts=%s '
                'fallback=%s in_tokens=%s out_tokens=%s request_id=%s',
                candidate.key, candidate.provider, response.resolved_model, attempts,
                fallback_used, response.input_tokens, response.output_tokens, request_id,
            )
            return AIResponse(
                content=response.content,
                provider=response.provider,
                requested_model=selected.provider_model_id,
                resolved_model=response.resolved_model,
                finish_reason=response.finish_reason,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                fallback_used=fallback_used,
                provider_attempts=attempts,
                metadata={
                    **response.metadata,
                    'served_model_key': candidate.key,
                    'served_model_name': candidate.display_name,
                    'free_policy': candidate.free_policy,
                },
            )

        logger.warning(
            'ai_gateway.free_pool_exhausted attempts=%s last_category=%s request_id=%s',
            attempts, last_error.category if last_error else 'none', request_id,
        )
        # Every approved free model was tried (or the attempt budget ran out).
        # This is where a lesser gateway would reach for a paid model; EcoIQ
        # returns a stable, safe failure instead.
        raise FreeModelsUnavailable()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _public_error(exc: ProviderCallError) -> AIGatewayError:
        error_class = CATEGORY_TO_PUBLIC_ERROR.get(exc.category, FreeModelsUnavailable)
        return error_class()

    @staticmethod
    def _log_failure(candidate, exc: ProviderCallError, attempt: int, request_id: str) -> None:
        # Category and model key only. Never the prompt, never the response
        # body, never the upstream detail string.
        logger.warning(
            'ai_gateway.attempt_failed model_key=%s provider=%s category=%s status=%s '
            'attempt=%s request_id=%s',
            candidate.key, candidate.provider, exc.category, exc.status_code,
            attempt, request_id,
        )


router = AIProviderRouter()
