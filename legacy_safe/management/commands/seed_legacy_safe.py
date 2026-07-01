"""
Seed the LegacySafe AI demo project (idempotent).

Usage:
    python manage.py seed_legacy_safe
"""
from django.core.management.base import BaseCommand

from legacy_safe.services.seed_demo import create_demo_data


class Command(BaseCommand):
    help = 'Seed the Samruk Energy LegacySafe AI demo project, documents, and derived memory.'

    def handle(self, *args, **opts):
        project = create_demo_data()
        self.stdout.write(self.style.SUCCESS(
            f'LegacySafe AI demo ready: "{project.name}" '
            f'({project.source_documents.count()} documents, '
            f'{project.derived_memories.count()} derived memories).'
        ))
