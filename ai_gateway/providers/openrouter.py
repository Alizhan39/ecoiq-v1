"""
ai_gateway/providers/openrouter.py — OpenRouter adapter.

Free eligibility here is decided by *price*, not by name. A model whose id
ends in `:free` still has to prove every request-relevant pricing dimension
is numerically zero, and a model with no `:free` suffix is perfectly welcome
if it does. The two are unrelated: OpenRouter's catalogue contains
zero-priced models without the suffix, and the suffix is not a contract.

Pricing is parsed with `decimal.Decimal`, never `float`. OpenRouter reports
prices as decimal strings like "0.00000009"; binary floating point cannot
represent those exactly, and "is this exactly zero?" is precisely the
question where that matters.
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings

from ai_gateway.base import BaseProvider
from ai_gateway.exceptions import ProviderCallError
from ai_gateway.providers import _openai_compat
from ai_gateway.types import (
    CAPABILITY_CHAT, CAPABILITY_TOOLS, CAPABILITY_VISION,
    PROVIDER_OPENROUTER, AIResponse, ProviderModel,
)

logger = logging.getLogger('ecoiq.ai_gateway')

#: Pricing dimensions that must be present AND exactly zero for a text-chat
#: request. `request` is optional in OpenRouter's payload (absent means "no
#: per-request charge"), but if present it must also be zero.
REQUIRED_ZERO_DIMENSIONS = ('prompt', 'completion')
OPTIONAL_ZERO_DIMENSIONS = ('request', 'internal_reasoning')

#: Dimensions that only bill for modalities EcoIQ does not send or accept in a
#: text-chat request (we never upload audio, and we reject models that emit
#: audio/image). Ignoring them is safe *because* the modality gate below runs.
IGNORED_DIMENSIONS = frozenset({
    'image', 'audio', 'input_audio_cache', 'web_search',
    'input_cache_read', 'input_cache_write', 'input_cache_write_1h',
    'image_output', 'audio_output', 'overrides',
})

FREE_POLICY_ZERO_PRICE = 'openrouter_zero_price'
FREE_POLICY_FREE_ROUTER = 'openrouter_free_router'


def _is_exactly_zero(raw) -> bool:
    """
    True only for a value that parses cleanly as a decimal zero. Missing,
    null, empty, non-numeric or negative values all return False — ambiguity
    is a rejection, never an approval.
    """
    if raw is None:
        return False
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError, TypeError):
        return False
    return value == 0


class OpenRouterProvider(BaseProvider):
    provider_name = PROVIDER_OPENROUTER
    enabled_setting = 'OPENROUTER_ENABLED'
    api_key_setting = 'OPENROUTER_API_KEY'

    # ── Catalogue ─────────────────────────────────────────────────────────────

    def fetch_catalog(self) -> list[dict]:
        data = _openai_compat.get_json(
            provider_name=self.provider_name,
            url=f'{settings.OPENROUTER_BASE_URL.rstrip("/")}/models',
            api_key=self.api_key,
            timeout_seconds=settings.OPENROUTER_TIMEOUT_SECONDS,
        )
        models = data.get('data')
        if not isinstance(models, list):
            raise ProviderCallError('malformed_response', 'catalogue has no data list',
                                    provider=self.provider_name)
        return [m for m in models if isinstance(m, dict)]

    # ── Free policy ───────────────────────────────────────────────────────────

    def evaluate_free_eligibility(self, entry: dict) -> tuple[bool, str, str]:
        """
        Return (eligible, policy, rejection_reason) for one catalogue entry.

        A selectable OpenRouter model must satisfy all of:
          1. an approved free variant, or the approved free router;
          2. every request-relevant pricing dimension exactly zero;
          3. EcoIQ allowlist membership (checked by the caller);
          4. text in, text out;
          5. not expired / not withdrawn.
        """
        model_id = entry.get('id', '')

        # (5) expiry — an expired model is not selectable at any price.
        if entry.get('expiration_date'):
            return False, '', f'expired ({entry["expiration_date"]})'

        # (4) modality. Checked *before* price, because a model can be free on
        # `prompt`/`completion` while billing through an image/audio dimension —
        # google/lyria-3-pro-preview in the live catalogue does exactly that.
        architecture = entry.get('architecture') or {}
        input_modalities = set(architecture.get('input_modalities') or [])
        output_modalities = set(architecture.get('output_modalities') or [])
        if not input_modalities or not output_modalities:
            return False, '', 'modalities missing from catalogue entry'
        if 'text' not in input_modalities:
            return False, '', 'does not accept text input'
        if output_modalities != {'text'}:
            extra = ','.join(sorted(output_modalities - {'text'}))
            return False, '', f'emits non-text output ({extra})'

        # (2) pricing.
        pricing = entry.get('pricing')
        if not isinstance(pricing, dict) or not pricing:
            return False, '', 'pricing missing'

        for dimension in REQUIRED_ZERO_DIMENSIONS:
            if dimension not in pricing:
                return False, '', f'pricing dimension "{dimension}" missing'
            if not _is_exactly_zero(pricing[dimension]):
                return False, '', f'pricing dimension "{dimension}" is not zero'

        for dimension in OPTIONAL_ZERO_DIMENSIONS:
            if dimension in pricing and not _is_exactly_zero(pricing[dimension]):
                return False, '', f'pricing dimension "{dimension}" is not zero'

        # Any *unrecognised* dimension is a rejection rather than a shrug: a new
        # billing axis added by OpenRouter must be reviewed before EcoIQ treats
        # a model carrying it as free.
        known = set(REQUIRED_ZERO_DIMENSIONS) | set(OPTIONAL_ZERO_DIMENSIONS) | IGNORED_DIMENSIONS
        unknown = sorted(set(pricing) - known)
        if unknown:
            return False, '', f'unrecognised pricing dimension(s): {",".join(unknown)}'

        # (1) approved free variant or approved free router.
        if model_id == settings.OPENROUTER_FREE_ROUTER_MODEL:
            if not settings.OPENROUTER_FREE_ROUTER_ENABLED:
                return False, '', 'free router disabled by configuration'
            return True, FREE_POLICY_FREE_ROUTER, ''

        return True, FREE_POLICY_ZERO_PRICE, ''

    @staticmethod
    def _capabilities(entry: dict) -> frozenset[str]:
        architecture = entry.get('architecture') or {}
        supported = set(entry.get('supported_parameters') or [])
        capabilities = {CAPABILITY_CHAT}
        if 'image' in set(architecture.get('input_modalities') or []):
            capabilities.add(CAPABILITY_VISION)
        if 'tools' in supported:
            capabilities.add(CAPABILITY_TOOLS)
        return frozenset(capabilities)

    def evaluate_catalog(self) -> tuple[list[ProviderModel], list[ProviderModel]]:
        if not self.is_configured:
            return [], []

        allowlist = self.allowlist()
        if not allowlist:
            return [], []

        catalog = {entry.get('id'): entry for entry in self.fetch_catalog()}
        approved: list[ProviderModel] = []
        rejected: list[ProviderModel] = []

        for model_id in sorted(allowlist):
            entry = catalog.get(model_id)
            if entry is None:
                rejected.append(ProviderModel(
                    provider=self.provider_name, provider_model_id=model_id,
                    display_name=model_id, free_eligible=False,
                    rejection_reason='not present in the current OpenRouter catalogue',
                ))
                continue

            eligible, policy, reason = self.evaluate_free_eligibility(entry)
            model = ProviderModel(
                provider=self.provider_name,
                provider_model_id=model_id,
                display_name=entry.get('name') or model_id,
                description=(entry.get('description') or '').strip(),
                capabilities=self._capabilities(entry),
                context_length=entry.get('context_length'),
                free_eligible=eligible,
                free_policy=policy,
                free_label='Free',
                rejection_reason=reason,
            )
            (approved if eligible else rejected).append(model)

        return approved, rejected

    # ── Generation ────────────────────────────────────────────────────────────

    def _extra_body(self) -> dict:
        """
        Routing policy is decided here, server-side, from Django settings. The
        browser submits an opaque model key and nothing else — it can never
        contribute provider preferences, routing rules or ZDR settings.
        """
        provider_prefs: dict = {}
        if settings.OPENROUTER_ZDR_ENABLED:
            provider_prefs['zdr'] = True
        # Belt and braces on top of the catalogue-level price check: even if a
        # model's pricing changed between catalogue refresh and this request,
        # OpenRouter must not silently route it to a paid endpoint.
        provider_prefs['allow_fallbacks'] = False
        return {'provider': provider_prefs} if provider_prefs else {}

    def generate(self, *, model_id, messages, temperature, max_tokens, request_id) -> AIResponse:
        result = _openai_compat.chat_completion(
            provider_name=self.provider_name,
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=self.api_key,
            model_id=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=min(max_tokens, settings.OPENROUTER_MAX_OUTPUT_TOKENS),
            timeout_seconds=settings.OPENROUTER_TIMEOUT_SECONDS,
            request_id=request_id,
            extra_headers={
                'HTTP-Referer': settings.OPENROUTER_SITE_URL,
                'X-Title': settings.OPENROUTER_APP_NAME,
                'X-OpenRouter-Title': settings.OPENROUTER_APP_NAME,
            },
            extra_body=self._extra_body(),
        )
        return AIResponse(
            content=result['content'],
            provider=self.provider_name,
            requested_model=model_id,
            resolved_model=result['resolved_model'],
            finish_reason=result['finish_reason'],
            input_tokens=result['input_tokens'],
            output_tokens=result['output_tokens'],
            metadata={'latency_ms': result['latency_ms']},
        )
