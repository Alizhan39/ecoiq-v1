# Model training and candidate evaluation

Three existing estimators can be trained: GradientBoostingRegressor scoring,
IsolationForest statistical outliers, and KMeans peer groups. The OLS forecast
is a history-based calculation, not another neural network. The Islamic search
encoder is pretrained and pinned; the company training command does not fine-tune it.

## Current run status: 2026-10-09

Real-data training is **not performed**: no approved training dataset is accessible
in this run. The local database has no `league_company` table. No production
records were exported or updated and no replacement production weights were
produced. Deployment access details are deliberately kept out of this public
engineering document.

Existing scoring artefact loading also failed in the local scikit-learn 1.9.1
runtime with `ModuleNotFoundError: _loss`. Do not resolve this by silently
changing pickle imports. Rebuild from reviewed data in the deployment's tested
runtime and record the package versions. Do not load untrusted joblib files.

The numerical fixtures in `ml/tests_training.py` are explicitly synthetic. They
exercise fitting, fold isolation, serialization/reloading and inference; they
do not establish accuracy on companies, wrongdoing, ethical quality, or religious
retrieval. Fixture-generated models stay in temporary test directories.

## Real-data candidate run

After database access is restored and data provenance reviewed, run in an
authorized environment with the deployment's Python and dependency versions:

```sh
python manage.py train_ml_models --model=scoring --output-dir=/secure/ecoiq/candidates/run-001
python manage.py train_ml_models --model=anomaly --output-dir=/secure/ecoiq/candidates/run-001
python manage.py train_ml_models --model=clustering --output-dir=/secure/ecoiq/candidates/run-001
```

Each model writes to its own new subdirectory with the estimator, scaler and
JSON report. Reports include ordered feature names, feature-set version,
numerical input hash, seed, skipped-input counts, runtime versions and artefact
SHA-256 hashes. They contain no company names or raw training rows. The numeric
hash tracks the ordered training matrix and targets; it is not a source-evidence
digest or an independently reviewed dataset version.

Candidate directories cannot already exist and cannot be used with `--apply`.
No automatic promotion is performed. Training without `--output-dir` now fails
before querying the database unless `--allow-legacy-write` is explicitly passed.
`--apply` alone is not sufficient. The override cannot be combined with candidate
output and prints a warning: it is not evidence of independent review or quality.
With the override, training still replaces `ml/models` even without `--apply`;
`--apply` additionally updates records. A prediction-only read-only preview remains
available without either flag. Direct Python trainer calls retain their legacy
behavior; this guard protects the management command, not every internal caller.
Use candidate mode for experimentation. Existing automation that intentionally
writes must be reviewed before adding the override; do not add it blindly.

See [release verification](RELEASE_346_347.md) for activation gates and evidence.

## Quality and data requirements

- Skip duplicate/missing company IDs, unknown or nonfinite material inputs,
  malformed/nonfinite vectors and invalid scoring targets. Numerical completeness
  does not prove the company's source evidence is reliable.
- Score targets are existing EcoIQ scores, approximated without added artificial
  label noise. This cannot independently validate fairness or the score formula.
- With ten or more eligible rows, scoring uses five shuffled CV folds with seed 42.
  Each fold fits its own scaler on training rows only. Report MAE, CV R² and a
  mean-score baseline evaluated on the same folds. After evaluation, refit the
  fixed procedure on all eligible rows. No parameters are selected from test scores.
- Five to nine rows may fit a candidate but receive `NOT_MEASURED` quality and
  null R². Constant targets and too few rows are rejected. Ten rows are a technical
  minimum for the split, not a sufficient production dataset.
- Cluster sizes and anomaly counts are training diagnostics. Without reviewed
  labels, their quality remains `NOT_MEASURED`. Cluster names remain heuristics.
- Before activation, use independently reviewed labels, an untouched external
  test set, and splits appropriate to related companies and time. Random folds
  cannot establish performance on future observations or related-entity groups.
- Neural search fine-tuning needs licensed query/passage relevance labels,
  train/validation/test separation, EN/RU/KK/AR evaluation and comparison against
  the pinned encoder. Source passages and citations remain authoritative.

The preprocessing rule follows [scikit-learn's leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html).
For neural work, use the [Sentence Transformers training and evaluation workflow](https://www.sbert.net/docs/sentence_transformer/training_overview.html).

## Verification

```sh
python manage.py test ml --noinput
ruff check .
```

Also check candidate reload/predict in the deployment runtime, compare scoring
MAE with its baseline, inspect per-sector errors and unknown-input exclusions,
and confirm existing artefacts and public scores have not changed before review.

Local validation on 2026-10-09: the complete ML regression suite passed
(174 tests), as did the final nine training checks and the additional forecast
command failure check. Ruff and `git diff --check` passed. Existing `ml/models`
files have no diff. These are code validation results; real-data training and
neural fine-tuning remain unperformed.
