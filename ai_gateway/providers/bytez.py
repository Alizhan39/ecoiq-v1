"""
ai_gateway/providers/bytez.py — Bytez Model API adapter.

Two honest caveats are baked into this file.

1. **The catalogue schema here is unverified.** `GET
   https://api.bytez.com/models/v2/list/models?task=chat` returns 401 without
   a key, and this integration was written without a Bytez credential. Every
   field name below is therefore treated as a *hypothesis*: the free check
   requires explicit positive evidence and rejects on anything missing or
   ambiguous. The practical consequence is that Bytez contributes **zero**
   models until someone with a key runs `manage.py refresh_ai_models
   --explain`, reads the rejection reasons, and confirms the real field names.
   That is the intended failure mode — a wrong guess must never approve a
   model, only decline one.

2. **"Free plan" is not "free forever".** Bytez free-plan access can consume
   included credits. So: auto-reload is never enabled, credits are never
   purchased, a larger paid model is never substituted, and exhausted credits
   are treated as *unavailable* (a fallback trigger inside the free pool), not
   as a reason to spend. Bytez models are labelled "Free-plan model", never
   "Unlimited free".
"""
from __future__ import annotations

import logging
import re

from django.conf import settings

from ai_gateway.base import BaseProvider
from ai_gateway.exceptions import ProviderCallError
from ai_gateway.providers import _openai_compat
from ai_gateway.types import CAPABILITY_CHAT, PROVIDER_BYTEZ, AIResponse, ProviderModel

logger = logging.getLogger('ecoiq.ai_gateway')

FREE_POLICY_BYTEZ_FREE_TIER = 'bytez_free_tier_meter'

#: Candidate field names for the free-access meter. `sm-free` is the documented
#: indicator at the time of writing; confirm against current Bytez docs before
#: relying on it. Configurable via settings.BYTEZ_FREE_METERS.
DEFAULT_FREE_METERS = frozenset({'sm-free'})

#: Keys the catalogue might use for the meter, in priority order.
_METER_KEYS = ('meter', 'meterName', 'serviceMeter', 'accessMeter', 'tier')

#: Keys the catalogue might use for parameter count / model size.
_SIZE_KEYS = ('params', 'parameters', 'parameterCount', 'modelSize', 'size')

#: Providers whose models are closed-source and paid wherever they are hosted.
#: Routing these through Bytez while AI_FREE_ONLY is on is forbidden outright.
CLOSED_SOURCE_VENDORS = frozenset({
    'openai', 'anthropic', 'google', 'cohere', 'ai21', 'ai21labs',
    'perplexity', 'xai', 'x-ai', 'reka', 'aleph-alpha', 'deepmind',
})

_SIZE_RE = re.compile(r'^\s*([0-9]+(?:\.[0-9]+)?)\s*([bBmM])?\s*$')


def _parse_parameter_count_billions(raw) -> float | None:
    """
    Normalise "7B" / "7b" / "7000000000" / 7.0 to a float count in billions.
    Returns None when the value cannot be understood — which the caller treats
    as a rejection, not a pass.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        value = float(raw)
        return value / 1e9 if value > 1000 else value
    match = _SIZE_RE.match(str(raw))
    if not match:
        return None
    value = float(match.group(1))
    suffix = (match.group(2) or '').lower()
    if suffix == 'm':
        return value / 1000.0
    if suffix == 'b':
        return value
    return value / 1e9 if value > 1000 else value


class BytezProvider(BaseProvider):
    provider_name = PROVIDER_BYTEZ
    enabled_setting = 'BYTEZ_ENABLED'
    api_key_setting = 'BYTEZ_API_KEY'

    # ── Catalogue ─────────────────────────────────────────────────────────────

    def fetch_catalog(self) -> list[dict]:
        data = _openai_compat.get_json(
            provider_name=self.provider_name,
            url=settings.BYTEZ_MODELS_URL,
            api_key=self.api_key,
            # Bytez documents a bare key in Authorization, not `Bearer <key>`.
            auth_scheme='',
            timeout_seconds=settings.BYTEZ_TIMEOUT_SECONDS,
            params={'task': 'chat'},
        )
        for container in ('models', 'data', 'output', 'results'):
            models = data.get(container)
            if isinstance(models, list):
                return [m for m in models if isinstance(m, dict)]
        raise ProviderCallError('malformed_response', 'catalogue has no recognised model list',
                                provider=self.provider_name)

    @staticmethod
    def _model_id(entry: dict) -> str:
        for key in ('id', 'model', 'modelId', 'name'):
            value = entry.get(key)
            if isinstance(value, str) and value:
                return value
        return ''

    @staticmethod
    def _meter(entry: dict) -> str | None:
        for key in _METER_KEYS:
            value = entry.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def evaluate_free_eligibility(self, entry: dict) -> tuple[bool, str, str]:
        """
        A Bytez model is admitted only when it is: task=chat, on the free
        access meter, within the free-plan size limit, and open-weights.
        Every unknown is a rejection.
        """
        # (2) task must be chat.
        task = entry.get('task') or entry.get('taskType') or entry.get('pipeline_tag')
        if not isinstance(task, str) or task.strip().lower() not in ('chat', 'chat-completion', 'text-generation-chat'):
            return False, '', f'task is not "chat" (got {task!r})'

        # (7) closed-source paid provider models are never routed through Bytez
        # while AI_FREE_ONLY is on.
        model_id = self._model_id(entry)
        vendor = model_id.split('/')[0].lower() if '/' in model_id else ''
        open_source_flag = entry.get('openSource', entry.get('open_source'))
        if not settings.BYTEZ_ALLOW_CLOSED_MODELS:
            if vendor in CLOSED_SOURCE_VENDORS:
                return False, '', f'closed-source paid vendor "{vendor}"'
            if open_source_flag is False:
                return False, '', 'catalogue marks the model as not open-source'

        # (3)+(4) free-tier classification via the free access meter.
        # Deliberately NOT inferred from meterPrice alone — a zero price on a
        # paid meter still draws down purchased credits.
        free_meters = frozenset(getattr(settings, 'BYTEZ_FREE_METERS', DEFAULT_FREE_METERS))
        meter = self._meter(entry)
        if meter is None:
            return False, '', 'no free-access meter field found in the catalogue entry'
        if meter not in free_meters:
            return False, '', f'meter "{meter}" is not an approved free meter'

        # (5) free-plan model-size restriction.
        raw_size = next((entry[k] for k in _SIZE_KEYS if k in entry), None)
        size_b = _parse_parameter_count_billions(raw_size)
        if size_b is None:
            return False, '', 'model size missing or unparseable'
        limit_b = float(getattr(settings, 'BYTEZ_FREE_MAX_PARAMETERS_B', 10))
        if size_b > limit_b:
            return False, '', f'model size {size_b:g}B exceeds the free-plan limit of {limit_b:g}B'

        return True, FREE_POLICY_BYTEZ_FREE_TIER, ''

    def evaluate_catalog(self) -> tuple[list[ProviderModel], list[ProviderModel]]:
        if not self.is_configured:
            return [], []

        # BYTEZ_FREE_ONLY=false while AI_FREE_ONLY=true is a contradiction. The
        # stricter global policy wins and Bytez contributes nothing, rather
        # than a per-provider flag being able to widen the global one.
        if settings.AI_FREE_ONLY and not settings.BYTEZ_FREE_ONLY:
            logger.warning(
                'ai_gateway.policy_conflict provider=bytez '
                'reason=BYTEZ_FREE_ONLY_false_under_AI_FREE_ONLY',
            )
            return [], []

        allowlist = self.allowlist()
        if not allowlist:
            return [], []

        catalog = {self._model_id(entry): entry for entry in self.fetch_catalog()}
        approved: list[ProviderModel] = []
        rejected: list[ProviderModel] = []

        for model_id in sorted(allowlist):
            entry = catalog.get(model_id)
            if entry is None:
                rejected.append(ProviderModel(
                    provider=self.provider_name, provider_model_id=model_id,
                    display_name=model_id, free_eligible=False,
                    rejection_reason='not present in the current authenticated Bytez catalogue',
                ))
                continue

            eligible, policy, reason = self.evaluate_free_eligibility(entry)
            approved_model = ProviderModel(
                provider=self.provider_name,
                provider_model_id=model_id,
                display_name=entry.get('displayName') or entry.get('name') or model_id,
                description=(entry.get('description') or '').strip(),
                capabilities=frozenset({CAPABILITY_CHAT}),
                context_length=entry.get('contextLength') or entry.get('context_length'),
                free_eligible=eligible,
                free_policy=policy,
                # Never "Unlimited free" — Bytez free-plan access can draw on
                # included credits.
                free_label='Free-plan model',
                rejection_reason=reason,
            )
            (approved if eligible else rejected).append(approved_model)

        return approved, rejected

    # ── Generation ────────────────────────────────────────────────────────────

    def generate(self, *, model_id, messages, temperature, max_tokens, request_id) -> AIResponse:
        if settings.AI_FREE_ONLY and settings.BYTEZ_ALLOW_PAID_CREDITS:
            # A misconfiguration that would let a "free" request spend credits.
            # Refuse rather than spend; the router treats this as terminal.
            raise ProviderCallError(
                'configuration_error',
                'BYTEZ_ALLOW_PAID_CREDITS is true while AI_FREE_ONLY is true',
                provider=self.provider_name, model_id=model_id,
            )

        result = _openai_compat.chat_completion(
            provider_name=self.provider_name,
            base_url=settings.BYTEZ_OPENAI_BASE_URL,
            api_key=self.api_key,
            model_id=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=min(max_tokens, settings.BYTEZ_MAX_OUTPUT_TOKENS),
            timeout_seconds=settings.BYTEZ_TIMEOUT_SECONDS,
            request_id=request_id,
            auth_scheme='',   # bare key, matching the catalogue endpoint
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
