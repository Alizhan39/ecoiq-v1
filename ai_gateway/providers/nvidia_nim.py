"""
ai_gateway/providers/nvidia_nim.py — NVIDIA NIM adapter.

NVIDIA Developer Program hosted endpoints are **prototype and development
access**, not permanently free production inference. This adapter treats them
that way:

  * models are labelled "NVIDIA preview" / "Development only", never
    "Unlimited free";
  * while `NVIDIA_NIM_PUBLIC_PRODUCTION_ENABLED=False` they are visible only
    to staff and development users, and are excluded from the automatic
    fallback pool for ordinary production traffic;
  * the approved model list is a manually reviewed server-side allowlist —
    nothing is auto-approved, nothing is scraped from undocumented pages;
  * per-model capabilities and parameter defaults come from
    `settings.NVIDIA_MODEL_CONFIG`, because NVIDIA models do not all accept
    the same parameters.

Allowlisted ids are validated against the live NVIDIA API catalogue
(`GET {NVIDIA_NIM_BASE_URL}/models`) on every registry refresh — an id that
has disappeared from the catalogue drops out of the registry rather than
failing at request time.
"""
from __future__ import annotations

import logging

from django.conf import settings

from ai_gateway.base import BaseProvider
from ai_gateway.exceptions import ProviderCallError
from ai_gateway.providers import _openai_compat
from ai_gateway.types import CAPABILITY_CHAT, PROVIDER_NVIDIA_NIM, AIResponse, ProviderModel

logger = logging.getLogger('ecoiq.ai_gateway')

FREE_POLICY_NVIDIA_PROTOTYPE = 'nvidia_developer_prototype'


class NvidiaNimProvider(BaseProvider):
    provider_name = PROVIDER_NVIDIA_NIM
    enabled_setting = 'NVIDIA_NIM_ENABLED'
    api_key_setting = 'NVIDIA_NIM_API_KEY'

    # ── Catalogue ─────────────────────────────────────────────────────────────

    def fetch_catalog(self) -> list[dict]:
        data = _openai_compat.get_json(
            provider_name=self.provider_name,
            url=f'{settings.NVIDIA_NIM_BASE_URL.rstrip("/")}/models',
            api_key=self.api_key,
            timeout_seconds=settings.NVIDIA_NIM_TIMEOUT_SECONDS,
        )
        models = data.get('data')
        if not isinstance(models, list):
            raise ProviderCallError('malformed_response', 'catalogue has no data list',
                                    provider=self.provider_name)
        return [m for m in models if isinstance(m, dict)]

    @staticmethod
    def model_config(model_id: str) -> dict:
        return (getattr(settings, 'NVIDIA_MODEL_CONFIG', {}) or {}).get(model_id, {})

    @property
    def publicly_visible(self) -> bool:
        """
        True only when someone has explicitly approved public production use.
        `NVIDIA_NIM_PROTOTYPE_ONLY` is an independent second latch: both must
        agree before a NVIDIA model is offered to ordinary users.
        """
        return (
            bool(settings.NVIDIA_NIM_PUBLIC_PRODUCTION_ENABLED)
            and not settings.NVIDIA_NIM_PROTOTYPE_ONLY
        )

    def evaluate_catalog(self) -> tuple[list[ProviderModel], list[ProviderModel]]:
        if not self.is_configured:
            return [], []

        allowlist = self.allowlist()
        if not allowlist:
            return [], []

        catalog_ids = {entry.get('id') for entry in self.fetch_catalog()}
        approved: list[ProviderModel] = []
        rejected: list[ProviderModel] = []

        for model_id in sorted(allowlist):
            config = self.model_config(model_id)
            if not config:
                rejected.append(ProviderModel(
                    provider=self.provider_name, provider_model_id=model_id,
                    display_name=model_id, free_eligible=False,
                    rejection_reason='no reviewed entry in settings.NVIDIA_MODEL_CONFIG',
                ))
                continue

            if model_id not in catalog_ids:
                rejected.append(ProviderModel(
                    provider=self.provider_name, provider_model_id=model_id,
                    display_name=config.get('display_name', model_id), free_eligible=False,
                    rejection_reason='not present in the current NVIDIA API catalogue',
                ))
                continue

            # `public` in NVIDIA_MODEL_CONFIG can only ever *narrow* visibility.
            # It cannot widen it past the two environment latches above.
            public = bool(config.get('public', False)) and self.publicly_visible
            approved.append(ProviderModel(
                provider=self.provider_name,
                provider_model_id=model_id,
                display_name=config.get('display_name', model_id),
                description=config.get('description', ''),
                capabilities=frozenset(config.get('capabilities') or {CAPABILITY_CHAT}),
                context_length=config.get('context_length'),
                free_eligible=True,
                free_policy=FREE_POLICY_NVIDIA_PROTOTYPE,
                free_label='NVIDIA preview',
                public=public,
                development_only=bool(config.get('development_only', True)),
            ))

        return approved, rejected

    # ── Generation ────────────────────────────────────────────────────────────

    def generate(self, *, model_id, messages, temperature, max_tokens, request_id) -> AIResponse:
        config = self.model_config(model_id)
        if not config:
            # Defence in depth: the registry should never hand us an id that
            # is not in the reviewed config, so if it happens, stop.
            raise ProviderCallError('configuration_error', 'model not in NVIDIA_MODEL_CONFIG',
                                    provider=self.provider_name, model_id=model_id)

        # Not every NVIDIA model accepts the same parameters — send only the
        # ones this model's reviewed config declares.
        extra_body: dict = {}
        if config.get('top_p') is not None:
            extra_body['top_p'] = config['top_p']

        result = _openai_compat.chat_completion(
            provider_name=self.provider_name,
            base_url=settings.NVIDIA_NIM_BASE_URL,
            api_key=self.api_key,
            model_id=model_id,
            messages=messages,
            temperature=config.get('temperature', temperature),
            max_tokens=min(max_tokens, settings.NVIDIA_NIM_MAX_OUTPUT_TOKENS),
            timeout_seconds=settings.NVIDIA_NIM_TIMEOUT_SECONDS,
            request_id=request_id,
            extra_body=extra_body or None,
        )
        return AIResponse(
            content=result['content'],
            provider=self.provider_name,
            requested_model=model_id,
            resolved_model=result['resolved_model'],
            finish_reason=result['finish_reason'],
            input_tokens=result['input_tokens'],
            output_tokens=result['output_tokens'],
            metadata={'latency_ms': result['latency_ms'], 'development_only': True},
        )
