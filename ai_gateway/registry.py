"""
ai_gateway/registry.py — `AIModelRegistry`, the sole source of truth for which
models EcoIQ will show and run.

The runtime registry is an intersection, and every term is required:

    provider catalogue
      ∩ provider free policy
      ∩ EcoIQ allowlist
      ∩ supported capabilities
      ∩ enabled environment configuration

A `model_key` submitted by a browser is only ever *looked up* here. It is
never parsed for routing information, never turned into a provider model id by
string manipulation, and never trusted to carry a provider, base URL or model
name. If the key is not in this registry, the request is rejected.

Caching: provider catalogues are fetched at most once per
`AI_MODEL_CATALOG_CACHE_SECONDS`, never per page load and never per chat
request. A second copy is written under a longer TTL so that a failed refresh
serves the last known-good registry (marked `stale=True`) instead of
collapsing the model list to empty.
"""
from __future__ import annotations

import logging
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from ai_gateway.exceptions import ProviderCallError
from ai_gateway.providers import PROVIDER_ORDER, all_providers, get_provider
from ai_gateway.types import (
    AVAILABILITY_AVAILABLE, AVAILABILITY_UNAVAILABLE, CAPABILITY_CHAT,
    PROVIDER_KEY_PREFIXES, AIModelDefinition, ProviderModel, RegistrySnapshot,
)

logger = logging.getLogger('ecoiq.ai_gateway')

CACHE_VERSION = 'v1'
FRESH_CACHE_KEY = f'ecoiq:ai_gateway:registry:{CACHE_VERSION}'
STALE_CACHE_KEY = f'ecoiq:ai_gateway:registry:stale:{CACHE_VERSION}'

#: How much longer the stale copy survives than the fresh one. Bounded on
#: purpose: "serve the last good catalogue through a provider blip" is
#: legitimate; "serve a month-old catalogue forever" is not.
STALE_TTL_MULTIPLIER = 6

#: How long an all-providers-failed result is cached when there is no stale
#: copy to serve. Short on purpose — a transient outage must not blank the
#: model selector for a full catalogue TTL.
FAILED_BUILD_TTL_SECONDS = 60

#: Cooldown applied to one model after a live request against it fails with a
#: transient error, so the next user is not routed straight back into it.
UNAVAILABLE_COOLDOWN_SECONDS = 300


def _slugify_model_id(provider_model_id: str) -> str:
    """`openai/gpt-oss-20b:free` → `openai-gpt-oss-20b-free`."""
    slug = provider_model_id.strip().lower()
    for char in ('/', ':', '.', ' ', '_'):
        slug = slug.replace(char, '-')
    while '--' in slug:
        slug = slug.replace('--', '-')
    return slug.strip('-')


def build_model_key(provider: str, provider_model_id: str) -> str:
    """
    Build the opaque, server-issued key the browser sees.

    A presentation override may supply a friendlier slug (that is how
    `openrouter/free` becomes `openrouter:auto-free`), but the key is always
    minted here — never derived client-side, and never reversible into
    credentials or routing configuration.
    """
    prefix = PROVIDER_KEY_PREFIXES.get(provider, provider)
    overrides = (getattr(settings, 'AI_MODEL_PRESENTATION', {}) or {}).get(provider_model_id, {})
    slug = overrides.get('key_slug') or _slugify_model_id(provider_model_id)
    return f'{prefix}:{slug}'


def _presentation(provider_model_id: str) -> dict:
    return (getattr(settings, 'AI_MODEL_PRESENTATION', {}) or {}).get(provider_model_id, {})


def _availability_cache_key(provider: str, provider_model_id: str) -> str:
    return f'ecoiq:ai_gateway:down:{provider}:{provider_model_id}'


def mark_model_unavailable(provider: str, provider_model_id: str, reason: str) -> None:
    """Cool one model off after a transient live failure."""
    cache.set(_availability_cache_key(provider, provider_model_id), reason,
              timeout=UNAVAILABLE_COOLDOWN_SECONDS)


def model_availability(provider: str, provider_model_id: str) -> str:
    if cache.get(_availability_cache_key(provider, provider_model_id)):
        return AVAILABILITY_UNAVAILABLE
    return AVAILABILITY_AVAILABLE


#: Provider catalogue descriptions run to several paragraphs. The selector
#: shows a one-line hint, so trim at the source rather than in the template.
MAX_DESCRIPTION_CHARS = 160


def _short_description(text: str) -> str:
    text = ' '.join((text or '').split())
    if len(text) <= MAX_DESCRIPTION_CHARS:
        return text
    return text[:MAX_DESCRIPTION_CHARS].rstrip() + '…'


def _to_definition(model: ProviderModel) -> AIModelDefinition:
    presentation = _presentation(model.provider_model_id)
    return AIModelDefinition(
        key=build_model_key(model.provider, model.provider_model_id),
        provider=model.provider,
        provider_model_id=model.provider_model_id,
        display_name=presentation.get('display_name') or model.display_name,
        description=_short_description(presentation.get('description') or model.description),
        capabilities=model.capabilities or frozenset({CAPABILITY_CHAT}),
        context_length=model.context_length,
        free_eligible=model.free_eligible,
        free_policy=model.free_policy,
        enabled=True,
        public=model.public,
        priority=int(presentation.get('priority', 500)),
        development_only=model.development_only,
        free_label=model.free_label or 'Free',
        availability=model_availability(model.provider, model.provider_model_id),
    )


def _serialise(snapshot: RegistrySnapshot) -> dict:
    """Cache as plain JSON-able data — dataclasses with frozensets are not."""
    def dump(model: AIModelDefinition) -> dict:
        data = model.__dict__.copy()
        data['capabilities'] = sorted(model.capabilities)
        return data

    def dump_rejected(model: ProviderModel) -> dict:
        data = model.__dict__.copy()
        data['capabilities'] = sorted(model.capabilities)
        return data

    return {
        'models': [dump(m) for m in snapshot.models],
        'refreshed_at': snapshot.refreshed_at,
        'provider_errors': snapshot.provider_errors,
        'rejected': [dump_rejected(m) for m in snapshot.rejected],
    }


def _deserialise(payload: dict, *, stale: bool) -> RegistrySnapshot:
    models = []
    for data in payload.get('models', []):
        data = dict(data)
        data['capabilities'] = frozenset(data.get('capabilities') or [CAPABILITY_CHAT])
        definition = AIModelDefinition(**data)
        # Availability is deliberately re-evaluated on read, not cached: a
        # model that failed 30 seconds ago must show as unavailable even
        # though the catalogue snapshot around it is still fresh.
        models.append(_replace_availability(definition))
    rejected = []
    for data in payload.get('rejected', []):
        data = dict(data)
        data['capabilities'] = frozenset(data.get('capabilities') or [])
        rejected.append(ProviderModel(**data))
    return RegistrySnapshot(
        models=tuple(models),
        refreshed_at=payload.get('refreshed_at', ''),
        stale=stale,
        provider_errors=payload.get('provider_errors', {}),
        rejected=tuple(rejected),
    )


def _replace_availability(definition: AIModelDefinition) -> AIModelDefinition:
    availability = model_availability(definition.provider, definition.provider_model_id)
    if availability == definition.availability:
        return definition
    data = definition.__dict__.copy()
    data['availability'] = availability
    return AIModelDefinition(**data)


class AIModelRegistry:
    """Build, cache and query the approved model set."""

    # ── Building ──────────────────────────────────────────────────────────────

    def build(self) -> RegistrySnapshot:
        """
        Fetch every configured provider's catalogue and intersect it with the
        EcoIQ allowlist and free policy. One provider failing never fails the
        whole build — its error is recorded and the other providers still
        contribute.
        """
        approved: list[AIModelDefinition] = []
        rejected: list[ProviderModel] = []
        errors: dict[str, str] = {}

        for provider in all_providers():
            if not provider.is_configured:
                reason = provider.unavailable_reason()
                if reason and provider.enabled:
                    errors[provider.provider_name] = reason
                continue
            try:
                provider_approved, provider_rejected = provider.evaluate_catalog()
            except ProviderCallError as exc:
                # Category only — an upstream body or URL never lands in a
                # cached snapshot that a staff endpoint later renders.
                errors[provider.provider_name] = exc.category
                logger.warning('ai_gateway.catalog_refresh_failed provider=%s category=%s',
                               provider.provider_name, exc.category)
                continue
            except Exception:  # noqa: BLE001 — a provider bug must not break the registry
                errors[provider.provider_name] = 'internal_error'
                logger.exception('ai_gateway.catalog_refresh_crashed provider=%s',
                                 provider.provider_name)
                continue

            approved.extend(_to_definition(m) for m in provider_approved)
            rejected.extend(provider_rejected)

        # Global free-only gate. Belt and braces on top of every provider's own
        # check: nothing that failed its provider free policy can be here.
        if settings.AI_FREE_ONLY:
            approved = [m for m in approved if m.free_eligible]

        approved.sort(key=lambda m: (m.priority, m.display_name.lower()))

        return RegistrySnapshot(
            models=tuple(approved),
            refreshed_at=timezone.now().isoformat(),
            stale=False,
            provider_errors=errors,
            rejected=tuple(rejected),
        )

    # ── Caching ───────────────────────────────────────────────────────────────

    def get_snapshot(self, *, force_refresh: bool = False) -> RegistrySnapshot:
        if not force_refresh:
            cached = cache.get(FRESH_CACHE_KEY)
            if cached:
                return _deserialise(cached, stale=False)

        try:
            snapshot = self.build()
        except Exception:  # noqa: BLE001
            logger.exception('ai_gateway.registry_build_crashed')
            snapshot = None

        # A build that produced nothing at all (total provider outage) must not
        # overwrite a good cached registry — fall back to the stale copy.
        failed = snapshot is None or (not snapshot.models and snapshot.provider_errors)
        if failed:
            stale = cache.get(STALE_CACHE_KEY)
            if stale:
                logger.warning('ai_gateway.registry_served_stale errors=%s',
                               sorted((snapshot.provider_errors if snapshot else {}).keys()))
                return _deserialise(stale, stale=True)
            if snapshot is None:
                return RegistrySnapshot(models=(), refreshed_at=timezone.now().isoformat(),
                                        stale=True, provider_errors={'registry': 'build_failed'})

        payload = _serialise(snapshot)
        ttl = int(settings.AI_MODEL_CATALOG_CACHE_SECONDS)
        if failed:
            # Every provider failed and there is no stale copy to fall back on.
            # Cache the empty result only briefly, so a transient outage cannot
            # blank the model selector for a full catalogue TTL — the next
            # request retries within a minute instead of within an hour.
            cache.set(FRESH_CACHE_KEY, payload, timeout=min(ttl, FAILED_BUILD_TTL_SECONDS))
            return snapshot

        cache.set(FRESH_CACHE_KEY, payload, timeout=ttl)
        cache.set(STALE_CACHE_KEY, payload, timeout=ttl * STALE_TTL_MULTIPLIER)
        return snapshot

    def invalidate(self) -> None:
        cache.delete(FRESH_CACHE_KEY)

    def peek_cached(self) -> RegistrySnapshot | None:
        """
        Read the cached registry WITHOUT triggering a build. Used by
        `check_ai_configuration`, which must not touch the network by default —
        `get_snapshot()` would fetch provider catalogues on a cold cache.
        Returns None when nothing is cached.
        """
        cached = cache.get(FRESH_CACHE_KEY) or cache.get(STALE_CACHE_KEY)
        return _deserialise(cached, stale=cached is not cache.get(FRESH_CACHE_KEY)) if cached else None

    # ── Querying ──────────────────────────────────────────────────────────────

    def visible_models(self, user=None, *, snapshot: RegistrySnapshot | None = None
                       ) -> list[AIModelDefinition]:
        """
        The models this particular caller may see. Development-only models
        (NVIDIA preview) are hidden from ordinary production users and shown
        to staff — the same rule the resolver enforces, so the selector can
        never offer something the chat endpoint would refuse.
        """
        snapshot = snapshot or self.get_snapshot()
        allow_development = self.user_may_use_development_models(user)
        return [
            model for model in snapshot.models
            if model.enabled
            and (model.public or (model.development_only and allow_development))
            and (model.free_eligible or not settings.AI_FREE_ONLY)
        ]

    @staticmethod
    def user_may_use_development_models(user) -> bool:
        if user is None:
            return False
        return bool(getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False))

    def resolve(self, model_key: str, user=None, *,
                required_capability: str = CAPABILITY_CHAT) -> AIModelDefinition:
        """
        Turn an opaque `model_key` into an approved `AIModelDefinition`, or
        raise. Every one of the six conditions in the spec is checked here:
        exists, enabled, public (for this caller), free-eligible, supports the
        requested modality, and passes the provider availability check.
        """
        from ai_gateway.exceptions import InvalidModelSelection, ModelNotPermitted

        if not isinstance(model_key, str) or not model_key.strip():
            raise InvalidModelSelection()

        snapshot = self.get_snapshot()
        definition = snapshot.by_key(model_key.strip())
        if definition is None:
            raise InvalidModelSelection()
        if not definition.enabled:
            raise InvalidModelSelection()
        if settings.AI_FREE_ONLY and not definition.free_eligible:
            # Unreachable via the normal build (the global gate above strips
            # these) — kept as the last line of defence against a paid model
            # ever being reachable by key.
            raise ModelNotPermitted()
        if not definition.public:
            if not (definition.development_only and self.user_may_use_development_models(user)):
                raise ModelNotPermitted()
        if not definition.supports(required_capability):
            raise InvalidModelSelection(
                'That model does not support this kind of request.',
                code='UNSUPPORTED_CAPABILITY',
            )
        provider = get_provider(definition.provider)
        if not provider.is_configured:
            raise InvalidModelSelection()
        return definition

    def default_model(self, user=None) -> AIModelDefinition | None:
        """
        `AI_DEFAULT_MODEL_KEY` when it is currently selectable, otherwise the
        highest-priority model this caller can see. Returns None when the free
        pool is empty — callers turn that into FREE_MODELS_UNAVAILABLE.
        """
        visible = self.visible_models(user)
        if not visible:
            return None
        configured = settings.AI_DEFAULT_MODEL_KEY
        for model in visible:
            if model.key == configured and model.availability == AVAILABILITY_AVAILABLE:
                return model
        available = [m for m in visible if m.availability == AVAILABILITY_AVAILABLE]
        return (available or visible)[0]

    def routable_models(self, user=None) -> list[AIModelDefinition]:
        """
        Everything this caller could legitimately be routed to. For a public
        caller this already excludes development-only models, so NVIDIA preview
        cannot reach public routing even if a later filter were removed.
        """
        return [m for m in self.visible_models(user) if m.free_eligible]

    def select_route(self, profile, user=None) -> list[AIModelDefinition]:
        """
        Automatic routing: the ordered chain of approved free models to try for
        this request. No model_key involved — EcoIQ chooses.

        Returns [] when nothing is eligible; the caller turns that into the
        stable FREE_MODELS_UNAVAILABLE response, never into a paid model.
        """
        from ai_gateway import routing

        chain = routing.build_chain(self.routable_models(user), profile)
        if not chain:
            logger.warning(
                'ai_gateway.no_eligible_route module=%s task=%s mode=%s audience=%s',
                profile.module, profile.task, profile.mode, profile.audience,
            )
        return chain

    def fallback_chain(self, selected: AIModelDefinition, user=None) -> list[AIModelDefinition]:
        """
        The ordered attempt list: the selected model first, then the same
        provider's approved free models, then other providers' approved free
        models. Every entry is drawn from the same visible, free-eligible pool,
        so a fallback can never leave the free pool or escalate to a paid model.

        Development-only models are excluded from the fallback tail for users
        who cannot select them anyway, and are never *silently* substituted for
        a production user's choice.
        """
        chain = [selected]
        if not settings.AI_ALLOW_AUTOMATIC_FALLBACK:
            return chain

        candidates = [
            model for model in self.visible_models(user)
            if model.key != selected.key
            and model.availability == AVAILABILITY_AVAILABLE
            and model.free_eligible
        ]
        same_provider = [m for m in candidates if m.provider == selected.provider]
        other_provider = [m for m in candidates if m.provider != selected.provider]
        other_provider.sort(key=lambda m: (PROVIDER_ORDER.index(m.provider)
                                           if m.provider in PROVIDER_ORDER else 99,
                                           m.priority))

        max_attempts = max(1, int(settings.AI_MAX_PROVIDER_ATTEMPTS))
        chain.extend(same_provider + other_provider)
        # Hard cap — the router also counts attempts, but truncating the chain
        # here makes an over-long chain structurally impossible.
        return chain[:max_attempts]


#: Module-level singleton. Stateless apart from the shared Django cache, so it
#: is safe to share across threads in the gthread worker.
registry = AIModelRegistry()
