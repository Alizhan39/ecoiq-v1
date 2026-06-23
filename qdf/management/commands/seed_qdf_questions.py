"""
Seed / refresh the 10 Quranic Decision Filter questions from
qdf/seed/decision_questions.json (idempotent).

Usage:
    python manage.py seed_qdf_questions
    python manage.py seed_qdf_questions --validate-only
"""
import json

from django.core.management.base import BaseCommand, CommandError

from qdf.scoring import load_seed, ensure_questions, RED_LINE_KEYS

REQUIRED_KEYS = ['niyyah', 'halal', 'adl', 'rahmah', 'mizan',
                 'amanah', 'maslahah', 'darar', 'shura', 'akhirah']


class Command(BaseCommand):
    help = 'Seed the 10 Quranic Decision Filter questions from the JSON seed file.'

    def add_arguments(self, parser):
        parser.add_argument('--validate-only', action='store_true',
                            help='Validate the seed file without writing to the DB.')

    def handle(self, *args, **opts):
        try:
            data = load_seed()
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f'Could not read seed file: {exc}')

        questions = data.get('questions', [])
        keys = [q.get('key') for q in questions]

        if sorted(keys) != sorted(REQUIRED_KEYS):
            raise CommandError(
                f'Seed must contain exactly these keys: {REQUIRED_KEYS}. Got: {keys}')

        for q in questions:
            for field in ('definition', 'plain_english', 'ai_prompt',
                          'evidence_required', 'red_flags', 'scoring_rubric',
                          'low_score_actions', 'example_company',
                          'example_policy', 'example_investment'):
                if not q.get(field):
                    raise CommandError(f'Question "{q.get("key")}" missing field: {field}')

        self.stdout.write(self.style.SUCCESS(
            f'Validated {len(questions)} questions '
            f'(red-line: {", ".join(sorted(RED_LINE_KEYS))}).'))

        if opts['validate_only']:
            self.stdout.write('Validate-only: no DB writes performed.')
            return

        qs = ensure_questions()
        self.stdout.write(self.style.SUCCESS(
            f'Seeded / refreshed {qs.count()} DecisionQuestion rows.'))
