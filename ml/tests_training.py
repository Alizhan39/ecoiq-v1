"""Synthetic numerical fixtures verify training mechanics, not company quality."""
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import SimpleTestCase
import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler

from ml.features import get_feature_names, MATERIAL_FEATURE_SOURCES
from ml.training import training_rows


class RecordingScaler(StandardScaler):
    fit_sizes = []

    def fit(self, X, y=None, sample_weight=None):
        self.fit_sizes.append(len(X))
        return super().fit(X, y, sample_weight=sample_weight)


def fixtures(n=30):
    rng = np.random.default_rng(42)
    matrix = rng.uniform(10, 90, size=(n, len(get_feature_names())))
    companies = [SimpleNamespace(pk=i + 1, ecoiq_score=float(row[0]),
        profile=SimpleNamespace(**{name: 50.0 for name in MATERIAL_FEATURE_SOURCES}))
        for i, row in enumerate(matrix)]
    return companies, matrix


class TrainingTests(SimpleTestCase):
    def setUp(self):
        self.companies, self.X = fixtures()
        self.vector_patch = patch('ml.training.company_to_vector',
                                  side_effect=lambda company: self.X[company.pk - 1])
        self.vector_patch.start()
        self.addCleanup(self.vector_patch.stop)

    def test_rejects_duplicate_unknown_nonfinite_and_invalid_target_rows(self):
        self.companies[0].profile.public_benefit_score = None
        self.companies[1].profile.public_benefit_score = float('nan')
        self.X[2, 0] = float('inf')
        self.companies[3].ecoiq_score = float('nan')
        X, y, ids, skipped = training_rows(self.companies + [self.companies[-1]], supervised=True)
        self.assertEqual(len(X), 26)
        self.assertTrue(np.isfinite(X).all() and np.isfinite(y).all())
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(skipped, {'unknown_material_inputs': 1, 'invalid_material_inputs': 1,
                                  'invalid_features': 1, 'invalid_target': 1,
                                  'duplicate_or_missing_id': 1})

    def test_cross_validation_fits_scaler_only_on_training_fold(self):
        from ml.scoring_model import EcoIQScoringModel

        RecordingScaler.fit_sizes = []
        with TemporaryDirectory() as root, patch('sklearn.preprocessing.StandardScaler', RecordingScaler):
            result = EcoIQScoringModel().train(self.companies, output_dir=Path(root) / 'scoring')
        self.assertEqual(RecordingScaler.fit_sizes.count(24), 5)
        self.assertEqual(RecordingScaler.fit_sizes.count(30), 1)  # declared final refit
        self.assertEqual(result['evaluation']['status'], 'MEASURED')
        self.assertLess(result['evaluation']['mae'], result['evaluation']['baseline_mae'])
        self.assertFalse(result['independent_evidence_validated'])

    def test_all_three_models_fit_serialize_reload_and_predict(self):
        from ml.anomaly_detection import AnomalyDetector
        from ml.clustering import CompanyClusterer
        from ml.scoring_model import EcoIQScoringModel

        cases = [('scoring', EcoIQScoringModel, 'scoring_gbr.joblib', 'scoring_scaler.joblib'),
                 ('anomaly', AnomalyDetector, 'anomaly_iforest.joblib', 'anomaly_scaler.joblib'),
                 ('clustering', CompanyClusterer, 'cluster_kmeans.joblib', 'cluster_scaler.joblib')]
        with TemporaryDirectory() as root:
            for name, factory, model_file, scaler_file in cases:
                with self.subTest(model=name):
                    directory = Path(root) / name
                    trained = factory()
                    result = trained.train(self.companies, output_dir=directory)
                    model = joblib.load(directory / model_file)
                    scaler = joblib.load(directory / scaler_file)
                    np.testing.assert_allclose(model.predict(scaler.transform(self.X)),
                                               trained.model.predict(trained.scaler.transform(self.X)))
                    report = json.loads((directory / f'{name}_training.json').read_text())
                    self.assertEqual(report, json.loads(json.dumps(result)))
                    self.assertEqual(len(report['artifacts'][model_file]), 64)
                    if name != 'scoring':
                        self.assertEqual(report['evaluation']['status'], 'NOT_MEASURED')

    def test_tiny_dataset_never_reports_training_fit_as_validation_quality(self):
        from ml.scoring_model import EcoIQScoringModel

        with TemporaryDirectory() as root:
            result = EcoIQScoringModel().train(self.companies[:5], output_dir=Path(root) / 'scoring')
        self.assertIsNone(result['r2_mean'])
        self.assertIsNone(result['r2_std'])
        self.assertEqual(result['evaluation']['status'], 'NOT_MEASURED')

    def test_candidate_cannot_replace_existing_directory_or_apply_to_database(self):
        from ml.scoring_model import EcoIQScoringModel

        with TemporaryDirectory() as root:
            target = Path(root) / 'scoring'
            EcoIQScoringModel().train(self.companies, output_dir=target)
            before = (target / 'scoring_gbr.joblib').read_bytes()
            with self.assertRaises(ValueError):
                EcoIQScoringModel().train(self.companies, output_dir=target)
            with self.assertRaises(ValueError):
                EcoIQScoringModel().train(self.companies, output_dir=Path(root) / 'other', apply=True)
            self.assertEqual(before, (target / 'scoring_gbr.joblib').read_bytes())

    def test_constant_target_is_not_saved_as_a_successful_scoring_model(self):
        from ml.scoring_model import EcoIQScoringModel

        for company in self.companies:
            company.ecoiq_score = 50.0
        with TemporaryDirectory() as root:
            target = Path(root) / 'scoring'
            result = EcoIQScoringModel().train(self.companies, output_dir=target)
            self.assertEqual(result['error'], 'constant_target')
            self.assertFalse(target.exists())

    def test_command_refuses_candidate_apply_before_accessing_database(self):
        with self.assertRaisesMessage(CommandError, 'cannot be combined'):
            call_command('train_ml_models', output_dir='/unused/candidate', apply=True, stdout=StringIO())

    def test_command_failure_does_not_announce_pipeline_success(self):
        from companies.management.commands.train_ml_models import Command

        command = Command(stdout=StringIO())
        command.output_dir = None
        with patch('ml.scoring_model.EcoIQScoringModel.train', return_value={
                'error': 'insufficient_data', 'n_samples': 0}), self.assertRaises(CommandError):
            command._run_scoring([], False)
        self.assertNotIn('✓', command.stdout.getvalue())

    def test_command_saves_all_candidates_without_database_updates(self):
        from unittest.mock import MagicMock

        query = MagicMock()
        query.select_related.return_value.order_by.return_value = self.companies
        with TemporaryDirectory() as root, patch('league.models.Company.objects.filter', return_value=query), \
                patch('ml.prediction.predict_12m', return_value=None):
            target = Path(root) / 'candidates'
            call_command('train_ml_models', output_dir=str(target), stdout=StringIO())
            for name in ('scoring', 'anomaly', 'clustering'):
                self.assertTrue((target / name / f'{name}_training.json').exists())
        query.update.assert_not_called()

    def test_forecast_error_is_a_failed_command(self):
        from companies.management.commands.train_ml_models import Command

        command = Command(stdout=StringIO())
        with patch('ml.prediction.apply_predictions', return_value={'updated': 1, 'failed': 1}), \
                self.assertRaises(CommandError):
            command._run_prediction([], True)
        self.assertNotIn('✓', command.stdout.getvalue())
