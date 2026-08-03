"""
ai_gateway/providers — the three concrete AI providers behind the EcoIQ
gateway. Nothing outside this package constructs a provider client directly;
callers go through `get_provider()` / `all_providers()`.
"""
from __future__ import annotations

from ai_gateway.types import PROVIDER_BYTEZ, PROVIDER_NVIDIA_NIM, PROVIDER_OPENROUTER

__all__ = ['get_provider', 'all_providers', 'PROVIDER_ORDER']

#: Stable provider ordering — also the default cross-provider fallback order.
PROVIDER_ORDER = (PROVIDER_OPENROUTER, PROVIDER_BYTEZ, PROVIDER_NVIDIA_NIM)


def _provider_classes() -> dict:
    # Imported lazily so that `ai_gateway.providers._openai_compat` (which the
    # concrete providers import from this same package) does not create a
    # circular import at module-import time.
    from ai_gateway.providers.bytez import BytezProvider
    from ai_gateway.providers.nvidia_nim import NvidiaNimProvider
    from ai_gateway.providers.openrouter import OpenRouterProvider

    return {
        PROVIDER_OPENROUTER: OpenRouterProvider,
        PROVIDER_BYTEZ: BytezProvider,
        PROVIDER_NVIDIA_NIM: NvidiaNimProvider,
    }


def get_provider(provider_name: str):
    classes = _provider_classes()
    if provider_name not in classes:
        raise KeyError(f'unknown AI provider: {provider_name!r}')
    return classes[provider_name]()


def all_providers() -> list:
    classes = _provider_classes()
    return [classes[name]() for name in PROVIDER_ORDER]
