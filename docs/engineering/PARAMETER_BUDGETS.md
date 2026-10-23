# CI, database and training parameter budgets

## CI execution

`.github/workflows/django.yml` cancels superseded runs of the same PR, using the
workflow name and PR number as the concurrency key. Main push runs use their
commit SHA and finish independently. Lint, typing, skill validation, frontend
and full Django checks remain blocking; no paths or tests are excluded.

The three jobs that install the full Python dependency tree cache pip downloads
against **both** `requirements.txt` and `requirements-dev.txt`. Installation still
runs on every job. Ruff installs only its pinned package, as before.

Job timeouts are 5 minutes for Ruff, 15 each for typing/frontend/skills and 40
for Django. The last observed main workflow before this change completed in
about 21 minutes overall; these are ceilings, not claimed new timings. The
Django job caps OpenMP/OpenBLAS/MKL at one thread to avoid overhead from small
ML test fits. Cache-hit rate and actual runner time must be measured after CI.

## Django database connections

`DATABASE_CONN_MAX_AGE` accepts integer seconds from 0 to 3600 and defaults to
the existing 600-second lifetime. Invalid values fail startup; health checks
remain enabled. A value of 0 closes connections after each request.

Set it below a database/proxy idle timeout. Each WSGI worker thread may keep a
connection, so lifetime alone does not cap connection count: measure active
connections and request latency against the actual database capacity before
changing worker/thread counts. For ASGI, use 0 and review pooling separately.
This change adds an operator control; it does not modify the deployed environment.

## ML selection and resource limits

See [ML_TRAINING.md](ML_TRAINING.md#bounded-parameter-selection) for the
candidate-only eight-configuration scoring search and `--training-jobs` (1..8,
default 1). Nested CV keeps parameter selection separate from outer evaluation.
It still requires independent real-data validation before activation. Existing
model files, source evidence, score publication gates and inference weights
are not rewritten by these code changes.

## Validation

Run with Python 3.11.16 and the repository's development dependencies:

```sh
DEBUG=True OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python manage.py test ml core.tests_quality_gate core.tests_deployment_safety
python manage.py check
python manage.py makemigrations --check --dry-run
ruff check .
```

Tests exercise fold-local preprocessing, serialized candidate/report agreement,
small-data refusal, unsafe-write refusal, bounded worker arguments, native
thread restoration after errors and database lifetime validation.

References: [GitHub concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency),
[Django persistent connections](https://docs.djangoproject.com/en/5.2/ref/databases/#persistent-connections),
[scikit-learn nested CV](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html).
