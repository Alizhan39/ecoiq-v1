# API Evidence Migration

**Audited against:** `origin/main` @ `3f78683` (post-#239)
**Goal:** unsupported score → not presented as evidence, on every public transport.
**Rule:** unknown → unknown. Never unknown → `0`, `50`, `-1`, `""` or `"N/A"`.

---

## 0. A correction to the stated reason for deferring the API in #239

#239's commit message justified leaving `/api/v1/` unchanged by pointing at "the
shipped Flutter client". **That overstated the constraint.**

Checked on `main`:

| Signal | Finding |
|---|---|
| `mobile/lib/config/environment.dart:46` | `String.fromEnvironment('ECOIQ_ENV', defaultValue: 'mock')` — the app runs against a **mock client** unless explicitly built for production |
| `mobile/pubspec.yaml` | `version: 1.0.0+1` |
| `.github/workflows/mobile.yml:129` | *"Build App Bundle (debug — no release signing configured yet)"* |
| Signing keys | none committed |

**There is no evidence the client has ever been released.** It cannot be proven
that no build was ever side-loaded, but nothing in the repository indicates
distribution.

The decision to leave v1 alone was still correct — but for a *different* reason
than the one given: **v1 is an anonymous public HTTP contract**. `IsPublicOrAPIKey`
allows every GET without authentication, and the `APIKey` model exists, so
external integrators may be consuming it in ways this repository cannot see.
That is the durable argument. The mobile client is a much weaker one, and
treating it as the blocker would have set the migration's pace wrongly.

**Consequence:** the mobile cutover is cheap, not expensive. It does not need a
long compatibility window, and it should not be allowed to gate v1's cleanup.

---

## 1. Every anonymous API surface exposing a score

Probed against production, unauthenticated. `IsPublicOrAPIKey` permits all GETs,
so every row below is **anonymous public**.

| Route | Score fields exposed |
|---|---|
| `/api/v1/companies/` | `ecoiq_score`, `ml_score`, `rank` |
| `/api/v1/companies/<slug>/` | **17 fields** — `ecoiq_score`, `ecoiq_total_score`, `public_benefit_score`, `environmental_responsibility_score`, `modernization_score`, `transparency_anti_corruption_score`, `ethical_alignment_score`, `anti_corruption_score`, `ml_score`, `ml_score_confidence`, `anomaly_score`, `score_pollution_footprint`, `score_reduction_progress`, `score_investment`, `score_transparency`, `score_community_impact`, `rank` |
| `/api/v1/companies/<slug>/scores/` | 15 fields incl. `profile_scores` |
| `/api/v1/leaderboard/` | `ecoiq_score`, `ml_score`, `rank` |
| `/api/v1/search/` | `ecoiq_score`, `ml_score`, `rank` |
| `/api/v1/countries/` | `avg_ecoiq_score` |
| `/api/v1/companies/<slug>/responsible-finance/` | `responsible_finance_score`, `dimension_scores`, `ecoiq_total_score` |
| `/api/v1/intelligence/ethical-score/` | `overall_score`, `harm_score`, `confidence_score`, `greenwashing_risk_score` |
| `/api/v1/companies/<slug>/ethical-intelligence/` | same as above |

**Nine endpoints, not one.** `/api/v1/leaderboard/` was the example, not the
extent.

Not exposing scores: `/companies/<slug>/harm-signals/`, `/assess/<slug>/*`
(404 for the probed slug), `/capital-integrity/` and `/finance/islamic-fit/`
(405 — POST-only). `/assess/<slug>/refresh/` requires an API key.

### Classification

| Tier | Routes |
|---|---|
| **Anonymous public** | all nine above |
| **Authenticated** | `/assess/<slug>/refresh/` (`IsAPIKeyAuthenticated`) |
| **Internal** | none in `api/` — internal surfaces live in gated apps |
| **Mobile contract** | `/companies/`, `/companies/<slug>/`, `/search/` (see §2) |

---

## 2. Mobile consumers

37 `.dart` files. Every score touchpoint:

| File | Line | Current |
|---|---|---|
| `data/models/company.dart` | 19 | `final double ecoiqScore;` (`Company`) |
| `data/models/company.dart` | 29 | `ecoiqScore: double.tryParse('${json['ecoiq_score']}') ?? 0` |
| `data/models/company.dart` | 91 | `final double ecoiqScore;` (`CompanyProfile`) |
| `data/models/company.dart` | 107 | same `?? 0` fallback |
| `features/company/company_profile_screen.dart` | 116 | `profile.ecoiqScore.toStringAsFixed(0)` |
| `features/search/search_screen.dart` | 136–143 | score label, colour tone thresholds, a11y label |
| `core/api/mock_api_client.dart` | 28, 44, 71, 189 | mock fixtures |

**Five files plus tests.** The `?? 0` is the anti-pattern: a missing score
becomes the worst possible score, silently.

---

## 3. Proposed truthful contract

Reuses the #238 foundation — no new status framework. `companies.evidence`
already defines the vocabulary, and it deliberately mirrors
`decision_studio.DecisionSession`.

```json
{
  "slug": "orsted",
  "name": "Ørsted",
  "ecoiq_score": null,
  "score_status": "INSUFFICIENT_EVIDENCE",
  "evidence_coverage": 0,
  "rank": null
}
```

and when evidence exists:

```json
{
  "ecoiq_score": 78.4,
  "score_status": "PUBLISHED",
  "evidence_coverage": 87,
  "rank": 12
}
```

- `score_status` ∈ `PUBLISHED` | `INSUFFICIENT_EVIDENCE` — the constants already
  in `companies/evidence.py`.
- `evidence_coverage` is a whole percent, from `CoverageReport.coverage_percent`.
- `ecoiq_score` is `null`, never `0`. Same for `rank`.
- A genuine `0.0` stays `0.0`; a genuine `50.0` stays `50.0`. **Status, not the
  numeral, carries the meaning** — this is what makes the contract compatible
  with the D-programme's central invariant.

---

## 4. Versioning strategy

The root URLconf already mounts `path('api/v1/', include('api.urls', ...))`, so
the repository's own convention is a path-prefixed version. `/api/v2/` follows
it; no new mechanism is invented.

**v2 is additive.** It introduces new routes and touches no v1 code path, so it
cannot break any existing consumer. That makes it the smallest safe first change.

**v1 is not mutated.** Turning a numeric field into `null` in place would be a
silent contract change for anonymous integrators this repository cannot
enumerate. It also has no deprecation convention today (no `Deprecation` /
`Sunset` header handling anywhere in `api/`), so there is nothing to reuse and
adding one is its own decision.

---

## 5. Release sequence

Adjusted from the brief's shape because §0 removes the long mobile window:

| # | Step | Blocking? |
|---|---|---|
| 1 | **Ship `/api/v2/` alongside v1** (API-A) | no — additive |
| 2 | Update Flutter to nullable score + evidence-pending UI, pointed at v2 (API-B) | no — client unreleased |
| 3 | Verify mobile shows *pending*, never `0` | — |
| 4 | Document v2 as canonical; mark v1 legacy-compatibility in the docs | no |
| 5 | Add `Deprecation`/`Sunset` metadata to v1 responses | needs a convention decision |
| 6 | **Stop v1 exposing unevidenced numerics** (API-C) | breaking — needs a date |
| 7 | Retire v1 | later |

Steps 1–4 create no false user-visible score and break nothing. Step 6 is the
only breaking one.

**Step 2 does not gate step 6** for mobile reasons — the client is unreleased.
Step 6 is gated by *external* integrators, which is a communications decision
about how long v1 stays truthful-but-legacy.

---

## 6. When v1 can safely stop exposing legacy numeric scores

Conditions, all necessary:

1. v2 shipped and documented as canonical (steps 1 and 4).
2. Flutter migrated (step 2) — cheap, and removes the only consumer we can see.
3. A stated sunset window for anonymous integrators. There is no telemetry on
   v1 consumption in this repository, so the window is a judgement, not a
   measurement. **Recommend 90 days from documenting v2 as canonical.**
4. `Deprecation` / `Sunset` metadata live on v1 for that window.

Until then v1 keeps its current numeric contract. It is inconsistent with the
web surface, and that inconsistency is the deliberate cost of not breaking
unknown integrators — recorded here rather than left implicit.

---

## 7. Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | v1 keeps publishing unevidenced numbers while v2 exists | **Medium-High** | Time-boxed; §6 sets the conditions. The web surface — the one people actually read — is already contained by #239 |
| 2 | Unknown third-party v1 integrators | Medium | Additive v2; sunset window; no in-place mutation |
| 3 | Nullable score crashes Flutter elsewhere (sorting, charts, cache) | Medium | §2 lists every touchpoint; API-B must cover all five files, not just the model |
| 4 | v2 drifts from v1 | Low-Medium | v2 serializers derive from the same models; no second scoring path |
| 5 | Doubling endpoint count doubles maintenance | Low | v2 covers the score-bearing routes only, not all 20 |

---

## 8. Rollback

**API-A:** revert. v2 routes disappear; v1 untouched throughout, so no consumer
is affected either way.
**API-B:** revert the Flutter change; the client returns to v1.
**API-C:** revert restores v1's numeric fields.

No data, schema or migration is involved at any step.

---

## 9. PR sequence

| PR | Scope | Breaking |
|---|---|---|
| **API-A** *(implemented now)* | `/api/v2/` with the truthful contract for the company and leaderboard endpoints. Additive. | no |
| API-B | Flutter: nullable `double?`, evidence-pending UI, point at v2, cover all five files | no |
| API-C | v1 deprecation metadata, then stop exposing unevidenced numerics | yes, dated |
| — | then **D2 — calculation semantics** | — |

---

## 10. Scope boundary

This programme is transport only. It does not touch `_clamp`, `_avg`,
`_pollution_to_env_base`, the 22 `or 50` fallbacks in `financing/matching.py`,
model defaults, nullability or schema. Those remain D2–D4, and D2 begins once
API-A is merged.
