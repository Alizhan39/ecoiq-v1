"""
Run the evaluations that can actually be run, and report the rest honestly.

    python manage.py evaluate_modules

Prints one line per module. Anything unmeasured says NOT YET MEASURED, and
there is no flag to turn that into a number.
"""
from django.core.management.base import BaseCommand

from platform_registry.evaluation import evaluate_all


class Command(BaseCommand):
    help = 'Evaluate registered modules and report what is measured.'

    def handle(self, *args, **options):
        results = evaluate_all()
        measured = [key for key, ev in results.items() if ev.is_measured]

        for key in sorted(results):
            evaluation = results[key]
            marker = 'OK ' if evaluation.is_measured else '   '
            self.stdout.write(f'{marker}{key:30s} {evaluation.summary}')
            for measurement in evaluation.measurements:
                if measurement.measured and measurement.sample_size:
                    self.stdout.write(
                        f'      n={measurement.sample_size} · {measurement.method}')

        self.stdout.write('')
        self.stdout.write(
            f'{len(measured)} of {len(results)} modules carry a measurement. '
            f'{len(results) - len(measured)} are NOT YET MEASURED, which is a '
            'truthful result and is never rendered as 0%.')
