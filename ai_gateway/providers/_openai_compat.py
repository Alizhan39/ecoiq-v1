"""
ai_gateway/providers/_openai_compat.py — one HTTP client for the three
OpenAI-compatible chat endpoints EcoIQ talks to.

Why httpx and not the `openai` SDK: the SDK is not a dependency of this
project (it is absent from requirements.txt and from the project's .venv),
while httpx already is — it backs
`backend_intelligence_engine/services/http_client.py`. All three providers
here speak the identical `POST {base_url}/chat/completions` wire format, so
one ~150-line client replaces three SDK client objects and keeps the test
suite mockable at a single seam.

That shared client is NOT reused directly: it retries internally with
`time.sleep()`, which is right for a background Celery task and wrong for a
user-facing request where the router owns the attempt budget
(`AI_MAX_PROVIDER_ATTEMPTS`). This client makes exactly one attempt and
raises a categorised `ProviderCallError`; deciding what to do next is the
router's job, not the transport's.
"""
from __future__ import annotations

import logging
import time

import httpx

from ai_gateway.exceptions import ProviderCallError

logger = logging.getLogger('ecoiq.ai_gateway.http')

USER_AGENT = 'EcoIQ-AI-Gateway/1.0 (+https://ecoiq.uk/about)'

#: Upstream status → normalised failure category. Anything not listed maps by
#: range below (4xx → invalid_request, 5xx → server_error).
_STATUS_CATEGORIES = {
    401: 'unauthorized',
    403: 'unauthorized',
    402: 'credits_exhausted',   # "payment required" — free allowance exhausted
    404: 'model_unavailable',
    408: 'timeout',
    413: 'invalid_request',
    422: 'invalid_request',
    429: 'rate_limit',
    503: 'model_unavailable',
    504: 'timeout',
}

#: Substrings that mean "your free allowance ran out", regardless of status
#: code — some providers return 400/500 with an explanatory body instead of
#: 402. Matching is lowercase and substring-based on the error message only.
_CREDIT_EXHAUSTED_MARKERS = (
    'insufficient credit',
    'insufficient_credits',
    'out of credits',
    'credit balance',
    'quota exceeded',
    'exceeded your current quota',
    'free tier limit',
    'add more credits',
)


def _categorise_status(status_code: int, body_text: str) -> str:
    lowered = (body_text or '').lower()
    if any(marker in lowered for marker in _CREDIT_EXHAUSTED_MARKERS):
        return 'credits_exhausted'
    if status_code in _STATUS_CATEGORIES:
        return _STATUS_CATEGORIES[status_code]
    if status_code >= 500:
        return 'server_error'
    if status_code >= 400:
        return 'invalid_request'
    return 'server_error'


def _extract_text(content) -> str:
    """
    Normalise the `message.content` field, which is a plain string on most
    providers but a list of typed parts on some. Only `text` parts are kept:
    a `thinking` / `reasoning` part is dropped here and never reaches EcoIQ.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get('type') in ('text', 'output_text'):
                parts.append(part.get('text', '') or '')
        return ''.join(parts)
    return ''


def chat_completion(
    *,
    provider_name: str,
    base_url: str,
    api_key: str,
    model_id: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    timeout_seconds: float,
    request_id: str,
    auth_scheme: str = 'Bearer',
    extra_headers: dict | None = None,
    extra_body: dict | None = None,
) -> dict:
    """
    One attempt against one model. Returns a normalised dict:

        {content, resolved_model, finish_reason, input_tokens,
         output_tokens, upstream_provider}

    Raises `ProviderCallError` on every failure path — never returns partial
    or fabricated output, and never raises a bare httpx exception upwards.
    """
    if not api_key:
        raise ProviderCallError('configuration_error', 'missing api key',
                                provider=provider_name, model_id=model_id)

    url = f'{base_url.rstrip("/")}/chat/completions'
    headers = {
        'Authorization': f'{auth_scheme} {api_key}'.strip() if auth_scheme else api_key,
        'Content-Type': 'application/json',
        'User-Agent': USER_AGENT,
    }
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        'model': model_id,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'stream': False,
    }
    if extra_body:
        # Server-controlled only. `extra_body` is built from Django settings by
        # the provider adapter — a browser can never contribute to it.
        payload.update(extra_body)

    started = time.monotonic()
    try:
        with httpx.Client(timeout=httpx.Timeout(timeout_seconds), follow_redirects=False) as client:
            response = client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise ProviderCallError('timeout', type(exc).__name__,
                                provider=provider_name, model_id=model_id) from exc
    except httpx.HTTPError as exc:
        raise ProviderCallError('connection', type(exc).__name__,
                                provider=provider_name, model_id=model_id) from exc

    elapsed_ms = int((time.monotonic() - started) * 1000)

    if response.status_code >= 400:
        # Body is read for categorisation and truncated structured logging
        # only — it is never propagated into an API response.
        body = response.text[:500]
        category = _categorise_status(response.status_code, body)
        logger.warning(
            'ai_gateway.upstream_error provider=%s status=%s category=%s latency_ms=%s request_id=%s',
            provider_name, response.status_code, category, elapsed_ms, request_id,
        )
        raise ProviderCallError(category, body, provider=provider_name,
                                model_id=model_id, status_code=response.status_code)

    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderCallError('malformed_response', 'non-json body',
                                provider=provider_name, model_id=model_id) from exc

    if not isinstance(data, dict):
        raise ProviderCallError('malformed_response', 'non-object body',
                                provider=provider_name, model_id=model_id)

    # Some OpenAI-compatible gateways answer 200 with an `error` envelope.
    if data.get('error'):
        err = data['error']
        detail = err.get('message', '') if isinstance(err, dict) else str(err)
        raise ProviderCallError(_categorise_status(200, detail) if detail else 'server_error',
                                detail[:500], provider=provider_name, model_id=model_id)

    choices = data.get('choices') or []
    if not choices or not isinstance(choices, list):
        raise ProviderCallError('empty_response', 'no choices',
                                provider=provider_name, model_id=model_id)

    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get('message') if isinstance(first.get('message'), dict) else {}
    content = _extract_text(message.get('content'))

    if not content.strip():
        raise ProviderCallError('empty_response', 'empty content',
                                provider=provider_name, model_id=model_id)

    usage = data.get('usage') if isinstance(data.get('usage'), dict) else {}

    logger.info(
        'ai_gateway.upstream_ok provider=%s latency_ms=%s finish=%s request_id=%s',
        provider_name, elapsed_ms, first.get('finish_reason'), request_id,
    )

    return {
        'content': content,
        # `data['model']` is the concrete model the upstream actually ran. For
        # OpenRouter's free router this differs from the requested id, which is
        # exactly the value the spec asks EcoIQ to record.
        'resolved_model': data.get('model') or None,
        'finish_reason': first.get('finish_reason'),
        'input_tokens': usage.get('prompt_tokens'),
        'output_tokens': usage.get('completion_tokens'),
        'upstream_provider': data.get('provider') or '',
        'latency_ms': elapsed_ms,
    }


def get_json(
    *,
    provider_name: str,
    url: str,
    api_key: str,
    timeout_seconds: float,
    auth_scheme: str = 'Bearer',
    params: dict | None = None,
    extra_headers: dict | None = None,
) -> dict:
    """Catalogue fetch. Same single-attempt, categorised-failure contract."""
    headers = {'Accept': 'application/json', 'User-Agent': USER_AGENT}
    if api_key:
        headers['Authorization'] = f'{auth_scheme} {api_key}'.strip() if auth_scheme else api_key
    if extra_headers:
        headers.update(extra_headers)

    try:
        with httpx.Client(timeout=httpx.Timeout(timeout_seconds), follow_redirects=True) as client:
            response = client.get(url, headers=headers, params=params or None)
    except httpx.TimeoutException as exc:
        raise ProviderCallError('timeout', type(exc).__name__, provider=provider_name) from exc
    except httpx.HTTPError as exc:
        raise ProviderCallError('connection', type(exc).__name__, provider=provider_name) from exc

    if response.status_code >= 400:
        raise ProviderCallError(
            _categorise_status(response.status_code, response.text[:300]),
            f'HTTP {response.status_code}', provider=provider_name,
            status_code=response.status_code,
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderCallError('malformed_response', 'non-json catalogue',
                                provider=provider_name) from exc

    if not isinstance(data, dict):
        raise ProviderCallError('malformed_response', 'non-object catalogue',
                                provider=provider_name)
    return data
