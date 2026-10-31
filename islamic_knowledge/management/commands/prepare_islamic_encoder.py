from django.core.management.base import BaseCommand, CommandError

from islamic_knowledge.neural import MODEL_VERSION, NeuralUnavailable, load_encoder


class Command(BaseCommand):
    help = 'Check pinned local neural weights; --download explicitly prepares them before serving requests.'

    def add_arguments(self, parser):
        parser.add_argument('--download', action='store_true')

    def handle(self, *args, **options):
        try:
            load_encoder(allow_download=options['download'])
        except NeuralUnavailable as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f'Prepared {MODEL_VERSION}')
