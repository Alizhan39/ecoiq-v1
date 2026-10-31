"""Synthetic controls for candidate selection, isolation and output safety."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase
import joblib
import numpy as np

from ml.scoring_model import EcoIQScoringModel
from ml.tests_training import RecordingScaler, fixtures


class CandidateTuningTests(SimpleTestCase):
    def test_nested_selection_is_fold_local_and_saved_candidate_matches_report(self):
        companies, X = fixtures()
        RecordingScaler.fit_sizes = []
        with TemporaryDirectory() as root, \
                patch('ml.training.company_to_vector', side_effect=lambda c: X[c.pk - 1]), \
                patch('ml.tuning.StandardScaler', RecordingScaler):
            directory = Path(root) / 'candidate'
            scorer = EcoIQScoringModel()
            result = scorer.train(companies, output_dir=directory, tune=True)
            model = joblib.load(directory / 'scoring_gbr.joblib')
            scaler = joblib.load(directory / 'scoring_scaler.joblib')
            report = json.loads((directory / 'scoring_training.json').read_text())
            self.assertEqual(report, result)
            np.testing.assert_allclose(model.predict(scaler.transform(X)),
                                       scorer.model.predict(scorer.scaler.transform(X)))

        # With 30 rows: outer train=24, inner train=16; final search train=20.
        # No validation fold participates in fitting its preprocessing.
        self.assertEqual(set(RecordingScaler.fit_sizes), {16, 20, 24, 30})
        self.assertEqual(RecordingScaler.fit_sizes.count(24), 5)
        self.assertEqual(RecordingScaler.fit_sizes.count(30), 1)
        self.assertIn('nested', result['evaluation']['method'])
        self.assertTrue(np.isfinite(result['evaluation']['mae']))
        self.assertFalse(result['evaluation']['external_validation'])
        self.assertFalse(result['independent_evidence_validated'])
        self.assertEqual(result['target'], 'existing_ecoiq_score')
        self.assertEqual(result['tuning']['n_candidates'], 8)
        for key, value in result['tuning']['selected_parameters'].items():
            self.assertEqual(model.get_params()[key], value)

    def test_insufficient_tuning_data_creates_no_artifacts(self):
        companies, X = fixtures(29)
        with TemporaryDirectory() as root, \
                patch('ml.training.company_to_vector', side_effect=lambda c: X[c.pk - 1]):
            target = Path(root) / 'candidate'
            with self.assertRaisesMessage(ValueError, 'at least 30 eligible rows'):
                EcoIQScoringModel().train(companies, output_dir=target, tune=True)
            self.assertFalse(target.exists())

    def test_direct_tuning_cannot_write_active_models_or_apply_scores(self):
        for options in ({}, {'output_dir': '/unused/candidate', 'apply': True}):
            with self.subTest(options=options), \
                    self.assertRaisesMessage(ValueError, 'candidate output directory'):
                EcoIQScoringModel().train([], tune=True, **options)

    def test_anomaly_worker_budget_rejects_unbounded_parallelism(self):
        from ml.anomaly_detection import AnomalyDetector

        with self.assertRaisesMessage(ValueError, 'Training jobs'):
            AnomalyDetector().train([], n_jobs=-1)
