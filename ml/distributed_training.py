"""Optional Dask execution of independent outer scoring folds.

Workers receive numerical arrays and estimators only; they never query Django
or write model artifacts. The coordinator retains final selection and saving.
"""
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import platform
from urllib.parse import urlsplit


def validate_scheduler(address):
    parsed = urlsplit(address)
    if (parsed.scheme != 'tls' or not parsed.hostname or not parsed.port
            or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise ValueError('Dask scheduler must be a tls://host:port address.')


def runtime_signature():
    """Compare code/runtime before any dataset is sent to workers."""
    root = Path(__file__).resolve().parent
    return {
        'python': platform.python_version(),
        'packages': {name: version(name) for name in (
            'numpy', 'scipy', 'scikit-learn', 'joblib', 'threadpoolctl', 'dask', 'distributed')},
        'code': {name: sha256((root / name).read_bytes()).hexdigest()
                 for name in ('tuning.py', 'distributed_training.py')},
    }


def fit_outer_fold(search, X, y, train, test):
    """One independent selection/evaluation; nested search stays sequential."""
    from sklearn.base import clone
    from sklearn.dummy import DummyRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
    from threadpoolctl import threadpool_limits

    with threadpool_limits(limits=1):
        fitted = clone(search).fit(X[train], y[train])
        predicted = fitted.predict(X[test])
        baseline = DummyRegressor(strategy='mean').fit(X[train], y[train]).predict(X[test])
    return {'r2': float(r2_score(y[test], predicted)),
            'mae': float(mean_absolute_error(y[test], predicted)),
            'baseline_mae': float(mean_absolute_error(y[test], baseline))}


def distributed_folds(search, X, y, splits, scheduler_address):
    validate_scheduler(scheduler_address)
    try:
        from distributed import Client, wait
        from distributed.security import Security
    except ImportError as exc:
        raise ValueError('Install requirements-training.txt to use multi-host training.') from exc

    # Security reads the configured CA/client certificate/key from Dask config.
    # No auto-created LocalCluster and no plaintext remote dataset transfer.
    with Client(scheduler_address, security=Security(require_encryption=True),
                timeout='15s', set_as_default=False) as client:
        client.wait_for_workers(2, timeout=30)
        workers = client.scheduler_info()['workers']
        addresses = sorted(workers)[:len(splits)]
        if len(addresses) < 2 or any(workers[a]['nthreads'] != 1 for a in addresses):
            raise ValueError('Use at least two Dask workers, each with one task thread.')
        expected = runtime_signature()
        signatures = client.run(runtime_signature, workers=addresses)
        if any(signature != expected for signature in signatures.values()):
            raise ValueError('Dask worker code or package versions do not match the coordinator.')

        scattered, futures = [], []
        try:
            scattered = client.scatter([X, y], broadcast=False, hash=False)
            for index, (train, test) in enumerate(splits):
                futures.append(client.submit(
                    fit_outer_fold, search, *scattered, train, test,
                    workers=[addresses[index % len(addresses)]],
                    allow_other_workers=False, pure=False, retries=0,
                ))
            wait(futures, timeout=1800)
            rows = client.gather(futures)
            return rows, {
                'backend': 'dask', 'outer_folds': len(splits),
                'worker_count': len(addresses),
                'host_count': len({workers[a]['host'] for a in addresses}),
                'worker_native_threads': 1, 'inner_search_jobs': 1,
                'final_refit': 'coordinator', 'runtime_verified': True,
            }
        except BaseException:
            if futures:
                client.cancel(futures)
            raise
        finally:
            for future in futures + scattered:
                future.release()
