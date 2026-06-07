"""Idempotently seed the five Khalifa Heat household packages."""
from django.core.management.base import BaseCommand

from heating.models import HeatingPackage
from heating.seed_data import PACKAGE_SEED


class Command(BaseCommand):
    help = 'Seed/refresh the Khalifa Heat household packages (idempotent by slug).'

    def handle(self, *args, **options):
        created, updated = 0, 0
        for row in PACKAGE_SEED:
            obj, was_created = HeatingPackage.objects.update_or_create(
                slug=row['slug'], defaults=row,
            )
            created += int(was_created)
            updated += int(not was_created)
        self.stdout.write(self.style.SUCCESS(
            f'Khalifa Heat packages — created {created}, updated {updated}.'
        ))
