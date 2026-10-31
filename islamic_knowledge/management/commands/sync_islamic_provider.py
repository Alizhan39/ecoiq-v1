import json
from pathlib import Path

import requests
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from islamic_knowledge.imports import import_export
from islamic_knowledge.providers import MAX_FEED_BYTES, PROVIDERS, ProviderUnavailable, fetch_feed


class Command(BaseCommand):
    help = 'Import an authorised Sajda/Azan.kz JSON export; new or changed passages require editorial review.'

    def add_arguments(self, parser):
        parser.add_argument('--provider', required=True, choices=tuple(PROVIDERS))
        parser.add_argument('--file', help='Normalised provider export; otherwise use the configured agreed feed.')

    def handle(self, *args, **options):
        try:
            if options['file']:
                with Path(options['file']).open('rb') as handle:
                    raw = handle.read(MAX_FEED_BYTES + 1)
                if len(raw) > MAX_FEED_BYTES:
                    raise ValueError('Export exceeds the import size limit.')
                data = json.loads(raw)
            else:
                data = fetch_feed(options['provider'])
            result = import_export(options['provider'], data)
        except (OSError, ValueError, ValidationError, ProviderUnavailable, requests.RequestException) as exc:
            # Do not echo a feed URL, credentials, or arbitrary provider body.
            raise CommandError('Import failed: verify the configured feed/export, schema and source attribution.') from exc
        self.stdout.write(json.dumps(result))
