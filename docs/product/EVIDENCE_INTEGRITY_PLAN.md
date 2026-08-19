# Evidence Integrity Plan

**Audited against:** `origin/main` @ `39faafb`
**Principle:** UNKNOWN IS NOT NEUTRAL.
**Status:** audit + plan. No schema, scoring or data change is proposed for immediate execution.

---

## 0. The finding that reorders this work

The brief assumed the problem is *"unknown data defaults to 50"*. That is real, but it is
the second-largest problem. Tracing the write path produced a larger one.

**The 27 `CompanyProfile` score fields are populated by seeding commands that generate
values with a seeded random number generator around a hand-assigned target.**

`companies/management/commands/add_400_companies.py:298-340`:

```python
penalty = HARM_PENALTY[harm_level]
base = float(target) + penalty
rng = random.Random(abs(hash(name)) % (2**31))

def n(centre, amp=5):
    return clamp(centre + rng.uniform(-amp, amp))

pb  = n(base)   # public_benefit        25 %
env = n(base)   # environmental         25 %
...
waste = n(env); water = n(env); biodiv = n(env)
```

The company list itself is `(name, sector, country, target_ecoiq_score, harm_level)` — the
score is an editorial input, and the pillar and sub-scores are decomposed back out of it
with ±5 noise. `companies/scoring.py:recalculate_and_save()` then faithfully aggregates
those synthetic inputs into `ecoiq_total_score`, which is published on ~401 public company
pages and registered in `sitemap.xml`.

**Verified, not inferred.** Running `add_400_companies` on a clean database produced 186
profiles; every sub-score is a continuous value in the 21–82 range with no clustering at
any default.

There is **no evidence-linked writer** for these 27 fields, and **no `is_demo` or seed
marker on `CompanyProfile`** to separate seeded rows from any future real ones.

**Consequence for this plan:** a `50 → NULL` migration would not fix the integrity problem,
because the values are not 50. The first job is provenance, not nullability.

---

## 1. Affected fields

### 1.1 `default=50` inventory

| Scope | Count |
|---|---|
| `models.py` files | **39** across 6 apps |
| All `.py` excluding migrations | **41** |
| Including migrations | 80 |

By file:

| File | Count |
|---|---|
| `companies/models.py` | **27** |
| `waste_to_value_capital_allocation_engine/models.py` | 5 |
| `khalifa_stewardship_tour_operating_system/models.py` | 3 |
| `financial_intelligence_cloud/models.py` | 2 |
| `digital_twin/models.py` | 1 |
| `good_agents/models.py` | 1 |

### 1.2 Measured distribution (186 seeded profiles)

| Field | exactly 50.0 | range |
|---|---|---|
| `profit_extraction_score` | **186 (100%)** | 50.0–50.0 |
| `jobs_created_score` | 2 (1.1%) | 24.3–78.4 |
| `future_readiness_score` | 2 (1.1%) | 28.3–78.2 |
| `environmental_responsibility_score` | 2 (1.1%) | 26.0–76.5 |
| 8 further fields | 1 (0.5%) each | ~22–81 |
| 9 fields | 0 | ~21–82 |

**Two things follow.**

1. `profit_extraction_score` is at its default for every profile seeded by
   `add_400_companies` — that command never sets it (three *other* seed commands do, via
   dict literals). It feeds `profit_extraction_warning` (`companies/models.py:350`), which
   is rendered publicly at `templates/companies/detail.html:882`.
2. **Genuine values of exactly 50.0 already exist** — roughly 0.5–1% of cells. Scenario E
   in the brief is not hypothetical. A blind `50 → NULL` migration would destroy them.
   This empirically justifies the safety rule.

---

## 2. Runtime fallback-50 logic

Model defaults are not where most of the damage is. **41 non-model locations** convert
missing data into a value at runtime.

### 2.1 The core scoring engine has three *different* missing-data behaviours

`companies/scoring.py`:

```python
def _clamp(v, lo=0.0, hi=100.0) -> float:
    return max(lo, min(hi, float(v or 0)))          # None -> 0     (!!)

def _avg(*values) -> float:
    filtered = [_clamp(v) for v in values if v is not None]
    return sum(filtered) / len(filtered) if filtered else 50.0   # all-unknown -> 50

def _pollution_to_env_base(pollution_level: str) -> float:
    return {...}.get(pollution_level, 50.0)          # unknown category -> 50
```

- `_clamp(None)` → **0**, the *worst possible* score, not a neutral one. It also cannot
  distinguish `None` from a real `0.0`.
- `_avg()` → **50** when every input is missing.
- `_pollution_to_env_base()` → **50** for an unrecognised category.

`_clamp` is applied directly in `calculate_transparency` (weighted 0.40/0.35/0.25),
`calculate_anti_corruption`, and `calculate_ethical_alignment`.

> **This is the single most important constraint on the migration.** Making these fields
> nullable *today* would silently convert unknown into **0** through `_clamp`, publishing
> the worst possible score for unevidenced companies. Schema-first is unsafe. Calculation
> semantics must be fixed before nullability.

### 2.2 Financing and capital estimates — 22 fallbacks in one file

`financing/matching.py` contains ~22 `or 50` fallbacks feeding financing logic:

```python
mod          = profile.modernization_score or 50.0
energy       = profile.energy_transition_score or 50.0
transparency = profile.transparency_score_detail or 50.0
...
mod_gap      = max(0, 70 - (profile.modernization_score or 50))
```

Note `or 50` is triggered by `0.0` as well as `None` — a genuine zero silently becomes 50.
This is the path the brief singles out: it produces financing recommendations from values
that may be entirely absent.

### 2.3 Confidence itself defaults to 50

`pandas_scoring_engine/services/scoring.py:91`:

```python
avg_confidence = float(np.mean(confidences)) if confidences else 50.0
```

**No confidence data produces "50% confident".** This is the most self-undermining
instance found: the field that exists to express uncertainty fabricates a value.

### 2.4 Clean areas

- **Templates:** no `|default:50` anywhere. `gold_intelligence/investor_view.html` already
  uses an honest pattern worth reusing: `{% if capital.available %}…{% else %}Data source
  required{% endif %}`.
- **Frontend JS:** no `|| 50` / `?? 50` in `frontend/app/src/` or `static/js/`.

---

## 3. Field matrix

Classification per the brief's types. Full per-field table is generated by
`manage.py report_evidence_coverage` (added in D1); the summary:

| Group | Fields | Type | Recommendation |
|---|---|---|---|
| `CompanyProfile` sub-scores (waste, water, biodiversity, jobs, regional, infra, national, energy, digital, infra-upgrade, future, transparency, audit, procurement, anti-corruption) | 15 | **B** — normalised 0–100 from inputs that do not exist yet | Nullable *after* §2.1 is fixed; needs provenance |
| `CompanyProfile` pillar scores (public benefit, environmental, modernization, transparency+AC, ethical alignment) | 5 | **B** — computed by `recalculate_and_save` | Derived; should become `None` when inputs are unknown, never 50 |
| `profit_extraction_score` | 1 | **C** — synthetic neutral, 100% default in the largest seed set, drives a public warning | Highest priority |
| `controversy_risk_score`, `profit_extraction_risk_score` (`default=30.0`) | 2 | **C** — non-50 synthetic defaults, same class of problem | Include in scope |
| `CompanyScoreSnapshot` pillar copies | 6 | **B** — historical snapshots | Snapshot the coverage alongside the score |
| `waste_to_value`, `khalifa_tours`, `financial_intelligence_cloud`, `digital_twin`, `good_agents` | 12 | mixed **B/D/E** | Audit per-app in a later phase; out of the first PR |

---

## 4. Provenance architecture already available

**Do not build a new framework.** The repository already contains four usable pieces.

| Component | What it already provides |
|---|---|
| **`decision_studio.DecisionSession`** | `DATA_AVAILABILITY_CHOICES` = AVAILABLE / PARTIAL / INSUFFICIENT / UNKNOWN, and `CONFIDENCE_CHOICES` = HIGH / MEDIUM / LOW / **INSUFFICIENT_EVIDENCE**, with `confidence_label` defaulting to `INSUFFICIENT_EVIDENCE` — it already fails closed. `confidence_score` is nullable. |
| **`evidence_memory`** | `confidence = FloatField(null=True)` with the comment *"Never fabricated — null until a real confidence value is known."* The correct pattern, already written down. |
| **`company_intelligence`** | `CompanyKPIAssessment` (`status` defaulting to `not_assessed`, `confidence` low/medium/high, `rationale` required to reference linked evidence, `assessed_by`, `last_assessed_at`) plus `CompanyKPIEvidenceLink` — real per-assessment evidence linkage. |
| **`global_research`** | `ResearchClaim` / `ClaimAssessment`, `ContradictionRecord`, `freshness_classification`, `source_owner_type` — source quality and contradiction tracking. |
| **`digital_twin`** | `TwinDataGap` — an explicit model for "this input is missing", and every `ModernisationScenario` impact axis is already `null=True`. |

**Recommended taxonomy: adopt `decision_studio`'s two enums verbatim** rather than
inventing MEASURED/ESTIMATED/MODELLED/INFERRED/UNKNOWN as a third vocabulary. Add a
provenance enum only where the existing two cannot express it:

```
DataAvailability : AVAILABLE | PARTIAL | INSUFFICIENT | UNKNOWN     (existing)
Confidence       : HIGH | MEDIUM | LOW | INSUFFICIENT_EVIDENCE      (existing)
Provenance       : MEASURED | ESTIMATED | MODELLED | INFERRED |
                   SEEDED | LEGACY_UNKNOWN_PROVENANCE               (new, minimal)
```

`SEEDED` is required by §0: the dominant real-world provenance today is "generated by a
seeding command", and the taxonomy must be able to say so rather than laundering it into
`ESTIMATED`.

---

## 5. Can historical values be classified?

**Partly, and the honest answer is mostly no.**

| Signal | Available? | Usable for per-field provenance? |
|---|---|---|
| `CompanyProfile.public_sources` (JSON) | yes | No — profile-level, not per-field |
| `is_verified` | yes | No — profile-level boolean |
| `created_at` / `updated_at` | yes | Weakly — cannot attribute a single field |
| `last_refresh_at`, `last_source_discovery_at`, `tracking_status` | yes | Weakly |
| `CompanyKPIEvidenceLink` | yes | **Yes**, but only for KPI assessments, not the 27 score fields |
| Per-field source / snapshot | **no** | — |
| Seed marker on the profile | **no** | — |

**Therefore:** every existing `CompanyProfile` score value must be classified
`LEGACY_UNKNOWN_PROVENANCE` unless a specific, defensible signal says otherwise. Do not
label historical values `MEASURED`.

One deterministic rule *is* available and worth using: a value that exactly equals the
field default **and** the profile has no evidence links **and** was created by a seeding
run can be classified `SEEDED`. This is precisely the `profit_extraction_score` case
(100% of the `add_400_companies` set). It must not be generalised to fields whose observed
distribution is continuous.

---

## 6. Evidence Coverage — proposal

```
coverage = Σ(weight of inputs with real provenance) / Σ(weight of material inputs)
```

Denominator taken from the actual scoring architecture in `companies/scoring.py`, not
invented. The five pillars carry documented weights (25/25/20/15/10/5), so **material
weighting already exists and should be reused** rather than a new weighting scheme:

| Pillar | Weight | Sub-inputs |
|---|---|---|
| Public benefit | 25% | jobs, regional development, infrastructure contribution, national value |
| Environmental | 25% | pollution level, waste, water, biodiversity |
| Modernization | 20% | energy transition, digitalization, infrastructure upgrade, future readiness |
| Transparency | 15% | transparency detail (0.40), audit quality (0.35), procurement (0.25) |
| Anti-corruption | 10% | anti-corruption |
| Ethical alignment | 5% | controversy risk, national value |

A sub-input counts toward the numerator only when its provenance is `MEASURED`,
`ESTIMATED`, `MODELLED` or `INFERRED` — never `SEEDED` or `LEGACY_UNKNOWN_PROVENANCE`.

**Under this definition, today's coverage for every seeded profile is 0%.** That is the
correct and uncomfortable answer, and it is why thresholds must be chosen with the impact
table in §8 in front of you.

Display only as a whole percentage, and only alongside the count it derives from
(e.g. `Evidence coverage 43% · 6 of 14 material inputs`). No decimal places: the
denominator is 14–17 inputs, so a figure like `82.4%` would be fake precision.

---

## 7. Confidence — proposal

Coverage and confidence are different and must stay separate. Confidence is a function of
the *quality* of what is present, and the repository already models most of its inputs:

| Factor | Existing source |
|---|---|
| Source quality | `global_research.source_owner_type`, `ResearchSource` |
| Recency | `global_research.freshness_classification` (current/stable/stale/unknown), `last_refresh_at` |
| Verification | `CompanyProfile.is_verified`, `CompanyKPIAssessment.status` |
| Contradictions | `global_research.ContradictionRecord` |
| Direct vs inferred | proposed `Provenance` enum |
| Human review | `CompanyKPIAssessment.assessed_by` |

Emit the existing `decision_studio` label set — HIGH / MEDIUM / LOW /
`INSUFFICIENT_EVIDENCE` — and keep the numeric score nullable, as `decision_studio` already
does. **Delete the `else 50.0` at `pandas_scoring_engine/services/scoring.py:91`**; absent
confidence must be `None`, not 50.

---

## 8. Score eligibility — candidate thresholds

Proposed three-state behaviour:

| State | Condition | Public presentation |
|---|---|---|
| Eligible | coverage ≥ T_full **and** confidence ≥ MEDIUM | `EcoIQ Score: 78.4` + coverage + confidence |
| Provisional | T_min ≤ coverage < T_full | `EcoIQ Score: 71.2 — Provisional` + explicit caveat |
| Unavailable | coverage < T_min | `Not available — insufficient evidence to produce a defensible score` |

**Thresholds are deliberately left unset.** The simulation the brief asks for cannot be run
honestly yet, because under §6 every current profile scores 0% coverage — so *any*
threshold above zero makes 100% of the ~401 public profiles Unavailable:

| Minimum coverage | Eligible | Provisional | Unavailable |
|---|---|---|---|
| any value > 0% | **0** | **0** | **all (~401)** |

That is a product decision, not an engineering one, and it is the real content of this
audit. The options are: (a) retire the public company scores until evidence exists,
(b) relabel them explicitly as illustrative/seeded, or (c) treat seeded values as a
provenance tier that is displayed but never presented as measured. **Recommendation: (b)
then (a)** — label first because it is reversible and immediate, retire second.

`manage.py report_evidence_coverage` (shipped in D1) produces this table against the real
production database so the decision is made on real numbers, not this document's.

---

## 9. Financing estimate gating

Everything in `financing/matching.py` that produces a monetary or return figure currently
runs on `or 50` fallbacks (§2.2). Required behaviour:

| Evidence | Output |
|---|---|
| Sufficient | estimate with range, assumptions and provenance |
| Weak | `Indicative modelled range` with caveat |
| Absent | `Insufficient evidence for a defensible estimate` — **no number** |

Implementation note: replace `or 50` with an explicit unknown-propagating helper, so a
missing input makes the *estimate* unavailable rather than making it average. `or 50` must
go regardless of the threshold decision, because it also silently rewrites genuine `0.0`.

---

## 10. Score dependency graph

```
seed command (random.uniform ±5 around editorial target)   <-- actual origin today
        |
        v
CompanyProfile.<15 sub-scores>            default=50.0, NOT NULL
        |
        |  _clamp(v) -> float(v or 0)        None -> 0        (companies/scoring.py:34)
        |  _avg(...) -> 50.0 if all None     unknown -> 50    (companies/scoring.py:38)
        |  _pollution_to_env_base -> 50.0    unknown -> 50    (companies/scoring.py:43)
        v
5 pillar scores  ->  weighted 25/25/20/15/10/5  ->  harm_penalty
        |
        v
CompanyProfile.ecoiq_total_score  ->  CompanyScoreSnapshot
        |
        +--> templates/companies/detail.html      (public)
        +--> companies directory / league table   (public, sorted)
        +--> api/serializers.py FloatField()      (no allow_null)
        +--> sitemap.xml                          (~401 URLs)
        +--> financing/matching.py `or 50` x22    (financing recommendations)
```

---

## 11. Compatibility risks of nullability

| Surface | Risk |
|---|---|
| `companies/scoring.py` | **Blocking** — `_clamp` turns `None` into 0 (§2.1) |
| `api/serializers.py` | `FloatField()` without `allow_null=True` raises on `None` |
| Sorting / rankings | `NULL` ordering differs by backend; unevidenced profiles could sort to an end |
| Templates | `{{ score|floatformat:1 }}` renders `None` as empty; needs `default_if_none` |
| `financing/matching.py` | `or 50` masks `None` today; removing the default exposes it |
| Admin / forms | `FloatField` required unless `blank=True` added |
| Exports / CSV / PDF | `league/pdf_report.py`, report generators |
| Mobile client | consumes the API serializers |
| Tests | ~4,695 currently green; scoring assertions will move |

---

## 12. Recommended PR sequence

The brief's D1 ("schema foundation — allow genuine unknowns") **cannot safely come first**:
§2.1 shows nullable fields would publish 0-scores through `_clamp`. Revised:

| PR | Scope | Risk |
|---|---|---|
| **D1 — measurement foundation** *(this PR)* | Read-only evidence-coverage module + reporting command + invariant tests. No schema, no scoring, no UI change. Produces the real numbers for §8. | **Very low** |
| D2 — calculation semantics | Fix `_clamp` None/0 conflation, make `_avg` propagate unknown, delete the confidence `else 50.0`, replace `financing/matching.py` `or 50`. Scores change; needs before/after distribution comparison. | Medium |
| D3 — provenance schema | Add `Provenance` + per-field or per-profile provenance records; backfill everything as `LEGACY_UNKNOWN_PROVENANCE` / `SEEDED`. | Medium |
| D4 — nullability | `default=50.0` → `null=True`, only after D2 and D3. Irreversible; needs the §13 validation. | High |
| D5 — public eligibility | Provisional / Unavailable states, financing gating, ranking treatment. | Medium |
| D6 — historical cleanup | Only where provenance permits deterministic classification. | High |

---

## 13. Validation required before any production migration (D4+)

1. Backup and a tested rollback path.
2. Run on a copy of production, not production.
3. Row counts before/after.
4. Score distribution before/after.
5. List of profiles whose score changes.
6. List of profiles becoming Unavailable.
7. Verify no evidence records are lost.
8. **Verify genuine `50.0` values survive** — ~0.5–1% of cells (§1.2).
9. Full test suite.
10. CI green.

---

## 14. Separation of concerns — preserved

`StewardshipKPI` (Khalifah governance, with `blocking_threshold` / `blocking_rule`) and the
analytical scores remain **two systems**. Nothing here merges them. A high analytical score
must still be blockable by a stewardship rule, and an unavailable analytical score must not
imply governance approval.
