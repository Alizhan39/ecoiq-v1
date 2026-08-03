"""
ai_gateway/routing.py — how EcoIQ decides which free model answers a request.

Normal users do not choose a model. They do not send one, and if they send one
anyway it is ignored. This module turns *what the request needs* into an
ordered list of approved free models to try.

A routing profile is built from things EcoIQ controls, never from free-form
user input:

  * the endpoint and active module   → task, privacy level, min context
  * the answer mode (auto/quick/deep) → output ceiling, capability preference
  * the requested language            → validated language code only
  * required modality                 → derived from the request payload
  * structured-output requirement     → from the module's routing profile
  * audience                          → public vs staff/development

Scoring then ranks the eligible models by task benchmark (where EcoIQ has
measured one), health, and configured priority. The free router
(`OPENROUTER_FREE_ROUTER_MODEL`) is deliberately placed *last*: it is the
catch-all when nothing more specific applies, not the first choice.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from django.conf import settings
from django.core.cache import cache

from ai_gateway.types import (
    AVAILABILITY_AVAILABLE, CAPABILITY_CHAT, AIModelDefinition,
)

logger = logging.getLogger('ecoiq.ai_gateway')

AUDIENCE_PUBLIC = 'public'
AUDIENCE_STAFF = 'staff'

MODE_AUTO = 'auto'
MODE_QUICK = 'quick'
MODE_DEEP = 'deep'

#: How long a single model's failure count is remembered when ranking. Short:
#: this biases *ordering*, it does not ban a model (that is what the separate
#: availability cooldown in registry.py does).
HEALTH_WINDOW_SECONDS = 900
MAX_HEALTH_PENALTY = 40.0


@dataclass(frozen=True)
class RoutingProfile:
    """What this request needs. Never contains user-authored free text."""
    audience: str = AUDIENCE_PUBLIC
    mode: str = MODE_AUTO
    module: str = ''
    task: str = 'chat'
    language: str = 'en'
    required_capabilities: frozenset[str] = field(default_factory=lambda: frozenset({CAPABILITY_CHAT}))
    min_context_length: int = 0
    structured_output: bool = False
    privacy_level: str = 'standard'
    max_output_tokens: int = 1600

    @property
    def is_public(self) -> bool:
        return self.audience == AUDIENCE_PUBLIC


def normalise_mode(mode) -> str:
    modes = getattr(settings, 'AI_ROUTING_MODES', {}) or {}
    default = getattr(settings, 'AI_DEFAULT_ROUTING_MODE', MODE_AUTO)
    if not isinstance(mode, str):
        return default
    candidate = mode.strip().lower()
    return candidate if candidate in modes else default


def build_profile(
    *,
    user=None,
    mode=None,
    module: str = '',
    language: str = 'en',
    needs_vision: bool = False,
    estimated_input_chars: int = 0,
) -> RoutingProfile:
    """
    Assemble the profile. `module` has already been shape-validated by
    `AIService`; everything else here comes from Django settings.
    """
    from ai_gateway.registry import registry

    mode = normalise_mode(mode)
    mode_config = (getattr(settings, 'AI_ROUTING_MODES', {}) or {}).get(mode, {})

    module_profile = dict(getattr(settings, 'AI_ROUTING_DEFAULT_PROFILE', {}) or {})
    module_profile.update((getattr(settings, 'AI_MODULE_ROUTING', {}) or {}).get(module, {}))

    capabilities = {CAPABILITY_CHAT}
    if needs_vision:
        capabilities.add('vision')

    # Context requirement: the larger of what the module declares, what the
    # mode asks for, and a rough token estimate of the conversation itself
    # (~4 chars/token, doubled to leave room for the answer).
    estimated_tokens = (estimated_input_chars // 4) * 2
    min_context = max(
        int(module_profile.get('min_context_length', 0)),
        int(mode_config.get('min_context_length', 0)),
        estimated_tokens,
    )

    ceiling = int(getattr(settings, 'AI_MAX_OUTPUT_TOKENS', 1600))
    mode_ceiling = mode_config.get('max_output_tokens')
    max_output = min(ceiling, int(mode_ceiling)) if mode_ceiling else ceiling

    audience = (AUDIENCE_STAFF if registry.user_may_use_development_models(user)
                else AUDIENCE_PUBLIC)

    return RoutingProfile(
        audience=audience,
        mode=mode,
        module=module,
        task=str(module_profile.get('task', 'chat')),
        language=language,
        required_capabilities=frozenset(capabilities),
        min_context_length=min_context,
        structured_output=bool(module_profile.get('structured_output', False)),
        privacy_level=str(module_profile.get('privacy_level', 'standard')),
        max_output_tokens=max_output,
    )


# ── Model health ──────────────────────────────────────────────────────────────

def _health_key(model_key: str) -> str:
    return f'ecoiq:ai_gateway:health:{model_key}'


def record_model_failure(model_key: str) -> None:
    """Bump a short-lived failure counter used to demote a flaky model."""
    key = _health_key(model_key)
    try:
        cache.set(key, int(cache.get(key) or 0) + 1, timeout=HEALTH_WINDOW_SECONDS)
    except Exception:  # noqa: BLE001 — ranking must never break a request
        logger.debug('ai_gateway.health_counter_failed model_key=%s', model_key)


def recent_failures(model_key: str) -> int:
    try:
        return int(cache.get(_health_key(model_key)) or 0)
    except Exception:  # noqa: BLE001
        return 0


# ── Eligibility + scoring ─────────────────────────────────────────────────────

def is_eligible(model: AIModelDefinition, profile: RoutingProfile) -> tuple[bool, str]:
    """Hard filters. Returns (eligible, reason_if_not) for explainable routing."""
    if not model.free_eligible:
        return False, 'not free-eligible'
    if model.availability != AVAILABILITY_AVAILABLE:
        return False, 'cooling off after a recent failure'
    if profile.is_public and model.development_only:
        # The decisive gate: NVIDIA preview can never enter a public chain.
        return False, 'development-only model excluded from public routing'
    missing = profile.required_capabilities - model.capabilities
    if missing:
        return False, f'missing capability: {",".join(sorted(missing))}'
    if profile.structured_output and 'tools' not in model.capabilities:
        return False, 'structured output required but tool support unknown'
    if (profile.min_context_length and model.context_length
            and model.context_length < profile.min_context_length):
        return False, (f'context {model.context_length} < required '
                       f'{profile.min_context_length}')
    return True, ''


def score(model: AIModelDefinition, profile: RoutingProfile) -> float:
    """
    Higher is better. Deterministic — no randomness, so the same request shape
    always produces the same chain, which keeps routing debuggable.
    """
    benchmarks = (getattr(settings, 'AI_MODEL_BENCHMARKS', {}) or {}).get(
        model.provider_model_id, {})
    # Benchmark for this exact task, else a general score, else nothing. EcoIQ
    # ships no benchmarks, so in practice this is 0 and priority decides.
    value = float(benchmarks.get(profile.task, benchmarks.get('general', 0.0)))

    # Configured priority is the standing preference order (lower = better).
    value += max(0.0, 100.0 - float(model.priority)) / 10.0

    # Mode preference. 'capable' rewards headroom, 'fast' rewards small
    # context (a proxy for a smaller, quicker model) — both only break ties.
    prefer = (getattr(settings, 'AI_ROUTING_MODES', {}) or {}).get(
        profile.mode, {}).get('prefer', 'balanced')
    context = model.context_length or 0
    if prefer == 'capable':
        value += min(context, 1_000_000) / 100_000.0
    elif prefer == 'fast':
        value += max(0.0, 10.0 - min(context, 1_000_000) / 100_000.0)

    # Recent failures demote but never disqualify.
    value -= min(MAX_HEALTH_PENALTY, recent_failures(model.key) * 8.0)
    return value


def is_catch_all_router(model: AIModelDefinition) -> bool:
    """The provider-side free router — always the last resort, never the first."""
    return model.provider_model_id == getattr(
        settings, 'OPENROUTER_FREE_ROUTER_MODEL', 'openrouter/free')


def build_chain(candidates: list[AIModelDefinition], profile: RoutingProfile
                ) -> list[AIModelDefinition]:
    """
    Order the eligible models:

        1. best approved task-specific free model
        2. next compatible approved free model
        3. the free router (openrouter/free) as the catch-all
        4. (caller returns FREE_MODELS_UNAVAILABLE when this list empties)

    Then truncate to AI_MAX_PROVIDER_ATTEMPTS. Deduplicated by key, so a chain
    can never revisit a model — a fallback loop is not representable.
    """
    eligible = [m for m in candidates if is_eligible(m, profile)[0]]

    specific = [m for m in eligible if not is_catch_all_router(m)]
    catch_all = [m for m in eligible if is_catch_all_router(m)]

    if getattr(settings, 'AI_ROUTING_MODE', 'automatic') == 'automatic':
        specific.sort(key=lambda m: (-score(m, profile), m.priority, m.key))
    else:
        specific.sort(key=lambda m: (m.priority, m.key))

    ordered, seen = [], set()
    for model in specific + catch_all:
        if model.key not in seen:
            seen.add(model.key)
            ordered.append(model)

    if not settings.AI_ALLOW_AUTOMATIC_FALLBACK:
        ordered = ordered[:1]

    max_attempts = max(1, int(settings.AI_MAX_PROVIDER_ATTEMPTS))
    return ordered[:max_attempts]


def explain(candidates: list[AIModelDefinition], profile: RoutingProfile) -> list[dict]:
    """Staff-facing routing explanation. Never exposed to public callers."""
    rows = []
    for model in candidates:
        eligible, reason = is_eligible(model, profile)
        rows.append({
            'key': model.key,
            'name': model.display_name,
            'eligible': eligible,
            'reason': reason,
            'score': round(score(model, profile), 2) if eligible else None,
            'catch_all': is_catch_all_router(model),
        })
    return rows
