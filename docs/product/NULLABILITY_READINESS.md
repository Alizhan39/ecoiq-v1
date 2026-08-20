# D4 Nullability Readiness

**Status: read-only survey. Nothing in this document has been changed.**

Produced during D2c (see PR #244) as the safety map for D4. It answers a
different question from the D2/D2b/D2c fallback sweeps, and the two must not be
confused:

| sweep | question | pattern |
|---|---|---|
| fallback (D2–D2c) | does this code INVENT a number when the value is missing? | `x or 50`, `float(v or 0)`, `.get(k, 50)` |
| **nullability (this)** | **does this code CRASH when the value is missing?** | `round(x, 1)`, `float(x)`, `x < 50`, `f'{x:.1f}'` |

A site can be clean on the first and fatal on the second. `round(profile.public_benefit_score, 1)`
fabricates nothing — it is honest code — and it raises `TypeError` the moment
that column is nullable. Those sites are invisible to a fallback search, which is
why this document exists before D4 rather than during it.

## Why now

D2 (#242), D2b (#243) and D2c (#244) made the calculation layer able to *produce*
`None`. D3 adds provenance. D4 makes the columns nullable — and the instant it
does, every site below receives a `None` it was never written to handle. Most of
them are on public request paths, so the failure mode is a 500 on a company page,
not a wrong number.

**None of these are bugs today.** Every listed column is currently `NOT NULL`,
so none of these expressions can receive `None`. They become bugs on the D4
migration, and they must be fixed in the same change that makes the columns
nullable — not after.

## Summary

| operation | sites |
|---|---|
| `round()` | 26 |
| `float()/int()` | 65 |
| `comparison` | 20 |
| `f-string :.Nf` | 56 |
| **total** | **167 across 51 modules** |

## Sites

| Site | Field | Operation | None-safe? | Public/internal | Fix needed before D4 |
|---|---|---|---|---|---|
| `api/v2_serializers.py:44` | `score` | `round()` | No | **public** | Yes |
| `api/views.py:411` | `ecoiq_score` | `float()/int()` | No | **public** | Yes |
| `companies/embed_views.py:117` | `score` | `float()/int()` | No | **public** | Yes |
| `companies/embed_views.py:122` | `score` | `f-string :.Nf` | No | **public** | Yes |
| `companies/investment_report.py:230` | `total_score` | `f-string :.Nf` | No | **public** | Yes |
| `companies/investment_report.py:231` | `total_score` | `f-string :.Nf` | No | **public** | Yes |
| `companies/investment_report.py:262` | `controversy_risk_score` | `f-string :.Nf` | No | **public** | Yes |
| `companies/investment_report.py:382` | `ecoiq_total_score` | `float()/int()` | No | **public** | Yes |
| `companies/investment_report.py:383` | `public_benefit_score` | `float()/int()` | No | **public** | Yes |
| `companies/investment_report.py:384` | `environmental_responsibility_score` | `float()/int()` | No | **public** | Yes |
| `companies/investment_report.py:385` | `modernization_score` | `float()/int()` | No | **public** | Yes |
| `companies/investment_report.py:386` | `transparency_anti_corruption_score` | `float()/int()` | No | **public** | Yes |
| `companies/investment_report.py:387` | `controversy_risk_score` | `float()/int()` | No | **public** | Yes |
| `companies/views.py:627` | `history_scores` | `round()` | No | **public** | Yes |
| `companies/views.py:636` | `public_benefit_score` | `round()` | No | **public** | Yes |
| `companies/views.py:637` | `environmental_responsibility_score` | `round()` | No | **public** | Yes |
| `companies/views.py:638` | `modernization_score` | `round()` | No | **public** | Yes |
| `companies/views.py:639` | `transparency_anti_corruption_score` | `round()` | No | **public** | Yes |
| `companies/views.py:640` | `anti_corruption_score` | `round()` | No | **public** | Yes |
| `companies/views.py:641` | `ethical_alignment_score` | `round()` | No | **public** | Yes |
| `companies/views.py:1103` | `scores` | `float()/int()` | No | **public** | Yes |
| `companies/views.py:1159` | `score` | `f-string :.Nf` | No | **public** | Yes |
| `companies/views.py:1365` | `score` | `f-string :.Nf` | No | **public** | Yes |
| `core/views.py:536` | `score_overall` | `float()/int()` | No | **public** | Yes |
| `countries/views.py:289` | `transition_readiness_score` | `round()` | No | **public** | Yes |
| `countries/views.py:290` | `policy_environment_score` | `round()` | No | **public** | Yes |
| `countries/views.py:291` | `investment_climate_score` | `round()` | No | **public** | Yes |
| `countries/views.py:292` | `transparency_score` | `round()` | No | **public** | Yes |
| `countries/views.py:293` | `industrial_modernization_score` | `round()` | No | **public** | Yes |
| `harvester/views.py:73` | `source_quality_score` | `round()` | No | **public** | Yes |
| `intelligence/views.py:74` | `scores` | `float()/int()` | No | **public** | Yes |
| `intelligence/views.py:116` | `ecoiq_score` | `float()/int()` | No | **public** | Yes |
| `intelligence/views.py:131` | `ecoiq_score` | `float()/int()` | No | **public** | Yes |
| `intelligence/views.py:188` | `scores` | `float()/int()` | No | **public** | Yes |
| `intelligence/views.py:255` | `score` | `float()/int()` | No | **public** | Yes |
| `intelligence/views.py:286` | `ecoiq_score` | `float()/int()` | No | **public** | Yes |
| `intelligence/views.py:330` | `scores` | `float()/int()` | No | **public** | Yes |
| `intelligence/views.py:451` | `ecoiq_score` | `float()/int()` | No | **public** | Yes |
| `intelligence/views.py:469` | `scores` | `float()/int()` | No | **public** | Yes |
| `intelligence/views.py:511` | `ecoiq_score` | `float()/int()` | No | **public** | Yes |
| `investor_portfolio/changes.py:92` | `exposure_score` | `round()` | No | **public** | Yes |
| `league/pdf_report.py:164` | `score` | `float()/int()` | No | **public** | Yes |
| `league/pdf_report.py:189` | `history_scores` | `float()/int()` | No | **public** | Yes |
| `league/views.py:73` | `score_pollution_footprint` | `comparison` | No | **public** | Yes |
| `league/views.py:91` | `score_reduction_progress` | `comparison` | No | **public** | Yes |
| `league/views.py:109` | `score_investment` | `comparison` | No | **public** | Yes |
| `league/views.py:127` | `score_transparency` | `comparison` | No | **public** | Yes |
| `league/views.py:145` | `score_community_impact` | `comparison` | No | **public** | Yes |
| `league/views.py:191` | `ecoiq_score` | `float()/int()` | No | **public** | Yes |
| `league/views.py:228` | `_sector_scores` | `float()/int()` | No | **public** | Yes |
| `league/views.py:250` | `score` | `float()/int()` | No | **public** | Yes |
| `league/views.py:256` | `ecoiq_score` | `float()/int()` | No | **public** | Yes |
| `league/views.py:288` | `ecoiq_score` | `float()/int()` | No | **public** | Yes |
| `league/views.py:311` | `history_scores` | `float()/int()` | No | **public** | Yes |
| `league/views.py:321` | `ecoiq_score` | `float()/int()` | No | **public** | Yes |
| `league/views.py:331` | `score` | `float()/int()` | No | **public** | Yes |
| `league/views.py:332` | `ecoiq_score` | `float()/int()` | No | **public** | Yes |
| `league/views.py:350` | `score` | `float()/int()` | No | **public** | Yes |
| `league/views.py:351` | `ecoiq_score` | `float()/int()` | No | **public** | Yes |
| `league/views.py:497` | `score_arc` | `float()/int()` | No | **public** | Yes |
| `qdf/api_views.py:54` | `decision_integrity_score` | `round()` | No | **public** | Yes |
| `qdf/api_views.py:69` | `score` | `round()` | No | **public** | Yes |
| `qdf/api_views.py:148` | `decision_integrity_score` | `round()` | No | **public** | Yes |
| `agent_training_evaluation_lab/admin.py:44` | `overall_score` | `f-string :.Nf` | No | internal | Yes |
| `agent_training_evaluation_lab/models.py:89` | `score` | `f-string :.Nf` | No | internal | Yes |
| `audit/models.py:384` | `confidence_score` | `round()` | No | internal | Yes |
| `backend_intelligence_engine/tasks.py:119` | `score` | `f-string :.Nf` | No | internal | Yes |
| `capital_guardian/services/command_centre.py:412` | `score` | `f-string :.Nf` | No | internal | Yes |
| `cms/blocks.py:175` | `ecoiq_score` | `float()/int()` | No | internal | Yes |
| `cms/blocks.py:185` | `history_scores` | `float()/int()` | No | internal | Yes |
| `cms/blocks.py:215` | `ecoiq_score` | `float()/int()` | No | internal | Yes |
| `cms/models.py:123` | `ecoiq_score` | `float()/int()` | No | internal | Yes |
| `cms/models.py:186` | `ecoiq_score` | `float()/int()` | No | internal | Yes |
| `cms/models.py:200` | `history_scores` | `float()/int()` | No | internal | Yes |
| `companies/admin.py:287` | `ecoiq_total_score` | `comparison` | No | internal | Yes |
| `companies/admin.py:291` | `ecoiq_total_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/admin.py:605` | `total_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/ai_helpers.py:94` | `ecoiq_total_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/ai_helpers.py:95` | `public_benefit_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/ai_helpers.py:96` | `environmental_responsibility_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/ai_helpers.py:97` | `modernization_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/ai_helpers.py:98` | `transparency_anti_corruption_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/ai_helpers.py:99` | `anti_corruption_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/ai_helpers.py:100` | `ethical_alignment_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/ai_helpers.py:101` | `profit_extraction_risk_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/ai_helpers.py:259` | `current_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/ai_helpers.py:260` | `target_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/ai_helpers.py:264` | `current_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/ai_helpers.py:266` | `target_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/ai_helpers.py:275` | `target_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/management/commands/build_embeddings.py:85` | `public_benefit_score` | `f-string :.Nf` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `companies/management/commands/build_embeddings.py:86` | `environmental_responsibility_score` | `f-string :.Nf` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `companies/management/commands/build_embeddings.py:87` | `transparency_anti_corruption_score` | `f-string :.Nf` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `companies/management/commands/build_embeddings.py:88` | `modernization_score` | `f-string :.Nf` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `companies/management/commands/compute_responsible_finance.py:88` | `score` | `f-string :.Nf` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `companies/management/commands/seed_companies.py:975` | `ecoiq_total_score` | `f-string :.Nf` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `companies/management/commands/seed_score_history.py:82` | `public_benefit_score` | `round()` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `companies/management/commands/seed_score_history.py:83` | `environmental_score` | `round()` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `companies/management/commands/seed_score_history.py:84` | `modernization_score` | `round()` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `companies/management/commands/seed_score_history.py:85` | `governance_score` | `round()` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `companies/management/commands/seed_score_history.py:86` | `anti_corruption_score` | `round()` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `companies/management/commands/seed_score_history.py:87` | `ethical_alignment_score` | `round()` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `companies/models.py:293` | `ecoiq_total_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/models.py:340` | `modernization_score` | `comparison` | No | internal | Yes |
| `companies/models.py:345` | `transparency_score_detail` | `comparison` | No | internal | Yes |
| `companies/models.py:350` | `profit_extraction_score` | `comparison` | No | internal | Yes |
| `companies/models.py:351` | `public_benefit_score` | `comparison` | No | internal | Yes |
| `companies/models.py:527` | `total_score` | `f-string :.Nf` | No | internal | Yes |
| `companies/screening.py:66` | `score` | `f-string :.Nf` | No | internal | Yes |
| `companies/screening.py:72` | `score` | `f-string :.Nf` | No | internal | Yes |
| `company_intelligence/services/evidence_review.py:340` | `freshness_score` | `comparison` | No | internal | Yes |
| `ethics/admin.py:171` | `composite_ethics_score` | `f-string :.Nf` | No | internal | Yes |
| `ethics/admin.py:190` | `composite_ethics_score` | `f-string :.Nf` | No | internal | Yes |
| `ethics/models.py:311` | `normalized_score` | `f-string :.Nf` | No | internal | Yes |
| `financing/matching.py:529` | `score` | `f-string :.Nf` | No | internal | Yes |
| `geo_intelligence/services/maps.py:84` | `score` | `f-string :.Nf` | No | internal | Yes |
| `ingestion/pipeline.py:829` | `score` | `f-string :.Nf` | No | internal | Yes |
| `intelligence/admin.py:22` | `national_ecoiq_score` | `float()/int()` | No | internal | Yes |
| `intelligence/compute.py:45` | `ecoiq_score` | `float()/int()` | No | internal | Yes |
| `intelligence/compute.py:135` | `current_score` | `float()/int()` | No | internal | Yes |
| `intelligence/compute.py:148` | `score` | `f-string :.Nf` | No | internal | Yes |
| `intelligence/compute.py:164` | `prev_score` | `f-string :.Nf` | No | internal | Yes |
| `intelligence/compute.py:172` | `score_transparency` | `comparison` | No | internal | Yes |
| `intelligence/compute.py:331` | `ecoiq_score` | `float()/int()` | No | internal | Yes |
| `intelligence/management/commands/monitor_companies.py:170` | `prev_score` | `float()/int()` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `intelligence/management/commands/monitor_companies.py:180` | `prev_score` | `float()/int()` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `intelligence/management/commands/monitor_companies.py:183` | `prev_score` | `f-string :.Nf` | No | internal (seed/command) | Yes (guard or skip unscored rows) |
| `league/explainability.py:442` | `confidence_score` | `comparison` | No | internal | Yes |
| `league/explainability.py:719` | `confidence_score` | `comparison` | No | internal | Yes |
| `league/models.py:220` | `ecoiq_score` | `float()/int()` | No | internal | Yes |
| `league/models.py:230` | `ecoiq_score` | `float()/int()` | No | internal | Yes |
| `league/scoring.py:78` | `ecoiq_score` | `float()/int()` | No | internal | Yes |
| `mizan/project.py:322` | `score` | `f-string :.Nf` | No | internal | Yes |
| `mizan/scoring.py:468` | `score` | `f-string :.Nf` | No | internal | Yes |
| `ml/ethics/greenwashing_risk.py:350` | `score` | `f-string :.Nf` | No | internal | Yes |
| `ml/features.py:108` | `score_pollution_footprint` | `float()/int()` | No | internal | Yes |
| `ml/features.py:109` | `score_reduction_progress` | `float()/int()` | No | internal | Yes |
| `ml/features.py:110` | `score_investment` | `float()/int()` | No | internal | Yes |
| `ml/features.py:111` | `score_transparency` | `float()/int()` | No | internal | Yes |
| `ml/features.py:112` | `score_community_impact` | `float()/int()` | No | internal | Yes |
| `ml/features.py:116` | `pb_score` | `float()/int()` | No | internal | Yes |
| `ml/features.py:117` | `env_score` | `float()/int()` | No | internal | Yes |
| `ml/features.py:118` | `modern_score` | `float()/int()` | No | internal | Yes |
| `ml/features.py:119` | `transp_score` | `float()/int()` | No | internal | Yes |
| `ml/features.py:120` | `ethical_score` | `float()/int()` | No | internal | Yes |
| `ml/features.py:121` | `anti_corruption_score` | `float()/int()` | No | internal | Yes |
| `ml/finance/islamic_finance_fit.py:762` | `score` | `f-string :.Nf` | No | internal | Yes |
| `ml/finance/islamic_finance_fit.py:780` | `score` | `f-string :.Nf` | No | internal | Yes |
| `ml/finance/islamic_finance_fit.py:787` | `score` | `f-string :.Nf` | No | internal | Yes |
| `ml/finance/islamic_finance_fit.py:795` | `score` | `f-string :.Nf` | No | internal | Yes |
| `ml/scoring_model.py:77` | `score` | `float()/int()` | No | internal | Yes |
| `pandas_scoring_engine/services/scoring.py:76` | `compute_ecoiq_profile_score` | `f-string :.Nf` | No | internal | Yes |
| `qdf/engine.py:64` | `score` | `float()/int()` | No | internal | Yes |
| `qdf/engine.py:83` | `score` | `float()/int()` | No | internal | Yes |
| `qdf/engine.py:113` | `scored` | `f-string :.Nf` | No | internal | Yes |
| `qdf/engine.py:210` | `decision_integrity_score` | `round()` | No | internal | Yes |
| `qdf/models.py:174` | `decision_integrity_score` | `f-string :.Nf` | No | internal | Yes |
| `qdf/models.py:264` | `score` | `f-string :.Nf` | No | internal | Yes |
| `qdf/models.py:268` | `score` | `comparison` | No | internal | Yes |
| `qdf/models.py:269` | `score` | `comparison` | No | internal | Yes |
| `qdf/models.py:270` | `score` | `comparison` | No | internal | Yes |
| `qdf/models.py:279` | `score` | `comparison` | No | internal | Yes |
| `qdf/models.py:280` | `score` | `comparison` | No | internal | Yes |
| `qdf/models.py:281` | `score` | `comparison` | No | internal | Yes |
| `qdf/scoring.py:190` | `score` | `f-string :.Nf` | No | internal | Yes |
| `transition/engine.py:82` | `score` | `float()/int()` | No | internal | Yes |
| `transition/engine.py:293` | `ecoiq_score` | `float()/int()` | No | internal | Yes |

## Notes on the sweep

**It is a lower bound, not a census.** Four regex patterns were used, listed at
the top. They will miss `sorted(..., key=...)` over score fields, `sum()` over a
values_list, numpy array construction from a queryset, and template filters that
assume a number. Treat the table as the known minimum.

**`ml/features.py` (11 sites) is deliberately exempt.** `_safe_float` imputes
50.0 to satisfy a committed `GradientBoostingRegressor` that cannot accept NaN,
and the fitted scaler was trained on that imputation. Those sites are None-safe
by construction and must NOT be "fixed" without retraining — see the note at the
top of that module. D2c handled the boundary instead:
`missing_material_features()` reports what is unknown, and `predict_company()`
refuses rather than predicting from defaults.

**Seed and management commands** (`seed_score_history.py`,
`build_embeddings.py`, `ingest_*`) write synthetic or derived data. They should
skip unscored rows rather than gain None-guards — a seeder has no business
inventing a value for a company with no score, which is the same rule the rest of
the programme follows.

**`CompanyScoreSnapshot.create_from_profile`** (`companies/models.py:551`)
copies profile values verbatim into the snapshot table. It fabricates nothing, so
it is not in the table above — but its own columns are `NOT NULL`, so D4 must
make the snapshot columns nullable in the *same* migration or every background
refresh will raise `IntegrityError`.

## Recommended D4 sequence

1. Make the `CompanyProfile` score columns nullable **and** the
   `CompanyScoreSnapshot` mirror columns nullable, in one migration.
2. Fix every **public** site in the table above in the same PR. A `TypeError` on
   `/companies/<slug>/` is a 500, and the D1.5 evidence gate does not protect it:
   the gate covers organisations with *no* evidence, while D4 introduces
   organisations with *partial* evidence that render the full page.
3. Fix internal sites.
4. Only then backfill NULLs, and only where provenance (D3) shows the stored
   value was never evidenced. Bulk `50 → NULL` remains explicitly forbidden.

## What this document is not

It is not a list of defects, and it is not a work order for D2c. It is the map
D4 needs so that making a column nullable does not take a public page down.
