"""Real TLS scheduler + two worker processes; synthetic numerical data only."""
from importlib.util import find_spec
from unittest import skipUnless
from unittest.mock import patch

from django.test import SimpleTestCase, tag
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from ml.tuning import tune_scoring


@skipUnless(find_spec('distributed'), 'Optional requirements-training.txt not installed')
@tag('dask')
class DaskIntegrationTests(SimpleTestCase):
    def test_two_tls_worker_processes_match_local_metrics_and_predictions(self):
        import os
        from distributed import Client, LocalCluster, Security

        security = Security.temporary()
        rng = np.random.default_rng(42)
        X = rng.uniform(0, 1, size=(30, 3))
        y = X[:, 0] * 100
        estimator = GradientBoostingRegressor(random_state=42)
        local_model, local = tune_scoring(estimator, X, y)
        with LocalCluster(n_workers=2, threads_per_worker=1, processes=True,
                          protocol='tls', security=security, dashboard_address=None,
                          memory_limit='1GiB', silence_logs=40) as cluster:
            with Client(cluster, set_as_default=False) as observer:
                observer.wait_for_workers(2, timeout=30)
                pids = observer.run(os.getpid)
                self.assertEqual(len(set(pids.values())), 2)
                self.assertNotIn(os.getpid(), pids.values())
                # The production path still builds its own encrypted client;
                # only certificate material is supplied from this temporary CA.
                with patch('distributed.security.Security', return_value=security):
                    remote_model, remote = tune_scoring(
                        estimator, X, y, scheduler_address=cluster.scheduler_address)
                self.assertEqual(len(observer.scheduler_info()['workers']), 2)
        for key in ('mae', 'baseline_mae'):
            self.assertAlmostEqual(local['evaluation'][key], remote['evaluation'][key], places=12)
        self.assertAlmostEqual(local['r2_mean'], remote['r2_mean'], places=12)
        np.testing.assert_allclose(local_model.predict(X), remote_model.predict(X))
        self.assertEqual(local['tuning']['selected_parameters'], remote['tuning']['selected_parameters'])
        self.assertEqual(remote['execution']['worker_count'], 2)
        self.assertEqual(remote['execution']['host_count'], 1)  # local test is not two physical hosts
        self.assertTrue(remote['execution']['runtime_verified'])
