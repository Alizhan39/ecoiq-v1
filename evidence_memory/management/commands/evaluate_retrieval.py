"""Reproducible lexical/semantic benchmark without accessing project evidence."""
import json
from importlib.metadata import version
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from evidence_memory.evaluation.benchmark import LocalSemanticEncoder, evaluate, hashing_encoder, load_dataset


class Command(BaseCommand):
    help = 'Evaluate retrieval against synthetic, explicitly labelled source judgements.'

    def add_arguments(self, parser):
        parser.add_argument('--dataset', default=str(Path(settings.BASE_DIR) / 'evidence_memory/evaluation/control_set.json'))
        parser.add_argument('--semantic-model-dir')
        parser.add_argument('--output', required=True)

    def handle(self, *args, **options):
        try:
            data = load_dataset(options['dataset'])
            report = {'dataset': data['name'], 'dataset_sha256': data['sha256'],
                      'document_count': len(data['documents']), 'question_count': len(data['queries']),
                      'scope': 'Synthetic diagnostic set; not a production accuracy estimate or a calibrated confidence score.',
                      'lexical': evaluate(data, hashing_encoder, {'name': 'production HashingVectorizer', 'sklearn': version('scikit-learn')}),
                      'semantic': {'status': 'not_run', 'reason': 'No local semantic model supplied.'}}
            if options['semantic_model_dir']:
                semantic = LocalSemanticEncoder(options['semantic_model_dir'])
                report['semantic'] = evaluate(data, semantic, semantic.identity)
            Path(options['output']).write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        except (ValueError, OSError, ImportError, KeyError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps({k: v.get('answerable', v) for k, v in report.items() if k in ('lexical', 'semantic')}, indent=2))
