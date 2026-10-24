# Multi-host scoring candidate training

EcoIQ can distribute the **five independent outer folds** of scoring's nested
cross-validation across an existing Dask cluster. Every fold runs the same
eight-candidate, three-inner-fold search, with preprocessing fitted inside its
training split. Each worker uses one task thread and one native math thread.
The coordinator performs final selection/refitting and writes the candidate
and JSON report only after every outer fold succeeds.

This is parallel model selection. A single GradientBoostingRegressor is still
fitted on one machine; training rows are not partitioned for out-of-core tree
building. Anomaly detection, KMeans, OLS and Islamic neural search are not
distributed by this option. Small datasets can run faster locally once network
and serialization costs are considered; no speedup is asserted here.

## Prepare an existing trusted cluster

Use the **same EcoIQ checkout/commit and exact Python/package versions** on
the coordinator and every worker. On each host, install into a dedicated venv:

```sh
python -m pip install -r requirements-training.txt
```

The optional file includes the existing application dependencies and pins
Dask/distributed together; it is not installed by the production web build.
Workers must be able to import `ml.tuning` and `ml.distributed_training` from
the checkout (run commands from its root, or set PYTHONPATH accordingly).
Preflight verifies Python, numerical/distribution package versions and SHA256
of both worker code modules before sending training arrays.

Configure an organization-issued CA, certificate and key for scheduler,
workers and client. All endpoints require mutually authenticated TLS.
Certificate paths below are examples; use your existing PKI and private network.
For the client, Dask reads its standard configuration, for example:

```sh
export DASK_DISTRIBUTED__COMM__TLS__CA_FILE=/secure/cluster-ca.pem
export DASK_DISTRIBUTED__COMM__TLS__CLIENT__CERT=/secure/client-cert.pem
export DASK_DISTRIBUTED__COMM__TLS__CLIENT__KEY=/secure/client-key.pem
```

On the scheduler host:

```sh
dask scheduler --host tls://SCHEDULER_PRIVATE_IP --port 8786 --no-dashboard \
  --tls-ca-file /secure/cluster-ca.pem \
  --tls-cert /secure/scheduler-cert.pem --tls-key /secure/scheduler-key.pem
```

On each of at least two worker processes/hosts:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  dask worker tls://SCHEDULER_PRIVATE_IP:8786 --nthreads 1 --nworkers 1 \
  --memory-limit 2GiB --no-dashboard \
  --tls-ca-file /secure/cluster-ca.pem \
  --tls-cert /secure/worker-cert.pem --tls-key /secure/worker-key.pem
```

Choose memory for the actual dataset: each worker needs a full numeric matrix,
fold copies and estimator overhead. The 2 GiB example is not a sizing guarantee.
No shared filesystem, worker database credentials or production secrets are
needed. Dask executes Python on its workers: use only a cluster you control and
data whose processing rights cover all worker hosts.

## Train a candidate

In an authorized coordinator environment with reviewed company data:

```sh
python manage.py train_ml_models --model=scoring --tune-scoring \
  --training-jobs=1 --dask-scheduler=tls://SCHEDULER_PRIVATE_IP:8786 \
  --output-dir=/secure/ecoiq/candidates/distributed-001
```

At least 30 eligible nonconstant scoring rows are required. The report records
backend, selected worker and host counts, runtime verification and final-refit
location. It retains input/feature hashes and estimator parameters. Addresses,
certificate paths, worker identities and raw rows are not written to the report.
Numeric feature matrices and targets do go over the encrypted cluster connection;
they may still be sensitive. Native limits on the coordinator come from
`--training-jobs`; worker fold fitting stays at one native thread.

No cluster is created by this command. Failure to connect or a worker failure
fails the run without falling back to local training or saving a candidate.
Preflight waits up to 30 seconds for two workers; fold execution has a 30-minute
deadline. Cleanup cancels/releases this run's futures and closes its client; it
does not shut down the scheduler or workers. Already-running fits may finish
after cancellation, but never write artifacts. Final refit runs locally under
the normal command budget and has no separate hard timeout.

Existing candidate-output and database-write guards remain active. Real-data
accuracy, cross-host throughput and deployment readiness need separate evidence;
this feature does not activate models automatically.

## Verification

```sh
python manage.py test ml.tests_distributed_training ml.tests_distributed_integration
```

The integration test starts a temporary TLS scheduler and **two separate worker
processes on one host**, sends synthetic arrays, verifies distinct PIDs and
compares CV metrics, selected parameters and predictions with local execution.
It does not prove physical multi-host network performance. Its dedicated GitHub
workflow installs optional dependencies and runs it as a blocking job.

References: [Dask futures](https://docs.dask.org/en/stable/futures.html) and
[Dask mutual TLS](https://distributed.dask.org/en/stable/tls.html).
