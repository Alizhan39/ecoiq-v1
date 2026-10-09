"""
train_ml_models — Train and optionally apply all EcoIQ ML models.

Usage:
    python manage.py train_ml_models --output-dir=/secure/ecoiq/candidates/run-001
    python manage.py train_ml_models --model=prediction  # read-only OLS preview

Training requires a new candidate output directory by default. The explicit
--allow-legacy-write escape hatch permits legacy artefact replacement and
--apply database updates. It is NOT an approval of model quality.
Candidate output never applies scores to database records. OLS is a preview,
not an independently trained neural model.

Models:
    scoring    — GradientBoostingRegressor (writes ml_score)
    anomaly    — IsolationForest (writes anomaly_score, is_anomaly)
    clustering — KMeans (writes ml_cluster, ml_cluster_label)
    prediction — 12-month OLS forecast (writes ml_predicted_score_12m)
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError, ProgrammingError
from pathlib import Path
import time


class Command(BaseCommand):
    help = 'Train EcoIQ ML models (scoring, anomaly, clustering, prediction)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir', type=Path,
            help='New directory for candidate models and JSON evaluation reports (no DB apply)',
        )
        parser.add_argument(
            '--allow-legacy-write', action='store_true',
            help='Explicitly permit legacy artefact replacement / DB apply; not quality approval',
        )
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
        self.output_dir = Path(options['output_dir']) if options['output_dir'] else None
        if apply and self.output_dir:
            raise CommandError('--output-dir candidates cannot be combined with --apply.')
        legacy_write = options['allow_legacy_write']
        if legacy_write and self.output_dir:
            raise CommandError('--allow-legacy-write cannot be combined with --output-dir.')
        if not self.output_dir and not legacy_write and (model_choice != 'prediction' or apply):
            raise CommandError(
                'Use --output-dir for safe candidate training. Legacy writes require '
                '--allow-legacy-write after independent review; --apply alone is not sufficient.'
            )
        if legacy_write:
            self.stderr.write(self.style.WARNING(
                'Legacy writes enabled: training may replace active artefacts; --apply also '
                'updates company records. This flag does not establish production readiness.'
            ))
        width        = 60

        self.stdout.write('═' * width)
        self.stdout.write('  EcoIQ ML Training Pipeline')
        self.stdout.write(f'  Model: {model_choice}   Apply: {apply}')
        self.stdout.write('═' * width)

        # Pre-fetch all companies once (shared across models)
        try:
            companies = list(Company.objects.filter(ecoiq_score__gt=0).select_related('profile').order_by('pk'))
        except (OperationalError, ProgrammingError) as exc:
            raise CommandError('Training data unavailable. Check database access and migrations.') from exc
        self.stdout.write(f'\n  Companies with scores: {len(companies)}')

        if not companies:
            raise CommandError('No companies with ecoiq_score > 0. Import reviewed data first.')

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
            result = scorer.train(companies=companies, apply=apply, **self._candidate_options('scoring'))
            if 'error' in result:
                raise CommandError(f'Scoring not trained: {result["error"]}; eligible={result["n_samples"]}.')
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ n={result["n_samples"]}  '
                    + (f'CV R²={result["r2_mean"]:.3f}±{result["r2_std"]:.3f}  '
                       f'MAE={result["evaluation"]["mae"]:.3f}  '
                       f'baseline MAE={result["evaluation"]["baseline_mae"]:.3f}'
                       if result['r2_mean'] is not None else 'quality=NOT_MEASURED')
                    + ('  [applied]' if apply else '')
                ))
        except ImportError as exc:
            raise CommandError(f'Scoring dependencies unavailable: {exc}') from exc
        except Exception as exc:
            raise CommandError(f'Scoring training failed: {exc}') from exc
        self.stdout.write(f'  ({time.time() - t0:.1f}s)')

    def _run_anomaly(self, companies, apply: bool):
        self.stdout.write('\n→ Anomaly Detection (Isolation Forest)…')
        t0 = time.time()
        try:
            from ml.anomaly_detection import AnomalyDetector
            detector = AnomalyDetector()
            result   = detector.train(companies=companies, apply=apply, **self._candidate_options('anomaly'))
            if 'error' in result:
                raise CommandError(f'Anomaly not trained: {result["error"]}; eligible={result["n_samples"]}.')
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ n={result["n_samples"]}  '
                    f'anomalies={result["n_anomalies"]}'
                    + ('  [applied]' if apply else '')
                ))
        except ImportError as exc:
            raise CommandError(f'Anomaly dependencies unavailable: {exc}') from exc
        except Exception as exc:
            raise CommandError(f'Anomaly training failed: {exc}') from exc
        self.stdout.write(f'  ({time.time() - t0:.1f}s)')

    def _run_clustering(self, companies, apply: bool):
        self.stdout.write('\n→ Clustering (K-Means, k=6)…')
        t0 = time.time()
        try:
            from ml.clustering import CompanyClusterer
            clusterer = CompanyClusterer()
            result    = clusterer.train(companies=companies, apply=apply, **self._candidate_options('clustering'))
            if 'error' in result:
                raise CommandError(f'Clustering not trained: {result["error"]}; eligible={result["n_samples"]}.')
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
            raise CommandError(f'Clustering dependencies unavailable: {exc}') from exc
        except Exception as exc:
            raise CommandError(f'Clustering training failed: {exc}') from exc
        self.stdout.write(f'  ({time.time() - t0:.1f}s)')

    def _candidate_options(self, name):
        return {'output_dir': self.output_dir / name} if self.output_dir else {}

    def _run_prediction(self, companies, apply: bool):
        self.stdout.write('\n→ 12-Month Score Prediction (OLS trend)…')
        t0 = time.time()
        try:
            from ml.prediction import apply_predictions
            if apply:
                result = apply_predictions(companies=companies)
                if result['failed']:
                    raise CommandError(f'Prediction application failed for {result["failed"]} companies.')
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
            raise CommandError(f'Prediction failed: {exc}') from exc
        self.stdout.write(f'  ({time.time() - t0:.1f}s)')
