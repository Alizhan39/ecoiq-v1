"""
ai_gateway/types.py — the normalised data shapes every provider in the EcoIQ
AI gateway must speak.

Nothing here is provider-specific. A raw OpenRouter / Bytez / NVIDIA NIM
response object never leaves `ai_gateway/providers/` — it is converted to an
`AIResponse` at the provider boundary, and `AIResponse` deliberately has no
field for hidden reasoning, chain-of-thought, provider debug payloads or the
system prompt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Capabilities ──────────────────────────────────────────────────────────────
# Deliberately a tiny, closed vocabulary: these are the only capability names
# the registry, the API and the frontend badges all agree on.
CAPABILITY_CHAT = 'chat'      # text in → text out
CAPABILITY_VISION = 'vision'  # accepts image input
CAPABILITY_TOOLS = 'tools'    # supports tool/function calling

ALL_CAPABILITIES = frozenset({CAPABILITY_CHAT, CAPABILITY_VISION, CAPABILITY_TOOLS})

# ── Availability ──────────────────────────────────────────────────────────────
AVAILABILITY_AVAILABLE = 'available'
AVAILABILITY_DEGRADED = 'degraded'      # recently failed, still eligible to try
AVAILABILITY_UNAVAILABLE = 'unavailable'  # cooling off — not selectable right now


@dataclass(frozen=True)
class AIResponse:
    """
    The only thing an EcoIQ view ever sees back from a provider.

    `resolved_model` is the concrete model a router actually ran (OpenRouter's
    `openrouter/free` picks one per request and reports it back in the
    response body) — `requested_model` stays whatever EcoIQ asked for.
    """
    content: str
    provider: str
    requested_model: str
    resolved_model: str | None = None
    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    fallback_used: bool = False
    provider_attempts: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderModel:
    """
    One model as its *provider* describes it, after that provider's free-policy
    check has run — but before EcoIQ's own allowlist has had a say.

    `free_eligible=False` entries are kept (rather than dropped) so that
    `manage.py refresh_ai_models` and the staff health endpoint can explain
    *why* an allowlisted model did not make it into the runtime registry.
    """
    provider: str
    provider_model_id: str
    display_name: str
    description: str = ''
    capabilities: frozenset[str] = frozenset({CAPABILITY_CHAT})
    context_length: int | None = None
    free_eligible: bool = False
    free_policy: str = ''
    free_label: str = ''
    rejection_reason: str = ''
    public: bool = True
    development_only: bool = False


@dataclass(frozen=True)
class AIModelDefinition:
    """
    A model EcoIQ is willing to run, addressed by an opaque server-issued
    `key` (e.g. `openrouter:auto-free`). The browser only ever sees `key` —
    never `provider_model_id`, never a base URL, never a credential.
    """
    key: str
    provider: str
    provider_model_id: str
    display_name: str
    description: str
    capabilities: frozenset[str]
    context_length: int | None
    free_eligible: bool
    free_policy: str
    enabled: bool
    public: bool
    priority: int
    development_only: bool = False
    free_label: str = 'Free'
    availability: str = AVAILABILITY_AVAILABLE

    @property
    def provider_display_name(self) -> str:
        return PROVIDER_DISPLAY_NAMES.get(self.provider, self.provider)

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities


# ── Provider identifiers ──────────────────────────────────────────────────────
# The internal provider slug is also the first segment of every model key, so
# it is part of the public (but opaque) contract — do not rename casually.
PROVIDER_OPENROUTER = 'openrouter'
PROVIDER_BYTEZ = 'bytez'
PROVIDER_NVIDIA_NIM = 'nvidia_nim'

# Key prefixes are shorter than the internal slug for nvidia_nim, matching the
# `nvidia:llama-31-8b-preview` shape in the EcoIQ AI gateway specification.
PROVIDER_KEY_PREFIXES = {
    PROVIDER_OPENROUTER: 'openrouter',
    PROVIDER_BYTEZ: 'bytez',
    PROVIDER_NVIDIA_NIM: 'nvidia',
}

PROVIDER_DISPLAY_NAMES = {
    PROVIDER_OPENROUTER: 'OpenRouter',
    PROVIDER_BYTEZ: 'Bytez',
    PROVIDER_NVIDIA_NIM: 'NVIDIA NIM',
}


@dataclass(frozen=True)
class RegistrySnapshot:
    """
    The whole selectable-model world at one point in time.

    `stale=True` means at least one provider catalogue refresh failed and this
    snapshot was served from the extended-TTL cache copy instead — the
    registry keeps serving the last known-good model list rather than
    collapsing to "no models available" on a transient provider outage.
    """
    models: tuple[AIModelDefinition, ...]
    refreshed_at: str
    stale: bool = False
    provider_errors: dict[str, str] = field(default_factory=dict)
    rejected: tuple[ProviderModel, ...] = ()

    def by_key(self, key: str) -> AIModelDefinition | None:
        for model in self.models:
            if model.key == key:
                return model
        return None
