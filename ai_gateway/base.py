"""
ai_gateway/base.py — the one interface every EcoIQ AI provider implements.

Views never touch this. The call chain is strictly:

    Django view → AIService → AIModelRegistry → AIProviderRouter → AIProvider

A provider is responsible for exactly three things:
  1. saying whether it is configured at all (`is_configured`);
  2. reporting which of EcoIQ's allowlisted models it currently offers, with
     that provider's own free-policy verdict attached (`list_available_models`);
  3. running one generation and normalising the result to `AIResponse`.

It is *not* responsible for deciding whether a model may be shown to a user —
that is the registry's job, and it requires EcoIQ's allowlist to agree.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ai_gateway.types import AIResponse, ProviderModel


@runtime_checkable
class AIProvider(Protocol):
    provider_name: str

    def generate(
        self,
        *,
        model_id: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        request_id: str,
    ) -> AIResponse:
        ...

    def list_available_models(self) -> list[ProviderModel]:
        ...


class BaseProvider:
    """
    Shared behaviour for the three concrete providers. Not required by the
    Protocol above — a provider only has to match the signatures — but it
    keeps the free-policy bookkeeping identical across all three.
    """
    provider_name: str = ''
    enabled_setting: str = ''
    api_key_setting: str = ''

    # ── Configuration ─────────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        from django.conf import settings
        return bool(getattr(settings, self.enabled_setting, False))

    @property
    def api_key(self) -> str:
        from django.conf import settings
        return (getattr(settings, self.api_key_setting, '') or '').strip()

    @property
    def is_configured(self) -> bool:
        """
        A provider with no credential is *not configured*, and its models never
        enter the registry at all. That is deliberate: it means "missing API
        key" can never appear as a mid-request fallback reason, so the router
        never has to distinguish a transient outage from a permanent
        misconfiguration while a user is waiting.
        """
        return self.enabled and bool(self.api_key)

    def unavailable_reason(self) -> str:
        if not self.enabled:
            return 'disabled'
        if not self.api_key:
            return 'missing_credentials'
        return ''

    # ── Allowlist ─────────────────────────────────────────────────────────────

    def allowlist(self) -> frozenset[str]:
        """EcoIQ's server-side allowlist for this provider (never user input)."""
        from django.conf import settings
        raw = (getattr(settings, 'AI_MODEL_ALLOWLIST', {}) or {}).get(self.provider_name, set())
        return frozenset(raw)

    # ── Interface ─────────────────────────────────────────────────────────────

    def list_available_models(self) -> list[ProviderModel]:
        approved, _rejected = self.evaluate_catalog()
        return approved

    def evaluate_catalog(self) -> tuple[list[ProviderModel], list[ProviderModel]]:
        """
        Return (approved, rejected). `rejected` explains why an allowlisted
        model did not qualify — surfaced by `manage.py refresh_ai_models` and
        the staff health endpoint, never by the public models endpoint.
        """
        raise NotImplementedError

    def generate(self, *, model_id, messages, temperature, max_tokens, request_id) -> AIResponse:
        raise NotImplementedError
