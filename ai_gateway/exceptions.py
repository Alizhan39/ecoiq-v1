"""
ai_gateway/exceptions.py — the stable EcoIQ error surface for AI requests.

Two distinct layers:

  * `ProviderCallError` is *internal*. It carries a normalised `category`
    that the router uses to decide whether falling back to another approved
    free model is legitimate. It never reaches a client.
  * `AIGatewayError` subclasses are *public*. Each maps to one fixed HTTP
    status and one fixed, safe message. A raw provider exception, upstream
    body, URL or credential can never travel out through these.
"""
from __future__ import annotations


# ── Internal failure categories ───────────────────────────────────────────────

#: Transient conditions. The selected model failed for a reason that another
#: approved *free* model might not share, so fallback inside the free pool is
#: legitimate (spec: timeout, connection failure, 429, 5xx, model temporarily
#: unavailable, empty/malformed response, free-plan credits exhausted).
RETRYABLE_CATEGORIES = frozenset({
    'timeout',
    'connection',
    'rate_limit',
    'server_error',
    'model_unavailable',
    'empty_response',
    'malformed_response',
    'credits_exhausted',
})

#: Permanent conditions. Retrying or falling back would either repeat the same
#: failure or quietly paper over a real bug/misconfiguration, so the router
#: stops immediately (spec: invalid request, unsupported modality, permanent
#: invalid configuration).
TERMINAL_CATEGORIES = frozenset({
    'invalid_request',
    'unsupported_capability',
    'unauthorized',
    'configuration_error',
})


class ProviderCallError(Exception):
    """
    Raised inside `ai_gateway/providers/`. `detail` may contain upstream text
    for structured logs; it is never rendered into an API response.
    """

    def __init__(self, category: str, detail: str = '', *, provider: str = '',
                 model_id: str = '', status_code: int | None = None):
        super().__init__(f'{provider or "provider"}:{category}')
        self.category = category
        self.detail = detail
        self.provider = provider
        self.model_id = model_id
        self.status_code = status_code

    @property
    def retryable(self) -> bool:
        return self.category in RETRYABLE_CATEGORIES


# ── Public EcoIQ errors ───────────────────────────────────────────────────────

class AIGatewayError(Exception):
    """Base class — every subclass is safe to serialise straight to a client."""
    code = 'AI_ERROR'
    http_status = 500
    message = 'The EcoIQ AI service is unavailable.'

    def __init__(self, message: str = '', *, code: str = '', http_status: int | None = None):
        self.message = message or self.message
        self.code = code or self.code
        self.http_status = http_status or self.http_status
        super().__init__(self.message)

    def to_payload(self) -> dict:
        return {'success': False, 'error': {'code': self.code, 'message': self.message}}


class InvalidAIRequest(AIGatewayError):
    code = 'INVALID_REQUEST'
    http_status = 400
    message = 'The request could not be processed. Please check your input and try again.'


class InvalidModelSelection(InvalidAIRequest):
    code = 'INVALID_MODEL_SELECTION'
    message = 'That model is not available. Please choose a model from the list.'


class ModelNotPermitted(AIGatewayError):
    code = 'MODEL_NOT_PERMITTED'
    http_status = 403
    message = 'You do not have access to that model.'


class AIUnauthorized(AIGatewayError):
    code = 'UNAUTHORIZED'
    http_status = 401
    message = 'Sign in to use the EcoIQ assistant.'


class AIRateLimited(AIGatewayError):
    code = 'RATE_LIMITED'
    http_status = 429
    message = 'Too many requests. Please wait a moment and try again.'


class UpstreamMalformed(AIGatewayError):
    code = 'UPSTREAM_MALFORMED'
    http_status = 502
    message = 'The AI model returned an unusable response. Please try again.'


class FreeModelsUnavailable(AIGatewayError):
    code = 'FREE_MODELS_UNAVAILABLE'
    http_status = 503
    message = 'Free AI models are temporarily unavailable. Please try again later.'


class ProviderTimeout(AIGatewayError):
    code = 'PROVIDER_TIMEOUT'
    http_status = 504
    message = 'The AI model took too long to respond. Please try again.'


#: Terminal provider categories → the public error EcoIQ reports for them.
#: Anything not listed here is treated as "all free models exhausted", i.e.
#: FreeModelsUnavailable — never as an upgrade path to a paid model.
CATEGORY_TO_PUBLIC_ERROR = {
    'timeout': ProviderTimeout,
    'rate_limit': AIRateLimited,
    'malformed_response': UpstreamMalformed,
    'empty_response': UpstreamMalformed,
    'invalid_request': InvalidAIRequest,
    'unsupported_capability': InvalidAIRequest,
    'unauthorized': FreeModelsUnavailable,      # an EcoIQ-side credential fault
    'configuration_error': FreeModelsUnavailable,
}
