"""Offline boundaries: no datasets sent before runtime/resource validation."""
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import MagicMock, patch

from django.core.management import call_command, CommandError
from django.test import SimpleTestCase
import numpy as np

from ml.distributed_training import distributed_folds, validate_scheduler
from ml.scoring_model import EcoIQScoringModel
from ml.tests_training import fixtures


class DistributedTrainingTests(SimpleTestCase):
    def test_only_explicit_tls_addresses_are_accepted(self):
        for value in ('tcp://host:8786', 'host:8786', 'tls://host',
                      'tls://user:secret@host:8786', 'tls://host:8786/path'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_scheduler(value)
        validate_scheduler('tls://scheduler.internal:8786')

    def test_command_rejects_unsafe_modes_before_database_access(self):
        cases = ({}, {'model': 'anomaly', 'tune_scoring': True},
                 {'model': 'scoring', 'tune_scoring': True, 'apply': True},
                 {'model': 'scoring', 'tune_scoring': True, 'allow_legacy_write': True})
        for options in cases:
            with self.subTest(options=options), patch('league.models.Company.objects.filter') as query:
                with self.assertRaisesMessage(CommandError, '--dask-scheduler requires'):
                    call_command('train_ml_models', dask_scheduler='tls://host:8786',
                                 output_dir='/unused/candidate', stdout=StringIO(), **options)
                query.assert_not_called()

    def test_remote_failure_does_not_create_candidate_or_replace_active_model(self):
        companies, X = fixtures()
        scorer = EcoIQScoringModel()
        with TemporaryDirectory() as root, \
                patch('ml.training.company_to_vector', side_effect=lambda c: X[c.pk - 1]), \
                patch('ml.distributed_training.distributed_folds', side_effect=RuntimeError('worker failed')):
            target = Path(root) / 'candidate'
            with self.assertRaisesMessage(RuntimeError, 'worker failed'):
                scorer.train(companies, output_dir=target, tune=True,
                             scheduler_address='tls://host:8786')
            self.assertFalse(target.exists())
            self.assertIsNone(scorer.model)

    def test_direct_remote_training_requires_candidate_tuning(self):
        for options in ({}, {'tune': True}, {'tune': True, 'apply': True}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                EcoIQScoringModel().train([], scheduler_address='tls://host:8786', **options)

    def test_runtime_mismatch_or_threaded_workers_abort_before_scatter(self):
        for threads, mismatch in ((2, False), (1, True)):
            with self.subTest(threads=threads, mismatch=mismatch):
                client = MagicMock()
                client.scheduler_info.return_value = {'workers': {
                    'tls://a:1': {'nthreads': threads, 'host': 'a'},
                    'tls://b:1': {'nthreads': threads, 'host': 'b'},
                }}
                client.run.return_value = {'tls://a:1': {'version': 'different'}}
                factory = MagicMock()
                factory.return_value.__enter__.return_value = client
                module = ModuleType('distributed')
                module.Client, module.wait = factory, MagicMock()
                security = ModuleType('distributed.security')
                security.Security = MagicMock()
                with patch.dict('sys.modules', {'distributed': module, 'distributed.security': security}), \
                        patch('ml.distributed_training.runtime_signature', return_value={'version': 'expected'}):
                    with self.assertRaises(ValueError):
                        distributed_folds(None, np.ones((30, 2)), np.ones(30),
                                          [(np.arange(24), np.arange(24, 30))] * 5, 'tls://host:8786')
                client.scatter.assert_not_called()
                client.submit.assert_not_called()

    def test_command_passes_the_scheduler_to_scoring(self):
        query = MagicMock()
        companies = [object()]
        query.select_related.return_value.order_by.return_value = companies
        with patch('league.models.Company.objects.filter', return_value=query), \
                patch('ml.scoring_model.EcoIQScoringModel.train', return_value={
                    'n_samples': 30, 'r2_mean': None}) as train:
            call_command('train_ml_models', model='scoring', tune_scoring=True,
                         output_dir='/unused/candidate', dask_scheduler='tls://host:8786', stdout=StringIO())
        train.assert_called_once_with(companies=companies, apply=False, tune=True,
                                      output_dir=Path('/unused/candidate/scoring'),
                                      scheduler_address='tls://host:8786')

    def test_failed_remote_batch_releases_data_and_cancels_only_its_tasks(self):
        client = MagicMock()
        client.scheduler_info.return_value = {'workers': {
            'tls://a:1': {'nthreads': 1, 'host': 'a'},
            'tls://b:1': {'nthreads': 1, 'host': 'b'},
        }}
        client.run.return_value = {'tls://a:1': {}, 'tls://b:1': {}}
        data = [MagicMock(), MagicMock()]
        client.scatter.return_value = data
        task = MagicMock()
        client.submit.return_value = task
        factory = MagicMock()
        factory.return_value.__enter__.return_value = client
        module = ModuleType('distributed')
        module.Client = factory
        module.wait = MagicMock(side_effect=TimeoutError('fixture deadline'))
        security = ModuleType('distributed.security')
        security.Security = MagicMock()
        with patch.dict('sys.modules', {'distributed': module, 'distributed.security': security}), \
                patch('ml.distributed_training.runtime_signature', return_value={}):
            with self.assertRaises(TimeoutError):
                distributed_folds(None, np.ones((30, 2)), np.ones(30),
                                  [(np.arange(24), np.arange(24, 30))] * 5, 'tls://host:8786')
        client.cancel.assert_called_once_with([task] * 5)
        task.release.assert_called()
        for future in data:
            future.release.assert_called_once()
        client.shutdown.assert_not_called()
