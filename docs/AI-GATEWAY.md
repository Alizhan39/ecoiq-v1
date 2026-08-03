# EcoIQ AI Gateway

One provider-neutral, **free-only** AI system in front of OpenRouter, Bytez and
NVIDIA NIM. **EcoIQ selects the model automatically** — normal users never see,
choose or send a model.

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
routing              ai_gateway/routing.py     request → routing profile → ranked chain
        ↓
AIModelRegistry      ai_gateway/registry.py    approved free model set
        ↓
AIProviderRouter     ai_gateway/router.py      attempt the chain, bounded
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
| `GET /api/ai/models/` | authenticated | Approved model catalogue — **staff only in practice**: a normal caller gets `selection_available: false` and an empty list |
| `POST /api/ai/chat/` | authenticated | One generation, model chosen automatically |
| `GET /api/ai/health/` | **staff only** | Configuration + catalogue freshness |
| `GET /ai-assistant/` | login required | The assistant page (prompt, answer mode, language — no model selector) |

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
  "language": "en",
  "mode": "auto",
  "history": [],
  "context": { "company_id": 123, "module": "company-analysis" }
}
```

**No field names a model.** `provider`, `base_url`, `model`, `free_only`,
`provider_preferences`, `route` and `api_key` are **rejected with 400** — none
is ever legitimate from a client. `model_key` is accepted only from staff (for
benchmarking) and **ignored** for everyone else, so a stale client that still
remembers a selection keeps working instead of erroring.

`mode` is one of `auto` / `quick` / `deep`. It adjusts routing *requirements*
(output ceiling, minimum context, capability preference); it never names a
model.

The public response carries the answer and nothing about how it was produced —
no model name, no provider, no fallback notice. Staff additionally get a
`routing` block for benchmark attribution.

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

### Bytez — disabled

`BYTEZ_ENABLED=false`. The provider, its free-policy check, the catalogue
survey command and all its tests **remain in the codebase** and are still
exercised by the suite; the switch only keeps it out of the runtime registry.
Set `BYTEZ_ENABLED=true` to bring it back once its catalogue is verified.

**Ships with an empty allowlist.** The catalogue endpoint returns 401 without a
key, so its free-tier field names could not be verified; every field name in
`providers/bytez.py` is treated as a hypothesis and the check requires explicit
positive evidence. Anything missing or ambiguous is a rejection. Bytez
therefore contributes zero models until someone with a key runs the catalogue
survey:

```bash
python manage.py refresh_ai_models --provider bytez --dry-run --explain
```

That command makes **catalogue requests only** — never an inference request,
never a credit purchase, never an allowlist write. It prints the fields the
catalogue actually returns, which of them the free-policy check recognises, and
a per-model accept/reject verdict with the reason. Eligible models are reported
as *candidates, not approved*.

Approval is a human step: add the confirmed ids to the `BYTEZ_APPROVED_MODELS`
environment variable (space- or comma-separated), then re-run
`check_ai_configuration`. Nothing is ever auto-approved, and the list is
deliberately not a long literal in `render.yaml`.

**Until that happens Bytez serves nothing**, and `check_ai_configuration`
reports it as a WARNING (a missing capability), not an error.

Free-plan access can consume included credits, so: auto-reload is never
enabled, credits are never purchased, a larger paid model is never substituted,
and exhausted credits are treated as *unavailable* (a free-pool fallback
trigger). Bytez models are labelled **"Free-plan model"**, never "Unlimited
free".

### NVIDIA NIM — staff / development only

Developer Program hosted endpoints are prototype and development access, not
permanently free production inference. Two ids are allowlisted for **staff and
development users only** — `meta/llama-3.1-8b-instruct` and
`nvidia/llama-3.1-nemotron-70b-instruct` — both verified present in the live
NVIDIA API catalogue and both carrying a reviewed `NVIDIA_MODEL_CONFIG` entry.

A hard filter in `routing.is_eligible()` removes development-only models from
any public chain, so **no public request can reach NVIDIA**.

Models are labelled **"NVIDIA preview"**,
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

## Automatic routing

Normal users do not choose a model. `ai_gateway/routing.py` turns *what the
request needs* into an ordered chain of approved free models.

A **routing profile** is built only from things EcoIQ controls — never from
free-form user input:

| Input | Source |
| --- | --- |
| task, privacy level, min context | the active module, via `AI_MODULE_ROUTING` |
| output ceiling, capability preference | the answer mode (`auto` / `quick` / `deep`) |
| language | validated language code only |
| required modality | derived from the request payload |
| structured-output requirement | the module's routing profile |
| context length | the larger of module, mode and an estimate of the conversation |
| audience | public vs staff/development |

**Hard filters** then remove anything ineligible: not free, cooling off after a
recent failure, missing a required capability, too small a context window, or —
for a public caller — development-only. **Scoring** ranks what survives by task
benchmark, configured priority, mode preference and recent health.

The public chain is therefore:

```
1. Nemotron 3 Super           ← primary model for ordinary users
2. next compatible free model
3. openrouter/free            ← the reserve, holds the LAST slot
4. FREE_MODELS_UNAVAILABLE    ← never a paid model
```

**Ordinary users** get `nvidia/nemotron-3-super-120b-a12b:free` first (262k
context, tools, structured outputs), with `openrouter/free` as the reserve.
**Staff and development users** additionally get NVIDIA NIM. **Bytez is off** —
see below.

`openrouter/free` is deliberately last: it is the reserve when nothing more
specific works, not the default first choice. It **holds the last slot** rather
than queueing behind the specific models — otherwise a large approved pool plus
a small `AI_MAX_PROVIDER_ATTEMPTS` would truncate it away and the documented
final reserve would be unreachable.

There is no free Kimi/Moonshot model: all eight in the OpenRouter catalogue are
paid (`moonshotai/kimi-k2.6` is $0.60/M in, $3.41/M out), so none can be used
while `AI_FREE_ONLY=true`.

`AI_MODEL_BENCHMARKS` ships **empty**. EcoIQ has not run its own task
benchmarks, and inventing scores would make routing look principled while being
arbitrary. With no entries the scorer falls back to configured priority.
Populating it changes ranking and nothing else.

### Staff override

Staff may pin a model for benchmarking, reasoning comparison, structured-output
and tool-calling testing, or multilingual evaluation. It is permission-gated
(`AI_STAFF_MODEL_OVERRIDE_ENABLED`), goes through `registry.resolve()` so it
accepts only registered keys, cannot reach a paid model, and cannot name a
provider, base URL or raw slug. **No public request ever silently uses NVIDIA
development access.**

## Fallback

Three invariants, enforced structurally rather than by convention:

* **Never leaves the free pool** — the chain is built by the registry from
  already-approved, already-free-eligible models. "Fall back to a paid model" is
  not expressible in this code.
* **Never loops** — the chain is deduplicated by key when built and each key is
  attempted at most once, then capped by `AI_MAX_PROVIDER_ATTEMPTS`.
* **Never falls back on a terminal error** — invalid request, unsupported
  modality, unauthorised, or broken configuration stops immediately.

Fallback *does* happen on: timeout, connection failure, 429, 5xx, model
temporarily unavailable, empty/malformed response, free-plan credits exhausted.
A failing model is also cooled off and demoted in future rankings.

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
always pinned at message index 0. Whichever model automatic routing picks —
and whichever fallback it lands on — changes nothing about it. `system`-role
messages from clients are **rejected**, not silently dropped, so the only path
to a system message is that file.

## User experience

The assistant page shows: EcoIQ Intelligence, a prompt box, answer language,
the answer, and the standard missing-data framing from the system prompt. The
only routing control is an answer mode — **Auto / Quick answer / Deep
analysis** — which adjusts routing requirements, not model selection.

It does **not** show, and cannot send: OpenRouter, Bytez, NVIDIA, model names,
provider or model selectors, base URLs, temperature, or API terminology. The
page does not call `/api/ai/models/` at all.

## Logging

Logger `ecoiq.ai_gateway`. Safe metrics only: internal model key, provider,
resolved model, latency, token counts, fallback flag, normalised error
category, free-policy decision. Never: prompts, responses, API keys, company
context, personal information or hidden reasoning.

## Operations

### Validate the configuration

```bash
python manage.py check_ai_configuration
```

Local-only by default: it reads Django settings and the **cached** registry and
**makes no network call at all** (it uses `registry.peek_cached()`, never
`get_snapshot()`, which would fetch catalogues on a cold cache).

It checks free-only policy, paid-model flags, automatic routing, attempt caps,
fallback config, provider base URLs and credential presence, the OpenRouter free
router, the Bytez allowlist, NVIDIA development-only state, that the public
registry holds no paid and no development-only models, that no raw
provider/model input is accepted from the public API, that default public
routing has a route, and that no fallback loop is possible.

Exit codes: **0** safe (possibly with warnings), **1** unsafe. The distinction
is deliberate — a *warning* means a capability is missing ("Bytez has no
approved models"); an *error* means the deployment could spend money or expose
prototype access, and must not ship. Secrets are never printed, in whole or in
part; a configured key is reported only as "configured".

```bash
python manage.py check_ai_configuration --live-catalog
```

Adds **read-only** catalogue reachability checks. Still never makes an inference
request, never approves a model, never writes an allowlist.

### Refresh the model registry

```bash
python manage.py refresh_ai_models                 # rebuild from live catalogues
python manage.py refresh_ai_models --explain       # why each model was rejected
python manage.py refresh_ai_models --dry-run       # don't write the cache
```

### Survey one provider before allowlisting

```bash
python manage.py refresh_ai_models --provider bytez --dry-run --explain
```

Prints the fields the catalogue actually returns, which the free-policy check
recognises, and a per-model verdict. With no key configured it makes **no
network call** and instead prints the exact command to run once the key is set.

All of these make **no inference request**, purchase nothing, and never
auto-approve a model — approving one means editing the allowlist
(`BYTEZ_APPROVED_MODELS` for Bytez). Safe to schedule if a scheduler already
exists; this change does not create one.

## Tests

```bash
python manage.py test ai_gateway
```

Every provider call is mocked at two seams (`_openai_compat.get_json` and
`.chat_completion`). `NoLiveCallTests` proves the no-network claim rather than
asserting it, by patching `httpx.Client` to raise and confirming a full mocked
request still succeeds.
