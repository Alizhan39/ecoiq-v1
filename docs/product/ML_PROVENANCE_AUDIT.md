# ML and Greenwashing Provenance — Audit

**D3C-3f.** Audit performed against `main` at `730b69b` before any edit.

The brief's assumption — four modules, four metrics — did not survive the
audit. There are **six** modules that write, **four** registered metrics, and
the two do not line up.

---

## 1. Inventory of ML outputs

| Output | Function | Persisted? | Registry key | Inputs | Model / version | Public or API consumer |
|---|---|---|---|---|---|---|
| Greenwashing risk score | `ml.ethics.greenwashing_risk.greenwashing_from_profile` | **No** — `GreenwashingAssessment` dataclass | `greenwashing.risk` | 6 material + 1 derived pillar (`company.transparency_governance`); `audit_quality_score` drops out when `is_verified` | deterministic, `ecoiq-greenwashing-public-data` v1 | `api/views.py` via `compute_ethical_intelligence`; Mizan (advisory only); `mizan/project.py` |
| Responsible Finance score | `ml.responsible_finance.compute_responsible_finance_score` | **No** — returned dict | `ml.responsible_finance` | 1 material + 6 derived (5 pillars + `company.harm_penalty`) | deterministic, `ecoiq-responsible-finance-stewardship` v1 | `api/views.py:440`; `compute_responsible_finance` command (logs to `DataIngestionLog`, does not persist the score) |
| ML company score | `EcoIQScoringModel._apply_scores` (batch) / `.predict_company` (single) | **Yes** — `league.Company.ml_score`, `ml_score_confidence` | `ml.score` | 15 registered of 29 model features | GBR artefact; `fs<feature-set>+<sha256[:12]>` | `companies/views.py:995` |
| 12-month forecast | `ml.prediction.predict_12m` / `apply_predictions` | **Yes** — `league.Company.ml_predicted_score_12m` | `ml.predicted_12m` | **1** declared; see §4 | OLS, `ecoiq-forecast-ols-12m` v1 | `train_ml_models` command |
| Peer cluster + label | `CompanyClusterer._apply_clusters` | **Yes** — `ml_cluster`, `ml_cluster_label` | **none** | K-Means over the same 29 features | KMeans artefact | `companies/views.py:1014` |
| Anomaly score + flag | `AnomalyDetector._apply_scores` | **Yes** — `anomaly_score`, `is_anomaly` | **none** | IsolationForest over the same features | IForest artefact | `companies/views.py:1003` |
| Ethical intelligence bundle | `ml.ethics.compute_ethical_intelligence` | **No** | **none** — an aggregate of other outputs | greenwashing + 5 ethics sub-scores | composition, no model | `api/views.py` ×3 |

**Two outputs were in the brief's expected list but do not exist as separate
metrics:** there is no standalone "classification / probability" metric, and
`ml.responsible_finance` is not a helper behind `financing.readiness` (§3).

**Two writers were NOT in the brief's list** and were found by the audit:
`ml/clustering.py` and `ml/anomaly_detection.py`. Both persist to
`league.Company`. Neither is a registered metric, and no provenance is recorded
for either — see §5.

---

## 2. Why the initial grep missed the writers

Worth recording, because it nearly produced a wrong audit. A search for
`.save(` / `.create(` / `update_or_create` over `ml/` returned **nothing**, and
the obvious conclusion — "ML never writes" — was wrong. All four writers use
`Company.objects.filter(pk=...).update(...)`, a queryset update that no
instance-level hook sees.

That is also why these writes were invisible to earlier provenance work.

---

## 3. `ml.responsible_finance` vs `financing.readiness`

The brief asked whether these are the same thing wearing two names. They are
not.

| | `financing.readiness` (#252) | `ml.responsible_finance` (this PR) |
|---|---|---|
| module | `financing/matching.py` | `ml/responsible_finance.py` |
| persisted | yes — `CompanyFinancingProfile.financing_readiness` | no — returned dict |
| inputs | 4 | 7 |
| framework | capital-readiness matching | five stewardship dimensions |
| cross-reference | none | none |

Neither module imports the other, in either direction. Two independent
assessments that both concern capital. **Classification: ACTIVE, not a legacy
duplicate** — it has a live API consumer at `api/views.py:440`.

---

## 4. `ml.predicted_12m` — lineage that is honestly partial

`predict_12m` has two paths and neither is well described by metric provenance.

- **Primary** (≥3 history points): an OLS fit over `ScoreHistory` rows. It does
  **not** read `company.ecoiq_total` at all.
- **Fallback** (<3 points): anchored on `company.ecoiq_score`, adjusted by up
  to ±10 points of `DataIngestionLog` RSS signal.

`ScoreHistory` and `DataIngestionLog` are *records*, not metrics. They carry no
provenance rows, so there is nothing for the lineage to point at.

The single declared input, `company.ecoiq_total`, is the closest
provenance-bearing relative of the history rows — they are snapshots of that
composite over time — and on the fallback path it is the literal anchor. It is
**not** a claim that the declared input produced the number. The module says so
at the declaration, and a test asserts the disclaimer is present.

The forecast is `MODELLED` on both paths and never inherits the provenance
status of the current score. A projection about next year is a model output
even when every input to it was measured.

---

## 5. Writer classification (STEP 23)

| module | classification | provenance in this PR | rationale |
|---|---|---|---|
| `ml/ethics/greenwashing_risk.py` | **ACTIVE WRITER** (new) | yes — `greenwashing.risk` | live API + Mizan consumer; registered ephemeral metric |
| `ml/responsible_finance.py` | **ACTIVE WRITER** (new) | yes — `ml.responsible_finance` | live API consumer at `api/views.py:440` |
| `ml/scoring_model.py` | **ACTIVE WRITER** | yes — `ml.score` | persists to `league.Company`; consumed by `companies/views.py` |
| `ml/prediction.py` | **ACTIVE WRITER** | yes — `ml.predicted_12m` | persists to `league.Company` |
| `ml/clustering.py` | **ACTIVE WRITER** | **no** — see below | persists `ml_cluster`, `ml_cluster_label` |
| `ml/anomaly_detection.py` | **ACTIVE WRITER** | **no** — see below | persists `anomaly_score`, `is_anomaly` |
| `ml/features.py` | **ACTIVE READ-ONLY** | n/a | feature extraction; no writes |
| `ml/model_identity.py` | **ACTIVE READ-ONLY** (new) | n/a | artefact digests |
| `ml/ethics/ethical_score.py` | **ACTIVE READ-ONLY** | no | aggregate of other outputs, not a metric of its own |
| `ml/ethics/capital_integrity.py` | **ACTIVE READ-ONLY** | no | consumed by `api/views.py`; unregistered |
| `ml/ethics/{evidence_confidence, harm_reduction, justice_balance, public_benefit, stewardship}.py` | **ACTIVE READ-ONLY** | no | reached only through `ethical_score.py`; unregistered sub-scores |
| `ml/finance/islamic_finance_fit.py` | **ACTIVE READ-ONLY** | no | consumed by `mizan/project.py`; unregistered |
| `ml/projects/project_readiness.py` | **ACTIVE READ-ONLY** | no | consumed by `api/views.py`; project-level, not company-level |

**No LEGACY DUPLICATE, LABS or UNUSED module was found.** Every module in `ml/`
has at least one live consumer outside the package. Nothing here needs pruning
on provenance grounds.

### Why clustering and anomaly detection get no provenance yet

Both persist real model outputs, so on the face of it both qualify. Neither was
given a registry key, deliberately:

- **`ml_cluster` / `ml_cluster_label`** are a *peer-group assignment*, not an
  assessment of the company. A cluster index is meaningful only relative to a
  particular fitted K-Means and the population it was fitted on; it is not a
  quantity that can be higher or lower, better or worse. Registering it as a
  metric would put a categorical, population-relative label into a vocabulary
  built for company-level quantities.
- **`anomaly_score` / `is_anomaly`** are closer to a genuine metric, and are
  the stronger candidate of the two. They are excluded here only because the
  brief scoped this PR to the ML/ethical *analytical outputs*, and adding a
  registry key is a semantics decision that deserves its own consideration
  rather than being smuggled in.

Recorded so the gap is explicit rather than accidental. Neither is publicly
exposed today.

---

## 6. D2 residuals found and fixed

Both were found by tracing formulas, not by grep — the same way #252's residual
surfaced.

### `ml/responsible_finance.py` — unknown pollution level scored as medium

```python
pollution_level = getattr(profile, 'pollution_level', 'medium') or 'medium'
pollution_penalty = _POLLUTION_PENALTY.get(pollution_level, 0)   # medium → -5
```

An unclassified company was docked 5 points: an **adverse** finding invented
from an absence. This is the same pattern `greenwashing_from_profile` already
carries a comment about having fixed — *"`or 'medium'` substituted a real
classification for a missing one"* — surviving in a second module.

Fixed: unknown applies no penalty, matching the `harm_penalty` treatment three
lines below, and the unknown is surfaced in `summary_factors` so it is not
mistaken for a measured `low`.

### `ml/scoring_model.py` — batch path bypassed the material-input gate

`predict_company()` refuses to predict when material features are unknown
(#244), because `ml/features.py` imputes `50.0` to satisfy the dense-matrix
contract and the model reads that as an average company.

`_apply_scores()`, the batch path behind `train(apply=True)`, had no such gate.
The same company could therefore have a **persisted** `ml_score` that the API
would decline to produce — and the persisted one wins on every page that reads
the field.

Fixed: the batch path applies the same gate, skipping rather than nulling
(erasing a score another run produced is not this method's mandate).

---

## 7. Defensibility of ML outputs today

Measured on a disposable database with fully evidenced (`MEASURED`) fixtures:

| metric | defensible with fully evidenced inputs | with any SEEDED / LEGACY input |
|---|---|---|
| `greenwashing.risk` | **True** | False |
| `ml.responsible_finance` | **True** | False |
| `ml.score` | **True** | False |
| `ml.predicted_12m` | **True** | False |

Contamination is judged against the *actual* ancestry, not the whole graph.
Seeding `regional_development_score` two layers below leaves `greenwashing.risk`
**True**, correctly: that score reaches the public-benefit pillar, which
greenwashing does not consume. The other three go False. A guard that failed
everything on any contamination anywhere would be easier to defend and would be
wrong.

The guard was **not** changed to manufacture a `True`. These are true only
because the fixtures record genuinely `MEASURED` material provenance, which no
company in the production estate has — every one of the 467 is
`LEGACY_UNKNOWN_PROVENANCE`, so all four metrics are `False` in production and
nothing is published.

### One sharp edge

`ml.score` and `ml.predicted_12m` resolve their value **live** through
`profile.company`, and both writers persist with a queryset `.update()`, which
leaves any in-memory `Company` stale. `_row_is_defensible` rejects a row whose
value resolves to `None`, so the guard answers **False** for a fully defensible
metric when the caller happens to hold a stale instance. Refreshing the
instance flips it to `True`; the rows themselves were never in doubt.

Left as-is deliberately. Refreshing inside the guard would mask a caller bug,
and relaxing the `None` check would weaken a rule that is correct for every
other metric. Nothing on a public path calls this function, so no user-visible
behaviour depends on it. Pinned by tests so it cannot drift silently.

Ephemeral metrics are immune — they resolve from `recorded_value` on the row.

Note what a `True` here does *not* mean. For `ml.score` it means every declared
input is evidenced — 15 of 29 features. The other 14 carry no provenance at
all, so a defensible verdict rests on a lineage that is real but incomplete.
This is the strongest argument for keeping `is_publicly_defensible` gated
behind more than the provenance check alone.

---

## 8. Open items

| item | state |
|---|---|
| `anomaly_score` as a registered metric | **open** — the stronger of the two unregistered writers |
| `ml_cluster` representation | **open** — categorical and population-relative; may never be a metric |
| model artefacts overwritten in place | **open** — digest detects a retrain, cannot retrieve the old model |
| `FEATURE_SET_VERSION` hand-maintained | **open** — a silent reorder would be invisible |
| `ScoreHistory` / `DataIngestionLog` lineage | **open** — see `CALCULATION_CONTEXT_PROVENANCE.md` |
| 14 of 29 `ml.score` features unrepresented | **open** — legacy `Company.score_*` fields and runtime context |
