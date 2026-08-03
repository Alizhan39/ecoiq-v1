# EcoIQ AI Gateway

One provider-neutral, **free-only** AI system in front of OpenRouter, Bytez and
NVIDIA NIM, with a per-request model selector.

> This is **not** a replacement for `agent_runtime_model_router` (governed
> *agent* execution against Anthropic/OpenAI/Gemini/Azure) or `core/ai.py` (the
> Anthropic ESG scoring path). Both are untouched and keep their own budgets.
> This is the user-facing chat gateway, and it never routes to a paid model.

## Architecture

```
Django views (ai_gateway/views.py)
        ↓
AIService            ai_gateway/service.py     validation, prompt, public payload
        ↓
AIModelRegistry      ai_gateway/registry.py    model_key → approved model
        ↓
AIProviderRouter     ai_gateway/router.py      attempt + bounded free-pool fallback
        ↓
├── OpenRouterProvider   ai_gateway/providers/openrouter.py
├── BytezProvider        ai_gateway/providers/bytez.py
└── NvidiaNimProvider    ai_gateway/providers/nvidia_nim.py
```

A view never instantiates a provider client. Every provider speaks the same
OpenAI-compatible `/chat/completions` wire format, so all three share one httpx
client at `ai_gateway/providers/_openai_compat.py` — the only place in the app
that opens a socket.

**Why httpx and not the `openai` SDK:** the SDK is not a dependency of this
project (absent from `requirements.txt` and from `.venv`), while httpx already
is. No new runtime dependency was added for this feature.

## Endpoints

| Endpoint | Auth | Purpose |
| --- | --- | --- |
| `GET /api/ai/models/` | authenticated | Selectable model catalogue |
| `POST /api/ai/chat/` | authenticated | One generation, one model |
| `GET /api/ai/health/` | **staff only** | Configuration + catalogue freshness |
| `GET /ai-assistant/` | login required | The assistant page + model selector |

Authentication reuses EcoIQ's existing chain. The views deliberately do **not**
pin `authentication_classes`; they inherit
`REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`, which is where the project
already declares its schemes (website session, B2B `api.models.APIKey`, and the
mobile device-token scheme where that app is installed). Pinning them — as
`api/views.py` and `mizan/views.py` do — would duplicate that decision and
hard-couple this app to whichever authentication apps happen to be installed.

`ai_gateway/permissions.py:IsEcoIQAuthenticated` is what actually decides who
gets in, and it accepts any of those schemes — including an API key with no
owner user, which plain `IsAuthenticated` would wrongly reject. Permission and
throttle classes *are* pinned per view, because those genuinely differ from the
project defaults (staff-only health, AI-specific rate limits).

### Request

```json
{
  "message": "Analyse this company",
  "model_key": "openrouter:auto-free",
  "language": "en",
  "history": [],
  "context": { "company_id": 123, "module": "company-analysis" }
}
```

`model_key` is **opaque and server-issued**. A raw provider slug
(`openrouter/free`), a `provider`, a `base_url` or a `model` field submitted by
a client is never read. The key is looked up in the registry; it is never
parsed for routing information.

### Errors

| Status | Code | Meaning |
| --- | --- | --- |
| 400 | `INVALID_REQUEST` / `INVALID_MODEL_SELECTION` | Bad input or unknown model key |
| 401 | `UNAUTHORIZED` | Not an authenticated EcoIQ caller |
| 403 | `MODEL_NOT_PERMITTED` | Model exists but not for this caller (e.g. NVIDIA preview) |
| 429 | `RATE_LIMITED` | EcoIQ or provider rate limit |
| 502 | `UPSTREAM_MALFORMED` | Unusable upstream response |
| 503 | `FREE_MODELS_UNAVAILABLE` | Every approved free model was tried and failed |
| 504 | `PROVIDER_TIMEOUT` | Upstream timeout |

A raw provider exception, body, URL or credential never reaches a client.

## Free-only policy

`AI_FREE_ONLY=true` (the default) means: paid models are neither displayed nor
callable, no request is silently upgraded to a paid model, no account credits
are spent, no auto-reload is triggered, and a failing free model can only ever
fall back to **another free model**. When the free pool is exhausted the
gateway returns the stable `FREE_MODELS_UNAVAILABLE` response rather than
reaching for a paid one.

Setting `AI_FREE_ONLY=true` together with `AI_ALLOW_PAID_MODELS=true` raises
`ImproperlyConfigured` at startup — that combination is a deployment mistake,
not a runtime decision.

A model is selectable only at the **intersection** of:

```
provider catalogue ∩ provider free policy ∩ EcoIQ allowlist
                   ∩ supported capabilities ∩ enabled environment configuration
```

Open-source weights are **not** evidence of free hosted inference. The two are
unrelated and are never conflated here.

### OpenRouter

Free eligibility is decided by price, not by name. The `:free` suffix carries
no weight; a zero-priced model without it is perfectly welcome. Prices are
parsed with `decimal.Decimal`, never `float`.

A model qualifies only when **all** hold: it is the approved free router or an
approved free variant; `prompt` and `completion` are present and exactly zero;
`request` and `internal_reasoning`, if present, are exactly zero; every pricing
dimension is recognised (a brand-new billing axis is a rejection, not a shrug);
input includes text and output is text **only**; and it has no expiration date.

The modality gate runs *before* the price gate on purpose: the live catalogue
contains models that are zero on `prompt`/`completion` while billing through an
`audio` or `image` dimension.

Routing policy (ZDR, `allow_fallbacks: false`) is built server-side from
settings. The frontend cannot contribute to it.

### Bytez

**Ships with an empty allowlist.** The catalogue endpoint returns 401 without a
key, so its free-tier field names could not be verified; every field name in
`providers/bytez.py` is treated as a hypothesis and the check requires explicit
positive evidence. Anything missing or ambiguous is a rejection. Bytez
therefore contributes zero models until someone with a key runs:

```bash
python manage.py refresh_ai_models --explain
```

reads the rejection reasons, confirms the real field names, and edits
`AI_MODEL_ALLOWLIST`.

Free-plan access can consume included credits, so: auto-reload is never
enabled, credits are never purchased, a larger paid model is never substituted,
and exhausted credits are treated as *unavailable* (a free-pool fallback
trigger). Bytez models are labelled **"Free-plan model"**, never "Unlimited
free".

### NVIDIA NIM

Developer Program hosted endpoints are prototype and development access, not
permanently free production inference. Models are labelled **"NVIDIA preview"**,
are visible only to staff/development users, and require **two** independent
latches (`NVIDIA_NIM_PUBLIC_PRODUCTION_ENABLED=true` **and**
`NVIDIA_NIM_PROTOTYPE_ONLY=false`) before ordinary production users can see
them. Do not flip either until licensing for public production traffic has been
separately approved.

The allowlist is manually reviewed. Every id is validated against the live
NVIDIA API catalogue on each refresh, and must also have a reviewed entry in
`NVIDIA_MODEL_CONFIG` — NVIDIA models do not all accept the same parameters, so
capabilities and parameter defaults are configured per model rather than
assumed uniform.

## Fallback

```
Selected free model
        ↓ unavailable
Same provider's approved free fallback
        ↓ unavailable
Another provider's approved free fallback
        ↓ unavailable
FREE_MODELS_UNAVAILABLE
```

Three invariants, enforced structurally rather than by convention:

* **Never leaves the free pool** — the attempt chain is built by the registry
  from already-approved, already-free-eligible models. "Fall back to a paid
  model" is not expressible in this code.
* **Never loops** — each key is attempted at most once, and the chain is capped
  by `AI_MAX_PROVIDER_ATTEMPTS`.
* **Never falls back on a terminal error** — invalid request, unsupported
  modality, unauthorised, or broken configuration stops immediately.

Fallback *does* happen on: timeout, connection failure, 429, 5xx, model
temporarily unavailable, empty/malformed response, free-plan credits exhausted.

A provider with **no API key is not configured**, and its models never enter
the registry at all — so "missing credentials" can never appear as a
mid-request fallback reason.

## Caching

Provider catalogues are fetched at most once per
`AI_MODEL_CATALOG_CACHE_SECONDS` — never per page load, never per chat request.
A second copy is written under a 6× TTL so a failed refresh serves the last
known-good registry (marked `stale: true`) instead of collapsing the model list
to empty. A model that fails a live request is cooled off for 5 minutes and
shows as unavailable in the selector.

Note that EcoIQ has no `CACHES` setting, so this uses Django's default
per-process `LocMemCache`. With Render's single gunicorn worker that is
effectively one shared cache; if the service is ever scaled to multiple
workers, each will keep its own catalogue copy (correct, just less efficient).
Adding a Redis `CACHES` backend would consolidate it — deliberately not done
here, since Redis is not currently a paid resource on this deployment.

## System prompt

There is exactly one, in `ai_gateway/prompts.py`, assembled server-side and
always pinned at message index 0. Changing the selected model changes nothing
about it. `system`-role messages from clients are **rejected**, not silently
dropped — so the only path to a system message is that file.

## Logging

Logger `ecoiq.ai_gateway`. Safe metrics only: internal model key, provider,
resolved model, latency, token counts, fallback flag, normalised error
category, free-policy decision. Never: prompts, responses, API keys, company
context, personal information or hidden reasoning.

## Operations

```bash
# Refresh the registry from live provider catalogues
python manage.py refresh_ai_models

# ...and explain why each allowlisted model was rejected
python manage.py refresh_ai_models --explain

# ...without writing the cached registry
python manage.py refresh_ai_models --dry-run
```

The command makes **no inference request**, purchases nothing, and never
auto-approves a model — approving one means editing
`settings.AI_MODEL_ALLOWLIST`. It is safe to schedule if a scheduler already
exists; this change does not create one.

## Tests

```bash
python manage.py test ai_gateway
```

Every provider call is mocked at two seams (`_openai_compat.get_json` and
`.chat_completion`). `NoLiveCallTests` proves the no-network claim rather than
asserting it, by patching `httpx.Client` to raise and confirming a full mocked
request still succeeds.
