from django.core.management.base import BaseCommand, CommandError

from islamic_knowledge.neural import NeuralUnavailable, index_passages


class Command(BaseCommand):
    help = 'Batch-encode published passages with the pinned multilingual neural model.'

    def handle(self, *args, **options):
        try:
            count = index_passages()
        except (NeuralUnavailable, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f'Indexed {count} passages.')
