"""
ai_gateway/views.py — the three EcoIQ AI gateway endpoints.

    GET  /api/ai/models/   authenticated  — the selectable model catalogue
    POST /api/ai/chat/     authenticated  — one generation, one model
    GET  /api/ai/health/   staff only     — configuration + freshness

Written in the same style as the rest of the EcoIQ JSON API (`mizan/views.py`,
`api/views.py`): DRF function views with explicit permission and throttle
classes. Authentication is inherited from the project defaults — see the note
below the imports for why this one differs from its neighbours.

These views contain no provider logic whatsoever. They validate authentication,
call `AIService`, and translate `AIGatewayError` into a stable HTTP status —
that is the whole job.
"""
from __future__ import annotations

import logging

from django.conf import settings
from rest_framework.decorators import (
    api_view, permission_classes, throttle_classes,
)
from rest_framework.response import Response

from ai_gateway.exceptions import AIGatewayError, InvalidAIRequest
from ai_gateway.permissions import IsEcoIQAuthenticated, IsEcoIQStaff
from ai_gateway.providers import all_providers
from ai_gateway.registry import registry
from ai_gateway.service import reject_untrusted_routing_fields, service
from ai_gateway.throttles import AICatalogThrottle, AIChatIPThrottle, AIChatUserThrottle

logger = logging.getLogger('ecoiq.ai_gateway')

# Authentication is deliberately NOT pinned here. These views inherit
# `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`, which is where EcoIQ
# already declares its authentication chain (session, B2B API key, and the
# mobile device-token scheme where that app is installed). Listing the classes
# explicitly — as `api/views.py` and `mizan/views.py` do — would both duplicate
# that decision and hard-couple this app to whichever authentication apps
# happen to be installed. `IsEcoIQAuthenticated` below is what actually decides
# who gets in, and it accepts any of those schemes.
#
# Permission and throttle classes ARE pinned per view, because those genuinely
# differ from the project defaults (staff-only health, AI-specific rate limits).


def _error_response(exc: AIGatewayError) -> Response:
    return Response(exc.to_payload(), status=exc.http_status)


# ── Model discovery ───────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsEcoIQAuthenticated])
@throttle_classes([AICatalogThrottle])
def ai_models(request):
    """
    GET /api/ai/models/

    Under automatic routing this is a STAFF tool, not a public selector: a
    normal caller gets `selection_available: false` and an empty model list, so
    no public UI can build a model picker from it.

    For staff it returns only models that are enabled, free-eligible and
    currently offered by a configured provider. It never returns API keys, base
    URLs, private or disabled models, paid models, provider balances, raw
    provider errors or pricing internals.
    """
    try:
        payload = service.list_models(request.user if request.user.is_authenticated else None)
    except AIGatewayError as exc:
        return _error_response(exc)
    return Response(payload)


# ── Chat ──────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsEcoIQAuthenticated])
@throttle_classes([AIChatUserThrottle, AIChatIPThrottle])
def ai_chat(request):
    """
    POST /api/ai/chat/

    Body: {message, language, history, context, mode}

    EcoIQ selects the model automatically. `provider`, `base_url`, `model`,
    `free_only` and provider routing preferences are REJECTED with 400 — they
    are never legitimate from a client. `model_key` is accepted only from staff
    (benchmarking) and ignored for everyone else, so a stale client that still
    remembers a selection keeps working rather than erroring.

    `mode` is one of the routing modes (auto / quick / deep). It adjusts
    routing requirements; it does not name a model.
    """
    data = request.data
    if not isinstance(data, dict):
        return _error_response(InvalidAIRequest('Request body must be a JSON object.'))

    try:
        reject_untrusted_routing_fields(data)
        payload = service.chat(
            user=request.user if request.user.is_authenticated else None,
            message=data.get('message'),
            model_key=data.get('model_key'),
            language=data.get('language'),
            history=data.get('history'),
            context=data.get('context'),
            mode=data.get('mode'),
        )
    except AIGatewayError as exc:
        return _error_response(exc)
    except Exception:  # noqa: BLE001
        # An unexpected internal fault must not leak a traceback or an upstream
        # body to the client. Full detail goes to the server log only.
        logger.exception('ai_gateway.chat_unhandled_error')
        return _error_response(AIGatewayError())

    return Response(payload)


# ── Staff health ──────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsEcoIQStaff])
def ai_health(request):
    """
    GET /api/ai/health/ — staff only.

    Reports configuration and catalogue freshness. Makes no generation call of
    any kind, and never returns keys, partial keys, balances, private headers,
    complete raw catalogues or raw provider errors — provider failures appear
    as normalised category strings only.
    """
    snapshot = registry.get_snapshot()

    providers = []
    for provider in all_providers():
        providers.append({
            'provider': provider.provider_name,
            'enabled': provider.enabled,
            # Boolean only — never the key, never a prefix, never a length.
            'configured': provider.is_configured,
            'unavailable_reason': provider.unavailable_reason(),
            'allowlisted_models': len(provider.allowlist()),
            'approved_models': sum(1 for m in snapshot.models
                                   if m.provider == provider.provider_name),
        })

    return Response({
        'free_only': bool(settings.AI_FREE_ONLY),
        'allow_paid_models': bool(settings.AI_ALLOW_PAID_MODELS),
        'selection_mode': settings.AI_MODEL_SELECTION_MODE,
        'default_model_key': settings.AI_DEFAULT_MODEL_KEY,
        'automatic_fallback': bool(settings.AI_ALLOW_AUTOMATIC_FALLBACK),
        'max_provider_attempts': int(settings.AI_MAX_PROVIDER_ATTEMPTS),
        'providers': providers,
        'catalogue': {
            'refreshed_at': snapshot.refreshed_at,
            'stale': snapshot.stale,
            'cache_seconds': int(settings.AI_MODEL_CATALOG_CACHE_SECONDS),
            'approved_free_models': len(snapshot.models),
            'rejected_models': len(snapshot.rejected),
        },
        # Normalised categories, e.g. {"openrouter": "rate_limit"}.
        'recent_provider_errors': snapshot.provider_errors,
        'nvidia': {
            'development_only': not (
                settings.NVIDIA_NIM_PUBLIC_PRODUCTION_ENABLED
                and not settings.NVIDIA_NIM_PROTOTYPE_ONLY
            ),
            'public_production_enabled': bool(settings.NVIDIA_NIM_PUBLIC_PRODUCTION_ENABLED),
            'prototype_only': bool(settings.NVIDIA_NIM_PROTOTYPE_ONLY),
        },
    })
