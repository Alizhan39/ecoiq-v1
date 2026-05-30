"""
train_ml_models — Train and optionally apply all EcoIQ ML models.

Usage:
    python manage.py train_ml_models                         # train all, no apply
    python manage.py train_ml_models --apply                 # train all + write to DB
    python manage.py train_ml_models --model=scoring         # only GBR scoring
    python manage.py train_ml_models --model=anomaly --apply
    python manage.py train_ml_models --model=clustering --apply
    python manage.py train_ml_models --model=prediction --apply

Models:
    scoring    — GradientBoostingRegressor (writes ml_score)
    anomaly    — IsolationForest (writes anomaly_score, is_anomaly)
    clustering — KMeans (writes ml_cluster, ml_cluster_label)
    prediction — 12-month OLS forecast (writes ml_predicted_score_12m)
"""
from django.core.management.base import BaseCommand
import time


class Command(BaseCommand):
    help = 'Train EcoIQ ML models (scoring, anomaly, clustering, prediction)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            choices=['all', 'scoring', 'anomaly', 'clustering', 'prediction'],
            default='all',
            help='Which ML model to train (default: all)',
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            default=False,
            help='Write ML results back to Company records in the database',
        )

    def handle(self, *args, **options):
        from league.models import Company

        model_choice = options['model']
        apply        = options['apply']
        width        = 60

        self.stdout.write('═' * width)
        self.stdout.write('  EcoIQ ML Training Pipeline')
        self.stdout.write(f'  Model: {model_choice}   Apply: {apply}')
        self.stdout.write('═' * width)

        # Pre-fetch all companies once (shared across models)
        companies = list(
            Company.objects.filter(ecoiq_score__gt=0).select_related('profile')
        )
        self.stdout.write(f'\n  Companies with scores: {len(companies)}')

        if not companies:
            self.stdout.write(self.style.WARNING(
                '  No companies with ecoiq_score > 0. Add data first.'
            ))
            return

        start_total = time.time()

        if model_choice in ('all', 'scoring'):
            self._run_scoring(companies, apply)

        if model_choice in ('all', 'anomaly'):
            self._run_anomaly(companies, apply)

        if model_choice in ('all', 'clustering'):
            self._run_clustering(companies, apply)

        if model_choice in ('all', 'prediction'):
            self._run_prediction(companies, apply)

        total = time.time() - start_total
        self.stdout.write('\n' + '═' * width)
        self.stdout.write(self.style.SUCCESS(f'  ML pipeline complete in {total:.1f}s'))
        self.stdout.write('═' * width)

    # ── Sub-runners ─────────────────────────────────────────────────────────

    def _run_scoring(self, companies, apply: bool):
        self.stdout.write('\n→ Scoring (Gradient Boosting Regressor)…')
        t0 = time.time()
        try:
            from ml.scoring_model import EcoIQScoringModel
            scorer = EcoIQScoringModel()
            result = scorer.train(companies=companies, apply=apply)
            if 'error' in result:
                self.stdout.write(self.style.WARNING(f'  Skipped: {result["error"]}'))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ n={result["n_samples"]}  '
                    f'R²={result["r2_mean"]:.3f}±{result["r2_std"]:.3f}'
                    + ('  [applied]' if apply else '')
                ))
        except ImportError as exc:
            self.stdout.write(self.style.ERROR(
                f'  scikit-learn / shap not installed: {exc}\n'
                f'  Run: pip install scikit-learn shap'
            ))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'  Scoring error: {exc}'))
        self.stdout.write(f'  ({time.time() - t0:.1f}s)')

    def _run_anomaly(self, companies, apply: bool):
        self.stdout.write('\n→ Anomaly Detection (Isolation Forest)…')
        t0 = time.time()
        try:
            from ml.anomaly_detection import AnomalyDetector
            detector = AnomalyDetector()
            result   = detector.train(companies=companies, apply=apply)
            if 'error' in result:
                self.stdout.write(self.style.WARNING(f'  Skipped: {result["error"]}'))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ n={result["n_samples"]}  '
                    f'anomalies={result["n_anomalies"]}'
                    + ('  [applied]' if apply else '')
                ))
        except ImportError as exc:
            self.stdout.write(self.style.ERROR(f'  scikit-learn not installed: {exc}'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'  Anomaly error: {exc}'))
        self.stdout.write(f'  ({time.time() - t0:.1f}s)')

    def _run_clustering(self, companies, apply: bool):
        self.stdout.write('\n→ Clustering (K-Means, k=6)…')
        t0 = time.time()
        try:
            from ml.clustering import CompanyClusterer
            clusterer = CompanyClusterer()
            result    = clusterer.train(companies=companies, apply=apply)
            if 'error' in result:
                self.stdout.write(self.style.WARNING(f'  Skipped: {result["error"]}'))
            else:
                labels_str = '  '.join(
                    f'{k}:{v}' for k, v in result.get('cluster_labels', {}).items()
                )
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ n={result["n_samples"]}  clusters={result["n_clusters"]}'
                    + ('  [applied]' if apply else '')
                ))
                self.stdout.write(f'  Labels: {labels_str}')
        except ImportError as exc:
            self.stdout.write(self.style.ERROR(f'  scikit-learn not installed: {exc}'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'  Clustering error: {exc}'))
        self.stdout.write(f'  ({time.time() - t0:.1f}s)')

    def _run_prediction(self, companies, apply: bool):
        self.stdout.write('\n→ 12-Month Score Prediction (OLS trend)…')
        t0 = time.time()
        try:
            from ml.prediction import apply_predictions
            if apply:
                result = apply_predictions(companies=companies)
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ updated={result["updated"]}  failed={result["failed"]}  [applied]'
                ))
            else:
                # Just preview without saving
                previewed = 0
                for company in companies[:5]:
                    from ml.prediction import predict_12m
                    pred = predict_12m(company)
                    if pred is not None:
                        self.stdout.write(
                            f'  Preview: {company.name[:40]:<40} → {pred:.1f}'
                        )
                        previewed += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ previewed {previewed} companies (use --apply to save)'
                ))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'  Prediction error: {exc}'))
        self.stdout.write(f'  ({time.time() - t0:.1f}s)')
