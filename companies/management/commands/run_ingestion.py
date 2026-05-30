"""
run_ingestion — Master command: runs all or selected data ingestion pipelines.

Usage:
    python manage.py run_ingestion                # all pipelines
    python manage.py run_ingestion --source=yfinance
    python manage.py run_ingestion --source=rss
    python manage.py run_ingestion --source=cdp
    python manage.py run_ingestion --source=sec
    python manage.py run_ingestion --source=ch
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
import time


class Command(BaseCommand):
    help = 'Run all EcoIQ data ingestion pipelines (or a specific one)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['all', 'yfinance', 'sec', 'cdp', 'rss', 'ch'],
            default='all',
            help='Which pipeline to run (default: all)',
        )

    def handle(self, *args, **options):
        source = options['source']
        width  = 56

        self.stdout.write('═' * width)
        self.stdout.write('  EcoIQ Automated Data Ingestion Pipeline')
        self.stdout.write(f'  Source: {source}')
        self.stdout.write('═' * width)

        pipelines = [
            ('yfinance', 'Yahoo Finance / Bloomberg (financial + ESG)', 'ingest_yfinance'),
            ('sec',      'SEC EDGAR (US company disclosures)',           'ingest_sec_edgar'),
            ('cdp',      'CDP Climate Scores',                           'ingest_cdp'),
            ('rss',      'Regulatory RSS Signals',                       'ingest_rss_signals'),
            ('ch',       'Companies House UK',                           'ingest_companies_house'),
        ]

        start_total = time.time()

        for key, label, cmd in pipelines:
            if source not in ('all', key):
                continue

            self.stdout.write(f'\n→ {label}…')
            t0 = time.time()
            try:
                call_command(cmd)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'  Pipeline error: {exc}'))
            elapsed = time.time() - t0
            self.stdout.write(f'  (completed in {elapsed:.1f}s)')

        total = time.time() - start_total
        self.stdout.write('\n' + '═' * width)
        self.stdout.write(self.style.SUCCESS(
            f'  All pipelines complete in {total:.1f}s'
        ))
        self.stdout.write('═' * width)
